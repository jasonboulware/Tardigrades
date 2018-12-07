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

goog.provide('unisubs.subtitle.Dialog');

/**
 * @constructor
 * @param {unisubs.subtitle.ServerModel} serverModel
 * @param {unisubs.widget.SubtitleState} subtitles existing subtitles
 */
unisubs.subtitle.Dialog = function(videoSource, serverModel, subtitles, opt_opener, opt_skipFinished, reviewOrApprovalType) {
    unisubs.Dialog.call(this, videoSource);
    unisubs.SubTracker.getInstance().start(false);
    this.serverModel_ = serverModel;
    this.opener_ = opt_opener;
    this.skipFinished_ = !!opt_skipFinished;
    this.captionSet_ = this.serverModel_.getCaptionSet();
    this.captionManager_ =
        new unisubs.CaptionManager(
            this.getVideoPlayerInternal(), this.captionSet_);
    this.serverModel_ = serverModel;
    this.serverModel_.init();
    /**
     * @type {?boolean} True if we pass into FINISHED state.
     */
    this.saved_ = false;
    /**
     *
     * @type {?unisubs.subtitle.Dialog.State_}
     */
    this.state_ = null;
    this.currentSubtitlePanel_ = null;
    this.savedNotes_ = null;
    this.rightPanelListener_ = new goog.events.EventHandler(this);
    this.doneButtonEnabled_ = true;
    this.exitURL = null;

    /**
     * @type {unisubs.widget.SubtitleState}
     */
    this.subtitles_ = subtitles;

    this.alreadySaving_ = false;

    this.keyEventsSuspended_ = false;
    this.reviewOrApprovalType_ = reviewOrApprovalType;
    // if this is a review approve dialog, we must fetch saved notes for this task if available
    // but we should only do it when the dialog laods the first time
    // (else as users move back and forward between panels we might
    // overwrite their notes). This is what this flag is for
    this.notesFectched_ = false;
    if ( !Boolean(this.reviewOrApprovalType_)){
       this.notesFectched_ = true;
    }
};

goog.inherits(unisubs.subtitle.Dialog, unisubs.Dialog);

/**
 *
 * @enum
 */
unisubs.subtitle.Dialog.State_ = {
    TRANSCRIBE: 0,
    SYNC: 1,
    EDIT_METADATA: 2,
    REVIEW: 3,
    FINISHED: 4

};

// if the last sub is unsyced how much to consider it's end time 
// (after start time), in milliseconds
unisubs.subtitle.Dialog.END_TIME_PADDING = 4000;

