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

"""build_closure_bundle -- Build Javascript media bundles with closure

This command builds the older Javascript media bundles like the old embedder
(embed.js).
"""

# WARNING: the code in this module is not great.  It's basically a
# cut-and-paste job from the old compile_media command, which wasn't that
# pretty to begin with.  This is a quick and dirty job because we are hoping
# to get deprecate/trash the javascript code that gets built.

import os
import shutil
import subprocess
import tempfile

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from deploy.git_helpers import get_current_commit_hash
import staticmedia
import widget

LEGACYJS_DIR = os.path.join(settings.STATIC_ROOT, 'legacy-js')

JS_LIB = os.path.join(settings.PROJECT_ROOT, "media")
CLOSURE_LIB = os.path.join(JS_LIB, "js", "closure-library")
FLOWPLAYER_JS = os.path.join(
    settings.PROJECT_ROOT, "media/flowplayer/flowplayer-3.2.13.min.js")
COMPILER_PATH = os.path.join(settings.PROJECT_ROOT,  "closure", "compiler.jar")


LAST_COMMIT_GUID = get_current_commit_hash() or settings.LAST_COMMIT_GUID

# Old settings that we need to do the builds, but we don't want to keep in
# settings.py

# paths provided relative to media/js
JS_CORE = \
    ['js/unisubs.js', 
     'js/rpc.js',
     'js/clippy.js',
     'js/flash.js',
     'js/spinner.js',
     'js/sliderbase.js',
     'js/closingwindow.js',
     'js/loadingdom.js',
     'js/tracker.js',
     'js/style.js',
     'js/html/markdown.js',
     'js/messaging/simplemessage.js',
     'js/player/video.js',
     'js/player/captionview.js',
     'js/widget/usersettings.js',
     'js/player/abstractvideoplayer.js',
     'js/player/flashvideoplayer.js',
     'js/player/html5mediaplayer.js',
     'js/player/html5videoplayer.js',
     'js/player/html5audioplayer.js',
     'js/player/youtubevideoplayer.js',
     'js/player/ytiframevideoplayer.js',
     'js/player/youtubebasemixin.js',
     'js/player/jwvideoplayer.js',
     'js/player/flvvideoplayer.js',
     'js/player/flashaudioplayer.js',
     'js/player/mediasource.js',
     'js/player/mp3source.js',
     'js/player/html5videosource.js',
     'js/player/youtubevideosource.js',
     'js/player/ytiframevideosource.js',
     'js/player/brightcovevideosource.js',
     'js/player/brightcovevideoplayer.js',
     'js/player/flvvideosource.js',
     'js/player/controlledvideoplayer.js',
     'js/player/vimeovideosource.js',
     'js/player/vimeovideoplayer.js',
     'js/player/dailymotionvideosource.js',
     'js/player/wistiavideosource.js',
     'js/player/wistiavideoplayer.js',
     'js/player/dailymotionvideoplayer.js',
     'js/startdialog/model.js',
     'js/startdialog/videolanguage.js',
     'js/startdialog/videolanguages.js',
     'js/startdialog/tolanguage.js',
     'js/startdialog/tolanguages.js',
     'js/startdialog/dialog.js',
     'js/streamer/streambox.js', 
     'js/streamer/streamboxsearch.js', 
     'js/streamer/streamsub.js', 
     'js/streamer/streamervideotab.js', 
     'js/streamer/streamerdecorator.js', 
     'js/widget/videotab.js',
     'js/widget/hangingvideotab.js',
     'js/widget/subtitle/editablecaption.js',
     "js/widget/subtitle/editablecaptionset.js",
     'js/widget/logindialog.js',
     'js/widget/howtovideopanel.js',
     'js/widget/guidelinespanel.js',
     'js/widget/dialog.js',
     'js/widget/captionmanager.js',
     'js/widget/rightpanel.js',
     'js/widget/basestate.js',
     'js/widget/subtitlestate.js',
     'js/widget/dropdowncontents.js',
     'js/widget/playcontroller.js',
     'js/widget/subtitlecontroller.js',
     'js/widget/subtitledialogopener.js',
     'js/widget/opendialogargs.js',
     'js/widget/dropdown.js',
     'js/widget/resumeeditingrecord.js',
     'js/widget/resumedialog.js',
     'js/widget/subtitle/savedsubtitles.js',
     'js/widget/play/manager.js',
     'js/widget/widgetcontroller.js',
     'js/widget/widget.js'
]

