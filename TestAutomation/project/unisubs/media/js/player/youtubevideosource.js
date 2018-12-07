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

goog.provide('unisubs.player.YoutubeVideoSource');

/**
 * @constructor
 * @implements {unisubs.player.MediaSource}
 * @param {string} youtubeVideoID Youtube video id
 * @param {Object.<string, *>=} opt_videoConfig Params to use for 
 *     youtube query string, plus optional 'width' and 'height' 
 *     parameters.
 */
unisubs.player.YoutubeVideoSource = function(youtubeVideoID, opt_videoConfig) {
    this.youtubeVideoID_ = youtubeVideoID;
    this.uuid_ = unisubs.randomString();
    this.videoConfig_ = opt_videoConfig;
};
unisubs.player.YoutubeVideoSource.extractVideoID = function(videoURL) {
    var videoIDExtract = /(?:v[\/=]|embed\/|youtu\.be\/)([0-9a-zA-Z\-\_]+)/i.exec(videoURL);
    return videoIDExtract ? videoIDExtract[1] : null;
};
unisubs.player.YoutubeVideoSource.forURL = function(videoURL, opt_videoConfig) {
    var videoID = unisubs.player.YoutubeVideoSource.extractVideoID(videoURL);
    if (videoID)
        return new unisubs.player.YoutubeVideoSource(
            videoID, opt_videoConfig);
    else
        return null;
};
unisubs.player.YoutubeVideoSource.isYoutube = function(videoURL) {
    return (/^\s*https?:\/\/([^\.]+\.)?youtu\.?be/i).test(videoURL);
};
unisubs.player.YoutubeVideoSource.prototype.createPlayer = function() {
    return this.createPlayerInternal(false);
};
unisubs.player.YoutubeVideoSource.prototype.createControlledPlayer = function() {
    return new unisubs.player.ControlledVideoPlayer(this.createPlayerInternal(true));
};

/**
 * @protected
 */
unisubs.player.YoutubeVideoSource.prototype.createPlayerInternal = function(forDialog) {
    return new unisubs.player.YoutubeVideoPlayer(
        new unisubs.player.YoutubeVideoSource(
            this.youtubeVideoID_, this.videoConfig_), 
        forDialog);
};

unisubs.player.YoutubeVideoSource.prototype.getYoutubeVideoID = function() {
    return this.youtubeVideoID_;
};
unisubs.player.YoutubeVideoSource.prototype.getUUID = function() {
    return this.uuid_;
};
unisubs.player.YoutubeVideoSource.prototype.getVideoConfig = function() {
    return this.videoConfig_;
};
unisubs.player.YoutubeVideoSource.prototype.setVideoConfig = function(config) {
    this.videoConfig_ = config;
};
unisubs.player.YoutubeVideoSource.prototype.sizeFromConfig = function() {
    if (this.videoConfig_ && this.videoConfig_['width'] && 
        this.videoConfig_['height']) {
        return new goog.math.Size(
            parseInt(this.videoConfig_['width'], 0), parseInt(this.videoConfig_['height'], 0));
    }
    else {
        return null;
    }
};
unisubs.player.YoutubeVideoSource.prototype.getVideoURL = function() {
    return "http://www.youtube.com/watch?v=" + this.youtubeVideoID_;
};

/**
* Checks if this video url is indeed for this MediaSource type, returns a
* mediaSource subclass if it is, null if it isn't
*/
unisubs.player.YoutubeVideoSource.getMediaSource = function(videoURL, opt_videoConfig) {
    if (unisubs.player.YoutubeVideoSource.isYoutube(videoURL)) {
        var videoSource = null;
        if (!window['swfobject']["hasFlashPlayerVersion"]("9")) {
            videoSource = unisubs.player.YTIFrameVideoSource.forURL(
                videoURL, opt_videoConfig);
        }
        else {
            videoSource = unisubs.player.YoutubeVideoSource.forURL(
                videoURL, opt_videoConfig);
        }
        if (videoSource != null){
            return videoSource;
        }
    }
    return null;
}

// add this mediaSource to our registry
unisubs.player.MediaSource.addMediaSource(unisubs.player.YoutubeVideoSource.getMediaSource);
