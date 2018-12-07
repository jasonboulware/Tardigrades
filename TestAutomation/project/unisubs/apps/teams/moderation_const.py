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

CAN_MODERATE_VERSION = "can_moderate_version"
CAN_SET_VIDEO_AS_MODERATED = "can_set_video_as_moderated"
CAN_UNSET_VIDEO_AS_MODERATED = "can_unset_video_as_moderated"

UNMODERATED = "not__under_moderation"
WAITING_MODERATION = "waiting_moderation"
APPROVED = "approved"
REJECTED = "rejected"

# for now these status are only used in notification, at
# some point they should be incorporated into the general flow
REVIEWED_AND_PUBLISHED = 'approved_and_published'
REVIEWED_AND_PENDING_APPROVAL = 'reviewed-and-pending-approval'
REVIEWED_AND_SENT_BACK = 'reviewed-and-sent-back'

MODERATION_STATUSES = (
    (UNMODERATED, "not__under_moderation",),
    (WAITING_MODERATION, "waiting_moderation",),
    (APPROVED, "approved"),
    (REJECTED, "rejected"),
)

SUBJECT_EMAIL_VERSION_REJECTED = "Your version for %s was declined"
