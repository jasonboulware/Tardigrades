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

goog.provide('unisubs.translate.MetadataTranslation');

unisubs.translate.MetadataTranslationWidget = function(originalValue, captionSet, key) {
    goog.ui.Component.call(this);
    this.originalValue = originalValue || '';
    this.captionSet_ = captionSet;
    this.key = key;
};

goog.inherits(unisubs.translate.MetadataTranslationWidget, goog.ui.Component);

unisubs.translate.MetadataTranslationWidget.prototype.createDom = function() {
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());

    this.setElementInternal(
        $d('li', null,
           $d('div', null,
              $d('span', 'unisubs-title unisubs-title-notime',
                  $d('span', 'meta', this.getLabel()),
                  this.originalValue ),
              this.loadingIndicator_ = $d('span', 'unisubs-loading-indicator', 'loading...')
           ),
           this.translateInput_ = $d('textarea', 'unisubs-translateField' + (this.captionSet_.languageIsRTL ? ' is-rtl' : ''))
        )
    );

    this.getHandler().listen(
        this.translateInput_, goog.events.EventType.BLUR,
        this.inputLostFocus_);
};
unisubs.translate.MetadataTranslationWidget.prototype.showLoadingIndicator = function(){
    unisubs.style.showElement(this.loadingIndicator_, true);
};
unisubs.translate.MetadataTranslationWidget.prototype.hideLoadingIndicator = function(){
    unisubs.style.showElement(this.loadingIndicator_, false);
};
unisubs.translate.MetadataTranslationWidget.prototype.getLabel = function() {
    switch(this.key) {
        case 'speaker-name':
            return 'Speaker Name: ';
        case 'location':
            return 'Location: ';
        default:
            return 'Unknown Type: ';
    }
};
unisubs.translate.MetadataTranslationWidget.prototype.getOriginalValue = function(){
    return this.originalValue;
};
unisubs.translate.MetadataTranslationWidget.prototype.isEmpty = function(){
    return ! goog.string.trim(this.translateInput_.value);
};
unisubs.translate.MetadataTranslationWidget.prototype.setTranslation = function(value){
    this.translateInput_.value = value;
    this.inputLostFocus_();
};

unisubs.translate.MetadataTranslationWidget.prototype.setTranslationContent = 
    unisubs.translate.MetadataTranslationWidget.prototype.setTranslation;

unisubs.translate.MetadataTranslationWidget.prototype.inputLostFocus_ = function(event) {
    this.captionSet_.metadata[this.key] = this.translateInput_.value;
};
