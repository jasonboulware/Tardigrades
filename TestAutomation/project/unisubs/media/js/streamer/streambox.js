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

goog.provide('unisubs.streamer.StreamBox');

/**
 * @constructor
 */
unisubs.streamer.StreamBox = function() {
    goog.ui.Component.call(this);
    this.subMap_ = null;
    this.displayedSub_ = null;
};
goog.inherits(unisubs.streamer.StreamBox, goog.ui.Component);

unisubs.streamer.StreamBox.prototype.createDom = function() {
    unisubs.streamer.StreamBox.superClass_.createDom.call(this);
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    this.transcriptElem_ = $d('div', 'unisubs-transcript');
    this.resyncButton_ = $d('a', 'resync', 'Back to current line');
    unisubs.style.setVisibility(this.resyncButton_, false);
    var unisubsLink = 
        $d('a', { 'href': '#', 'id': 'unisubs-logo' },
           $d('img', 
              { 'src': 
                unisubs.imageAssetURL('widget_button.png') } ));
    this.videoTab_ = new unisubs.streamer.StreamerVideoTab(unisubsLink);
    var prevArrow, nextArrow, resultCount;
    var searchContainer = 
        $d('div', 'unisubs-search-container',
           $d('div', 'unisubs-search-input',
              $d('input', { 'className': 'unisubs-search', 'label': 'Search...' }),
                 resultCount = $d('span', 'resultcount')),
           prevArrow = unisubs.createLinkButton($d, '↑'),
           nextArrow = unisubs.createLinkButton($d, '↓'));
    var substreamerElem = 
        $d('div', 'unisubs-substreamer',
           $d('div', 'unisubs-substreamer-controls', 
              $d('ul', null, 
                 $d('li', null, unisubsLink)),
              this.resyncButton_,
             searchContainer),
           this.transcriptElem_);
    goog.dom.append(this.getElement(), substreamerElem);
    this.streamBoxSearch_ = new unisubs.streamer.StreamBoxSearch();
    this.streamBoxSearch_.decorate(searchContainer);
};

unisubs.streamer.StreamBox.prototype.decorateInternal = function(elem) {
    unisubs.streamer.StreamBox.superClass_.decorateInternal.call(this, elem);
    this.transcriptElem_ = goog.dom.getElementsByTagNameAndClass(
        'div', 'unisubs-transcript', elem)[0];
    this.resyncButton_ = goog.dom.getElementsByTagNameAndClass(
        'a', 'resync', elem)[0];
    this.videoTab_ = new unisubs.streamer.StreamerVideoTab(
        goog.dom.getElement("unisubs-logo"));
    var subSpans = goog.dom.getElementsByTagNameAndClass(
        'p', 'unisubs-transcript-paragraph', elem);
    this.makeSubsAndSubMap_(subSpans);
    this.streamBoxSearch_ = new unisubs.streamer.StreamBoxSearch();
    var searchContainer = goog.dom.getElementsByTagNameAndClass(
        null, 'unisubs-search-container', elem)[0];
    this.streamBoxSearch_.decorate(searchContainer);
    this.streamBoxSearch_.setTranscriptElemAndSubs(
        this.transcriptElem_, this.subs_);
};


unisubs.streamer.StreamBox.prototype.getVideoTab = function() {
    return this.videoTab_;
};

/*
* Creates the actual dom nodes for subtitles.
* @param  A two dimensional array of subs, groupped by paragraps, such as:
* [
  [sub1, sub2, sub3] // this is the first paragraph
  [sub4, sub5, sub6, sub7, sub8, sub9] 
]
*/
unisubs.streamer.StreamBox.prototype.createSubsEls_ = function(subs){
    var paragraphs = [];
    var currentParagraph;
    goog.array.forEach(subs, function(sub, index){
        
        var startParagraph = index == 0 || sub['start_of_paragraph'];
        if (startParagraph){
            currentParagraph = []
            paragraphs.push(currentParagraph)
        }
        currentParagraph.push(sub);
        
    });
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    var els = goog.array.map(paragraphs, function(thisParagraph, index){
        var lines = goog.array.map(thisParagraph, function(sub){
            return span  = $d(
                'span', 
                { 'className': 'unisubs-sub',
                  'id': 'usub-a-' + sub['subtitle_id'] },
                sub['text']  );

        });
        var args = goog.array.concat(["p", null] , lines);
        return $d.apply(null, args);
        
    });
    return els;
}