unisubs.subtitle.Dialog.prototype.captionReached_ = function(event) {
    var c = event.caption;
    var text;

    if (c) {
        text = this.captionSet_.x['content'](c.node || c);
    } else {
        text = '';
    }
    this.getVideoPlayerInternal().showCaptionText(text);
};
unisubs.subtitle.Dialog.prototype.createDom = function() {
    unisubs.subtitle.Dialog.superClass_.createDom.call(this);
    var initialState = unisubs.subtitle.Dialog.State_.TRANSCRIBE;
    if (this.reviewOrApprovalType_){
        initialState = unisubs.subtitle.Dialog.State_.SYNC;
    }
    this.enterState_(initialState);
};
unisubs.subtitle.Dialog.prototype.showDownloadLink_ = function() {
    var that = this;
    this.getRightPanelInternal().showDownloadLink(
        function() {
            return that.makeDFXPString();
        });
};
unisubs.subtitle.Dialog.prototype.enterDocument = function() {
    unisubs.subtitle.Dialog.superClass_.enterDocument.call(this);
    unisubs.Dialog.translationDialogOpen = false;
    var doc = this.getDomHelper().getDocument();
    this.getHandler().
        listen(
            doc,
            goog.events.EventType.KEYDOWN,
            this.handleKeyDown_, true).
        listen(
            doc,
            goog.events.EventType.KEYUP,
            this.handleKeyUp_).
        listen(
            this.captionManager_,
            unisubs.CaptionManager.CAPTION,
            this.captionReached_);

    if (this.reviewOrApprovalType_ && !this.notesFectched_){
        var func  = this.serverModel_.fetchReviewData ;
        var that = this;
        if (this.reviewOrApprovalType_ == unisubs.Dialog.REVIEW_OR_APPROVAL.APPROVAL){
            func = this.serverModel_.fetchApproveData;
        }
        // make sure we retain the correct scope
        func.call(this.serverModel_, unisubs.task_id, function(body) {
            that.onNotesFetched_(body);
        });
    }

};
unisubs.subtitle.Dialog.prototype.setExtraClass_ = function(extraClass) {
    var extraClasses = goog.array.map(
        ['transcribe', 'sync', 'review', 'finished'],
        function(suffix) { return 'unisubs-modal-widget-' + suffix + (extraClass || ''); });
    var currentClass = "";
    var s = unisubs.subtitle.Dialog.State_;
    if (this.state_ == s.TRANSCRIBE)
        currentClass = extraClasses[0];
    else if (this.state_ == s.SYNC)
        currentClass = extraClasses[1];
    else if (this.state_ == s.REVIEW)
        currentClass = extraClasses[2];
    else if (this.state_ == s.FINISHED)
        currentClass = extraClasses[3];
    goog.array.remove(extraClasses, currentClass);
    goog.dom.classes.addRemove(this.getContentElement(), extraClasses, currentClass);
};
unisubs.subtitle.Dialog.prototype.setState_ = function(state) {
    this.state_ = state;

    this.suspendKeyEvents_(false);

    var s = unisubs.subtitle.Dialog.State_;

    this.setExtraClass_();

    var nextSubPanel = this.makeCurrentStateSubtitlePanel_();
    var captionPanel = this.getCaptioningAreaInternal();
    captionPanel.removeChildren(true);
    captionPanel.addChild(nextSubPanel, true);


    var rightPanel = nextSubPanel.getRightPanel();
    this.setRightPanelInternal(rightPanel);

    this.getTimelinePanelInternal().removeChildren(true);

    var currentNoteContent =  this.getNotesContent_(this.currentSubtitlePanel_);
    if (currentNoteContent){
        this.setNotesContent_(nextSubPanel, currentNoteContent);
    }

    this.disposeCurrentPanels_();
    this.currentSubtitlePanel_ = nextSubPanel;

    var et = unisubs.RightPanel.EventType;
    this.rightPanelListener_.
        listen(
            rightPanel, et.LEGENDKEY, this.handleLegendKeyPress_).
        listen(
            rightPanel, et.DONE, this.handleDoneKeyPress_).
        listen(
            rightPanel, et.SAVEANDOPENINNEWEDITOR, this.handleSaveAndOpenInNewEditor_).
        listen(
            rightPanel, et.SAVEANDEXIT, this.handleSaveAndExitKeyPress_).
        listen(
            rightPanel, et.GOTOSTEP, this.handleGoToStep_);
    var backButtonText = null;
    if (state == s.EDIT_METADATA ){
        backButtonText = "Back to Sync";
    }else if (state == s.SYNC && ! this.reviewOrApprovalType_){
        backButtonText = "Back to Typing";
    }else if (state == s.REVIEW ){
        backButtonText = "Back to Edit Info";
    }
    if (backButtonText){
        rightPanel.showBackLink(backButtonText);
        this.rightPanelListener_.listen(
            rightPanel, et.BACK, this.handleBackKeyPress_);

    }
    if (state == s.SYNC || state == s.REVIEW) {
            this.timelineSubtitleSet_ =
            new unisubs.timeline.SubtitleSet(
                this.captionSet_, this.getVideoPlayerInternal());
        this.getTimelinePanelInternal().addChild(
            new unisubs.timeline.Timeline(
                1, this.timelineSubtitleSet_,
                this.getVideoPlayerInternal(), false), true);
    }
    if (state == s.REVIEW)
        this.showDownloadLink_();

    var videoPlayer = this.getVideoPlayerInternal();
    if (this.isInDocument()) {
        videoPlayer.pause();
        videoPlayer.setPlayheadTime(0);
    }
};
unisubs.subtitle.Dialog.prototype.suspendKeyEvents_ = function(suspended) {
    this.keyEventsSuspended_ = suspended;
    if (this.currentSubtitlePanel_)
        this.currentSubtitlePanel_.suspendKeyEvents(suspended);
};
unisubs.subtitle.Dialog.prototype.setFinishedState_ = function() {
    if (this.skipFinished_)
        this.setVisible(false);
    if (!unisubs.isFromDifferentDomain()) {

        if (this.exitURL) {
            window.location = this.exitURL;
        } else {
            window.location.assign(this.serverModel_.getPermalink() + '?saved=true');
        }
        return;
    }
    this.state_ = unisubs.subtitle.Dialog.State_.FINISHED;
    this.setExtraClass_();
    var sharePanel = new unisubs.subtitle.SharePanel(
        this.serverModel_);
    this.setRightPanelInternal(sharePanel);
    this.getTimelinePanelInternal().removeChildren(true);
    this.getCaptioningAreaInternal().removeChildren(true);
    var bottomContainer = this.getBottomPanelContainerInternal();
    var bottomFinishedPanel = new unisubs.subtitle.BottomFinishedPanel(
        this, this.serverModel_.getPermalink());
    bottomContainer.addChild(bottomFinishedPanel, true);

    var videoPlayer = this.getVideoPlayerInternal();
    if (this.isInDocument()) {
        // TODO: make video player stop loading here?
        videoPlayer.pause();
        videoPlayer.setPlayheadTime(0);
    }
};
unisubs.subtitle.Dialog.prototype.handleGoToStep_ = function(event) {
    this.setState_(event.stepNo);
};
unisubs.subtitle.Dialog.prototype.handleKeyDown_ = function(event) {
    if (this.keyEventsSuspended_)
        return;
    var s = unisubs.subtitle.Dialog.State_;
    if (event.keyCode == goog.events.KeyCodes.TAB) {
        if (event.shiftKey) {
            this.skipBack_();
            this.getRightPanelInternal().setKeyDown(event.keyCode,
                unisubs.RightPanel.KeySpec.Modifier.SHIFT, true);
        }
        else {
            this.togglePause_();
            this.getRightPanelInternal().setKeyDown(event.keyCode, 0, true);
        }
        event.preventDefault();
    }
};
unisubs.subtitle.Dialog.prototype.handleKeyUp_ = function(event) {
    if (event.keyCode == goog.events.KeyCodes.TAB) {
        var modifier = 0;
        if (event.shiftKey)
            modifier = unisubs.RightPanel.KeySpec.Modifier.SHIFT;
        this.getRightPanelInternal().setKeyDown(event.keyCode, modifier, false);
    }
    else if (event.keyCode == goog.events.KeyCodes.SHIFT) {
        // if shift is released before tab, we still need to untoggle the legend
        this.getRightPanelInternal().setKeyDown(goog.events.KeyCodes.TAB,
            unisubs.RightPanel.KeySpec.Modifier.SHIFT, false);
    }
};
unisubs.subtitle.Dialog.prototype.handleBackKeyPress_ = function(event) {
    var s = unisubs.subtitle.Dialog.State_;
    if (this.state_ == s.SYNC)
        this.setState_(s.TRANSCRIBE);
    else if (this.state_ == s.REVIEW)
        this.setState_(s.EDIT_METADATA);
    else if (this.state_ == s.EDIT_METADATA)
        this.setState_(s.SYNC);
};
unisubs.subtitle.Dialog.prototype.handleLegendKeyPress_ = function(event) {
    if (event.keyCode == goog.events.KeyCodes.TAB &&
        event.keyEventType == goog.events.EventType.CLICK) {
        if (event.modifiers == unisubs.RightPanel.KeySpec.Modifier.SHIFT)
            this.skipBack_();
        else
            this.togglePause_();
    }
};
unisubs.subtitle.Dialog.prototype.handleSaveAndOpenInNewEditor_ = function(event) {
    if (!this.doneButtonEnabled_) {
        return;
    }

    this.exitURL = '/subtitles/editor/' + this.serverModel_.videoID_ + '/' +
        this.subtitles_.LANGUAGE + '/?from-old-editor=true';
    this.saveWork(false, true);
};
unisubs.subtitle.Dialog.prototype.handleSaveAndExitKeyPress_ = function(event) {
    if (!this.doneButtonEnabled_) {
        return;
    }
    this.saveWork(false, true);
};
unisubs.subtitle.Dialog.prototype.handleDoneKeyPress_ = function(event) {
    if (!this.doneButtonEnabled_) {
        return;
    }

    if (this.state_ == unisubs.subtitle.Dialog.State_.REVIEW) {

        // Make sure this subtitle set has captions.
        if((this.captionSet_.captions_.length === 0) && 
            !this.captions_.hasMetadataChanged()) {
                alert('You must create captions in order to submit.');
                return false;
        } else {
            if (this.captionSet_.needsSync()) {
                alert("You have unsynced captions. Please make sure that all lines, including the last one, have start and end time set properly before submitting subtitles. HINT: Use the up arrow to set a caption's end time");
                return false;
            }

            // We are satisifed with the start and end times of all captions.
            //
            // However, if the last caption has no end time, set it to either a) the duration of the video or b) the start time
            // of the caption + end time padding seconds.
            if (this.captionSet_.captions_[this.captionSet_.captions_.length -1].getEndTime() ==
                    unisubs.subtitle.EditableCaption.TIME_UNDEFINED) {

                var cap = this.captionSet_.captions_[this.captionSet_.captions_.length -1];

                var newEndTime;
                if (this.videoPlayer_.getDuration()) {
                    newEndTime = Math.min(this.videoPlayer_.getDuration() * 1000, cap.getStartTime() + unisubs.subtitle.Dialog.END_TIME_PADDING);
                } else {
                    newEndTime = cap.getStartTime() + unisubs.subtitle.Dialog.END_TIME_PADDING;
                }

                cap.setEndTime(newEndTime);
            }
        }

        this.saveWork(false, false);
    } else {
        this.enterState_(this.nextState_());
    }
};
unisubs.subtitle.Dialog.prototype.isWorkSaved = function() {
    if (this.reviewOrApprovalType_) {
        if (this.getNotesContent_(this.currentSubtitlePanel_) !== '') {
            return this.saved_;
        }
    }
    return this.saved_ || !this.serverModel_.anySubtitlingWorkDone();
};
unisubs.subtitle.Dialog.prototype.saveWorkInternal = function(closeAfterSave, saveForLater) {
    if(this.alreadySaving_){
        return;
    }

    this.alreadySaving_ = true;

    var notes = this.getNotesContent_(this.currentSubtitlePanel_);
    if (notes !== '') {
        this.serverModel_.setTaskNotes(notes);
    }

    if (goog.array.isEmpty(
        this.serverModel_.captionSet_.nonblankSubtitles()) &&
        !this.captionSet_.hasMetadataChanged() &&
        this.exitURL) {
        // No changes, but we want to go to the new subtitle editor.  Special
        // case this and just to a redirect
        this.saved_ = true;
        window.location = this.exitURL;
        return;
    }

    if (this.captionSet_.needsSync()) {
        this.saveWorkImpl_(closeAfterSave, saveForLater, false);
    } else if (goog.array.isEmpty(
        this.serverModel_.captionSet_.nonblankSubtitles()) && !this.forceSave_){
        this.alreadySaving_ = false;
        if(this.captionSet_.hasMetadataChanged()) {
            this.showTitleDescriptionChangedDialog(closeAfterSave, saveForLater);
        } else {
            // there are no subs here, close dialog or back to subtitling
            this.showEmptySubsDialog();
        }
        return;
    } else {
        unisubs.subtitle.CompletedDialog.show(
            !!this.subtitles_.IS_COMPLETE,
            goog.bind(this.saveWorkImpl_, this, closeAfterSave, saveForLater));
    }

};
unisubs.subtitle.Dialog.prototype.onWorkSaved = function(closeAfterSave, isComplete){
    this.saved_ = true;
    unisubs.widget.ResumeEditingRecord.clear();
    if (this.finishFailDialog_) {
        this.finishFailDialog_.setVisible(false);
        this.finishFailDialog_ = null;
    }
    if (closeAfterSave)
        this.setVisible(false);
    else {
        this.doneButtonEnabled_ = true;
        this.setFinishedState_();
    }
};
unisubs.subtitle.Dialog.prototype.saveWorkImpl_ = function(closeAfterSave, saveForLater, isComplete) {
    this.doneButtonEnabled_ = false;
    this.getRightPanelInternal().showLoading(true);
    this.captionSet_.completed = isComplete;
    var that = this;
    this.serverModel_.finish(
        function(serverMsg){
            unisubs.subtitle.OnSavedDialog.show(serverMsg, function(){
                that.onWorkSaved(closeAfterSave, isComplete);
            });
        },
        function(opt_status) {
            if (that.finishFailDialog_)
               that.finishFailDialog_.failedAgain(opt_status);
            else
                that.finishFailDialog_ = unisubs.finishfaildialog.Dialog.show(
                    that.captionSet_, opt_status,
                    goog.bind(that.saveWorkImpl_, that,
                              closeAfterSave, saveForLater, isComplete));
        },
        function() {
            that.doneButtonEnabled_ = true;
            that.getRightPanelInternal().showLoading(false);
        },
        saveForLater);
};
unisubs.subtitle.Dialog.prototype.enterState_ = function(state) {
    var skipHowto = unisubs.UserSettings.getBooleanValue(unisubs.UserSettings.Settings.SKIP_HOWTO_VIDEO);

    if ((!this.reviewOrApprovalType_) && (!skipHowto)) {
        this.showHowToForState_(state);
    } else {
        this.showGuidelinesForState_(state);
    }
};
unisubs.subtitle.Dialog.prototype.showGuidelinesForState_ = function(state) {
    var skipGuidelines = unisubs.UserSettings.getBooleanValue(
                            unisubs.UserSettings.Settings.ALWAYS_SKIP_GUIDELINES);

    if(skipGuidelines){
        this.setState_(state);
        return;
    }

    var s = unisubs.subtitle.Dialog.State_;
    // the same dialog can be used in transcribing or review approval, which guidelines should we use?
    var guideline = this.reviewOrApprovalType_ ? this.getTeamGuidelineForReview() : unisubs.guidelines['subtitle'];
    // guidelines should only be shown in the first step, which is transcribe for non review, or sync for review:
    var firstStep = s.TRANSCRIBE;
    if (this.reviewOrApprovalType_){
        firstStep = s.SYNC;
    }
    if (state !== firstStep || !guideline) {
        this.setState_(state);
        return;
    }

    this.suspendKeyEvents_(true);
    this.getVideoPlayerInternal().pause();


    var guidelinesPanel = new unisubs.GuidelinesPanel(guideline);
    this.showTemporaryPanel(guidelinesPanel);
    this.displayingGuidelines_ = true;

    var that = this;
    this.getHandler().listenOnce(guidelinesPanel, unisubs.GuidelinesPanel.CONTINUE, function(e) {
        goog.Timer.callOnce(function() {
            that.displayingGuidelines_ = false;
            that.hideTemporaryPanel();
            that.setState_(state);
        });
    });
};
unisubs.subtitle.Dialog.prototype.showHowToForState_ = function(state) {
    this.suspendKeyEvents_(true);
    this.getVideoPlayerInternal().pause();
    var s = unisubs.subtitle.Dialog.State_;
    var vc = unisubs.HowToVideoPanel.VideoChoice;
    var videoChoice;
    if (state == s.TRANSCRIBE)
        videoChoice = vc.TRANSCRIBE;
    else if (state == s.SYNC)
        videoChoice = vc.SYNC;
    else if (state == s.REVIEW)
        videoChoice = vc.REVIEW;
    if (videoChoice){
        // the edit metadata has no helper video
        var howToPanel = new unisubs.HowToVideoPanel(videoChoice);
        this.showTemporaryPanel(howToPanel);
        this.displayingHowTo_ = true;
        var that = this;
        this.getHandler().listenOnce(
            howToPanel, unisubs.HowToVideoPanel.CONTINUE,
            function(e) {
                goog.Timer.callOnce(function() {
                    that.displayingHowTo_ = false;
                    that.hideTemporaryPanel();
                    that.showGuidelinesForState_(state);
                });
            });

    }else{
        this.showGuidelinesForState_(state);
    }
 };
