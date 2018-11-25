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

goog.provide('unisubs.timeline.Subtitle');

/**
* @constructor
* @param {unisubs.subtitle.EditableCaption} editableCaption
* @param {unisubs.player.AbstractVideoPlayer} videoPlayer
*/
unisubs.timeline.Subtitle = function(editableCaption, videoPlayer) {
    goog.events.EventTarget.call(this);
    this.editableCaption_ = editableCaption;
    this.videoPlayer_ = videoPlayer;
    this.nextSubtitle_ = null;
    this.eventHandler_ = new goog.events.EventHandler(this);
    this.eventHandler_.listen(
        editableCaption,
        unisubs.subtitle.EditableCaption.CHANGE,
        this.captionChanged_);
    this.videoEventHandler_ = null;
    this.updateTimes_();
};

goog.inherits(unisubs.timeline.Subtitle, goog.events.EventTarget);

unisubs.timeline.Subtitle.CHANGE = 'tsubchanged';
unisubs.timeline.Subtitle.MIN_UNASSIGNED_LENGTH = 2000;
unisubs.timeline.Subtitle.UNASSIGNED_SPACING = 500;

unisubs.timeline.Subtitle.orderCompare = function(a, b) {
    return a.getEditableCaption().getSubOrder() -
        b.getEditableCaption().getSubOrder();
};
unisubs.timeline.Subtitle.prototype.captionChanged_ = function(e) {
    if (this.editableCaption_.getStartTime() != -1)
        this.updateTimes_();
    if (this.nextSubtitle_ && this.nextSubtitle_.isLoneUnsynced_())
        this.nextSubtitle_.updateTimes_();
    this.dispatchEvent(unisubs.timeline.Subtitle.CHANGE);
};
unisubs.timeline.Subtitle.prototype.updateTimes_ = function() {
    if (this.isLoneUnsynced_()) {
        var previousCaption = this.editableCaption_.getPreviousCaption();
        var prevSubtitleEndTime = previousCaption == null ? -1 :
                                  previousCaption.getEndTime();
        this.startTime_ =
            Math.max(prevSubtitleEndTime,
                     parseInt(this.videoPlayer_.getPlayheadTime() * 1000))  +
            unisubs.timeline.Subtitle.UNASSIGNED_SPACING;
    }
    else {
        this.startTime_ = this.editableCaption_.getStartTime();
    }
    if (this.isLoneUnsynced_() ||
        this.editableCaption_.hasStartTimeOnly()) {
        if (this.videoEventHandler_ == null) {
            this.videoEventHandler_ = new goog.events.EventHandler(this);
            this.videoEventHandler_.listen(
                this.videoPlayer_,
                unisubs.player.AbstractVideoPlayer.EventType.TIMEUPDATE,
                this.videoTimeUpdate_);
        }
        if (this.editableCaption_.hasStartTimeOnly()) {
            this.endTime_ = Math.max(
                this.startTime_ +
                    unisubs.timeline.Subtitle.MIN_UNASSIGNED_LENGTH,
                parseInt(this.videoPlayer_.getPlayheadTime() + 1000));
            if (this.nextSubtitle_)
                this.nextSubtitle_.bumpUnsyncedTimes(this.endTime_);
        }
        else {
            this.endTime_ = this.startTime_ +
                unisubs.timeline.Subtitle.MIN_UNASSIGNED_LENGTH;
        }
    }
    else {
        this.endTime_ = this.editableCaption_.getEndTime();
        if (this.videoEventHandler_ != null) {
            this.videoEventHandler_.dispose();
            this.videoEventHandler_ = null;
        }
    }
};
unisubs.timeline.Subtitle.prototype.isLoneUnsynced_ = function() {
    var previous = this.editableCaption_.getPreviousCaption();
    var isLone =  this.editableCaption_.getStartTime() == -1 &&
        ( !previous || previous.getEndTime() != -1);
    return isLone;
};
unisubs.timeline.Subtitle.prototype.isNextToBeSynced = function() {
    return this.editableCaption_.getStartTime() == -1;
};
unisubs.timeline.Subtitle.prototype.setNextSubtitle = function(sub) {
    this.nextSubtitle_ = sub;
    if (sub && this.editableCaption_.hasStartTimeOnly())
        this.nextSubtitle_.bumpUnsyncedTimes(this.getEndTime());
};
unisubs.timeline.Subtitle.prototype.videoTimeUpdate_ = function(e) {
    if (this.editableCaption_.hasStartTimeOnly()) {
        var prevEndTime = this.endTime_;
        this.endTime_ = Math.max(
            this.startTime_ + unisubs.timeline.Subtitle.MIN_UNASSIGNED_LENGTH,
            parseInt(this.videoPlayer_.getPlayheadTime() * 1000));
        if (prevEndTime != this.getEndTime()) {
            this.dispatchEvent(unisubs.timeline.Subtitle.CHANGE);
            if (this.nextSubtitle_)
                this.nextSubtitle_.bumpUnsyncedTimes(this.endTime_);
        }
    }
    else {
        if (this.editableCaption_.getPreviousCaption() == null)
            this.bumpUnsyncedTimes(parseInt(this.videoPlayer_.getPlayheadTime() * 1000));
        else{
            var previousEndTime = this.editableCaption_.getPreviousCaption().getEndTime();
            var bumpTo = Math.max( this.videoPlayer_.getPlayheadTime() * 1000, previousEndTime || 0);
            this.bumpUnsyncedTimes(bumpTo);

        }

    }
};
unisubs.timeline.Subtitle.prototype.bumpUnsyncedTimes = function(time) {
    var prevStartTime = this.startTime_;
    this.startTime_ = time +
        unisubs.timeline.Subtitle.UNASSIGNED_SPACING;
    this.endTime_ = this.startTime_ +
        unisubs.timeline.Subtitle.MIN_UNASSIGNED_LENGTH;
    if (this.startTime_ != prevStartTime)
        this.dispatchEvent(unisubs.timeline.Subtitle.CHANGE);
};
unisubs.timeline.Subtitle.prototype.getStartTime = function() {
    return this.startTime_;
};
unisubs.timeline.Subtitle.prototype.getEndTime = function() {
    return this.endTime_;
};
unisubs.timeline.Subtitle.prototype.getEditableCaption = function() {
    return this.editableCaption_
};
unisubs.timeline.Subtitle.prototype.disposeInternal = function() {
    unisubs.timeline.Subtitle.superClass_.disposeInternal.call(this);
    this.eventHandler_.dispose();
    if (this.videoEventHandler_)
        this.videoEventHandler_.dispose();
};
