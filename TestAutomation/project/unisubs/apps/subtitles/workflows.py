# Amara, universalsubtitles.org
#
# Copyright (C) 2014 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.

"""
Subtitle Workflows
==================

Subtitle workflows control how subtitle sets get edited and published.  In
particular they control:

- Work Modes -- Tweak the subtitle editor behavior (for example review mode)
- Actions -- User actions that can be done to subtitle sets (Publish,
  Approve, Send back, etc).
- Permissions -- Who can edit subtitles, who can view private subtitles

Overriding workflows
--------------------

By default, we use a workflow that makes sense for public videos -- Anyone
can edit, the only action is Publish, etc.

**To override the workflow by Video** (for example for videos in a
certain type of team):
    - Create a :class:`VideoWorkflow` subclass
    - Create a :class:`LanguageWorkflow` subclass (make this returned by
      VideoWorkflow.get_default_language_workflow())
    - Override :func:`get_workflow` and return your custom VideoWorkflow

**To override the workflow for by SubtitleLanguage** (for example you can
override the workflow for the SubtitleLanguage covered by professional service
request):
    - Create a :class:`LanguageWorkflow` subclass
    - Override :func:`get_language_workflow` and return your custom
      LanguageWorkflow


Workflow Classes
----------------

.. autoclass:: VideoWorkflow
    :members: user_can_view_video, user_can_edit_video, get_add_language_mode, extra_tabs, get_default_language_workflow

.. autoclass:: LanguageWorkflow
    :members: get_work_mode, get_actions, action_for_add_subtitles,
        get_editor_notes, user_can_edit_subtitles,
        user_can_view_private_subtitles, user_can_delete_subtitles

Behavior Functions
------------------
.. autofunction:: get_workflow(video)
.. autofunction:: get_language_workflow(video, language_code)

.. seealso::

    :doc:`behaviors module<behaviors>` for how you can override these
    functions.

Editor Notes
------------
.. autoclass:: EditorNotes

Work Modes
----------
.. autoclass:: WorkMode

Actions
-------

Actions are things things that users can do to a subtitle set other than
changing the actual subtitles.  They correspond to the buttons in the editor
at the bottom of the workflow session (publish, endorse, send back, etc).
Actions can occur alongside changes to the subtitle lines or independent of
them.

.. autoclass:: Action
   :members:

.. autoclass:: Publish

"""

from collections import namedtuple
from datetime import datetime, timedelta
import logging

from django.utils.translation import ugettext_lazy
from django.utils.translation import ugettext as _

from subtitles import signals
from subtitles.exceptions import ActionError
from subtitles.models import SubtitleNote
from utils.behaviors import behavior

logger = logging.getLogger(__name__)

