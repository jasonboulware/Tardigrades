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

(function() {

    var module = angular.module('amara.SubtitleEditor.video.controllers', []);

    module.controller('VideoController', ['$scope', '$sce', 'EditorData', 'VideoPlayer', 'PreferencesService', function($scope, $sce, EditorData, VideoPlayer, PreferencesService) {
        $scope.subtitleText = null;
        $scope.showSubtitle = false;

        $scope.videoState = {
            loaded: false,
            playing: false,
            currentTime: null,
            duration: null,
            volumeBarVisible: false,
            volume: 0.0,
        }

        $scope.$root.$on("video-update", function() {
            $scope.videoState.loaded = true;
            $scope.videoState.playing = VideoPlayer.isPlaying();
            $scope.videoState.currentTime = VideoPlayer.currentTime();
            $scope.videoState.duration = VideoPlayer.duration();
            $scope.videoState.volume = VideoPlayer.getVolume();
        });
        $scope.$root.$on("video-time-update", function(evt, currentTime) {
            $scope.videoState.currentTime = currentTime;
        });
        $scope.$root.$on("video-volume-update", function(evt, volume) {
            $scope.videoState.volume = volume;
        });
        $scope.$root.$on("user-action", function() {
            $scope.toggleTutorial(false);
            if ($scope.hideTutorialNextTime) {
                PreferencesService.tutorialShown();
                $scope.hideTutorialNextTime = false;
                $scope.hideNextTime();
            }
        });

        $scope.playPauseClicked = function(event) {
            VideoPlayer.togglePlay();
            event.preventDefault();
        };

        $scope.volumeToggleClicked = function(event) {
            $scope.volumeBarVisible = !$scope.volumeBarVisible;
            event.preventDefault();
        };

        function recalcCurrentSubtitle() {
            if($scope.currentEdit.inProgress()) {
                setCurrentSubtitle($scope.currentEdit.subtitle);
            } else {
                setCurrentSubtitle($scope.timeline.shownSubtitle);
            }
        }
        function setCurrentSubtitle(subtitle) {
            $scope.currentSubtitle = subtitle;
            if(subtitle) {
                $scope.showSubtitle = true;
                $scope.subtitleText = $sce.trustAsHtml(subtitle.content());
            } else {
                $scope.showSubtitle = false;
                $scope.subtitleText = '';
            }
        }

        $scope.$watch('currentEdit.subtitle.content()', recalcCurrentSubtitle);
        $scope.$watch('timeline.shownSubtitle', recalcCurrentSubtitle);

        $scope.$root.$on('subtitle-selected', function($event, scope) {
            if(scope.subtitle.isSynced()) {
                VideoPlayer.playChunk(scope.startTime, scope.duration());
            }
            setCurrentSubtitle(scope.subtitle);
        });

        // use evalAsync so that the video player gets loaded after we've
        // rendered all of the subtitles.
        $scope.$evalAsync(function() {
              VideoPlayer.init();
        });

    }]);

    module.controller('PlaybackModeController', ['$scope', '$timeout', 'VideoPlayer', 'EditorData', 'PreferencesService',
                      function($scope, $timeout, VideoPlayer, EditorData, PreferencesService) {
        function ModeHandler() {}
        ModeHandler.prototype = {
            onActivate: function() {},
            onDeactivate: function() {},
            onTextEditKeystroke: function() {},
            onVideoPlaybackChanges: function() {}
        }

        function MagicModeHandler() {}
        MagicModeHandler.prototype = Object.create(ModeHandler.prototype);
        _.extend(MagicModeHandler.prototype, {
            keystrokeTimeout: null,
            continuousTypingTimeout: null,
            magicPauseStartTime: -1,
            anticipatePauseStartTime: -1,
            state: 'inactive', // inactive, anticipating-pause, magic-paused

            cancelKeystrokeTimeout: function() {
                if(this.keystrokeTimeout !== null) {
                    $timeout.cancel(this.keystrokeTimeout);
                    this.keystrokeTimeout = null;
                }
            },
            cancelContinuousTypingTimeout: function() {
                if(this.continuousTypingTimeout !== null) {
                    $timeout.cancel(this.continuousTypingTimeout);
                    this.continuousTypingTimeout = null;
                }
            },
            reset: function(reason) {
                this.state = 'inactive';
                this.cancelKeystrokeTimeout();
                this.cancelContinuousTypingTimeout();
                this.magicPauseStartTime = -1;
                this.anticipatePauseStartTime = -1;
            },
            startAnticipatingPause: function() {
                this.anticipatePauseStartTime = VideoPlayer.currentTime();

                var self = this;
                self.continuousTypingTimeout = $timeout(function() {
                    // At least 4 seconds have elapsed while the user is continuously typing
                    self.continuousTypingTimeout = null;
                    self.startMagicPause();
                }, self.continuousTypingTimeoutDuration);

                self.continueAnticipatingPause();
            },
            continueAnticipatingPause: function() {
                if(!VideoPlayer.isPlaying()) {
                    this.reset('video paused externally while anticipating magic pause');
                    return;
                }

                this.state = 'anticipating-pause';

                var self = this;
                self.cancelKeystrokeTimeout();
                self.keystrokeTimeout = $timeout(function() {
                    self.keystrokeTimeout = null;
                    self.reset(self.keystrokeTimeoutDuration.toString() + ' ms have elapsed without a text edit keystroke');
                }, self.keystrokeTimeoutDuration);
            },
            startMagicPause: function() {
                if(!VideoPlayer.isPlaying()) {
                    // We have been paused by the user or some external piece of code
                    this.reset('video paused externally just before magic pause started');
                    return;
                }

                // If we're more than half a second away from the expected pause time,
                // assume we have been seeked by the user or some external piece of code.
                // 
                // NOTE: This is a little bit ugly. It solves the problem, but if we do subsecond seeks
                // in external code during a magic pause, this may cause unexpected behavior.
                //
                // That being said, we will probably have to modify this code if there's a use case
                // which involves sub-second seeking during a magic pause.
                //
                // The alternative is to truly differentiate between user initiated video update events,
                // and those initiated by external code.  And in that case, we'd have to ignore non-user
                // initiated events generated by calling the VideoPlayer API from within this mode handler.
                var currentTime = VideoPlayer.currentTime();
                var expectedTime = this.anticipatePauseStartTime + this.continuousTypingTimeoutDuration;
                var error = Math.abs(expectedTime - currentTime);
                if(error > 500) {
                    this.reset('video was seeked externally');
                    return;
                }

                this.state = 'magic-paused';
                VideoPlayer.pause();
                this.magicPauseStartTime = VideoPlayer.currentTime();
                this.continueMagicPause();
            },
            continueMagicPause: function() {
                var self = this;

                self.cancelKeystrokeTimeout();
                self.keystrokeTimeout = $timeout(function() {
                    // At least 1 second has elapsed without an edit keystroke
                    self.keystrokeTimeout = null;

                    // If we haven't been unpaused and the video time is exactly the magic pause start time,
                    // then the magic pause completed without user or external code intervention.
                    // So we can safely seek backwards.
                    var deltaTime = Math.abs(VideoPlayer.currentTime() - self.magicPauseStartTime);
                    if(!VideoPlayer.isPlaying() && deltaTime < 100) {
                        VideoPlayer.seek(self.magicPauseStartTime - self.resumeRewindAmount);
                        VideoPlayer.play();
                    }

                    self.reset('successfully resumed from magic pause');
                }, self.keystrokeTimeoutDuration);
            },

            onActivate: function() {
                // This mode has just been activated. Return to the initial state.
                this.reset();

                // TODO: Values from user preferences
                // TODO: make sure to watch these values & hook them up to the UI
                this.keystrokeTimeoutDuration = 1000;
                this.continuousTypingTimeoutDuration = 4000;
                this.resumeRewindAmount = 3000;
            },
            onDeactivate: function() {
                this.reset();
            },
            onTextEditKeystroke: function() {
                switch(this.state) {
                    case 'inactive':
                        this.startAnticipatingPause();
                        break;
                    case 'anticipating-pause':
                        this.continueAnticipatingPause();
                        break;
                    case 'magic-paused':
                        this.continueMagicPause();
                        break;
                }
            }
        });

        function StandardModeHandler() {}
        StandardModeHandler.prototype = Object.create(ModeHandler.prototype);

        function BeginnerModeHandler() {}
        BeginnerModeHandler.prototype = Object.create(ModeHandler.prototype);
        _.extend(BeginnerModeHandler.prototype, {
            playbackTimeout: null,
            playbackTimeoutStartTime: -1,
            playbackTimeoutDuration: 4000,

            cancelPlaybackTimeout: function() {
                if(this.playbackTimeout !== null) {
                    $timeout.cancel(this.playbackTimeout);
                }
            },

            onActivate: function() {
                this.playbackTimeoutDuration = 4000;
            },
            onDeactivate: function() {
                this.cancelPlaybackTimeout();
            },
            onVideoPlaybackChanges: function() {
                if(VideoPlayer.isPlaying()) {
                    var self = this;

                    this.playbackTimeoutStartTime = VideoPlayer.currentTime();
                    this.playbackTimeout = $timeout(function() {
                        self.playbackTimeout = null;

                        var expectedTime = self.playbackTimeoutStartTime + self.playbackTimeoutDuration;
                        var deltaTime = Math.abs(expectedTime - VideoPlayer.currentTime());
                        if(deltaTime < 500) {
                            VideoPlayer.pause();
                        }
                    }, this.playbackTimeoutDuration);
                } else {
                    this.cancelPlaybackTimeout();
                }
            }
        });

        // Map playback mode id strings to modes
        var playbackModes = {};
        $.each(EditorData.playbackModes, function(index, mode) {
            playbackModes[mode.idStr] = mode;
        });

        // Map playback mode ids to mode handlers
        var modeHandlers = {};
        modeHandlers[playbackModes.magic.id] = new MagicModeHandler();
        modeHandlers[playbackModes.standard.id] = new StandardModeHandler();
        modeHandlers[playbackModes.beginner.id] = new BeginnerModeHandler();

        function setStagePlaybackMode() {
            if (typeof $scope.timelineShown  === "undefined") {
                return;
            }
            if ($scope.timelineShown) {
                $scope.stagePlaybackMode = playbackModes.standard;
            } else {
                $scope.stagePlaybackMode = $scope.playbackMode;
            }
        }

        // Set the view's playbackMode based on preferences data from the backend
        var initialPlaybackModeId = EditorData.preferences.playbackModeId;
        $.each(EditorData.playbackModes, function(index, mode) {
            if(mode.id === initialPlaybackModeId) {
                $scope.playbackMode = mode;
                setStagePlaybackMode();
            }
        });

        var currentModeHandler = modeHandlers[$scope.playbackMode.id];
        currentModeHandler.onActivate();

        $scope.$root.$on('text-edit-keystroke', function($event) {
            currentModeHandler.onTextEditKeystroke();
        });

        $scope.$root.$on('video-playback-changes', function($event) {
            currentModeHandler.onVideoPlaybackChanges();
        });

        $scope.$watch('timelineShown', function(newShown, oldShown) {
            setStagePlaybackMode();
        });

        $scope.$watch('playbackMode', function(newMode, oldMode) {
            if(newMode != oldMode) {
                setStagePlaybackMode();
                // Save the new playbackMode preference server-side
                PreferencesService.setPlaybackMode(newMode.id);
            }
        });

        $scope.$watch('stagePlaybackMode', function(newMode, oldMode) {
            VideoPlayer.pause();
            currentModeHandler.onDeactivate();
            currentModeHandler = modeHandlers[newMode.id];
            currentModeHandler.onActivate();
        });
    }]);
}).call(this);
