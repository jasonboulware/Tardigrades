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
from django.urls import reverse
from django.forms.models import model_to_dict
from django.utils.translation import ugettext as _

from messages import tasks as notifier
from teams.models import (
    Team, TeamMember, Application, Project
)
from teams.permissions import roles_user_can_assign, save_role
from utils import translation
from utils.rpc import Error, Msg, RpcRouter

class TeamsApiClass(object):
    def create_application(self, team_id, msg, user):
        if not user.is_authenticated():
            return Error(_('You should be authenticated.'))

        try:
            if not team_id:
                raise Team.DoesNotExist
            team = Team.objects.get(pk=team_id)
        except Team.DoesNotExist:
            return Error(_('Team does not exist'))

        try:
            TeamMember.objects.get(team=team, user=user)
            return Error(_(u'You are already a member of this team.'))
        except TeamMember.DoesNotExist:
            pass

        if team.is_open():
            TeamMember(team=team, user=user).save()
            return Msg(_(u'You are now a member of this team.'))
        elif team.is_by_application():

            if msg.strip() == '':
                return Error(_(u'The "About you" field is required in order to apply.'))
            try:
                application = team.applications.get(user=user)
                if application.status == Application.STATUS_PENDING:
                    return Error(_(u'You have already applied to this team.'))
                elif application.status == Application.STATUS_DENIED:
                    return Error(_(u'Your application has been denied.'))
                elif application.status == Application.STATUS_MEMBER_REMOVED:
                    return Error(_(u'You have been removed from this team.'))
                elif application.status == Application.STATUS_MEMBER_LEFT:
                    # the user chose to participate, so we can already approve it
                    application.note = msg
                    application.approve(author=application.user, interface='web UI')
                    return Msg(_(u"Your application has been approved. "
                         u"You are now a member of this team"))
            except Application.DoesNotExist:
                application = Application(team=team, user=user)
            application.note = msg
            application.save(author=user, interface='web UI')
            notifier.application_sent.delay(application.pk)

            return Msg(_(u"Your application has been submitted. "
                         u"You will be notified of the team administrator's response"))
        else:
            return Error(_(u"You can't join this team by application."))

    def promote_user(self, team_id, member_id, role, user):
        try:
            team = Team.objects.for_user(user).get(pk=team_id)
        except Team.DoesNotExist:
            return Error(_(u'Team does not exist.'))

        if not team.is_manager(user):
            return Error(_(u'You are not manager of this team.'))

        if not role in dict(TeamMember.ROLES):
            return Error(_(u'Incorrect team member role.'))

        try:
            tm = TeamMember.objects.get(pk=member_id, team=team)
        except TeamMember.DoesNotExist:
            return Error(_(u'Team member does not exist.'))

        if tm.user == user:
            return Error(_(u'You can\'t promote yourself.'))

        tm.role = role
        tm.save()
        return Msg(_(u'Team member role changed.'))

TeamsApi = TeamsApiClass()


def _project_to_dict(p):
    d  = model_to_dict(p, fields=["name", "slug", "order", "description", "pk",
                                  "workflow_enabled"])
    d.update({
        "pk":p.pk,
        "url": reverse("teams:project_video_list", kwargs={
            "slug":p.team.slug,
            "project_slug": p.slug,
        })
    })
    return d



class TeamsApiV2Class(object):
    def test_api(self, message, user):
        return Msg(u'Received message: "%s" from user "%s"' % (message, unicode(user)))

    def member_role_info(self, team_slug, member_pk, user):
        team = Team.objects.get(slug=team_slug)
        member = team.members.get(pk=member_pk)
        roles =  roles_user_can_assign(team, user, member.user)
        # massage the data format to make it easier to work with
        # over the client side templating
        verbose_roles = [{"val":x[0], "name":x[1]} for x in TeamMember.ROLES if x[0] in roles]
        narrowings = member.narrowings.all()

        current_languages = [n.language for n in narrowings if n.language]
        current_projects = [n.project for n in narrowings if n.project]

        projects = []
        for p in Project.objects.for_team(team):
            data = dict(pk=p.pk, name=p.name)
            if p in current_projects:
                data['selected'] = "selected"
            projects.append(data)

        langs = []
        writeable_languages = team.get_writable_langs()
        for code, name in [l for l in translation.SUPPORTED_LANGUAGE_CHOICES if l[0] in writeable_languages]:
            lang = {
                'selected': True if code in current_languages else False,
                'code': code,
                'name': name,
            }
            langs.append(lang)

        langs.sort(key=lambda l: unicode(l['name']))

        return {
            'current_role': member.role,
            'roles': verbose_roles,
            'languages': langs,
            'projects': projects,
        }

    def save_role(self, team_slug, member_pk, role, projects, languages, user=None):
        team = Team.objects.get(slug=team_slug)
        member = team.members.get(pk=member_pk)

        if role == 'admin':
            languages = None

        projects = map(int, projects or [])
        res = save_role(team, member, role, projects, languages, user)
        if res:
            return { 'success': True }
        else:
            return { 'success': False,
                     'errors': [_('You cannot assign that role to that member.')] }


TeamsApiV2 = TeamsApiV2Class()

rpc_router = RpcRouter('teams:rpc_router', {
    'TeamsApi': TeamsApi,
    'TeamsApiV2': TeamsApiV2,
})
