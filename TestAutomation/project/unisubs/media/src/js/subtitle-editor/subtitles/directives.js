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
var LOCK_EXPIRATION = 25;
var USER_IDLE_MINUTES = 15;

(function() {

    var module = angular.module('amara.SubtitleEditor.subtitles.directives', []);

    module.directive('subtitleEditor', function() {
        return function link(scope, elm, attrs) {
            // For some reason using ng-keydown at the HTML tag doesn't work.
            // Use jquery instead.
            $(document).keydown(function(evt) {
                scope.$apply(function(scope) {
                    scope.handleAppKeyDown(evt);
                });
            });
        };
    });
    module.directive('workingSubtitles', ['VideoPlayer', '$timeout', function(VideoPlayer, $timeout) {
        return function link(scope, elem, attrs) {
            var startHelper = $('div.sync-help.begin', elem);
            var endHelper = $('div.sync-help.end', elem);
            var infoTray = $('div.info-tray', elem);
            var subtitleList = $('.subtitles ul', elem);
            var currentArrow = undefined;
            var wrapper = $(elem);

            function getSubtitleTop(subtitle) {
                var li = scope.getSubtitleRepeatItem(subtitle);
                var top = li.offset().top - wrapper.offset().top;
                if(top < 0 || top + startHelper.height() >= wrapper.height()) {
                    return null;
                }
                return top;
            }

            var lastSyncStart = null;
            var lastSyncEnd = null;

            scope.positionSyncHelpers = function(startSub, endSub) {
                if(startSub === undefined) {
                    startSub = lastSyncStart;
                }
                if(endSub === undefined) {
                    endSub = lastSyncEnd;
                }
                lastSyncStart = startSub;
                lastSyncEnd = endSub;

                if(!scope.timelineShown || !VideoPlayer.isPlaying()) {
                    startHelper.hide();
                    endHelper.hide();
                    return;
                }
                var startTop = null;
                var endTop = null;
                if(startSub !== null) {
                    startTop = getSubtitleTop(startSub);
                }
                if(endSub !== null) {
                    endTop = getSubtitleTop(endSub);
                }
                if(startTop !== null) {
                    startHelper.css('top', startTop + 'px');
                    startHelper.show();
                } else {
                    startHelper.hide();
                }
                if(endTop !== null) {
                    endHelper.css('top', endTop + 'px');
                    endHelper.show();
                } else {
                    endHelper.hide();
                }
            }

            scope.positionInfoTray = function() {
                var BUFFER = 22;
                var subtitle = scope.currentEdit.subtitle;
                if(subtitle === null) {
                    infoTray.hide();
                    return;
                }
                var li = scope.getSubtitleRepeatItem(subtitle);
                if(li) {
                    currentArrow = li.find(".arrow");
                    var top = li.offset().top - wrapper.offset().top;
                    var bottom = top + li.height();

                    var infoTrayBottom = infoTray.height() + top;
                    var willTrim = wrapper.height() < infoTrayBottom;
                    if (willTrim) {
                        var adjustedTop = top - (infoTrayBottom - wrapper.height());
                        if (adjustedTop + BUFFER < bottom && adjustedTop - BUFFER > top - infoTray.height()) {
                            top = adjustedTop;
                        }
                    }
                    if(top + BUFFER >= 0 && top + BUFFER < wrapper.height()) {
                        infoTray.css('top', top + 'px');
                        infoTray.show();
                        currentArrow.show();
                    } else {
                        infoTray.hide();
                        currentArrow.hide();
                    }
                }
            }

            scope.$watch("currentEdit.subtitle", function() {
                if (currentArrow) {
                    currentArrow.hide(); // Kinda hate this, i think it would be cleaner to give each line its own controller
                }
                $timeout(function() {
                    // use timeout to make sure that this happens after the DOM has updated,
                    // since changes to contents of the info tray may have changed its size.
                    scope.positionInfoTray();
                }, 0, false);
            });

            scope.$watch("currentEdit.subtitle.markdown", function() {
                $timeout(function() {
                    // use timeout to make sure that this happens after the DOM has updated,
                    // since changes to contents of the info tray may have changed its size.
                    scope.positionInfoTray();
                }, 0, false);
            });

            scope.$watch("timelineShown", function() {
                scope.positionSyncHelpers();
            });

            scope.$root.$on("video-playback-changes", function() {
                scope.positionSyncHelpers();
            });

            scope.$root.$on('working-subtitles-scrolled', function() {
                scope.positionSyncHelpers();
                scope.positionInfoTray();
            });
        };
    }]);

    module.directive('subtitleScroller', ["$window", function($window) {
        var window = $($window);
	var scrollingPrevious = [];
	$('div.subtitles').each(function(index) {
	    scrollingPrevious[index] = $(this).scrollTop();
	});
        return function link(scope, elem, attrs) {
            var scroller = $(elem);
            var isWorkingSet = (attrs.subtitleScroller == "working-subtitle-set");
            // Handle scroll.
            scroller.scroll(function() {
                // If scroll sync is locked.
                if (scope.scrollingSynced) {
                    var delta = 0;
                    var index_scrolled = -1;
                    $('div.subtitles').each(function(index) {
                        var newScrollTop = $(this).scrollTop();
                        if (newScrollTop != scrollingPrevious[index]) {
                            delta = newScrollTop - scrollingPrevious[index];
                            index_scrolled = index;
                        }
                    });
                    if (index_scrolled != -1) {
                        $('div.subtitles').each(function(index) {
                            if (index != index_scrolled) {
                                var newScrollTop = $(this).scrollTop() + delta;
                                $(this).scrollTop(newScrollTop);
                                var updatedScrollTop = $(this).scrollTop();
                                if ((updatedScrollTop != newScrollTop) && (updatedScrollTop != 0)) {
                                    $(this).children().last().height($(this).children().last().height() + newScrollTop - updatedScrollTop);
                                    $(this).scrollTop(newScrollTop);
                                }
                            }
                        });
                    }
                }
		$('div.subtitles').each(function(index) {
		    scrollingPrevious[index] = $(this).scrollTop();
		});

                if(isWorkingSet) {
                    scope.$root.$emit("working-subtitles-scrolled");
                }
            });

            function resizeScroller() {
                if (scope.timelineShown) {
                    var scrollerTop = 398;
                } else {
                    var scrollerTop = 327;
                }
                scroller.height(window.height() - scrollerTop);
            }

            scope.$watch('timelineShown', resizeScroller);
            window.on('resize', resizeScroller);
            resizeScroller();

            if (isWorkingSet) {
                scope.$root.$on('scroll-to-subtitle', function(evt, subtitle) {
                    if(scope.currentEdit.inProgress()) {
                        return;
                    }
                    var target = scope.getSubtitleRepeatItem(subtitle);
                    var prev = target.prev();
                    if(prev.length > 0) {
                        target = prev;
                    }
                    if(target) {
                        scroller.scrollTop(scroller.scrollTop() +
                                target.offset().top - scroller.offset().top);
                    }
                });
            }
        }
    }]);

    module.directive('subtitleRepeat', ["$interpolate", "$filter", "$parse", "DomUtil", "EditorData", function($interpolate, $filter, $parse,
                DomUtil, EditorData) {
        /* Specialized repeat directive to work with subtitleList
         *
         * Because we need to deal potentially thousands of subtitles,
         * ng-repeat is not ideal.  subtitleRepeat is a specialized directive
         * that creates the <ul> that we need for a subtitle list.  The
         * speedups come from a couple things:
         *
         *   - It hooks up to the change callback of subtitleList to calculate
         *   changes quickly.
         *   - it doesn't create a child scope for each subtitle.
         *
         *  When using subtitle-repeat, set the value of subtitle-repeat to
         *  the subtitleList to bind to.  Optionally, create a read-only
         *  attribute to specify a read-only list.
         */
        return function link($scope, elm, attrs) {
            var subtitleList = $scope.$eval(attrs.subtitleRepeat);
            // Map subtitle ID to DOM node for that subtitle
            var subtitleMap = {};
            // are we a read-only list?
            var readOnly = Boolean(attrs.readOnly);
            var displayTime = $filter('displayTime');
            // Template elements that we use to create list items
            var templateLI = $('<li />');
            templateLI.append('<span class="timing" />');
            templateLI.append('<span class="subtitle-text" />');
            if(!readOnly) {
		templateLI.append('<span class="warning">!</span>');
                templateLI.append(
                    '<button class="new-paragraph">&para;</button>');
		templateLI.append(makeSubtitleMenu());
            } else {
                templateLI.append('<span class="new-paragraph">&para;</span>');
            }

            $scope.getSubtitleRepeatItem = function(subtitle) {
                var rv = subtitleMap[subtitle.id];
                if(rv !== undefined) {
                    return rv;
                } else {
                    return null;
                }
            }

            if(!readOnly) {
                $scope.$watch('currentEdit.subtitle', function(newValue, oldValue) {
                    if(oldValue) {
                        stopEditOn(oldValue);
                    }
                    if(newValue) {
                        startEditOn(newValue);
                    }
                });
                elm.on('click', function(evt) {
                    var action = findSubtitleClick(evt.target);
                    var subtitle = findSubtitleData(evt.target);
                    if(action && $scope.onSubtitleClick) {
                        $scope.$apply(function() {
                            $scope.onSubtitleClick(evt, subtitle, action);
                        });
                    }
                });
            }

            $scope.$watch('timeline.shownSubtitle', function(newSub, oldSub) {
                if(newSub && subtitleMap[newSub.id]) {
                    subtitleMap[newSub.id].addClass('current-subtitle');
                }
                if(oldSub && subtitleMap[oldSub.id]) {
                    subtitleMap[oldSub.id].removeClass('current-subtitle');
                }
            });

            subtitleList.addChangeCallback(handleChanges);
            reloadSubtitles();

            function makeSubtitleMenu() {
		var toolbox = $('<div />').prop('class', "sub-toolbox");
		var icon = $('<a />');
		icon.prop('href', '#');
		icon.append($('<img />').prop('src', EditorData.staticURL + "images/subtitle-editor/glyphicons_halflings_135_wrench_light.png"));
		var menu = $('<ul />').prop('class', "sub-toolbox-menu");
		[["jump-to", "Seek to subtitle"],
		 ["insert-top", "Insert subtitle above"],
		 ["insert-down", "Insert subtitle below"],
		 ["remove", "Delete subtitle"],
		 ["note-time", "Start note for current time"]].forEach(function(data) {
		    menu.append($('<li />').append($('<a />').prop('class', data[0]).prop('title', data[1])));
		});
		toolbox.append($('<div />').prop('class', "sub-toolbox-inside").append(icon).append(menu));
		return toolbox;
            }

            function createLIForSubtitle(subtitle) {
                var elt = templateLI.clone();
                renderSubtitle(subtitle, elt);
                subtitleMap[subtitle.id] = elt;
                elt.data('subtitle', subtitle);
                return elt;
            }

            function renderSubtitle(subtitle, elt) {
                var content = subtitle.content();
                var classes = ["sub"];

                if($scope.timeline.shownSubtitle === subtitle) {
                    classes.push('current-subtitle');
                }
                if(content == '') {
                    classes.push('empty');
                }
                if(subtitle.startOfParagraph) {
                    classes.push('paragraph-start');
                }
                if($scope.currentEdit.isForSubtitle(subtitle)) {
                    classes.push('edit');
                }
                elt.prop('className', classes.join(' '));
                $('span.subtitle-text', elt).html(content);
                $('span.timing', elt).text(displayTime(subtitle.startTime));
		$('span.warning', elt).toggle($scope.warningsShown && subtitle.hasWarning());
            }

            function findSubtitleData(node) {
                // Find the subtitle that we set with the jquery data()
                // function by starting with node and moving up the DOM tree.
                var toplevelNode = elm[0];
                while(node && node != toplevelNode) {
                    var subtitle = $(node).data('subtitle');
                    if(subtitle) {
                        return subtitle;
                    } else {
                        node = node.parentNode;
                    }
                }
                return null;
            }

            function findSubtitleClick(node, dataName) {
                var toplevelNode = elm[0];
                while(node && node != toplevelNode) {
                    if(node.tagName == 'BUTTON') {
                        switch(node.className) {
                            case 'insert-subtitle':
                                return 'insert';

                            case 'remove-subtitle':
                                return 'remove';

                            case 'new-paragraph':
                                return 'changeParagraph'
                        }
                    } else if(node.tagName == 'LI') {
                        return 'edit';
                    } else if(node.tagName == 'A') {
                        switch(node.className) {
			case 'jump-to':
			    return 'jump-to';
			case 'insert-top':
			    return 'insert-top';
			case 'insert-down':
			    return 'insert-down';
			case 'remove':
			    return 'remove';
			case 'note-time':
			    return 'note-time';
			}
		    }
                    node = node.parentNode;
                }
                return null;
            }

            function handleChanges(changes) {
                _.each(changes, handleChange);
            }

            function handleChange(change) {
                var subtitle = change.subtitle;
                switch(change.type) {
                    case 'remove':
                        var node = subtitleMap[subtitle.id];
                        node.remove();
                        delete subtitleMap[subtitle.id];
                        break;
                    case 'update':
                        renderSubtitle(subtitle, subtitleMap[subtitle.id]);
                        break;
                    case 'insert':
                        if(change.before !== null) {
                            var node = subtitleMap[change.before.id];
                            node.before(createLIForSubtitle(subtitle));
                        } else {
                            elm.append(createLIForSubtitle(subtitle));
                        }
                        break;
                    case 'insert-top':
                        if(change.before !== null) {
                            var node = subtitleMap[change.before.id];
                            node.before(createLIForSubtitle(subtitle));
                        } else {
                            elm.append(createLIForSubtitle(subtitle));
                        }
                        break;
                    case 'insert-down':
                        if(change.before !== null) {
                            var node = subtitleMap[change.before.id];
                            node.before(createLIForSubtitle(subtitle));
                        } else {
                            elm.append(createLIForSubtitle(subtitle));
                        }
                        break;
                    case 'reload':
                        reloadSubtitles();
                }
                $scope.$emit('subtitle-list-changed');
            }

            function startEditOn(subtitle) {
                var li = subtitleMap[subtitle.id];
		if (li) {
                    li.addClass('edit');
                    var textarea = $('<textarea class="subtitle-edit" placeholder="Type a subtitle and press Enter"/>');
                    textarea.val(subtitle.markdown);
                    li.append(textarea);
                    textarea.autosize();
                    textarea.focus();
                    var caretPos = $scope.currentEdit.initialCaretPos;
                    DomUtil.setSelectionRange(textarea[0], caretPos, caretPos);
                    textarea.on('keyup input propertychange', function(evt) {
                        var content = textarea.val();
                        if($scope.currentEdit.hasChanges(content)) {
                            $scope.currentEdit.update(subtitleList, textarea.val());
                            $scope.$root.$emit('work-done');
                            $scope.$root.$digest();
                        }
                    });
                    if($scope.onEditKeydown) {
                        textarea.on('keydown', function(evt) {
                            $scope.$apply(function() {
                                $scope.onEditKeydown(evt);
                            });
                        });
                    }
                }
            }
            function stopEditOn(subtitle) {
                var li = subtitleMap[subtitle.id];
                if(li) {
                    li.removeClass('edit');
                    $('textarea.subtitle-edit', li).remove();
                }
            }

            $scope.canSplitSubtitle = function(subtitle) {
                var li = subtitleMap[subtitle.id];
                if(!li) {
                    return false;
                }
                var textarea = $('textarea.subtitle-edit', li);
                return textarea.length > 0;
            }

            $scope.calcSubtitleSplit = function(subtitle) {
                var li = subtitleMap[subtitle.id];
                var textarea = $('textarea.subtitle-edit', li);
                var selectionRange = DomUtil.getSelectionRange(textarea[0]);
                var markdown = textarea.val();
                return {
                    first: markdown.substring(0, selectionRange.start).replace(/\s+$/, ''),
                    second: markdown.substring(selectionRange.start).replace(/^\s+/, '')
                };
            }

            function reloadSubtitles() {
                elm.empty();
                subtitleMap = {}
                _.each(subtitleList.subtitles, function(subtitle) {
                    elm.append(createLIForSubtitle(subtitle));
                });
            }
        }
    }]);

    module.directive('languageSelector', ["SubtitleStorage", function(SubtitleStorage) {
        return {
            compile: function compile(elm, attrs, transclude) {
                return {
                    post: function post(scope, elm, attrs) {
                        /* For some reason, if we use ng-select angular
                         * creates an extra option because it thinks
                         * scope.versionNumber is an invalid value for the
                         * options, even though it isn't.  I think it has to
                         * do with the fact that we manually create options
                         * with ng-repeat.  In any case, we handle the
                         * select ourself.
                         */
                        $('select.version-select', elm).change(function(evt) {
                            scope.versionNumber = this.value;
                            scope.$digest();
                        });
                        scope.setInitialDisplayLanguage(SubtitleStorage.getLanguages());
                    }
                };
            }
        };
    }]);
})();
