# -*- coding: utf-8 -*-
# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

"""The subtitle creation pipeline.

To understand why this module/idea is necessary you need to understand the pain
that not having it causes.

In the beginning was videos.models.SubtitleVersion.  When you needed to update
some subtitles for a video, you created a new SubtitleVersion and saved it in
the standard Django manner.  This is simple, but things quickly spiraled out of
control.

First, there are a number of special things you may or may not need to do when
adding a new version.  You need to check that the user actually has permission
to add it.  It probably needs to trigger reindexing (if it's public).  It may
need to interact with tasks.  There are many little things like this.

Second, there are a number of places where we need to add versions.  Obviously
the subtitling dialog needs to create them, as do the Review/Approve dialog.  So
does the "rollback" functionality.  The "upload a subtitle file" process create
versions.

If you try to stick with a simple Django model creation for all the places
versions are created, you need to perform all the fiddly little checks in all
those places.  This quickly becomes painful and unmanageable.

And so we come to the subtitle pipeline.  Its purpose is to encapsulate the
process of adding subtitles to keep all the painful complexity in one place.  In
a nutshell:

                                subtitles go in
                                       ||
                         (pipeline handles everything)
                                       ||
                                       \/
                           SubtitleVersion comes out

"""

from django.db import transaction

from videos.models import Video
from subtitles.models import (
    SubtitleLanguage, SubtitleVersion, ORIGIN_ROLLBACK, ORIGIN_API,
    ORIGIN_UPLOAD, ORIGIN_WEB_EDITOR
)
from subtitles import signals
from subtitles import workflows
from teams.signals import api_subtitles_edited

# Utility Functions -----------------------------------------------------------
def _strip_nones(d):
    """Strip all entries in a dictionary that have a value of None."""

    items = d.items()
    for k, v in items:
        if v == None:
            d.pop(k)


# Private Implementation ------------------------------------------------------
def _perform_team_operations(version, committer, action):
    """Perform any teams-based operations that need to happen to this version.

    If the version is not on a video from a team, does nothing.

    Otherwise, performs all the extra fiddly steps that need to happen to
    appease the teams system gods.

    """
    from teams.workflows.old.subtitleworkflows import Complete

    team_video = version.video.get_team_video()

    if not team_video:
        return

    complete = isinstance(action, Complete)

    _record_workflow_origin(team_video, version)
    _update_visibility_and_tasks(team_video, version, committer, complete)

def _record_workflow_origin(team_video, version):
    """Figure out and record where the given version started out.

    Should be used right after creation.

    This is a giant ugly hack.  It can be killed once the new UI is in place.
    I'm sorry.

    """
    if version and not version.get_workflow_origin():
        tasks = team_video.task_set.incomplete()
        tasks = list(tasks.filter(language=version.language_code)[:1])

        if tasks:
            open_task_type = tasks[0].get_type_display()

            workflow_origin = {
                'Subtitle': 'transcribe',
                'Translate': 'translate',
                'Review': 'review',
                'Approve': 'approve'
            }.get(open_task_type)

            if workflow_origin:
                version.set_workflow_origin(workflow_origin)

def _user_can_bypass_moderation(team_video, version, committer):
    """Determine whether the given committer can bypass moderation for this video.

    A user can bypass moderation iff:

    1) They are a moderator.
    2) This version is a post-publish edit.
    3) The subtitles are complete.

    If no committer is specified, treat the current user as a super user.

    Note that version.subtitle_language.subtitles_complete must be correctly set
    *before* this for this to work properly.

    TODO: Can we eliminate that property?  Are moderators going to be submitting
    incomplete subtitles as post-publish edits?  Why would that happen?

    """
    if not committer:
        return True

    from teams.permissions import can_publish_edits_immediately
    subtitle_language = version.subtitle_language

    is_post_publish_edit = (version.sibling_set.public()
                                               .exclude(id=version.id)
                                               .exists())
    user_can_bypass = can_publish_edits_immediately(team_video, committer,
                                                    subtitle_language.language_code)

    return is_post_publish_edit and user_can_bypass

def _set_language_for_subtitle_tasks(team_video, saved_version):
    """Set the language attribute for subtitle tasks.

    When tasks are created, we don't know the primary language, so subtitle
    tasks might not have their language set.  We should set it when we save
    the primary audio-language
    """
    if saved_version.subtitle_language.is_primary_audio_language():
        subtitle_tasks = team_video.task_set.incomplete_subtitle()
        for task in subtitle_tasks.filter(language=''):
            task.language = saved_version.language_code
            task.save()

