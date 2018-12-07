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

    var module = angular.module('amara.SubtitleEditor.timeline.controllers', []);

    module.controller('TimelineController', ["$scope", "$timeout", "VideoPlayer", "MIN_DURATION", function($scope, $timeout, VideoPlayer, MIN_DURATION) {
        // Controls the scale of the timeline, currently we just set this to
        // 1.0 and leave it.
        $scope.scale = 1.0;
        // Video time info.
        $scope.currentTime = $scope.duration = null;
        // Subtitle at currentTime, or null.
        $scope.subtitle = null;
        $scope.showUpcomingUnsyncedSubtitle = false;
        /* Subtitles that we will sync when the user hits the up/down arrows.
         *
         * Contains the following properties:
         *    start - subtitle whose startTime will be synced
         *    end - subtitle whose endTime will be synced
         */

        var willSync = { start: null, end: null};
        var lastTimeReturned = null;
        var lastTimeReturnedAt = null;
        var lastTime = null;

        // Handle animating the timeline.  We don't use the timeupdate event
        // from popcorn because it doesn't fire granularly enough.
        var timeoutPromise = null;
        function startTimer() {
            if(timeoutPromise === null) {
                var delay = 30; // aim for 30 FPS or so
                timeoutPromise = $timeout(handleTimeout, delay, false);
            }
        }

        function cancelTimer() {
            if(timeoutPromise !== null) {
                $timeout.cancel(timeoutPromise);
                timeoutPromise = null;
            }
        }

        function handleTimeout() {
            updateTimeline();
            timeoutPromise = null;
            startTimer();
        }

        function updateTime() {
            var newTime = VideoPlayer.currentTime();
            // On the youtube player, popcorn only updates the time every 250
            // ms, which is not enough granularity for our animation.  Try to
            // get more granularity by starting a timer of our own.
            if(VideoPlayer.isPlaying()) {
                if(lastTimeReturned === newTime) {
                    var timePassed = Date.now() - lastTimeReturnedAt;
                    // If lots of time has bassed since the last new time, it's
                    // possible that the video is slowing down for some reason.
                    // Don't adjust the time too much.
                    timePassed = Math.min(timePassed, 500);
                    $scope.currentTime = newTime + timePassed;
                } else {
                    $scope.currentTime = newTime;
                    lastTimeReturnedAt = Date.now();
                    lastTimeReturned = newTime;
                }
            } else {
                $scope.currentTime = newTime;
                // Unset lastTimeReturned and lastTimeReturnedAt, we don't
                // want to tweak the time when the video is paused
                lastTimeReturned = lastTimeReturnedAt = null;
            }

            // If we adjust the time with the code above, then get a new time
            // from popcorn, it's possible that the time given will be less
            // that our adjusted time.  Try to fudge things a little so that
            // time doesn't go backwards while we're playing.
            if(lastTime !== null && $scope.currentTime < lastTime &&
                $scope.currentTime > lastTime - 250) {
                $scope.currentTime = lastTime;
            }
            lastTime = $scope.currentTime;
            $scope.timeline.currentTime = $scope.currentTime;
        }

        function calcWillSync() {
            var rv = { start: null, end: null};

            if($scope.currentTime === null) {
                return rv;
            }
            var time = $scope.currentTime;
            var subtitleList = $scope.workingSubtitles.subtitleList;
            var nextIndex = subtitleList.indexOfFirstSubtitleAfter(time);
            if(nextIndex >= 0) {
                /* We are in the range of synced subtitles */
                var next = subtitleList.subtitles[nextIndex];
                rv.start = next;
                if(next.isAt(time)) {
                    rv.end = next;
                } else if(nextIndex > 0) {
                    rv.end = subtitleList.subtitles[nextIndex-1];
                } else {
                    rv.end = null;
                }
                return rv;
            }

            var firstUnsynced = subtitleList.firstUnsyncedSubtitle();
            if(firstUnsynced == null) {
                /* We are past the last synced subtitle, but there are no
                 * unsynced ones.
                 */
                rv.start = null;
                rv.end = subtitleList.lastSyncedSubtitle();
                return rv;
            }

            if(firstUnsynced.startTime < 0) {
                // The first unsynced subtitle needs a start time
                rv.start = firstUnsynced;
                rv.end = subtitleList.lastSyncedSubtitle();
            } else {
                // The first unsynced subtitle has a start time set.  If the
                // user syncs the start time, then we will set the start time
                // for the second unsynced subtitle.
                rv.end = firstUnsynced;
                var nextUnsynced = subtitleList.secondUnsyncedSubtitle();
                if(nextUnsynced == null) {
                    rv.start = null;
                } else {
                    rv.start = nextUnsynced;
                }
            }
            return rv;
        }

        function updateWillSync() {
            var newWillSync = calcWillSync();
            if(willSync.start != newWillSync.start ||
                willSync.end != newWillSync.end) {
                willSync = newWillSync;
                $scope.$root.$emit('will-sync-changed', willSync);
            }
        }

        function unsyncedShown() {
            var lastSynced = $scope.workingSubtitles.subtitleList.lastSyncedSubtitle();
            return (!lastSynced || lastSynced.endTime < $scope.currentTime);
        }

        function updateUpcomingSubtitleSticker() {
            if (unsyncedShown()) {
                var s = $scope.workingSubtitles.subtitleList.secondUnsyncedSubtitle();
            } else {
                var s = $scope.workingSubtitles.subtitleList.firstUnsyncedSubtitle();
            }
            if (s) {
                // This is not good data binding but is kept consistent
                // with placement of subs on the timeline.
                // Using bind-html, we would keep the formatting.
                var span = $('span.upcomingUnsyncedSubtitleText');
                span.html(s.content());
                $scope.showUpcomingUnsyncedSubtitle = true;
            } else {
                $scope.showUpcomingUnsyncedSubtitle = false;
            }
        }

        function updateTimeline(redrawSubtitleOptions) {
            updateTime();
            updateWillSync();
            updateUpcomingSubtitleSticker();
            $scope.redrawCanvas();
            $scope.redrawSubtitles(redrawSubtitleOptions);
        }

        function scrollToSubtitle(subtitle) {
            $scope.$root.$emit('scroll-to-subtitle', subtitle);
        }

        $scope.$root.$on('video-update', function() {
            $scope.duration = VideoPlayer.duration();
            $scope.timeline.duration = $scope.duration;
            updateTimeline();
            if(VideoPlayer.isPlaying()) {
                startTimer();
            } else {
                cancelTimer();
            }
        });
        $scope.$root.$on("work-done", function() {
            updateTimeline({forcePlace: true});
        });

        $scope.$root.$on('dialog-opened', function() {
            $scope.hideContextMenu();
        });

        $scope.$root.$on('sync-next-start-time', function($event) {
            var subtitleList = $scope.workingSubtitles.subtitleList;
            var syncTime = $scope.currentTime;
            var subtitle = willSync.start;
            if(subtitle === null) {
                if(willSync.end !== null && !willSync.end.isSynced()) {
                    /* Special case: the user hit the down arrow when only 1
                     * subtitle was left and it had a start time set.  In this
                     * case, set the end time for that subtile
                     */
                    subtitleList.updateSubtitleTime(willSync.end,
                        willSync.end.startTime, syncTime);
                    scrollToSubtitle(willSync.end);
                    $scope.$root.$emit("work-done");
                }
                return;
            }
            /* Check to see if we're setting the start time for the second
             * unsynced subtitle.  In this case, we should also set the end
             * time for the first.
             */

            var prev = subtitleList.prevSubtitle(subtitle);
            if(prev !== null && !prev.isSynced()) {
                // Ensure that we give the previous subtitle MIN_DURATION
                syncTime = Math.max(syncTime, prev.startTime + MIN_DURATION);
                subtitleList.updateSubtitleTime(prev, prev.startTime,
                    syncTime);
            } else if(subtitle.endTime != -1) {
                syncTime = Math.min(syncTime, subtitle.endTime -
                        MIN_DURATION);
            }

            subtitleList.updateSubtitleTime(subtitle, syncTime,
                subtitle.endTime);

            scrollToSubtitle(subtitle);
            $scope.$root.$emit("work-done");
        });
        // Sets the end of a subtitle at current position. If onlyUnsync is true
        // it only does it if the current endTime is unsynced, ie partially 
        // synced subtitle
        var setEndSubtitle = function($event, onlyUnsync) {
            var subtitleList = $scope.workingSubtitles.subtitleList;
            var subtitle = willSync.end;
            if ((subtitle === null) || (onlyUnsync && (subtitle.endTime != -1))) {
                return;
            }
            var syncTime = Math.max($scope.currentTime, subtitle.startTime +
                MIN_DURATION);
            subtitleList.updateSubtitleTime(subtitle, subtitle.startTime,
                syncTime);
            scrollToSubtitle(subtitle);
            $scope.$root.$emit("work-done");
        };
        var setEndSubtitleOnlyUnsync = function($event) {
            setEndSubtitle($event, true);
        };
        var setEndSubtitleAll = function($event) {
            setEndSubtitle($event, false);
        };
        // If playback is paused, currently partially synced subtitled gets
        // entirely synced to avoid having half-synced subs in the timeline
        $scope.$root.$on('video-playback-changes', setEndSubtitleOnlyUnsync);
        $scope.$root.$on('sync-next-end-time', setEndSubtitleAll);
    }]);
}).call(this);
