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

"""staticmedia.bundles -- bundle media files

This module handles bundling Javascript, CSS, and other media files.  Bundling
the files does several things.

    - Combines multiple files into a single file
    - Compresses/minifies them
    - Optionally processes them through a preprocessor like SASS

See the bundle_* functions for exactly what we do for various media types.
"""

import json
import os
import shutil
import tempfile
import time

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.template.loader import render_to_string

from staticmedia import utils
import optionalapps

def media_directories():
    dirs = [ settings.STATIC_ROOT ]
    for repo_dir in optionalapps.get_repository_paths():
        repo_media_dir = os.path.join(repo_dir, 'media')
        if os.path.exists(repo_media_dir):
            dirs.append(repo_media_dir)
    return dirs

class Bundle(object):
    """Represents a single media bundle."""

    mime_type = NotImplemented
    bundle_type = NotImplemented

    def __init__(self, name, config):
        self.name = name
        self.config = config

    def path(self, filename):
        for media_dir in media_directories():
            path_try = os.path.join(media_dir, filename)
            if os.path.exists(path_try):
                return path_try
        raise ValueError("Can't find media path: {}".format(filename))

    def paths(self):
        return [self.path(p) for p in self.config['files']]

    def concatinate_files(self):
        return ''.join(open(p).read() for p in self.paths())

    def build_contents(self):
        """Build the contents of this bundle

        Subclasses of Bundle must implement this function

        :returns: string representing the bundle
        """
        raise NotImplementedError()

    def get_url(self):
        """Get an URL that points to this bundle."""
        if settings.STATIC_MEDIA_USES_S3:
            return self.get_s3_url()
        else:
            return self.get_local_server_url()

    def get_s3_url(self):
        return "%s%s/%s" % (utils.static_url(), self.bundle_type, self.name)

    def get_local_server_url(self):
        view_name = 'staticmedia:%s_bundle' % self.bundle_type
        return reverse(view_name, kwargs={
            'bundle_name': self.name,
        })

    def get_html(self):
        """Get the HTML for this bundle

        This gets placed inside the <head> tag.
        """
        raise NotImplementedError()

    def modified_since(self, since):
        """Check if any of our files has been modified after a certain time
        """
        return max(os.path.getmtime(p) for p in self.paths()) > since

    def cache_key(self):
        return 'staticmedia:bundle:%s' % self.name

    def get_contents(self):
        """Get the data for this bundle.

        The first time this method is called, we will build the bundle, then
        store the result in the django cache.

        On subsequent calls, we will only build the bundle again if one of our
        files has been modified since the last build.
        """
        cached_value = cache.get(self.cache_key())
        if cached_value is not None:
            if not self.modified_since(cached_value[0]):
                return cached_value[1]
        cache_time = time.time()
        rv = self.build_contents()
        cache.set(self.cache_key(), (cache_time, rv))
        return rv

class JavascriptBundle(Bundle):
    """Bundle Javascript files.

    Javascript files are concatinated together, then run through uglifyjs to
    minify them.
    """

    mime_type = 'text/javascript'
    bundle_type = 'js'

    def should_add_amara_conf(self):
        return self.config.get('add_amara_conf', False)

    def generate_amara_conf(self):
        return render_to_string('staticmedia/amara-conf.js', {
            'base_url': settings.HOSTNAME,
            'static_url': utils.static_url(),
        })

    def concatinate_files(self):
        content = Bundle.concatinate_files(self)
        if self.should_add_amara_conf():
            return self.generate_amara_conf() + content
        else:
            return content

    def build_contents(self):
        source_code = self.concatinate_files()
        if settings.STATIC_MEDIA_COMPRESSED:
            return utils.run_command(['uglifyjs'], stdin=source_code)
        else:
            return source_code

    def get_html(self):
        return '<script src="%s"></script>' % self.get_url()

