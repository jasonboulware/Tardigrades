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

from collections import namedtuple
import os

from django.conf import settings
from django.urls import reverse
from django.template.loader import TemplateDoesNotExist, render_to_string
from markdown import markdown
import pykss
import yaml

from ui import Link

CSS_ROOT = os.path.join(settings.PROJECT_ROOT, 'amara-assets/scss/')
TOC_PATH = os.path.join(settings.PROJECT_ROOT, 'apps/styleguide/styleguide-toc.yml')

# Single example in a section
StyleGuideExample = namedtuple('StyleGuideExample', 'source styles')
# TOC item that refers to a single section
StyleGuideTOCItem = namedtuple('StyleGuideTOCItem', 'title section_id')
# TOC item that refers to a list of subitems
StyleGuideTOCList= namedtuple('StyleGuideTOCList', 'title children')

class StyleGuideSectionTemplate(object):
    """
    Section of the styleguide that we render using a template from
    the styleguide/sections/ directory
    """
    def __init__(self, section_id, title):
        self.id = section_id
        self.title = title
        self.template_name = 'styleguide/{}.html'.format(section_id)

class StyleGuideSectionPyKSS(object):
    """
    Section of the styleguide that we render using pykss

    This class wraps the pykss Section class to provide the things we use in
    our styleguide HTML.
    """
    def __init__(self, pykss_section):
        self.setup_id(pykss_section)
        self.setup_title_description(pykss_section)
        self.setup_examples(pykss_section)
        self.template_name = "styleguide/kss-section.html"

    def setup_id(self, pykss_section):
        self.id = pykss_section.section.replace('.', '-')

    def setup_title_description(self, pykss_section):
        if '\n' in pykss_section.description:
            title, description = pykss_section.description.split('\n', 1)
        else:
            title = pykss_section.description
            description = ''
        self.title = title.strip()
        self.description = markdown(description.strip())

    def setup_examples(self, pykss_section):
        self.examples = [
            StyleGuideExample(example.template, example.styles)
            for example in pykss_section.examples
        ]

    def render_content(self):
        self.content = render_to_string('styleguide/section.html', {
            'title': self.title,
            'description': self.description,
            'examples': self.examples,
        })

class StyleGuide(object):
    def __init__(self):
        self.pykss_parser = pykss.Parser(CSS_ROOT)
        self.sections = {}
        self.walk_toc_file()

    def parse_toc_file(self):
        with open(TOC_PATH) as f:
            return yaml.load(f)

    def walk_toc_file(self):
        self.toc = []
        toc_data = self.parse_toc_file()
        for section in toc_data:
            name, items = section[0], section[1:]
            self.toc.append(
                (
                    name,
                    [ self.parse_toc_section(i) for i in items ]
                 )
            )

    def parse_toc_section(self, section_data):
        if isinstance(section_data, dict):
            # Handle a section that we render with a django template
            section = StyleGuideSectionTemplate(section_data['id'], section_data['title'])
        else:
            # Handle a section that we render with PyKSS
            section = StyleGuideSectionPyKSS(self.pykss_parser.sections[section_data])
        self.sections[section.id] = section

        url = reverse('styleguide:section', args=(section.id,))
        link = Link(section.title, url, class_='styleGuide-navLink')
        link.section_id = section.id
        return link