unisubs.subtitle.Dialog.prototype.skipBack_ = function() {
    var videoPlayer = this.getVideoPlayerInternal();
    var now = videoPlayer.getPlayheadTime();
    videoPlayer.setPlayheadTime(Math.max(now - 4, 0));
    videoPlayer.play();
};
unisubs.subtitle.Dialog.prototype.togglePause_ = function() {
    this.getVideoPlayerInternal().togglePause();
};
unisubs.subtitle.Dialog.prototype.makeCurrentStateSubtitlePanel_ = function() {
    var s = unisubs.subtitle.Dialog.State_;
    // make sure we clear the current displayed subtitle
    this.captionManager_.onPanelChanged();

    if (this.state_ == s.TRANSCRIBE) {
        return new unisubs.subtitle.TranscribePanel(
            this.captionSet_,
            this.getVideoPlayerInternal(),
            this.serverModel_,
            this.reviewOrApprovalType_);
    } else if (this.state_ == s.SYNC) {
        return new unisubs.subtitle.SyncPanel(
            this.captionSet_,
            this.getVideoPlayerInternal(),
            this.serverModel_,
            this.captionManager_,
            this.reviewOrApprovalType_);
    } else if (this.state_ == s.REVIEW) {
        return new unisubs.subtitle.ReviewPanel(
            this.captionSet_,
            this.getVideoPlayerInternal(),
            this.serverModel_,
            this.captionManager_,
            this.reviewOrApprovalType_,
            this);
    } else if (this.state_ == s.EDIT_METADATA) {
        return new unisubs.editmetadata.Panel(
            this.captionSet_,
            this.getVideoPlayerInternal(),
            this.serverModel_,
            this.captionManager_,
            null,
            true,
            this.reviewOrApprovalType_,
            this);
    }
};
unisubs.subtitle.Dialog.prototype.nextState_ = function() {
    var s = unisubs.subtitle.Dialog.State_;
    // the dialog is different when reviewing / approving
    // we only show the sync and edit metadata panels
    if (this.reviewOrApprovalType_) {
       if (this.state_ == s.SYNC) {
            return s.EDIT_METADATA;
       }
    } else {
        if (this.state_ == s.TRANSCRIBE) {
            return s.SYNC;
        } else if (this.state_ == s.EDIT_METADATA) {
            if (!this.isReviewOrApproval_) {
                return s.REVIEW;
            }
        } else if (this.state_ == s.SYNC) {
            return s.EDIT_METADATA;
        }
        else if (this.state_ == s.REVIEW) {
            return s.FINISHED;
        }
    }
};
unisubs.subtitle.Dialog.prototype.showLoginNag_ = function() {
    // not doing anything here right now.
};

