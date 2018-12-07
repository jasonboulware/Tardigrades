// Amara, universalsubtitles.org
// 
// Copyright (C) 2012 Participatory Culture Foundation
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

goog.provide('unisubs.player.WistiaVideoPlayer');

/**
 * @constructor
 */
 
 /***
 
 UGLY: this is ripped from the YTIFrame player 
 
 
 ***/
 
 
unisubs.player.WistiaVideoPlayer = function(videoSource, opt_forDialog) {
    unisubs.player.AbstractVideoPlayer.call(this, videoSource);
    this.player_ = null;
    this.videoSource_ = videoSource;
    this.playerElemID_ = unisubs.randomString() + "_wistiaplayer";
    this.forDialog_ = !!opt_forDialog;
    this.commands_ = [];
    this.progressTimer_ = new goog.Timer(
        unisubs.player.AbstractVideoPlayer.PROGRESS_INTERVAL);
    this.timeUpdateTimer_ = new goog.Timer(
        unisubs.player.AbstractVideoPlayer.TIMEUPDATE_INTERVAL);
    this.videoPlayerType_ = 'wistia';

    this.player_ = null;
    this.modeSelect = null;
};
goog.inherits(unisubs.player.WistiaVideoPlayer, unisubs.player.AbstractVideoPlayer);

unisubs.player.WistiaVideoPlayer.prototype.isChromeless = function() {
    return true;
};

unisubs.player.WistiaVideoPlayer.prototype.setDimensionsKnownInternal = function() {
    this.dimensionsKnown_ = true;
    var size = this.getVideoSize();
    unisubs.style.setSize(this.getElement(), size.width, size.height);
    this.dispatchEvent(
        unisubs.player.AbstractVideoPlayer.EventType.DIMENSIONS_KNOWN);
};

unisubs.player.WistiaVideoPlayer.prototype.getVideoSize = function() {
    return this.playerSize_;
};
unisubs.player.WistiaVideoPlayer.prototype.getDuration = function() {
    return this.player_['duration']();
};
unisubs.player.WistiaVideoPlayer.isWistiaAPIReady = function() {
    var isReady =  window['Wistia'] && window['Wistia']['embed'];
    return isReady;
};

unisubs.player.WistiaVideoPlayer.prototype.onWistiaAPIReady = function(videoId, containerID) 
{
    this.player_ = window['Wistia']['embed'](videoId, {
        'playerColor': "ff0000",
        'fullscreenButton': false,
        'container': containerID,
        'autoplay': false,
        'chromeless': this.forDialog_,
        'controlsVisibleOnLoad': !this.forDialog_,
        'doNotTrack': true,
        'playButton': ! this.forDialog_,
        'playBar': ! this.forDialog_,
        'videoFoam': false
    });
    // add listeners to buttons
    var play_btn = goog.dom.getElementByClass('unisubs-play-beginner');
    if (play_btn){

        goog.events.listen(play_btn, goog.events.EventType.CLICK, goog.bind(this.playInternal, this));
    }
    // add listeners for TAB key
    var that = this;
    // player controls
    var boundFunc = goog.bind(that.playPause, that);
    var playPauseBtn = goog.dom.getElementByClass('unisubs-playPause');
    if (playPauseBtn){
        goog.events.listen(playPauseBtn,
            goog.events.EventType.CLICK, boundFunc);
    }
    this.player_['bind']('timechange', function(t){that.onPlayerTimeChanged(t);});
    // init the player correctly else play pause states will be weird
    this.player_['play']() && this.player_['pause']();
};

unisubs.player.WistiaVideoPlayer.prototype.onPlayerTimeChanged = function(newTime) {
    this.playTime_ = newTime *1000;
    this.dispatchEvent(
        unisubs.player.AbstractVideoPlayer.EventType.TIMEUPDATE);
};

