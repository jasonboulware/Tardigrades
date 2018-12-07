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

import re
import textwrap

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from lxml import html

from auth.models import CustomUser as User
from messages.models import Message, SYSTEM_NOTIFICATION
from utils.enum import Enum
from utils.taskqueue import job

Notifications = Enum('Notifications', [
    ('ROLE_CHANGED', _('Role changed')),
    ('TEAM_INVITATION', _('Team invitation')),
])

def notify_users(notification, user_list, subject, template_name,
                 context, send_email=None):
    """
    Send notification messages to a list of users

    Arguments:
        notification: member from the Notifications enum
        user_list: list/iterable of CustomUser objects to notify
        template_name: template to render the notification with
        context: context dict to use for the 2 templates
        send_email: Should we send an email alongside the message?  Use
            True/False to force an email to be sent or not sent.  None, the
            default means use the notify_by_email flag from CustomUser.

    Note that we use the same template to render both the HTML and plaintext
    version of the message.  Here's the system we use to make this work.

        - Templates are written in simplified HTML
        - The only block-level tags supported are <p>, <ul>, and <li>
        - The only inline tags supported are <a>, <em>, and <strong>
        - For <a> tags make sure to use the {% universal_url %} tag or filter
    """
    message = _render_message_template(subject, template_name, context, 'text')
    html_message = _render_message_template(subject, template_name, context,
                                            'html')
    do_notify_users.delay(notification, [u.id for u in user_list], subject,
                          message, html_message, send_email)

@job
def do_notify_users(notification, user_ids, subject, message, html_message,
                    send_email):
    user_list = User.objects.filter(id__in=user_ids)
    for user in user_list:
        if not user.is_active:
            continue
        if should_send_email(user, send_email):
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                      [user.email], html_message=html_message)
        if user.notify_by_message:
            Message.objects.create(user=user, subject=subject,
                                   message_type=SYSTEM_NOTIFICATION,
                                   content=html_message, html_formatted=True)

def should_send_email(user, send_email):
    """
    Logic to decide if we should send an email to the user for notify_users()
    """
    return (user.email and
            (send_email == True or
             send_email is None and user.notify_by_email))

def _render_message_template(subject, template_name, context, mode):
    source = render_to_string(template_name, context)
    if mode == 'html':
        return format_html_message(subject, source)
    else:
        return format_text_message(subject, source)

def format_html_message(subject, source):
    return render_to_string('messages/html-email.html', {
        'subject': subject,
        'body': source,
    })

def format_text_message(subject, source):
    return TextEmailRenderer(source).text

class TextEmailRenderer(object):
    """
    Handles converting the HTML emails to plaintext
    """

    def __init__(self, source):
        self.parts = []
        self.process_source(source)
        self.text = ''.join(self.parts)

    def process_source(self, source):
        tree = html.fragment_fromstring(source, create_parent=True)

        self.check_no_text(tree.text)
        for i, elt in enumerate(tree):
            if i > 0:
                self.parts.append('\n') # extra newline to separate paragraphs
            self.process_blocklevel(elt)

    def process_blocklevel(self, elt):
        self.check_no_text(elt.tail)

        if elt.tag == 'p':
            self.process_inline_text(elt)
            self.parts.append('\n')
        elif elt.tag == 'ul':
            self.process_list(elt)

    def process_inline_text(self, elt):
        inline_parts = []
        if elt.text:
            inline_parts.append(elt.text)
        for child in elt:
            if child.tag == 'a':
                inline_parts.append(self.format_link(child))
            else:
                raise ValueError(
                    "Don't know how to process inline {} "
                    "elements for the plaintext email".format(child.tag))
            if child.tail:
                inline_parts.append(child.tail)
        self.parts.append(textwrap.fill(
            ''.join(inline_parts), 70))

    def process_list(self, elt):
        for child in elt:
            if child.tag == 'li':
                self.parts.append('  - ')
                self.process_inline_text(child)
                self.parts.append('\n')
            else:
                raise ValueError(
                    "Invalid ul child: {}".format(elt.tag))

    def format_link(self, elt):
        return '{} ({})'.format(elt.text, elt.get('href'))

    def check_no_text(self, text_or_tail):
        if text_or_tail and not text_or_tail.isspace():
            raise ValueError(
                "Can't process text outside <p> tags for the "
                "plaintext email: {}".format(text_or_tail))
