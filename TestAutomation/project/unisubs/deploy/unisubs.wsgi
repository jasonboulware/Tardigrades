from uwsgidecorators import timer
import django.core.handlers.wsgi
import logging
import os
import startup
import sys
import uwsgi

DEFAULT_LANGUAGE = 'en'

sys.stdout = sys.stderr

startup.startup()

from django.conf import settings

PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
application = django.core.handlers.wsgi.WSGIHandler()

handler = django.core.handlers.wsgi.WSGIHandler()

disabled_file_path = os.path.join(PROJECT_ROOT, 'disabled')

# instrumenting for tracelytics
try:
    import oboeware.djangoware
    from oboeware import OboeMiddleware
    handler = OboeMiddleware(application, {'oboe.tracing_mode': 'always'}, layer="wsgi")
except ImportError:
    # production, dev and local installs shouldn have that
    pass

if settings.DEBUG:
    from django.utils import autoreload

    @timer(3)
    def change_code_gracefull_reload(sig):
        if autoreload.code_changed():
            uwsgi.reload()

metrics_logger = logging.getLogger('metrics')
@timer(30)
def log_metrics(sig):
    keys = [
        'core.avg_response_time',
        'core.busy_workers',
        'core.idle_workers',
        'core.total_rss',
    ]
    msg_parts = []
    metrics = {}
    for key in keys:
        short_key = key.split('.')[-1]
        value = uwsgi.metric_get(key)
        msg_parts.append('{}={}'.format(short_key, value))
        metrics[short_key] = value
    metrics_logger.info(' '.join(msg_parts), extra={ 'metrics': metrics, })

def application(environ, start_response):
    if os.path.exists(disabled_file_path):
        start_response('503 Service Unavailable', [('Content-type', 'text/html; charset=utf-8')])
        
        langs = environ.get('HTTP_ACCEPT_LANGUAGE', 'en').split(',')
        langs.append(DEFAULT_LANGUAGE)

        for lang in langs:
            lang = lang.split(';')[0].split('-')[0].lower()
            off_tpl_path = rel('unisubs', 'templates', 'off_template', '%s.html' % lang)
            if os.path.exists(off_tpl_path):
                break

        return open(off_tpl_path).read()        
    else:    
        return handler(environ, start_response)
