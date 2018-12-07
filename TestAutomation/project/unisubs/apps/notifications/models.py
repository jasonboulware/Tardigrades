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

import json

from django.db import models, transaction, IntegrityError
from django.db.models import Max
from django.utils.translation import ugettext_lazy as _, ugettext

from utils import dates
from teams.models import Team

class TeamNotificationSettings(models.Model):
    team = models.OneToOneField(Team)
    extra_teams = models.ManyToManyField(Team,
                                         related_name="team_settings_extra",
                                         verbose_name=_('Extra teams to notify'))
    type = models.CharField(max_length=30)
    url = models.URLField(max_length=512)
    auth_username = models.CharField(max_length=128, blank=True)
    auth_password = models.CharField(max_length=128, blank=True)
    header1 = models.CharField(max_length=256, blank=True)
    header2 = models.CharField(max_length=256, blank=True)
    header3 = models.CharField(max_length=256, blank=True)

    class Meta:
        verbose_name_plural = 'Team notification settings'

    @classmethod
    def lookup(cls, team):
        try:
            return TeamNotificationSettings.objects.get(team=team)
        except TeamNotificationSettings.DoesNotExist:
            team_settings = TeamNotificationSettings.objects.filter(extra_teams=team)
            if team_settings.exists():
                return team_settings[0]
            return None

    def get_headers(self):
        headers = {}
        for i in xrange(1, 4):
            header = getattr(self, 'header{}'.format(i))
            if header:
                key, value = header.split(':', 1)
                headers[key.strip()] = value.strip()
        return headers

class TeamNotification(models.Model):
    """Records a sent notication."""
    team = models.ForeignKey(Team)
    number = models.IntegerField() # per-team, auto-increment
    data = models.CharField(max_length=5120)
    url = models.URLField(max_length=512)
    timestamp = models.DateTimeField()
    response_status = models.IntegerField(null=True, blank=True)
    error_message = models.CharField(max_length=256, null=True, blank=True)

    @classmethod
    def create_new(cls, team, url, data):
        data = data.copy()
        if isinstance(team, Team):
            obj = cls(team=team, url=url, timestamp=dates.now())
        else:
            obj = cls(team_id=team, url=url, timestamp=dates.now())
        obj.set_number()
        # There is a potential race condition here where another thread also
        # creates a TeamNotification and takes our number.  If that happens,
        # then try with the next number.
        for i in range(10):
            try:
                with transaction.atomic():
                    data['number'] = obj.number
                    obj.data = json.dumps(data)
                    obj.save()
                    return obj
            except IntegrityError:
                obj.number = obj.number + 1
        raise IntegrityError("Couldn't find unused number")

    def set_number(self):
        self.number = TeamNotification.next_number_for_team(self.team)

    def is_in_progress(self):
        return self.response_status is None and self.error_message is None

    @classmethod
    def next_number_for_team(cls, team):
        qs = (cls.objects
              .filter(team=team)
              .aggregate(max_number=Max('number')))
        max_number = qs['max_number']
        return max_number + 1 if max_number is not None else 1

    class Meta:
        unique_together = [
            ('team', 'number'),
        ]