JS_DIALOG = \
    ['js/subtracker.js',
     'js/srtwriter.js',
     'js/widget/unsavedwarning.js',
     'js/widget/emptysubswarningdialog.js',
     'js/widget/confirmdialog.js',
     'js/widget/droplockdialog.js',
     'js/finishfaildialog/dialog.js',
     'js/finishfaildialog/errorpanel.js',
     'js/finishfaildialog/reattemptuploadpanel.js',
     'js/finishfaildialog/copydialog.js',
     'js/widget/editmetadata/dialog.js',
     'js/widget/editmetadata/panel.js',
     'js/widget/editmetadata/editmetadatarightpanel.js',
     'js/widget/subtitle/dialog.js',
     'js/widget/subtitle/msservermodel.js',
     'js/widget/subtitle/subtitlewidget.js',
     'js/widget/subtitle/addsubtitlewidget.js',
     'js/widget/subtitle/subtitlelist.js',
     'js/widget/subtitle/transcribeentry.js',
     'js/widget/subtitle/transcribepanel.js',
     'js/widget/subtitle/transcriberightpanel.js',
     'js/widget/subtitle/syncpanel.js',
     'js/widget/subtitle/reviewpanel.js',
     'js/widget/subtitle/reviewrightpanel.js',
     'js/widget/subtitle/sharepanel.js',
     'js/widget/subtitle/completeddialog.js',
     'js/widget/subtitle/editpanel.js',
     'js/widget/subtitle/onsaveddialog.js',
     'js/widget/subtitle/editrightpanel.js',
     'js/widget/subtitle/bottomfinishedpanel.js',
     'js/widget/subtitle/logger.js',
     'js/widget/timeline/timerow.js',
     'js/widget/timeline/timerowul.js',
     'js/widget/timeline/timelinesub.js',
     'js/widget/timeline/timelinesubs.js',
     'js/widget/timeline/timelineinner.js',
     'js/widget/timeline/timeline.js',
     'js/widget/timeline/subtitle.js',
     'js/widget/timeline/subtitleset.js',
     'js/widget/controls/bufferedbar.js',
     'js/widget/controls/playpause.js',
     'js/widget/controls/progressbar.js',
     'js/widget/controls/progressslider.js',
     'js/widget/controls/timespan.js',
     'js/widget/controls/videocontrols.js',
     'js/widget/controls/volumecontrol.js',
     'js/widget/controls/volumeslider.js',
     'js/widget/translate/bingtranslator.js',
     'js/widget/translate/dialog.js',
     'js/widget/translate/translationpanel.js',
     'js/widget/translate/translationlist.js',
     'js/widget/translate/translationwidget.js',
     'js/widget/translate/descriptiontranslationwidget.js',
     'js/widget/translate/translationrightpanel.js',
     'js/widget/translate/forkdialog.js',
     'js/widget/translate/titletranslationwidget.js']

JS_OFFSITE = list(JS_CORE)
JS_OFFSITE.append('js/widget/crossdomainembed.js')

JS_API = list(JS_CORE)
JS_API.extend(JS_DIALOG)
JS_API.extend([
        "js/widget/api/servermodel.js",
        "js/widget/api/api.js"])

JS_WIDGETIZER_CORE = list(JS_CORE)
JS_WIDGETIZER_CORE.extend([
    "js/widget/widgetdecorator.js",
    "js/widgetizer/videoplayermaker.js",
    "js/widgetizer/widgetizer.js",
    "js/widgetizer/youtube.js",
    "js/widgetizer/html5.js",
    "js/widgetizer/jwplayer.js",
    "js/widgetizer/youtubeiframe.js",
    "js/widgetizer/wistia.js",
    "js/widgetizer/soundcloud.js",
    'js/player/ooyalaplayer.js', 
    'js/player/brightcoveliteplayer.js', 
    'js/player/soundcloudplayer.js',
    'js/streamer/overlaycontroller.js'])

JS_WIDGETIZER = list(JS_WIDGETIZER_CORE)
JS_WIDGETIZER.append('js/widgetizer/dowidgetize.js')

# MEDIA_BUNDLES that need closure, copied from the old settings files
MEDIA_BUNDLES = {
    "unisubs-api":{
        "type": "js",
        "files": ["js/config.js"] + JS_API,
        "bootloader": { 
            "gatekeeper": "UnisubsApiLoaded", 
            "render_bootloader": False
        }
     },
    "unisubs-offsite-compiled":{
        "type": "js",
        "files": JS_OFFSITE,
    },
    "unisubs-widgetizer":{
        "type": "js",
        "closure_deps": "js/closure-dependencies.js",
        "files": ["js/config.js"] + JS_WIDGETIZER,
        "bootloader": { 
            "template": "widget/widgetizerbootloader.js",
            "gatekeeper": "UnisubsWidgetizerLoaded",
            "render_bootloader": True
        }
    },
}

