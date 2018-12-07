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

goog.provide('unisubs.player.DailymotionVideoSource');

/**
 * @constructor
 * @implements {unisubs.player.MediaSource}
 */
unisubs.player.DailymotionVideoSource = function(videoID, videoURL, opt_videoConfig) {
    this.videoID_ = videoID;
    this.videoURL_ = videoURL;
    this.uuid_ = unisubs.randomString();
    
    this.videoConfig_ = opt_videoConfig;
};

unisubs.player.DailymotionVideoSource.prototype.createPlayer = function() {
    return this.createPlayer_(false, false);
};

unisubs.player.DailymotionVideoSource.prototype.createControlledPlayer = function() {
    return new unisubs.player.ControlledVideoPlayer(this.createPlayer_(true, true));
};

unisubs.player.DailymotionVideoSource.prototype.createPlayer_ = function(chromeless, forDialog) {
    return new unisubs.player.DailymotionVideoPlayer(
        new unisubs.player.DailymotionVideoSource(this.videoID_, this.videoURL_, this.videoConfig_), 
        chromeless, forDialog);
};

unisubs.player.DailymotionVideoSource.prototype.sizeFromConfig = function() {
    if (this.videoConfig_ && this.videoConfig_['width'] && 
        this.videoConfig_['height']) {
        return new goog.math.Size(
            parseInt(this.videoConfig_['width']), parseInt(this.videoConfig_['height']));
    }
    else {
        return null;
    }
};


unisubs.player.DailymotionVideoSource.prototype.getVideoId = function() {
    return this.videoID_;
};

unisubs.player.DailymotionVideoSource.prototype.getUUID = function() {
    return this.uuid_;
};

unisubs.player.DailymotionVideoSource.prototype.getVideoURL = function() {
    return this.videoURL_;
};

unisubs.player.DailymotionVideoSource.prototype.setVideoConfig = function(config) {
    this.videoConfig_ = config;
};

/**
* Checks if this video url is indeed for this MediaSource type, returns a
* mediaSource subclass if it is, null if it isn't
*/
unisubs.player.DailymotionVideoSource.getMediaSource = function(videoURL, opt_videoConfig) {
    if (/^\s*https?:\/\/([^\.]+\.)?dailymotion/.test(videoURL)) {
        var videoIDExtract = /dailymotion.com\/video\/([0-9a-z]+)/i.exec(videoURL);
        if (videoIDExtract)
            return new unisubs.player.DailymotionVideoSource(
                videoIDExtract[1], videoURL, opt_videoConfig);
    }
    return null;
}

// add this mediaSource to our registry
unisubs.player.MediaSource.addMediaSource(unisubs.player.DailymotionVideoSource.getMediaSource);
