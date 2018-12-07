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

from __future__ import absolute_import
from collections import OrderedDict

from django.test import TestCase
from nose.tools import *

from utils import dataprintout

class DataPrintoutTest(TestCase):
    def setUp(self):
        self.printer = dataprintout.DataPrinter(
            max_size=1000, max_item_size=1000, max_repr_size=1000)

    def assert_printout(self, data, correct_response):
        format_result = self.printer.printout(data)
        assert_equal(format_result, correct_response,
                     "format() returned wrong string:\n{}\n{}".format(
                         format_result, correct_response))

    def assert_printout_max_size(self, data, max_size):
        format_result = self.printer.printout(data)
        # allow for slight amount of overflow
        assert_less(len(format_result), max_size + 5)

    def test_format_data(self):
        o = object()
        data = OrderedDict([
            ('foo', 'string'),
            ('bar', u'unicode string'),
            ('baz', 123),
            ('qux', o),
        ])
        self.assert_printout(data, """\
foo: 'string'
bar: u'unicode string'
baz: 123
qux: <object: {}>
""".format(id(o)))

    def test_object_representation(self):
        # for objects we should ignore their repr function and just always
        # print the type and id
        class ObjectWithACrazyRepr(object):
            def __repr__(self):
                return 'Lots of nonsense that should be ignored'
        o = ObjectWithACrazyRepr()
        self.assert_printout({'o': o}, """\
o: <ObjectWithACrazyRepr: {}>
""".format(id(o)))

    def test_nested_data(self):
        data = OrderedDict([
            ('foo', [1, 2, 3]),
            ('bar', OrderedDict([
                ('a', 1),
                ('b', 2),
                ('c', [3, 4, 5]),
            ])),
        ])
        self.assert_printout(data, """\
foo: [1, 2, 3]
bar: {'a': 1, 'b': 2, 'c': [3, 4, 5]}
""")

    def test_unicode_string(self):
        self.assert_printout({'foo': u'a\u1234b'}, """\
foo: u'a\\u1234b'
""")

    def test_long_string(self):
        self.printer.max_repr_size = 7
        self.assert_printout({'foo': "abcdefhijk"}, """\
foo: 'abc...
""")

    def test_long_name(self):
        self.printer.max_repr_size = 7
        self.assert_printout({'abcdefhijk': "foo"}, """\
abcd...: 'foo'
""")

    def test_long_item(self):
        self.printer.max_item_size = 15
        data = {'foo': range(100)}
        self.assert_printout_max_size(data, 15)

    def test_long_total_size(self):
        self.printer.max_size = 100
        data = {'key{}'.format(i): i for i in range(100)}
        self.assert_printout_max_size(data, 100)