class Workflow(object):
    """
    **Deprecated**

    We used to have everything in 1 class, the new system is to split this
    code into VideoWorkflow and LanguageWorkflow.
    """

    def __init__(self, video):
        self.video = video

    def get_work_mode(self, user, language_code):
        """Get the work mode to use for an editing session

        Args:
            user (User): user who is editing
            language_code (str): language being edited

        Returns:
            :class:`WorkMode` object to use
        """
        raise NotImplementedError()

    def get_actions(self, user, language_code):
        """Get available actions for a user

        Args:
            user (User): user who is editing
            language_code (str): language being edited

        Returns:
            list of :class:`Action` objects that are available to the user.
        """
        raise NotImplementedError()

    def action_for_add_subtitles(self, user, language_code, complete):
        """Get an action to use for add_subtitles()

        This is used when pipeline.add_subtitles() is called, but not passed
        an action.  This happens for a couple reasons:

        - User saves a draft (in which case complete will be None)
        - User is adding subtitles via the API (complete can be True, False,
          or None)

        Subclasses can override this method if they want to use different
        actions to handle this case.

        Args:
            user (User): user adding subtitles
            language_code (str): language being edited
            complete (bool or None): complete arg from add_subtitles()

        Returns:
            Action object or None.
        """
        if complete is None:
            return None
        elif complete:
            return APIComplete()
        else:
            return Unpublish()

    def extra_tabs(self, user):
        """Get extra tabs for the videos page

        Returns:
            list of (name, title) tuples.  name is used for the tab id, title
            is a human friendly title.  For each tab name you should create a
            video-<name>.html and video-<name>-tab.html templates.  If you
            need to pass variables to those templates, create a
            setup_tab_<name> method that inputs the same args as the methods
            from VideoPageContext and returns a dict of variables for the
            template.
        """
        return []

    def get_add_language_mode(self, user):
        """Control the add new language section of the video page

        Args:
            user (User): user viewing the page

        Returns:
            - None/False: Don't display anything
            - "<standard>": Use the standard behavior -- a link that opens
              the create subtitles dialog.
            - any other string: Render this in the section.  You probably want
              to send the string through mark_safe() to avoid escaping HTML
              tags.
        """
        return "<standard>"

    def get_editor_notes(self, user, language_code):
        """Get notes to display in the editor

        Returns:
            :class:`EditorNotes` object
        """
        return EditorNotes(self.video, language_code)

    def lookup_action(self, user, language_code, action_name):
        for action in self.get_actions(user, language_code):
            if action.name == action_name:
                return action
        raise LookupError("No action: %s" % action_name)

    def perform_action(self, user, language_code, action_name):
        """Perform an action on a subtitle set

        This method is used to perform an action by itself, without new
        subtitles being added.
        """
        action = self.lookup_action(user, language_code, action_name)
        subtitle_language = self.video.subtitle_language(language_code)
        subtitle_language.freeze()
        action.validate(user, self.video, subtitle_language, None)
        action.update_language(user, self.video, subtitle_language, None)
        action.perform(user, self.video, subtitle_language, None)
        subtitle_language.thaw()

    def user_can_view_private_subtitles(self, user, language_code):
        """Check if a user can view private subtitles

        Private subtitles are subtitles with visibility or visibility_override
        set to "private".  A typical use is to limit viewing of the subtitles
        to members of a team.

        Returns:
            True/False
        """
        raise NotImplementedError()

    def user_can_delete_subtitles(self, user, language_code):
        """Check if a user can delete a language

        Returns:
            True/False
        """
        raise NotImplementedError()

    def delete_subtitles_bullets(self):
        """Bullet points for the delete subtitles dialog

        returns: list of text strings
        """
        return NotImplementedError()

    def user_can_view_video(self, user):
        """Check if a user can view the video

        Returns:
            True/False
        """
        raise NotImplementedError()

    def user_can_set_video_duration(self, user):
        """Check if a user can set duration of a video

        Returns:
            True/False
        """
        return not user.is_anonymous()

    def user_can_edit_video(self, user):
        """Check if a user can edit the video

        Returns:
            True/False
        """
        raise NotImplementedError()

    def user_can_edit_subtitles(self, user, language_code):
        """Check if a user can edit subtitles

        Returns:
            True/False
        """
        raise NotImplementedError()

    # Right now these are both tied to the edit permissions, but we might
    # change that at some point
    def user_can_view_notes(self, user, language_code):
        """Check if a user can view editor notes."""
        return self.user_can_edit_subtitles(user, language_code)

    def user_can_post_notes(self, user, language_code):
        """Check if a user can post editor notes."""
        return self.user_can_edit_subtitles(user, language_code)

    def editor_data(self, user, language_code):
        """Get data to pass to the editor for this workflow."""
        data = {
            'work_mode': self.get_work_mode(user, language_code).editor_data(),
            'actions': [action.editor_data() for action in
                        self.get_actions(user, language_code)],
        }
        editor_notes = self.get_editor_notes(user, language_code)
        if editor_notes:
            data.update({
                'notesHeading': editor_notes.heading,
                'notes': editor_notes.note_editor_data(),
            })
        else:
            data['notesEnabled'] = False
        return data

    def editor_video_urls(self, language_code):
        """Get video URLs to send to the editor."""
        video_urls = list(self.video.get_video_urls())
        video_urls.sort(key=lambda vurl: vurl.primary, reverse=True)
        if video_urls and video_urls[0].is_html5():
            # If the primary video URL is HTML5, then only send html5 video
            # URLs (see #2089)
            video_urls = [vurl for vurl in video_urls if vurl.is_html5()]
        return [v.get_video_type().player_url() for v in video_urls]

