// Amara, universalsubtitles.org
//
// Copyright (C) 2015 Participatory Culture Foundation
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

(function(){
    var module = angular.module('amara.SubtitleEditor.preferences', []);

    var urlsByType = {
        'tutorial_shown': '/en/subtitles/editor/tutorial_shown',
        'set_playback_mode': '/en/subtitles/editor/set_playback_mode'
    };

    function getPreferencesUrl(type) {
        var url = urlsByType[type];
        return url ? url : null;
    }

    module.factory('PreferencesService', ["$http", "$cookies", function($http, $cookies){
        return {
            makePreferencesRequest: function(type, data) {
                var config = {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': $cookies.csrftoken,
                        'Content-type': 'application/x-www-form-urlencoded'
                    },
                    url: getPreferencesUrl(type)
                };

                if(data !== undefined) {
                    config.data = $.param(data);
                }

                return $http(config);
            },

            tutorialShown: function(){
                return this.makePreferencesRequest('tutorial_shown')
            },

            setPlaybackMode: function(playbackMode) {
                return this.makePreferencesRequest('set_playback_mode', {playback_mode: playbackMode})
            }
        }
    }]);

}).call(this);
