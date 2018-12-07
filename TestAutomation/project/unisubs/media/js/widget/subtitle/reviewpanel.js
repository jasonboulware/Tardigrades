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

goog.provide('unisubs.subtitle.ReviewPanel');

/**
* @constructor
* @extends unisubs.subtitle.SyncPanel
*/
unisubs.subtitle.ReviewPanel = function(subtitles, videoPlayer, serverModel, captionManager, reviewOrApprovalType, dialog) {
    unisubs.subtitle.SyncPanel.call(this, subtitles, videoPlayer,
                                     serverModel, captionManager);
    this.reviewOrApprovalType_ = reviewOrApprovalType;
    this.numSteps_ = 4;
    this.currentStep_ = 3;
    this.nextButtonText_ = "Submit your work";
    this.dialog_ = dialog;
};

goog.inherits(unisubs.subtitle.ReviewPanel, unisubs.subtitle.SyncPanel);

/**
 * @override
 */
unisubs.subtitle.ReviewPanel.prototype.createRightPanelInternal = function() {
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    var keySpecs = [];
    var internalComponents = unisubs.RightPanel.createInternalContentsReviewOrApproval(
        $d, this.reviewOrApprovalType_, this.numSteps_, this.currentStep_, false);
    if (! internalComponents){
        keySpecs = this.makeKeySpecsInternal();
        internalComponents = {
            'helpContents': new unisubs.RightPanel.HelpContents(
                "Check your work", [],
                this.numSteps_, this.currentStep_)
        };

        internalComponents['helpContents'].html =
        "<p>Watch the video one more time and correct any mistakes in text or timing. Tips for making high quality subtitles:</p>" +
        "<ul>" +
        "<li>Include text that appears in the video (signs, etc.)</li>" +
        "<li>Include important sounds in [brackets]</li>" +
        "<li>It's best to split subtitles at the end of a sentence or a long phrase.</li>" +
        "</ul>";

     }else{
        this.bodyInput_ = internalComponents['bodyInput'];
    }
    return new unisubs.subtitle.ReviewRightPanel(
        this.dialog_, this.serverModel_, internalComponents['helpContents'],
        internalComponents['extraHelp'], keySpecs , false, "Done?",
        this.nextButtonText_,  this.reviewOrApprovalType_ , this.bodyInput_);
};
