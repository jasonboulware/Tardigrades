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

class FormRouter(object):
    """Form router -- handle multiple forms on one page

    Form router manages multiple forms that live together on a page.  When a
    form is submitted, we route the POST data to that form but not the others.
    We accomplish this with a simple system, each form is given a name and the
    POST data should include a "name" field which specifies which form is
    being submitted.

    Form router also ensures each form has a unique auto_id field, so that we
    don't create multiple inputs with the same id attribute.

    Use dictionary access to access individual forms.  Forms are built lazily.
    They won't be created unless they are accessed.

    Attributes:
        submitted_form -- form that was submitted or None.
    """

    def __init__(self, form_map, request, *args, **kwargs):
        """Create a FormRouter

        Args:
            form_map: dict mapping unique names to form classes
            request: Django request object.  This will be used to pass POST
                data to one of the forms if needed
            args, kwargs: arguments to pass to the form class constructors.
                Note that all forms must handle these arguments (plus standard
                arguments like data, files, auto_id, etc).
        """
        self.form_map = form_map
        self.args = args
        self.kwargs = kwargs
        self.built_forms = {}
        if request.method == 'POST':
            self.submitted_form_name = request.POST.get('form')
            self.data = request.POST
            self.files = request.FILES
        else:
            self.submitted_form_name = None
            self.data = self.files = None

    def __getitem__(self, name):
        if name not in self.built_forms:
            self.built_forms[name] = self._build_form(name)
        return self.built_forms[name]

    def __contains__(self, name):
        return name in self.form_map

    def _build_form(self, name):
        kwargs = self.kwargs.copy()
        kwargs['auto_id'] = '{}_id-%s'.format(name)
        if name == self.submitted_form_name:
            kwargs['data'] = self.data
            kwargs['files'] = self.files
        FormClass = self.form_map[name]
        return FormClass(*self.args, **kwargs)

    @property
    def submitted_form(self):
        if self.submitted_form_name is None:
            return None
        else:
            return self[self.submitted_form_name]