/**
 * Did we ever pass into finished state?
 */
unisubs.subtitle.Dialog.prototype.isSaved = function() {
    return this.saved_;
};
unisubs.subtitle.Dialog.prototype.disposeCurrentPanels_ = function() {
    if (this.currentSubtitlePanel_) {
        this.currentSubtitlePanel_.dispose();
        this.currentSubtitlePanel_ = null;
    }
    this.rightPanelListener_.removeAll();
    if (this.timelineSubtitleSet_) {
        this.timelineSubtitleSet_.dispose();
        this.timelineSubtitleSet_ = null;
    }
};
unisubs.subtitle.Dialog.prototype.disposeInternal = function() {
    unisubs.subtitle.Dialog.superClass_.disposeInternal.call(this);
    this.disposeCurrentPanels_();
    if (this.captionManager_)
        this.captionManager_.dispose();
    this.serverModel_.dispose();
    this.rightPanelListener_.dispose();
    if (this.captionSet_)
        this.captionSet_.dispose();
};
unisubs.subtitle.Dialog.prototype.addTranslationsAndClose = function() {
    // Adam hypothesizes that this will get called 0 times except in testing
    unisubs.Tracker.getInstance().trackPageview('Adding_translations_on_close');
    var oldReturnURL = unisubs.returnURL;
    unisubs.returnURL = null;
    this.setVisible(false);
    unisubs.returnURL = oldReturnURL;
    var that = this;
    if (this.opener_) {
        unisubs.widget.ChooseLanguageDialog.show(
            true,
            function(subLanguage, originalLanguage, forked) {
                that.opener_.openDialog(
                    null, subLanguage, null,
                    unisubs.isForkedLanguage(subLanguage));
            });
    }
};
unisubs.subtitle.Dialog.prototype.onNotesFetched_ = function(body) {
    this.setNotesContent_(this.currentSubtitlePanel_, body);
};
unisubs.subtitle.Dialog.prototype.setNotesContent_ = function(panel, newContent) {
    if (panel && panel.bodyInput_) {
        panel.bodyInput_.value = newContent;
        this.savedNotes_ = null;
    } else {
        this.savedNotes_ = newContent;
    }
};
unisubs.subtitle.Dialog.prototype.getNotesContent_ = function(panel) {
    if (panel && panel.bodyInput_) {
        return  panel.bodyInput_.value;
    } else {
        return this.savedNotes_;
    }
};
unisubs.subtitle.Dialog.prototype.getServerModel = function(){
    return this.serverModel_;
};
unisubs.subtitle.Dialog.prototype.makeDFXPString =  function (){
    return this.captionManager_.x['xmlToString'](true, true);
};
