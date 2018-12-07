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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

from django.conf import settings


if not hasattr(settings, 'AUTHENTICATION_PROVIDER_REGISTRY'):
    settings.AUTHENTICATION_PROVIDER_REGISTRY = {}

def add_authentication_provider(ap_instance):
    existing_ap = settings.AUTHENTICATION_PROVIDER_REGISTRY.get(ap_instance.code)
    if existing_ap:
        if existing_ap.verbose_name != ap_instance.verbose_name:
            assert False, "Authentication provider code collision!"
        else:
            # Assume that if we're adding a provider with the same code and
            # verbose_name as an existing one that it's Python's importing being
            # silly and not a real collision.
            return

    settings.AUTHENTICATION_PROVIDER_REGISTRY[ap_instance.code] = ap_instance

def get_authentication_provider(key):
    return settings.AUTHENTICATION_PROVIDER_REGISTRY.get(key)

def get_authentication_provider_choices():
    choices = []
    for provider in settings.AUTHENTICATION_PROVIDER_REGISTRY.values():
        choices.append((provider.code, provider.verbose_name))
    return choices


class AuthenticationProvider(object):
    """The base class that other authentication providers should implement.

    In a nutshell, an AuthenticationProvider is a simple class that has:

    * A code attribute.  This should be a unique string less than
      24 characters long that will be stored as an attribute of Teams.

    * A verbose_name attribute, for admin labels.

    * A url() method, which takes a "next" URL, and returns the URL we should
      send the user to where they can log in with the provider.

    * An image_url() method, which returns the URL for an image we should
      display to the user when they're deciding whether or not to continue and
      log in.

    """
    code = None
    verbose_name = None

    def url(self):
        """Return the URL someone should be sent to where they will log in."""
        assert False, "Not Implemented"

    def image_url(self):
        """Return the URL of an image to display (probably a logo) or None."""
        assert False, "Not Implemented"


class SampleAuthProvider(AuthenticationProvider):
    code = 'sample'
    verbose_name = 'Sample Provider'

    def url(self):
        return 'http://example.com/'

    def image_url(self):
        return 'http://placekitten.com/200/200/'

add_authentication_provider(SampleAuthProvider())


