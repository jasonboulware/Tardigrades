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

from __future__ import absolute_import

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.urls import reverse
from django.utils.translation import to_locale, ugettext as _

from ui import tasks
from ui.ajax import AJAXResponseRenderer
from utils.taskqueue import Job
from utils.text import fmt
from utils.translation import get_language_choices

TASK_UPDATE_INTERVAL = 0.5

def task_progress(request, job_id):
    if not request.is_ajax():
        raise Http404
    job = Job.fetch(job_id, queue='high')
    job_meta = job.get_meta() if job else {}
    status = job_meta.get('form_status')
    response_renderer = AJAXResponseRenderer(request)
    if status == 'PROGRESS':
        progress = float(job_meta['current']) / job_meta['total']
        response_renderer.show_modal_progress(progress, fmt(
            _("Processing: %(current)s / %(total)s"),
            current=job_meta['current'],
            total=job_meta['total']))
        response_renderer.perform_request(TASK_UPDATE_INTERVAL,
                                          "ui:task-progress", job.id)
    elif status == 'SUCCESS':
        response_renderer.show_modal_progress(1.0, _("Complete"))
        add_job_messages(request, job_meta)
        response_renderer.reload_page()
    elif status == 'FAILURE':
        add_job_messages(request, job_meta)
        response_renderer.reload_page()
    else:
        response_renderer.show_modal_progress(0.0, _("Processing"))
        response_renderer.perform_request(TASK_UPDATE_INTERVAL,
                                          "ui:task-progress", job_id)
    return response_renderer.render()

def add_job_messages(request, job_meta):
    for message in job_meta.get('messages', []):
        messages.success(request, message)
    for message in job_meta.get('error_messages', []):
        messages.error(request, message)

def render_management_form_submit(request, form):
    response_renderer = AJAXResponseRenderer(request)
    if form.should_process_in_task():
        job = tasks.process_management_form.delay(
            type(form), form.get_pickle_state())
        response_renderer.show_modal_progress(0.0, _("Processing"))
        response_renderer.perform_request(TASK_UPDATE_INTERVAL,
                                          "ui:task-progress", job.id)
    else:
        response_renderer = AJAXResponseRenderer(request)
        form.submit()
        message = form.message()
        if message:
            messages.success(request, message)
        for error in form.error_messages():
            messages.error(request, error)
        response_renderer.reload_page()
    return response_renderer.render()

def language_select(request):
    url = request.META.get('HTTP_REFERER').split('/')
    template_name = 'future/language_switcher.html'
    response_renderer = AJAXResponseRenderer(request)
    context = {}
    context['languages'] = []
    valid_options = [code for code, label in settings.LANGUAGES]
    for code, name in get_language_choices(flat=True, limit_to=valid_options):
        url[3] = code
        context['languages'] += [('/'.join(url), code, name)]
    response_renderer.show_modal(template_name, context)
    return response_renderer.render()