class VideoWorkflow(object):
    """
    VideoWorkflow subclasses work with LanguageWorkflow subclasses to control
    the overall workflow for editing and publishing subtitles.  Workflows
    control the work modes, actions, permissions, etc. for subtitle sets.
    """
    def __init__(self, video):
        self.video = video
        self.language_workflow_cache = {}

    def user_can_view_video(self, user):
        """Check if a user can view the video

        Returns:
            True/False
        """
        raise NotImplementedError()

    def user_can_set_video_duration(self, user):
        """Check if a user can set duration of a video

        Returns:
            True/False
        """
        return not user.is_anonymous()

    def user_can_edit_video(self, user):
        """Check if a user can view the video

        Returns:
            True/False
        """
        raise NotImplementedError()

    def user_can_create_new_subtitles(self, user):
        """Check if a user can add a new SubtitleLanguage to the video

        Returns:
            True/False
        """
        raise NotImplementedError()

    def get_add_language_mode(self, user):
        """Control the add new language section of the video page

        Args:
            user (User): user viewing the page

        Returns:
            Value that specifies how the section should appear

            - None/False: Don't display anything
            - "<standard>": Use the standard behavior a link that
              opens the create subtitles dialog.
            - any other string: Render this in the section.  You probably
              want to send the string through mark_safe() to avoid escaping
              HTML tags.
        """
        return "<standard>"

    def extra_tabs(self, user):
        """Get extra tabs for the videos page

        Returns:
            list of (name, title) tuples.  Name is used for the tab id, title
            is a human friendly title.

            For each tab name you should create a video-<name>.html and
            video-<name>-tab.html templates.  If you need to pass variables to
            those templates, create a setup_tab_<name> method that inputs the
            same args as the methods from VideoPageContext and returns a dict
            of variables for the template.
        """
        return []

    def get_language_workflow(self, language_code):
        """
        Get the LanguageWorkflow object to use for a language.  This method
        first calls get_language_workflow().  If that method returns
        an object then we use that.  Otherwise, we use the return value of
        get_default_language_workflow()

        Why the complexity?  To allow components to override the workflow for
        only 1 specific language.  For example: professional service requests.
        If a team orders subtitles for a language, then we want to use the
        pro-request workflow for that language, but use the default workflow
        for all other languages.
        """
        try:
            return self.language_workflow_cache[language_code]
        except KeyError:
            workflow = get_language_workflow(self.video, language_code)
            if workflow is None:
                workflow = self.get_default_language_workflow(language_code)
            self.language_workflow_cache[language_code] = workflow
            return workflow

    def get_default_language_workflow(self, language_code):
        """Get the default LanguageWorkflow for this VideoWorkflow.

        This will be used unless some other component overrides it with
        :func:`get_language_workflow`

        """
        raise NotImplementedError()

    # The following methods are from LanguageWorkflow, but we wrap them here
    # to allow VideoWorkflow to have the same signature as Workflow.

    def get_work_mode(self, user, language_code):
        return self.get_language_workflow(language_code).get_work_mode(user)

    def get_actions(self, user, language_code):
        return self.get_language_workflow(language_code).get_actions(user)

    def action_for_add_subtitles(self, user, language_code, complete):
        return (self.get_language_workflow(language_code)
                .action_for_add_subtitles(user, complete))

    def get_editor_notes(self, user, language_code):
        return self.get_language_workflow(language_code).get_editor_notes(user)

    def lookup_action(self, user, language_code, action_name):
        return (self.get_language_workflow(language_code)
                .lookup_action(user, action_name))

    def perform_action(self, user, language_code, action_name):
        return (self.get_language_workflow(language_code)
                .perform_action(user, action_name))

    def user_can_view_private_subtitles(self, user, language_code):
        return (self.get_language_workflow(language_code)
                .user_can_view_private_subtitles(user))

    def user_can_delete_subtitles(self, user, language_code):
        return (self.get_language_workflow(language_code)
                .user_can_delete_subtitles(user))

    def delete_subtitles_bullets(self, language_code):
        return (self.get_language_workflow(language_code)
                .delete_subtitles_bullets())

    def user_can_edit_subtitles(self, user, language_code):
        return (self.get_language_workflow(language_code)
                .user_can_edit_subtitles(user))

    def user_can_view_notes(self, user, language_code):
        """Check if a user can view editor notes."""
        return (self.get_language_workflow(language_code)
                .user_can_view_notes(user))

    def user_can_post_notes(self, user, language_code):
        """Check if a user can post editor notes."""
        return (self.get_language_workflow(language_code)
                .user_can_post_notes(user))

    def editor_data(self, user, language_code):
        return self.get_language_workflow(language_code).editor_data(user)

    def editor_video_urls(self, language_code):
        return self.get_language_workflow(language_code).editor_video_urls()

    def action_requires_subtitle_language_tip(self, user, language_code, action_name):
        action = self.lookup_action(user, language_code, action_name)
        return action.requires_subtitle_language_tip

