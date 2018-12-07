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

class SyncingError(StandardError):
    def __init__(self, msg, *args):
        StandardError.__init__(self)
        self.msg = msg % args

    def __str__(self):
        return self.msg

class RetryableSyncingError(SyncingError):
    def __init__(self, orig_error, msg, *args):
        super(RetryableSyncingError, self).__init__(msg, *args)
        self.orig_error = orig_error

class YouTubeAccountExistsError(StandardError):
    def __init__(self, other_account):
        StandardError.__init__(self)
        self.other_account = other_account

class VimeoSyncAccountExistsError(StandardError):
    def __init__(self, other_account):
        StandardError.__init__(self)
        self.other_account = other_account
