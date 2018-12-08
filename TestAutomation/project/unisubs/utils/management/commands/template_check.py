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

import os
import warnings

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template import Template
from django.template.loaders.app_directories import app_template_dirs


class Command(BaseCommand):
    help = u'Test that all templates compile'
    
    def handle(self, *args, **kwargs):
        warnings.simplefilter('always')
        self.error_count = self.warning_count = self.template_count = 0

        for path in self.find_template_files():
            self.template_count += 1
            self.check_template(path)
        self.stdout.write(
            "\n{0} templates checked {1} errors {2} warnings\n".format(
                self.template_count, self.error_count, self.warning_count))

    def find_template_files(self):
        for template_dir in (settings.TEMPLATE_DIRS + app_template_dirs):
            for dir_path, dirnames, filenames in os.walk(template_dir):
                for filename in filenames:
                    if filename.startswith('.'):
                        continue
                    yield os.path.join(dir_path, filename)

    def check_template(self, path):
        try:
            with warnings.catch_warnings(record=True) as caught_warnings:
                content = open(path).read()
                Template(content)
            for w in caught_warnings:
                self.warning_count += 1
                self.report_issue(path, 'Warning: {0}', warnings.formatwarning(
                    w.message, w.category, w.filename, w.lineno))
        except Exception, e:
            self.error_count += 1
            self.report_issue(path, 'Compile error: {0}', e)

    def report_issue(self, path, msg, *args, **kwargs):
        msg = msg.format(*args, **kwargs)
        self.stdout.write('{0}: {1}\n'.format(path, msg))

