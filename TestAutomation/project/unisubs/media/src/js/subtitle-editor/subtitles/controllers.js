// Amara, universalsubtitles.org
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

    var module = angular.module('amara.SubtitleEditor.subtitles.controllers', []);

    module.controller('LanguageSelectorController', ["$scope", function($scope) {
        /**
         * This controller is responsible for the language and version selector
         * widget.  The widget allows the user to select a reference language and
         * version when translating subtitles into another language.
         *
         * The $scope contains 'languages' and 'versions'.  Each list is
         * represented in the UI as a <select> element.  The selected language or
         * version is stored on the $scope as a 'language' and 'version' model.
         *
         * Whenever the language selection is changed, we update the list of
         * versions.  When a new version is selected, we retrieve the subtitles
         * (either from memory or from the API via ajax) and display them in the
         * side panel.
         */

        /**
         * The second param will be either an int or the version data object,
         * depending if this is being set from the bootstrapped value or later
         * fetches.
         */
        $scope.versionNumber = null;
        $scope.currentVersion = null;
        $scope.versions = [];
        $scope.languageChanged = function() {
            if (!$scope.language) {
                return;
            }

            $scope.versions = _.sortBy($scope.language.versions, function(item) {
                return item.version_no;
            }).reverse();

            $scope.versionNumber = getInitialVersion();
            if($scope.versionNumber !== null) {
                loadSubtitles();
            } else {
                loadEmptySubtitles();
            }
        };


        function getInitialVersion() {
            // Get the version to select when a user first switches to a
            // language.
            if($scope.versions.length > 0) {
                return $scope.versions[0].version_no.toString();
            } else {
                return null;
            }
        }
        $scope.findVersion = function(versionNumber) {
            for(var i = 0; i < $scope.versions.length; i++) {
                if($scope.versions[i].version_no == versionNumber) {
                    return $scope.versions[i];
                }
            }
            return null;
        }
        $scope.versionNumberChanged = function() {
            loadSubtitles();
        };

        function loadSubtitles() {
            /* loadSubtitles gets called a bunch of times as we are populating
             * the dropdowns.  Wrap it in a $evalAsync so that we wait for things
             * to settle before actually trying to load them.
             */
            $scope.$evalAsync(function() {
                var newVersion = $scope.findVersion($scope.versionNumber);
                if(!newVersion || newVersion == $scope.currentVersion) {
                    return;
                }

                $scope.currentVersion = newVersion;
                $scope.referenceSubtitles.getSubtitles(
                    $scope.language.code, newVersion.version_no);
                $scope.adjustReferenceSize();
            });
        }

        function loadEmptySubtitles() {
            $scope.currentVersion = null;
            $scope.referenceSubtitles.initEmptySubtitles(
                    $scope.language.code);
            $scope.adjustReferenceSize();
        }

        function pickInitialLanguage() {
            if(!$scope.languages) {
                return null;
            }
            // try to pick the primary audio language
            for(var i = 0; i < $scope.languages.length; i++) {
                var language = $scope.languages[i];
                if(language.isPrimaryAudioLanguage) {
                    return language;
                }
            }
            // fall back on picking the first language
            return $scope.languages[0];
        }

        $scope.setInitialDisplayLanguage = function(allLanguages) {
            $scope.languages = _.filter(allLanguages, function(l) {
                return l.versions.length > 0;
            })
            $scope.language = pickInitialLanguage();
            $scope.languageChanged();
        }

        $scope.$watch('language', function(newValue, oldValue) {
            $scope.languageChanged();
        });
        $scope.$watch('versionNumber', $scope.versionNumberChanged);
    }]);

    module.controller('WorkingSubtitlesController', ["$scope", "DomWindow", "$filter", "VideoPlayer", "SubtitleSoftLimits", function($scope, DomWindow, $filter, VideoPlayer, SubtitleSoftLimits) {
        /**
         * Handles the subtitles the user is working on.
         */
        var willSync = {start: null, end:null};
        var subtitleList = $scope.workingSubtitles.subtitleList;

        function updateSyncHelpers() {
            var startSub = null, endSub = null;
            if(willSync.start !== null) {
                startSub = willSync.start;
            }
            if(willSync.end !== null) {
                endSub = willSync.end;
            }
            $scope.positionSyncHelpers(startSub, endSub);
        }

        $scope.$root.$on('will-sync-changed', function(evt, newWillSync) {
            willSync = newWillSync;
            updateSyncHelpers();
        });

        $scope.$on('subtitle-list-changed', updateSyncHelpers);
        $scope.$watch('currentEdit.inProgress()', function(value) {
            if(value) {
                trackMouseDown();
            } else {
                DomWindow.offDocumentEvent('mousedown.subtitle-edit');
            }

        });

        $scope.splitCurrentSubtitle = function() {
            var currentSubtitle = $scope.currentEdit.subtitle;
            if(!$scope.canSplitSubtitle(currentSubtitle)) {
                return;
            }
            var splitInfo = $scope.calcSubtitleSplit(currentSubtitle);
            $scope.currentEdit.finish(subtitleList);
            subtitleList.splitSubtitle(currentSubtitle, splitInfo.first, splitInfo.second);
            $scope.$root.$emit('work-done');
        }

        function trackMouseDown() {
            // Disconnect any previous handlers to keep sanity
            DomWindow.offDocumentEvent('mousedown.subtitle-edit');
            DomWindow.onDocumentEvent('mousedown.subtitle-edit', function(evt) {
                var subtitle = $scope.currentEdit.subtitle;
                var li = $scope.getSubtitleRepeatItem(subtitle);
                var clicked = $(evt.target);
                var textarea = $('textarea.subtitle-edit', li);
                if(clicked[0] != textarea[0] &&
                    !clicked.hasClass('subtitle-overlay-text') &&
                    !clicked.hasClass('info-tray') &&
                    clicked.parents('.info-tray').length == 0) {
                    $scope.currentEdit.finish(subtitleList);
                }
            });
        }

        function insertAndStartEdit(before, region, options) {
            var newSub = subtitleList.insertSubtitleBefore(before, region);
            $scope.currentEdit.start(newSub, options);
        }

	$scope.showWarning = function(subtitle, type, data) {
	    if(subtitle && $scope.warningsShown)
		return subtitle.hasWarning(type, data);
	    return false;
	};

        $scope.warningMessages = SubtitleSoftLimits.warningMessages;

        $scope.onSubtitleClick = function(evt, subtitle, action) {
            var madeChange = false;
            switch(action) {
                case 'jump-to':
	            $scope.$root.$emit('jump-to-subtitle', subtitle);
                    break;

                case 'note-time':
                    $scope.$root.$emit('set-note-heading', $filter('displayTime')(subtitle.startTime));
                    $scope.$root.$emit('set-focus', "newNoteFocus");
                    break;

                case 'insert':
                    insertAndStartEdit(subtitle);
                    madeChange = true;
                    break;

                case 'insert-top':
                    insertAndStartEdit(subtitle, subtitle.region);
                    madeChange = true;
                    break;

                case 'insert-down':
                    insertAndStartEdit(subtitleList.nextSubtitle(subtitle), subtitle.region);
                    madeChange = true;
                    break;

                case 'changeParagraph':
                    subtitleList.updateSubtitleParagraph(subtitle);
                    madeChange = true;
                    break;

                case 'remove':
                    if($scope.currentEdit.isForSubtitle(subtitle)) {
                        $scope.currentEdit.finish();
                    }
                    subtitleList.removeSubtitle(subtitle);
                    madeChange = true;
                    break;

                case 'edit':
                    if(!$scope.currentEdit.isForSubtitle(subtitle)) {
                        var caret = DomWindow.caretPos();
                        $scope.currentEdit.start(subtitle, {initialCaretPos: caret});
                        madeChange = true;
                    }
                    break;
            }
            if(madeChange) {
                evt.preventDefault();
                $scope.$root.$emit('work-done');
            }
        }

        $scope.newSubtitleClicked = function(evt) {
            var lastSubtitle = subtitleList.lastSubtitle();
            insertAndStartEdit(null, lastSubtitle ? lastSubtitle.region : undefined);
            evt.preventDefault();
            $scope.$root.$emit('work-done');
        }

        $scope.onEditKeydown = function(evt) {
            var subtitle = $scope.currentEdit.subtitle;

            var isAltPressed = function(evt) {
                return (evt.altKey || evt.metaKey);
            };

            if (evt.keyCode === 13 && evt.ctrlKey) {
                // Ctrl-enter splits the subtitles
                $scope.splitCurrentSubtitle();
            } else if (evt.keyCode === 13 && !evt.shiftKey) {
                // Enter without shift finishes editing
                var nextSubtitle = subtitleList.nextSubtitle(subtitle);
                $scope.currentEdit.finish(subtitleList);
                if(nextSubtitle === null) {
                    if(!$scope.timelineShown) {
                        $scope.currentEdit.appendAndStart(subtitleList);
                    }
                } else {
                    $scope.currentEdit.start(nextSubtitle);
                    $scope.$root.$emit('scroll-to-subtitle', nextSubtitle);
                }
                evt.preventDefault();
                evt.stopPropagation();
            } else if (evt.keyCode === 27) {
                // Escape cancels editing
                $scope.currentEdit.finish(subtitleList);
                $scope.$root.$emit('work-done');
                evt.preventDefault();
                evt.stopPropagation();
            }
        }
        
        $scope.bottomState = function() {
            if($scope.currentEdit.inProgress()) {
                return 'edit-help'
            } else if($scope.timelineShown) {
                return 'add-button'
            } else {
                return 'type-shortcuts-help'
            }
        }
    }]);

    module.controller("SubtitleMetadataController", ["$scope", function($scope) {
        $scope.currentSubtitles = {
            title: $scope.workingSubtitles.getTitle(),
            description: $scope.workingSubtitles.getDescription(),
            metadata: $scope.workingSubtitles.getMetadata()
        };
        var backupSubtitles = _.clone($scope.currentSubtitles);

        $scope.update = function(subtitles) {
            $scope.workingSubtitles.title = subtitles.title;
            $scope.workingSubtitles.description = subtitles.description;
            $scope.workingSubtitles.metadata = _.clone(subtitles.metadata);
            backupSubtitles = _.clone(subtitles);
            $scope.dialogManager.close();
        };
 
        $scope.reset = function() {
            $scope.currentSubtitles = _.clone(backupSubtitles);
            $scope.dialogManager.close();
        };
    }]);
}).call(this);
