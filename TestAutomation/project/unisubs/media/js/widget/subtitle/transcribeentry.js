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

goog.provide('unisubs.subtitle.TranscribeEntry');
/**
* @constructor
* @extends goog.ui.Component
*/
unisubs.subtitle.TranscribeEntry = function(videoPlayer, languageIsRTL) {
    goog.ui.Component.call(this);
    this.videoPlayer_ = videoPlayer;
    this.languageIsRTL_ = languageIsRTL;
    this.endOfPPlayheadTime_ = null;

    this.wasPlaying_ = false;
    this.continuouslyTyping_ = false;
    this.continuousTypingTimer_ = new goog.Timer(
        unisubs.subtitle.TranscribeEntry.P * 1000);
    this.typingPauseTimer_ = new goog.Timer(
        unisubs.subtitle.TranscribeEntry.S * 1000);
    this.playStopTimer_ = new goog.Timer(4000);
};
goog.inherits(unisubs.subtitle.TranscribeEntry, goog.ui.Component);

unisubs.subtitle.TranscribeEntry.P = 4;
unisubs.subtitle.TranscribeEntry.R = 3;
unisubs.subtitle.TranscribeEntry.S = 1;
unisubs.subtitle.TranscribeEntry.CHAR_LIMIT = 100;
unisubs.subtitle.TranscribeEntry.prototype.createDom = function() {
    unisubs.subtitle.TranscribeEntry.superClass_.createDom.call(this);
    this.getElement().setAttribute('class', 'unisubs-transcribeControls');
    this.addChild(this.labelInput_ = new goog.ui.Textarea(), true);
    this.labelInput_.getElement().placeholder= 'Type subtitle and press enter';

    if (this.languageIsRTL_) {
        this.labelInput_.getElement().dir = 'rtl';
    }

    this.labelInput_.LABEL_CLASS_NAME = 'unisubs-label-input-label';
    goog.ui.Textarea.NEEDS_HELP_SHRINKING_ = false;
    this.labelInput_.setMinHeight(17);
    this.labelInput_.setMaxHeight(70);
    goog.dom.classes.add(this.labelInput_.getElement(), 'trans');
};
unisubs.subtitle.TranscribeEntry.prototype.enterDocument = function() {
    unisubs.subtitle.TranscribeEntry.superClass_.enterDocument.call(this);
    this.keyHandler_ = new goog.events.KeyHandler(this.labelInput_.getElement());
    this.getHandler().
        listen(this.keyHandler_,
               goog.events.KeyHandler.EventType.KEY,
               this.handleKey_).
        listen(this.labelInput_.getElement(),
               goog.events.EventType.KEYUP,
               this.handleKeyUp_).
        listen(this.typingPauseTimer_,
               goog.Timer.TICK,
               this.typingPauseTimerTick_).
        listen(this.continuousTypingTimer_,
               goog.Timer.TICK,
               this.continuousTypingTimerTick_).
        listen(this.playStopTimer_,
               goog.Timer.TICK,
               this.playStopTimerTick_).
        listen(this.videoPlayer_,
               unisubs.player.AbstractVideoPlayer.EventType.PLAY,
              this.startPlaying_);
    this.labelInput_.enterDocument();
};
unisubs.subtitle.TranscribeEntry.prototype.startPlaying_ = function() {
    if (this.playMode_ == unisubs.subtitle.TranscribePanel.PlayMode.PLAY_STOP) {
        this.playStopTimer_.start();
    }
};
unisubs.subtitle.TranscribeEntry.prototype.focus = function() {
    if (this.labelInput_.getValue() == '')
        this.labelInput_.setFocused();
    else
        this.labelInput_.getElement().focus();
};
unisubs.subtitle.TranscribeEntry.prototype.handleKey_ = function(event) {
    if (event.keyCode == goog.events.KeyCodes.ENTER && !event.shiftKey) {
        event.preventDefault();
        this.addNewTitle_();
        
    }
    else if (event.keyCode != goog.events.KeyCodes.TAB &&
             this.playMode_ == unisubs.subtitle.TranscribePanel.PlayMode.AUTOPAUSE) {
        this.typingPauseTimer_.stop();
        this.typingPauseTimer_.start();
        if (!this.continuouslyTyping_) {
            this.continuousTypingTimer_.start();
            this.continuouslyTyping_ = true;
        }
    }
};

