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

goog.provide('unisubs.subtitle.EditableCaption');

/**
 * Don't call this constructor directly. Instead call the factory method in
 * unisubs.subtitle.EditableCaptionSet.
 *
 * @constructor
 * @param {Number=} opt_subOrder Order in which this sub appears. Provide
 *    this parameter iff the caption doesn't exist in the unisubs
 *    system.
 * @param {JSONCaption=} opt_jsonCaption optional JSON caption on which
 *     we're operating. Provide this parameter iff the caption exists
 *     already in the unisubs system.
 */
unisubs.subtitle.EditableCaption = function(node, x) {
    goog.events.EventTarget.call(this);
    this.previousCaption_ = null;
    this.nextCaption_ = null;

    this.node = node;
    this.x = x;

};

goog.inherits(unisubs.subtitle.EditableCaption, goog.events.EventTarget);

unisubs.subtitle.EditableCaption.prototype.fork = function(otherSub) {
    // FIXME:
    this.setStartTime(otherSub.getStarTime());
    this.setEndTime(otherSub.getEndTime());
    this.setText(otherSub.getText());
}
unisubs.subtitle.EditableCaption.orderCompare = function(a, b) {
    return a.getSubOrder() - b.getSubOrder();
};

/*
 * @const
 * @type {int} 
 */
unisubs.subtitle.EditableCaption.TIME_UNDEFINED = -1;
unisubs.subtitle.EditableCaption.TIME_UNDEFINED_SERVER = (100 * 60 * 60) -1;

unisubs.subtitle.EditableCaption.isTimeUndefined = function(v){
    return !goog.isDefAndNotNull(v) || 
        v == unisubs.subtitle.EditableCaption.TIME_UNDEFINED ||
        v == unisubs.subtitle.EditableCaption.TIME_UNDEFINED_SERVER || false;
};

unisubs.subtitle.EditableCaption.CHANGE = 'captionchanged';

/**
 * Minimum subtitle length, in seconds.
 */
unisubs.subtitle.EditableCaption.MIN_LENGTH = 0.5;

/**
 * @param {unisubs.subtitle.EditableCaption} caption Previous caption in list.
 *
 */
unisubs.subtitle.EditableCaption.prototype.setPreviousCaption = function(caption) {
    this.previousCaption_ = caption;
};
unisubs.subtitle.EditableCaption.prototype.getPreviousCaption = function() {
    return this.previousCaption_;
};

/**
 * @param {unisubs.subtitle.EditableCaption} caption Next caption in list.
 *
 */
