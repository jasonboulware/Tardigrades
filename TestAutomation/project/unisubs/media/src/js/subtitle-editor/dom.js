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
    var module = angular.module('amara.SubtitleEditor.dom', []);

    module.directive('autosizeBind', ["$parse", function($parse) {
        return function link(scope, elm, attrs) {
            var getter = $parse(attrs.autosizeBind);
            // set the value before calling autosize, otherwise we don't size
            // correctly on the first pass
            elm.val(getter(scope));
            elm.autosize();
            scope.$watch(attrs.autosizeBind, function(newVal) {
                elm.val(newVal).trigger('autosize');
            });
            elm.on('change', function() {
                scope.$apply(function() {
                    getter.assign(scope, elm.val());
                });
            });
        }
    }]);

    module.directive('fixsizeBind', ["$parse", function($parse) {
        return function link(scope, elm, attrs) {
            var getter = $parse(attrs.fixsizeBind);
            // set the value before calling autosize, otherwise we don't size
            // correctly on the first pass
            elm.val(getter(scope));
            scope.$watch(attrs.fixsizeBind, function(newVal) {
                elm.val(newVal).trigger('autosize');
            });
            elm.on('change', function() {
                scope.$apply(function() {
                    getter.assign(scope, elm.val());
                });
            });
        }
    }]);

    module.factory('DomUtil', function() {
        return {
            getSelectionRange: function(elem) {
                return {
                    start: elem.selectionStart,
                    end: elem.selectionEnd
                };
            },
            setSelectionRange: function(elem, selectionStart, selectionEnd) {
                elem.setSelectionRange(selectionStart, selectionEnd);
            }
        };
    });
    
    /*
     * Interface to the window object.  We avoid doing that directly in the
     * controllers because it makes them hard to test.
     */

    module.factory('DomWindow', ["$window", function($window) {
        var document = $($window.document);
        return {
            caretPos: function() {
                return $window.getSelection().anchorOffset;
            },
            onDocumentEvent: function(eventName, func) {
                document.on(eventName, func);
            },
            offDocumentEvent: function(eventName) {
                document.off(eventName);
            },
        };
    }]);
}).call(this);

