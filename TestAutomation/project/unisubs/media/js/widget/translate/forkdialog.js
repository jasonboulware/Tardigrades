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

goog.provide('unisubs.translate.ForkDialog');

/**
 * @constructor
 * @param {function()} finishedCallback Called iff the user decides to go ahead and fork.
 */
unisubs.translate.ForkDialog = function(finishedCallback) {
    goog.ui.Dialog.call(this, 'unisubs-forkdialog', true);
    this.setButtonSet(null);
    this.setDisposeOnHide(true);
    this.finishedCallback_ = finishedCallback;
};
goog.inherits(unisubs.translate.ForkDialog, goog.ui.Dialog);

unisubs.translate.ForkDialog.prototype.createDom = function() {
    unisubs.translate.ForkDialog.superClass_.createDom.call(this);
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    this.getElement().appendChild(
        $d('div', null,
           $d('h3', null, 'Convert to Timed Subtitles'),
           $d('p', null, 'You are about to convert this translation to Timed Subtitles. Please note:'),
           $d('ul', null, 
              $d('li', null, 'You will no longer be able to see the language you were translating from.'),
              $d('li', null, 'Any untranslated lines will be blank.'),
              $d('li', null, 'You will not be able to undo this action.')
            ),
           $d('p', null,
              $d('strong', null, 'ARE YOU SURE you want to continue?')
            )
           ));
    this.cancelButton_ =
        $d('a',
           {'href':'#',
            'className': 'unisubs-green-button unisubs-big'},
           'Cancel');
    this.okButton_ =
        $d('a',
           {'href':'#',
            'className': 'unisubs-green-button unisubs-big'},
           'Continue');
    this.getElement().appendChild(this.cancelButton_);
    this.getElement().appendChild(this.okButton_);
    var clearDiv = $d('div');
    unisubs.style.setProperty(clearDiv, 'clear', 'both');
    clearDiv.innerHTML = "&nbsp;";
    this.getElement().appendChild(clearDiv);
};

unisubs.translate.ForkDialog.prototype.enterDocument = function() {
    unisubs.translate.ForkDialog.superClass_.enterDocument.call(this);
    this.getHandler().
        listen(this.okButton_,
               'click',
               this.linkClicked_).
        listen(this.cancelButton_,
               'click',
               this.linkClicked_);
};

unisubs.translate.ForkDialog.prototype.linkClicked_ = function(e) {
    e.preventDefault();
    this.setVisible(false);
    if (e.target == this.okButton_) {
        this.finishedCallback_();
    }
};