class LanguageWorkflow(object):
    def __init__(self, video, language_code):
        self.video = video
        self.language_code = language_code

    def get_work_mode(self, user):
        """Get the work mode to use for an editing session

        Args:
            user (User): user who is editing

        Returns:
            :class:`WorkMode` object to use
        """
        raise NotImplementedError()

    def get_actions(self, user):
        """Get available actions for a user

        Args:
            user (User): user who is editing

        Returns:
            list of :class:`Action` objects that are available to the user.
        """
        raise NotImplementedError()

    def action_for_add_subtitles(self, user, complete):
        """Get an action to use for add_subtitles()

        This is used when pipeline.add_subtitles() is called, but not passed
        an action.  This happens for a couple reasons:

        - User saves a draft (in which case complete will be None)
        - User is adding subtitles via the API (complete can be True, False,
          or None)

        Subclasses can override this method if they want to use different
        actions to handle this case.

        Args:
            user (User): user adding subtitles
            complete (bool or None): complete arg from add_subtitles()

        Returns:
            Action object or None.
        """
        if complete is None:
            return None
        elif complete:
            return APIComplete()
        else:
            return Unpublish()

    def get_editor_notes(self, user):
        """Get notes to display in the editor

        Returns:
            :class:`EditorNotes` object
        """
        return EditorNotes(self.video, self.language_code)

    def lookup_action(self, user, action_name):
        for action in self.get_actions(user):
            if action.name == action_name:
                return action
        raise LookupError("No action: %s" % action_name)

    def perform_action(self, user, action_name):
        """Perform an action on a subtitle set

        This method is used to perform an action by itself, without new
        subtitles being added.
        """
        action = self.lookup_action(user, action_name)
        subtitle_language = self.video.subtitle_language(self.language_code)
        subtitle_language.freeze()
        action.validate(user, self.video, subtitle_language, None)
        action.update_language(user, self.video, subtitle_language, None)
        action.perform(user, self.video, subtitle_language, None)
        subtitle_language.thaw()

    def user_can_view_private_subtitles(self, user):
        """Check if a user can view private subtitles

        Private subtitles are subtitles with visibility or visibility_override
        set to "private".  A typical use is to limit viewing of the subtitles
        to members of a team.

        Returns:
            True/False
        """
        raise NotImplementedError()

    def user_can_delete_subtitles(self, user, language_code):
        """Check if a user can delete a language

        Returns:
            True/False
        """
        raise NotImplementedError()

    def user_can_edit_subtitles(self, user):
        """Check if a user can edit subtitles

        Returns:
            True/False
        """
        raise NotImplementedError()

    def user_can_view_notes(self, user):
        """Check if a user can view the editor notes."""
        return self.user_can_edit_subtitles(user)

    def user_can_post_notes(self, user):
        """Check if a user can post editor notes."""
        return self.user_can_edit_subtitles(user)

    def editor_data(self, user):
        """Get data to pass to the editor for this workflow."""
        data = {
            'work_mode': self.get_work_mode(user).editor_data(),
            'actions': [action.editor_data() for action in
                        self.get_actions(user)],
        }
        editor_notes = self.get_editor_notes(user)
        if editor_notes:
            data.update({
                'notesHeading': editor_notes.heading,
                'notes': editor_notes.note_editor_data(),
            })
        else:
            data['notesEnabled'] = False
        return data

    def editor_video_urls(self):
        """Get video URLs to send to the editor."""
        video_urls = list(self.video.get_video_urls())
        video_urls.sort(key=lambda vurl: vurl.primary, reverse=True)
        if video_urls and video_urls[0].is_html5():
            # If the primary video URL is HTML5, then only send html5 video
            # URLs (see #2089)
            video_urls = [vurl for vurl in video_urls if vurl.is_html5()]
        return [v.get_video_type().player_url() for v in video_urls]

