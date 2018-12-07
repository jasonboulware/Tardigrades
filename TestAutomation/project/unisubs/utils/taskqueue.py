"""
utils.taskqueue -- Code to handle tasks

This module wraps the django_rq API.  We use this rather than django_rq
directly to simplify the process of switching to another task framework.
"""

from datetime import timedelta

from django.conf import settings

import rq
import django_rq

def job(func=None, queue='default', timeout=None):
    """
    Decorator to allow a function to be run as a job in the worker process

    This works like the celery @task decorator, and the rq @job decorator.
    """
    def wrapper(func):
        def delay(*args, **kwargs):
            if settings.RUN_JOBS_EAGERLY:
                return func(*args, **kwargs)
            rq_job = django_rq.get_queue(queue).enqueue(
                func, timeout=timeout, args=args, kwargs=kwargs)
            return Job(rq_job)

        def enqueue_in(timeout, *args, **kwargs):
            if settings.RUN_JOBS_EAGERLY:
                return func(*args, **kwargs)
            scheduler = django_rq.get_scheduler(queue)
            rq_job = scheduler.enqueue_in(timedelta(seconds=timeout), func, *args,
                                 **kwargs)
            return Job(rq_job)
        func.delay = delay
        func.enqueue_in = enqueue_in
        return func

    if func is None:
        return wrapper
    else:
        return wrapper(func)

class Job(object):
    """
    Encapsulates a job in the task queue
    """

    def __init__(self, rq_job):
        self.rq_job = rq_job
        self.id = rq_job.id

    @classmethod
    def fetch(cls, id, queue='default'):
        rq_job = django_rq.get_queue(queue).fetch_job(id)
        return cls(rq_job)

    @classmethod
    def get_current(cls):
        return cls(rq.get_current_job())

    def get_meta(self):
        return self.rq_job.meta

    def update_meta(self, metadata):
        self.rq_job.meta.update(metadata)
        self.rq_job.save_meta()

__all__ = [
    'job', 'Job'
]
