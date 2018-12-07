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

"""
CodeField -- Django field for storing codes

This filed works like an enum field.  At the code-level, you assign it
slug-like strings.  In the database, the codes get stored as 2-byte integers.

CodeField has support for extending the supported codes.  This allows you to
define a CodeField on a model in one app, then add extra codes in other apps

Each code has an associated Code object, which is accessible from the model
class.  This combines nicely with the above feature, since you can use the
extension codes to change the model behavior.

A good example of CodeField is the ActivityRecord.type field, which classifies
the kind of activity and customizes the message we display for it.
"""

# FIXME: Merge this code with EnumField

from __future__ import absolute_import

from django.db import models
from django.core import exceptions

class Code(object):
    """A possible code for a CodeField"""
    slug = NotImplemented
    label = NotImplemented

class SimpleCode(object):
    """Code consisting of simply a slug and a label."""
    def __init__(self, slug, label):
        self.slug = slug
        self.label = label

# UnusedCode represents a number in the underlying integer field that's not
# used anymore.  Use this when a code is deleted, since removing it from the
# list would change all subsequent codes
UnusedCode = SimpleCode('unused', 'Unused')

class CodeField(models.PositiveSmallIntegerField):
    """
    Store codes in a database field.

    This field adds several attributes to the model class.  If you have a
    CodeField named "foo", then we create the following fields:

      - foo: code slug
      - foo_code: code integer value
      - foo_obj: instance of the Code subclass
    """

    # DB Storage:
    #  We have a small int field, which means we can store values 0-65535.  We
    #  use the first two decimal digits to for the ext_id, then the next 3
    #  digits for the choice itself with a 1-based index.  This allows us to
    #  safely store 999 choices for 64 extensions.

    MAX_CHOICES = 1000

    def __init__(self, choices=None, **kwargs):
        super(CodeField, self).__init__(**kwargs)
        self.value_to_code = {} # map DB values to Code instances
        self.slug_to_value = {} # map slugs to DB values
        self.current_ext_ids = set()
        self.code_list = []
        self._choices = []
        if choices is not None:
            self._validate_choices(choices)
            self._add_choices(0, choices)

    def extend(self, ext_id, choices):
        """
        Add extra code choices for this field

        This allows other apps to extend the default code choices.

        Params:
            ext_id: integer value that identifies the extension.  If multiple
                apps call extend, each must use a unique value here
            choices: list of Choice objects

        Note:
            We generate our databes values based on the index of each choices.
            This means you can add or change code, but should never remove
            them.  If you want to retire a code, then replace it with a dummy
            Code class.
        """
        self._check_ext_id(ext_id)
        self._validate_choices(choices)
        self._add_choices(ext_id, choices)

    def _add_choices(self, ext_id, choices):
        self.current_ext_ids.add(ext_id)
        for i, code in enumerate(choices):
            if code is UnusedCode:
                continue
            elif isinstance(code, type):
                # If we get passed in a class, create an instance from it
                code = code()
            elif isinstance(code, tuple):
                # If we get passed in a 2-tuple, create a SimpleCode from it
                code = SimpleCode(*code)
            assert code.slug is not NotImplemented
            assert code.label is not NotImplemented
            code_value = (ext_id * self.MAX_CHOICES) + i + 1
            self.value_to_code[code_value] = code
            self.slug_to_value[code.slug] = code_value
            self._choices.append((code.slug, code.label))
            self.code_list.append(code)

    def _check_ext_id(self, ext_id):
        if not 1 <= ext_id <= 64:
            raise ValueError("ext_id must be between 1 and 64")
        if ext_id in self.current_ext_ids:
            raise ValueError("ext_id {} already taken".format(ext_id))

    def _validate_choices(self, choices):
        if len(choices) > self.MAX_CHOICES:
            raise ValueError(
                "Only {} choices can be stored per extension".format(
                    self.MAX_CHOICES))

    def contribute_to_class(self, cls, name):
        super(CodeField, self).contribute_to_class(cls, name)
        choices_attr_name = '{}_choices'.format(name)
        code_attr_name = '{}_code'.format(name)
        obj_attr_name = '{}_obj'.format(name)
        @staticmethod
        def get_code_choices():
            return self.choices
        @property
        def get_code_value(instance):
            slug = getattr(instance, self.get_attname(), None)
            if slug is None:
                return None
            else:
                return self.slug_to_value[slug]
        @property
        def get_code_obj(instance):
            slug = getattr(instance, self.get_attname(), None)
            if slug is None:
                return None
            return self.value_to_code[self.slug_to_value[slug]]
        setattr(cls, choices_attr_name, get_code_choices)
        setattr(cls, code_attr_name, get_code_value)
        setattr(cls, obj_attr_name, get_code_obj)

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return None
        try:
            return self.value_to_code[value].slug
        except KeyError:
            # We're given a raw number, but can't find it, just return that
            # number.  This is especially useful in database migrations, since
            # we don't have the code values setup there
            if isinstance(value, (int, long)):
                return value
            return 'unknown-code-{}'.format(value)

    def to_python(self, value):
        if value is None:
            return None
        elif isinstance(value, (int, long)):
            return self.value_to_code[value].slug
        elif isinstance(value, basestring):
            return value
        else:
            raise exceptions.ValidationError(
                'Bad type for CodeField: {}'.format(value))

    def get_prep_value(self, value):
        if value is None:
            return None
        # If we get a type code, just return it
        if isinstance(value, (int, long)):
            return value
        try:
            return self.slug_to_value[value]
        except KeyError:
            raise KeyError("Unknown code: {!r}".format(value))

    def deconstruct(self):
        name, path, args, kwargs = super(CodeField, self).deconstruct()
        if 'choices' in kwargs:
            del kwargs['choices']
        return name, path, args, kwargs

class TinyCodeField(CodeField):
    """Codefield that onll uses a TINYINT to store its values.

    Using a TINYINT leads to some limitations:
      - We only allow 256 choices
      - We don't allow any extension choices
    """
    MAX_CHOICES = 256

    def extend(self, ext_id, choices):
        raise TypeError("TinyCodeField doesn't support extension codes")

    def db_type(self, connection):
        return 'tinyint UNSIGNED'
