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

from django.core.management.base import BaseCommand, CommandError
from django.db.models.loading import get_model

# Map app names to the fields to work on
APP_MAP = {
    'auth': ['CustomUser.picture',],
    'videos': ['Video.s3_thumbnail',],
    'teams': ['Team.logo', 'Team.square_logo',],
}

class Command(BaseCommand):
    args = '[app]...'
    help = u'Recreate thumbnails'
    CHUNK_SIZE =25 # max number of objects to select at once

    def parse_args(self, args):
        """Parse the arguments given into a list of
        (app_name, model_name, field_name) tuples
        """
        if not args:
            args = APP_MAP.keys()
        rv = []
        for app_name in args:
            for composite_field_name in APP_MAP[app_name]:
                rv.append([app_name] + composite_field_name.split('.'))
        return rv

    def handle(self, *args, **kwargs):
        for app_name, model_name, field_name in self.parse_args(args):
            self.recreate_thumbnails(app_name, model_name, field_name)

    def recreate_thumbnails(self, app_name, model_name, field_name):
        Model = get_model(app_name, model_name)

        last_id = None
        while True:
            qs = Model.objects.exclude(**{field_name:''}).order_by('id')
            if last_id is not None:
                qs = qs.filter(id__gt=last_id)

            found_obj = False
            for obj in qs[:self.CHUNK_SIZE]:
                found_obj = True
                last_id = obj.id
                try:
                    getattr(obj, field_name).recreate_all_thumbnails()
                except Exception, e:
                    self.stdout.write("Error recreating thumbnails for "
                                      "%s: %s\n" % (obj, e))
                else:
                    self.stdout.write("Recreated thumbnails for %s.%s\n" %
                                      (obj, field_name))
            if not found_obj:
                break
