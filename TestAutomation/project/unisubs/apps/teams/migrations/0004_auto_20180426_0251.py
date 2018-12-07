# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0003_auto_20180418_0950'),
    ]

    operations = [
        migrations.AlterField(
            model_name='setting',
            name='key',
            field=models.PositiveIntegerField(choices=[(100, b'messages_invite'), (101, b'messages_manager'), (102, b'messages_admin'), (103, b'messages_application'), (104, b'messages_joins'), (105, b'messages_joins_localized'), (200, b'guidelines_subtitle'), (201, b'guidelines_translate'), (202, b'guidelines_review'), (300, b'block_invitation_sent_message'), (301, b'block_application_sent_message'), (302, b'block_application_denided_message'), (303, b'block_team_member_new_message'), (304, b'block_team_member_leave_message'), (305, b'block_task_assigned_message'), (306, b'block_reviewed_and_published_message'), (307, b'block_reviewed_and_pending_approval_message'), (308, b'block_reviewed_and_sent_back_message'), (309, b'block_approved_message'), (310, b'block_new_video_message'), (311, b'block_new_collab_assignments_message'), (312, b'block_collab_auto_unassignments_message'), (313, b'block_collab_deadlines_passed_message'), (401, b'pagetext_welcome_heading'), (402, b'pagetext_warning_tasks'), (501, b'enable_require_translated_metadata')]),
            preserve_default=True,
        ),
    ]
