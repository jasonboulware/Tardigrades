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

goog.provide('unisubs.subtitle.ReviewRightPanel');

/**
* @constructor
* @extends unisubs.RightPanel
*/
unisubs.subtitle.ReviewRightPanel = function(dialog, serverModel, helpContents, extraHelp, legendKeySpecs, showRestart, doneStrongText, doneText, reviewOrApprovalType, notesInput_) {
    unisubs.RightPanel.call(this, serverModel, helpContents, extraHelp,
                             legendKeySpecs,
                             showRestart, doneStrongText, doneText);
    this.reviewOrApprovalType_  = reviewOrApprovalType;
    this.showDoneButton = ! reviewOrApprovalType;
    this.notesInput_ = notesInput_;
    this.dialog_ = dialog;
};

goog.inherits(unisubs.subtitle.ReviewRightPanel, unisubs.RightPanel);

unisubs.subtitle.ReviewRightPanel.prototype.appendMiddleContentsInternal = function($d, el) {
    if (this.reviewOrApprovalType_){
        return;
    }
    el.appendChild(this.makeExtra_($d,
        'Drag edges in timeline to adjust subtitle timing'));
    el.appendChild(this.makeExtra_($d,
        'Double click any subtitle to edit text. Rollover subtitles and use buttons to tweak time, add / remove subtitles.'));
};
// FIXME: duplication with editmetadatarightpanel
unisubs.subtitle.ReviewRightPanel.prototype.finish = function(e, approvalCode, saveForLater) {
    if (e){
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
    var onCompletedCallback = function( isComplete){
        this.serverModel_.setComplete(isComplete);
        this.serverModel_.finish(successCallback, failureCallback, null, saveForLater);
    };
    // set the servel models vars to finishe this, the taskId and taskType were
    // set when retrieving the task data
    this.serverModel_.setTaskNotes(goog.dom.forms.getValue(this.notesInput_));
    this.serverModel_.setTaskApproved(approvalCode);
    // if approving and on original subs, we should prompt the user if the subs
    // are completed
    if (approvalCode == unisubs.Dialog.MODERATION_OUTCOMES.APPROVED &&
        this.inSubtitlingDialog_) {
        // we default to true, since the review is approving, most likely it
        // will be complete
        unisubs.subtitle.CompletedDialog.show(
            true, goog.bind(onCompletedCallback, this));
    } else {
        this.serverModel_.finish(successCallback, failureCallback, null, saveForLater);
    }
};
// FIXME: duplication with editmetadatarightpanel
unisubs.subtitle.ReviewRightPanel.prototype.appendCustomButtonsInternal = function($d, el) {
    if (!this.reviewOrApprovalType_ ){
        // for the subtitling dialog, we need the button to advance to the next painel
        return;
    }
    var buttonText = this.reviewOrApprovalType_ == unisubs.Dialog.REVIEW_OR_APPROVAL.APPROVAL ?
        'Approve' : 'Accept';

    this.sendBackButton_ = $d('a', {'class': 'unisubs-done widget-button'}, 'Send Back');
    this.approveButton_ = $d('a', {'class': 'unisubs-done widget-button'}, buttonText);

    el.appendChild(this.sendBackButton_);
    el.appendChild(this.approveButton_);

    var handler = this.getHandler();
    var that = this;
    handler.listen(this.sendBackButton_, 'click', function(e){
        that.finish(e, unisubs.Dialog.MODERATION_OUTCOMES.SEND_BACK, false);
    });
    handler.listen(this.approveButton_, 'click', function(e){
        that.finish(e, unisubs.Dialog.MODERATION_OUTCOMES.APPROVED, false);
    });
};
unisubs.subtitle.ReviewRightPanel.prototype.makeExtra_ = function($d, text) {
    return $d('div', 'unisubs-extra unisubs-extra-left',
              $d('p', null, text),
              $d('span', 'unisubs-spanarrow'));
};
