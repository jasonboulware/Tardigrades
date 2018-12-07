# Amara, universalsubtitles.org
#
# Copyright (C) 2018 Participatory Culture Foundation
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


"""
utils.privatestorage

Manages a Django Storage that we use to store private files.  On production,
these get stored on a private S3 server.  When a user is authorized to view
the file, we redirect them a presigned S3 URL that expires after a short time.
"""

import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from storages.backends.s3boto3 import S3Boto3Storage

PRIVATE_STORAGE_BUCKET = getattr(
    settings, 'PRIVATE_STORAGE_BUCKET', None)
PRIVATE_STORAGE_PREFIX = getattr(
    settings, 'PRIVATE_STORAGE_PREFIX', None)

if PRIVATE_STORAGE_BUCKET:
    if PRIVATE_STORAGE_PREFIX:
        location = '{}/'.format(PRIVATE_STORAGE_PREFIX)
    else:
        location = ''
    storage = S3Boto3Storage(
        bucket_name=PRIVATE_STORAGE_BUCKET, location=location,
        default_acl=None)
else:
    storage = FileSystemStorage(
        location=os.path.join(settings.MEDIA_ROOT, 'private'),
        base_url='http://{}/user-data/private/'.format(settings.HOSTNAME))

