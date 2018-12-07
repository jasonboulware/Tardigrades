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

goog.provide('unisubs.widget.EmptySubsWarningDialog');
/**
* Shows a warning that this session cannot be saved, since
* there are no subtitles to save (the user has either deleted)
* them or never entered none. Either the dialog will be closed
* and the user will be back into subtitling , or he will quit
* the dialog all together. Valid for both Subtitiling and Translation 
* dialogs
* @constructor
* @param {function()} finishedCallback Called iff the wants to quit all together
*/
unisubs.widget.EmptySubsWarningDialog = function(finishedCallback) {
    goog.ui.Dialog.call(this, 'unisubs-modal-completed', true);
    this.setButtonSet(null);
    this.setDisposeOnHide(true);
    this.finishedCallback_ = finishedCallback;
};
goog.inherits(unisubs.widget.EmptySubsWarningDialog, goog.ui.Dialog);

unisubs.widget.EmptySubsWarningDialog.prototype.createDom = function() {
    unisubs.widget.EmptySubsWarningDialog.superClass_.createDom.call(this);
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    this.getElement().appendChild($d('h3', null, "You haven't entered any subtitles!"));
    this.getElement().appendChild(
        $d('div', null,
           $d('p', null, 
              'You can go back and continue working on these subtitles, or ' +
              'you can just exit without saving.' )));
    this.backToSubtitlingButton_ =
        $d('a',
           {'href':'#',
            'className': 'unisubs-green-button unisubs-big'},
           'Back to subtitling!');
    this.justQuitButton_ =
        $d('a',
           {'href':'#',
            'className': 'unisubs-green-button unisubs-big'},
           'Just exit');
    this.getElement().appendChild(this.backToSubtitlingButton_);
    this.getElement().appendChild(this.justQuitButton_);
    var clearDiv = $d('div');
    unisubs.style.setProperty(clearDiv, 'clear', 'both');
    clearDiv.innerHTML = "&nbsp;";
    this.getElement().appendChild(clearDiv);
};

unisubs.widget.EmptySubsWarningDialog.prototype.enterDocument = function() {
    unisubs.widget.EmptySubsWarningDialog.superClass_.enterDocument.call(this);
    this.getHandler().
        listen(this.justQuitButton_,
               'click',
               this.linkClicked_).
        listen(this.backToSubtitlingButton_,
               'click',
               this.linkClicked_);
};

unisubs.widget.EmptySubsWarningDialog.prototype.linkClicked_ = function(e) {
    e.preventDefault();
    this.setVisible(false);
    if (e.target == this.justQuitButton_) {
        this.finishedCallback_();
    }else{
        this.setVisible(false);
    }
};
