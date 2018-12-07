from datetime import timedelta
import logging

logger = logging.getLogger('notifications.tasks')

from django.db.models import Q, Max

from notifications.models import TeamNotification
from teams.models import Team
from utils.taskqueue import job
import utils.dates

REMOVE_AFTER = 90
MIN_KEEP = 1000

@job
def prune_notification_history():
    remove_after = utils.dates.now() - timedelta(days=REMOVE_AFTER)
    team_list = Team.objects.all()
    for team in team_list:
        notification_list = TeamNotification.objects.filter(team=team)

        if not len(notification_list) > 0:
            continue

        max_number = notification_list.aggregate(Max('number'))['number__max']
        keep_up_to = max_number - MIN_KEEP

        if not keep_up_to > 0:
            continue

        to_remove = TeamNotification.objects.filter(
                        Q(team=team),                   # part of team
                        Q(number__lte=keep_up_to),      # not in MIN_KEEP highest numbers
                        Q(timestamp__lte=remove_after)  # older than REMOVE_AFTER
                    )

        to_remove.delete()
