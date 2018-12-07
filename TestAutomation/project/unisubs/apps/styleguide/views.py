# Amara, universalsubtitles.org
#
# Copyright (C) 2016 Participatory Culture Foundation
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
import json

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

from styleguide import forms
from styleguide.styleguide import StyleGuide
from ui.ajax import AJAXResponseRenderer
from utils.pagination import AmaraPaginatorFuture

# add your form class here if you need to test form processing on a styleguide
# section
forms_by_section = {
    'multi-field': forms.MultiFieldForm,
    'image-upload': forms.ImageUpload,
    'switches': forms.SwitchForm,
    'dynamic-help-text': forms.DynamicHelpTextForm,
    'content-header': forms.ContentHeader,
    'filter-box': forms.FilterBox,
    'split-button': forms.SplitButton,
}

extra_context_func_map = {}
def extra_context_func(section_id):
    def wrapper(func):
        extra_context_func_map[section_id] = func
        return func
    return wrapper

_cached_styleguide = None
def get_styleguide():
    global _cached_styleguide
    if _cached_styleguide is None or settings.DEBUG:
        _cached_styleguide = StyleGuide()
    return _cached_styleguide

def home(request):
    return render(request, 'styleguide/home.html', {
        'section': {
            'title': _('Styleguide home'),
        },
        'styleguide': get_styleguide(),
        'active_section': None,
    })

def section(request, section_id):
    styleguide = get_styleguide()
    section = styleguide.sections[section_id]

    context = {
        'styleguide': styleguide,
        'section': section,
        'active_section': section_id,
        'form': get_form_for_section(request, section_id),
    }

    extra_context = extra_context_func_map.get(section_id)
    if extra_context:
        context.update(extra_context(request, section_id))

    return render(request, section.template_name, context)

def get_form_for_section(request, section_id):
    FormClass = forms_by_section.get(section_id)
    if FormClass:
        if request.method == 'POST':
            form = FormClass(request, data=request.POST, files=request.FILES)
            if form.is_valid():
                form.save()
            return form
        else:
            return FormClass(request)
    else:
        return None

def member_search(request):
    data = {
        'results': [
            {
                "id": 1,
                "avatar": '<span class="avatar avatar-teal"></span>',
                "text": "Jianfeng Fan",
            },
            {
                "id": 2,
                "avatar": '<span class="avatar avatar-default"></span>',
                "text": "Anton Hikov",
            },
            {
                "id": 3,
                "avatar": '<span class="avatar avatar-plum"></span>',
                "text": "Joost van der Borg",
            },
            {
                "id": 4,
                "avatar": '<span class="avatar avatar-inverse"></span>',
                "text": "Hacker mc Hack Hack <script>alert('hi');</script>"
            }
        ]
    }
    return HttpResponse(json.dumps(data), 'application/json')

filter_box_colors = [ 'plum', 'amaranth', 'lime']
filter_box_shapes = [ 'Square', 'Triangle', 'Circle']

def calc_filter_box_colors(request):
    if 'color' in request.GET:
        return [
            color for color in filter_box_colors
            if color in request.GET.getlist('color')
        ]
    else:
        return filter_box_colors

def calc_filter_box_shapes(request):
    if 'shape' in request.GET:
        return [
            shape for shape in filter_box_shapes
            if any(shape.lower().startswith(q.lower()) for q in
                   request.GET.getlist('shape'))
        ]
    else:
        return filter_box_shapes

def filter_box(request):
    styleguide = get_styleguide()
    section = styleguide.sections['filter-box']

    context = {
        'styleguide': styleguide,
        'section': section,
        'active_section': 'filter-box',
        'form': get_form_for_section(request, 'filter-box'),
        'colors': calc_filter_box_colors(request),
        'shapes': calc_filter_box_shapes(request),
    }
    if request.is_ajax():
        response_renderer = AJAXResponseRenderer(request)
        response_renderer.replace(
            '#content-list', 'styleguide/filter-box-content.html', context
        )
        return response_renderer.render()
    else:
        return render(request, 'styleguide/filter-box.html', context)

@extra_context_func('content-footer')
def content_footer_extra(request, section_id):
    paginator = AmaraPaginatorFuture(range(100), 20)
    page = paginator.get_page(request)
    return {
        'paginator': paginator,
        'page': page
    }
