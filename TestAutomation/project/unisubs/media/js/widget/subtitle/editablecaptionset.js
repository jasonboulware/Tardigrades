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

/**
 * @fileoverview A model in true MVC sense: dispatches events when model
 *     changes. This keeps disparate parts of the UI which are interested
 *     in model state (e.g. timeline, sync panel, video) informed when
 *     alterations are made to subtitles.
 */

goog.provide('unisubs.subtitle.EditableCaptionSet');

/**
 * @constructor
 * @param {array.<object.<string, *>>} existingJsonCaptions No sort order necessary.
 * @param {boolean=} opt_completed Only meaningful for non-dependent subs.
 * @param {string=} opt_title 
 * @param {string=} opt_description 
 * @param {boolean=} opt_forkedDuringEdits This is a bit ugly, but this parameter should only be used 
 *     when deserializing an EditableCaptionSet from memory after a finish failure. It means that 
 *     during the failed editing session, the EditableCaptionSet got forked.
 */
unisubs.subtitle.EditableCaptionSet = function(dfxp, opt_completed, opt_title, opt_forkedDuringEdits, opt_description, opt_languageName, opt_languageIsRTL, opt_isModerated, opt_languageWasForked, opt_metadata) {
    goog.events.EventTarget.call(this);
    var that = this;
    var c;

    this.x = new window['AmaraDFXPParser']();
    this.x['init'](dfxp);
    window.x = this.x;

    this.captions_ = goog.array.map(
        this.x['getSubtitles'](), function(node) {
            c = new unisubs.subtitle.EditableCaption(node, that.x);
            c.setParentEventTarget(that);
            return c;
        });
    var i;

    if(opt_metadata === undefined) {
        opt_metadata = {};
    }

    this.setPreviousAndNextCaptions();

    this.completed = opt_completed;

    this.title = opt_title;
    this.description = opt_description;
    this.metadata = opt_metadata;

    this.originalTitle = opt_title;
    this.originalDescription = opt_description;
    this.originalMetadata = goog.object.clone(opt_metadata);

    this.forkedDuringEdits_ = !!opt_forkedDuringEdits;
    this.languageName = opt_languageName;
    this.languageIsRTL = opt_languageIsRTL;
    this.isModerated = opt_isModerated;

    this.languageWasForked = opt_languageWasForked;
};

goog.inherits(unisubs.subtitle.EditableCaptionSet, goog.events.EventTarget);

unisubs.subtitle.EditableCaptionSet.EventType = {
    CLEAR_ALL: 'clearall',
    CLEAR_TIMES: 'cleartimes',
    RESET_SUBS: 'resetsubs',
    ADD: 'addsub',
    DELETE: 'deletesub'
};

/**
 * Always in ascending order by start time.
 */
unisubs.subtitle.EditableCaptionSet.prototype.captionsWithTimes = function() {
    return goog.array.filter(
        this.captions_, function(c) { return c.getStartTime() != -1; });
};

unisubs.subtitle.EditableCaptionSet.prototype.clear = function() {
    this.x['removeSubtitles']();
    this.dispatchEvent(
        unisubs.subtitle.EditableCaptionSet.EventType.CLEAR_ALL);
};
unisubs.subtitle.EditableCaptionSet.prototype.clearTimes = function() {
    this.x['clearAllTimes']();
    this.dispatchEvent(
        unisubs.subtitle.EditableCaptionSet.EventType.CLEAR_TIMES);
};
unisubs.subtitle.EditableCaptionSet.prototype.needsTranslation = function() {
    return this.x['needsAnyTranscribed']();
};
unisubs.subtitle.EditableCaptionSet.prototype.resetSubs = function() {
    var that = this;
    this.x['resetSubtitles']();
    var caption;
    var newCaptions = [];
    // since subtitles might have been removed, we need to recreate
    // the entire captions_ array, and be sure we have the right
    // xml node and prev and nex set for each of them.
    goog.array.forEach(this.x['getSubtitles'](), function(node, i) {
            caption = that.captions_[i];
            if (!caption){
                caption = new unisubs.subtitle.EditableCaption(node, that.x);
                caption.setParentEventTarget(that);
            }else{
                that.captions_[i].node = node;

            }
            newCaptions[i] = caption;
    }, this);
    this.captions_ = newCaptions;
    this.setPreviousAndNextCaptions();
    this.dispatchEvent(
        unisubs.subtitle.EditableCaptionSet.EventType.RESET_SUBS);
};
unisubs.subtitle.EditableCaptionSet.prototype.count = function() {
    return this.x['subtitlesCount']();
};
unisubs.subtitle.EditableCaptionSet.prototype.caption = function(index) {
    return this.captions_[index];
};
unisubs.subtitle.EditableCaptionSet.prototype.makeDFXPString = function() {
    return this.x['xmlToString'](true);
};
//unisubs.subtitle.EditableCaptionSet.prototype.makeJsonSubs = function() {
    //return goog.array.map(this.captions_, function(c) { return c.json; });
