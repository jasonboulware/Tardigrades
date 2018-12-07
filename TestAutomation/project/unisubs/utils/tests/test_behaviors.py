# -*- coding: utf-8 -*-
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

from django.test import TestCase

from utils.behaviors import behavior, DONT_OVERRIDE

class BehaviorTest(TestCase):
    def test_function_override(self):
        @behavior
        def func():
            return 'foo'
        self.assertEquals(func(), 'foo')

        @func.override
        def override():
            return 'bar'
        self.assertEquals(func(), 'bar')

    def test_dont_override_return(self):
        @behavior
        def func():
            return 'foo'
        @func.override
        def override():
            return DONT_OVERRIDE

    def test_override_the_override(self):
        # test overriding the override function.  The function that overrides
        # the override should be called first
        @behavior
        def func():
            return 'foo'
        @func.override
        def override1():
            return 'bar'
        @override1.override
        def override2():
            return 'baz'

        self.assertEquals(func(), 'baz')

    def test_override_twice(self):
        # test overriding a behavior twice, in this case the 1st override
        # function should be called first
        @behavior
        def func():
            return 'foo'
        @func.override
        def override1():
            return 'bar'
        @func.override
        def override2():
            return 'baz'

        self.assertEquals(func(), 'bar')
