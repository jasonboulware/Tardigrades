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

goog.provide('unisubs.translate.TranslationWidget');

/**
 * @constructor
 * @param {Object.<string, *>} subtitle Base language subtitle in json format
 * @param {unisubs.subtitle.EditableCaption} translation
 */
unisubs.translate.TranslationWidget = function(originalNode, translationCaption, dialog, dfxpWrapper) {
    goog.ui.Component.call(this);
    this.originalNode_ = originalNode;
    this.dialog_ = dialog;
    this.videoURL_ = this.dialog_.getVideoPlayerInternal().videoSource_.videoURL_ || '';

    /**
     * @type {unisubs.subtitle.EditableCaption}
     */
    this.translationCaption_ = translationCaption;
    this.dfxpWrapper_ = dfxpWrapper;
};

goog.inherits(unisubs.translate.TranslationWidget, goog.ui.Component);

unisubs.translate.TranslationWidget.prototype.getSubtitle = function(){
    return this.originalNode_;
};
unisubs.translate.TranslationWidget.prototype.getOriginalValue = function(){
    return this.dfxpWrapper_['content'](this.originalNode_);
};

unisubs.translate.TranslationWidget.prototype.createDom = function() {

    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());

    var timingToDisplay = this.translationCaption_.getStartTime();

    this.setElementInternal(
        $d('li', null,
           $d('div', null,
              $d('span', {'className': 'unisubs-timestamp-time-fixed'}, 
                         unisubs.formatTime(timingToDisplay)),
              this.originalTitleWidgetThing_ = $d('span', 'unisubs-title unisubs-title-notime', ''),
              this.loadingIndicator_ = $d('span', 'unisubs-loading-indicator', 'loading...')
           ),
           this.translateInput_ = $d('textarea', 'unisubs-translateField')
        )
    );

    this.originalTitleWidgetThing_.innerHTML = this.dfxpWrapper_['markdownToHTML'](this.getOriginalValue());
    
    this.getHandler()
        .listen(
            this.translateInput_, goog.events.EventType.KEYUP,
            goog.bind(this.inputKeyUp_, this, true))
        .listen(
            this.translateInput_, goog.events.EventType.BLUR,
            goog.bind(this.inputLostFocus_, this, true))
        .listen(
            this.translateInput_, goog.events.EventType.FOCUS,
            this.inputGainedFocus_);
    this.setTranslateinputValue(this.translationCaption_ ? this.translationCaption_.getText() : '');
};
unisubs.translate.TranslationWidget.prototype.inputGainedFocus_ = function(event) {
    this.onFocusText_ = this.getTranslateinputValue();
    this.dialog_.getVideoPlayerInternal().showCaptionText(this.onFocusText_ || this.getOriginalValue());
};
unisubs.translate.TranslationWidget.prototype.inputKeyUp_ = function(track) {
    this.onKeyUpText_ = this.getTranslateinputValue();
    this.dialog_.getVideoPlayerInternal().showCaptionText(this.onKeyUpText_ || this.getOriginalValue());
};
unisubs.translate.TranslationWidget.prototype.inputLostFocus_ = function(track) {
    var value = goog.string.trim(this.getTranslateinputValue());
    var edited = value != this.onFocusText_;
    if (track && edited) {
        if (this.onFocusText_ == "")
            unisubs.SubTracker.getInstance().trackAdd(this.translationCaption_.getCaptionIndex());
    }
    this.translationCaption_.setText(value);
    this.dialog_.getVideoPlayerInternal().showCaptionText('');
};
unisubs.translate.TranslationWidget.prototype.setTranslationContent = function(value){
    this.setTranslateinputValue(value);
    this.inputLostFocus_(false);
};
unisubs.translate.TranslationWidget.prototype.setEnabled = function(enabled) {
    this.translateInput_.disabled = !enabled;
    if (!enabled) {
        this.setTranslateinputValue('');
    }
};
unisubs.translate.TranslationWidget.prototype.getTranslateinputValue = function() {
    return this.translateInput_.value;
};
unisubs.translate.TranslationWidget.prototype.setTranslateinputValue = function(text) {
    this.translateInput_.value = text;
};
unisubs.translate.TranslationWidget.prototype.getCaptionID = function() {
    return this.dfxpWrapper_['getSubtitleIndex'](this.originalNode_);
};

/**
 * Return if translate input has some value
 * @return {boolean}
 */
unisubs.translate.TranslationWidget.prototype.isEmpty = function(){
    return !goog.string.trim(this.getTranslateinputValue());
};

unisubs.translate.TranslationWidget.prototype.showLoadingIndicator = function(){
    unisubs.style.showElement(this.loadingIndicator_, true);
};
unisubs.translate.TranslationWidget.prototype.hideLoadingIndicator = function(){
    unisubs.style.showElement(this.loadingIndicator_, false);
};
