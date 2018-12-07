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

from django.test import TestCase
from nose.tools import *
import mock

from utils.forms import FormRouter

class FormRouterTestCase(TestCase):
    def setUp(self):
        self.form_classes = {}
        self.forms = {}
        for name in ('form1', 'form2', 'form3'):
            FormClass = mock.Mock()
            form = FormClass.return_value = mock.Mock()
            self.form_classes[name] = FormClass
            self.forms[name] = form

    def make_form_router(self, request, *args, **kwargs):
        return FormRouter(self.form_classes, request, *args, **kwargs)

    def check_form_created_with_no_data(self, form_router, name, *args,
                                        **kwargs):
        form = form_router[name]
        kwargs['auto_id'] = '{}_id-%s'.format(name)
        assert_equal(self.form_classes[name].call_args,
                     mock.call(*args, **kwargs))

    def check_form_created_with_with_data(self, form_router, name, request,
                                          *args, **kwargs):
        form = form_router[name]
        kwargs.update({
            'auto_id': '{}_id-%s'.format(name),
            'data': request.POST,
            'files': request.FILES,
        })
        assert_equal(self.form_classes[name].call_args,
                     mock.call(*args, **kwargs))

    def test_build_without_data(self):
        # test building the forms for a GET request when we aren't passing
        # data to any form
        request = mock.Mock(method='GET')
        form_router = self.make_form_router(request, 'foo', bar='baz')
        self.check_form_created_with_no_data(
            form_router, 'form1', 'foo', bar='baz')
        self.check_form_created_with_no_data(
            form_router, 'form2', 'foo', bar='baz')
        self.check_form_created_with_no_data(
            form_router, 'form3', 'foo', bar='baz')
        assert_equal(form_router.submitted_form, None)

    def test_build_with_data(self):
        # test building the forms for a POST request when we want to pass data
        # to 1 form
        request = mock.Mock(method='POST', POST={
            'form': 'form1',
            'name': 'value',
        })
        form_router = self.make_form_router(request, 'foo', bar='baz')
        self.check_form_created_with_with_data(
            form_router, 'form1', request, 'foo', bar='baz')
        self.check_form_created_with_no_data(
            form_router, 'form2', 'foo', bar='baz')
        self.check_form_created_with_no_data(
            form_router, 'form3', 'foo', bar='baz')
        assert_equal(form_router.submitted_form, self.forms['form1'])

    def test_lazy_building(self):
        # forms shouldn't be built until they're accessed
        request = mock.Mock(method='GET')
        form_router = self.make_form_router(request)
        FormClass = self.form_classes['form1']
        assert_equal(FormClass.call_count, 0)
        form_router['form1']
        assert_equal(FormClass.call_count, 1)
        # accessing the form again shouldn't result in it being built again
        form_router['form1']
        assert_equal(FormClass.call_count, 1)

    def test_contains(self):
        # forms shouldn't be built until they're accessed
        request = mock.Mock(method='GET')
        form_router = self.make_form_router(request)
        assert_true('form1' in form_router)
        assert_true('form2' in form_router)
        assert_true('form3' in form_router)
        assert_false('form4' in form_router)
