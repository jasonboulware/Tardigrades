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

import os
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = u'Build the amara documentaiton'
    
    def handle(self, *args, **kwargs):
        docs_dir = os.path.join(settings.PROJECT_ROOT, 'docs')
        os.chdir(docs_dir)
        subprocess.check_call(['make', 'html'])
