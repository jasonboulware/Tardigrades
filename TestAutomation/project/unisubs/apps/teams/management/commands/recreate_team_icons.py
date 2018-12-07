# Amara, universalsubtitles.org
#
# Copyright (C) 2016 Participatory Culture Foundation
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

from optparse import make_option
import sys

from django.core.management.base import BaseCommand

from teams.models import Team
import time

class Command(BaseCommand):
    help = "Recreate icons fro all teams"

    def handle(self, *args, **options):
        for team in Team.objects.all():
            print 'Recreating for {}'.format(team)
            if team.square_logo:
                try:
                    team.square_logo.recreate_all_thumbnails()
                except Exception, e:
                    print 'error recreating square logo'
            if team.logo:
                try:
                    team.logo.recreate_all_thumbnails()
                except Exception, e:
                    print 'error recreating logo'