/**
 * @param {Array} subtitles json subs from server
 */
unisubs.streamer.StreamBox.prototype.setSubtitles = function(subtitles) {
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    var subSpans = this.createSubsEls_(subtitles);
    goog.dom.removeChildren(this.transcriptElem_);
    var elems = [];
    for (var i = 0; i < subSpans.length; i++) {
        elems.push(subSpans[i]);
        if (i < subSpans.length - 1) {
            elems.push(goog.dom.createTextNode(" "));
        }
    }
    goog.dom.append(this.transcriptElem_, elems);
    this.makeSubsAndSubMap_(subSpans);
    this.streamBoxSearch_.setTranscriptElemAndSubs(
        this.transcriptElem_, this.subs_);
};

unisubs.streamer.StreamBox.prototype.enterDocument = function() {
    unisubs.streamer.StreamBox.superClass_.enterDocument.call(this);
    this.getHandler().
        listen(
            this.transcriptElem_,
            goog.events.EventType.SCROLL,
            this.transcriptScrolled_).
        listen(
            this.resyncButton_,
            goog.events.EventType.CLICK,
            this.resyncClicked_);
};



unisubs.streamer.StreamBox.prototype.transcriptScrolled_ = function(e) {
    if (this.videoScrolling_) {
        this.videoScrolling_ = false;
        return;
    }
    this.ignoreVideoScrolling_ = true;
    this.showResyncButton_(true);
};

unisubs.streamer.StreamBox.prototype.showResyncButton_ = function(show) {
    unisubs.style.setVisibility(this.resyncButton_, show);
};

unisubs.streamer.StreamBox.prototype.makeSubsAndSubMap_ = function(paragraphs) {
    var subSpans = [];
    // get all span span elements for this transcript
    goog.array.forEach(paragraphs, function(p){
        var nodes = goog.dom.getElementsByTagNameAndClass("span", null, p)
        for (var i = 0 ;i < nodes.length; i++){
            subSpans.push(nodes[i]);
        }
    });
    this.subs_ = goog.array.map(
        subSpans, function(s) { 
            return new unisubs.streamer.StreamSub(s); 
        });
    this.subMap_ = new goog.structs.Map();
    goog.array.forEach(this.subs_, function(s) { 
        s.setParentEventTarget(this);
        this.subMap_.set(s.SUBTITLE_ID, s); 
    }, this);
};

unisubs.streamer.StreamBox.prototype.resyncClicked_ = function(e) {
    e.preventDefault();
    this.ignoreVideoScrolling_ = false;
    this.showResyncButton_(false);
    this.showDisplayedSub_();
};

unisubs.streamer.StreamBox.prototype.displaySub = function(subtitleID) {
    if (this.displayedSub_) {
        this.displayedSub_.display(false);
        this.displayedSub_ = null;
    }
    if (subtitleID) {
        this.displayedSub_ = this.subMap_.get(subtitleID);
        this.showDisplayedSub_();
    }
};

unisubs.streamer.StreamBox.prototype.showDisplayedSub_ = function() {
    if (this.displayedSub_) {
        this.displayedSub_.display(true);
        this.scrollIntoView_(this.displayedSub_);
    }
};

unisubs.streamer.StreamBox.prototype.scrollIntoView_ = function(streamSub) {
    if (this.ignoreVideoScrolling_) {
        return;
    }
    this.videoScrolling_ = true;

    goog.style.scrollIntoContainerView(
        streamSub.getSpan(), this.transcriptElem_, true);
};
