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

import json, datetime

from django.db import models
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.db.models.signals import post_save
from django.urls import reverse
from django.utils.html import escape
from django.db.models import Q
import bleach

from auth.models import CustomUser as User
MESSAGE_MAX_LENGTH = getattr(settings,'MESSAGE_MAX_LENGTH', 1000)

SYSTEM_NOTIFICATION = 'S'
MESSAGE = 'M'
OLD_MESSAGE = 'O'
MESSAGE_TYPES = (SYSTEM_NOTIFICATION, MESSAGE, OLD_MESSAGE)
MESSAGE_TYPE_CHOICES = (
    (SYSTEM_NOTIFICATION, 'System Notification'),
    (MESSAGE, 'Personal Message'),
    (OLD_MESSAGE, 'Old Type Message'),
)

class MessageManager(models.Manager):
    use_for_related_fields = True

    def for_user(self, user, thread_tip_only=False):
        qs = self.get_queryset().filter(user=user, deleted_for_user=False)
        if thread_tip_only:
            qs = qs.filter(has_reply_for_user=False)
        return qs

    def for_author(self, user, thread_tip_only=False):
        qs = self.get_queryset().filter(author=user, deleted_for_author=False)
        if thread_tip_only:
            qs = qs.filter(has_reply_for_author=False)
        return qs

    def for_user_or_author(self, user, thread_tip_only=False):
        qs = self.get_queryset().filter((Q(author=user) & Q(deleted_for_author=False)) | (Q(user=user) & Q(deleted_for_user=False)))
        if thread_tip_only:
            qs = qs.filter(Q(has_reply_for_author=False) | Q(has_reply_for_user=False))
        return qs

    def thread(self, message, user):
        if message.thread:
            thread_id = message.thread
        else:
            thread_id = message.id
        return self.get_queryset().filter(Q(thread=thread_id) | Q(id=thread_id)).filter((Q(author=user) & Q(deleted_for_author=False)) | (Q(user=user) & Q(deleted_for_user=False)))

    def previous_in_thread(self, message, user):
        if message.thread:
            previous_messages = self.thread(message, user)
            if message.created is not None:
                previous_messages = previous_messages.filter(created__lt = message.created)
            previous_messages = previous_messages.order_by('-created')
            if previous_messages.exists():
                return previous_messages[0]
        return None

    def unread(self):
        return self.get_queryset().filter(read=False)

    def bulk_create(self, object_list, **kwargs):
        super(MessageManager, self).bulk_create(object_list, **kwargs)
        for user_id in set(m.user_id for m in object_list):
            User.cache.invalidate_by_pk(user_id)

    def cleanup(self, days, message_type=None):
        messages_to_clean = self.get_queryset().filter(created__lte=datetime.datetime.now() - datetime.timedelta(days=days))
        if message_type:
            messages_to_clean = messages_to_clean.filter(message_type=message_type)
        messages_to_clean.delete()

def validate_message_type(value):
    if value not in MESSAGE_TYPES:
        raise ValidationError('%s is not a valid message type' % value)

