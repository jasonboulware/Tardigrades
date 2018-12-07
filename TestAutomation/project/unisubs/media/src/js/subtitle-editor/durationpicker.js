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
    var module = angular.module('amara.SubtitleEditor.durationpicker', []);
    var wholeNumberRe = /^\s*\d+\s*$/;

    module.directive('durationPicker', ['pgettext', function(pgettext) {
        var durationUnits = {
            'hours': {
                'label': pgettext('hours', 'h'), // label for the input
                'min': 0,                        // minimum input value
                'max': 999,                      // maximum input value
                'scale': 3600000                 // scale to convert to milliseconds
            },
            'minutes': {
                'label': pgettext('minutes', 'm'),
                'min': 0,
                'max': 59,
                'scale': 60000
            },
            'seconds': {
                'label': pgettext('seconds', 's'),
                'min': 0,
                'max': 59,
                'scale': 1000
            },
            'milliseconds': {
                'label': pgettext('milliseconds', 'ms'),
                'min': 0,
                'max': 999,
                'scale': 1
            },
        };

        function createChildElements(durationPicker) {
            function createForUnit(unit) {
                var label = durationUnits[unit].label;

                durationPicker.append($('<input>').attr({
                    "class": "durationPicker-input " + unit,
                    "type": "text",
                    "size": "3"
                }));
                durationPicker.append(label);
            }
            createForUnit('hours');
            createForUnit('minutes');
            createForUnit('seconds');
            createForUnit('milliseconds');
        }

        return function link($scope, elem, attrs) {
            createChildElements(elem);
            var inputs = $('.durationPicker-input', elem);
            var inputsByUnit = _.mapObject(durationUnits, function(info, unit) {
                return inputs.filter('.' + unit);
            });

            inputs.focus(function() {
                $(this).select();
            }).change(function() {
                var input = $(this);
                if(_.isNaN(parseInput(input))) {
                    input.addClass('invalid');
                } else {
                    input.removeClass('invalid');
                }
            });

            if(attrs.ngDisable) {
                $scope.$watch(attrs.ngDisable, function(newValue) {
                    if(newValue) {
                        $(elem).addClass('disabled');
                        $('.durationPicker-input', elem).prop('disabled', true);
                    } else {
                        $(elem).removeClass('disabled');
                        $('.durationPicker-input', elem).prop('disabled', false);
                    }
                });
            }

            if(attrs.ngModel) {
                $scope.$watch(attrs.ngModel, updateInputsFromModel);
                inputs.change(updateModelFromInputs);
                inputs.keyup(updateModelFromInputs);
            }

            function parseInput(input) {
                var unparsed = $.trim(input.val());
                if(unparsed == '') {
                    return 0;
                }
                if(unparsed.match(wholeNumberRe) === null) {
                    return NaN;
                }
                var amount = parseInt(unparsed);
                if(_.isNaN(amount)) {
                    return NaN;
                }
                var unitInfo = getUnitInfo(input);
                if(amount < unitInfo.min || amount > unitInfo.max) {
                    return NaN;
                }
                return amount * unitInfo.scale;
            }

            function getUnitInfo(input) {
                for(key in durationUnits) {
                    if(input.hasClass(key)) {
                        return durationUnits[key]
                    }
                }
            }

            var lastAmountFromInputs = NaN;
            function updateInputsFromModel(newValue) {
                if(_.isNaN(newValue) || newValue == lastAmountFromInputs) {
                    return;
                }
                var ms = Math.floor(newValue);
                inputsByUnit.milliseconds.val(ms % 1000);
                inputsByUnit.seconds.val(Math.floor(ms / 1000) % 60);
                inputsByUnit.minutes.val(Math.floor(ms / 60000 ) % 60);
                inputsByUnit.hours.val(Math.floor(ms / 3600000));
            }
            function updateModelFromInputs() {
                var amount = 0;
                inputs.each(function() {
                    amount += parseInput($(this));
                });
                $scope[attrs.ngModel] = amount;
                lastAmountFromInputs = amount;
                if(attrs.ngChange) {
                    $scope.$apply(attrs.ngChange);
                }
            }
        };
    }]);

    function pad2(value) {
        return ('00' + value).substr(-2);
    }
    function pad3(value) {
        return ('000' + value).substr(-3);
    }

    // Format a time in milliseconds in the (h:mm:ss.ms).  This can be helpful when displaying the times from the duration picker
    module.factory('formatTime', ['gettext', 'interpolate', function(gettext, interpolate) {
        return function(milliseconds, options) {
            if(options === undefined) {
                options = {};
            }
            _.defaults(options, {
                longFormat: false,
                includeMilliseconds: false
            });
            var hours = Math.floor(milliseconds / 60 / 60 / 1000);
            var minutes = Math.floor((milliseconds / 60 / 1000) % 60);
            var seconds = Math.floor((milliseconds / 1000) % 60);
            var milliseconds = milliseconds % 1000;

            if(!options.longFormat) {
                if(hours && !minutes && !seconds && !milliseconds) {
                    return interpolate('%(count)s hours', {count: hours}, true);
                }
                if(!hours && minutes && !seconds && !milliseconds) {
                    return interpolate('%(count)s minutes', {count: minutes}, true);
                }
                if(!hours && !minutes && seconds && !milliseconds) {
                    return interpolate('%(count)s seconds', {count: seconds}, true);
                }
                if(!hours && !minutes && !seconds && milliseconds) {
                    return interpolate('%(count)s milliseconds', {count: milliseconds}, true);
                }
            }

            if(milliseconds || options.includeMilliseconds) {
                return hours + ':' + pad2(minutes) + ':' + pad2(seconds) + '.' + pad3(milliseconds);
            } else {
                return hours + ':' + pad2(minutes) + ':' + pad2(seconds);
            }
        }
    }]);

}).call(this);
