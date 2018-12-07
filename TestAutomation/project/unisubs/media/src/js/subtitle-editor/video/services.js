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

    var module = angular.module('amara.SubtitleEditor.video.services', []);


    module.factory('VideoData', ["$http", "EditorData", function($http, EditorData) {
        var getVideoDurationAPIURL = function(videoId) {
            return ('/api/videos/' + videoId + '/duration');
        };
        function authHeaders() {
            var rv = {};
            for (var key in EditorData.authHeaders) {
                var val = EditorData.authHeaders[key];
                var utfVal = unescape(encodeURIComponent(val));
               rv[key] = utfVal;
            }
            return rv;
        }
        return {
            updateVideoDuration: function(duration) {
               duration = Math.round(duration / 1000);
		if (isNaN(parseInt(EditorData.video.duration))) {
                    var url = getVideoDurationAPIURL(EditorData.video.id);
                    $http({
                        method: 'PUT',
                        headers: authHeaders(),
                        url: url,
                        data: {'duration': duration}
                    }).then(function(response) {
                        EditorData.video.duration = duration;
                    });
               }
           }
        };
    }]);

    module.factory('VideoPlayer', ["$rootScope", "SubtitleStorage", "EditorData", "VideoData", function($rootScope, SubtitleStorage, EditorData, VideoData) {
        var videoURLs = [];
        var pop = null;
        var playing = false;

        function emitSignal(signalName, data) {
            var phase = $rootScope.$$phase;
            if(phase != '$apply' && phase != '$digest') {
                $rootScope.$apply(function() {
                    $rootScope.$emit(signalName, data);
                });
            } else {
                $rootScope.$emit(signalName, data);
            }
        }
        function routeEvents() {
            $rootScope.$on("video-loadedmetadata", function() {
               VideoData.updateVideoDuration(getDuration());
           });
        }
        function getDuration() {
                return Math.round(pop.duration() * 1000);
        }

        function handlePopcornEvents() {
            // Handle popcorn events
            pop.on('canplay', function() {
                emitSignal('video-update');
            }).on('playing', function() {
                wasPlaying = playing;
                playing = true;
                if (!wasPlaying) emitSignal('video-playback-changes');
                emitSignal('video-update');
            }).on('pause', function() {
                playing = false;
                emitSignal('video-playback-changes');
                emitSignal('video-update');
            }).on('ended', function() {
                playing = false;
                emitSignal('video-update');
            }).on('durationchange', function() {
                emitSignal('video-update');
            }).on('loadedmetadata', function() {
                emitSignal('video-loadedmetadata');
            }).on('seeked', function() {
                emitSignal('video-update');
            }).on('timeupdate', function() {
                emitSignal('video-time-update',
                    Math.round(pop.currentTime() * 1000));
            }).on('volumeupdate', function() {
                emitSignal('video-volume-update', pop.volume());
            });
        }

        // private methods
        function removeAllTrackEvents() {
            var trackEvents = pop.getTrackEvents();
            for (var i = 0; i < trackEvents.length; i++) {
                pop.removeTrackEvent(trackEvents[i].id);
            }
        };

        // Public methods
        return {
            init: function() {
                videoURLs = SubtitleStorage.getVideoURLs();
                pop = window.Popcorn.amara('#video', videoURLs, EditorData.video.primaryVideoURLType, {
                    controls: false,
                });
                handlePopcornEvents();
                routeEvents();
            },
            play: function() {
                pop.play();
            },
            pause: function() {
                pop.pause();
            },
            seek: function(time) {
                if(time < 0) {
                    time = 0;
                } else if (time > this.duration()) {
                    time = this.duration();
                }
                pop.currentTime(time / 1000);
            },
            togglePlay: function() {
                if (pop.paused()) {
                    pop.play();
                } else {
                    pop.pause();
                }
            },
            currentTime: function() {
                return Math.round(pop.currentTime() * 1000);
            },
            duration: function() {
                return getDuration();
            },
            isPlaying: function() {
                return playing;
            },
            getVolume: function() {
                return pop.volume();
            },
            setVolume: function(volume) {
                pop.volume(volume);
                // For some players (vimeo), popcorn doesn't send the
                // volumeupdate event.  So let's send it manually here.
                $rootScope.$emit('video-volume-update', volume);
            },
            playChunk: function(start, duration) {
                // Play a specified amount of time in a video, beginning at
                // 'start', and then pause.

                pop.pause();

                // Remove any existing cues that may interfere.
                removeAllTrackEvents();

                if (start < 0) {
                    start = 0;
                }
                pop.currentTime(start / 1000);
                pop.cue((start + duration) / 1000, function() {
                    pop.pause();
                });
                pop.play();
            },
        };
    }]);
}).call(this);
