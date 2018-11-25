//
// Copyright (C) 2013 Participatory Culture Foundation
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see
// http://www.gnu.org/licenses/agpl-3.0.html.

var angular = angular || null;

(function() {

    var module = angular.module('amara.SubtitleEditor', [
        'amara.SubtitleEditor.blob',
        'amara.SubtitleEditor.help',
        'amara.SubtitleEditor.modal',
        'amara.SubtitleEditor.dom',
        'amara.SubtitleEditor.durationpicker',
        'amara.SubtitleEditor.gettext',
        'amara.SubtitleEditor.lock',
        'amara.SubtitleEditor.preferences',
        'amara.SubtitleEditor.notes',
        'amara.SubtitleEditor.session',
        'amara.SubtitleEditor.shifttime',
        'amara.SubtitleEditor.toolbar',
        'amara.SubtitleEditor.workflow',
        'amara.SubtitleEditor.subtitles.controllers',
        'amara.SubtitleEditor.subtitles.directives',
        'amara.SubtitleEditor.subtitles.filters',
        'amara.SubtitleEditor.subtitles.models',
        'amara.SubtitleEditor.subtitles.services',
        'amara.SubtitleEditor.timeline.controllers',
        'amara.SubtitleEditor.timeline.directives',
        'amara.SubtitleEditor.video.controllers',
        'amara.SubtitleEditor.video.directives',
        'amara.SubtitleEditor.video.services',
        'ngCookies'
    ]);

    module.config(["$compileProvider", "$interpolateProvider", function($compileProvider, $interpolateProvider) {
        // instead of using {{ }} for variables, use [[ ]]
        // so as to avoid conflict with django templating
        $interpolateProvider.startSymbol('[[');
        $interpolateProvider.endSymbol(']]');
        // Allow blob: urls
        $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|blob):/);
    }]);

    module.constant('MIN_DURATION', 250); // 0.25 seconds
    module.constant('DEFAULT_DURATION', 4000); // 4 seconds

    module.factory('EditorData', ["$window", function($window) {
        /**
         * Get the editor data that was passed to us from python
         *
         */
        return $window.editorData;
    }]);

    module.controller("AppController", ['$scope', '$sce', '$controller', 
                      '$window', 'EditorData', 'VideoPlayer', 'Workflow',
                      function($scope, $sce, $controller, $window, EditorData,
                          VideoPlayer, Workflow) {
        $controller('AppControllerSubtitles', {$scope: $scope});
        $controller('AppControllerLocking', {$scope: $scope});
        $controller('AppControllerEvents', {$scope: $scope});
        $controller('DialogController', {$scope: $scope});
        $controller('PlaybackModeController', {$scope: $scope});
        $controller('SessionBackend', {$scope: $scope});
        $controller('SessionController', {$scope: $scope});

        $scope.videoId = EditorData.video.id;
        $scope.canSync = EditorData.canSync;
        $scope.showHideNextTime = EditorData.preferences.showTutorial
        $scope.canAddAndRemove = EditorData.canAddAndRemove;
        $scope.playbackModes = EditorData.playbackModes;
        $scope.scrollingSynced = true;
        $scope.loadingFinished = false;
        $scope.tutorialShown = false;
        $scope.uploading = false;
        $scope.uploadError = false;
        $scope.exiting = false;
        $scope.hideNextTime = function() {
            $scope.showHideNextTime = false;
        };
        $scope.translating = function() {
            return ($scope.referenceSubtitles.language && $scope.workingSubtitles.language.code !=  $scope.referenceSubtitles.language.code);
        };
        $scope.isTranslatingTyping = function() {return $scope.translating() && ($scope.workflow.stage == "typing");};
        $scope.isTranslatingSyncing = function() {return $scope.translating() && ($scope.workflow.stage == "syncing");};
        $scope.isTranslatingReviewing = function() {return $scope.translating() && ($scope.workflow.stage == "review");};
        $scope.isTyping = function() {return (!$scope.translating()) && ($scope.workflow.stage == "typing");};
        $scope.isSyncing = function() {return (!$scope.translating()) && ($scope.workflow.stage == "syncing");};
        $scope.isReviewing = function() {return (!$scope.translating()) && ($scope.workflow.stage == "review");};
        $scope.analytics = function() {
            if (typeof sendAnalytics !== 'undefined')
		sendAnalytics.apply(this, Array.prototype.slice.call(arguments, 0));
        };
        $scope.analytics('editor', 'launched');
        if (EditorData.customCss)
            $scope.customCSSs = [{"href": EditorData.customCss}];
        if (EditorData.teamAttributes) {
            $scope.teamName = EditorData.teamAttributes.teamName
            if (EditorData.teamAttributes.type && EditorData.teamAttributes.type != "O")
                $scope.noLinkToLegacy = true;
            if (EditorData.teamAttributes.guidelines &&
		(EditorData.teamAttributes.guidelines['subtitle'] ||
		 EditorData.teamAttributes.guidelines['translate'] ||
		 EditorData.teamAttributes.guidelines['review'])
	       ) {
		var noGuideline = "No guidelines specified.";
                $scope.teamGuidelines = { 'subtitle': $sce.trustAsHtml(EditorData.teamAttributes.guidelines['subtitle'] || noGuideline),
                                          'translate': $sce.trustAsHtml(EditorData.teamAttributes.guidelines['translate'] || noGuideline),
                                          'review': $sce.trustAsHtml(EditorData.teamAttributes.guidelines['review'] || noGuideline) };
            }
            // Needs to be a function as we can only know once language was retrieved
            $scope.teamTaskType = function() {
		return EditorData.task_needs_pane ? 'review' : $scope.translating() ? 'translate' : 'subtitle';
            };
        } else {
            $scope.teamTaskType = function() {return "";}
        }
        $scope.showTeamGuidelines = function() {
            if (($scope.teamGuidelines) && ($scope.teamName))
                return true;
            return false; 
        };
	$scope.workflow = new Workflow($scope.workingSubtitles.subtitleList);
	$scope.emptySubtitleWarningShown = function() {
            return ((!$scope.currentEdit.inProgress()) &&
                    ($scope.workflow.subtitleList.needsAnyTranscribed()) &&
                    ($scope.workflow.subtitleList.length() > 1));
        };
	$scope.invalidTimingWarningShown = function() {
            return ((!$scope.currentEdit.inProgress()) &&
                    ($scope.workflow.subtitleList.firstInvalidTiming()));
        };
	$scope.missingTranslationShown = function() {
            action = {'requires_translated_metadata_if_enabled': true};
            return $scope.session.forbidAction(action).forbid;
        };
        $scope.warningsShown = true;
        $scope.timelineShown = $scope.workflow.stage != 'typing';
        $scope.toggleScrollingSynced = function() {
            $scope.scrollingSynced = !$scope.scrollingSynced;
        };
        $scope.toggleTimelineShown = function() {
            $scope.timelineShown = !$scope.timelineShown;
        };
        $scope.toggleWarningsShown = function() {
            $scope.warningsShown = !$scope.warningsShown;
	    $scope.workingSubtitles.subtitleList.emitChange("reload", null);
        };
        $scope.toggleTutorial = function(shown) {
           $scope.tutorialShown = (typeof shown === "undefined") ? (!$scope.tutorialShown) : shown;
           if($scope.tutorialShown) {
               $scope.timelineShown = (!$scope.isTyping() && !$scope.isTranslatingTyping());
           }
        };
        $scope.keepHeaderSizeSync = function() {
            var newHeaderSize = Math.max($('div.subtitles.reference .content').outerHeight(),
                                         $('div.subtitles.working .content').outerHeight());
            $('div.subtitles.reference .content').css('min-height', '' + newHeaderSize + 'px');
            $('div.subtitles.working .content').css('min-height', '' + newHeaderSize + 'px');
        };
        // TODO: what is the angularjs way to bind functions to DOM events?
        $( "div.subtitles .content" ).change($scope.keepHeaderSizeSync);
        $scope.adjustReferenceSize = function() {
            $scope.keepHeaderSizeSync();
            if($scope.referenceSubtitles.subtitleList.length() > 0 && ($scope.referenceSubtitles.subtitleList.length() == $scope.workingSubtitles.subtitleList.length())) {
                var $reference = $('div.subtitles.reference').first();
                var $working = $('div.subtitles.working').first();
                if($reference.height() < $working.height())
                    $reference.last().height($reference.last().height() + $working.height() - $reference.height() );
            }
        }

	$scope.copyTimingEnabled = function() {
            return ($scope.workingSubtitles.subtitleList.length() > 0 &&
                     $scope.referenceSubtitles.subtitleList.syncedCount > 0)
        }

        $scope.showUploadSubtitlesModal = function($event) {
            $scope.dialogManager.open('upload-subtitles');
            $event.stopPropagation();
            $event.preventDefault();
        };

        $scope.showShiftForwardModal = function($event) {
            $scope.dialogManager.open('shift-forward');
            $event.stopPropagation();
            $event.preventDefault();
        };

        $scope.showShiftBackwardModal = function($event) {
            $scope.dialogManager.open('shift-backward');
            $event.stopPropagation();
            $event.preventDefault();
        };

        // Required by ajax plugin but not present in our version of
        // jQuery
        jQuery.extend({
            handleError: function( s, xhr, status, e ) {
		// If a local callback was specified, fire it
		if ( s.error )
			s.error( xhr, status, e );
		// If we have some XML response text (e.g. from an AJAX call) then log it in the console
		else if(xhr.responseText)
			console.log(xhr.responseText);
	    },
            httpData: function( xhr, type, s ) {
                var ct = xhr.getResponseHeader("content-type"),
                         xml = type == "xml" || !type && ct && ct.indexOf("xml") >= 0,
                         script = type == "script" || !type && ct && ct.indexOf("script") >= 0,
                         json = type == "json" || !type && ct && ct.indexOf("json") >= 0,
                         data = xml ? xhr.responseXML : xhr.responseText;

                if ( xml && data.documentElement.tagName == "parsererror" )
                    throw "parsererror";

                // Allow a pre-filtering function to sanitize the response
                // s != null is checked to keep backwards compatibility
                if( s && s.dataFilter )
                    data = s.dataFilter( data, type );

                // If the type is "script", eval it in global context
                if ( script )
                    jQuery.globalEval( data );

                // Get the JavaScript object, if JSON is used.
                if ( json )
                    data = eval("(" + data + ")");

                return data;
            }
        });

        function authHeaders() {
            // authHeaders copied from subtitles/services.js.  We should
            // remove this as part of #1830

            var rv = {};
            // The following code converts the values of
            // EditorData.authHeaders into utf-8 encoded bytestrings to send
            // back to the server.  The unescape/encodeURIComponent part seems
            // pretty hacky, but it should work for all browsers
            // (http://monsur.hossa.in/2012/07/20/utf-8-in-javascript.html)
            for (var key in EditorData.authHeaders) {
                var val = EditorData.authHeaders[key];
                var utfVal = unescape(encodeURIComponent(val));
                rv[key] = utfVal;
            }
            return rv;
        }

        $scope.onCopyTimingClicked = function($event) {
            console.log('copy timing');
            $scope.dialogManager.openDialog('confirmCopyTiming', {
                continueButton: function() {
                    $scope.workingSubtitles.subtitleList.copyTimingsFrom($scope.referenceSubtitles.subtitleList);
                    $scope.$root.$emit('work-done');
                }
            });
            $event.stopPropagation();
            $event.preventDefault();
        };

        $scope.onClearTimingsClicked = function($event) {
            $scope.workingSubtitles.subtitleList.clearAllTimings();
            $scope.$root.$emit('work-done');
        };

        $scope.onClearTextClicked = function($event) {
            $scope.workingSubtitles.subtitleList.clearAllText();
            $scope.$root.$emit('work-done');
        };

        $scope.showDeleteEmptySubtitlesModal = function($event) {
            $scope.dialogManager.openDialog('confirmDeleteEmptySubtitles', {
                continueButton: $scope.deleteEmptySubtitles
            });
            $event.stopPropagation();
            $event.preventDefault();
        };

        $scope.deleteEmptySubtitles = function() {
            $scope.workingSubtitles.subtitleList.deleteEmptySubtitles();
            $scope.$root.$emit('work-done');
        };

        $scope.showTutorial = function($event) {
            $scope.toggleTutorial(true);
            $event.stopPropagation();
        };
        $scope.showResetModal = function($event) {
            $scope.dialogManager.openDialog('confirmChangesReset', {
                continueButton: $scope.resetToLastSavedVersion
            });
            $event.stopPropagation();
            $event.preventDefault();
        };

        $scope.resetToLastSavedVersion = function() {
            if($scope.workingSubtitles.versionNumber) {
                $scope.workingSubtitles.getSubtitles(EditorData.editingVersion.languageCode,
                    $scope.workingSubtitles.versionNumber);
            } else {
                $scope.workingSubtitles.initEmptySubtitles(
                    EditorData.editingVersion.languageCode, EditorData.baseLanguage);
            }
            $scope.$root.$emit('work-done');
        }

        $scope.displayedTitle = function() {
            return ($scope.workingSubtitles.getTitle() || 
                     $scope.referenceSubtitles.getTitle());
        }
        $scope.timeline = {
            shownSubtitle: null,
            currentTime: null,
            duration: null,
        };
        $scope.collab = {
            notes: EditorData.savedNotes
        };
        $scope.exitEditor = function() {
            $scope.analytics('editor', 'exit');
            $scope.exiting = true;
            $scope.releaseLock();
            $window.location = EditorData.redirectUrl;
        }
        $scope.exitToLegacyEditor = function() {
            $scope.analytics('editor', 'exit-to-legacy');
            $scope.exiting = true;
            $scope.releaseLock();
            $window.location = EditorData.oldEditorURL;
        }
        $scope.showDebugModal = function(evt) {
            $scope.dialogManager.open('debug');
            evt.preventDefault();
            evt.stopPropagation();
            return false;
        };
        $scope.onGuidelinesClicked = function($event) {
            $event.preventDefault();
            $event.stopPropagation();
            $scope.dialogManager.open('guidelines');
        }
        $scope.onPlaybackModeClicked = function($event) {
            $event.preventDefault();
            $event.stopPropagation();
            $scope.dialogManager.open('playback-mode');
        }
        $scope.onMoreControlsClicked = function($event) {
            $event.preventDefault();
            $event.stopPropagation();
            $scope.dialogManager.open('more-controls');
        }
        $scope.onTitleClicked = function($event) {
            $event.preventDefault();
            $event.stopPropagation();
            $scope.dialogManager.open('metadata');
        }
        // Hide the loading modal after we are done with bootstrapping
        // everything
        $scope.$evalAsync(function() {
            $scope.loadingFinished = true;
            $scope.toggleTutorial(EditorData.preferences.showTutorial);
        });
        // Overrides for debugging
        $scope.overrides = {
            forceSaveError: false
        };
    }]);

    /* AppController is large, so we split it into several components to
     * keep things a bit cleaner.  Each controller runs on the same scope.
     */


    /*
     * FIXME: this can probably be moved to a service to keep the app module
     * lean and mean.
     */
    module.controller("AppControllerLocking", ["$sce", "$scope", "$timeout", "$window", "EditorData", "LockService", function($sce, $scope, $timeout, $window, EditorData, LockService) {
        var regainLockTimer;

        $scope.minutesIdle = 0;

        $scope.releaseLock = function() {
            LockService.releaseLock($scope.videoId, 
                    EditorData.editingVersion.languageCode);
        }

        function regainLock() {
            return LockService.regainLock($scope.videoId,
                    EditorData.editingVersion.languageCode);
        }

        function userIdleTimeout() {
            $scope.minutesIdle++;

            if ($scope.minutesIdle >= USER_IDLE_MINUTES) {
                $scope.showIdleModal();
                $timeout.cancel(regainLockTimer);
            } else {
                startUserIdleTimer();
            }
        }

        function startUserIdleTimer() {
            $timeout(userIdleTimeout, 60 * 1000);
        }

        $scope.cancelUserIdleTimeout = function() {
            $timeout.cancel(userIdleTimeout);
        }

        function startRegainLockTimer() {
            var regainLockTimeout = function() {
                regainLock();
                regainLockTimer = $timeout(regainLockTimeout, 15 * 1000);
            };

            regainLockTimer = $timeout(regainLockTimeout, 15 * 1000);

        }

        function regainLockAfterIdle() {
            $scope.dialogManager.showFreezeBox(
                    $sce.trustAsHtml('Regaining lock&hellip;'));
            regainLock().then(function onSuccess(response) {
                $scope.dialogManager.closeFreezeBox();
                if (response.data.ok) {
                    $scope.minutesIdle = 0;
                    startRegainLockTimer();
                    startUserIdleTimer();
                } else {
                    $scope.showResumeSessionErrorModal();
                }
            }, function onError() {
                $scope.showResumeSessionErrorModal();
            });
        }
        $scope.showIdleModal = function () {
            var secondsUntilClosing = 120;
            
            function makeText() {
                return "You've been idle for more than " + USER_IDLE_MINUTES + " minutes. " + "To ensure no work is lost we will close your session in " + secondsUntilClosing + " seconds.";
            }

            function closeSessionTick() {
                if (--secondsUntilClosing <= 0) {
                    $scope.dialogManager.close();
                    $scope.showCloseSessionModal();
                } else {
                    $scope.dialogManager.updateDialogText(makeText());
                    closeSessionTimeout = $timeout(closeSessionTick, 1000);
                }
            }

            var closeSessionTimeout = $timeout(closeSessionTick, 1000);

            $scope.dialogManager.openDialog('sessionWillClose', {
                regainLock: function() {
                    if (closeSessionTimeout) {
                        $timeout.cancel(closeSessionTimeout);
                    }
                    regainLockAfterIdle();
                },
                closeEditor: $scope.exitEditor
            }, { text: makeText() });
        }

        $scope.showCloseSessionModal = function() {
            $scope.releaseLock();
            var dialogManager = $scope.dialogManager;

            dialogManager.openDialog('sessionEnded', {
                regainLock: regainLockAfterIdle,
                closeEditor: $scope.exitEditor
            });
        }

        $scope.showResumeSessionErrorModal = function() {
            $scope.dialogManager.open('resume-error');
        }

        startUserIdleTimer();
        startRegainLockTimer();
    }]);

    module.controller("AppControllerEvents", ["$scope", "VideoPlayer", function($scope, VideoPlayer) {
        $scope.isMac = navigator.platform.toUpperCase().indexOf('MAC') > -1;
        function insertAndEditSubtitle() {
            var sub = $scope.workingSubtitles.subtitleList.insertSubtitleBefore(null);
            $scope.currentEdit.start(sub);
        }

        // This function is to have the keyboard shortcut help
        // panel trigger same actions as keystrokes
        $scope.handleMouseKeyDown = function(keyString) {
            var evt = {
                ctrlKey: false,
                shiftKey: false,
                preventDefault: function() {},
                stopPropagation: function() {},
                target: {}
            }
            var keys = keyString.split('-');
            evt.keyCode = parseInt(keys[0]);
            for (var i = 1 ; i < keys.length ; i++) {
                if (keys[i] == "ctrl")
                    evt.ctrlKey = true;
                else if (keys[i] == "shift")
                    evt.shiftKey = true;
            }
            $scope.handleAppKeyDown(evt);
        }
        if($scope.isMac) {
            function ctrlOrCmd(evt) {
                return evt.metaKey;
            }
        } else {
            function ctrlOrCmd(evt) {
                return evt.ctrlKey;
            }
        }
        $scope.handleAppKeyDown = function(evt) {
            // Reset the lock timer.
	    var isDel = function(key) {
		return ((key === 46) || (key === 8));
	    };
	    var isAltPressed = function(evt) {
		return (evt.altKey || evt.metaKey);
	    };
            $scope.minutesIdle = 0;
            $scope.$root.$emit("user-action");
            if (evt.keyCode == 9 && !evt.shiftKey) {
                // Tab, Toggle playback
                if($scope.dialogManager.current()) {
                    // If a dialog is open, then don't mess with playback.  The user probably wants to navigate the form
                    return;
                }
                VideoPlayer.togglePlay();
            } else if (evt.keyCode === 9 && evt.shiftKey) {
                // Shift+Tab, go back 2 seconds
                if($scope.dialogManager.current()) {
                    // If a dialog is open, then don't mess with playback.  The user probably wants to navigate the form
                    return;
                }
                VideoPlayer.seek(VideoPlayer.currentTime() - 2000);
            } else if (evt.keyCode === 188 && evt.shiftKey && evt.ctrlKey) {
                // Control+Shift+Comma, go back 4 seconds
                VideoPlayer.seek(VideoPlayer.currentTime() - 4000);
            } else if (evt.keyCode === 190 && evt.shiftKey && evt.ctrlKey) {
                // Control+Shift+Period, go forward 4 seconds
                VideoPlayer.seek(VideoPlayer.currentTime() + 4000);
            } else if (evt.keyCode === 90 && ctrlOrCmd(evt) && !evt.altKey) {
                // Ctrl-Z -- undo
                if($scope.currentEdit.inProgress()) {
                    if($scope.currentEdit.undoAutoCreatedSubtitle($scope.workingSubtitles.subtitleList)) {
                        // Corner case: the user hit enter in typing mode to
                        // create a new subtitle, then hit Ctrl-Z.  We
                        // auto-undo the insert in this case.  Don't try to
                        // also undo the change before that.
                        $scope.$root.$emit('work-done');
                        return;
                    }
                    $scope.currentEdit.finish($scope.workingSubtitles.subtitleList);
                }
                if($scope.workingSubtitles.subtitleList.canUndo()) {
                    $scope.workingSubtitles.subtitleList.undo();
                    $scope.$root.$emit('work-done');
                }
            } else if ( (!$scope.isMac && evt.keyCode === 89 && evt.ctrlKey) ||
                        ($scope.isMac && evt.keyCode === 90 && evt.metaKey && evt.shiftKey)) {
                // Ctrl-Y -- redo
                if($scope.workingSubtitles.subtitleList.canRedo()) {
                    $scope.workingSubtitles.subtitleList.redo();
                    $scope.$root.$emit('work-done');
                }
            } else if (evt.keyCode === 73 && isAltPressed(evt) && evt.shiftKey) {
                // Alt+Shift+i, insert subtitle below
		if($scope.currentEdit.inProgress()) {
		    $scope.workingSubtitles.subtitleList.insertSubtitleBefore(
			$scope.workingSubtitles.subtitleList.nextSubtitle($scope.currentEdit.subtitle));
                }
            } else if (evt.keyCode === 73 && isAltPressed(evt)) {
                // Alt+i, insert subtitle above
		if($scope.currentEdit.inProgress()) {
		    $scope.workingSubtitles.subtitleList.insertSubtitleBefore(
			$scope.currentEdit.subtitle);
                }
            } else if (isDel(evt.keyCode) && isAltPressed(evt)) {
                // Alt+del, remove current subtitle
		if($scope.currentEdit.inProgress()){
                    var subtitleList = $scope.workingSubtitles.subtitleList;
                    var currentSubtitle = $scope.currentEdit.subtitle;
                    var nextSubtitle = subtitleList.nextSubtitle(currentSubtitle);
                    var prevSubtitle = subtitleList.prevSubtitle(currentSubtitle);
                    var replacement = nextSubtitle || prevSubtitle;

                    subtitleList.removeSubtitle(currentSubtitle);

                    // After removing current subtitle, move cursor and open text-area of adjacent subtitle
                    if (replacement){
                        // Tell the root scope that we're no longer editing, now.
                        $scope.currentEdit.finish(subtitleList);
                        $scope.currentEdit.start(replacement);
                        $scope.$root.$emit('scroll-to-subtitle', replacement);
                        evt.preventDefault();
                        evt.stopPropagation();
                   }
                   $scope.$root.$emit('work-done');
                }
            } else if (isAltPressed(evt) && ((evt.keyCode === 38) || (evt.keyCode === 40))) {
		var nextSubtitle;
		var subtitle = $scope.currentEdit.subtitle;
		var subtitleList = $scope.workingSubtitles.subtitleList;
		if(subtitle) {
		    if (evt.keyCode === 38)
			nextSubtitle = subtitleList.prevSubtitle(subtitle);
		    else
			nextSubtitle = subtitleList.nextSubtitle(subtitle);
		    if (nextSubtitle) {
			$scope.currentEdit.finish(subtitleList);
			$scope.currentEdit.start(nextSubtitle);
			$scope.$root.$emit('scroll-to-subtitle', nextSubtitle);
			evt.preventDefault();
			evt.stopPropagation();
		    }
		} else if ((evt.keyCode === 40) && (subtitleList.length() > 0)){
		    subtitle = $scope.workingSubtitles.subtitleList.firstSubtitle();
		    $scope.currentEdit.start(subtitle);
		}
	    } else if (evt.target.type == 'textarea') {
                $scope.$root.$emit('text-edit-keystroke');
                return;
	    }
		// Shortcuts that should be disabled while editing a subtitle
            else if (evt.keyCode === 32) {
                VideoPlayer.togglePlay();
                // Space: toggle play / pause.
            } else if ((evt.keyCode == 40) && ($scope.timelineShown)) {
                $scope.$root.$emit("sync-next-start-time");
            } else if ((evt.keyCode == 38) && ($scope.timelineShown)) {
                $scope.$root.$emit("sync-next-end-time");
            } else if ((evt.keyCode == 13) && (!$scope.timelineShown) && (!$scope.dialogManager.current())) {
                insertAndEditSubtitle();
            } else {
                return;
            }
            evt.preventDefault();
            evt.stopPropagation();
        };

        $scope.handleAppMouseMove = function(evt) {
            // Reset the lock timer.
            $scope.minutesIdle = 0;
        };

        $scope.handleAppMouseClick = function(evt) {
            // Reset the lock timer.
            $('#context-menu').hide();
            $scope.minutesIdle = 0;
            $scope.$root.$emit("user-action");
        };
        $scope.handleBadgeMouseClick = function(evt) {
            evt.stopPropagation();
        };
    }]);

    module.controller("AppControllerSubtitles", ["$scope", "$timeout", "EditorData", "SubtitleStorage", "CurrentEditManager", "SubtitleBackupStorage", "SubtitleVersionManager", function($scope, $timeout,
                EditorData, SubtitleStorage, CurrentEditManager,
                SubtitleBackupStorage, SubtitleVersionManager) {
        var video = EditorData.video;
        $scope.currentEdit = new CurrentEditManager();
        $scope.workingSubtitles = new SubtitleVersionManager(
            video, SubtitleStorage);
        $scope.referenceSubtitles = new SubtitleVersionManager(
            video, SubtitleStorage);
        var editingVersion = EditorData.editingVersion;

        if(editingVersion.versionNumber) {
            $scope.workingSubtitles.getSubtitles(editingVersion.languageCode,
                    editingVersion.versionNumber);
        } else {
            $scope.workingSubtitles.initEmptySubtitles(
                    editingVersion.languageCode, EditorData.baseLanguage);
        }

        $scope.submitUploadForm = function($event) {
            $scope.uploading = true;
            $scope.uploadError = false;
            var file = $('#subtitles-file-field')[0].files[0];
            var fileData = new FileReader();
            var sub_format = file.name.split('.').pop();
            fileData.onload = function(e) {
                SubtitleStorage.saveSubtitles(
                    fileData.result,
                    $scope.workingSubtitles.title,
                    $scope.duration,
                    $scope.workingSubtitles.description,
                    $scope.workingSubtitles.metadata,
                    null, "", sub_format, true).then(
                        function onSuccess(data, status, xhr) {
			    location.reload();
		        },
                        function onError(xhr, status, error) {
                            $scope.uploading = false;
                            $scope.uploadError = true;
		    });
	    };
            fileData.readAsText(file, "UTF-8");
            $event.stopPropagation();
            $event.preventDefault();
        };

        $scope.saveAutoBackup = function() {
            SubtitleBackupStorage.saveBackup(video.id,
                    $scope.workingSubtitles.language.code,
                    $scope.workingSubtitles.versionNumber,
                    $scope.workingSubtitles.subtitleList.toXMLString());
        }

        $scope.restoreAutoBackup = function() {
            var savedData = SubtitleBackupStorage.getBackup(video.id,
                    $scope.workingSubtitles.language.code,
                    editingVersion.versionNumber);
            $scope.workingSubtitles.subtitleList.loadXML(savedData);
            $scope.$root.$emit('work-done');
        }

        $scope.promptToRestoreAutoBackup = function() {
            $scope.dialogManager.openDialog('restoreAutoBackup', {
                restore: $scope.restoreAutoBackup,
                discard: SubtitleBackupStorage.clearBackup
            });
        }

        $scope.autoBackupNeeded = false;

        // Check if we have an auto-backup to restore
        if(SubtitleBackupStorage.hasBackup(video.id,
                $scope.workingSubtitles.language.code,
                editingVersion.versionNumber)) {
            $timeout($scope.promptToRestoreAutoBackup);
        }

        $scope.$root.$on('work-done', function() {
            $scope.autoBackupNeeded = true;
        });

        function handleAutoBackup() {
            if($scope.autoBackupNeeded) {
                $scope.saveAutoBackup();
                $scope.autoBackupNeeded = false;
            }
            $timeout(handleAutoBackup, 60 * 1000);
        }
        $timeout(handleAutoBackup, 60 * 1000);

        function watchSubtitleAttributes(newValue, oldValue) {
            if(newValue != oldValue) {
                $scope.$root.$emit('work-done');
            }
        }
        $scope.$watch('workingSubtitles.title', watchSubtitleAttributes);
        $scope.$watch('workingSubtitles.description', watchSubtitleAttributes);
        $scope.$watch('workingSubtitles.metadata', watchSubtitleAttributes,
                true);

    }]);

}).call(this);