@behavior
def get_workflow(video):
    """Get the workflow to use for a video.

    By default this method returns the workflow for public, non-team videos.
    Other apps can override it to customize the behavior.
    """

    return DefaultVideoWorkflow(video)

@behavior
def get_language_workflow(video, language_code):
    """Override the default LanguageWorkflow for a subtitle set

    Normally this method returns None, which means use the default for the
    VideoWorkflow.  Other apps can override this and control the workflow for
    specific video languages.
    """
    return None

class WorkMode(object):
    """
    Work modes are used to change the workflow section of the editor and
    affect the overall feel of the editing session.  Currently we only have 2
    work modes:

    * .. autoclass:: NormalWorkMode
    * .. autoclass:: ReviewWorkMode
    """

    def editor_data(self):
        """Get data to send to the editor for this work mode."""
        raise NotImplementedError()

class NormalWorkMode(object):
    """The usual work mode with typing/syncing/review steps."""

    def editor_data(self):
        return {
            'type': 'normal',
        }

class ReviewWorkMode(object):
    """Review someone else's work (for example a review/approve task)

    Args:
        heading (str): heading to display in the workflow area
    """

    def __init__(self, heading, help_text=None):
        self.heading = heading
        self.help_text = help_text

    def editor_data(self):
        return {
            'type': 'review',
            'heading': self.heading,
            'helpText': self.help_text,
        }

