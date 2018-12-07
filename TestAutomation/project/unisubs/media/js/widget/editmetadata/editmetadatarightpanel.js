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

goog.provide('unisubs.editmetadata.RightPanel');

/**
 * @constructor
 * @extends unisubs.RightPanel
 */
unisubs.editmetadata.RightPanel = function(dialog,
                                           serverModel,
                                           helpContents,
                                           extraHelp,
                                           legendKeySpecs,
                                           showRestart,
                                           doneStrongText,
                                           doneText,
                                           reviewOrApprovalType,
                                           notesInput,
                                           inSubtitlingDialog) {
    unisubs.RightPanel.call(this,  serverModel, helpContents, extraHelp,
                            legendKeySpecs, showRestart, doneStrongText, doneText);

    this.showSaveExit = true;
    this.showDoneButton = !reviewOrApprovalType;
    this.helpContents = helpContents;
    // TODO: See if there's a way to avoid the circular reference here.
    this.dialog_ = dialog;
    this.reviewOrApprovalType_ = reviewOrApprovalType;
    this.inSubtitlingDialog_ = inSubtitlingDialog;
    this.notesInput_ = notesInput;
};

goog.inherits(unisubs.editmetadata.RightPanel, unisubs.RightPanel);

unisubs.editmetadata.RightPanel.prototype.appendHelpContentsInternal = function($d, el) {
    var helpHeadingDiv = $d('div', 'unisubs-help-heading');
    el.appendChild(helpHeadingDiv);
    helpHeadingDiv.appendChild($d('h2', null, this.helpContents_.header));
    if (this.helpContents_.numSteps) {
        var that = this;
        var stepsUL = $d('ul', null, $d('span', null, 'Steps'));
        for (var i = 0; i < this.helpContents_.numSteps; i++) {
            var linkAttributes = { 'href' : '#' };
            if (i == this.helpContents_.activeStep)
                linkAttributes['className'] = 'unisubs-activestep';
            var link = $d('a', linkAttributes, i + 1 + '');
            this.getHandler().listen(
                link, 'click', goog.partial(function(step, e) {
                    e.preventDefault();
                }, i));
            stepsUL.appendChild($d('li', null, link));
        }
        helpHeadingDiv.appendChild(stepsUL);
    }
    if (this.helpContents_.html) {
        var div = $d('div');
        div.innerHTML = this.helpContents_.html;
        el.appendChild(div);
    }
    else{
        goog.array.forEach(this.helpContents_.paragraphs, function(p) {
            el.appendChild($d('p', null, p));
        });
    }

    // FIXME : check if not needed when not in review mode
    if (false && this.showDoneButton){

        var stepsDiv = $d('div', 'unisubs-steps', this.loginDiv_);
        this.doneAnchor_ = this.createDoneAnchor_($d);
        stepsDiv.appendChild(this.doneAnchor_);
        el.appendChild(stepsDiv);

        this.getHandler().listen(this.doneAnchor_, 'click', this.doneClicked_);
    }
};

// FIXME: remove duplication from the subtitle.reviewpanel
unisubs.editmetadata.RightPanel.prototype.finish = function(e, approvalCode, saveForLater) {
    if (e) {
        e.preventDefault();
    }
    var dialog = this.dialog_;
    var that = this;

    var actionName = this.reviewOrApprovalType_ == unisubs.Dialog.REVIEW_OR_APPROVAL.APPROVAL ?
        'approve' : 'review';
    var successCallback = function(serverMsg) {
        unisubs.subtitle.OnSavedDialog.show(serverMsg, function() {
            dialog.onWorkSaved(true);
        }, actionName);
    };

    var failureCallback = function(opt_status) {
        if (dialog.finishFailDialog_) {
            dialog.finishFailDialog_.failedAgain(opt_status);
        } else {
            dialog.finishFailDialog_ = unisubs.finishfaildialog.Dialog.show(
                that.serverModel_.getCaptionSet(), opt_status,
                goog.bind(dialog.saveWorkInternal, dialog, false));
        }
    };

    var onCompletedCallback = function(isComplete){
        this.serverModel_.setComplete(isComplete);
        this.serverModel_.finish(successCallback, failureCallback, null, saveForLater);
    };
    // set the servel models vars to finish this, the taskId and taskType were
    // set when retrieving the task data
    this.serverModel_.setTaskNotes(goog.dom.forms.getValue(this.notesInput_));
    this.serverModel_.setTaskApproved(approvalCode);
    // if approving and on original subs, we should prompt the user if the subs
    // are completed
    if (approvalCode == unisubs.Dialog.MODERATION_OUTCOMES.APPROVED &&
        this.inSubtitlingDialog_){
        // we default to true, since the review is approving, most likely it
        // will be complete
        unisubs.subtitle.CompletedDialog.show(
            true, goog.bind(onCompletedCallback, this));
    } else {
        this.serverModel_.finish(successCallback, failureCallback, null, saveForLater);
    }

};
unisubs.editmetadata.RightPanel.prototype.appendCustomButtonsInternal = function($d, el) {
    if (!this.reviewOrApprovalType_ ){
        // for the subtitling dialog, we need the button to advance to the next painel
        return;
    }
    this.sendBackButton_ = $d('a', {'class': 'unisubs-done widget-button'}, 'Send Back');
    var buttonText = this.reviewOrApprovalType_ == unisubs.Dialog.REVIEW_OR_APPROVAL.APPROVAL ?
        'Approve' : 'Accept';
    this.approveButton_ = $d('a', {'class': 'unisubs-done widget-button'}, buttonText);

    var handler = this.getHandler();

    if (this.serverModel_.getCaptionSet().needsSync() ||
        this.serverModel_.getCaptionSet().needsTranslation()) {

        this.needsSyncWarning_ = $d('p', {},
                                    $d('div', {'class': 'unisubs-needs-sync unisubs-extra'}, 
                                        $d('p', {}, 'The draft has unsynced / untranslated lines and cannot be approved / accepted. You can complete it or send back.'),
                                        $d('span', {'class': 'unisubs-spanarrow'}, '')
                                    )
                                );

        this.approveButton_.style.opacity = '0.3';
        el.appendChild(this.needsSyncWarning_);
        el.appendChild(this.sendBackButton_);
        el.appendChild(this.approveButton_);

    } else {

        el.appendChild(this.sendBackButton_);
        el.appendChild(this.approveButton_);

        handler.listen(this.approveButton_, 'click', function(e){
            that.finish(e, unisubs.Dialog.MODERATION_OUTCOMES.APPROVED, false);
        });
    }

    var that = this;

    handler.listen(this.sendBackButton_, 'click', function(e){
        that.finish(e, unisubs.Dialog.MODERATION_OUTCOMES.SEND_BACK, false);
    });
};
