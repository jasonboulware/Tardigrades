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

goog.provide('unisubs.editmetadata.Dialog');

/**
 * @constructor
 */
unisubs.editmetadata.Dialog = function(videoSource, serverModel, subtitleState) {
    unisubs.Dialog.call(this, videoSource);
    unisubs.SubTracker.getInstance().start(true);

    this.opener_ = opener;
    this.subtitleState_ = subtitleState;
    this.serverModel_ = serverModel;
    this.captionSet_ = this.serverModel_.getCaptionSet();
    this.captionManager_ = new unisubs.CaptionManager(this.getVideoPlayerInternal(), this.captionSet_);
    this.saved_ = false;
};
goog.inherits(unisubs.editmetadata.Dialog, unisubs.Dialog);

unisubs.editmetadata.Dialog.prototype.createDom = function() {
    unisubs.editmetadata.Dialog.superClass_.createDom.call(this);
    this.metadataPanel_ = new unisubs.editmetadata.EditmetadataPanel(
        this.serverModel_.getCaptionSet(), this.getVideoPlayerInternal(),
        this.serverModel_, this.captionManager_);
    this.getCaptioningAreaInternal().addChild(this.metadataPanel_, true);

    var rightPanel = this.createRightPanel_();

    this.setRightPanelInternal(rightPanel);
    this.getHandler().
        listen(
            rightPanel, unisubs.RightPanel.EventType.DONE,
            this.handleDoneKeyPress_).
        listen(
            rightPanel, unisubs.RightPanel.EventType.SAVEANDEXIT,
            this.handleSaveAndExitKeyPress_);
    goog.dom.classes.add(this.getContentElement(), 'unisubs-modal-widget-translate');
    this.showGuidelines_();

    this.timelineSubtitleSet_ = new unisubs.timeline.SubtitleSet(this.captionSet_, this.getVideoPlayerInternal());
    this.getTimelinePanelInternal().addChild(
        new unisubs.timeline.Timeline(1, this.timelineSubtitleSet_,
                                      this.getVideoPlayerInternal(), true), true);
};

unisubs.editmetadata.Dialog.prototype.showGuidelines_ = function() {
    if (!unisubs.guidelines['review']) {
        return;
    }

    var guidelinesPanel = new unisubs.GuidelinesPanel(unisubs.guidelines['review']);
    this.showTemporaryPanel(guidelinesPanel);
    this.displayingGuidelines_ = true;

    var that = this;
    this.getHandler().listenOnce(guidelinesPanel, unisubs.GuidelinesPanel.CONTINUE, function(e) {
        goog.Timer.callOnce(function() {
            that.displayingGuidelines_ = false;
            that.hideTemporaryPanel();
        });
    });
};

unisubs.editmetadata.Dialog.prototype.createRightPanel_ = function() {
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    var title = "Edit Title & Description Subtitles";
    var helpContents = new unisubs.RightPanel.HelpContents(title, [
        $d('p', {}, "Edit title and description for this video.")
    ]);
    return new unisubs.editmetadata.EditmetadataRightPanel(
        this, this.serverModel_, helpContents, [], false, "Done?", "Submit final Review");
};

unisubs.editmetadata.Dialog.prototype.captionReached_ = function(event) {
    var c = event.caption;
    this.getVideoPlayerInternal().showCaptionText(c ? c.getText() : '');
};

unisubs.editmetadata.Dialog.prototype.enterDocument = function() {
    unisubs.editmetadata.Dialog.superClass_.enterDocument.call(this);
    unisubs.Dialog.translationDialogOpen = false;
    var doc = this.getDomHelper().getDocument();
    this.getHandler().listen(
            this.captionManager_,
            unisubs.CaptionManager.CAPTION,
            this.captionReached_);
};

unisubs.editmetadata.Dialog.prototype.disposeInternal = function() {
    unisubs.editmetadata.Dialog.superClass_.disposeInternal.call(this);
    this.serverModel_.dispose();
    this.timelineSubtitleSet_.dispose();
    this.timelineSubtitleSet_ = null;
};

unisubs.editmetadata.Dialog.prototype.getSubtitleLanguage = function() {
    return this.subtitleState_.LANGUAGE;
};

unisubs.editmetadata.Dialog.prototype.getServerModel = function() {
    return this.serverModel_;
};

unisubs.editmetadata.Dialog.prototype.isWorkSaved = function() {
    return this.saved_ || false;
};

unisubs.editmetadata.Dialog.prototype.saveWorkInternal = function(closeAfterSave, saveForLater) {
    var that = this;
    this.getRightPanelInternal().showLoading(true);
    this.getRightPanelInternal().finish('In Progress', saveForLater);
};

unisubs.editmetadata.Dialog.prototype.onWorkSaved = function(closeAfterSave){
    this.saved_ = true;
    unisubs.widget.ResumeEditingRecord.clear();
    if (this.finishFailDialog_) {
        this.finishFailDialog_.setVisible(false);
        this.finishFailDialog_ = null;
    }
    if (closeAfterSave) {
        this.setVisible(false);
    }
};
