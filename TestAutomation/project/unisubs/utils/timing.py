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

import logging
import time

logger = logging.getLogger("timing")

class DebuggingTimer:
    def __init__(self):
        self.start_time = self.last_time = time.time()

    def log_time(self, msg):
        current_time = time.time()
        logger.info("%s: %0.4f", msg, current_time - self.last_time)
        self.last_time = current_time

    def log_total_time(self, msg):
        current_time = time.time()
        logger.info("total time for %s: %0.3f", msg,
                     current_time - self.start_time)
