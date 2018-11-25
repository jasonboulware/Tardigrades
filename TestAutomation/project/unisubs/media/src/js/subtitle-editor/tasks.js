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

(function(){

    var API_BASE_PATH = '/api/teams/';

    var module = angular.module('amara.SubtitleEditor.services', []);

    function getUpdateTaskAPIUrl(taskId, teamSlug){
        return API_BASE_PATH + teamSlug + "/tasks/" + taskId; 
    }

    module.factory("TaskService", ["$http", function($http){

        var authHeaders = cachedData.authHeaders;

        return {
            completeTask: function(taskId, teamSlug, note, subtitleVersionId){
                var url = getUpdateTaskAPIUrl(taskId, teamSlug);

                return $http({
                    method: 'PUT',
                    url: url,
                    headers: authHeaders,
                    data:  {
                        version_number: subtitleVersionId,
                        complete: true,
                        body: note
                    }
                });
            }
        }
    }]);

}).call(this);
