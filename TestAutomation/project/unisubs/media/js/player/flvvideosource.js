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

goog.provide('unisubs.player.FlvVideoSource');

/**
 * @constructor
 * @implements {unisubs.player.MediaSource}
 * @param {string} flvURL
 * @param {Object=} opt_videoConfig Plugins to use for FlowPlayer 
 *     (see http://flowplayer.org/documentation/configuration/plugins.html)
 *     plus optional 'width' and 'height' parameters.
 */
unisubs.player.FlvVideoSource = function(flvURL, opt_videoConfig) {
    this.flvURL_ = flvURL;
    this.videoConfig_ = opt_videoConfig;
};

unisubs.player.FlvVideoSource.prototype.createPlayer = function() {
    return this.createPlayer_(false);
};

unisubs.player.FlvVideoSource.prototype.createControlledPlayer = function() {
    return new unisubs.player.ControlledVideoPlayer(this.createPlayer_(true));
};

unisubs.player.FlvVideoSource.prototype.createPlayer_ = function(chromeless) {
    return new unisubs.player.FlvVideoPlayer(this, chromeless);
};

unisubs.player.FlvVideoSource.prototype.getFlvURL = function() {
    return this.flvURL_;
};

unisubs.player.FlvVideoSource.prototype.getVideoURL = function() {
    return this.getFlvURL();
};

unisubs.player.FlvVideoSource.prototype.getVideoConfig = function() {
    return this.videoConfig_;
};

unisubs.player.FlvVideoSource.prototype.setVideoConfig = function(config) {
    this.videoConfig_ = config;
};

unisubs.player.FlvVideoSource.prototype.sizeFromConfig = function() {
    if (this.videoConfig_ && this.videoConfig_['width'] && 
        this.videoConfig_['height']) {
        return new goog.math.Size(
            parseInt(this.videoConfig_['width']), parseInt(this.videoConfig_['height']));
    }
    else {
        return null;
    }
};

/**
* Checks if this video url is indeed for this MediaSource type, returns a
* mediaSource subclass if it is, null if it isn't
*/
unisubs.player.FlvVideoSource.getMediaSource = function(videoURL, opt_videoConfig) {
    if (/\.flv$|\.mov$/i.test(videoURL)) {
        return new unisubs.player.FlvVideoSource(videoURL, opt_videoConfig);
    }
    return null;
}

// add this mediaSource to our registry
unisubs.player.MediaSource.addMediaSource(unisubs.player.FlvVideoSource.getMediaSource);