def call_command(command):
    process = subprocess.Popen(command.split(' '),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    return process.communicate()

def _make_version_debug_string():
    """
    See Command._append_verion_for_debug

    We have this as an external function because we need this on compilation and testing deployment
    """
    return '/*unisubs.static_version="%s"*/' % LAST_COMMIT_GUID

class Command(BaseCommand):
    help = 'Build legacy Javascript media bundles'
    args = '|'.join(MEDIA_BUNDLES.keys() + ['all'])

    def handle(self, *args, **options):
        self.verbosity = int(options.get('verbosity'))
        self.setup_options()
        self.ensure_dir_exists()
        try:
            build_name = args[0]
        except IndexError:
            raise CommandError("Must provide a bundle name to compile")

        self.setup_temp_dir()
        try:
            self.run_build(build_name)
            self.copy_files_to_media_dir()
        finally:
            self.cleanup_temp_dir()

    def ensure_dir_exists(self):
        if not os.path.exists(LEGACYJS_DIR):
            os.mkdir(LEGACYJS_DIR)

    def setup_temp_dir(self):
        self.temp_dir = tempfile.mkdtemp(prefix='legacyjs-build-')
        os.mkdir(os.path.join(self.temp_dir, 'js'))

    def cleanup_temp_dir(self):
        self.check_temp_dir_empty()
        shutil.rmtree(self.temp_dir)

    def check_temp_dir_empty(self):
        leftover_files = []
        for root, dirs, files in os.walk(self.temp_dir):
            rel_dir = os.path.relpath(root, self.temp_dir)
            leftover_files.extend(os.path.join(rel_dir, f) for f in files)
        if leftover_files:
            self.stderr.write("Leftover files in temp dir!\n")
            for path in leftover_files:
                self.stderr.write("* %s\n" % path)

    def setup_options(self):
        # we used to allow these as options in the compile_media() command.
        # Now we just hardcode a value
        self.compilation_level = 'ADVANCED_OPTIMIZATIONS'

    def log_command(self, command):
        if self.verbosity >= 2:
            self.stdout.write("* %s\n" % command)
        return call_command(command)

    def run_build(self, build_name):
        if build_name == 'all':
            for bundle_name in MEDIA_BUNDLES.keys():
                self.compile_bundle(bundle_name)
        else:
            self.compile_bundle(build_name)

    def compile_bundle(self, bundle_name):
        if self.verbosity >= 1:
            self.stdout.write("building %s\n" % bundle_name)
        bundle_settings = MEDIA_BUNDLES[bundle_name]
        files = bundle_settings['files']
        # hack, we don't really want to compile bootloaders anymore for
        # various reasons.
        if 'bootloader' in bundle_settings:
            del bundle_settings['bootloader']
        self.compile_js_closure_bundle(bundle_name, bundle_settings, files)

    def copy_files_to_media_dir(self):
        temp_js_dir = os.path.join(self.temp_dir, 'js')
        for filename in os.listdir(temp_js_dir):
            dest = os.path.join(LEGACYJS_DIR, filename)
            if self.verbosity >= 1:
                rel_dest = os.path.relpath(dest, settings.PROJECT_ROOT)
                self.stdout.write("moving %s to %s\n" % (filename, rel_dest))
            shutil.move(os.path.join(temp_js_dir, filename), dest)

    def compile_js_closure_bundle(self, bundle_name, bundle_settings, files):
        if 'bootloader' in bundle_settings:
            output_file_name = "{0}-inner.js".format(bundle_name)
        else:
            output_file_name = "{0}.js".format(bundle_name)

        debug = bundle_settings.get("debug", False)
        extra_defines = bundle_settings.get("extra_defines", None)
        include_flash_deps = bundle_settings.get("include_flash_deps", True)
        closure_dep_file = bundle_settings.get("closure_deps",'js/closure-dependencies.js' )
        optimization_type = bundle_settings.get("optimizations", self.compilation_level)

        deps = [" --js %s " % os.path.join(JS_LIB, file) for file in files]
        if 'output' in bundle_settings:
            if 'bootloader' in bundle_settings:
                name = bundle_settings['output']
                name = "".join([os.path.splitext(name)[0], '-inner', os.path.splitext(name)[1]])
            compiled_js = os.path.join(self.temp_dir, name)
        else:
            compiled_js = os.path.join(self.temp_dir, "js" , output_file_name)
        compiler_jar = COMPILER_PATH

        js_debug_dep_file = ''
        if debug:
            js_debug_dep_file = '-i {0}/{1}'.format(JS_LIB, 'js/closure-debug-dependencies.js')

        cmd_str = "%s/closure/bin/calcdeps.py -i %s/%s %s -p %s/ -o script"  % (
            CLOSURE_LIB,
            JS_LIB,
            closure_dep_file,
            js_debug_dep_file,
            CLOSURE_LIB)
        output,_ = self.log_command(cmd_str)

        # This is to reduce the number of warnings in the code.
        # The unisubs-calcdeps.js file is a concatenation of a bunch of Google Closure
        # JavaScript files, each of which has a @fileoverview tag to describe it.
        # When put all in one file, the compiler complains, so remove them all.
        output_lines = filter(lambda s: s.find("@fileoverview") == -1,
                              output.split("\n"))

        calcdeps_js = os.path.join(JS_LIB, 'js', 'unisubs-calcdeps.js')
        calcdeps_file = open(calcdeps_js, "w")
        if 'ignore_closure' in bundle_settings:
            calcdeps_file.write("\n")
        else:
            calcdeps_file.write("\n".join(output_lines))
        calcdeps_file.close()

        debug_arg = ''
        if not debug:
            debug_arg = '--define goog.DEBUG=false'
        extra_defines_arg = ''
        if extra_defines is not None:
            for k, v in extra_defines.items():
                extra_defines_arg += ' --define {0}={1} '.format(k, v)
        cmd_str =  ("java -jar %s --js %s %s --js_output_file %s %s %s "
                    "--define goog.NATIVE_ARRAY_PROTOTYPES=false "
                    "--output_wrapper (function(){%%output%%})(); "
                    "--warning_level QUIET "
                    "--compilation_level %s") % \
                    (compiler_jar, calcdeps_js, deps, compiled_js,
                     debug_arg, extra_defines_arg, optimization_type)

        output,err = self.log_command(cmd_str)
        if err and self.verbosity >= 2:
            # if an error comes up, is will look like:
            self.stderr.write("Errors compiling : %s \n%s" %
                               (bundle_name, err))

        with open(compiled_js, 'r') as compiled_js_file:
            compiled_js_text = compiled_js_file.read()

        with open(compiled_js, 'w') as compiled_js_file:

            # Include dependencies needed for DFXP parsing.
            with open(os.path.join(JS_LIB, 'src', 'js', 'third-party', 'amara-jquery.min.js'), 'r') as jqueryjs_file:
                compiled_js_file.write(jqueryjs_file.read())
            with open(os.path.join(JS_LIB, 'src', 'js', 'dfxp', 'dfxp.js'), 'r') as dfxpjs_file:
                compiled_js_file.write(dfxpjs_file.read())

            if include_flash_deps:
                with open(os.path.join(JS_LIB, 'js', 'swfobject.js'), 'r') as swfobject_file:
                    compiled_js_file.write(swfobject_file.read())
                with open(FLOWPLAYER_JS, 'r') as flowplayerjs_file:
                    compiled_js_file.write(flowplayerjs_file.read())
            compiled_js_file.write(compiled_js_text)
            self._append_version_for_debug(compiled_js_file, "js")

        if 'bootloader' in bundle_settings:
            self._compile_js_bootloader(
                bundle_name, bundle_settings,
                bundle_settings['bootloader'])

    def _compile_js_bootloader(self, bundle_name, bundle_settings,
                               bootloader_settings):
        context = { 'gatekeeper' : bootloader_settings['gatekeeper'],
                    'script_src': "{0}/js/{1}-inner.js".format(
                get_cache_base_url(), bundle_name) }
        template_name = "widget/bootloader.js"
        if "template" in bootloader_settings:
            template_name = bootloader_settings["template"]
        rendered = render_to_string(template_name, context)
        file_name = os.path.join(
            self.temp_dir, "js", "{0}.js".format(bundle_name))
        output_override = bundle_settings.get('output', None)
        if output_override:
            file_name = os.path.join(self.temp_dir, output_override)
        uncompiled_file_name = os.path.join(
                self.temp_dir, "js", "{0}-uncompiled.js".format(bundle_name))
        with open(uncompiled_file_name, 'w') as f:
            f.write(rendered)
        cmd_str = ("java -jar {0} --js {1} --js_output_file {2} "
                   "--compilation_level {3}").format(
            COMPILER_PATH, uncompiled_file_name, file_name, self.compilation_level)
        self.log_command(cmd_str)
        os.remove(uncompiled_file_name)

    def _append_version_for_debug(self, descriptor, file_type):
        """
        We append the /*unisubs.static_version="{{commit guid}"*/ to the end of the
        file so we can debug, be sure we have the correct version of media.

        Arguments:
        `descriptor` : the fd to append to
        `file_type` : if it's a js or html or css file - we currently only support js and css
            """
        descriptor.write(_make_version_debug_string())