class Message(models.Model):
    user = models.ForeignKey(User)
    subject = models.CharField(max_length=100, blank=True)
    content = models.TextField(blank=True, max_length=MESSAGE_MAX_LENGTH)
    html_formatted = models.BooleanField(default=False)
    author = models.ForeignKey(User, blank=True, null=True, related_name='sent_messages')
    read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    deleted_for_user = models.BooleanField(default=False)
    deleted_for_author = models.BooleanField(default=False)

    content_type = models.ForeignKey(ContentType, blank=True, null=True,
            related_name="content_type_set_for_%(class)s")
    object_pk = models.TextField('object ID', blank=True, null=True)
    object = GenericForeignKey(ct_field="content_type", fk_field="object_pk")

    objects = MessageManager()
    thread = models.PositiveIntegerField(blank=True, null=True, db_index=True)
    has_reply_for_author = models.BooleanField(default=False)
    has_reply_for_user = models.BooleanField(default=False)

    message_type = models.CharField(max_length=1,
                                    choices=MESSAGE_TYPE_CHOICES,
                                    validators=[validate_message_type])
    class Meta:
        ordering = ['-id']
        index_together = [
            ('user', 'deleted_for_user', 'has_reply_for_user'),
            ('user', 'deleted_for_author', 'has_reply_for_author'),
            ('user', 'deleted_for_user', 'read', 'id'),
        ]


    def __unicode__(self):
        if self.subject and not u' ' in self.subject:
            return self.subject[:40]+u'...'
        return self.subject or ugettext('[no subject]')

    def get_reply_url(self):
        return '%s?reply=%s' % (reverse('messages:new'), self.pk)

    def delete_for_user(self, user):
        if self.user == user:
            self.deleted_for_user = True
            if self.thread is not None and not self.has_reply_for_user:
                previous_in_thread = Message.objects.previous_in_thread(self, self.user)
                if previous_in_thread is not None:
                    previous_in_thread.has_reply_for_user = False
                    previous_in_thread.save()
            self.save()
        elif self.author == user:
            self.delete_for_author(user)

    def delete_for_author(self, author):
        if self.author == author:
            self.deleted_for_author = True
            if self.thread is not None and not self.has_reply_for_author:
                previous_in_thread = Message.objects.previous_in_thread(self, self.user)
                if previous_in_thread is not None:
                    previous_in_thread.has_reply_for_author = False
                    previous_in_thread.save()
            self.save()

    def json_data(self):
        data = {
            'id': self.pk,
            'author-avatar': self.author and self.author.small_avatar() or '',
            'author-username': self.author and unicode(self.author) or '',
            'author-id': self.author and self.author.pk or '',
            'thread': self.thread or self.id or '',
            'user-avatar': self.user and self.user.small_avatar() or '',
            'user-username': self.user and unicode(self.user) or '',
            'user-id': self.user and self.user.pk or '',
            'message-content': self.get_content(),
            'message-subject': self.subject,
            'message-subject-display': unicode(self),
            'is-read': self.read,
            'can-reply': bool(self.author_id)
        }
        if self.object and hasattr(self.object, 'message_json_data'):
            data = self.object.message_json_data(data, self)
        return json.dumps(data)

    def get_content(self):
        if self.html_formatted:
            return self.content

        content = []

        if self.content:
            if self.message_type == SYSTEM_NOTIFICATION:
                escaped_content = self.content
            else:
                escaped_content = escape(self.content)
            my_content_with_links = bleach.linkify(escaped_content)
            content.append(my_content_with_links.replace('\n', '<br />'))
            content.append('\n')

        if self.object and hasattr(self.object, 'render_message'):
            added_content = self.object.render_message(self)
            content.append(added_content)

        return ''.join(content)

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.subject and not self.content and not self.object:
            raise ValidationError(_(u'You should enter subject or message.'))

    def save(self, *args, **kwargs):
        """
        If the receipient (user) has opted out completly of receiving site
        messages we mark the message as read, but still stored in the database
        """
        if not self.user.notify_by_message:
            self.read = True

        if getattr(settings, "MESSAGES_DISABLED", False):
            return
        self.auto_truncate_subject()
        if self.thread is not None and self.pk is None:
            previous_in_thread = Message.objects.previous_in_thread(self, self.user)
            if previous_in_thread is not None:
                previous_in_thread.has_reply_for_author = True
                previous_in_thread.has_reply_for_user = True
                previous_in_thread.save()
        super(Message, self).save(*args, **kwargs)

    def auto_truncate_subject(self):
         max_length = self._meta.get_field('subject').max_length
         if self.subject and len(self.subject) > max_length:
             self.subject = self.subject[:max_length-3] + '...'

    @classmethod
    def on_delete(cls, sender, instance, **kwargs):
        ct = ContentType.objects.get_for_model(sender)
        cls.objects.filter(content_type__pk=ct.pk, object_pk=instance.pk).delete()