unisubs.player.WistiaVideoPlayer.prototype.playPause = function() {
    if (! this.player_){
        this.commands_.push(goog.bind(this, this.playPause));
        return;
    }
    return;
    if (this.isPlaying()){
        this.pauseInternal();
    }else{
        this.playInternal();
    }
}
unisubs.player.WistiaVideoPlayer.prototype.createDom = function() {
    unisubs.player.WistiaVideoPlayer.superClass_.createDom.call(this);
    this.setPlayerSize_();
    var embedUri = new goog.Uri(
        "http://fast.wistia.com/embed/iframe/" + 
            this.videoSource_.getVideoId());
    this.addQueryString_(embedUri);

    var sizeFromConfig = this.videoSource_.sizeFromConfig();
    if (!this.forDialog_ && sizeFromConfig)
        this.playerSize_ = sizeFromConfig;
    else
        this.playerSize_ = this.forDialog_ ?
        unisubs.player.AbstractVideoPlayer.DIALOG_SIZE :
        unisubs.player.AbstractVideoPlayer.DEFAULT_SIZE;
    this.setDimensionsKnownInternal();

    div_args = {
        'id': this.playerElemID_,
        'data-video-width': this.playerSize_.width + '',
        'data-video-height': this.playerSize_.height + '', 
        'style': unisubs.style.setSizeInString('', this.playerSize_) 
    };
    var videoDiv = this.getDomHelper().createDom('div', div_args);
    this.getElement().appendChild(videoDiv);
    var that = this;
	unisubs.addScript(
        "http://fast.wistia.com/static/E-v1.js",
        true,
        unisubs.player.WistiaVideoPlayer.isWistiaAPIReady,
        function(){
            that.onWistiaAPIReady(that.videoSource_.getVideoId(), that.playerElemID_);
     });

};

unisubs.player.WistiaVideoPlayer.prototype.setPlayheadTime = function(t) {
    if (!this.player_) {
        this.commands_.push(goog.bind(this.setPlayheadTime, this, t));
        return;
    }
    this.player_['time'](t);
};

unisubs.player.WistiaVideoPlayer.prototype.pauseInternal = function() {
    if (!this.player_){
        this.commands_.push(goog.bind(this.pauseInternal, this));
        return;
    }
    this.player_['pause']();
    this.paused = true;
    this.timeUpdateTimer_.stop();
    this.dispatchEvent(unisubs.player.AbstractVideoPlayer.EventType.PAUSE);
};

unisubs.player.WistiaVideoPlayer.prototype.playInternal = function() {
    if (! this.player_) {
        this.commands_.push(goog.bind(this.playInternal, this));
        return;
    }
    this.player_['play']();
    this.paused = false;
    this.timeUpdateTimer_.start();
    this.dispatchEvent(unisubs.player.AbstractVideoPlayer.EventType.PLAY);
};

unisubs.player.WistiaVideoPlayer.prototype.progressTick_ = function(e) {
    if (this.getDuration() > 0)
        this.dispatchEvent(
            unisubs.player.AbstractVideoPlayer.EventType.PROGRESS);
};

unisubs.player.WistiaVideoPlayer.prototype.addQueryString_ = function(uri) {
    var config = this.videoSource_.getVideoConfig();
    if (!this.forDialog_ && config) {
        for (var prop in config) {
            if (prop != 'width' && prop != 'height')
                uri.setParameterValue(prop, config[prop]);
        }
    }
    var locationUri = new goog.Uri(window.location);
    var domain = window.location.protocol + "//" + 
        locationUri.getDomain() + 
        (locationUri.getPort() != null ? (':' + locationUri.getPort()) : '');
    uri.setParameterValue('origin', domain).
        setParameterValue('wmode', 'opaque').
        setParameterValue('videoWidth',400).
        setParameterValue('videoHeight',300).
        setParameterValue('doNotTrack',true);
        
    if (this.forDialog_) {
        uri.setParameterValue('playbar',false).
        setParameterValue('chromeless', true);
    }
};

