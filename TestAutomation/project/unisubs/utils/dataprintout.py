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

"""dataprintout -- serialize object data into strings

This module contains the DataPrinter object which serialies a dict of data for
debugging purposes.  The serialized data looks something like YAML.
DataPrinter allows to specify maximum length in several ways to make the
printout a) more readable and b) not take up too much space

DataPrinter is used for printing local vars and GET/POST data to our logs.  It
assumes that the dict keys are basically identifiers.  Chars like newlines
will mess up the formatting.

DataPrinter enforces several size limits.
 - Limit on the total size
 - Limit on the size of a single item in the dict (this may by a list/dict
     that contains other objects)
 - Limit on the size of a single repr (the string we use to represent a
     single python object)

Note that size limits should be considered soft limits.  We may overflow them
by a few bytes to include the "..." chars.
"""

# Couple exceptions used for flow control
class SizeOverflow(StandardError):
    pass
class ItemSizeOverflow(StandardError):
    pass

class PrintoutBuffer(object):
    """Handle a string buffer for DataPrinter.

    PrintoutBuffer implements a simple string accumulator with several size
    limitations
    """

    def __init__(self, max_size, max_item_size, max_repr_size):
        self.max_size = max_size
        self.max_item_size = max_item_size
        self.max_repr_size = max_repr_size
        self.current_item_size = 0
        self.current_size = 0
        self.parts = []

    def get_string(self):
        return ''.join(self.parts)

    def start_new_item(self):
        self.current_item_size = 0

    def constrain_text(self, text, max_size):
        """Constrain a text string to a maximum size

        Returns a tuple with the new text and if it was truncated
        """
        if len(text) > max_size:
            if max_size < 3:
                # no room for anything, overflow max_size just a bit in this
                # case
                return '...', True
            return text[:max_size-3] + '...', True
        else:
            return text, False

    def append_raw(self, text):
        self.parts.append(text)
        self.current_size += len(text)
        self.current_item_size += len(text)

    def append_text(self, text):
        text, item_size_overflow = self.constrain_text(
            text, self.max_item_size - self.current_item_size)
        text, size_overflow = self.constrain_text(
            text, self.max_size - self.current_size)
        self.append_raw(text)
        if size_overflow:
            raise SizeOverflow()
        if item_size_overflow:
            raise ItemSizeOverflow()

    def append_repr(self, value):
        if isinstance(value, basestring):
            text = repr(value)
        elif isinstance(value, (int, long, float)):
            text = repr(value)
        else:
            # Don't actually call repr on objects, it's hard to control how
            # long the output is.  Also, it's not really useful for a lot of
            # objects like django's HttpRequest.
            text = '<{}: {}>'.format(type(value).__name__, id(value))
        text, _ = self.constrain_text(text, self.max_repr_size)
        self.append_text(text)

    def append_name(self, name):
        text, _ = self.constrain_text(name, self.max_repr_size)
        self.append_text(text)

class DataPrinter(object):
    """Print data to a string

    This method formats data somewhat like YAML, but a bit more loose.  Also
    it has several size restrictions.
    """
    def __init__(self, max_size, max_item_size, max_repr_size):
        self.max_size = max_size
        self.max_item_size = max_item_size
        self.max_repr_size = max_repr_size

    def printout(self, data):
        """Printout a dict of data to a string """
        buf = PrintoutBuffer(self.max_size, self.max_item_size,
                             self.max_repr_size)
        try:
            for name, value in data.items():
                try:
                    buf.append_name(name)
                    buf.append_text(': ')
                    self.format_value(buf, value)
                except ItemSizeOverflow:
                    pass
                buf.append_raw('\n')
                buf.start_new_item()
        except SizeOverflow:
            pass
        return buf.get_string()

    def format_value(self, buf, value):
        if isinstance(value, dict):
            value_repr = self.format_dict(buf, value)
        elif isinstance(value, list):
            value_repr = self.format_list(buf, value)
        else:
            buf.append_repr(value)

    def format_dict(self, buf, d):
        buf.append_text('{')
        for i, (key, value) in enumerate(d.items()):
            if i > 0:
                buf.append_text(', ')
            buf.append_repr(key)
            buf.append_text(': ')
            self.format_value(buf, value)
        buf.append_text('}')

    def format_list(self, buf, l):
        buf.append_text('[')
        for i, value in enumerate(l):
            if i > 0:
                buf.append_text(', ')
            self.format_value(buf, value)
        buf.append_text(']')
