# -*- coding: utf-8 -*-
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


from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.urls import reverse
from subtitles.models import (get_lineage, SubtitleLanguage,
                                   SubtitleVersion)


class SubtitleVersionInline(admin.TabularInline):

    def has_delete_permission(self, request, obj=None):
        # subtitle versions should be immutable, don't allow deletion
        return False

    model = SubtitleVersion
    fields = ['version_number']
    max_num = 0

class SubtitleLanguageAdmin(admin.ModelAdmin):
    list_display = ['video_title', 'language_code', 'version_count', 'tip',
                    'is_forked']
    list_filter = ['created', 'language_code']

    inlines = [SubtitleVersionInline]
    search_fields = ['video__title', 'video__video_id', 'language_code']
    raw_id_fields = ['video']

    def video_title(self, sl):
        return sl.video.title_display()
    video_title.short_description = 'video'

    def version_count(self, sl):
        return sl.subtitleversion_set.full().count()
    version_count.short_description = 'number of versions'

    def tip(self, sl):
        ver = sl.get_tip(full=True)
        return ver.version_number if ver else None
    tip.short_description = 'tip version'

class SubtitleVersionChangeList(ChangeList):
    def get_queryset(self, request):
        qs = super(SubtitleVersionChangeList, self).get_queryset(request)
        # for some reason using select_related makes MySQL choose an
        # absolutely insane way to perform the query.  Use prefetch_related()
        # instead to work around this.
        return qs.prefetch_related('video', 'subtitle_language')

class SubtitleVersionAdmin(admin.ModelAdmin):
    list_per_page = 20
    list_display = ['video_title', 'id', 'language', 'version_num',
                    'visibility', 'visibility_override',
                    'subtitle_count', 'created']
    list_select_related = False
    raw_id_fields = ['video', 'subtitle_language', 'parents', 'author']
    list_filter = ['created', 'visibility', 'visibility_override',
                   'language_code']
    list_editable = ['visibility', 'visibility_override']
    search_fields = ['video__video_id', 'video__title', 'title',
                     'language_code', 'description', 'note']

    # Unfortunately Django uses .all() on related managers instead of
    # .get_queryset().  We've disabled .all() on SubtitleVersion managers so we
    # can't let Django do this.  This means we can't edit parents in the admin,
    # but you should never be doing that anyway.
    exclude = ['parents', 'serialized_subtitles']
    readonly_fields = ['parent_versions']

    # don't allow deletion
    actions = []

    def get_changelist(self, request, **kwargs):
        return SubtitleVersionChangeList

    def has_delete_permission(self, request, obj=None):
        # subtitle versions should be immutable, don't allow deletion
        return False

    def version_num(self, sv):
        return '#' + str(sv.version_number)
    version_num.short_description = 'version #'

    def video_title(self, sv):
        return sv.video.title
    video_title.short_description = 'video'

    def language(self, sv):
        return sv.subtitle_language.get_language_code_display()

    def parent_versions(self, sv):
        links = []
        for parent in sv.parents.full():
            href = reverse('admin:subtitles_subtitleversion_change',
                           args=(parent.pk,))
            links.append('<a href="%s">%s</a>' % (href, parent))
        return ', '.join(links)
    parent_versions.allow_tags = True

    # Hack to generate lineages properly when modifying versions in the admin
    # interface.  Maybe we should just disallow this entirely once the version
    # models are hooked up everywhere else?
    def response_change(self, request, obj):
        response = super(SubtitleVersionAdmin, self).response_change(request, obj)
        obj.lineage = get_lineage(obj.parents.full())
        obj.save()
        return response

    def response_add(self, request, obj, *args, **kwargs):
        response = super(SubtitleVersionAdmin, self).response_add(request, obj)
        obj.lineage = get_lineage(obj.parents.full())
        obj.save()
        return response


# -----------------------------------------------------------------------------
admin.site.register(SubtitleLanguage, SubtitleLanguageAdmin)
admin.site.register(SubtitleVersion, SubtitleVersionAdmin)
