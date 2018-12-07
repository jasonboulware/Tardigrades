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

goog.provide('unisubs.editmetadata.Panel');

/**
 * @constructor
 * @param {unisubs.subtitle.EditableCaptionSet} subtitles The subtitles
 *     for the video, so far.
 * @param {unisubs.player.AbstractVideoPlayer} videoPlayer
 * @param {unisubs.CaptionManager} Caption manager, already containing subtitles
 *     with start_time set.
 */
unisubs.editmetadata.Panel = function(subtitles, videoPlayer, serverModel, captionManager, originalSubtitles, inSubtitlingDialog, reviewOrApprovalType, dialog) {
    goog.ui.Component.call(this);
    /**
     * @type {unisubs.subtitle.EditableCaptionSet}
     */
    this.subtitles_ = subtitles;
    this.dialog_ = dialog;

    this.videoPlayer_ = videoPlayer;
    /**
     * @protected
     */
    this.serverModel_ = serverModel;
    this.captionManager_ = captionManager;
    this.originalSubtitles_ = originalSubtitles;
    // when in the translate dialog, there are only 2 steps, for the subtitling, there are 4
    if (!reviewOrApprovalType && inSubtitlingDialog){
        this.currentStep_ = 2;
        this.numSteps_ = 4;
        this.nextButtonText_ = "Next Step: Check your work";
    }else{
        
        this.numSteps_ = 2;
        this.currentStep_ = 1;
        this.nextButtonText_ = "Submit final translation";
    }
    this.inSubtitlingDialog_  = inSubtitlingDialog;
    this.reviewOrApprovalType_ = reviewOrApprovalType;
};

goog.inherits(unisubs.editmetadata.Panel, goog.ui.Component);

unisubs.editmetadata.Panel.prototype.createDom = function() {
    unisubs.editmetadata.Panel.superClass_.createDom.call(this);
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());

    var $t = goog.bind(this.getDomHelper().createTextNode, this.getDomHelper());
    var el = this.getElement().appendChild(this.contentElem_ = $d('div'));
    // for original languages we won't have original subtitles
    var source;
    var originalTitle = originalDescription = "";
    var originalMetadata = {};
    if (!this.inSubtitlingDialog_){
        // we only show the original if this is a translation
        source = this.originalSubtitles_ ? this.originalSubtitles_ : this.subtitles_;
        originalTitle = source.TITLE ? source.TITLE : " no title ";
        originalDescription = source.DESCRIPTION? source.DESCRIPTION : " no description" ;
        originalMetadata = source.METADATA;

    }
    var title = this.subtitles_.title ? this.subtitles_.title : "";
    var description = this.subtitles_.description ? this.subtitles_.description : "";

    this.titleTranslationWidget_ = 
        new unisubs.translate.TitleTranslationWidget(
            originalTitle, this.subtitles_);
    this.descriptionTranslationWidget_ = 
        new unisubs.translate.DescriptionTranslationWidget(
            originalDescription, this.subtitles_);

    this.setElementInternal(this.getDomHelper().createDom('ul', "unisubs-titlesList"));
    this.addChild(this.titleTranslationWidget_, true);
    this.addChild(this.descriptionTranslationWidget_, true);
    this.descriptionTranslationWidget_.setTranslation(description);
    this.titleTranslationWidget_.setTranslation(title);

    for(name in this.subtitles_.metadata) {
        if(originalMetadata[name]) {
            var originalValue = originalMetadata[name];
        } else {
            var originalValue = '';
        }
        var widget  = new unisubs.translate.MetadataTranslationWidget(
                originalValue, this.subtitles_, name);
        this.addChild(widget, true);
        if(this.subtitles_.metadata && this.subtitles_.metadata[name]) {
            widget.setTranslation(this.subtitles_.metadata[name]);
        }
    }

    if (!this.inSubtitlingDialog_){
        var videoPlayerType = this.dialog_.getVideoPlayerInternal().videoPlayerType_;

        if (this.dialog_.reviewOrApprovalType_) {
            if (this.dialog_.translationPanel_) {
                this.baseLanguageCaptionSet_ = this.dialog_.translationPanel_.translationList_.captionSet_;
            }
        } else {
            this.baseLanguageCaptionSet_ = new unisubs.subtitle.EditableCaptionSet(
                this.dialog_.translationPanel_.translationList_.originalWrapper);
        }

        if (this.dialog_.translationPanel_) {
            this.captionManager_ =
                new unisubs.CaptionManager(
                    this.dialog_.getVideoPlayerInternal(), this.baseLanguageCaptionSet_);
        }
    }
};
unisubs.editmetadata.Panel.prototype.getRightPanel = function() {
   if (!this.rightPanel_) {
        this.rightPanel_ = this.createRightPanel_();
        //this.listenToRightPanel_();
    }
    return this.rightPanel_;

};
unisubs.editmetadata.Panel.prototype.disposeInternal = function() {
    unisubs.editmetadata.Panel.superClass_.disposeInternal.call(this);
    if (this.rightPanel_) {
        this.rightPanel_.dispose();
    }
};
unisubs.editmetadata.Panel.prototype.suspendKeyEvents = function(suspended) {
    this.keyEventsSuspended_ = suspended;
};
unisubs.editmetadata.Panel.prototype.createRightPanel_ = function(numSteps) {
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    var reviewOrApproval = true;
    var internalComponents = unisubs.RightPanel.createInternalContentsReviewOrApproval(
        $d, this.reviewOrApprovalType_, this.numSteps_, this.currentStep_, !Boolean(this.originalSubtitles_));
    if (! internalComponents){
        reviewOrApproval = false;
        var title = "Edit Title & Description";
        var desc = "Please take a moment to update the " + this.subtitles_.languageName + " title and description for these subtitles.";
        var helpContents = new unisubs.RightPanel.HelpContents(
            title, [$d('p', {}, desc)],
            this.numSteps_, this.currentStep_);
        internalComponents = {
        'helpContents' : helpContents,
        'extraHelp' : []
        };

    } else {
        this.bodyInput_ = internalComponents['bodyInput'];
    }
    

    return new unisubs.editmetadata.RightPanel(
        this.dialog_, this.serverModel_, internalComponents['helpContents'], 
        internalComponents['extraHelp'], [], false, "Done?", 
        this.nextButtonText_,  this.reviewOrApprovalType_, this.bodyInput_, this.inSubtitlingDialog_);


};
unisubs.editmetadata.Panel.prototype.getNotesContent_ = function(){
    if (this.bodyInput_){
        return  this.bodyInput_.value;
    }
    return null;
};
unisubs.editmetadata.Panel.prototype.setNotesContent_ = function(newContent){
    if (this.bodyInput_){
        this.bodyInput_.value = newContent;
        return true;
    }
    return null;
};
