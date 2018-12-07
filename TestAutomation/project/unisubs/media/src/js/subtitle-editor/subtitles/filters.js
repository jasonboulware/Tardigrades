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
    var module = angular.module('amara.SubtitleEditor.subtitles.filters', []);

    /*
    * Display a human friendly format.
    */
    function displayTime(milliseconds, showFraction) {
        if (milliseconds === -1 ||
            isNaN(Math.floor(milliseconds)) ||
            milliseconds === undefined ||
            milliseconds === null) {
                return "--";
            }
        var date;
        if (showFraction)
            date = new Date(10 * Math.round(milliseconds / 10));
        else 
            date = new Date(1000 * Math.round(milliseconds / 1000));
        var hours = date.getUTCHours(), minutes = date.getUTCMinutes(),
            seconds = date.getUTCSeconds(), cents = Math.floor(date.getUTCMilliseconds() / 10);
        var result = "" + (hours ? (hours + ":" + ("0" + minutes).slice (-2) + ":" + ("0" + seconds).slice (-2)) :
                                   (minutes + ":" + ("0" + seconds).slice (-2)));
        if (showFraction) result += "." + ("0" + cents).slice (-2);
        return result;
    }
    module.filter('displayTime', function(){
        return function(milliseconds) {
            return displayTime(milliseconds, true);
        }
    });
    module.filter('displayTimeSeconds', function(){
        return function(milliseconds) {
            return displayTime(milliseconds, false);
        }
    });
    module.filter('versionDropDownDisplay', function(){
        return function (versionData){
            if(versionData.visibility == 'private'
                || versionData.visibility == 'deleted') {
                return "Version " + versionData.version_no +
                            " (" + versionData.visibility + ")";
            } else {
                return "Version " + versionData.version_no;
            }
        }
    })
    module.filter('metadataTypeName', function(){
        // FIXME: the labels should be localized
        var typeNameMap = {
            'speaker-name': 'Speaker Name',
            'location': 'Location',
        };
        return function metadataTypeName(typeName) {
            if(typeName in typeNameMap) {
                return typeNameMap[typeName];
            } else {
                return typeName;
            }
        }
    })

}).call(this);
