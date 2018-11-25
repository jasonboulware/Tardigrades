
/*
 * Amara, universalsubtitles.org
 *
 * Copyright (C) 2018 Participatory Culture Foundation
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see
 * http://www.gnu.org/licenses/agpl-3.0.html.
 */


var angular = angular || null;

(function() {
    var module = angular.module('amara.SubtitleEditor.shifttime', []);

    module.controller("ShiftForwardController", ['$scope', 'formatTime', function($scope, formatTime) {
        function getLastSubtitle() {
            return $scope.workingSubtitles.subtitleList.lastSyncedSubtitle();
        }

        function getStartTime() {
            if($scope.subsToShift == 'all') {
                return 0;
            } else {
                return $scope.startTime;
            }
        }

        $scope.validateForm = function() {
            var lastSubtitle = getLastSubtitle();
            var startTime = getStartTime();
            $scope.dataValid = false;
            $scope.helpTextWarning = '';
            if(isNaN($scope.amount) || isNaN(startTime)) {
                $scope.helpText = gettext('An invalid time was entered.');
                $scope.helpTextError = true;
            } else if($scope.amount == 0) {
                $scope.helpText = gettext('Shift subtitles forward in bulk by a set amount of time.  This feature is useful when you edit the video and insert a new segment after already creating subtitles.');
                $scope.helpTextError = false;
            } else if(!lastSubtitle) {
                $scope.helpText = gettext('No subtitles to shift.');
                $scope.helpTextError = true;
            } else if(lastSubtitle.startTime < $scope.startTime) {
                $scope.helpText = gettext('Start time is after last subtitle.');
                $scope.helpTextError = true;
            } else {
                if(startTime > 0) {
                    var helpTextTemplate = gettext('Shift subtitles starting at %(start_time)s forward by %(amount)s.');
                } else {
                    var helpTextTemplate = gettext('Shift all subtitles forward by %(amount)s.');
                }
                $scope.helpText = interpolate(helpTextTemplate, {
                    start_time: formatTime(startTime),
                    amount: formatTime($scope.amount)
                }, true);
                if(lastSubtitle.startTime + $scope.amount > $scope.timeline.duration) {
                    $scope.helpTextWarning = gettext('Shift amount would move the last subtitle past the end of the video.');
                }
                $scope.helpTextError = true;
                $scope.helpTextError = false;
                $scope.dataValid = true;
            }
        }

        $scope.onShiftClick = function($event) {
            $scope.workingSubtitles.subtitleList.shiftForward(getStartTime(), $scope.amount);
            $scope.$root.$emit('work-done');
            $scope.dialogManager.close();

            $event.preventDefault();
            $event.stopPropagation();
        };

        function reset() {
            $scope.subsToShift = 'all';
            $scope.startTime = 0;
            $scope.amount = 0;
            $scope.validateForm();
        }
        $scope.$root.$on('dialog-opened', function(evt, dialogName) {
            if(dialogName == 'shift-forward') {
                reset();
            }
        });
        reset();
    }]);
    module.controller("ShiftBackwardController", ['$scope', 'formatTime', function($scope, formatTime) {
        $scope.validateForm = function() {
            $scope.dataValid = false;
            $scope.helpTextWarning = '';

            if(isNaN($scope.startTime) || isNaN($scope.endTime)) {
                $scope.helpText = gettext('An invalid time was entered.');
                $scope.helpTextError = true;
            } else if($scope.endTime == 0) {
                $scope.helpText = gettext('Delete all subtitles in a time range, and shift subtitles afterwards back by the duration.  This feature is useful when you edit the video and delete a segment after already creating subtitles.');
                $scope.helpTextError = false;
            } else if(!$scope.workingSubtitles.subtitleList.lastSyncedSubtitle()) {
                $scope.helpText = gettext('No subtitles to shift.');
                $scope.helpTextError = true;
            } else if($scope.endTime <= $scope.startTime) {
                $scope.helpText = gettext('Start time is after end time.');
                $scope.helpTextError = true;
            } else {
                var helpTextTemplate = gettext('Delete subtitles between %(start_time)s and %(end_time)s.  Shift subtitles after that back by %(amount)s.');
                $scope.helpTextError = true;
                $scope.helpText = interpolate(helpTextTemplate, {
                    start_time: formatTime($scope.startTime, {longFormat: true}),
                    end_time: formatTime($scope.endTime, {longFormat: true}),
                    amount: formatTime($scope.endTime - $scope.startTime),
                }, true);
                if($scope.startTime > $scope.timeline.duration) {
                    $scope.helpTextWarning = gettext('Warning: Start time exceeds the video duration.');
                }
                $scope.helpTextError = false;
                $scope.dataValid = true;
            }
        }

        $scope.onShiftClick = function($event) {
            $scope.workingSubtitles.subtitleList.shiftBackward($scope.startTime, $scope.endTime-$scope.startTime);
            $scope.$root.$emit('work-done');
            $scope.dialogManager.close();

            $event.preventDefault();
            $event.stopPropagation();
        };

        function reset() {
            $scope.startTime = 0;
            $scope.endTime = 0;
            $scope.validateForm();
        }
        $scope.$root.$on('dialog-opened', function(evt, dialogName) {
            if(dialogName == 'shift-backward') {
                reset();
            }
        });
        reset();
    }]);
}).call(this);
