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
teams.experience -- Track user experience on teams.

This module handles things like tracking how many subtitles were completed by
a member.
"""

from django.core.cache import cache
from django.db.models import Count
from django.db.models.signals import post_save
from django.dispatch import receiver

from caching import get_or_calc_many
from teams.models import TeamMember, TeamSubtitlesCompleted

def subtitles_completed_cache_key(member):
    if isinstance(member, TeamMember):
        member = member.id
    return 'team-subtitles-completed-{}'.format(member)

def get_subtitles_completed(member_list):
    """
    Get the number of subtitles completed for a list of members

    returns:
       List of subtitles completed counts, corresponding to the member_list
    """
    keys = [ subtitles_completed_cache_key(m) for m in member_list ]
    member_map = dict(zip(keys, member_list))

    def calc_subtitles_completed(keys):
        member_ids = [member_map[k].id for k in keys]
        qs = (
            TeamSubtitlesCompleted.objects.filter(member_id__in=member_ids)
            .values('member_id').annotate(count=Count('id')))
        count_map = {
            r['member_id']: r['count'] for r in qs
        }
        return [count_map.get(m_id, 0) for m_id in member_ids]

    return get_or_calc_many(keys, calc_subtitles_completed)

@receiver(post_save, sender=TeamSubtitlesCompleted)
def clear_subtitles_completed_cache(sender, instance, **kwargs):
    cache.delete(subtitles_completed_cache_key(instance.member_id))
