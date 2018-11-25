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

import datetime

from django.db import models

from auth.models import CustomUser as User

class ThirdPartyAccountManager(models.Manager):
    def for_user(self, user):
        return self.filter(user=user)

class ThirdPartyAccount(models.Model):
    """The (abstract) base model for the concept of a third-party account.

    Each of the subclasses of this class represents one external service.

    Each model instance holds all data related to that external service for
    a given user linked to it.

    For example, "Twitter" is a third-party service, and some Amara accounts may
    be "linked" to Twitter accounts by way of the TwitterAccount model.  The
    TwitterAccount model will hold things like the Twitter username, the OAuth
    access token, etc.

    These links are used for (or are planned to be used for) a variety of things
    on the Amara site, including:

    * Filling in User data automatically, such as the avatar and first/last
      name, so the user doesn't have to type it themselves.
    * Authenticating people into Amara Users without a username/password.
    * Performing actions in the external services themselves on the user's
      behalf, like tweeting a link to things.

    When creating new subclasses of ThirdPartyAccount we shouldn't duplicate
    data that is stored elsewhere (e.g. email address and first/last name, which
    are both in our User model).  If we have to for a client-specific reason
    that's fine, but the User model should always be the main source of truth
    for any of its fields for the Amara site.

    In general, the User <-> TPA relationship should be 1:1.  The exception
    would be if we implemented something like "OpenIDAccount" since it's
    possible a user would want to set up more than one OpenID URL linked to
    their account.

    Theoretically there's no reason one User couldn't link multiple external
    (e.g. Twitter) accounts to a single Amara User account. Maybe they want many
    people to share one Amara account but log in through multiple external
    Twitter accounts.  We don't currently let them but it might be something to
    think about in the future.

    When implementing a subclass of this, the 'kind' attribute should just be
    set to a human-readable name for the type of account, like 'Twitter' or
    'Facebook'.  It will be used in the __unicode__ representation and can be
    used to determine what type of object you're looking at in a pinch (instead
    of looking at the class).

    The identifier property should return the unique "identifier" of that
    account for that service.  For example, for Twitter this would be the
    username, but for Facebook it's the UID because not everyone has a vanity
    username.  This will also be used in the __unicode__ representation.

    """
    kind = 'Abstract'

    user = models.ForeignKey(User)

    created = models.DateTimeField(editable=False)
    modified = models.DateTimeField(editable=False)

    objects = ThirdPartyAccountManager()

    class Meta:
        abstract = True


    def save(self, *args, **kwargs):
        if not self.id and not self.created:
            self.created = datetime.datetime.now()
        self.modified = datetime.datetime.now()

        super(ThirdPartyAccount, self).save(*args, **kwargs)

    def __unicode__(self):
        return 'Third Party Account (%s): %s' % (self.kind, self.identifier)


    @property
    def identifier(self):
        return self.id

    @property
    def last_login(self):
        return self.user.last_login


class TwitterAccount(ThirdPartyAccount):
    """The Twitter-account-related data for a given User.

    Holds basic info like username and avatar URL, but also contains the OAuth
    access token needed to act on the user's behalf on Twitter.com.

    """
    kind = 'Twitter'

    username = models.CharField(max_length=200, unique=True)
    access_token = models.CharField(max_length=255, blank=True, null=True,
                                    editable=False)
    avatar = models.URLField(blank=True, null=True)

    @property
    def identifier(self):
        return self.username

class VimeoExternalAccount(ThirdPartyAccount):
    """The Vimeo-account-related data for a given User.
    """
    kind = 'Vimeo'

    username = models.CharField(max_length=200, unique=True)
    access_code = models.CharField(max_length=255, blank=True, null=True,
                                    editable=False)

    @property
    def identifier(self):
        return self.username


class FacebookAccount(ThirdPartyAccount):
    """The Facebook-account-related data for a given User.

    Holds basic info like avatar URL and the FBUID.

    Note that Facebook UIDs are extremely big and often won't fit into Integer
    datatypes in databases, Javascript, etc.  We store them as strings just to
    be safe.

    """
    kind = 'Facebook'

    uid = models.CharField(max_length=200, unique=True)
    avatar = models.URLField(blank=True, null=True)

    @property
    def identifier(self):
        return self.uid