unisubs.player.WistiaVideoPlayer.prototype.setPlayerSize_ = function() {
    /*var sizeFromConfig = this.videoSource_.sizeFromConfig();
    if (!this.forDialog_ && sizeFromConfig)
        this.playerSize_ = sizeFromConfig;
    else
        this.playerSize_ = this.forDialog_ ?
        unisubs.player.AbstractVideoPlayer.DIALOG_SIZE :
        unisubs.player.AbstractVideoPlayer.DEFAULT_SIZE;
        */
      this.playerSize_ = unisubs.player.AbstractVideoPlayer.DEFAULT_SIZE
    this.setDimensionsKnownInternal();
};

unisubs.player.WistiaVideoPlayer.prototype.decorateInternal = function(elem) {
    unisubs.player.WistiaVideoPlayer.superClass_.decorateInternal.call(this, elem);
    this.iframe_ = elem;
    if (elem.id) {
        this.playerElemID_ = elem.id;
    }
    else {
        elem.id = this.playerElemID_;
    }
    
    this.playerSize_ = new goog.math.Size(
        parseInt(400), parseInt(300));
    this.setDimensionsKnownInternal();
};

unisubs.player.WistiaVideoPlayer.prototype.enterDocument = function() {
    unisubs.player.WistiaVideoPlayer.superClass_.enterDocument.call(this);
    var w = window;
    if (w['Wistia'] && w['Wistia']['Player'])
        this.makePlayer_();
    else {
        var readyFunc = "onYouTubePlayerAPIReady";
        var oldReady = goog.nullFunction;
        if (w[readyFunc])
            oldReady = w[readyFunc];
        var myOnReady = goog.bind(this.makePlayer_, this);
        window[readyFunc] = function() {
            oldReady();
            myOnReady();
        };
    }
    this.getHandler().
        listen(this.timeUpdateTimer_, goog.Timer.TICK, this.timeUpdateTick_);
    this.progressTimer_.start();
};

unisubs.player.WistiaVideoPlayer.prototype.makePlayer_ = function() {
};

unisubs.player.WistiaVideoPlayer.prototype.playerStateChange_ = function (data) {
}

unisubs.player.WistiaVideoPlayer.prototype.playerReady_ = function(e) {
    this.player_ = this.almostPlayer_;
    goog.array.forEach(this.commands_, function(cmd) { cmd(); });
    this.commands_ = [];
    this.getHandler().
        listen(this.progressTimer_, goog.Timer.TICK, this.progressTick_).
        listen(this.timeUpdateTimer_, goog.Timer.TICK, this.timeUpdateTick_);
    this.progressTimer_.start();
};

unisubs.player.WistiaVideoPlayer.prototype.timeUpdateTick_ = function (){
    if (this.getDuration() > 0){
        this.sendTimeUpdateInternal();
    }
}
unisubs.player.WistiaVideoPlayer.prototype.getVideoElements = function() {
    return [this.iframe_];
};

unisubs.player.WistiaVideoPlayer.prototype.disposeInternal = function() {
    unisubs.player.WistiaVideoPlayer.superClass_.disposeInternal.call(this);
    this.progressTimer_.dispose();
    this.timeUpdateTimer_.dispose();
};

unisubs.player.WistiaVideoPlayer.prototype.exitDocument = function() {
    unisubs.player.WistiaVideoPlayer.superClass_.exitDocument.call(this);
    this.progressTimer_.stop();
    this.timeUpdateTimer_.stop();
};

unisubs.player.WistiaVideoPlayer.prototype.isPlaying = function() {
    return this.player_ && this.player_['state']() == 'playing';
};

unisubs.player.WistiaVideoPlayer.prototype.isPaused = function() {
    return this.player_ && this.player_['state']() == 'paused';
};

unisubs.player.WistiaVideoPlayer.prototype.getPlayheadTimeInternal = function() {
    if (this.player_) {
        return this.player_['time']();
    } else {
        return 0;
    }
};

unisubs.player.WistiaVideoPlayer.prototype.getVolume = function()
{
    return this.player_ ? this.player_['volume']() : 0;
};

unisubs.player.WistiaVideoPlayer.prototype.setVolume = function(vol)
{
    if (this.player_)
    {
        this.player_['volume'](vol);
        this.playVolume_ = vol;
    }
    else
        this.commands_.push(goog.bind(this.setVolume, this, vol));
}


