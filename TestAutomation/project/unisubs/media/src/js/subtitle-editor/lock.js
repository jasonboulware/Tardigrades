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

(function(){
    var module = angular.module('amara.SubtitleEditor.lock', []);

    function getLockingUrl(videoId, languageCode, type){
        return '/en/subtitles/editor/' + videoId + '/' + languageCode + '/' + type + "/";
    }

    module.factory('LockService', ["$http", "$cookies", function($http, $cookies){
        return {

            makeLockRequest: function(videoId, languageCode, type){
                return $http({
                    method: 'POST',
                    headers: {'X-CSRFToken': $cookies.csrftoken},
                    url: getLockingUrl(videoId, languageCode, type)
                });
            },

            regainLock: function(videoId, languageCode){
                return this.makeLockRequest(videoId, languageCode, 'regain')
            },
            releaseLock: function(videoId, languageCode){
                return this.makeLockRequest(videoId, languageCode, 'release')
            }
        }
    }]);

}).call(this);