//};
unisubs.subtitle.EditableCaptionSet.prototype.nonblankSubtitles = function() {
    var nonBlank = goog.array.filter(this.captions_, function(caption, index){
       return caption.getTrimmedText()  !== '';
    })
    return nonBlank;
};
unisubs.subtitle.EditableCaptionSet.prototype.identicalTo = function(otherCaptionSet) {
    var myNonblanks = this.nonblankSubtitles();
    var otherNonblanks = otherCaptionSet.nonblankSubtitles();
    if (myNonblanks.length != otherNonblanks.length)
        return false;
    for (var i = 0; i < myNonblanks.length; i++)
        if (!myNonblanks[i].identicalTo(otherNonblanks[i]))
            return false;
    return true;
};
unisubs.subtitle.EditableCaptionSet.prototype.addNewDependentSubtitle = function(originalNode, dfxpWrapper, atIndex) {
    var $newNode = dfxpWrapper['cloneSubtitle'](originalNode,false);
    var c = this.insertCaption(atIndex, $newNode['get'](0));
    return c;
};

/**
 *
 * @param {Number} atIndex The next subtitle's subOrder
 *     (returned by EditableCaption#getSubOrder())
 */
unisubs.subtitle.EditableCaptionSet.prototype.insertCaption = function(atIndex, newNode) {
    var prevSub;
    var nextSub = this.captions_[atIndex] || this.captions_[this.captions_.length -1];
    if(atIndex >0){
        prevSub = nextSub.getPreviousCaption();
    }
    var c;
    if (newNode) {
        // if you are adding subs that are in the source language
        // but not the translated one, you want to keep the node
        // as it can have other content
        this.x['addSubtitleNode'](newNode, atIndex);
        c = new unisubs.subtitle.EditableCaption(newNode, this.x);
    } else {
        // no node, you just want to add an 'empty' subtitle
        c = new unisubs.subtitle.EditableCaption(this.x['addSubtitle'](
            atIndex >= 1 ? atIndex - 1 : -1, {}, ""), this.x);
    }
    unisubs.SubTracker.getInstance().trackAdd(c.getCaptionIndex());
    goog.array.insertAt(this.captions_, c, atIndex );
    if (prevSub) {
        prevSub.setNextCaption(c);
        c.setPreviousCaption(prevSub);
    }
    c.setNextCaption(nextSub);
    nextSub.setPreviousCaption(c);
    if (c.needsSync()){
        this.setTimesOnInsertedSub_(c, prevSub, nextSub);
    }
    c.setParentEventTarget(this);
    this.dispatchEvent(
        new unisubs.subtitle.EditableCaptionSet.CaptionEvent(
            unisubs.subtitle.EditableCaptionSet.EventType.ADD,
            c));
    this.forkedDuringEdits_ = true;
    return c;
};
unisubs.subtitle.EditableCaptionSet.prototype.setTimesOnInsertedSub_ = function(insertedSub, prevSub, nextSub) {
    // if the gap between the prevSub.end_time and nextSub.start time is
    // > a minimal, we insert the sub right there.
    // Else, we take the time interval between the prevSub.startTime and nextSub.endTime
    // and divide by 3, that's the duration of each of the subs now..

    // We're creating a sub before the very first one.
    if (typeof prevSub === 'undefined') {
    
        // If the first sub starts at zero.
        if (nextSub.getStartTime() === 0) {

            var firstSubGap = nextSub.getEndTime() - nextSub.getStartTime();
            var midPoint = firstSubGap / 2;

            insertedSub.setStartTime(0);
            insertedSub.setEndTime(midPoint);
            nextSub.setStartTime(midPoint);

        }

    } else {
        if (!nextSub.needsSync() && !prevSub.needsSync()){
            // both are synced we can set actual time values for the new one
             var gap = nextSub.getStartTime() - prevSub.getEndTime();
            if (gap > 500){
                // gap is enough to fit in a sub between it
                insertedSub.setStartTime(prevSub.getEndTime());
                insertedSub.setEndTime(nextSub.getStartTime());
                return;
            }
            // no gap enough, so we need to divide times:
            var initialTime = prevSub.getStartTime();
            var finalTime = nextSub.getEndTime();
            if (finalTime === -1){
                // not synched can't rely on that timing
                finalTime = nextSub.getStartTime();
                // since there is no end time for the final one,
                // we can only split the time between the first
                // two
                gap = (finalTime - initialTime) / 2;
            } else {

                gap = (finalTime - initialTime) / 3;
            }
            prevSub.setEndTime(initialTime + gap);
            insertedSub.setStartTime(prevSub.getEndTime());
            insertedSub.setEndTime(prevSub.getEndTime() + gap);
            nextSub.setStartTime(insertedSub.getEndTime());
        }
    }
};

