# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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

from datetime import datetime
import inspect
import json
import logging
import traceback

from utils.dataprintout import DataPrinter

EXTRA_FIELDS = ['path', 'status_code', 'method', 'view', 'query', 'post_data',
                'metrics', 'user', 'ip_address',]

data_printer = DataPrinter(
    max_size=500, max_item_size=100, max_repr_size=50)

def record_data(record):
    data = {
        '@version': '1',
        '@timestamp': format_timestamp(record.created),
        'message': record.getMessage(),
        'level': record.levelname,
        'name': record.name,
    }
    if record.exc_info:
        data['exception'] = str(record.exc_info[0])
        data['traceback'] = format_traceback(record.exc_info[2])
    for name in EXTRA_FIELDS:
        if hasattr(record, name):
            data[name] = getattr(record, name)
    return data

def format_timestamp(time):
    tstamp = datetime.utcfromtimestamp(time)
    return (tstamp.strftime("%Y-%m-%dT%H:%M:%S") +
            ".%03d" % (tstamp.microsecond / 1000) + "Z")

def format_traceback(tb):
    try:
        return format_pretty_traceback(tb)
    except:
        pass
    try:
        return ''.join(traceback.format_tb(tb))
    except:
        return 'Error formatting traceback'

def format_pretty_traceback(tb):
    parts = []
    for frame in inspect.getinnerframes(tb, 5):
        line_info = '{} {}:{}\n'.format(frame[3], frame[1], frame[2])
        parts.append(line_info)
        parts.append('-' * (len(line_info)-1))
        parts.append('\n')
        if frame[0].f_locals:
            parts.append(data_printer.printout(frame[0].f_locals))
        leading_space = min([len(l) - len(l.lstrip()) for l in frame[4] if
                             l.lstrip()])
        parts.append('\n')
        for i, line in enumerate(frame[4]):
            if line.lstrip():
                line = line[leading_space:]
            prefix = '* ' if i == frame[5] else '  '
            parts.append(prefix + line)
        parts.append('\n')
    return ''.join(parts)

class JSONHandler(logging.StreamHandler):
    def format(self, record):
        return json.dumps(record_data(record))
