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

from django.db import models
from django.template.loader import render_to_string
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from auth.models import CustomUser as User, Awards
from django.conf import settings
from django.db.models.signals import post_save
from django.utils.html import escape, urlize

from localeurl.utils import universal_url

COMMENT_MAX_LENGTH = getattr(settings,'COMMENT_MAX_LENGTH', 3000)


class Comment(models.Model):
    content_type = models.ForeignKey(ContentType,
            related_name="content_type_set_for_%(class)s")
    object_pk = models.TextField('object ID')
    content_object = GenericForeignKey(ct_field="content_type", fk_field="object_pk")
    user = models.ForeignKey(User)
    reply_to = models.ForeignKey('self', blank=True, null=True)
    content = models.TextField('comment', max_length=COMMENT_MAX_LENGTH)
    submit_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-submit_date',)

    def __unicode__(self):
        return "%s: %s..." % (self.user.__unicode__(), self.content[:50])

    def get_content(self):
        content = []
        if self.content:
            content.append(urlize(escape(self.content)).replace('\n', '<br />'))
            content.append('\n')
        return ''.join(content)

    @classmethod
    def get_for_object(self, obj):
        if obj.pk:
            ct = ContentType.objects.get_for_model(obj)
            return self.objects.filter(content_type=ct, object_pk=obj.pk).order_by('submit_date').select_related('user')
        else:
            return self.objects.none()


def comment_post_save_handler(sender, instance, created, **kwargs):
    from messages.tasks import send_video_comment_notification
    send_video_comment_notification.delay(instance.pk)


post_save.connect(Awards.on_comment_save, Comment)
post_save.connect(comment_post_save_handler, Comment,
        dispatch_uid='notifications')
