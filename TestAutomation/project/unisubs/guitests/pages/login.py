# Amara, universalsubtitles.org
#
# Copyright (C) 2018 Participatory Culture Foundation
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

from .base import Page

class LoginPage(Page):
    path = 'auth/login'

    def username_field(self):
        return self.driver.find_element_by_css_selector('form.auth-form #id_username')

    def password_field(self):
        return self.driver.find_element_by_css_selector('form.auth-form #id_password')

    def signin_button(self):
        return self.driver.find_element_by_css_selector(
            'form.auth-form button[type="submit"]')
