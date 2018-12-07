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

goog.provide('unisubs.widget.ConfirmDialog');

unisubs.widget.ConfirmDialog = function(title, message, confirmCallback, cancelCallback) {
    goog.ui.Dialog.call(this, 'unisubs-modal-completed', true);
    this.setButtonSet(null);
    this.setDisposeOnHide(true);
    this.cancelCallback = cancelCallback;
    this.confirmCallback = confirmCallback;
    this.title = title;
    this.message = message;
};

goog.inherits(unisubs.widget.ConfirmDialog, goog.ui.Dialog);

unisubs.widget.ConfirmDialog.prototype.createDom = function() {
    unisubs.widget.ConfirmDialog.superClass_.createDom.call(this);
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());

    this.getElement().appendChild($d('h3', null, this.title));
    this.getElement().appendChild(
        $d('div', null,
           $d('p', null, this.message)));

    this.confirmButton =
        $d('a',
           {'href':'#',
            'className': 'unisubs-green-button unisubs-big'},
           'Ok');
    this.cancelButton =
        $d('a',
           {'href':'#',
            'className': 'unisubs-green-button unisubs-big'},
           'Cancel');

    this.getElement().appendChild(this.cancelButton);
    this.getElement().appendChild(this.confirmButton);

    var clearDiv = $d('div');
    unisubs.style.setProperty(clearDiv, 'clear', 'both');
    clearDiv.innerHTML = "&nbsp;";
    this.getElement().appendChild(clearDiv);
};

unisubs.widget.ConfirmDialog.prototype.enterDocument = function() {
    unisubs.widget.ConfirmDialog.superClass_.enterDocument.call(this);
    this.getHandler().
        listen(this.confirmButton,
               'click',
               this.linkClicked_).
        listen(this.cancelButton,
               'click',
               this.linkClicked_);
};

unisubs.widget.ConfirmDialog.prototype.linkClicked_ = function(e) {
    e.preventDefault();

    this.setVisible(false);

    if (e.target == this.confirmButton) {
        if(this.confirmCallback){
            this.confirmCallback();
        }
    } else {
        if(this.cancelCallback){
            this.cancelCallback();
        }
    }
};

