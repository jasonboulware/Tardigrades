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
    var module = angular.module('amara.SubtitleEditor.timeline.directives', []);

    /*
     * Define a couple of helper classes to handle updating the timeline
     * elements.  Our basic strategy is to make a really wide div, so that we
     * have a bit of a buffer, then scroll the div instead of re-rendering
     * everything.
     */
    function durationToPixels(duration, scale) {
        // by default 1 pixel == 10 ms.  scope.scale can adjusts that,
        // although there isn't any interface for it.
        return Math.floor(scale * duration / 10);
    }

    function pixelsToDuration(width, scale) {
        return width * 10 / scale;
    }

    function BufferTimespan(scope) {
        /* Stores the time range of the entire div.*/
        this.duration = 60000; // Buffer 1 minute of subtitles.
        // Position the buffer so that most of it is in front of the current
        // time.
        if(scope.currentTime !== null) {
            var currentTime = scope.currentTime;
        } else {
            var currentTime = 0;
        }
        this.startTime = currentTime - this.duration / 4;
        // We don't want to buffer negative times, but do let startTime go to
        // -0.5 seconds because the left side of the "0" is slightly left of
        // time=0.
        if(this.startTime < -500) {
            this.startTime = -500;
        }
        this.endTime = this.startTime + this.duration;
        if(scope.duration !== null) {
            this.endTime = Math.min(this.endTime, scope.duration)
        }
        this.width = durationToPixels(this.duration, scope.scale);
    }

    function VisibleTimespan(scope, width, deltaMS) {
        /* Stores the portion of the video time that is displayed in the
         * timeline.
         */

        this.scope = scope;
        this.scale = scope.scale;
        this.duration = pixelsToDuration(width, this.scale);
        if(scope.currentTime !== null) {
            var currentTime = scope.currentTime;
        } else {
            var currentTime = 0;
        }
        this.startTime = currentTime - this.duration / 2;
        if(deltaMS) {
            this.startTime += deltaMS;
        }
        this.endTime = this.startTime + this.duration;
    }

    VisibleTimespan.prototype.fitsInBuffer = function(bufferTimespan) {
        if(this.startTime < bufferTimespan.startTime && bufferTimespan.startTime > 0) {
            return false;
        }
        if(this.endTime > bufferTimespan.endTime && bufferTimespan.endTime < this.scope.duration) {
            return false;
        }
        return true;
    }

    VisibleTimespan.prototype.positionDiv = function(bufferTimespan, div) {
        var deltaTime = this.startTime - bufferTimespan.startTime;
        div.css('left', -durationToPixels(deltaTime, this.scale) + 'px');
    }

    module.directive('timelineTiming', ["displayTimeSecondsFilter", function(displayTimeSecondsFilter) {
        return function link(scope, elem, attrs) {
            var canvas = $(elem);
            var canvasElt = elem[0];
            var container = canvas.parent();
            var width=0, height=65; // dimensions of the canvas
            var containerWidth = container.width();
            var bufferTimespan = null;
            var visibleTimespan = null;

            function drawSecond(ctx, xPos, t) {
                // draw the second text on the timeline
                ctx.fillStyle = '#686868';
                var text = displayTimeSecondsFilter(t);
                var metrics = ctx.measureText(text);
                var x = xPos - (metrics.width / 2);
                ctx.fillText(text, x, 60);
            }
            function drawTics(ctx, xPos, duration) {
                // draw the tic marks between seconds
                // duration represents the amount of time to draw tics for in ms
                ctx.strokeStyle = '#686868';
                var divisions = duration / 250;
                var step = durationToPixels(250, scope.scale);
                ctx.lineWidth = 1;
                ctx.beginPath();
                for(var i = 1; i < divisions; i++) {
                    var x = Math.floor(0.5 + xPos + step * i);
                    x += 0.5;
                    ctx.moveTo(x, 60);
                    if(i == 2) {
                        // draw an extra long tic for the 50% mark;
                        ctx.lineTo(x, 45);
                    } else {
                        ctx.lineTo(x, 50);
                    }
                }
                ctx.stroke();
            }
            function drawCanvas() {
                var ctx = canvasElt.getContext("2d");
                ctx.clearRect(0, 0, width, height);
                ctx.font = (height / 5) + 'px Open Sans';

                var startTime = bufferTimespan.startTime;
                var endTime = bufferTimespan.endTime;
                if(startTime < 0) {
                    startTime = 0;
                }
                if(scope.duration) {
                    endTime = Math.min(endTime, scope.duration);
                }

                for(var t = startTime; t < endTime; t += 1000) {
                    var xPos = durationToPixels(t - bufferTimespan.startTime,
                            scope.scale);
                    drawSecond(ctx, xPos, t);
                    drawTics(ctx, xPos, Math.min(1000, endTime-t));
                }
            }

            function makeNewBuffer() {
                bufferTimespan = new BufferTimespan(scope);
                if(bufferTimespan.width != width) {
                    // Resize the width of the canvas to match the buffer
                    width = bufferTimespan.width;
                    canvasElt.width = width;
                    canvas.css('width', width + 'px');
                }
                drawCanvas();
            }

            // Put redrawCanvas in the scope, so that the controller can call
            // it.
            scope.redrawCanvas = function(deltaMS) {
                visibleTimespan = new VisibleTimespan(scope, containerWidth,
                        deltaMS);
                if(bufferTimespan === null ||
                    !visibleTimespan.fitsInBuffer(bufferTimespan) ||
                    bufferTimespan.endTime > scope.duration) {
                    makeNewBuffer();
                }
                visibleTimespan.positionDiv(bufferTimespan, canvas);
            };
            $(window).resize(function() {
                containerWidth = (container.width() || container.parent().width());
                scope.redrawCanvas();
            });
            scope.$on('timeline-drag', function(evt, deltaMS) {
                scope.redrawCanvas(deltaMS);
            });

            // Okay, finally done defining functions, let's draw the canvas.
            scope.redrawCanvas();
        }
    }]);

    module.directive('timelineSubtitles', ["VideoPlayer", "MIN_DURATION", "DEFAULT_DURATION", function(VideoPlayer, MIN_DURATION,
                DEFAULT_DURATION) {
        return function link(scope, elem, attrs) {
            var timelineDiv = $(elem);
            var container = timelineDiv.parent();
            var containerWidth = container.width();
            var timelineDivWidth = 0;
            var bufferTimespan = null;
            var visibleTimespan = null;
            var dragCounter = 0; // increments 1 for each drag we do.  Used to create unique changeGroups for updateSubtitleTimes
            // Map XML subtitle nodes to the div we created to show them
            var timelineDivs = {}
            // Store the DIV for the unsynced subtitle
            var unsyncedDiv = null;
            var unsyncedSubtitle = null;

            scope.hideContextMenu = function() {
                var contextMenu = $('#context-menu');
                contextMenu.hide();
            }

            function handleDragLeft(context, deltaMS) {
                context.startTime = context.initialStartTime + deltaMS;
                if (context.startTime < context.minStartTime) {
                    if (context.startTime > context.minStartTimePush) {
                        context.previousSubtitleEndTimeNew = context.startTime;
                    } else {
                        context.startTime = context.minStartTime;
                        context.previousSubtitleEndTimeNew = context.minStartTime;
                    }
                }
                if(context.startTime > context.endTime - MIN_DURATION) {
                    context.startTime = context.endTime - MIN_DURATION;
                }
            }

            function handleDragRight(context, deltaMS) {
                context.endTime = context.initialEndTime + deltaMS;
                if(context.maxEndTime !== null &&
                        context.endTime > context.maxEndTime) {
                            if (context.endTime < context.maxEndTimePush) {
                                context.nextSubtitleStartTimeNew = context.endTime;
                            } else {
                                context.nextSubtitleStartTimeNew = context.maxEndTime;
                                context.endTime = context.maxEndTime;
                            }
                        }
                if(context.endTime < context.startTime + MIN_DURATION) {
                    context.endTime = context.startTime + MIN_DURATION;
                }
            }

            function handleDragMiddle(context, deltaMS) {
                context.startTime = context.initialStartTime + deltaMS;
                context.endTime = context.initialEndTime + deltaMS;

                if(context.startTime < context.minStartTime) {
                    context.startTime = context.minStartTime;
                    context.endTime = (context.startTime +
                            context.subtitle.duration());
                }
                if(context.endTime > context.maxEndTime) {
                    context.endTime = context.maxEndTime;
                    context.startTime = (context.endTime -
                            context.subtitle.duration());
                }

            }

            function subtitleList() {
                return scope.workingSubtitles.subtitleList;
            }

            function handleMouseDown(evt) {
                scope.handleAppMouseClick(evt);
                if (evt.which == 3) return;
                if(!scope.canSync) {
                    return false;
                }
                VideoPlayer.pause();
                var subtitle = evt.data.subtitle;
                var dragHandler = evt.data.dragHandler;
                var context = {
                    subtitle: subtitle,
                    startTime: subtitle.startTime,
                    endTime: subtitle.endTime,
                    initialStartTime: subtitle.startTime,
                    initialEndTime: subtitle.endTime
                }
                if(!subtitle.isDraft) {
                    var storedSubtitle = subtitle;
                    var div = timelineDivs[storedSubtitle.id];
                } else {
                    var storedSubtitle = subtitle.storedSubtitle;
                    var div = unsyncedDiv;
                }

                if(!div) {
                    return false;
                }

                var changeGroup = 'timeline-drag-' + dragCounter++;

                var previousDiv = null, nextDiv = null; 
                var nextSubtitle = subtitleList().nextSubtitle(storedSubtitle);
                context.nextSubtitleStartTimeOr = context.nextSubtitleStartTimeNew = null;
                if(nextSubtitle && nextSubtitle.isSynced()) {
                    nextDiv = timelineDivs[nextSubtitle.id];
                    context.nextSubtitleStartTimeOr = nextSubtitle.startTime;
                    context.nextSubtitleStartTimeNew = null;
                    context.maxEndTime = nextSubtitle.startTime;
                    context.maxEndTimePush = nextSubtitle.endTime - MIN_DURATION;
                } else if(scope.duration !== null) {
                    context.maxEndTime = scope.duration;
                    context.maxEndTimePush = null;
                } else {
                    context.maxEndTime = 10000000000000;
                    context.maxEndTimePush = null;
                }
                var prevSubtitle = subtitleList().prevSubtitle(storedSubtitle);
                context.prevSubtitleEndTimeOr = context.prevSubtitleEndTimeNew = null;
                if(prevSubtitle) {
                    previousDiv = timelineDivs[prevSubtitle.id];
                    context.prevSubtitleEndTimeOr = prevSubtitle.endTime;
                    context.minStartTime = prevSubtitle.endTime;
                    context.minStartTimePush = prevSubtitle.startTime + MIN_DURATION;
                } else {
                    context.minStartTime = 0;
                    context.minStartTimePush = null;
                }

                var initialPageX = evt.pageX;

                function updateSubtitleTimes() {
                    var changes = [];
                    changes.push({
                        subtitle: storedSubtitle,
                        startTime: context.startTime,
                        endTime: context.endTime,
                    });

                    if (context.previousSubtitleEndTimeNew) {
                        changes.push({
                            subtitle: prevSubtitle,
                            startTime: prevSubtitle.startTime,
                            endTime: context.previousSubtitleEndTimeNew
                        });
                    }

                    if (context.nextSubtitleStartTimeNew) {
                        changes.push({
                            subtitle: nextSubtitle,
                            startTime: context.nextSubtitleStartTimeNew,
                            endTime: nextSubtitle.endTime
                        });
                    }

                    subtitleList().updateSubtitleTimes(changes, changeGroup);
                    scope.$root.$emit("work-done");
                    scope.$root.$digest();
                }

                $(document).on('mousemove.timelinedrag', function(evt) {
                    var deltaX = evt.pageX - initialPageX;
                    var deltaMS = pixelsToDuration(deltaX, scope.scale);
                    dragHandler(context, deltaMS);
                    updateSubtitleTimes();
                }).on('mouseup.timelinedrag', function(evt) {
                    $(document).off('.timelinedrag');
                    updateSubtitleTimes();
                }).on('mouseleave.timelinedrag', function(evt) {
                    $(document).off('.timelinedrag');
                    updateSubtitleTimes();
                });
                // need to prevent the default event from happening so that the
                // browser's DnD code doesn't mess with us.
                return false;
            }

            function makeDivForSubtitle(subtitle) {
                var div = $('<div/>', {class: 'subtitle'});
                var span = $('<span/>', {class: 'timeline-subtitle-text'});
                span.html(subtitle.content());
                var left = $('<a href="#" class="handle left"></a>');
                var right = $('<a href="#" class="handle right"></a>');
                left.on('mousedown',
                        {subtitle: subtitle, dragHandler: handleDragLeft},
                        handleMouseDown);
                right.on('mousedown',
                        {subtitle: subtitle, dragHandler: handleDragRight},
                        handleMouseDown);
                span.on('mousedown',
                        {subtitle: subtitle, dragHandler: handleDragMiddle},
                        handleMouseDown);
                div.append(left);
                div.append(span);
                div.append(right);
                timelineDiv.append(div);
                return div;
            }

            function updateDivForSubtitle(div, subtitle) {
                $('span', div).html(subtitle.content());
                if(subtitle.isSynced()) {
                    div.removeClass('unsynced');
                }
            }

            function handleMouseDownInContainer(evt) {
                if (evt.which == 3) {
                    var contextMenu = $('#context-menu');
                    contextMenu.show();
                    contextMenu.css({"left": evt.clientX, "top": evt.clientY});
                }
            }

            function handleMouseDownInTimeline(evt) {
                var initialPageX = evt.pageX;
                var maxDeltaX = 0;
                if(evt.which != 1) {
                    return;
                }
                $(document).on('mousemove.timelinedrag', function(evt) {
                    VideoPlayer.pause();
                    var deltaX = initialPageX - evt.pageX;
                    var deltaMS = pixelsToDuration(deltaX, scope.scale);
                    maxDeltaX = Math.max(Math.abs(deltaX), maxDeltaX);
                    scope.redrawSubtitles({
                        deltaMS: deltaMS,
                    });
                    scope.$emit('timeline-drag', deltaMS);
                }).on('mouseup.timelinedrag', function(evt) {
                    $(document).off('.timelinedrag');
                    if(maxDeltaX < 3) {
                        // mouse didn't move that much.  Interpret this as a
                        // click rather than a drag and seek to the current
                        // time.
                        var deltaX = evt.pageX - container.offset().left;
                        var deltaMS = pixelsToDuration(deltaX, scope.scale);
                        var seekTo = visibleTimespan.startTime + deltaMS;
                    } else {
                        var deltaX = initialPageX - evt.pageX;
                        var deltaMS = pixelsToDuration(deltaX, scope.scale);
                        var seekTo = scope.currentTime + deltaMS;
                    }
                    VideoPlayer.seek(seekTo);
                }).on('mouseleave.timelinedrag', function(evt) {
                    $(document).off('.timelinedrag');
                    scope.redrawSubtitles();
                    scope.$emit('timeline-drag', 0);
                });
                evt.preventDefault();
            }

            function placeSubtitle(startTime, endTime, div) {
                var x = durationToPixels(startTime - bufferTimespan.startTime,
                        scope.scale);
                var width = durationToPixels(endTime - startTime,
                        scope.scale);
                div.css({left: x, width: width});
            }

            function updateUnsyncedSubtitle() {
                /* Sometimes we want to show the first unsynced subtitle for
                 * the timeline.
                 *
                 * This method calculates if we want to show the subtitle or
                 * not and sets the unsyncedSubtitle variable accordingly.  If
                 * we don't want to show it, we set it to none.  If we do, we
                 * set it to a DraftSubtitle with the start/end times set
                 * based on the current time.
                 */
                var lastSynced = subtitleList().lastSyncedSubtitle();
                if(lastSynced !== null &&
                    lastSynced.endTime > scope.currentTime) {
                    // Not past the end of the synced subtitles
                    unsyncedSubtitle = null;
                    return;
                }
                var unsynced = subtitleList().firstUnsyncedSubtitle();
                if(unsynced === null) {
                    // All subtitles are synced.
                    unsyncedSubtitle = null;
                    return;
                }
                if(unsynced.startTime >= 0 && unsynced.startTime >
                        bufferTimespan.endTime) {
                    // unsynced subtitle has its start time set, and it's past
                    // the end of the timeline.
                    unsyncedSubtitle = null;
                    return;
                }


                if(unsyncedSubtitle === null) {
                    unsyncedSubtitle = unsynced.draftSubtitle();
                } else if (unsyncedSubtitle.storedSubtitle.id != unsynced.id) {
                    // We need to keep the stored subtitle up to date as
                    // it is used in the video overlay
                    unsyncedSubtitle = unsynced.draftSubtitle();
                }
                unsyncedSubtitle.markdown = unsynced.markdown;
                if(unsynced.startTime < 0) {
                    unsyncedSubtitle.startTime = scope.currentTime;
                    if(unsyncedSubtitle.startTime === null) {
                        // currentTime hasn't been set yet.  Let's use time=0
                        // for now.
                        unsyncedSubtitle.startTime = 0;
                    }
                    unsyncedSubtitle.endTime = scope.currentTime + DEFAULT_DURATION;
                } else {
                    unsyncedSubtitle.startTime = unsynced.startTime;
                    unsyncedSubtitle.endTime = Math.max(scope.currentTime,
                            unsynced.startTime + MIN_DURATION);
                }
            }

            function checkShownSubtitle() {
                // First check if the current subtitle is still shown, this is
                // the most common case, and it's fast
                if(scope.subtitle !== null &&
                    scope.subtitle.isAt(scope.currentTime)) {
                    return;
                }

                var shownSubtitle = subtitleList().subtitleAt(
                    scope.currentTime);
                scope.subtitle = shownSubtitle;
                if(shownSubtitle === null && unsyncedSubtitle !== null &&
                        unsyncedSubtitle.startTime <= scope.currentTime) {
                    shownSubtitle = unsyncedSubtitle.storedSubtitle;
                }
                if(shownSubtitle != scope.timeline.shownSubtitle) {
                    scope.timeline.shownSubtitle = shownSubtitle;
                    if(shownSubtitle !== null) {
                        scope.$root.$emit('scroll-to-subtitle', shownSubtitle);
                    }
                    var phase = scope.$root.$$phase;
                    if(phase != '$apply' && phase != '$digest') {
                        scope.$root.$digest();
                    }
                }
            }

            function placeSubtitles() {
                if(!scope.workingSubtitles) {
                    return;
                }
                var subtitles = subtitleList().getSubtitlesForTime(
                        bufferTimespan.startTime, bufferTimespan.endTime);
                var oldTimelineDivs = timelineDivs;
                timelineDivs = {}

                for(var i = 0; i < subtitles.length; i++) {
                    var subtitle = subtitles[i];
                    if(oldTimelineDivs.hasOwnProperty(subtitle.id)) {
                        var div = oldTimelineDivs[subtitle.id];
                        timelineDivs[subtitle.id] = div;
                        updateDivForSubtitle(div, subtitle);
                        delete oldTimelineDivs[subtitle.id];
                    } else {
                        var div = makeDivForSubtitle(subtitle);
                        timelineDivs[subtitle.id] = div;
                    }
                    placeSubtitle(subtitle.startTime, subtitle.endTime,
                            timelineDivs[subtitle.id]);
                }
                // remove divs no longer in the timeline
                for(var subId in oldTimelineDivs) {
                    oldTimelineDivs[subId].remove();
                }
            }
            function placeUnsyncedSubtitle() {
                updateUnsyncedSubtitle();
                if(unsyncedSubtitle !== null) {
                    if(unsyncedDiv === null) {
                        unsyncedDiv = makeDivForSubtitle(unsyncedSubtitle);
                        unsyncedDiv.addClass('unsynced')
                    } else {
                        updateDivForSubtitle(unsyncedDiv, unsyncedSubtitle);
                    }
                    placeSubtitle(unsyncedSubtitle.startTime,
                            unsyncedSubtitle.endTime, unsyncedDiv);
                } else if(unsyncedDiv !== null) {
                    unsyncedDiv.remove();
                    unsyncedDiv = null;
                }
            }

            // Put redrawSubtitles in the scope so that the controller can
            // call it.
            scope.redrawSubtitles = function(options) {
                if(options === undefined) {
                    options = {};
                }
                visibleTimespan = new VisibleTimespan(scope, containerWidth,
                        options.deltaMS);
                if(bufferTimespan === null ||
                    !visibleTimespan.fitsInBuffer(bufferTimespan)) {
                        bufferTimespan = new BufferTimespan(scope);
                    if(bufferTimespan.width != timelineDivWidth) {
                        timelineDivWidth = bufferTimespan.width;
                        timelineDiv.css('width', bufferTimespan.width + 'px');
                    }
                    placeSubtitles();
                } else if(options.forcePlace) {
                    placeSubtitles();
                }
                // always need to place the unsynced subtitle, since it
                // changes with the current time.
                placeUnsyncedSubtitle();
                checkShownSubtitle();

                visibleTimespan.positionDiv(bufferTimespan, timelineDiv);
            };

            // Handle drag and drop.
            timelineDiv.on('mousedown', handleMouseDownInTimeline);
            container.on('mousedown', handleMouseDownInContainer);
            // Redraw the subtitles on window resize
            $(window).resize(function() {
                containerWidth = (container.width() || container.parent().width());
                scope.redrawSubtitles();
            });
            // Redraw them now as well
            scope.redrawSubtitles();
        }
    }]);
})();
