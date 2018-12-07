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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

from __future__ import absolute_import

import os

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.test.utils import override_settings

from staticmedia import bundles
from utils import test_utils

@override_settings(MEDIA_BUNDLES={
    'test.js': {
        'files': (
            'foo.js',
            'bar.js',
        )
    },
    'test.css': {
        'files': (
            'foo.css',
            'bar.css',
        )
    },
})
class TestGetBundle(TestCase):
    def test_get_js_bundle(self):
        js_bundle = bundles.get_bundle('test.js')
        self.assertEqual(type(js_bundle), bundles.JavascriptBundle)
        self.assertEqual(js_bundle.name, 'test.js')
        self.assertEqual(js_bundle.bundle_type, 'js')
        self.assertEqual(js_bundle.config['files'], ('foo.js', 'bar.js'))
        self.assertEqual(js_bundle.mime_type, 'text/javascript')

    def test_get_css_bundle(self):
        css_bundle = bundles.get_bundle('test.css')
        self.assertEqual(css_bundle.name, 'test.css')
        self.assertEqual(css_bundle.bundle_type, 'css')
        self.assertEqual(type(css_bundle), bundles.CSSBundle)
        self.assertEqual(css_bundle.config['files'], ('foo.css', 'bar.css'))
        self.assertEqual(css_bundle.mime_type, 'text/css')

class TestBuildBundle(TestCase):
    @test_utils.patch_for_test('staticmedia.utils.run_command')
    @test_utils.patch_for_test('staticmedia.bundles.media_directories')
    def setUp(self, mock_media_directories, mock_run_command):
        self.mock_run_command = mock_run_command
        self.mock_run_command.return_value = 'test-compressed-output'
        self.static_root = os.path.join(os.path.dirname(__file__), 'testdata')
        mock_media_directories.return_value = [self.static_root]

    def read_and_combine_files(self, relative_paths):
        return ''.join([
            open(os.path.join(self.static_root, p)).read()
            for p in relative_paths
        ])

    @override_settings(STATIC_MEDIA_COMPRESSED=True)
    def test_build_css(self):
        css_paths = ['foo.css', 'bar.css']
        css_bundle = bundles.CSSBundle('bundle.css', {
            'files': css_paths,
        })

        result = css_bundle.build_contents()
        self.assertEquals(self.mock_run_command.call_count, 1)
        self.mock_run_command.assert_called_with([
            'sass',
            '-t', 'compressed', '-E', 'utf-8',
            '--load-path', os.path.join(self.static_root, 'css'),
            '--load-path', os.path.join(self.static_root),
            '--scss',
            '--stdin',
        ], stdin=self.read_and_combine_files(css_paths))
        self.assertEquals(result, 'test-compressed-output')

    @override_settings(STATIC_MEDIA_COMPRESSED=True)
    def test_build_js(self):
        js_paths = ['foo.js', 'bar.js']
        js_bundle = bundles.JavascriptBundle('bundle.js', {
            'files': js_paths,
        })

        result = js_bundle.build_contents()
        self.assertEquals(self.mock_run_command.call_count, 1)
        self.mock_run_command.assert_called_with(
            ['uglifyjs'],
            stdin=self.read_and_combine_files(js_paths))
        self.assertEquals(result, 'test-compressed-output')

    @override_settings(STATIC_MEDIA_COMPRESSED=False)
    def test_build_css_uncompressed(self):
        css_paths = ['foo.css', 'bar.css']
        css_bundle = bundles.CSSBundle('bundle.css', {
            'files': css_paths,
        })

        result = css_bundle.build_contents()
        self.assertEquals(self.mock_run_command.call_count, 1)
        self.mock_run_command.assert_called_with([
            'sass',
            '-t', 'expanded', '-E', 'utf-8',
            '--load-path', os.path.join(self.static_root, 'css'),
            '--load-path', os.path.join(self.static_root),
            '--scss',
            '--stdin',
        ], stdin=self.read_and_combine_files(css_paths))
        self.assertEquals(result, 'test-compressed-output')

    @override_settings(STATIC_MEDIA_COMPRESSED=False)
    def test_build_js_uncompressed(self):
        js_paths = ['foo.js', 'bar.js']
        js_bundle = bundles.JavascriptBundle('bundle.js', {
            'files': js_paths,
        })

        result = js_bundle.build_contents()
        self.assertEquals(self.mock_run_command.call_count, 0)
        self.assertEquals(result, self.read_and_combine_files(js_paths))

class TestCaching(TestCase):
    def setUp(self):
        self.bundle = bundles.Bundle('bundle.js', {
            'files': ('foo.js', 'bar.js')
        })

    @test_utils.patch_for_test('staticmedia.bundles.Bundle.path')
    @test_utils.patch_for_test('os.path.getmtime')
    def test_modified_since(self, mock_getmtime, mock_path):
        mock_path.side_effect = lambda filename: filename
        def getmtime(path):
            if path == 'foo.js':
                return 200
            elif path == 'bar.js':
                return 100
            else:
                raise ValueError("unexpected path: %s" % path)
        mock_getmtime.side_effect = getmtime
        # the latest mtime is 200, so the bundle should be considired modified
        # when the time earlier than that
        self.assertEquals(self.bundle.modified_since(300), False)
        self.assertEquals(self.bundle.modified_since(200), False)
        self.assertEquals(self.bundle.modified_since(100), True)

    def test_cache_key(self):
        self.assertEqual(self.bundle.cache_key(),
                         'staticmedia:bundle:bundle.js')

    @test_utils.patch_for_test('staticmedia.bundles.Bundle.modified_since')
    @test_utils.patch_for_test('staticmedia.bundles.Bundle.build_contents')
    def test_get_contents(self, mock_build, mock_modified_since):
        mock_build.return_value = 'build-output'
        # the first time we call get, there's nothing in the cache, so we
        # should build the bundle without checking any mtimes
        self.assertEqual(self.bundle.get_contents(), 'build-output')
        self.assertEqual(mock_build.call_count, 1)
        self.assertEqual(mock_modified_since.call_count, 0)
        # After the first call to get, we should only build the bundle if one
        # of the files has been modified (modified_since returns True)
        mock_modified_since.return_value = False
        self.assertEqual(self.bundle.get_contents(), 'build-output')
        self.assertEqual(mock_build.call_count, 1)
        self.assertEqual(mock_modified_since.call_count, 1)

        mock_modified_since.return_value = True
        self.assertEqual(self.bundle.get_contents(), 'build-output')
        self.assertEqual(mock_build.call_count, 2)
        self.assertEqual(mock_modified_since.call_count, 2)
