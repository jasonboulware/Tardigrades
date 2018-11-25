import json

from django.core.management.base import BaseCommand
from django.db import transaction

from activity.models import (ActivityRecord, ActivityMigrationProgress,
                             URLEdit, VideoDeletion, MemberJoined)
from teams.permissions_const import *
from videos.models import Action

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('-B', '--batch_size', dest='batch_size', default=200)

    def handle(self, *args, **options):
        self.batch_size = options['batch_size']
        progress = self.get_progress()
        while True:
            with transaction.atomic():
                last_migrated_id = self.process_rows(progress.last_migrated_id)
                if last_migrated_id is None:
                    return
                progress.last_migrated_id = last_migrated_id
                progress.save()
                print 'migrated to: {}'.format(last_migrated_id)

    def get_progress(self):
        try:
            return ActivityMigrationProgress.objects.get()
        except ActivityMigrationProgress.DoesNotExist:
            return ActivityMigrationProgress.objects.create(last_migrated_id=-1)

    def process_rows(self, last_migrated_id):
        qs = (Action.objects
              .filter(id__gt=last_migrated_id)
              .order_by('id')
              .select_related('video', 'user'))
        last_action_id = None
        for action in qs[:self.batch_size]:
            self.migrate_action(action)
            last_action_id = action.id
        return last_action_id

    def migrate_action(self, action):
        record = ActivityRecord(
            type=action.action_type,
            user=action.user,
            video=action.video,
            team_id=action.team_id,
            created=action.created)
        if action.new_language:
            record.language_code = action.new_language.language_code
        if action.video:
            record.video_language_code = action.video.primary_audio_language_code
            team_video = action.video.get_team_video()
            if team_video:
                assert (record.team_id is None or
                        record.team_id == team_video.team_id)
                record.team_id = team_video.team_id

        if action.action_type == Action.COMMENT:
            record.related_obj_id = action.comment_id
        elif action.action_type == Action.DELETE_VIDEO:
            deletion = VideoDeletion.objects.create(
                title=action.new_video_title)
            record.related_obj_id = deletion.id
        elif action.action_type == Action.MEMBER_JOINED:
            try:
                record.related_obj_id = MemberJoined.role_to_code[
                    action.member.role]
            except:
                print 'error parsing member role: {}'.format(action.member)
                record.related_obj_id = MemberJoined.role_to_code[
                    ROLE_CONTRIBUTOR]
        elif action.action_type == Action.EDIT_URL:
            try:
                data = json.loads(action.new_video_title)
            except:
                print 'error parsing new_video_title for EDIT_URL: {}'.format(
                    action.new_video_title)
                data = {}
            url_edit = URLEdit.objects.create(old_url=data.get('old_url', ''),
                                              new_url=data.get('new_url', ''))
            record.related_obj_id = url_edit.id
        elif action.action_type == Action.DELETE_URL:
            url_edit = URLEdit.objects.create(old_url=action.new_video_title)
            record.related_obj_id = url_edit.id
        record.save()
