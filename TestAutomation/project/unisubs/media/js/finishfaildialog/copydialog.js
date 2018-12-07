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

goog.provide('unisubs.finishfaildialog.CopyDialog');

/**
 * @constructor
 */
unisubs.finishfaildialog.CopyDialog = function(headerText, dfxpString, languageCode) {
    goog.ui.Dialog.call(this, 'unisubs-modal-lang', true);
    this.setButtonSet(null);
    this.setDisposeOnHide(true);
    this.headerText_ = headerText;

    if (dfxpString) {
        this.dfxpString_ = dfxpString;
    }
    if (languageCode) {
        this.languageCode_ = languageCode;
    }
};

goog.inherits(unisubs.finishfaildialog.CopyDialog, goog.ui.Dialog);

unisubs.finishfaildialog.CopyDialog.prototype.createDom = function() {
    unisubs.finishfaildialog.CopyDialog.superClass_.createDom.call(this);
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    this.textarea_ = $d('textarea', {'class': 'copy-dialog', 'value': this.dfxpString_});

    this.switcher_ = $d('select', 'copy-dialog-select',
            $d('option', {value: 'dfxp'}, 'DFXP'),
            $d('option', {value: 'srt'}, 'SRT'),
            $d('option', {value: 'ssa'}, 'SSA'),
            $d('option', {value: 'sbv'}, 'SBV')
        );

    this.getHandler().listen(
        this.switcher_,
        goog.events.EventType.CHANGE,
        this.switcherChanged_);

    goog.dom.append(
        this.getContentElement(),
        $d('p', null, this.headerText_),
        this.switcher_,
        this.textarea_);
};
unisubs.finishfaildialog.CopyDialog.prototype.switcherChanged_ = function(e) {
    e.preventDefault();
    this.fillTextarea(this.switcher_.value);
};
unisubs.finishfaildialog.CopyDialog.prototype.fillTextarea = function(format) {
    if (format === 'dfxp') {
        goog.dom.forms.setValue(this.textarea_, this.dfxpString_);
    } else {
        // watchout the selenium test checks for this value, see editor_pages/subtitle_editor.py
        goog.dom.forms.setValue(this.textarea_, 'Processing...');

        var textarea = this.textarea_;
        var that = this;

        goog.net.XhrIo.send('/widget/convert_subtitles/',
            function(event) {

                var output, response;

                if (!event.target.isSuccess()) {
                    output = 'There was an error processing your request. Below are your subtitles in DFXP format. Please copy them (not including this message) and you may upload them later.\n\n';
                    output += that.dfxpString_;
                }
                else if (event.target.getResponseJson()['errors']){
                    // watchout the selenium test checks for this value,
                    // see editor_pages/subtitle_editor.py
                    output = "Something went wrong, we're terribly sorry."
                }else{
                    output = event.target.getResponseJson()['result'];
                }

                goog.dom.forms.setValue(textarea, output);

            },
            'POST',
            unisubs.Rpc.encodeKeyValuePairs_({
                'subtitles': this.dfxpString_,
                'format': format,
                'language_code': this.languageCode_}
            ),
            null, null);
    }

};
unisubs.finishfaildialog.CopyDialog.prototype.enterDocument = function() {
    unisubs.finishfaildialog.CopyDialog.superClass_.enterDocument.call(this);
    this.getHandler().listen(
        this.textarea_,
        ['focus', 'click'],
        this.focusTextarea_);
};
unisubs.finishfaildialog.CopyDialog.prototype.focusTextarea_ = function() {
    var textarea = this.textarea_;
    goog.Timer.callOnce(function() { textarea.select(); });
};
unisubs.finishfaildialog.CopyDialog.showForErrorLog = function(log) {
    var copyDialog = new unisubs.finishfaildialog.CopyDialog(
        "This is the error report we generated. It would be a big help to us if you could copy and paste it into an email and send it to us at widget-logs@universalsubtitles.org. Thank you!",
        log);
    copyDialog.setVisible(true);
};
unisubs.finishfaildialog.CopyDialog.showForSubs = function(dfxpString, languageCode) {
    var copyDialog = new unisubs.finishfaildialog.CopyDialog(
        "Copy/paste these subtitles into a text editor and save. Use the dropdown to choose a format (make sure the file extension matches the format you choose). You'll be able to upload the subtitles to your video later.",
        dfxpString,
        languageCode);
    copyDialog.setVisible(true);
};
