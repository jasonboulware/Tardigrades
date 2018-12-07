# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
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

from functools import update_wrapper
import json
import sys

from django.shortcuts import render
from django.template.context import RequestContext
from django.http import HttpResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings

DEFAULT_PROTOCOL = getattr(settings, "DEFAULT_PROTOCOL", 'https')

try:
    import oboe
except ImportError:
    oboe = None

def render_to(template):
    """
    Decorator for Django views that sends returned dict to render_to_response function
    with given template and RequestContext as context instance.

    If view doesn't return dict then decorator simply returns output.
    Additionally view can return two-tuple, which must contain dict as first
    element and string with template name as second. This string will
    override template name, given as parameter

    Parameters:

     - template: template name to use
    """
    def renderer(func):
        def wrapper(request, *args, **kw):
            output = func(request, *args, **kw)
            if isinstance(output, (list, tuple)):
                return render(request, output[1], output[0])
            elif isinstance(output, dict):
                return render(request, template, output)
            return output
        return update_wrapper(wrapper, func)
    return renderer

def render_to_json(func):
    def wrapper(request, *args, **kwargs):
        result = func(request, *args, **kwargs)

        if isinstance(result, HttpResponse):
            return result

        content = json.dumps(result, cls=DjangoJSONEncoder)
        return HttpResponse(content, content_type="application/json")
    return update_wrapper(wrapper, func)

def send_templated_email(to, subject, body_template, body_dict,
                         from_email=None, ct="html", fail_silently=False,
                         check_user_preference=True):
    """
    Sends an html email with a template name and a rendering context.
    Parameters:
        to: a list of email addresses of User objects
        check_user_preferences: If set to false will send the email regardless
             of the user's notification preferences. This is useful in
             situations where you must send the email, for example on
             password retrivals.
    """
    from auth.models import CustomUser
    from django.contrib.auth.models import User
    to_unchecked = to
    if not isinstance(to_unchecked, list):
        to_unchecked = [to]
    to = []
    # if passed a User, check that he has opted in for email notification
    # unless check_user_preference is False (useful for example for password)
    # retrivals, else users that have opted out of email notifications
    # can never recover their passowrd
    for recipient in to_unchecked:
        if isinstance(recipient, User) or isinstance(recipient, CustomUser):
            if not bool(recipient.email):
                continue
            if check_user_preference is False or  recipient.notify_by_email:
                to.append(recipient.email)
        else:
            to.append(recipient)
    if not from_email: from_email = settings.DEFAULT_FROM_EMAIL

    body_dict['domain'] = settings.HOSTNAME
    body_dict['url_base'] = "%s://%s" % (DEFAULT_PROTOCOL,  settings.HOSTNAME)
    message = render_to_string(body_template, body_dict)
    bcc = settings.EMAIL_BCC_LIST
    email = EmailMessage(subject, message, from_email, to, bcc=bcc)
    email.content_subtype = ct
    if oboe:
        try:
            oboe.Context.log('email', 'info', backtrace=False,**{"template":body_template})
        except Exception, e:
            print >> sys.stderr, "Oboe error: %s" % e

    return email.send(fail_silently)

class CheckResult(object):
    """Result object for a check function

    This object gets returned from one of our typical check methods.  Those
    methods check if a user can perform some action: add subtitles to a video,
    take an assignment, manage a team, etc.  We usually want to return two
    things from those types of methods:

      - If the check was successful or not
      - Why was the check successful or not (e.g. why can't a user do the
        action)

    This class is made to be the return value from those methods.  It can be
    used as a boolean to simply test if the check was true or false.  It also
    has an optional reason attribute that describes the reasoning behind the
    decision.  Typically we set the reason for false values, and leave it
    blank for true values.
    """
    def __init__(self, result, reason=''):
        self.result = result
        self.reason = reason

    def __nonzero__(self):
        return bool(self.result)


def post_or_get_value(request, name, default=None):
    if name in request.POST:
        return request.POST[name]
    elif name in request.GET:
        return request.GET[name]
    else:
        return default
