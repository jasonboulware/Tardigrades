# Amara, universalsubtitles.org
#
# Copyright (C) 2017 Participatory Culture Foundation
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

# Copied and modified from http://djangosnippets.org/snippets/2413/

import re
from django.template import Library, Node, TemplateSyntaxError

register = Library()

@register.tag
def query_string(parser, token):
    """
    Template tag for getting and modifying query strings.

    Syntax:
        {% query_string  [modifier]* [as <var_name>] %}

        modifier is <name><op><value> where op in {=, +, -}

    Parameters:
      * modifiers may be repeated and have two forms:
          * var=value: set the var param to "value"
          * -var: Remove the var param
      * as <var name>: bind result to context variable instead of injecting in 
        output (same as in url tag).

    Examples (supposing the current query string is ?foo=bar)

    1.  {% query_string %}

        Result: "?foo=bar"

    2.  {% query_string foo2=bar2 %}

        Result: "?foo=bar&foo2=bar2"

    3.  {% query_string foo=bar2 %}

        Result: "?foo=bar2"

    3.  {% query_string -foo foo2=bar2 %}

        Result: "?foo2=bar2"
    """
    # matches 'tagname1+val1' or 'tagname1=val1' but not 'anyoldvalue'
    set_re = re.compile(r"^([\w-]+)=([\w-]+)$")
    remove_re = re.compile(r"^-([\w-]+)$")
    bits = token.split_contents()
    changes = []
    asvar = None
    bits = bits[1:]
    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]
    for bit in bits:
        match = set_re.match(bit)
        if match:
            name, value = match.groups()
        else:
            match = remove_re.match(bit)
            name = match.group(1)
            value = None
            if not match:
                raise TemplateSyntaxError("Malformed arguments to query_string tag")
        changes.append((name, value))
    return QueryStringNode(changes, asvar)

class QueryStringNode(Node):
    def __init__(self, changes, asvar):
        self.changes = changes
        self.asvar = asvar

    def render(self, context):
        request = context['request']
        if not self.changes:
            if request.META['QUERY_STRING']:
                return '?' + request.META['QUERY_STRING']
            else:
                return ''
        qdict = request.GET.copy()
        for key, value in self.changes:
            if value is None:
                if key in qdict:
                    del qdict[key]
            else:
                qdict[key] = value
        qstring = qdict.urlencode()
        if qstring:
            qstring = '?' + qstring
        if self.asvar:
            context[self.asvar] = qstring
            return ''
        else:
            return qstring
