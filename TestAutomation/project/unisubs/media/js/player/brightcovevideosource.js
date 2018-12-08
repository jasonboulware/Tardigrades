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

goog.provide('unisubs.player.BrightcoveVideoSource');
/**
 * @constructor
 * @implements {unisubs.player.MediaSource}
 * @param {string} playerID Brightcove player id
 * @param {string} playerKey Brightcove player key
 * @param {string} videoID Brightcove video id* 
 * @param {Object.<string, *>=} opt_videoConfig Params to use for 
 *     brightCove query string, plus optional 'width' and 'height' 
 *     parameters.
 */
unisubs.player.BrightcoveVideoSource = function(playerID, playerKey, videoID, opt_videoConfig) {
    this.playerID_ = playerID;
    this.videoID_ = videoID;
    this.playerKey_ = playerKey;
    this.uuid_ = unisubs.randomString();
    this.videoConfig_ = opt_videoConfig;
};

/* @const
 * @type {string} 
 */
unisubs.player.BrightcoveVideoSource.BASE_DOMAINS = ["brightcove.com", "bcove.me"];

unisubs.player.BrightcoveVideoSource.forURL = 
    function(videoURL, opt_videoConfig) 
{
    
    if (unisubs.player.BrightcoveVideoSource.isBrightcove(videoURL)){
        var uri = new goog.Uri(videoURL);
        var playerKey = uri.getParameterValue("bckey");
        var videoID = uri.getParameterValue("bctid");
        var playerID;
        try{
             playerID =  /bcpid([\d])+/.exec(videoURL)[0].substring(5);
        }catch(e){
            
        }
        if (!opt_videoConfig){
            opt_videoConfig = {};
        }
        opt_videoConfig["uri"] = videoURL;
        if (playerID){
            return new unisubs.player.BrightcoveVideoSource(
                playerID, playerKey, videoID, opt_videoConfig);    
        }
        
    }
    return null;
};

unisubs.player.BrightcoveVideoSource.isBrightcove = function(videoURL) {
    var uri = new goog.Uri(videoURL);
    return unisubs.player.BrightcoveVideoSource.BASE_DOMAINS.reduce(function(previous, current) {
        return (previous || goog.string.caseInsensitiveEndsWith(
            uri.getDomain(),
            current));})
};

unisubs.player.BrightcoveVideoSource.prototype.createPlayer = function() {
    return this.createPlayer_(false);
};

unisubs.player.BrightcoveVideoSource.prototype.createControlledPlayer = 
    function() 
{
    return new unisubs.player.ControlledVideoPlayer(this.createPlayer_(true));
};

unisubs.player.BrightcoveVideoSource.prototype.createPlayer_ = function(forDialog) {
    return new unisubs.player.BrightcoveVideoPlayer(
        new unisubs.player.BrightcoveVideoSource(
            this.playerID_, this.playerKey_, this.videoID_, this.videoConfig_), 
        forDialog);
};

unisubs.player.BrightcoveVideoSource.prototype.getPlayerID = function() {
    return this.playerID_;
};

unisubs.player.BrightcoveVideoSource.prototype.getVideoID = function() {
    return this.videoID_;
};

unisubs.player.BrightcoveVideoSource.prototype.getPlayerKey = function() {
     return this.playerKey_;
};

unisubs.player.BrightcoveVideoSource.prototype.getUUID = function() {
    return this.uuid_;
};

unisubs.player.BrightcoveVideoSource.prototype.getVideoConfig = function() {
    return this.videoConfig_;
};

unisubs.player.BrightcoveVideoSource.prototype.setVideoConfig = function(config) {
    this.videoConfig_ = config;
};


unisubs.player.BrightcoveVideoSource.prototype.getVideoURL = function() {
    return this.videoConfig_["url"];
};
unisubs.player.BrightcoveVideoSource.prototype.sizeFromConfig = function() {
    if (this.videoConfig_ && this.videoConfig_['width'] &&
        this.videoConfig_['height']) {
        return new goog.math.Size(
            parseInt(this.videoConfig_['width'], 0), parseInt(this.videoConfig_['height'], 0));
    }
    else {
        return null;
    }
};

unisubs.player.BrightcoveVideoSource.EMBED_SOURCE = "http://c.brightcove.com/services/viewer/federated_f9?isVid=1&isUI=1";
unisubs.player.BrightcoveVideoSource.prototype.toString = function() {
    return "BrightcoveVideoSource " + this.videoID_;
};

/**
* Checks if this video url is indeed for this MediaSource type, returns a
* mediaSource subclass if it is, null if it isn't
*/
unisubs.player.BrightcoveVideoSource.getMediaSource = function(videoURL, opt_videoConfig) {
    if (unisubs.player.BrightcoveVideoSource.isBrightcove(videoURL)) {
        return unisubs.player.BrightcoveVideoSource.forURL(videoURL);
    }
    return null;
}

// add this mediaSource to our registry
unisubs.player.MediaSource.addMediaSource(unisubs.player.BrightcoveVideoSource.getMediaSource);