/**
 *
 * @param {unisubs.subtitle.EditableCaption} caption
 */
unisubs.subtitle.EditableCaptionSet.prototype.deleteCaption = function(caption) {
    var index = caption.getCaptionIndex();
    var sub = this.captions_[index];
    var prevSub = sub.getPreviousCaption();
    var nextSub = sub.getNextCaption();
    goog.array.removeAt(this.captions_, index);
    this.x['removeSubtitle'](caption.node);
    if (prevSub){
        prevSub.setNextCaption(nextSub);
    }
    if (nextSub){
        nextSub.setPreviousCaption(prevSub);
    }
    this.dispatchEvent(
        new unisubs.subtitle.EditableCaptionSet.CaptionEvent(
            unisubs.subtitle.EditableCaptionSet.EventType.DELETE,
            sub, index));
    this.forkedDuringEdits_ = true;
};
unisubs.subtitle.EditableCaptionSet.prototype.findSubIndex_ = function(caption) {
    return this.x['getSubtitleIndex'](caption.node);
};
unisubs.subtitle.EditableCaptionSet.prototype.addNewCaption = function(opt_dispatchEvent) {

    // Pass the new node and the DFXP parser instance to the new EditableCaption.
    var c = new unisubs.subtitle.EditableCaption(this.x['addSubtitle'](), this.x);

    unisubs.SubTracker.getInstance().trackAdd(c.getCaptionIndex());

    c.setParentEventTarget(this);
    this.captions_.push(c)
    if (this.x['subtitlesCount']()> 1) {
        var previousCaption = this.captions_[this.captions_.length - 2];
        previousCaption.setNextCaption(c);
        c.setPreviousCaption(previousCaption);
    }
    if (opt_dispatchEvent) {
        this.dispatchEvent(
            new unisubs.subtitle.EditableCaptionSet.CaptionEvent(
                unisubs.subtitle.EditableCaptionSet.EventType.ADD,
                c));
    }
    return c;
};

/**
 * Find the last subtitle with a start time at or before time.
 * @param {number} time
 * @return {?unisubs.subtitle.EditableCaption} null if before first
 *     sub start time, or last subtitle with start time
 *     at or before playheadTime.
 */
