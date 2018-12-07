# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.

from rest_framework import negotiation
from rest_framework.parsers import JSONParser
from rest_framework_yaml.parsers import YAMLParser
from rest_framework_xml.parsers import XMLParser

class AmaraContentNegotiation(negotiation.DefaultContentNegotiation):
    """
    Handle content negotiation

    The main trick here is that we also need to support having a parser format
    listed in the format query param.  This is a relic from the tastypie days.

    Note:
        django-rest-framework has built in support for picking the renderer
        based on the query param so we don't have to handle that.
    """
    def select_parser(self, request, parsers):
        if 'format' in request.query_params:
            return self.select_parser_from_format(request, parsers)
        return super(AmaraContentNegotiation, self).select_parser(request,
                                                                  parsers)

    # map format query param values to (parser class, renderer class) tuples
    _format_to_parser_class = {
        'json': JSONParser,
        'yaml': YAMLParser,
        'xml': XMLParser,
    }

    def select_parser_from_format(self, request, parsers):
        try:
            fmt = request.query_params['format']
            parser_class = self._format_to_parser_class[fmt]
        except KeyError:
            return None
        for parser in parsers:
            if isinstance(parser, parser_class):
                return parser