def _handle_outstanding_tasks(outstanding_tasks, version, team_video, committer,
                              complete):
    """Handle any existing tasks for this subtitle addition."""
    from teams.permissions import can_assign_task

    language_code = version.language_code

    # There are tasks for this video.  If this version isn't published yet, it
    # belongs to those tasks, so update them.
    if version.visibility != 'public':
        outstanding_tasks.update(new_subtitle_version=version,
                                 language=language_code)

    # There may be existing subtitle/translate tasks.
    outstanding_subtrans_tasks = (
        team_video.task_set.incomplete_subtitle_or_translate()
                           .filter(language=language_code)
    )

    if outstanding_subtrans_tasks.exists():
        for task in outstanding_subtrans_tasks.all():
            # If there are any outstanding subtitle/translate tasks that are
            # unassigned, we can go ahead and assign them to the committer (as long
            # as they have permission to do so).
            if not task.assignee and committer and can_assign_task(task, committer):
                task.assignee = committer

                # We save here only if the subtitles are not complete, because
                # .complete() actually saves the task too.
                if not complete:
                    task.save()

            # Also, if the subtitles are complete, we can mark that outstanding
            # subtitle/translate task as complete.
            if complete:
                task.new_subtitle_version = version
                task.complete()

    # Outstanding review/approve tasks will need to be handled elsewhere.
    # TODO: Handle those here as well?

def _create_necessary_tasks(version, team_video, workflow, committer, complete):
    """Create any necessary tasks for the newly added version.

    By the time we call this function we know that:

    * There are no existing open tasks for this version/language.
    * The committer cannot bypass moderation.

    So we may (or may not) need to create a task for this version/language.

    """
    from teams.models import Task

    if complete:
        # If the subtitles are complete, then the new task will be either
        # a review or approve, depending on the team.
        if workflow.review_allowed:
            task_type = Task.TYPE_IDS['Review']
        elif workflow.approve_allowed:
            task_type = Task.TYPE_IDS['Approve']
        else:
            # Note that we may not have selected either of these, if the team
            # does not require review or approval.  That's okay, we're done in
            # that case.
            return
    else:
        # Otherwise the new task will be a subtitle or translate, depending
        # on the type of subs.
        # TODO: More advanced logic here?
        if version.subtitle_language.is_primary_audio_language():
            task_type = Task.TYPE_IDS['Subtitle']
        else:
            task_type = Task.TYPE_IDS['Translate']

    # We now know the type of task we need to create, so go ahead and make it.
    task = Task(team=team_video.team, team_video=team_video,
                language=version.language_code, type=task_type,
                new_subtitle_version=version)

    # Assign it to the correct user.
    if task.get_type_display() in ('Subtitle', 'Translate'):
        # If it's a subtitle/translate task, then someone just added
        # some incomplete subtitles.  We'll assign it to them by
        # default.
        task.assignee = committer
    else:
        # Otherwise it's a review/approve task, so we'll see if anyone
        # has reviewed or approved this before.  If so, assign it back
        # to them.  Otherwise just leave it unassigned.
        task.assignee = task._find_previous_assignee(
            task.get_type_display())

    task.save()

def _update_visibility_and_tasks(team_video, version, committer, complete):
    """Set the appropriate visibility flags for the new version.

    I hate everything about this.  This is all going to go away once the new UI
    is in place and we tear out the tasks system.  That day cannot come soon
    enough.

    """
    team = team_video.team

    # If the team does not use tasks, all versions are just public and we're
    # done here.  God help you if you have a team that has some existing tasks
    # and switches to "no tasks allowed".
    if not team.workflow_enabled:
        return

    workflow = team.get_workflow()

    # We know the workflow uses tasks.  However, the user may be able to bypass
    # the moderation system in some cases.
    can_bypass_moderation = _user_can_bypass_moderation(team_video, version,
                                                        committer)

    # If the user cannot bypass moderation, and the team's workflow requires
    # a review or approval step, then the version needs to be marked as private.
    if not can_bypass_moderation:
        if workflow.review_allowed or workflow.approve_allowed:
            version.visibility = 'private'
            version.save()

    _set_language_for_subtitle_tasks(team_video, version)

    # Okay, so now we have an appropriately-visibile version.  Next we see if
    # there are any outstanding tasks for this version/language.
    outstanding_tasks = team_video.task_set.incomplete().filter(
            language__in=[version.language_code, ''])

    if outstanding_tasks.exists():
        # If so, handle them.
        _handle_outstanding_tasks(outstanding_tasks, version, team_video,
                                  committer, complete)
    else:
        # Otherwise, there are no existing tasks.  We probably want to make
        # some, *unless* the user can bypass moderation.  If that's the case we
        # don't need to bother.
        if can_bypass_moderation:
            pass
        else:
            _create_necessary_tasks(version, team_video, workflow, committer,
                                    complete)

