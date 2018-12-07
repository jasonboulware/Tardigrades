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
from django import template
from django.core.paginator import Paginator, EmptyPage
register = template.Library()

def paginate(items, per_page, page):
    if page != 'last':
        page = int(page) if page else 1

    paginator = Paginator(items, per_page, allow_empty_first_page=True)
    if page == 'last':
        page = paginator.num_pages

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page_obj = paginator.page(paginator.num_pages)

    return page_obj.object_list, {
        'paginator': paginator,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    }

def paginator(context, adjacent_pages=3):
    """
    To be used in conjunction with the object_list generic view.

    Adds pagination context variables for use in displaying first, adjacent and
    last page links in addition to those created by the object_list generic
    view.

    """
    paginator = context['paginator']
    page_obj = context['page_obj']

    startPage = max(page_obj.number - adjacent_pages, 1)
    if startPage <= 3: startPage = 1
    endPage = page_obj.number + adjacent_pages + 1
    if endPage >= paginator.num_pages - 1: endPage = paginator.num_pages + 1
    page_numbers = [n for n in range(startPage, endPage) \
            if n > 0 and n <= paginator.num_pages]
    
    getvars = ''
    if 'request' in context:
        GET_vars = context['request'].GET.copy()
        if 'revisions_per_page' in GET_vars:
            del GET_vars['revisions_per_page']
        if 'page' in GET_vars:
            del GET_vars['page']
        if len(GET_vars.keys()) > 0:
            getvars = "&%s" % GET_vars.urlencode()

    return {
        'page_obj': page_obj,
        'paginator': paginator,
        'hits': paginator.count,
        'results_per_page': paginator.per_page,
        'page': page_obj.number,
        'pages': paginator.num_pages,
        'page_numbers': page_numbers,
        'next': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'show_first': 1 not in page_numbers,
        'getvars': getvars,
        'show_last': paginator.num_pages not in page_numbers,
    }

register.inclusion_tag('_paginator.html', takes_context=True)(paginator)

@register.tag
def ordered_column(parser, token):
    try:
        tokens = token.split_contents()
        field_name = tokens[1]
        title = tokens[2]
        get_params = tokens[3:]
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly two arguments" % token.contents.split()[0]
    return OrderedColumnNode(parser.compile_filter(field_name), parser.compile_filter(title), get_params)
    
class OrderedColumnNode(template.Node):
    
    def __init__(self, field_name, title, get_params):
        self.field_name = field_name
        self.title = title
        self.page = template.Variable('page')
        self.order_type = template.Variable('order_type')
        self.ordering = template.Variable('ordering')
        self.get_params = get_params
        
    def render(self, context):
        if context.has_key(self.page.var):
            page = self.page.resolve(context)
        else:
            page = None
        
        if context.has_key(self.ordering.var):
            ordering = self.ordering.resolve(context)
        else:
            ordering = None
                    
        if context.has_key(self.order_type.var):
            order_type = self.order_type.resolve(context)
        else:
            order_type = None
        
        extra_params = [] 
        anchor = ''
        for item in self.get_params:
            if item.startswith('#'):
                anchor = item
            else:
                items = item.split('=')
                variable = template.Variable(items[1])
                extra_params.append('&%s=%s' % (items[0], variable.resolve(context)))
        
        extra_params = ''.join(extra_params)+anchor
        field_name = self.field_name.resolve(context, True)
        
        ot = (ordering == field_name and order_type == 'desc') and 'asc' or 'desc'
        cls = (ordering == field_name) and order_type or ''
        if page:
            link = '?o=%s&ot=%s&page=%s%s' % (field_name, ot, page, extra_params)
        else:
            link = '?o=%s&ot=%s%s' % (field_name, ot, extra_params)
        return '<a href="%s" class="%s">%s</a>' % (link, cls, self.title.resolve(context, True))

@register.simple_tag   
def progress_color(value):
    if value <= 50:
        return 'red'
    if value >= 90:
        return 'green'
    return 'yellow'
