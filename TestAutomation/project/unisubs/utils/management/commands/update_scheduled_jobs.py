import importlib
import logging
import os

from django.core.management.base import BaseCommand
from django.conf import settings
import django_rq

from utils import dates

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update the RQ Schedule'
    args = '<queue>'

    def handle(self, *args, **options):
        scheduler = django_rq.get_scheduler('default', interval=5)
        print 'updating scheduled jobs'
        now = dates.utcnow()
        self.current_jobs = []
        self.cancel_old_periodic_jobs(scheduler)

        for job_info in settings.REPEATING_JOBS:
            self.schedule_job(now, scheduler, job_info)

    def cancel_old_periodic_jobs(self, scheduler):
        for job in list(scheduler.get_jobs()):
            if 'cron_string' in job.meta or 'interval' in job.meta:
                self.check_existing_job(scheduler, job)

    def check_existing_job(self, scheduler, job):
        for job_info in settings.REPEATING_JOBS:
            if self.job_matches(job_info, job):
                print 'keeping: ', job
                self.current_jobs.append(job_info)
                return
        print 'cancelling: ', job
        scheduler.cancel(job)

    def schedule_job(self, now, scheduler, job_info):
        try:
            job_name = job_info['job']
        except KeyError:
            raise ValueError('"job" key required: {}'.format(job_info))

        for current_job_info in self.current_jobs:
            if current_job_info == job_info:
                return
        print 'scheduling: ', job_info

        if 'crontab' in job_info:
            if 'period' in job_info:
                raise ValueError(
                    'Both crontab and period specified for {}'.format(job_name))
            scheduler.cron(
                self.cron_string(**job_info['crontab']),
                self.get_job_func(job_name))
        elif 'period' in job_info:
            scheduler.schedule(
                now,
                self.get_job_func(job_name),
                interval=job_info['period'].total_seconds())
        else:
            raise ValueError(
                'Neither crontab nor period specified for {}'.format(job_name))

    def cron_string(self, minute='*', hour='*', day='*', month='*', day_of_week='*'):
        return '{} {} {} {} {}'.format(minute, hour, day, month, day_of_week)

    def get_job_func(self, job_name):
        module_name, _, variable_name = job_name.rpartition('.')
        mod = importlib.import_module(module_name)
        return getattr(mod, variable_name)

    def job_matches(self, job_info, job):
        if job.func != self.get_job_func(job_info['job']):
            return False

        if 'cron_string' in job.meta:
            return self.cron_string(**job_info['crontab']) == job.meta['cron_string']
        elif 'interval' in job.meta:
            return job.meta['interval'] == job_info['period'].total_seconds()
        else:
            raise ValueError("job meta doesn't have cron_string or "
                             "period: {}".format(job))