class RequireJSBundle(Bundle):
    """Bundle Javascript using require.js

    This bundle is used when the extension is js and use_requirejs is set to
    True.

    The basic strategy is to use require.js to load our modules and it's
    companion r.js to combine and optimize them.  For development, we load
    require.js and point it at our toplevel modules.  For production, we use
    rjs to combine and compress the code.

    The root_dir and sub_dirs settings are used to create a virtual filesystem
    that require.js sees.  root_dir specifies the root directory contents and
    sub_dirs specifies the subdirectories.  Both of those commands take paths
    relative to STATIC_ROOT (AKA the media directory).

    One tricky part about the directory structure is that we have media
    directories in both unisubs and our optional repos.  For the virtual
    filesystem, we merge files from both of those.

    The config.js and main.js files then load our modules using the paths from
    the virtual filesystem.  Also the extension_modules setting allows
    optional repos to load other modules.

    Options:
        use_requirejs: Enables this bundle type instead of JavascriptBundle
        root_dir: root directory for modules
        sub_dirs: sub directories for modules
        main: Name of the main module (defaults to "main")
        config: Name of the configuration module (defaults to "config")
        extension_modules: Modules from extension repositories to load.
    """

    mime_type = 'text/javascript'
    bundle_type = 'js'

    # settings.STATIC_MEDIA_USES_S3
    # settings.STATIC_MEDIA_COMPRESSED

    def config_module(self):
        return self.config.get('config', 'config')

    def main_module(self):
        return self.config.get('main', 'main')

    def sub_dirs(self):
        return self.config.get('sub_dirs', {})

    def extension_modules(self):
        return self.config.get('extension_modules', [])

    def resolve_dev_path(self, module_path):
        """Locate a path to be served by the development server

        This method finds a filesystem path for a path relative to the baseUrl
        config value that we set up in get_html_local_server()
        """
        for dir_name, real_dir in self.sub_dirs().items():
            if module_path.startswith(dir_name + '/'):
                return self.path(module_path.replace(dir_name, real_dir, 1))
        return self.path(os.path.join(self.config['root_dir'], module_path))

    def setup_build_dir(self, build_dir):
        """Setup a temp directory to build from

        This method finds files in root_dir and sub_dirs in all the media
        directories (unisubs + all optional repos) and links to those files
        from build_dir.

        This directory is what we point r.js to when building our single JS
        file.
        """
        def setup_links(media_dir, dest_dir):
            for media_root in media_directories():
                source_dir = os.path.join(media_root, media_dir)
                if not os.path.exists(source_dir):
                    continue
                for filename in os.listdir(source_dir):
                    os.symlink(os.path.join(source_dir, filename),
                               os.path.join(dest_dir, filename))
        setup_links(self.config['root_dir'], build_dir)
        for dir_name, real_dir in self.sub_dirs().items():
            dir_path = os.path.join(build_dir, dir_name)
            os.mkdir(dir_path)
            setup_links(real_dir, dir_path)

    def build_contents(self):
        build_dir = tempfile.mkdtemp()
        try:
            return self._build_contents(build_dir)
        finally:
            shutil.rmtree(build_dir)

    def _build_contents(self, build_dir):
        self.setup_build_dir(build_dir)
        optimize = "uglify" if settings.STATIC_MEDIA_COMPRESSED else "none"
        build_config = {
            'baseUrl': build_dir,
            'mainConfigFile': os.path.join(build_dir,
                                           self.config_module() + '.js'),
            'findNestedDependencies': True,
            'name': os.path.join(settings.STATIC_ROOT,
                                 "bower/almond/almond.js"),
            'include': [self.main_module()] + self.extension_modules(),
            'insertRequire': self.extension_modules(),
            'optimize': optimize,
            'logLevel': 4,
        }
        r_path = os.path.join(settings.STATIC_ROOT, 'bower/rjs/dist/r.js')
        with tempfile.NamedTemporaryFile(suffix='.js', prefix='build-') as f:
            json.dump(build_config, f)
            f.flush()
            return utils.run_command([
                'nodejs', r_path, '-o', f.name, 'out=stdout'
            ])

    def get_html(self):
        if settings.STATIC_MEDIA_USES_S3:
            return self.get_html_s3()
        else:
            return self.get_html_local_server()

    def get_html_s3(self):
        return '<script async src="{}"></script>'.format(self.get_s3_url())

    def get_html_local_server(self):
        """HTML for a local dev server."""

        return """\
<script src="/media/js/require.js"></script>
<script>
  require.config({config});
  {config_module}
  require({modules});
</script>""".format(
    config=json.dumps({
        'baseUrl': self.get_url()
    }),
    config_module=self.config_module_source(),
    modules=json.dumps([
        self.main_module(),
    ] + self.extension_modules()))

    def config_module_source(self):
        path = self.path(os.path.join(self.config['root_dir'],
                                      self.config_module() + '.js'))
        with open(path) as f:
            return f.read()

class CSSBundle(Bundle):
    """Bundle CSS files

    For CSS files, we:
        - Concatinate all files together
        - Use SASS for process them.  We also use SASS to compress the CSS
        files.

    For regular CSS files, SASS simple handles compressing them.  CSS files
    can also use the Sassy CSS format.  SASS is run with --load-path
    STATIC_ROOT/css to control how sass finds modules.
    """

    mime_type = 'text/css'
    bundle_type = 'css'

    def include_paths(self):
        if 'include_paths' in self.config:
            return [
                self.path(path) for path in self.config['include_paths']
            ]
        seen = set()
        rv = []
        def add_paths(paths):
            for path in paths:
                if path not in seen:
                    rv.append(path)
                    seen.add(path)

        add_paths(os.path.join(path, 'css') for path in media_directories())
        add_paths(os.path.dirname(path) for path in self.paths())
        if 'include_paths' in self.config:
            add_paths(self.path(p) for p in self.config['include_paths'])
        return rv

    def modified_since(self, since):
        # Update modified_since to check all files in our paths.  This is
        # needed to handle the SASS include directive.
        for path in self.include_paths():
            for child in os.listdir(path):
                if os.path.getmtime(os.path.join(path, child)) > since:
                    return True
        return False

    def build_contents(self):
        source_css = self.concatinate_files()
        if settings.STATIC_MEDIA_COMPRESSED:
            sass_type = 'compressed'
        else:
            sass_type = 'expanded'
        cmdline = [
            'sass', '-t', sass_type, '-E', 'utf-8', 
        ]
        for path in self.include_paths():
            cmdline.extend(['--load-path', path])
        cmdline.extend(['--scss', '--stdin'])
        return utils.run_command(cmdline, stdin=source_css)

    def get_html(self):
        url = self.get_url()
        return '<link href="%s" rel="stylesheet" type="text/css" />' % url

def get_bundle(name):
    basename, ext = name.rsplit('.', 1)
    try:
        config = settings.MEDIA_BUNDLES[name]
    except KeyError:
        # hack to find the setting using the old unisubs_compressor format
        config = settings.MEDIA_BUNDLES[basename]
    if ext == 'css':
        return CSSBundle(name, config)
    elif ext == 'js':
        if config.get('use_requirejs'):
            return RequireJSBundle(name, config)
        else:
            return JavascriptBundle(name, config)
    else:
        raise ValueError("Unknown bundle type for %s" % name)
