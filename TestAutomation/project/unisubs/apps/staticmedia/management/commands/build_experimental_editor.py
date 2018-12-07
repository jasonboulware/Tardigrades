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

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import boto3

from staticmedia import bundles

class Command(BaseCommand):
    help = """Upload editor code to s3 as the experimental editor"""

    def handle(self, *args, **options):
        client = boto3.client('s3',
                              aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        self.upload(client, 'editor.js', 'application/javascript')
        self.upload(client, 'editor.css', 'text/css')

    def upload(self, client, bundle_name, mime_type):
        bundle = bundles.get_bundle(bundle_name)
        client.put_object(
            Bucket=settings.STATIC_MEDIA_EXPERIMENTAL_EDITOR_BUCKET,
            Key='experimental/{}/{}'.format(bundle.bundle_type, bundle_name),
            ContentType=bundle.mime_type,
            ACL='private',
            Body=bundle.build_contents())
        print('* {}'.format(bundle_name))