class Action(object):
    """Base class for actions

    Other components can define new actions by subclassing Action, setting the
    class attributes, and optionally implementing perform().

    Attributes:

        name: Machine-friendly name

        label: human-friendly label.  Strings should be run through ugettext_lazy()
        in_progress_text: text to display in the editor while this action is
            being performed.  Strings should be run through ugettext_lazy()

        visual_class: visual class to render the action with.  This controls
            things like the icon we use in our editor button.  Must be one of
            the `CLASS_` constants

        complete: how to handle subtitles_complete. There are 3 options:

            - True -- this action sets subtitles_complete
            - False -- this action unsets subtitles_complete
            - None (default) - this action doesn't change subtitles_complete

        subtitle_visibility: Visibility value for newly created
        SubtitleVersions ("public" or "private")

        CLASS_ENDORSE: visual class constant for endorse/approve buttons
        CLASS_SEND_BACK: visual class constant for reject/send-back buttons
    """

    name = NotImplemented 
    label = NotImplemented
    in_progress_text = NotImplemented
    visual_class = None
    complete = None
    requires_translated_metadata_if_enabled = False
    CLASS_ENDORSE = 'endorse'
    CLASS_SEND_BACK = 'send-back'
    subtitle_visibility = 'public'
    requires_subtitle_language_tip = True

    def require_synced_subtitles(self):
        """Should we require that all subtitles have timings?

        The default implementation uses the complete attribute
        """
        return bool(self.complete)

    def validate(self, user, video, subtitle_language, saved_version):
        """Check if we can perform this action.

        Args:
            user (User): User performing the action
            video (Video): Video being changed
            subtitle_language (SubtitleLanguage): SubtitleLanguage being
                changed
            saved_version (SubtitleVersion or None): new version that was
                created for subtitle changes that happened alongside this
                action.  Will be None if no changes were made.

        Raises:
            ActionError -- this action can't be performed
        """
        if self.require_synced_subtitles():
            if saved_version:
                version = saved_version
            else:
                version = subtitle_language.get_tip()
            if (version is None or not version.has_subtitles
                or not version.is_synced()):
                raise ActionError('Subtitles not complete')

    def perform(self, user, video, subtitle_language, saved_version):
        """Perform this action

        Args:
            user (User): User performing the action
            video (Video): Video being changed
            subtitle_language (SubtitleLanguage): SubtitleLanguage being
                changed
            saved_version (SubtitleVersion or None): new version that was
                created for subtitle changes that happened alongside this
                action.  Will be None if no changes were made.
        """
        pass

    def update_language(self, user, video, subtitle_language, saved_version):
        """Update the subtitle language after adding subtitles

        Args:
            user (User): User performing the action
            video (Video): Video being changed
            subtitle_language (SubtitleLanguage): SubtitleLanguage being
                changed
            saved_version (SubtitleVersion or None): new version that was
                created for subtitle changes that happened alongside this
                action.  Will be None if no changes were made.
        """
        if self.complete is not None:
            if self.complete:
                subtitle_language.mark_complete()
            else:
                subtitle_language.mark_incomplete()

    def editor_data(self):
        """Get a dict of data to pass to the editor for this action."""
        return {
            'name': self.name,
            'label': unicode(self.label),
            'in_progress_text': unicode(self.in_progress_text),
            'class': self.visual_class,
            'requireSyncedSubtitles': self.require_synced_subtitles(),
            'requires_translated_metadata_if_enabled': self.requires_translated_metadata_if_enabled,
        }

class Publish(Action):
    """Publish action

    Publish sets the subtitles_complete flag to True
    """
    name = 'publish'
    label = ugettext_lazy('Publish')
    in_progress_text = ugettext_lazy('Saving')
    visual_class = 'endorse'
    complete = True
    requires_translated_metadata_if_enabled = True

    def perform(self, user, video, subtitle_language, saved_version):
        tip = subtitle_language.get_tip()
        if not tip.is_public():
            tip.publish()
        signals.subtitles_published.send(subtitle_language,
                                         version=saved_version)

class Unpublish(Action):
    """Unpublish action

    Unpublish sets the subtitles_complete flag to False
    """
    name = 'unpublish'
    label = ugettext_lazy('Unpublish')
    in_progress_text = ugettext_lazy('Saving')
    visual_class = 'send-back'
    complete = False
    requires_translated_metadata_if_enabled = False

class SaveDraft(Action):
    name = 'save-draft'
    label = ugettext_lazy('Save Draft')
    in_progress_text = ugettext_lazy('Saving')
    complete = None
    requires_translated_metadata_if_enabled = False

