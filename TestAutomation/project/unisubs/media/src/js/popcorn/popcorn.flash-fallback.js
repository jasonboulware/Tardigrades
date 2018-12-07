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

var Popcorn = window.Popcorn || null;
var jQuery = window.jQuery || null;

(function (Popcorn, window, document) {

    var STATIC_ROOT_URL = window._amaraConf ? window._amaraConf.staticURL : window.Amara.conf.STATIC_ROOT_URL;
    var CURRENT_TIME_MONITOR_MS = 16;
    var EMPTY_STRING = "";

    function HTMLFlashFallbackVideoElement(id) {

        // FlashFallback iframe API requires postMessage
        if (!window.postMessage) {
            throw "ERROR: HTMLFlashFallbackVideoElement requires window.postMessage";
        }

        var self = this;
        var parent = typeof id === "string" ? Popcorn.dom.find(id) : id;
        var elem = document.createElement("div");

        var impl = {
            src: EMPTY_STRING,
            networkState: self.NETWORK_EMPTY,
            readyState: self.HAVE_NOTHING,
            seeking: false,
            autoplay: EMPTY_STRING,
            preload: EMPTY_STRING,
            controls: false,
            loop: false,
            poster: EMPTY_STRING,
            // FlashFallback seems to use .77 as default
            volume: 1,
            // FlashFallback has no concept of muted, store volume values
            // such that muted===0 is unmuted, and muted>0 is muted.
            muted: 0,
            currentTime: 0,
            ended: false,
            paused: true,
            error: null
        };

        var playerReady = false;
        var playerUID = Popcorn.guid();
        var player;
        var playerReadyCallbacks = [];
        var timeUpdateInterval;
        var currentTimeInterval;
        var lastCurrentTime = 0;

        elem.id = Popcorn.guid("amara-flowplayer");
        elem.style.height = '100%';

        window.elem = elem;

        // Namespace all events we'll produce
        self._eventNamespace = Popcorn.guid("HTMLFlashFallbackVideoElement::");

        self.parentNode = parent;

        // Mark type as FlashFallback
        self._util.type = "FlashFallback";

        function addPlayerReadyCallback(callback) {
            playerReadyCallbacks.unshift(callback);
        }

        function onPlayerReady() {
            var objEl =  jQuery("object", elem).eq(0);

            var clip = player.getClip(0);
            player.onVolume(function(newVolume) {
                if (impl.volume !== aValue) {
                    impl.volume = aValue;
                    self.dispatchEvent("volumechange");
                }
            });
            playerReady = true;
            clip.onResume(function () {
                onPlay();
            });
            clip.onFinish(function () {
                onPause();
            });
            clip.onPause(function () {
                onPause();
            });
            clip.onStop(function () {
                onPause();
            });
            clip.onStart(function () {
                onPlay();
            });
            // Popcorn needs this sequence of states to be set,
            // then the events dispatched so it can hook up
            // the listeners, don't touch this or bad things
            // **will happen**.
            impl.networkState = self.NETWORK_IDLE;
            impl.readyState = self.HAVE_METADATA;
            self.dispatchEvent( "loadedmetadata" );

            self.dispatchEvent( "loadeddata" );

            impl.readyState = self.HAVE_FUTURE_DATA;
            self.dispatchEvent( "canplay" );

            impl.readyState = self.HAVE_ENOUGH_DATA;
            self.dispatchEvent( "canplaythrough" );
        }

        function onPlayerJSReady(event) {
            parent.appendChild(elem);
            var flashEmbedParams = {
                'src': STATIC_ROOT_URL + "flowplayer/flowplayer-3.2.18.swf",
                'wmode': 'opaque',
                'width': '100%',
                'height': '100%'
            };
            var config = {
                'playlist': [
                    {
                        'url': impl.src,
                        'autoPlay': false
                    }
                ],
                'onLoad': function () {
                    onPlayerReady();
                },
                plugins:{
                    // controls are ideally disabled in editor and enabled
                    // in embedder, which is not obvious to make it optional
                    // with popcorn API, so putting it always on for now
                    // controls: null,
                }
            };
            player = player = window.$f(elem, flashEmbedParams, config);

            impl.networkState = self.NETWORK_LOADING;
            self.dispatchEvent("loadstart");
            self.dispatchEvent("progress");
        }

        function getDuration() {
            if (!playerReady) {
                return NaN;
            }
            return player.getClip(0).duration;
        }

        function destroyPlayer() {
            if (!( playerReady && player )) {
                return;
            }
            clearInterval(currentTimeInterval);
            player.pause();
            parent.removeChild(elem);
            elem = document.createElement("div");
        }

        self.play = function () {
            if (!playerReady) {
                addPlayerReadyCallback(function () {
                    self.play();
                });
                return;
            }

            player.play();
        };

        function changeCurrentTime(aTime) {
            if (!playerReady) {
                addPlayerReadyCallback(function () {
                    changeCurrentTime(aTime);
                });
                return;
            }

            onSeeking();
            player.seek(aTime);
        }

        function onSeeking() {
            impl.seeking = true;
            self.dispatchEvent("seeking");
        }

        function onSeeked() {
            impl.seeking = false;
            self.dispatchEvent("timeupdate");
            self.dispatchEvent("seeked");
            self.dispatchEvent("canplay");
            self.dispatchEvent("canplaythrough");
        }

        self.pause = function () {
            if (!playerReady) {
                addPlayerReadyCallback(function () {
                    self.pause();
                });
                return;
            }
            player.pause();
        };

        function onPause() {
            impl.paused = true;
            clearInterval(timeUpdateInterval);
            self.dispatchEvent("pause");
        }

        function onTimeUpdate() {
            self.dispatchEvent("timeupdate");
        }

        function onPlay() {
            if (impl.ended) {
                changeCurrentTime(0);
            }
            if (!currentTimeInterval) {
                currentTimeInterval = setInterval(monitorCurrentTime,
                    CURRENT_TIME_MONITOR_MS);
                // Only 1 play when video.loop=true
                if (impl.loop) {
                    self.dispatchEvent("play");
                }
            }
            timeUpdateInterval = setInterval(onTimeUpdate,
                self._util.TIMEUPDATE_MS);

            if (impl.paused) {
                impl.paused = false;
                // Only 1 play when video.loop=true
                if (!impl.loop) {
                    self.dispatchEvent("play");
                }
                self.dispatchEvent("playing");
            }
        }

        function onEnded() {
            if (impl.loop) {
                changeCurrentTime(0);
                self.play();
            } else {
                impl.ended = true;
                self.dispatchEvent("ended");
            }
        }

        function onCurrentTime(aTime) {
            var currentTime = impl.currentTime = aTime;

            if (currentTime !== lastCurrentTime) {
                self.dispatchEvent("timeupdate");
            }

            lastCurrentTime = impl.currentTime;
        }

        function monitorCurrentTime() {
            onCurrentTime(player.getTime());
        }

        function loadFlowPlayerJs() {
            var el = document.createElement("script");
            el.src = STATIC_ROOT_URL + "flowplayer/flowplayer-3.2.13.min.js";
            var firstScriptTag = document.getElementsByTagName('script')[0];
            firstScriptTag.parentNode.insertBefore(el, firstScriptTag);
            var intervalId = setInterval(function () {
                if (window.flowplayer && window.$f) {
                    clearInterval(intervalId);
                    onPlayerJSReady();
                }
            }, 200);
        }

        function changeSrc(aSrc) {
            if (!self._canPlaySrc(aSrc)) {
                var MediaError = MediaError || null;
                impl.error = {
                    name: "MediaError",
                    message: "Media Source Not Supported",
                    code: MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED
                };
                self.dispatchEvent("error");
                return;
            }
            impl.src = aSrc;
            loadFlowPlayerJs();
            return;
        }

        function setVolume(aValue) {
            impl.volume = aValue * 100;

            if (!playerReady) {
                addPlayerReadyCallback(function () {
                    setVolume(aValue);
                });
                return;
            }
            player.setVolume(impl.volume);
        }

        function getVolume() {
            // If we're muted, the volume is cached on impl.muted.
            return impl.muted > 0 ? impl.muted : impl.volume / 100;
        }

        function setMuted(aMute) {
            if (!playerReady) {
                impl.muted = aMute ? 1 : 0;
                addPlayerReadyCallback(function () {
                    setMuted(aMute);
                });
                return;
            }

            // Move the existing volume onto muted to cache
            // until we unmute, and set the volume to 0.
            if (aMute) {
                impl.muted = impl.volume;
                setVolume(0);
            } else {
                impl.muted = 0;
                setVolume(impl.muted);
            }
        }

        function getMuted() {
            return impl.muted > 0;
        }

        Object.defineProperties(self, {

            src: {
                get: function () {
                    return impl.src;
                },
                set: function (aSrc) {
                    if (aSrc && aSrc !== impl.src) {
                        changeSrc(aSrc);
                    }
                }
            },

            autoplay: {
                get: function () {
                    return impl.autoplay;
                },
                set: function (aValue) {
                    impl.autoplay = self._util.isAttributeSet(aValue);
                }
            },

            loop: {
                get: function () {
                    return impl.loop;
                },
                set: function (aValue) {
                    impl.loop = self._util.isAttributeSet(aValue);
                }
            },

            width: {
                get: function () {
                    return self.parentNode.offsetWidth;
                }
            },

            height: {
                get: function () {
                    return self.parentNode.offsetHeight;
                }
            },

            currentTime: {
                get: function () {
                    return impl.currentTime;
                },
                set: function (aValue) {
                    changeCurrentTime(aValue);
                }
            },

            duration: {
                get: function () {
                    return getDuration();
                }
            },

            ended: {
                get: function () {
                    return impl.ended;
                }
            },

            paused: {
                get: function () {
                    return impl.paused;
                }
            },

            seeking: {
                get: function () {
                    return impl.seeking;
                }
            },

            readyState: {
                get: function () {
                    return impl.readyState;
                }
            },

            networkState: {
                get: function () {
                    return impl.networkState;
                }
            },

            volume: {
                get: function () {
                    return getVolume();
                },
                set: function (aValue) {
                    if (aValue < 0 || aValue > 1) {
                        throw "Volume value must be between 0.0 and 1.0";
                    }

                    setVolume(aValue);
                }
            },

            muted: {
                get: function () {
                    return getMuted();
                },
                set: function (aValue) {
                    setMuted(self._util.isAttributeSet(aValue));
                }
            },

            error: {
                get: function () {
                    return impl.error;
                }
            }
        });
    }

    HTMLFlashFallbackVideoElement.prototype = new Popcorn._MediaElementProto();
    HTMLFlashFallbackVideoElement.prototype.constructor = HTMLFlashFallbackVideoElement;

    // Helper for identifying URLs we know how to play.
    HTMLFlashFallbackVideoElement.prototype._canPlaySrc = function (url) {
        var isH264 = /\.(mp4|m4v)(\?.*)?$/i.test(url);
        var isFlv = (/\.flv(\?.*)?$/i.test(url));
        var supportsVideo = !!document.createElement('video').canPlayType;

        // does this browser supports the native h264?
        var v = document.createElement("video");
        var canPlayH264 = v.canPlayType('video/mp4; codecs="avc1.42E01E, mp4a.40.2"');
        if ((isFlv) || (isH264 && (!supportsVideo || !canPlayH264))) {
            return "probably";
        }
    };

    Popcorn.HTMLFlashFallbackVideoElement = function (id) {
        return new HTMLFlashFallbackVideoElement(id);
    };
    Popcorn.HTMLFlashFallbackVideoElement._canPlaySrc = HTMLFlashFallbackVideoElement.prototype._canPlaySrc;

}(Popcorn, window, document));
