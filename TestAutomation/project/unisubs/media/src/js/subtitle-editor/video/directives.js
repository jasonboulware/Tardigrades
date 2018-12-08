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
    var module = angular.module('amara.SubtitleEditor.video.directives', []);

    // var SUBTITLE_MIME_TYPE = 'application/vnd.pculture.amara.subtitle';
    // Can't use the mime type we want because of an Edge bug (https://developer.microsoft.com/en-us/microsoft-edge/platform/issues/8007622/).
    // So, (ab)use a known mime type.
    var SUBTITLE_MIME_TYPE = 'text/plain';

    module.directive('volumeBar', ["VideoPlayer", function(VideoPlayer) {
        return function link($scope, elem, attrs) {
            elem = $(elem);
            var canvas = elem[0];
            var width = 40;
            var barHeight = 95;
            var topHeight = 9;
            var bottomHeight = 9;
            var paddingTop = 10;
            var paddingBottom = 5;
            var slices = $('div', elem);

            function drawBar() {
                var drawHeight = Math.round($scope.videoState.volume *
                    barHeight);
                if(drawHeight <= bottomHeight) {
                    slices.eq(0).height(0);
                    slices.eq(1).height(0);
                    slices.eq(2).height(drawHeight);
                    slices.eq(2).css('background-position',
                        'center ' + drawHeight + 'px');
                } else if(drawHeight <= barHeight - bottomHeight) {
                    slices.eq(0).height(0);
                    slices.eq(1).height(drawHeight - bottomHeight);
                    slices.eq(2).height(bottomHeight);
                    slices.eq(2).css('background-position', 'center 0');
                } else {
                    slices.eq(0).height(drawHeight -
                            (barHeight - bottomHeight));
                    slices.eq(1).height(barHeight - bottomHeight - topHeight);
                    slices.eq(2).height(bottomHeight);
                    slices.eq(2).css('background-position', 'center 0');
                }
                slices.eq(0).css('margin-top',
                        (barHeight - drawHeight) + 'px');
            }

            $scope.$watch('videoState.volume', drawBar);

            function setVolumeFromPageY(pageY) {
                var barBottom = elem.offset().top + barHeight + paddingTop;
                var volume = (barBottom - pageY) / barHeight;
                volume = Math.max(0.0, Math.min(1, volume));
                VideoPlayer.setVolume(volume);
            }

            $scope.onVolumeMouseDown = function(event) {
                setVolumeFromPageY(event.pageY);
                $(document).on('mousemove.volume-track', function(event) {
                    setVolumeFromPageY(event.pageY);
                }).on('mouseup.volume-track', function(event) {
                    $(document).off('.volume-track');
                }).on('mouseleave.volume-track', function(event) {
                    $(document).off('.volume-track');
                });
                event.preventDefault();
            };

            drawBar();
        }
    }]);
    module.directive('progressBar', ["VideoPlayer", function(VideoPlayer) {
        return function link($scope, elem, attrs) {
            elem = $(elem);
            var sliceLeft = $('div.slice-left div', elem);
            var sliceRight = $('div.slice-right div', elem);
            var sliceMid = $('div.slice-mid div', elem);
            var leftWidth = 14;
            var rightWidth = 14;

            function drawBar() {
                if($scope.videoState.currentTime === null ||
                    $scope.videoState.duration === null) {
                    return;
                }
                var progress = ($scope.videoState.currentTime /
                    $scope.videoState.duration);
                var barWidth = Math.round(elem.width())
                var drawWidth = Math.round(barWidth * progress);
                if(drawWidth <= leftWidth) {
                    sliceLeft.width(drawWidth);
                    sliceMid.width(0);
                    sliceRight.width(0);
                } else if(drawWidth <= barWidth - leftWidth) {
                    sliceLeft.css('width', '100%');
                    sliceMid.width(drawWidth - leftWidth);
                    sliceRight.width(0);
                } else {
                    sliceLeft.css('width', '100%');
                    sliceMid.css('width', '100%');
                    sliceRight.width(drawWidth - (barWidth - leftWidth));
                }
            }

            drawBar();
            $scope.$watch('videoState.currentTime', drawBar);
            $scope.$watch('videoState.duration', drawBar);

            $scope.$root.$on('jump-to-subtitle', function(evt, subtitle) {
		if(subtitle.isSynced())
                    VideoPlayer.seek(subtitle.startTime);
	    });

            $scope.$root.$on('jump-to-time', function(evt, displayTime) {
		var time = 0;
		var cents = displayTime.split('.');
		if (cents.length == 2) {
		    time += parseInt(cents[1]);
		    var seconds = cents[0].split(':');
		    if (seconds.length > 1) {
			var s = 0;
			for (var i = 0 ; i < seconds.length ; i++)
			    s += parseInt(seconds[i]) * Math.pow(60, seconds.length -1 - i);
			time += 100*s;
			VideoPlayer.seek(time * 10);
		    }
		}
	    });

            function setProgressFromPageX(pageX) {
                if($scope.videoState.duration === null) {
                    return;
                }
                var deltaX = pageX - elem.offset().left;
                var progress = deltaX / elem.width();
                progress = Math.max(0, Math.min(1, progress));

                VideoPlayer.seek(progress * $scope.videoState.duration);
            }

            $scope.onProgressMouseDown = function(event) {
                setProgressFromPageX(event.pageX);
                $(document).on('mousemove.progress-track', function(event) {
                    setProgressFromPageX(event.pageX);
                }).on('mouseup.progress-track', function(event) {
                    $(document).off('.progress-track');
                }).on('mouseleave.progress-track', function(event) {
                    $(document).off('.progress-track');
                });
                event.preventDefault();
            };
        }

    }]);

    module.directive('videoView', [ function() {
        // Handles view code to show the video.  Right now this means showing the current subtitle

        function watchShownSubtitlePosition($scope, overlays, text) {
            var topOverlay = overlays.filter('.top');
            var bottomOverlay = overlays.filter('.bottom');

            function recalcSubtitlePosition() {
                if(!$scope.currentSubtitle) {
                    bottomOverlay.append(text);
                } else if($scope.currentSubtitle.region == 'top') {
                    topOverlay.append(text);
                } else {
                    bottomOverlay.append(text);
                }
            }

            $scope.$watch('currentSubtitle.region', recalcSubtitlePosition);
            $scope.workingSubtitles.subtitleList.addChangeCallback(function(change) {
                recalcSubtitlePosition();
            });
        }
        return function link($scope, elem, attrs) {
            var overlays = elem.find('.subtitle-overlay');
            var text = elem.find('.subtitle-overlay-text');

            watchShownSubtitlePosition($scope, overlays, text);

            text.attr('draggable', true);
            text.on('dragstart', function(evt) {
                var subtitle = $scope.currentSubtitle;
                if(!subtitle) {
                    return;
                }
                var dataTransfer = evt.originalEvent.dataTransfer;
                dataTransfer.setData('text/plain', text.text());
                if(!subtitle.isDraft) {
                    dataTransfer.setData(SUBTITLE_MIME_TYPE, subtitle.id);
                } else {
                    dataTransfer.setData(SUBTITLE_MIME_TYPE, subtitle.storedSubtitle.id);
                }
                dataTransfer.effectAllowed = 'copyMove';
                dataTransfer.dropEffect = 'move';
                overlays.addClass('dragging');
                // var overlay = $(this.parentNode);
                // overlay.data('dragcount', 1);
                // overlay.addClass('will-drop');
            }).on('dragend', function(evt) {
                overlays.removeClass('dragging');
                overlays.removeClass('will-drop');
            });
            overlays.data('dragcount', 0);
            overlays.on('dragenter', function(evt) {
                var dataTransfer = evt.originalEvent.dataTransfer;
                if(_.contains(dataTransfer.types, SUBTITLE_MIME_TYPE)) {
                    var elt = $(this);
                    elt.data('dragcount', elt.data('dragcount') + 1);
                    dataTransfer.dropEffect = 'move';
                    $(this).addClass('will-drop');
                    evt.preventDefault();
                }
            }).on('dragover', function(evt) {
                var dataTransfer = evt.originalEvent.dataTransfer;
                if(_.contains(dataTransfer.types, SUBTITLE_MIME_TYPE)) {
                    var elt = $(this);
                    dataTransfer.dropEffect = 'move';
                    evt.preventDefault();
                }
            }).on('dragleave', function(evt) {
                var elt = $(this);
                var newCount = elt.data('dragcount') - 1;
                elt.data('dragcount', newCount);
                if(newCount == 0) {
                    $(this).removeClass('will-drop');
                }
            }).on('drop', function(evt) {
                var dataTransfer = evt.originalEvent.dataTransfer;
                var subtitleId = dataTransfer.getData(SUBTITLE_MIME_TYPE);
                var sub = $scope.workingSubtitles.subtitleList.getSubtitleById(subtitleId);
                if(sub) {
                    var region = calcRegionForDrop($(this));
                    $scope.workingSubtitles.subtitleList.updateSubtitleRegion(sub, region);
                    $scope.$root.$emit('work-done');
                }
                evt.preventDefault();
            });

            function calcRegionForDrop(elt) {
                if(elt.hasClass('top')) {
                    return 'top';
                } else {
                    return null;
                }
            }
        }
    }]);
})();

