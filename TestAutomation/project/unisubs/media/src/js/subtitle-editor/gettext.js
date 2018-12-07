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
    var module = angular.module('amara.SubtitleEditor.gettext', []);

    // take the global gettext functions that django provides and convert them to angular dependencies
    var gettextFuctions = [
        'gettext', 'ngettext', 'interpolate', 'get_format', 'gettext_noop',
        'pgettext', 'npgettext', 'pluralidx',
    ];
    _.each(gettextFuctions, function(name) {
        if(window[name]) {
            module.value(name, window[name]);
        }
    });

}).call(this);