unisubs.subtitle.EditableCaptionSet.prototype.findLastForTime = function(time) {
    var i;
    // TODO: write unit test then get rid of linear search in future.
    var captions = this.x['getSubtitles']();
    var currentStartTime;
    var nextStartTime;
    var isLast = false;
    var length = captions.length;
    for (i = 0; i < length; i++){
        currentStartTime = this.x['startTime'](this.x['getSubtitleByIndex'](i));
        isLast = i == length -1;
        if (!isLast){
            nextStartTime = this.x['startTime'](this.x['getSubtitleByIndex'](i+1));
        }else{
            nextStartTime  = undefined;
        }
        // we want a sub with a start time < play time
        // that either is the last one, or one where
        // the next is unsyced or it's start time is
        // greater then play time
        if (currentStartTime != -1 &&
            currentStartTime <= time &&
            (nextStartTime == -1 ||
             nextStartTime > time || isLast )){
            return this.captions_[i];
        }
    }
    return null;
};
/**
 * Always in ascending order by start time.
 * Returns a list of EditableCaptions that
 * should be displayed on the timeline. These are
 * all synced subs + the first unsyced sub
 */
unisubs.subtitle.EditableCaptionSet.prototype.timelineCaptions = function() {
    return goog.array.filter(
        this.captions_,
        function(c) {
            var prev = c.getPreviousCaption();
            return c.getStartTime() != -1 ||
                (prev && prev.getStartTime() != -1) ||
                (c.getStartTime() == -1 && !prev );
        });
};
/**
 * Used for both add and delete.
 * @constructor
 * @param {unisubs.subtitle.EditableCaptionSet.EventType} type of event
 * @param {unisubs.subtitle.EditableCaption} Caption the event applies to.
 */
unisubs.subtitle.EditableCaptionSet.CaptionEvent = function(type, caption, index) {
    this.type = type;
    /**
     * @type {unisubs.subtitle.EditableCaption}
     */
    this.caption = caption;
    this.index = index;
};

/*
 * @return {boolean} True if one or more captions have no time data, 
 * except for the last one, whose end time (only) can be undefined.
 */
unisubs.subtitle.EditableCaptionSet.prototype.needsSync = function() {
    return this.x['needsAnySynced']();
};

unisubs.subtitle.EditableCaptionSet.prototype.fork = function(originalSubtitleState) {
    var subMap = this.makeMap();
    var translatedSub;
    goog.array.forEach(
        originalSubtitleState.SUBTITLES,
        function(origSub) {
            translatedSub = subMap[origSub['subtitle_id']];
            if (translatedSub) {
                translatedSub.fork(origSub);
            }
        });
    goog.array.sort(
        this.captions_,
        unisubs.subtitle.EditableCaption.orderCompare);
    this.forkedDuringEdits_ = true;
};
unisubs.subtitle.EditableCaptionSet.prototype.wasForkedDuringEdits = function() {
    return this.forkedDuringEdits_;
};
unisubs.subtitle.EditableCaptionSet.prototype.makeMap = function() {
    var map = {};
    goog.array.forEach(
        this.captions_, 
        function(c) {
            map[c.getCaptionIndex()] = c;
        });
    return map;
};
unisubs.subtitle.EditableCaptionSet.prototype.setPreviousAndNextCaptions = function() {
    for (i = 1; i < this.captions_.length; i++) {
        this.captions_[i - 1].setNextCaption(this.captions_[i]);
        this.captions_[i].setPreviousCaption(this.captions_[i - 1]);
    }
};

unisubs.subtitle.EditableCaptionSet.prototype.hasTitleChanged = function() {
    return this.originalTitle !== this.title;
};

unisubs.subtitle.EditableCaptionSet.prototype.hasDescriptionChanged = function() {
    return this.originalDescription !== this.description;
};

unisubs.subtitle.EditableCaptionSet.prototype.hasMetadataChanged = function() {
    if(this.hasTitleChanged() || this.hasDescriptionChanged()) {
        return true;
    }
    for(key in this.originalMetadata) {
        if(this.metadata[key] != this.originalMetadata[key]) {
            return true;
        }
    }
    return false;
}
