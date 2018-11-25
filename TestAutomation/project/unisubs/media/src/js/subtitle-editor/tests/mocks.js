(function() {

    var module = angular.module('amara.SubtitleEditor.mocks', []);

    module.factory('VideoPlayer', function() {
        var mockVideoPlayer = jasmine.createSpyObj('VideoPlayer', [
            'init',
            'play',
            'pause',
            'seek',
            'togglePlay',
            'currentTime',
            'duration',
            'isPlaying',
            'getVolume',
            'setVolume',
            'playChunk',
        ]);
        mockVideoPlayer._playing = false;
        mockVideoPlayer.isPlaying.and.callFake(function() {
            return mockVideoPlayer._playing;
        });
        mockVideoPlayer.play.and.callFake(function() {
            mockVideoPlayer._playing = true;
        });
        mockVideoPlayer.pause.and.callFake(function() {
            mockVideoPlayer._playing = false;
        });
        mockVideoPlayer._currentTime = 0;
        mockVideoPlayer.currentTime.and.callFake(function() {
            return mockVideoPlayer._currentTime;
        });
        mockVideoPlayer.seek.and.callFake(function(ms) {
            mockVideoPlayer._currentTime = ms;
        });
        return mockVideoPlayer;
    });

    module.factory('PreferencesService', function() {
        return jasmine.createSpyObj('PreferencesService', [
            'setPlaybackMode'
        ]);
    });

    module.factory('SubtitleStorage', ["$q", function($q) {
        var methodNames = [
            'getLanguages',
            'getLanguage',
            'getSubtitles',
            'saveSubtitles',
            'performAction',
            'postNote'
        ];
        var SubtitleStorage = {
            deferreds: {},
        };
        _.each(methodNames, function(methodName) {
            var deferred = $q.defer();
            SubtitleStorage[methodName] = jasmine.createSpy(methodName);
            SubtitleStorage[methodName].and.returnValue(deferred.promise);
            SubtitleStorage.deferreds[methodName] = deferred;
        });
        return SubtitleStorage;
    }]);

    module.factory('DomWindow', function() {
        var mockObject = jasmine.createSpyObj('DomWindow', [
            'onDocumentEvent',
            'offDocumentEvent'
        ]);
        mockObject.caretPos = jasmine.createSpy('caretPos').and.returnValue(0);
        return mockObject;
    });

    module.factory('MockEvents', function() {
        function makeEvent(type, attrs) {
            evt = {
                type: type,
                preventDefault: jasmine.createSpy(),
                stopPropagation: jasmine.createSpy(),
            }
            return overrideEventAttributes(evt, attrs);
        }
        function overrideEventAttributes(evt, attrs) {
            if(attrs !== undefined) {
                for(key in attrs) {
                    evt[key] = attrs[key];
                }
            }
            return evt;
        }
        return {
            keydown: function(keyCode, attrs) {
                var evt = makeEvent('keydown');
                evt.keyCode = keyCode;
                evt.shiftKey = false;
                evt.ctrlKey = false;
                evt.altKey = false;
                evt.target = { type: 'div' };
                return overrideEventAttributes(evt, attrs);
            },
            click: function(attrs) {
                return makeEvent('click', attrs);
            },
        }
    });

    module.factory('EditorData', function() {
        return {
            "username": "testuser",
            "user_fullname": "Test User",
            "canSync": true,
            "canAddAndRemove": true,
            "languageCode": "en",
            "editingVersion": {
                "languageCode": "en",
                "versionNumber": null,
            },
            "video": {
                "id": "4oqOXzpPk5rU",
                "videoURLs": [
                    "http://vimeo.com/25082970"
                ],
            },
            "oldEditorURL": '/old-editor/test-url/',
            "languages": [
                {
                    "is_rtl": false,
                    "numVersions": 0,
                    "editingLanguage": true,
                    "language_code": "en",
                    "pk": 23,
                    "versions": [],
                    "is_primary_audio_language": true,
                    "name": "English"
                },
            ],
            'notes': [],
            'staticURL': 'http://example.com/',
            'preferences': {}
        };
    });

    module.factory('$timeout', function($q, $rootScope) {
        var timeouts = [];

        var mockTimeout = jasmine.createSpy('$timeout')
            .and.callFake(function(callback, delay) {
                var deferred = $q.defer();
                var promise = deferred.promise;
                var timeout = {
                    msLeft: delay,
                    deferred: deferred,
                    callback: callback,
                    completed: false
                };

                promise.index = timeouts.length;
                promise.then(callback);
                timeouts.push(timeout);
                return promise;
            });
        mockTimeout.cancel = jasmine.createSpy('cancel')
            .and.callFake(function(promise) {
                var timeout = timeouts[promise.index];
                timeout.completed = true;
                timeout.deferred.reject("timeout canceled");
            });
        mockTimeout.flush = jasmine.createSpy('flush')
            .and.callFake(function() {
                $.each(timeouts, function(index, timeout) {
                    if(!timeout.completed) {
                        timeout.completed = true;
                        timeout.deferred.resolve("timeout flushed");
                    }
                });
                timeouts.length = 0;
                $rootScope.$apply();
            });

        mockTimeout.simulateTime = function(ms) {
            for(var i = 0; i < timeouts.length; ++i) {
                var timeout = timeouts[i];
                if(!timeout.completed) {
                    timeout.msLeft -= ms;
                    if(timeout.msLeft <= 0) {
                        timeout.msLeft = 0;
                        timeout.completed = true;
                        timeout.deferred.resolve("timeout simulated");
                    }
                }
            }
            $rootScope.$apply();
        };
        return mockTimeout;
    });

    module.factory('SubtitleSoftLimits', function() {
	var warningMessages = {};

        warningMessages.lines = 'Too many lines';
        warningMessages.timing = 'Too short duration';
        warningMessages.cps = 'Too many characters per second';
        warningMessages.cpl = 'Too many characters per line';

        return {
            lines: 2,
            timing: 700,
            cps: 21,
            cpl: 42,
            warningMessages: warningMessages
        };
    });

    module.value('gettext', jasmine.createSpy().and.callFake(function(text) { return text; }));
    module.value('pgettext', jasmine.createSpy().and.callFake(function(context, text) { return text; }));
    module.value('interpolate', function(text, data, named) {
        // It's not so easy to implement interpolate.  Just return the raw data so it can be checked
        return {
            text: text,
            data: data,
            named: Boolean(named)
        };
    });
}).call(this);
