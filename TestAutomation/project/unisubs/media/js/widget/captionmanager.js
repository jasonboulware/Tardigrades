// Amara, universalsubtitles.org //
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

goog.provide('unisubs.CaptionManager');

/**
 * @constructor
 *
 * @param {unisubs.player.AbstractVideoPlayer} videoPlayer
 * @param {unisubs.subtitle.EditableCaptionSet} captionSet
 */
unisubs.CaptionManager = function(videoPlayer, captionSet) {
    goog.events.EventTarget.call(this);

    this.captions_ = captionSet.captionsWithTimes();
    window.manager = this;
    this.x = captionSet.x;

    var that = this;

    this.binaryCompare_ = function(time, node) {
        return  time - that.x['startTime'](node);
    };
    this.binaryCompareCaptions_ = function(time, caption) {
        return  time - that.x['startTime'](caption.node);
    };
    this.binaryCaptionCompare_ = function(c0, c1) {
        return that.x['startTime'](c0.node) - that.x['startTime'](c1.node);
    };
    this.videoPlayer_ = videoPlayer;
    this.eventHandler_ = new goog.events.EventHandler(this);

    this.eventHandler_.listen(
	videoPlayer,
	unisubs.player.AbstractVideoPlayer.EventType.TIMEUPDATE,
	this.timeUpdate_);
    this.eventHandler_.listen(
	captionSet,
        goog.array.concat(
            goog.object.getValues(
                unisubs.subtitle.EditableCaptionSet.EventType),
            unisubs.subtitle.EditableCaption.CHANGE),
	this.captionSetUpdate_);

    this.currentCaptionIndex_ = -1;
    this.lastCaptionDispatched_ = null;
    this.eventsDisabled_ = false;
};
goog.inherits(unisubs.CaptionManager, goog.events.EventTarget);

unisubs.CaptionManager.CAPTION = 'caption';
unisubs.CaptionManager.CAPTIONS_FINISHED = 'captionsfinished';

unisubs.CaptionManager.prototype.captionSetUpdate_ = function(event) {
    var et = unisubs.subtitle.EditableCaptionSet.EventType;
    if (event.type == et.CLEAR_ALL ||
        event.type == et.CLEAR_TIMES ||
        event.type == et.RESET_SUBS) {
	    this.captions_ = [];
        this.currentCaptionIndex_ = -1;
	    this.dispatchCaptionEvent_(null);
    }
    else if (event.type == et.ADD) {
        var caption = event.caption;
        if (caption.getStartTime() != -1) {
            goog.array.binaryInsert(
                this.captions_, caption, this.binaryCaptionCompare_);
            this.sendEventForRandomPlayheadTime_(
                this.videoPlayer_.getPlayheadTime());
        }
    }
    else if (event.type == et.DELETE) {
        var caption = event.caption;
        if (caption.getStartTime() != -1) {
            goog.array.binaryRemove(
                this.captions_, caption, this.binaryCaptionCompare_);
            this.sendEventForRandomPlayheadTime_(
                this.videoPlayer_.getPlayheadTime());
        }
    }
    else if (event.type == unisubs.subtitle.EditableCaption.CHANGE) {
	if (event.timesFirstAssigned) {
	    this.captions_.push(event.target);
	    this.timeUpdate_();
	}
    }
};

unisubs.CaptionManager.prototype.timeUpdate_ = function() {
    // players will emit playhead time in seconds
    // the rest of the system will use milliseconds
    this.sendEventsForPlayheadTime_(
	this.videoPlayer_.getPlayheadTime() * 1000);
};

unisubs.CaptionManager.prototype.sendEventsForPlayheadTime_ =
    function(playheadTime)
{

    if (this.captions_ === 0) {
        return;
    }

    if (this.currentCaptionIndex_ == -1 && playheadTime < this.x['startTime'](this.x['getFirstSubtitle']())){
        return;
    }

    var curCaption = this.currentCaptionIndex_ > -1 ?
        this.x['getSubtitleByIndex'](this.currentCaptionIndex_) : null;

    if (curCaption != null && this.x['isShownAt'](curCaption, playheadTime)){
        this.dispatchCaptionEvent_(this.captions_[this.currentCaptionIndex_], this.currentCaptionIndex_);
        return;
    }

    var nextCaptionIndex =  this.currentCaptionIndex_ < this.captions_.length -1 ?
        this.currentCaptionIndex_ + 1 : null;
    var nextCaption = this.currentCaptionIndex_ < this.captions_.length - 1 ?
        this.captions_[this.currentCaptionIndex_ + 1] : null;

    if (nextCaption != null && this.x['isShownAt'](this.x['getSubtitleByIndex'](nextCaptionIndex), playheadTime)) {
        this.currentCaptionIndex_++;
        this.dispatchCaptionEvent_(nextCaption, nextCaptionIndex);
        return;
    }

    if ((nextCaption == null || playheadTime < this.x['startTime'](nextCaption.node)) &&
        (curCaption == null || playheadTime >= this.x['startTime'](curCaption))) {
        this.dispatchCaptionEvent_(null);
        if (nextCaption == null && !this.eventsDisabled_) {
            this.dispatchEvent(unisubs.CaptionManager.CAPTIONS_FINISHED);
        }
        return;
    }

    this.sendEventForRandomPlayheadTime_(playheadTime);
};

unisubs.CaptionManager.prototype.sendEventForRandomPlayheadTime_ =
    function(playheadTime)
{
    var lastCaptionIndex = goog.array.binarySearch(this.captions_,
        playheadTime, this.binaryCompareCaptions_);

    if (lastCaptionIndex < 0) {
        lastCaptionIndex = (lastCaptionIndex * -1) - 2
    }

    this.currentCaptionIndex_ = lastCaptionIndex;
    var lastCaption = this.captions_[lastCaptionIndex];
    if (lastCaptionIndex >= 0 && lastCaption && this.x['isShownAt'](lastCaption.node, playheadTime)) {
        this.dispatchCaptionEvent_(lastCaption, lastCaptionIndex);
    } else {
        this.dispatchCaptionEvent_(null);
    }
};

unisubs.CaptionManager.prototype.dispatchCaptionEvent_ = function(caption, index, forceEvent) {
    if (caption == this.lastCaptionDispatched_ && !forceEvent)
        return;
    if (this.eventsDisabled_)
        return;
    this.lastCaptionDispatched_ = caption;
    this.dispatchEvent(new unisubs.CaptionManager.CaptionEvent(caption, index));
};

/**
 * When we switch panels, we should clear the currently displayed sub
 */
unisubs.CaptionManager.prototype.onPanelChanged = function() {
    this.currentCaptionIndex_ = -1;
    this.lastCaptionDispatched_ = null;
    this.dispatchCaptionEvent_(null, null, true)

}
unisubs.CaptionManager.prototype.disposeInternal = function() {
    unisubs.CaptionManager.superClass_.disposeInternal.call(this);
    this.eventHandler_.dispose();
};

unisubs.CaptionManager.prototype.disableCaptionEvents = function(disabled) {
    this.eventsDisabled_ = disabled;
};

/**
* @constructor
*/
unisubs.CaptionManager.CaptionEvent = function(editableCaption, index) {
    this.type = unisubs.CaptionManager.CAPTION;
    this.caption = editableCaption;
    this.index = index;
};