unisubs.subtitle.EditableCaption.prototype.setNextCaption = function(caption) {
    this.nextCaption_ = caption;
};
unisubs.subtitle.EditableCaption.prototype.getNextCaption = function() {
    return this.nextCaption_;
};
unisubs.subtitle.EditableCaption.prototype.identicalTo = function(other) {
    return this.getSubOrder() == other.getSubOrder() &&
        this.getTrimmedText() == other.getTrimmedText() &&
        this.getStartTime() == other.getStartTime() &&
        this.getEndTime() == other.getEndTime() &&
        this.getCaptionIndex() == other.getCaptionIndex() &&
        this.getStartOfParagraph() == other.getStartOfParagraph();
};
unisubs.subtitle.EditableCaption.prototype.getSubOrder = function() {
    return this.x['getSubtitleIndex'](this.node);
};
unisubs.subtitle.EditableCaption.prototype.setText = function(text, opt_dontTrack) {
    this.x['content'](this.node, text);
    this.changed_(false, opt_dontTrack);
};
unisubs.subtitle.EditableCaption.prototype.getOriginalText = function() {
    return this.json['original_text'];
};
unisubs.subtitle.EditableCaption.prototype.getHTML = function() {
    var rawText = this.x['content'](this.node);
    return this.x['markdownToHTML'](rawText);
};
unisubs.subtitle.EditableCaption.prototype.getText = function() {
    return this.x['content'](this.node);
};
unisubs.subtitle.EditableCaption.prototype.getStartOfParagraph = function(){
    return Boolean(this.x['startOfParagraph'](this.node));
};
unisubs.subtitle.EditableCaption.prototype.setStartOfParagraph = function(val, opt_dontTrack){
    if (this.getStartOfParagraph() != Boolean(val)){
        this.x['startOfParagraph'](this.node, Boolean(val));
        this.changed_(false, opt_dontTrack);
    }
    return this.getStartOfParagraph();
};
unisubs.subtitle.EditableCaption.prototype.toggleStartOfParagraph = function(){
    return this.setStartOfParagraph(!this.getStartOfParagraph(), true);
};
unisubs.subtitle.EditableCaption.prototype.getTrimmedText = function() {
    return goog.string.trim(this.x['content'](this.node));
};
unisubs.subtitle.EditableCaption.prototype.setStartTime = function(startTime) {
    var previousStartTime = this.getStartTime();
    this.setStartTime_(startTime);
    this.changed_(previousStartTime == 
                  unisubs.subtitle.EditableCaption.TIME_UNDEFINED);
};
unisubs.subtitle.EditableCaption.prototype.setStartTime_ = function(startTime) {
    var previousValue = this.x['startTime'](this.node);
    startTime = Math.max(startTime, this.getMinStartTime());
    this.x['startTime'](this.node, startTime);
    if (this.getEndTime() != unisubs.subtitle.EditableCaption.TIME_UNDEFINED &&
        this.getEndTime() < startTime +
        unisubs.subtitle.EditableCaption.MIN_LENGTH)
        this.setEndTime_(
            startTime + unisubs.subtitle.EditableCaption.MIN_LENGTH);
    if (this.previousCaption_ &&
        (this.previousCaption_.getEndTime() == 
         unisubs.subtitle.EditableCaption.TIME_UNDEFINED ||
         this.previousCaption_.getEndTime() > startTime)){
         this.previousCaption_.setEndTime(startTime);
    }
};
unisubs.subtitle.EditableCaption.prototype.getStartTime = function() {
    var val = this.x['startTime'](this.node);
    if (goog.isDefAndNotNull(val)) {
        return val;
    }
    else {
        return unisubs.subtitle.EditableCaption.TIME_UNDEFINED;
    }
};
unisubs.subtitle.EditableCaption.prototype.setEndTime = function(endTime) {
    this.setEndTime_(endTime);
    this.changed_(false);
};
unisubs.subtitle.EditableCaption.prototype.setEndTime_ = function(endTime) {
    this.x['endTime'](this.node, endTime);
    if (this.getStartTime() > endTime -
        unisubs.subtitle.EditableCaption.MIN_LENGTH)
        this.setStartTime_(
            endTime - unisubs.subtitle.EditableCaption.MIN_LENGTH);
    if (this.nextCaption_ &&
        this.nextCaption_.getStartTime() != 
        unisubs.subtitle.EditableCaption.TIME_UNDEFINED &&
        this.nextCaption_.getStartTime() < endTime)
        this.nextCaption_.setStartTime(endTime);
};

/**
 * Clears times. Does not issue a CHANGE event.
 */
unisubs.subtitle.EditableCaption.prototype.clearTimes = function() {
    if (this.getStartTime() != unisubs.subtitle.EditableCaption.TIME_UNDEFINED ||
        this.getEndTime() != unisubs.subtitle.EditableCaption.TIME_UNDEFINED) {
        this.x['startTime'](this.node, '');
        this.x['endTime'](this.node, '');
    }
};