def _update_followers(subtitle_language, author):
    """Update language followers when adding a new version."""
    if author:
        subtitle_language.followers.add(author)

def _fork_dependents(subtitle_language):
    for dsl in subtitle_language.get_dependent_subtitle_languages(direct=True):
        dsl.fork()

def _get_version(video, v):
    """Get the appropriate SV belonging to the given video.

    Works with SubtitleVersions, ids, and (language_code, version_number) pairs.

    """
    if isinstance(v, SubtitleVersion):
        if v.video_id != video.id:
            raise SubtitleVersion.DoesNotExist(
                "That SubtitleVersion does not belong to this Video!")
        else:
            return v
    elif isinstance(v, int):
        return SubtitleVersion.objects.get(video=video, id=v)
    elif isinstance(v, tuple) or isinstance(v, list):
        language_code, version_number = v
        return SubtitleVersion.objects.get(video=video,
                                           language_code=language_code,
                                           version_number=version_number)
    else:
        raise ValueError("Cannot look up version from %s" % type(v))

def _get_language(video, language_code):
    """Return appropriate SubtitleLanguage and a needs_save boolean.

    If a SubtitleLanguage for this video/language does not exist, an unsaved one
    will be created and returned.  It's up to the caller to save it if
    necessary.

    """
    try:
        with transaction.atomic():
            # Use select_for_update() to lock the row for the language we're
            # about to update.  Since we know that we're going to do some
            # work, then update the language, locking at the start prevents
            # deadlocks.
            return (SubtitleLanguage.objects.select_for_update()
                  .get(video=video, language_code=language_code))
    except SubtitleLanguage.DoesNotExist:
        return SubtitleLanguage.objects.create(video=video,
                                               language_code=language_code)

def _timings_changed(subtitle_language, new_version):
    """Calculate if the number of subtitles or the timings the subtitles have
    changed between the tip version and the previous version.
    """
    previous_version = new_version.previous_version()
    if previous_version is None:
        return False
    new_timings = [(s.start_time, s.end_time)
                   for s in new_version.get_subtitles()]
    old_timings = [(s.start_time, s.end_time)
                   for s in previous_version.get_subtitles()]
    return new_timings != old_timings


def _add_subtitles(video, sl, subtitles, title, duration, description, author,
                   visibility, visibility_override, parents,
                   rollback_of_version_number, committer, created, note,
                   origin, metadata, action):
    """Add subtitles in the language to the video.  Really.

    This function is the meat of the subtitle pipeline.  The user-facing
    add_subtitles is a thin wrappers around this.
    """
    with transaction.atomic():
        # Use select_for_update() to lock the row for our video.  We know
        # that we're going to do some work, then potentially update the video,
        # locking at the start prevents deadlocks.
        Video.objects.select_for_update().get(id=video.id)

        data = {'title': title, 'duration': duration, 'description': description, 'author': author,
                'visibility': visibility, 'visibility_override': visibility_override,
                'parents': [_get_version(video, p) for p in (parents or [])],
                'rollback_of_version_number': rollback_of_version_number,
                'created': created, 'note': note, 'origin': origin,
                'metadata': metadata}
        _strip_nones(data)
        version = sl.add_version(subtitles=subtitles, **data)
        _perform_team_operations(version, committer, action)
        if action:
            action.validate(author, video, sl, version)
            action.update_language(author, video, sl, version)
        _update_followers(sl, author)
        if origin in (ORIGIN_UPLOAD, ORIGIN_API):
            _fork_dependents(sl)
        elif origin == ORIGIN_WEB_EDITOR and _timings_changed(sl, version):
            # fork languages when they are edited in the new editor, since it's
            # easy to make things out-of-sync from the source language.  Once we
            # switch over to only using the new editor, we can get rid of the
            # entire concept of forking.
            sl.fork()
            _fork_dependents(sl)
        return version

def _rollback_to(video, subtitle_language, version_number, rollback_author):
    current = subtitle_language.get_tip(full=True)
    target = subtitle_language.subtitleversion_set.full().get(version_number=version_number)

    # The new version is mostly a copy of the target.
    data = {
        'video': target.video,
        'sl': subtitle_language,
        'subtitles': target.get_subtitles(),
        'title': target.title,
        'duration': target.duration,
        'description': target.description,
        'visibility_override': None,
        'committer': None,
        'created': None,
        'action': None,
        'note': target.note,
        'metadata': target.get_metadata(),
        'origin': ORIGIN_ROLLBACK,
    }

    # If any version in the history is public, then rollbacks should also result
    # in public versions.
    existing_versions = target.sibling_set.extant()
    data['visibility'] = ('public'
                          if any(v.is_public() for v in existing_versions)
                          else 'private')

    # The author of the rollback is distinct from the target's author.
    data['author'] = rollback_author

    # The new version is always simply a child of the current tip.
    data['parents'] = None

    # Finally, rollback versions have a special attribute to track them.
    data['rollback_of_version_number'] = version_number

    version = _add_subtitles(**data)

    # Rolling back to a version with a different number of subtitles needs to
    # fork the dependent translations.  For now.  Once the new UI is in place
    # this horrible "forking" crap is going away entirely.
    if current.subtitle_count != target.subtitle_count:
        _fork_dependents(version.subtitle_language)

    api_subtitles_edited.send(version)

    return version