unisubs.subtitle.TranscribeEntry.prototype.continuousTypingTimerTick_ = function() {
    // P seconds since continuous typing was started.
    this.continuousTypingTimer_.stop();
    this.wasPlaying_ = this.videoPlayer_.isPlaying();
    this.videoPlayer_.pause();
};
unisubs.subtitle.TranscribeEntry.prototype.typingPauseTimerTick_ = function() {
    // S seconds since last keystroke!
    var pSecondsElapsed = !this.continuousTypingTimer_.enabled;
    var newPlayheadTime = this.videoPlayer_.getPlayheadTime() -
        unisubs.subtitle.TranscribeEntry.R;
    this.continuouslyTyping_ = false;
    this.typingPauseTimer_.stop();
    this.continuousTypingTimer_.stop();
    if (pSecondsElapsed && this.wasPlaying_) {
        this.videoPlayer_.setPlayheadTime(newPlayheadTime);
        this.videoPlayer_.play();
    }
};
unisubs.subtitle.TranscribeEntry.prototype.playStopTimerTick_ = function() {
    this.playStopTimer_.stop();
    this.videoPlayer_.pause();
};
/**
 *
 * @param {unisubs.subtitle.TranscribePanel.PlayMode} mode
 */
unisubs.subtitle.TranscribeEntry.prototype.setPlayMode = function(mode) {
    this.playMode_ = mode;
    this.continuouslyTyping_ = false;
    this.continuousTypingTimer_.stop();
    this.typingPauseTimer_.stop();
    this.playStopTimer_.stop();
    if (this.playMode_ == unisubs.subtitle.TranscribePanel.PlayMode.PLAY_STOP &&
        this.videoPlayer_.isPlaying())
        this.playStopTimer_.start();
};
unisubs.subtitle.TranscribeEntry.prototype.handleKeyUp_ = function(event) {
    this.videoPlayer_.showCaptionText(this.labelInput_.getValue());
    this.issueLengthWarning_(this.insertsBreakableChar_(event.keyCode));
};
unisubs.subtitle.TranscribeEntry.prototype.addNewTitle_ = function() {
    var value = this.labelInput_.getValue();
    // FIXME: accessing private member of goog.ui.LabelInput
    this.labelInput_.label_ = '';
    this.labelInput_.setContent('');
    this.labelInput_.setFocused();
    this.dispatchEvent(new unisubs.subtitle.TranscribeEntry
                       .NewTitleEvent(value));
    this.getElement().rows = 1;
};
unisubs.subtitle.TranscribeEntry.prototype.issueLengthWarning_ =
    function(breakable)
{
    var max_chars;
    var start_warning;

    max = unisubs.subtitle.TranscribeEntry.CHAR_LIMIT;
    start_warning = 50;

    var length = this.labelInput_.getValue().length;
    if (breakable && length > max_chars)
        this.addNewTitle_();
    else
        unisubs.style.setProperty(
            this.getElement(), 'background',
            this.warningColor_(length, start_warning, max_chars));
};
unisubs.subtitle.TranscribeEntry.prototype.warningColor_ =
    function(length, firstChars, maxChars) {

    if (length < firstChars)
        return "#ddd";

    length -= firstChars;
    var r = 15;
    var g = 16 - 16 * length / (maxChars - firstChars);
    var b = 12 - 12 * length / (maxChars - firstChars);
    return ["#", this.hex_(r), this.hex_(g), this.hex_(b)].join('');
};
unisubs.subtitle.TranscribeEntry.prototype.hex_ = function(num) {
    return goog.math.clamp(Math.floor(num), 0, 15).toString(16);
};

unisubs.subtitle.TranscribeEntry.prototype.insertsBreakableChar_ =
    function(key)
{
    return key == goog.events.KeyCodes.SPACE;
};
unisubs.subtitle.TranscribeEntry.prototype.disposeInternal = function() {
    unisubs.subtitle.TranscribeEntry.superClass_.disposeInternal.call(this);
    if (this.keyHandler_)
        this.keyHandler_.dispose();
    this.typingPauseTimer_.dispose();
    this.continuousTypingTimer_.dispose();
};

unisubs.subtitle.TranscribeEntry.NEWTITLE = 'newtitle';

/**
* @constructor
*/
unisubs.subtitle.TranscribeEntry.NewTitleEvent = function(title) {
    this.type = unisubs.subtitle.TranscribeEntry.NEWTITLE;
    this.title = title;
};