unisubs.subtitle.EditableCaption.prototype.resetSub = function() {

    this.x['content'](this.node, this.x['originalContent'](this.node));

    if (this.getStartTime() != unisubs.subtitle.EditableCaption.TIME_UNDEFINED ||
        this.getEndTime() != unisubs.subtitle.EditableCaption.TIME_UNDEFINED) {

        var previousStartTime = this.x['startTime'](this.node);
        this.setStartTime_(this.x['originalStartTime'](this.node));
        this.changed_(previousStartTime == unisubs.subtitle.EditableCaption.TIME_UNDEFINED);

        var previousEndTime = this.x['endTime'](this.node);
        this.setEndTime_(this.x['originalEndTime'](this.node));
        this.changed_(previousEndTime == unisubs.subtitle.EditableCaption.TIME_UNDEFINED);
    }
};
unisubs.subtitle.EditableCaption.prototype.getEndTime = function() {
    var val = this.x['endTime'](this.node);
    if (goog.isDefAndNotNull(val)) {
        return val;
    }
    else {
        return unisubs.subtitle.EditableCaption.TIME_UNDEFINED;
    }
};
unisubs.subtitle.EditableCaption.prototype.getMinStartTime = function() {
    return this.previousCaption_ ?
        (this.previousCaption_.getStartTime() +
         unisubs.subtitle.EditableCaption.MIN_LENGTH) : 0;
};
unisubs.subtitle.EditableCaption.prototype.getMaxStartTime = function() {
    if (this.getEndTime() == unisubs.subtitle.EditableCaption.TIME_UNDEFINED)
        return 99999;
    else
        return this.getEndTime() -
            unisubs.subtitle.EditableCaption.MIN_LENGTH;
};
unisubs.subtitle.EditableCaption.prototype.getMinEndTime = function() {
    return this.getStartTime() + unisubs.subtitle.EditableCaption.MIN_LENGTH;
};
unisubs.subtitle.EditableCaption.prototype.getMaxEndTime = function() {
    return this.nextCaption_ && this.nextCaption_.getEndTime() != 
        unisubs.subtitle.EditableCaption.TIME_UNDEFINED ?
        (this.nextCaption_.getEndTime() -
         unisubs.subtitle.EditableCaption.MIN_LENGTH) : 99999;
};
unisubs.subtitle.EditableCaption.prototype.getCaptionIndex = function() {
    return this.x['getSubtitles']().index(this.node);
};
unisubs.subtitle.EditableCaption.prototype.isShownAt = function(time) {
    return this.getStartTime() <= time &&
        (this.getEndTime() == unisubs.subtitle.EditableCaption.TIME_UNDEFINED ||
            time < this.getEndTime());
};
unisubs.subtitle.EditableCaption.prototype.hasStartTimeOnly = function() {
    return this.getStartTime() != unisubs.subtitle.EditableCaption.TIME_UNDEFINED &&
        this.getEndTime() == unisubs.subtitle.EditableCaption.TIME_UNDEFINED;
};

/*
 * @return {boolean} True if either startTime or endTime is not defined.
 */
unisubs.subtitle.EditableCaption.prototype.needsSync = function() {
    return this.getStartTime() == unisubs.subtitle.EditableCaption.TIME_UNDEFINED ||
        this.getEndTime() == unisubs.subtitle.EditableCaption.TIME_UNDEFINED;
};

unisubs.subtitle.EditableCaption.prototype.changed_ = function(timesFirstAssigned, opt_dontTrack) {
    if (!opt_dontTrack)
        unisubs.SubTracker.getInstance().trackEdit(this.getCaptionIndex());
    this.dispatchEvent(
        new unisubs.subtitle.EditableCaption.ChangeEvent(
            timesFirstAssigned));
};
unisubs.subtitle.EditableCaption.adjustUndefinedTiming = function(json) {
    if (!json['start_time'] || json['start_time'] == unisubs.subtitle.EditableCaption.TIME_UNDEFINED){
        json['start_time'] = unisubs.subtitle.EditableCaption.TIME_UNDEFINED_SERVER;
    }
    if (!json['end_time'] || json['end_time'] == unisubs.subtitle.EditableCaption.TIME_UNDEFINED){
        json['end_time'] = unisubs.subtitle.EditableCaption.TIME_UNDEFINED_SERVER;
    }
    return json;
};
unisubs.subtitle.EditableCaption.toJsonArray = function(editableCaptions) {
    return goog.array.map(
        editableCaptions, 
        function(editableCaption) {
            return unisubs.subtitle.EditableCaption.adjustUndefinedTiming(editableCaption.json);
        });
};
unisubs.subtitle.EditableCaption.toIDArray = function(editableCaptions) {
    return goog.array.map(
        editableCaptions,
        function(ec) {
            return ec.getCaptionIndex();
        });
};

unisubs.subtitle.EditableCaption.prototype.toString = function() {
    return "EditableCaption: "  + this.getText()
}
/**
 * @constructor
 */
unisubs.subtitle.EditableCaption.ChangeEvent = function(timesFirstAssigned) {
    this.type = unisubs.subtitle.EditableCaption.CHANGE;
    this.timesFirstAssigned = timesFirstAssigned;
};
