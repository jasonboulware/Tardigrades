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

goog.provide('unisubs.translate.DescriptionTranslation');

/**
 * @constructor
 * @param {string} video description
 */
unisubs.translate.DescriptionTranslationWidget = function(videoDescription, captionSet) {
    goog.ui.Component.call(this);
    this.originalVideoDescription_ = videoDescription || '';
    this.captionSet_ = captionSet;
};

goog.inherits(unisubs.translate.DescriptionTranslationWidget, goog.ui.Component);

unisubs.translate.DescriptionTranslationWidget.prototype.createDom = function() {
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());

    this.setElementInternal(
        $d('li', null,
           $d('div', null,
              $d('span', 'unisubs-description unisubs-description-notime',
                  $d('span', 'meta', 'Description: '),
                  this.originalVideoDescription_),
              this.loadingIndicator_ = $d('span', 'unisubs-loading-indicator', 'loading...')
           ),
           this.translateInput_ = $d('textarea', {"class":'unisubs-translateField unisubs-descriptionField' + (this.captionSet_.languageIsRTL ? ' is-rtl' : ''), "rows":"10"})
        )
    );

    this.getHandler().listen(
        this.translateInput_, goog.events.EventType.BLUR,
        this.inputLostFocus_);
};
unisubs.translate.DescriptionTranslationWidget.prototype.showLoadingIndicator = function(){
    unisubs.style.showElement(this.loadingIndicator_, true);
};
unisubs.translate.DescriptionTranslationWidget.prototype.hideLoadingIndicator = function(){
    unisubs.style.showElement(this.loadingIndicator_, false);
};
unisubs.translate.DescriptionTranslationWidget.prototype.getOriginalValue = function(){
    return this.originalVideoDescription_;
};
unisubs.translate.DescriptionTranslationWidget.prototype.isEmpty = function(){
    return ! goog.string.trim(this.translateInput_.value);
};
unisubs.translate.DescriptionTranslationWidget.prototype.setTranslation = function(value){
    this.translateInput_.value = value;
    this.inputLostFocus_();
};

unisubs.translate.DescriptionTranslationWidget.prototype.setTranslationContent = 
    unisubs.translate.DescriptionTranslationWidget.prototype.setTranslation;

unisubs.translate.DescriptionTranslationWidget.prototype.inputLostFocus_ = function(event) {
    this.captionSet_.description = this.translateInput_.value;
};
