# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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

from django import dispatch
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from externalsites.models import account_models
from teams.models import TeamNotificationSetting

signal = dispatch.Signal(providing_args=['stdout'])

class Command(BaseCommand):
    help = u'Setup the domain for the default site.'
    
    def handle(self, *args, **kwargs):
        self.stdout.write("deleting user emails...\n")
        User.objects.all().update(email='')
        self.stdout.write("removing external accounts...\n")
        for AccountModel in account_models:
            AccountModel.objects.all().delete()
        self.stdout.write("removing team notification settings...\n")
        TeamNotificationSetting.objects.all().delete()

        signal.send(self, stdout=self.stdout)

        self.stdout.write("done\n")