# Public API ------------------------------------------------------------------
def add_subtitles(video, language_code, subtitles,
                  title=None, description=None, author=None,
                  visibility=None, visibility_override=None,
                  parents=None, committer=None, complete=None,
                  created=None, note=None, origin=None, metadata=None,
                  action=None, duration=None):
    """Add subtitles in the language to the video.  It all starts here.

    This function is your main entry point to the subtitle pipeline.

    It runs in a transaction, so while it may fail the DB should be left in
    a consistent state.

    If you already have a transaction running you can use unsafe_add_subtitles
    to avoid dealing with nested transactions.

    You need to check writelocking yourself.  For now.  This may change in the
    future.

    Subtitles can be given as a SubtitleSet, or a list of
    (from_ms, to_ms, content) tuples, or a string containing a hunk of DXFP XML.

    Title and description should be strings, or can be omitted to set them to
    ''.  If you want them to be set to the same thing as the previous version
    you need to pass it yourself.

    Author can be given as a CustomUser object.  If omitted the author will be
    marked as anonymous.

    Visibility and visibility_override can be given as the strings 'public' or
    'private', or omitted to use the defaults ('public' and '' respectively).

    Parents can be given as an iterable of parent identifiers.  These can be
    SubtitleVersion objects, or integers representing primary keys of
    SubtitleVersions, or tuples of (language_code, version_number).  Note that
    the previous version of the language (if any) will always be marked as
    a parent.

    Committer can be given as a CustomUser object.  This should be the user
    actually performing the action of adding the subtitles.  Permissions and
    such will be checked as if this user is adding them.  If omitted, the
    permission checks will be skipped, as if a "superuser" were adding the
    subtitles.

    Complete is a deprecated param that is needed for the API.  It alters how
    we handle the subtitles_complete attribute on the language.  New code
    should use action instead.

    action can be given as an action string.  If given, we will perform that
    action using the saved version.

    Created should be a datetime that will set the "created" date for the
    resulting version.  If not given it will default to today.

    """
    # complete and action do similar things.  In _add_subtitles _add_subtitles
    # we only want to deal with action, not complete.  this 

    action = _calc_action_for_add_subtitles(video, language_code, author,
                                            complete, action)
    if action:
        visibility = action.subtitle_visibility
    with transaction.atomic():
        subtitle_language = _get_language(video, language_code)
        subtitle_language.freeze()
        version = _add_subtitles(video, subtitle_language, subtitles, title,
                                 duration, description, author, visibility,
                                 visibility_override, parents, None, committer,
                                 created, note, origin, metadata, action)
    video.cache.invalidate()
    api_subtitles_edited.send(version)
    if action:
        action.perform(author, video, version.subtitle_language, version)
    subtitle_language.thaw()

    return version

def _calc_action_for_add_subtitles(video, language_code, author, complete,
                                   action_name):
    # complete and action do similar things.  In _add_subtitles _add_subtitles
    # we only want to deal with action, not complete.  this 

    if action_name and complete is not None:
        raise ValueError("Both action and complete set")

    workflow = workflows.get_workflow(video)
    if action_name:
        return workflow.lookup_action(author, language_code, action_name)
    else:
        return workflow.action_for_add_subtitles(author, language_code,
                                                 complete)

def rollback_to(video, language_code, version_number,
                rollback_author=None):
    """Rollback to the given video/language/version.

    A rollback creates a new version at the tip of the branch, identical to the
    target version except for a few items:

    * The parent is simply the current tip, regardless of the target's parents.
    * The author of the rollback is distinct from the target's author.
    * The new version will be public if ANY version in the history is public,
      or private otherwise.

    If the target version does not exist, a SubtitleVersion.DoesNotExist
    exception will be raised.

    This function runs in a transaction, so while it may fail the DB should be
    left in a consistent state.

    """
    subtitle_language = SubtitleLanguage.objects.get(video=video,
                                                     language_code=language_code)
    subtitle_language.freeze()
    with transaction.atomic():
        version = _rollback_to(video, subtitle_language, version_number,
                               rollback_author)
    video.cache.invalidate()
    subtitle_language.thaw()
    return version

