# Amara, universalsubtitles.org
#
# Copyright (C) 2014 Participatory Culture Foundation
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

"""utils.subtitles -- Subtitle-related functions.

This module creates a custom SubtitleLoader which allows us to control the
styling/layout.
"""

from babelsubs.loader import SubtitleLoader

subtitle_loader = SubtitleLoader()
subtitle_loader.add_style('amara-style',
                          color="white",
                          fontFamily="proportionalSansSerif",
                          fontSize="18px",
                          backgroundColor="transparent",
                          textOutline="black 1px 0px",
                          textAlign="center")
subtitle_loader.add_region('bottom', 'amara-style',
                           extent='100% 20%',
                           origin='0% 80%')
subtitle_loader.add_region('top', 'amara-style',
                           extent='100% 20%',
                           origin='0% 0%')

def create_new_subtitles(language_code, title='', description='',
                         frame_rate=None, frame_rate_multiplier=None,
                         drop_mode=None):
    return subtitle_loader.create_new(language_code, title, description,
                                      frame_rate, frame_rate_multiplier,
                                      drop_mode)

def load_subtitles(language_code, content, file_type):
    return subtitle_loader.loads(language_code, content, file_type)

def load_subtitles_from_file(language_code, path):
    return subtitle_loader.load(language_code, path)

def dfxp_merge(subtitle_sets):
    return subtitle_loader.dfxp_merge(subtitle_sets)
