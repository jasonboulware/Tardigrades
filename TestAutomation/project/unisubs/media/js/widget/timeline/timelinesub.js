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

goog.provide('unisubs.timeline.TimelineSub');
/**
* @constructor
* @extends goog.ui.Component
*/
unisubs.timeline.TimelineSub = function(
    subtitle, pixelsPerSecond, opt_pixelOffset, readOnly)
{
    goog.ui.Component.call(this);
    this.subtitle_ = subtitle;
    this.pixelsPerMillisecond_ = pixelsPerSecond  / 1000;
    this.pixelOffset_ = opt_pixelOffset ? opt_pixelOffset : 0;
    this.editing_ = false;
    this.documentEventHandler_ = new goog.events.EventHandler(this);
    this.readOnly_ = readOnly;
};
goog.inherits(unisubs.timeline.TimelineSub, goog.ui.Component);
/**
 * Whether one of the timeline subs is currently being edited.
 */
unisubs.timeline.TimelineSub.currentlyEditing_ = false;
unisubs.timeline.TimelineSub.isCurrentlyEditing = function() {
    return unisubs.timeline.TimelineSub.currentlyEditing_;
};
unisubs.timeline.TimelineSub.EventType = {
    START_EDITING : 'startediting',
    FINISH_EDITING : 'finishediting'
};
unisubs.timeline.TimelineSub.prototype.createDom = function() {
    unisubs.timeline.TimelineSub.superClass_.createDom.call(this);
    this.getElement().className = 'unisubs-timeline-sub';
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    this.$d = $d;
    var el = this.getElement();
    el.appendChild(this.textElem_ = $d('div', 'unisubs-subtext'));
    el.appendChild(
        this.leftGrabber_ =
            $d('span', 'unisubs-grabber unisubs-leftGrabber',
               $d('strong')));
    el.appendChild(
        this.rightGrabber_ =
            $d('span', 'unisubs-grabber unisubs-rightGrabber',
               $d('strong')));
    unisubs.style.setProperty(el, 'cursor', 'pointer');
    this.updateValues_();
};
unisubs.timeline.TimelineSub.prototype.enterDocument = function() {
    unisubs.timeline.TimelineSub.superClass_.enterDocument.call(this);
    this.getHandler().listen(
        this.getElement(), 'mouseover', this.onMouseOver_).
        listen(this.getElement(), 'mouseout', this.onMouseOut_).
        listen(this.leftGrabber_, 'mousedown', this.onGrabberMousedown_).
        listen(this.rightGrabber_, 'mousedown', this.onGrabberMousedown_).
        listen(this.subtitle_, unisubs.timeline.Subtitle.CHANGE,
               this.updateValues_);
};
unisubs.timeline.TimelineSub.prototype.onMouseOver_ = function(event) {
    if (this.readOnly_) {
        return;
    }
    if (!unisubs.timeline.TimelineSub.currentlyEditing_)
        this.setGrabberVisibility_(true);
    this.mouseOver_ = true;
};
unisubs.timeline.TimelineSub.prototype.onMouseOut_ = function(event) {
    if (this.readOnly_) {
        return;
    }
    if (event.relatedTarget &&
        !goog.dom.contains(this.getElement(), event.relatedTarget)) {
        if (!this.editing_)
            this.setGrabberVisibility_(false);
        this.mouseOver_ = false;
    }
};
unisubs.timeline.TimelineSub.prototype.onDocMouseMoveLeft_ = function(event) {
    // moving left grabber
    var time = this.grabberMousedownTime_ +
            (event.clientX - this.grabberMousedownClientX_) /
            this.pixelsPerMillisecond_;
    
    this.subtitle_.getEditableCaption().setStartTime(parseInt(time));
};
unisubs.timeline.TimelineSub.prototype.onDocMouseMoveRight_ = function(event) {
    // moving right grabber
    var time =         this.grabberMousedownTime_ +
            (event.clientX - this.grabberMousedownClientX_) /
            this.pixelsPerMillisecond_;
    this.subtitle_.getEditableCaption().setEndTime(parseInt(time));
};
unisubs.timeline.TimelineSub.prototype.onDocMouseUp_ = function(event) {
    this.editing_ = false;
    unisubs.timeline.TimelineSub.currentlyEditing_ = false;
    this.documentEventHandler_.removeAll();
    if (!this.mouseOver_)
        this.setGrabberVisibility_(false);
    this.dispatchEvent(
        unisubs.timeline.TimelineSub.EventType.FINISH_EDITING);
};
unisubs.timeline.TimelineSub.prototype.getSubtitle = function() {
    return this.subtitle_;
};
unisubs.timeline.TimelineSub.prototype.onGrabberMousedown_ =
    function(event)
{
    var left = goog.dom.contains(this.leftGrabber_, event.target);
    this.editing_ = true;
    this.dispatchEvent(
        unisubs.timeline.TimelineSub.EventType.START_EDITING);
    unisubs.timeline.TimelineSub.currentlyEditing_ = true;
    this.grabberMousedownClientX_ = event.clientX;
    this.grabberMousedownTime_ = left ?
        parseInt(this.subtitle_.getStartTime()) : parseInt(this.subtitle_.getEndTime());
    this.documentEventHandler_.listen(
        document, 'mousemove',
        left ? this.onDocMouseMoveLeft_ : this.onDocMouseMoveRight_);
    this.documentEventHandler_.listen(
        document, 'mouseup', this.onDocMouseUp_);
    event.preventDefault(); // necessary to prevent image dragging in FF3
};
unisubs.timeline.TimelineSub.prototype.setGrabberVisibility_ =
    function(visible)
{
    var c = goog.dom.classes;
    var overClass = 'unisubs-grabber-over';
    if (visible) {
        c.add(this.leftGrabber_, overClass);
        c.add(this.rightGrabber_, overClass);
    }
    else {
        c.remove(this.leftGrabber_, overClass);
        c.remove(this.rightGrabber_, overClass);
    }
};
unisubs.timeline.TimelineSub.prototype.updateValues_ = function() {
    var nextToBeSynced = this.subtitle_.isNextToBeSynced();
    if (this.subtitle_.getEditableCaption().getText() !=
        this.existingSubText_)
    {
        var frag = goog.dom.htmlToDocumentFragment(this.subtitle_.getEditableCaption().getHTML());
        var newTextElem = this.$d('div', 'unisubs-subtext', frag);

        goog.dom.replaceNode(newTextElem, this.textElem_);

        this.existingSubText_ = this.subtitle_.getEditableCaption().getText();
    }
    if (this.subtitle_.getEndTime() != this.existingSubEnd_ ||
        this.subtitle_.getStartTime() != this.existingSubStart_) {
        var width =
            (this.subtitle_.getEndTime() - this.subtitle_.getStartTime()) *
                this.pixelsPerMillisecond_;

        unisubs.style.setWidth( this.getElement(), width);
        this.existingSubEnd_ = this.subtitle_.getEndTime();
    }
    if (this.subtitle_.getStartTime() != this.existingSubStart_) {
        var left  = this.subtitle_.getStartTime() * this.pixelsPerMillisecond_ -
            this.pixelOffset_;
        unisubs.style.setPosition(
            this.getElement(),
            left, null);
        this.existingSubStart_ = this.subtitle_.getStartTime();
    }
    if ( nextToBeSynced != this.existingSubNextToSync_) {
        var c = goog.dom.classes;
        var unsyncedclass = 'unisubs-timeline-sub-unsynced';
        if (nextToBeSynced) {
            c.add(this.getElement(), unsyncedclass);
            unisubs.style.showElement(this.rightGrabber_, false);
        }
        else {
            c.remove(this.getElement(), unsyncedclass);
            unisubs.style.showElement(this.rightGrabber_, true);
        }
        this.existingSubNextToSync_ = nextToBeSynced;
    }
};
unisubs.timeline.TimelineSub.prototype.disposeInternal = function() {
    unisubs.timeline.TimelineSub.superClass_.disposeInternal.call(this);
    this.documentEventHandler_.dispose();
};
