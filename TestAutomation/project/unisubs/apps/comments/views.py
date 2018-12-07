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

import json

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.template import RequestContext

from forms import CommentForm
from models import Comment

@login_required
def post(request):
    output = dict(success=False)
    form = CommentForm(None, request.POST)
    if form.is_valid():
        form.save(request.user)
        output['success'] = True
    else:
        output['errors'] = form.get_errors()
        
    return HttpResponse(json.dumps(output), "text/javascript")

def update_comments(request):
    last_comment_id = request.POST.get('last_comment_id')
    object_pk = request.POST.get('obj_id')
    ct = request.POST.get('ct')
    if object_pk and ct:
        qs = Comment.objects.filter(content_type__pk=ct, object_pk=object_pk)
        if last_comment_id:
            try:
                last_comment = Comment.objects.get(pk=last_comment_id)
                qs = qs.filter(submit_date__gt=last_comment.submit_date)
            except Comment.DoesNotExist:
                pass        
    else:
        qs = Comment.objects.none()
    response = render(request, 'comments/update_comments.html',{
            'qs': qs
        })
    response['comments-count'] = len(qs)
    return response
