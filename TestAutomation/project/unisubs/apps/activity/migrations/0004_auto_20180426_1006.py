# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import codefield


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0003_auto_20180418_0950'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activityrecord',
            name='type',
            field=codefield.CodeField(choices=[(b'video-added', 'Video Added'), (b'video-title-changed', 'Video title changed'), (b'comment-added', 'Comment added'), (b'version-added', 'Version added'), (b'video-url-added', 'Video URL added'), (b'translation-added', 'Translation URL added'), (b'subtitle-request-created', 'Subtitle request created'), (b'version-approved', 'Version approved'), (b'member-joined', 'Member Joined'), (b'version-rejected', 'Version Rejected'), (b'member-left', 'Member Left'), (b'version-reviewed', 'Version Reviewed'), (b'version-accepted', 'Version Accepted'), (b'version-declined', 'Version Declined'), (b'video-deleted', 'Video deleted'), (b'video-url-edited', 'Video URL edited'), (b'video-url-deleted', 'Video URL deleted'), (b'video-moved-to-team', 'Video moved to team'), (b'video-moved-from-team', 'Video moved from team'), (b'team-settings-changed', 'Team settings changed'), (b'language-changed', 'Language Changed'), (b'collab-join', 'Collaboration joined'), (b'collab-leave', 'Collaboration left'), (b'collab-assign', 'Collaboration assigned'), (b'collab-reassign', 'Collaboration reassigned'), (b'collab-unassign', 'Collaboration unassigned'), (b'collab-auto-unassigned', 'Collaboration automatically unassigned'), (b'collab-endorse', 'Collaboration endorsed'), (b'collab-send-back', 'Collaboration sent back'), (b'collab-mark-complete', 'Collaboration marked complete'), (b'collab-move-from-team', 'Collaboration moved from team'), (b'collab-move-to-team', 'Collaboration moved to team'), (b'collab-delete', 'Collaboration deleted'), (b'collab-provider-accept', 'Collaboration accepted by provider'), (b'collab-provider-submit', 'Collaboration submitted by provider'), (b'collab-provider-unassign', 'Collaboration unassigned from provider'), (b'collab-set-evaluation-teams', 'Collaboration evaluation teams set'), (b'collab-change-state', 'Collaboration change State'), (b'collab-team-change', 'Collaboration team change'), (b'collab-deadline-passed', 'Collaboration deadline has passed')]),
            preserve_default=True,
        ),
    ]