class APIComplete(Action):
    """Action that handles complete=True from the API

    We have some strange rules here to maintain API compatibility:
        - If the subtitle set is synced or there are no subtitles, then we set
          subtitles_complete=True
        - If not, we set to to False
    """
    name = 'api-complete'
    label = ugettext_lazy('API Complete')
    in_progress_text = ugettext_lazy('Saving')
    visual_class = 'endorse'
    complete = None
    requires_translated_metadata_if_enabled = False

    def update_language(self, user, video, subtitle_language, saved_version):
        if saved_version.is_synced():
            subtitle_language.mark_complete()
        else:
            subtitle_language.mark_incomplete()

    def perform(self, user, video, subtitle_language, saved_version):
        if subtitle_language.subtitles_complete:
            signals.subtitles_published.send(subtitle_language,
                                             version=saved_version)

class EditorNotes(object):
    """Manage notes for the subtitle editor.

    EditorNotes handles fetching notes for the editor and posting new ones.

    Attributes:
        heading: heading for the editor section
        notes: list of SubtitleNotes for the editor (or any model that
            inherits from SubtitleNoteBase)

    .. automethod:: post
    """

    def __init__(self, video, language_code):
        self.video = video
        self.language_code = language_code
        self.heading = _('Notes')
        self.notes = self.fetch_notes()

    def fetch_notes(self):
        return list(SubtitleNote.objects
                    .filter(video=self.video,
                            language_code=self.language_code)
                    .order_by('created')
                    .select_related('user'))

    def post(self, user, body):
        """Add a new note.

        Args:
            user (CustomUser): user adding the note
            body (unicode): note text
        """
        return SubtitleNote.objects.create(video=self.video,
                                           language_code=self.language_code,
                                           user=user, body=body)

    def format_created(self, created, now):
        if created > now - timedelta(hours=12):
            format_str = '{d:%l}:{d.minute:02} {d:%p}'
        elif created > now - timedelta(days=6):
            format_str = '{d:%a}, {d:%l}:{d.minute:02} {d:%p}'
        else:
            format_str = ('{d:%b} {d.day} {d.year}, '
                          '{d:%l}:{d.minute:02} {d:%p}')
        return format_str.format(d=created)

    def note_editor_data(self):
        now = datetime.now()
        return [
            dict(user=note.get_username(),
                 created=self.format_created(note.created, now),
                 body=note.body)
            for note in self.notes
        ]

# This is deperated just like Workflow, but it needs to stay since other
# components are still using it as a base class.
class DefaultWorkflow(Workflow):
    def get_work_mode(self, user, language_code):
        return NormalWorkMode()

    def get_actions(self, user, language_code):
        return [SaveDraft(), Publish()]

    def user_can_view_private_subtitles(self, user, language_code):
        return user.is_staff

    def user_can_view_video(self, user):
        return True

    def user_can_edit_video(self, user):
        return True

    def user_can_edit_subtitles(self, user, language_code):
        return True

    def delete_subtitles_bullets(self, language_code):
        return [
            _(u'All subtitles will be deleted'),
            _('This language will no longer be usable for translations'),
        ]

class DefaultVideoWorkflow(VideoWorkflow):
    def user_can_view_video(self, user):
        return True

    def user_can_edit_video(self, user):
        return True

    def user_can_create_new_subtitles(self, user):
        return True

    def get_default_language_workflow(self, language_code):
        return DefaultLanguageWorkflow(self.video, language_code)

class DefaultLanguageWorkflow(LanguageWorkflow):
    def get_work_mode(self, user):
        return NormalWorkMode()

    def get_actions(self, user):
        return [SaveDraft(), Publish()]

    def user_can_view_private_subtitles(self, user):
        return user.is_staff

    def user_can_delete_subtitles(self, user):
        return user.is_superuser

    def delete_subtitles_bullets(self):
        return [
            _(u'All subtitles will be deleted'),
            _('This language will no longer be usable for translations'),
        ]

    def user_can_edit_subtitles(self, user):
        return True
