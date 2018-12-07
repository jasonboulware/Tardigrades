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

from rest_framework.serializers import ValidationError

class FieldFailMixin(object):
    """Mixin for serializers that adds the field_fail() method"""

    def field_fail(self, field_name, key, **kwargs):
        """
        Version of fail() that associates the error with a field.

        This is useful when you want to signal an error outside of the
        validation code.  For example when we catch an exception inside the
        create() method.
        """
        msg = self.error_messages[key]
        message_string = msg.format(**kwargs)
        raise ValidationError({field_name: message_string})
