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

from django import forms
from django.contrib import admin
from django.contrib import messages as django_messages
from django.contrib.admin.views.main import ChangeList
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from auth.models import CustomUser as User
from messages.forms import TeamAdminPageMessageForm
from teams import tasks
from teams.models import (
    Team, TeamMember, TeamVideo, Workflow, Task, Setting, MembershipNarrowing,
    Project, TeamLanguagePreference, TeamNotificationSetting, BillingReport,
    Partner, Application, ApplicationInvalidException, Invite, BillingRecord,
    LanguageManager, BillToClient, EmailInvite, TeamTag
)
from utils.text import fmt
from videos.models import Video

class ProjectManagerInline(admin.TabularInline):
    model = TeamMember.projects_managed.through
    verbose_name_plural = 'Project Manager For:'

class LanguageManagerInline(admin.TabularInline):
    model = LanguageManager
    verbose_name_plural = 'Language Manager For:'

class TeamAdmin(admin.ModelAdmin):
    search_fields = ('name'),
    list_display = ('name', 'not_deleted', 'membership_policy', 'video_policy',
                    'team_visibility', 'video_visibility',
                    'highlight', 'last_notification_time', 'thumbnail',
                    'partner')
    list_filter = ('highlight', 'team_visibility', 'video_visibility')
    actions = ['delete_selected', 'highlight', 'unhighlight', 'send_message']
    raw_id_fields = ['video', 'users', 'videos', 'applicants']
    exclude = ('users', 'applicants','videos')

    def thumbnail(self, object):
        return '<img src="%s"/>' % object.logo_thumbnail()
    thumbnail.allow_tags = True

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['message_form'] = TeamAdminPageMessageForm()
        return super(TeamAdmin, self).changelist_view(request, extra_context)

    def send_message(self, request, queryset):
        form = TeamAdminPageMessageForm(request.POST)
        if form.is_valid():
            count = form.send_to_teams(request.POST.getlist(u'_selected_action'), request.user)
            msg = fmt(_("%(count)s messages sent"), count=count)
            self.message_user(request, msg)
        else:
            self.message_user(request, _("Fill all fields please."))
    send_message.short_description = _('Send message')

    def not_deleted(self, team):
        return not team.deleted
    not_deleted.boolean = True
    not_deleted.short_description = _('Not deleted')

    def highlight(self, request, queryset):
        queryset.update(highlight=True)
    highlight.short_description = _('Feature teams')

    def unhighlight(self, request, queryset):
        queryset.update(highlight=False)
    unhighlight.short_description = _('Unfeature teams')

    def delete_selected(self, request, queryset):
        queryset.update(deleted=True)

    def get_queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """
        qs = Team.all_objects.all()
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def save_model(self, request, obj, form, change):
        super(TeamAdmin, self).save_model(request, obj, form, change)
        tasks.update_video_public_field.delay(obj.id)

class TeamMemberChangeList(ChangeList):
    # This class is a bit of a hack.
    #
    # We want to fetch the team and user fields for TeamMember without created
    # a bunch of extra queries.  Normally we would use select_related(), but
    # this causes things to run slowly.  So what we really want to use is
    # prefetch_related(), but it has a bug in Django 1.4 that prevents it from
    # working with model inheritance like we use with CustomUser (ticket
    # 19420).
    #
    # To work around all this, we manually do the work that prefetch_related
    # does.

    def get_results(self, request):
        super(TeamMemberChangeList, self).get_results(request)
        self.join_users(self.result_list)
        self.join_teams(self.result_list)

    def join_users(self, results):
        user_ids = [r.user_id for r in results]
        user_qs = User.objects.filter(id__in=user_ids)
        user_map = dict((u.id, u) for u in user_qs)
        for member in results:
            member.user = user_map.get(member.user_id)

    def join_teams(self, results):
        team_ids = [r.team_id for r in results]
        team_qs = Team.objects.filter(id__in=team_ids)
        team_map = dict((u.id, u) for u in team_qs)
        for member in results:
            team = team_map.get(member.team_id)
            if team is not None:
                # Could be None if team marked as deleted
                member.team = team

class TeamMemberAdmin(admin.ModelAdmin):
    search_fields = ('user__username', 'team__name', 'user__first_name', 'user__last_name')
    list_display = ('role', 'team_link', 'user_link', 'created',)
    raw_id_fields = ('user', 'team')
    exclude = ('projects_managed',)
    inlines = [
        ProjectManagerInline,
        LanguageManagerInline,
    ]

    def get_changelist(self, request, **kwargs):
        return TeamMemberChangeList

    def team_link(self, obj):
        url = reverse('admin:teams_team_change', args=[obj.team_id])
        return u'<a href="%s">%s</a>' % (url, obj.team)
    team_link.short_description = _('Team')
    team_link.allow_tags = True

    def user_link(self, obj):
        url = reverse('admin:amara_auth_customuser_change', args=[obj.user_id])
        return u'<a href="%s">%s</a>' % (url, obj.user)
    user_link.short_description = _('User')
    user_link.allow_tags = True

class TeamVideoAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'team_link', 'created')
    raw_id_fields = ['video', 'team', 'added_by', 'project']
    search_fields = ('video__title',)

    def team_link(self, obj):
        url = reverse('admin:teams_team_change', args=[obj.team_id])
        return u'<a href="%s">%s</a>' % (url, obj.team)
    team_link.short_description = _('Team')
    team_link.allow_tags = True

class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'team', 'project', 'team_video', 'created')
    list_filter = ('created', 'modified')
    search_fields = ('team__name', 'project__name', 'team_video__video__title')
    raw_id_fields = ('team', 'team_video', 'project')
    ordering = ('-created',)

class TaskChangeList(ChangeList):
    def get_queryset(self, request):
        # Hijack the query attribute so we can handle it ourselves
        query = self.query
        self.query = None
        qs = super(TaskChangeList, self).get_queryset(request)
        if query:
            qs = qs.filter(team_video__video__in=Video.objects.search(query))
        self.query = query
        return qs

class TaskAdmin(admin.ModelAdmin):
    # We specifically pull old/new subtitle version, assignee, team_video, team,
    # and language out into properties to force extra queries per row.
    #
    # This sounds like a bad idea, but when we allow Django to use the
    # select_related to add the INNER JOIN clauses MySQL decides to do horrible
    # things.
    #
    # It's only a hundred little queries or so, so it's not a super big deal.
    list_display = ('id', 'type', 'team_title', 'team_video_title',
                    'language_title', 'assignee_name', 'is_complete', 'deleted',
                    'old_subtitle_version_str', 'new_subtitle_version_str',)
    list_filter = ('type', 'deleted', 'created', 'modified', 'completed')
    search_fields = ('assignee__username', 'team__name', 'assignee__first_name',
                     'assignee__last_name', 'team_video__video__title')
    raw_id_fields = ('team_video', 'team', 'assignee', 'subtitle_version',
                     'review_base_version', 'new_subtitle_version',
                    'new_review_base_version')

    readonly_fields = ('created', 'modified')
    ordering = ('-id',)
    list_per_page = 20

    def get_changelist(self, request, **kwargs):
        return TaskChangeList

    def old_subtitle_version_str(self, o):
        return unicode(o.subtitle_version) if o.subtitle_version else ''
    old_subtitle_version_str.short_description = 'old subtitle version'

    def new_subtitle_version_str(self, o):
        return unicode(o.new_subtitle_version) if o.new_subtitle_version else ''
    new_subtitle_version_str.short_description = 'new subtitle version'

    def is_complete(self, o):
        return True if o.completed else False
    is_complete.boolean = True

    def assignee_name(self, o):
        return unicode(o.assignee) if o.assignee else ''
    assignee_name.short_description = 'assignee'

    def team_video_title(self, o):
        return unicode(o.team_video) if o.team_video else ''
    team_video_title.short_description = 'team video'

    def team_title(self, o):
        return unicode(o.team) if o.team else ''
    team_title.short_description = 'team'

    def language_title(self, o):
        return unicode(o.language) if o.language else ''
    language_title.short_description = 'language'
    language_title.admin_order_field = 'language__language'

class TeamLanguagePreferenceAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'team', 'language_code', 'preferred',
                    'allow_reads', 'allow_writes')
    list_filter = ('preferred', 'allow_reads', 'allow_writes')
    search_fields = ('team__name',)
    raw_id_fields = ('team',)

class MembershipNarrowingAdmin(admin.ModelAdmin):
    list_display = ('member', 'team', 'project', 'language')
    list_filter = ('created', 'modified')
    raw_id_fields = ('member', 'project', 'added_by')
    ordering = ('-created',)
    search_fields = ('member__team__name', 'member__user__username')

    def team(self, o):
        return o.member.team
    team.admin_order_field = 'member__team'

class SettingAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'team', 'key', 'created', 'modified')
    list_filter = ('key', 'created', 'modified')
    search_fields = ('team__name',)
    raw_id_fields = ('team',)
    ordering = ('-created',)

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'team', 'workflow_enabled')
    list_filter = ('workflow_enabled', 'created', 'modified')
    search_fields = ('team__name', 'name')
    raw_id_fields = ('team',)
    ordering = ('-created',)


class BillingReportAdmin(admin.ModelAdmin):
    def get_teams(self, obj):
        ",".join([x.slug for x in obj.teams.all()])
    list_display = ('get_teams', 'start_date', 'end_date', 'processed')


class InviteAdmin(admin.ModelAdmin):
    list_display = ('user', 'team', 'role', 'approved',)
    raw_id_fields = ('user',)


class ApplicationAdmin(admin.ModelAdmin):
    search_fields = ('user__username', 'team__name', 'user__first_name', 'user__last_name')
    list_display = ('user',  'team_link', 'user_link', 'created', 'status')
    list_filter = ('status', )
    raw_id_fields = ('user', 'team')
    ordering = ('-created',)

    def team_link(self, obj):
        url = reverse('admin:teams_team_change', args=[obj.team_id])
        return u'<a href="%s">%s</a>' % (url, obj.team)
    team_link.short_description = _('Team')
    team_link.allow_tags = True

    def user_link(self, obj):
        url = reverse('admin:amara_auth_customuser_change', args=[obj.user_id])
        return u'<a href="%s">%s</a>' % (url, obj.user)
    user_link.short_description = _('User')
    user_link.allow_tags = True

    def save_model(self, request, obj, form, change):
        try:
            if form.cleaned_data['status'] == Application.STATUS_APPROVED:
                obj.approve()
            elif form.cleaned_data['status'] == Application.STATUS_DENIED:
                obj.deny()
            else:
                obj.save()
        except ApplicationInvalidException:
           django_messages.error(request, 'Not saved! Status already in use %s' )


class BillingRecordAdmin(admin.ModelAdmin):
    list_display = (
        'video',
        'project',
        'new_subtitle_language',
        'minutes',
        'is_original',
        'team',
        'created',
        'source',
        'user',
        'new_subtitle_version'
    )
    list_filter = ('team', 'created', 'source', 'is_original',)
    raw_id_fields = ('user', 'subtitle_language',
                     'new_subtitle_language', 'subtitle_version',
                     'new_subtitle_version', 'video', 'project',
    )

class TeamTagAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("label",)}
    fields = ('label', 'slug')

admin.site.register(TeamMember, TeamMemberAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(TeamVideo, TeamVideoAdmin)
admin.site.register(Workflow, WorkflowAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(TeamLanguagePreference, TeamLanguagePreferenceAdmin)
admin.site.register(MembershipNarrowing, MembershipNarrowingAdmin)
admin.site.register(Setting, SettingAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(TeamNotificationSetting)
admin.site.register(BillingReport, BillingReportAdmin)
admin.site.register(BillToClient)
admin.site.register(Partner)
admin.site.register(Invite, InviteAdmin)
admin.site.register(Application, ApplicationAdmin)
admin.site.register(BillingRecord, BillingRecordAdmin)
admin.site.register(EmailInvite)
admin.site.register(TeamTag, TeamTagAdmin)
