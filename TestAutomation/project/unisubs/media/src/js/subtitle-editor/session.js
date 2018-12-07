// Amara, universalsubtitles.org
//
// Copyright (C) 2014 Participatory Culture Foundation
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
    var module = angular.module('amara.SubtitleEditor.session', []);

    module.controller('SessionBackend', ["$scope", "$q", "EditorData", "SubtitleStorage", function($scope, $q, EditorData, SubtitleStorage) {
        /* SessionControllerBackend handles the low-level details for
         * SessionController.  This includes things like saving the subtitles,
         * approving/recting tasks, etc.
         */
        $scope.sessionBackend = {
            saveSubtitles: function(action) {
                return SubtitleStorage.saveSubtitles(
                    $scope.workingSubtitles.subtitleList.toXMLString(),
                    $scope.workingSubtitles.title,
                    Math.floor($scope.timeline.duration / 1000),
                    $scope.workingSubtitles.description,
                    $scope.workingSubtitles.metadata,
                    null, action, 'dfxp', false).then(this.afterSaveSubtitles);
            },
            performAction: function(action) {
                return SubtitleStorage.performAction(action);
            },
            afterSaveSubtitles: function(response) {
                $scope.workingSubtitles.versionNumber = response.data.version_number;
                return true;
            },
            subtitlesComplete: function() {
                return ($scope.workingSubtitles.subtitleList.isComplete() &&
			($scope.workingSubtitles.subtitleList.firstInvalidTiming() == undefined));
            },
        };
    }]);

    module.controller('SessionController', ["$scope", "$sce", "$q", "$window", "EditorData", function($scope, $sce, $q, $window, EditorData) {
        /*
         * SessionController handles the high-level issues involved with
         * sending the user's work back to the server.  SessionController
         * works on the AppController's scope and creates a session object
         * there.  That object is responsible for:
         *   - Saving, approving/rejecting tasks, exiting, etc.
         *   - Tracking user changes to the subtitles
         *   - Popping up confirmation dialogs if the user wants to exit while
         *     there are outstanding changes
         *   - Popping up freeze boxes while we are waiting for the server to
         *     respond to our requests.
         */

        function saveSubtitles(action) {
            $scope.analytics('editor', 'save', action);
            if($scope.overrides.forceSaveError) {
                var deferred = $q.defer();
                deferred.reject('Simulated Error');
                return deferred.promise;
             } else if($scope.session.subtitlesChanged) {
                return $scope.sessionBackend.saveSubtitles(action).then(function() {
                    $scope.session.subtitlesChanged = false;
                });
            } else {
                // No changes need to be saved, just perform the action
                return $scope.sessionBackend.performAction(action);
            }
        }

        $scope.session = {
            exit: function() {
                if(!$scope.session.subtitlesChanged) {
                    $scope.exitEditor();
                } else {
                    $scope.dialogManager.openDialog('unsavedWork', {
                        'exit': $scope.exitEditor
                    });
                }
            },
            exitToLegacyEditor: function() {
                if(!$scope.session.subtitlesChanged) {
                    $scope.exitToLegacyEditor();
                } else {
                    $scope.dialogManager.openDialog('legacyEditorUnsavedWork', {
                        'discardChangesAndOpenLegacyEditor': $scope.exitToLegacyEditor
                    });
                }
            },
            allowSaveDraft: function() {
                return _.any(EditorData.actions, function(action) {
                    return action.name == 'save-draft';
                });
            },
            forbidAction: function(action) {
                if ((action.requires_translated_metadata_if_enabled === true) &&
                    $scope.translating() &&
                    (($scope.workingSubtitles.title == "") ||
                     (($scope.referenceSubtitles.description.length > 0) && ($scope.workingSubtitles.description == "")) ||
                     (("speaker-name" in $scope.referenceSubtitles.metadata) &&
                      ($scope.workingSubtitles.metadata["speaker-name"].trim() == ""))) &&
                    EditorData.teamAttributes &&
                    (EditorData.teamAttributes.features.indexOf('require_translated_metadata') > -1))
                    return {'forbid': true, 'tooltip': 'Title and description must be translated'};
		return {'forbid': false};
	    },
            saveDraft: function() {
                var msg = $sce.trustAsHtml('Saving&hellip;');
                $scope.dialogManager.showFreezeBox(msg);
                saveSubtitles('save-draft').then(function onSuccess() {
                    $scope.dialogManager.closeFreezeBox();
                    $scope.dialogManager.openDialog('changesSaved', {
                        exit: $scope.exitEditor
                    });
                }, function onError() {
                    $scope.dialogManager.closeFreezeBox();
                    $scope.dialogManager.open('save-error');
                });
            },
        };

        var visibleActions = _.filter(EditorData.actions, function(action) {
            return action.name != 'save-draft';
        });

        $scope.actions = _.map(visibleActions, function(action) {
            var sessionAction = {
                label: action.label,
                class: action.class,
                tooltip: function() {
                    var forbid = $scope.session.forbidAction(action);
                    if (forbid.forbid) return forbid.tooltip;
                    return "";
                },
                canPerform: function() {
                    if ($scope.session.forbidAction(action).forbid) return false;
                    if(action.requireSyncedSubtitles === true) {
                        return $scope.sessionBackend.subtitlesComplete();
                    } else {
                        return true;
                    }
                },
                perform: function() {
                    var msg = $sce.trustAsHtml(action.in_progress_text + '&hellip;');
                    $scope.dialogManager.showFreezeBox(msg);
                    saveSubtitles(action.name).then(
                        function onSuccess() {
                            $scope.dialogManager.closeFreezeBox();
                            $scope.exitEditor();
                        },
                        function onError() {
                            $scope.dialogManager.closeFreezeBox();
                            $scope.dialogManager.open('save-error');
                        }
                    );
                }
            };

            return sessionAction;
        });

        $scope.onExitClicked = function($event) {
            $event.preventDefault();
            $event.stopPropagation();
            $scope.session.exit();
        }

        $scope.onLegacyEditorClicked = function($event) {
            $event.preventDefault();
            $event.stopPropagation();
            $scope.session.exitToLegacyEditor();
        }

        $scope.onSaveDraftClicked = function($event) {
            $event.preventDefault();
            $event.stopPropagation();
            $scope.session.saveDraft();
        }

        $scope.$root.$on('work-done', function() {
            $scope.session.subtitlesChanged = true;
        });

        $window.onbeforeunload = function() {
            if($scope.session.subtitlesChanged && !$scope.exiting) {
              return "You have unsaved work";
            } else {
              return null;
            }
        };
    }]);
}).call(this);
