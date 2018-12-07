# Amara, universalsubtitles.org
#
# Copyright (C) 2017 Participatory Culture Foundation
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

import sys
import time

from django import dispatch
from django.core import management
from django.core.management.base import BaseCommand
from django.db import connection, DatabaseError

from auth.models import CustomUser as User
from videos.models import VideoUrl

# Connect to this if you want to do extra setup to prep the guitests
signal = dispatch.Signal()

class Command(BaseCommand):
    help = "Prepares the GUI tests to be run"

    def handle(self, **options):
        self.setup_database()
        self.create_admin_user()
        signal.send(sender=None)

    def setup_database(self):
        self.wait_for_db()
        management.call_command('migrate')
        management.call_command('flush', interactive=False)

    def wait_for_db(self):
        start_time = time.time()
        while time.time() < start_time + 30:
            try:
                with connection.cursor():
                    return
            except DatabaseError:
                pass

        print("Can't connect to database")
        sys.exit(1)

    def create_admin_user(self):
        User.objects.create_user(username='admin', password='password')
