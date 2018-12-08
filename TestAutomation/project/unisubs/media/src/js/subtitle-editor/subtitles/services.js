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

    var API_BASE_PATH_TEAMS = '/api/teams/';

    var module = angular.module('amara.SubtitleEditor.subtitles.services', []);

    var getTaskSaveAPIUrl = function(teamSlug, taskID) {
        return API_BASE_PATH_TEAMS + teamSlug + '/tasks/' + taskID + '/';
    };
    var getSubtitlesAPIURL = function(videoId, languageCode) {
        return ('/api/videos/' + videoId +
                '/languages/' + languageCode + '/subtitles/');
    };
    var getSubtitlesFetchAPIURL = function(videoId, languageCode, versionNumber) {
        var url = getSubtitlesAPIURL(videoId, languageCode);
        url += '?format=json&sub_format=dfxp';
        if (versionNumber) {
            url = url + '&version=' + versionNumber;
        }
        return url
    }
    var getActionAPIUrl = function(videoId, languageCode) {
        return getSubtitlesAPIURL(videoId, languageCode) + 'actions/';
    };

    var getNoteAPIUrl = function(videoId, languageCode) {
        return getSubtitlesAPIURL(videoId, languageCode) + 'notes/';
    };

    /*
     * Language object that we return from getLanguage()
     */
    function Language(responseData) {
        /*
         * Create a new Language object
         *
         * responseData is either:
         *   - data that we got back from the API
         *   - or data from the editor_data variable
         *
         * This means that editor_data should be formated exactly as the
         * response data is.
         */
        this.responseData = responseData;
        this.name = responseData.name;
        this.code = responseData.language_code;
        this.versions = responseData.versions;
        if(responseData.is_rtl) {
            this.dir = 'rtl';
        } else {
            this.dir = 'ltr';
        }
        this.isPrimaryAudioLanguage = responseData.is_original;
        this.subtitlesComplete = responseData.subtitles_complete;
        var lastVersion = _.last(responseData.versions);
        if(lastVersion) {
            this.lastVersionNumber = lastVersion.version_no;
        } else {
            this.lastVersionNumber = null;
        }
    }

    module.factory('SubtitleStorage', ["$http", "EditorData", function($http, EditorData) {

        // Map language codes to Language objects
        var languageMap = {};
        _.forEach(EditorData.languages, function(languageData) {
            var language = new Language(languageData);
            languageMap[language.code] = language;
        });

        // Map language_code/version_number to subtitle data
        var cachedSubtitleData = {};
        // Populate cachedSubtitleData with versions from editorData that
        // were pre-filled with the data we need.
        _.each(EditorData.languages, function(language) {
            var language_code = language.language_code;
            cachedSubtitleData[language_code] = {};
            _.each(language.versions, function(version) {
                var versionNum = version.version_no;
                if(version.subtitles) {
                    cachedSubtitleData[language_code][versionNum] = version;
                }
            });
        });

        function authHeaders() {
            var rv = {};
            // The following code converts the values of
            // EditorData.authHeaders into utf-8 encoded bytestrings to send
            // back to the server.  The unescape/encodeURIComponent part seems
            // pretty hacky, but it should work for all browsers
            // (http://monsur.hossa.in/2012/07/20/utf-8-in-javascript.html)
            for (var key in EditorData.authHeaders) {
                var val = EditorData.authHeaders[key];
                var utfVal = unescape(encodeURIComponent(val));
                rv[key] = utfVal;
            }
            return rv;
        }


        return {
            approveTask: function(versionNumber, notes) {

                var url = getTaskSaveAPIUrl(EditorData.team_slug,
                        EditorData.task_id);

                var promise = $http({
                    method: 'PUT',
                    url: url,
                    headers: authHeaders(),
                    data:  {
                        complete: true,
                        body: notes,
                        version_number: versionNumber,
                    }
                });

                return promise;

            },
            updateTaskNotes: function(notes) {

                var url = getTaskSaveAPIUrl(EditorData.team_slug,
                        EditorData.task_id);

                var promise = $http({
                    method: 'PUT',
                    url: url,
                    headers: authHeaders(),
                    data:  {
                        body: notes,
                    }
                });

                return promise;
            },
            performAction: function(actionName) {
                var url = getActionAPIUrl(EditorData.video.id,
                        EditorData.editingVersion.languageCode);

                return $http.post(url, { action: actionName }, {
                    headers: authHeaders()
                });
            },
            postNote: function(body) {
                var url = getNoteAPIUrl(EditorData.video.id,
                        EditorData.editingVersion.languageCode);

                return $http.post(url, { body: body }, {
                    headers: authHeaders()
                });
            },
            getLanguages: function(callback) {
                return _.values(languageMap);
            },
            getLanguage: function(languageCode) {
                return languageMap[languageCode];
            },
            getSubtitles: function(languageCode, versionNumber, callback){

                // You must supply a language code in order to get subtitles.
                if (!languageCode) {
                    throw Error('You must supply a language code to getSubtitles().');
                }

                var subtitleData;
                if(versionNumber === null) {
                    var language = languageMap[languageCode];
                    var versionNum = language.lastVersionNumber;
                    if(versionNum === null) {
                        throw "no versions for language: " + languageCode;
                    }
                } else {
                    var versionNum = parseInt(versionNumber, 10);
                }
                var cacheData = cachedSubtitleData[languageCode][versionNum];
                if(cacheData) {
                   callback(cacheData);
                } else {
                    var url = getSubtitlesFetchAPIURL(EditorData.video.id, languageCode, versionNumber);
                    $http.get(url, {
                        headers: authHeaders()
                    }).success(function(response) {
                        cachedSubtitleData[languageCode][versionNum] = response;
                        callback(response)
                    });
                }
            },
            getVideoURLs: function() {
                return EditorData.video.videoURLs;
            },
            sendBackTask: function(versionNumber, notes) {

                var url = getTaskSaveAPIUrl(EditorData.team_slug,
                        EditorData.task_id);

                var promise = $http({
                    method: 'PUT',
                    url: url,
                    headers: authHeaders(),
                    data:  {
                        complete: true,
                        body: notes,
                        send_back: true,
                        version_number: versionNumber,
                    }
                });

                return promise;

            },
            saveSubtitles: function(subString, title, duration, description, metadata, isComplete, action, sub_format, upload) {
                var videoID = EditorData.video.id;
                var languageCode = EditorData.editingVersion.languageCode;

                if(upload) {
                    var origin = 'upload';
                } else {
                    var origin = 'editor';
                }

                var url = getSubtitlesAPIURL(videoID, languageCode);
                // if isComplete is not specified as true or false, we send
                // null, which means keep the complete flag the same as before
                if(isComplete !== true && isComplete !== false) {
                    isComplete = null;
                }
                var promise = $http({
                    method: 'POST',
                    url: url,
                    headers: authHeaders(),
                    data:  {
                        video: videoID,
                        language: languageCode,
                        subtitles: subString,
                        sub_format: sub_format,
                        title: title,
                        description: description,
                        origin: origin,
                        metadata: metadata,
                        action: action,
                        duration: duration,
                    }
                });

                return promise;
            }
        };
    }]);
    module.factory('SubtitleBackupStorage', ["$window", function($window) {
        /**
         * Get the editor data that was passed to us from python
         *
         */
        var storage = $window.localStorage;
        var storageKey = 'amara-subtitle-backup';

        function getSavedData() {
            var data = $window.localStorage.getItem(storageKey);
            if(data === null) {
                return null;
            } else {
                try {
                    return JSON.parse(data);
                } catch (e) {
                    return null;
                }

            }
        }

        function savedDataIsValid(savedData, videoId, languageCode, versionNumber) {
                return (savedData !== null &&
                        savedData.videoId == videoId &&
                        savedData.languageCode == languageCode &&
                        savedData.versionNumber == versionNumber);
        }

        return {
            saveBackup: function(videoId, languageCode, versionNumber, dfxpString) {
                var data = {
                    videoId: videoId,
                    languageCode: languageCode,
                    versionNumber: versionNumber,
                    dfxpString: dfxpString
                }
                $window.localStorage.setItem(storageKey,
                        JSON.stringify(data));
            },
            hasBackup: function(videoId, languageCode, versionNumber) {
                return savedDataIsValid(getSavedData(), videoId,
                        languageCode, versionNumber);
            },
            hasAnyBackup: function() {
                return getSavedData() !== null;
            },
            getBackup: function(videoId, languageCode, versionNumber) {
                var savedData = getSavedData();
                if(savedDataIsValid(savedData, videoId, languageCode,
                            versionNumber)) {
                    this.clearBackup();
                    return savedData.dfxpString;
                } else {
                    return null;
                }
            },
            clearBackup: function() {
                $window.localStorage.removeItem(storageKey);
            },
        };
    }]);

    module.factory('SubtitleSoftLimits', ["EditorData", "gettext", "ngettext", "interpolate", function(EditorData, gettext, ngettext, interpolate) {
        var warningMessages = {};

        function format_ms(value) {
            // forman min/max duration for display
            if(value < 1000) {
                return value + ' ' + gettext('milliseconds');
            } else if (value % 1000 == 0) {
                return (value / 1000) + ' ' + gettext('seconds');
            } else {
                return Math.floor(value / 1000) + '.' + Math.round(value % 1000 / 100) + ' ' + gettext('seconds');
            }
        }

        warningMessages.lines = interpolate(ngettext(
                    'Avoid more than %(count)s line per subtitle; split the subtitle into two.',
                    'Avoid more than %(count)s lines per subtitle; split the subtitle into two.',
                    EditorData.softLimits.lines), { count: EditorData.softLimits.lines}, true);

        warningMessages.minDuration = interpolate(gettext(
                    'Briefly displayed subtitles are hard to read; the duration should be more than %(milliseconds)s.'),
                {milliseconds: format_ms(EditorData.softLimits.min_duration)}, true);

        warningMessages.cps = interpolate(gettext(
                    "Reading rate shouldn't exceed %(count)s characters / sec; lengthen duration, reduce text or split the subtitle."),
                {count: EditorData.softLimits.cps}, true);

        warningMessages.cpl = interpolate(gettext(
                    "Line length shouldn't exceed %(count)s characters; add a line break if necessary."),
                {count: EditorData.softLimits.cpl}, true);

        var guidelines = {};

        guidelines.lines = interpolate(ngettext(
                    "Avoid more than %(count)s line per subtitle.",
                    "Avoid more than %(count)s lines per subtitle.",
                    EditorData.softLimits.lines), { count: EditorData.softLimits.lines}, true);

        guidelines.minDuration = interpolate(gettext('Subtitles should at least %(milliseconds)s.'),
                {milliseconds: format_ms(EditorData.softLimits.min_duration)}, true);

        guidelines.maxDuration = interpolate(gettext('Split subtitles longer than %(milliseconds)s.'),
                {milliseconds: format_ms(EditorData.softLimits.max_duration)}, true);

        guidelines.cps = interpolate(gettext("Reading rate shouldn't exceed %(count)s characters / sec."),
                {count: EditorData.softLimits.cps}, true);

        guidelines.cpl = interpolate(gettext("Keep subtitle length to about %(count)s characters."),
                {count: EditorData.softLimits.cpl}, true);

        return {
            lines: EditorData.softLimits.lines,
            minDuration: EditorData.softLimits.min_duration,
            maxDuration: EditorData.softLimits.max_duration,
            cps: EditorData.softLimits.cps,
            cpl: EditorData.softLimits.cpl,
            warningMessages: warningMessages,
            guidelines: guidelines
        };
    }]);
}).call(this);
