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

goog.provide('unisubs.RightPanel');

/**
 * @constructor
 * @extends goog.ui.Component
 *
 * @param {unisubs.ServerModel} serverModel
 * @param {unisubs.RightPanel.HelpContents} helpContents
 * @param {Array.<string>} extraHelp paragraphs to display in extra bubble.
 *     0-length array will not display bubble.
 * @param {Array.<unisubs.RightPanel.KeySpec>} legendKeySpecs
 * @param {boolean} showRestart
 * @param {string} doneStrongText
 * @param {string} doneText
 */
unisubs.RightPanel = function(serverModel, helpContents, extraHelp, legendKeySpecs, showRestart, doneStrongText, doneText) {
    goog.ui.Component.call(this);
    this.serverModel_ = serverModel;
    this.helpContents_ = helpContents;
    this.extraHelp_ = extraHelp;
    this.legendKeySpecs_ = legendKeySpecs;
    this.showRestart_ = showRestart;
    this.doneStrongText_ = doneStrongText;
    this.doneText_ = doneText;
    this.loginDiv_ = null;
    this.doneAnchor_ = null;

    /**
     * Whether to show the "Save and Exit" link in the panel. Should be overridden by
     * sub classes as needed.
     *
     * @protected
     * @type {boolean}
     */
    this.showSaveExit = true;

    /**
     * Whether to show the "Done? ... >" button. Should be overridden by sub
     * classes as needed.
     *
     * @protected
     * @type {boolean}
     */
    this.showDoneButton = true;

    /**
     * Non-null iff the mouse has just been pressed on one of the legend keys
     * and not released or moved away from the legend key yet.
     * @type {?string}
     */
    this.mouseDownKeyCode_ = null;
    this.saveAndOpenInNewEditor  = null;
};

goog.inherits(unisubs.RightPanel, goog.ui.Component);

unisubs.RightPanel.EventType = {
    LEGENDKEY : 'legend',
    RESTART : 'restart',
    DONE : 'done',
    BACK : 'back',
    GOTOSTEP : 'gotostep',
    SAVEANDEXIT: 'saveandexit',
    SAVEANDOPENINNEWEDITOR: 'saveandopeninneweditor'
};
unisubs.RightPanel.prototype.createDom = function() {
    unisubs.RightPanel.superClass_.createDom.call(this);

    // TODO: you might really want to do this in enterDocument instead
    // of createDom, given that we're adding event listeners.

    var el = this.getElement();
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());

    this.appendHelpContentsInternal($d, el);

    this.appendExtraHelp_($d, el);

    this.appendLegendContents_($d, el);

    this.appendMiddleContentsInternal($d, el);

    this.appendStepsContents_($d, el);
};
unisubs.RightPanel.prototype.showLoading = function(show) {
    unisubs.style.showElement(this.loadingGif_, show);
};
unisubs.RightPanel.prototype.showBackLink = function(linkText) {
    unisubs.style.showElement(this.backAnchor_, true);
    goog.dom.setTextContent(this.backAnchor_, linkText);
};
unisubs.RightPanel.prototype.appendHelpContentsInternal = function($d, el) {
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
    else
        goog.array.forEach(this.helpContents_.paragraphs, function(p) {
            el.appendChild($d('p', null, p));
        });
};
unisubs.RightPanel.prototype.appendExtraHelp_ = function($d, el) {
    if (this.extraHelp_ && this.extraHelp_.length > 0) {
        this.appendExtraHelpInternal($d, el);
    }
};
unisubs.RightPanel.prototype.appendExtraHelpInternal = function($d, el) {
    var extraDiv = $d('div', 'unisubs-extra');
    for (var i = 0; i < this.extraHelp_.length; i++)
        extraDiv.appendChild($d('p', null, this.extraHelp_[i]));
    extraDiv.appendChild($d('span', 'unisubs-spanarrow'));
    el.appendChild(extraDiv);
};
unisubs.RightPanel.prototype.appendLegendContents_ = function($d, el) {
    var legendDiv = $d('div', 'unisubs-legend');
    el.appendChild(legendDiv);
    this.appendLegendContentsInternal($d, legendDiv);
    this.appendLegendClearInternal($d, legendDiv);
};
unisubs.RightPanel.prototype.findSpec_ = function(keyCode, modifiers) {
    return goog.array.find(this.legendKeySpecs_,
                           function(s) { return s.keyCode == keyCode && s.modifiers == modifiers; });
};
unisubs.RightPanel.prototype.setKeyDown = function(keyCode, modifiers, active) {
    this.enableButtonClassInternal(keyCode, modifiers, '-down', active);
};

/**
 * @protected
 * @param {string=} opt_text text for the button, or null to revert to original text.
 */
unisubs.RightPanel.prototype.setButtonTextInternal = function(keyCode, modifiers, opt_text) {
    var spec = this.findSpec_(keyCode, modifiers);
    if (spec)
        goog.dom.setTextContent(
            spec.textSpan, opt_text ? opt_text : spec.legendText);
};

unisubs.RightPanel.prototype.enableButtonClassInternal = function (keyCode, modifiers, classSuffix, enable) {
    var spec = this.findSpec_(keyCode, modifiers);
    if (spec)
        goog.dom.classes.enable(
            spec.div, spec.divClass + classSuffix, enable);
};
unisubs.RightPanel.prototype.appendLegendContentsInternal = function($d, legendDiv) {
    var et = goog.events.EventType;
    for (var i = 0; i < this.legendKeySpecs_.length; i++) {
        var spec = this.legendKeySpecs_[i];
        var textSpan = $d('span', null, spec.legendText);
        var keyTextSpan = $d('span', spec.spanClass);
        var keyLines = spec.keyText.split("\n");
        for (var j = 0; j < keyLines.length; j++) {
            if (j > 0)
                goog.dom.appendChild(keyTextSpan, $d('br'));
            goog.dom.appendChild(keyTextSpan, goog.dom.createTextNode(keyLines[j]));
        }
        var key = $d('div', spec.divClass, keyTextSpan, textSpan);
        legendDiv.appendChild(key);
        spec.div = key;
        spec.textSpan = textSpan;
        this.getHandler().listen(
            key, et.CLICK, goog.bind(this.legendKeyClicked_,
                                     this, spec.keyCode, spec.modifiers));
        this.getHandler().listen(
            key, et.MOUSEDOWN, goog.bind(this.legendKeyMousedown_,
                                         this, spec.keyCode, spec.modifiers));
        var mouseupFn = goog.bind(this.legendKeyMouseup_, this, spec.keyCode, spec.modifiers);
        this.getHandler().listen(key, et.MOUSEUP, mouseupFn);
        this.getHandler().listen(key, et.MOUSEOUT, mouseupFn);
    }
};
unisubs.RightPanel.prototype.appendLegendClearInternal = function($d, legendDiv) {
    legendDiv.appendChild($d('div', 'unisubs-clear'));
};
unisubs.RightPanel.prototype.appendMiddleContentsInternal = function($d, el) {
    // dear subclasses, override me if you want. love, rightpanel.
};
unisubs.RightPanel.prototype.appendCustomButtonsInternal = function($d, el) {
    // dear subclasses, override me if you want. love, rightpanel.
};
unisubs.RightPanel.prototype.createBackAnchor_ = function($d, el) {
    var anchor = $d('a', {'className':'unisubs-backTo unisubs-greybutton', 'href':'#'},
           'Return to Typing');
    this.getHandler().listen(anchor, 'click', this.backClickedInternal);
    unisubs.style.showElement(anchor, false);
    return anchor;

};
unisubs.RightPanel.prototype.createDoneAnchor_ = function($d) {
    return $d('a', {'className':'unisubs-done', 'href':'#'},
                          $d('span', null,
                             this.loadingGif_,
                             $d('strong', null, this.doneStrongText_),
                             goog.dom.createTextNode(" "),
                             goog.dom.createTextNode(this.doneText_)));
};
unisubs.RightPanel.prototype.appendStepsContents_ = function($d, el) {
    this.loginDiv_ = $d('div');
    this.loadingGif_ = $d('img',
                          {'src': unisubs.imageAssetURL('spinner.gif') });
    this.showLoading(false);
    this.doneAnchor_ = this.createDoneAnchor_($d);
    var stepsDiv = $d('div', 'unisubs-steps', this.loginDiv_);



    this.backAnchor_ = this.createBackAnchor_($d, el);
    unisubs.style.showElement(this.backAnchor_, false);
    stepsDiv.appendChild(this.backAnchor_);

    if (this.showRestart_) {
        var restartAnchor =
            $d('a', {'className': 'unisubs-restart','href':'#'},
               'Restart this Step');
        this.getHandler().listen(
            restartAnchor, 'click', this.restartClicked_);
        stepsDiv.appendChild(restartAnchor);
    }

    this.downloadLink_ = $d(
        'a', {'href':'#', 'className':'unisubs-download-subs'},
        'Download subtitles');
    goog.style.showElement(this.downloadLink_, false);
    goog.dom.append(stepsDiv, this.downloadLink_);
    this.getHandler().listen(
        this.downloadLink_, 'click', this.downloadClicked_);

    this.appendCustomButtonsInternal($d, el);

    if (this.showDoneButton) {
        goog.dom.append(stepsDiv, this.doneAnchor_);
        this.getHandler().listen(this.doneAnchor_, 'click', this.doneClicked_);
    }

    if (this.showSaveExit) {
        var saveAndExitAnchor = $d(
            'div', 'unisubs-saveandexit',
            $d('span', null, 'Need to stop and come back later? '),
            $d('a', {'href': '#'},
            $d('span', null, 'Save and Exit')));
        goog.dom.append(stepsDiv, saveAndExitAnchor);
        this.getHandler().listen(
            saveAndExitAnchor, goog.events.EventType.CLICK,
            this.saveAndExitClicked_);
    }

    this.createSaveAndOpenInNewEditor(stepsDiv);

    goog.dom.append(el, stepsDiv);
    this.updateLoginState();
};
unisubs.RightPanel.prototype.createSaveAndOpenInNewEditor = function(stepsDiv) {
   // If this subtitle version was created from a base language that was forked from a
    // translation, we need to display a link to get into the new editor so that the user
    // can compare these captions to captions of other languages.
    if (!this.saveAndOpenInNewEditor) {

        var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
        var videoType = this.parent_.parent_.videoPlayer_.videoPlayerType_;
        this.saveAndOpenInNewEditor = $d(
            'div', 'unisubs-saveandopeninneweditor',
            $d('a', {'href': '#'},
            $d('span', null, 'Save and open in new editor')));

        goog.dom.append(stepsDiv, this.saveAndOpenInNewEditor);
        this.getHandler().listen(
            this.saveAndOpenInNewEditor, goog.events.EventType.CLICK,
            this.saveAndOpenInNewEditorClicked_);
    }
}
unisubs.RightPanel.prototype.legendKeyClicked_ = function(keyCode, modifiers, event) {
    this.dispatchEvent(
        new unisubs.RightPanel.LegendKeyEvent(keyCode, modifiers, event.type));
};
unisubs.RightPanel.prototype.legendKeyMousedown_ = function(keyCode, modifiers, event) {
    this.dispatchEvent(
        new unisubs.RightPanel.LegendKeyEvent(keyCode, modifiers, event.type));
    this.mouseDownKeyCode_ = keyCode;
};
unisubs.RightPanel.prototype.legendKeyMouseup_ = function(keyCode, modifiers, event) {
    if (this.mouseDownKeyCode_) {
        this.mouseDownKeyCode_ = null;
        this.dispatchEvent(
            new unisubs.RightPanel.LegendKeyEvent(keyCode, modifiers, 'mouseup'));
    }
};
unisubs.RightPanel.prototype.backClickedInternal = function(event) {
    event.preventDefault();
    this.dispatchEvent(unisubs.RightPanel.EventType.BACK);
};
unisubs.RightPanel.prototype.restartClicked_ = function(event) {
    event.preventDefault();
    this.dispatchEvent(unisubs.RightPanel.EventType.RESTART);
};
unisubs.RightPanel.prototype.doneClicked_ = function(event) {
    event.preventDefault();
    this.dispatchEvent(unisubs.RightPanel.EventType.DONE);
};
unisubs.RightPanel.prototype.saveAndExitClicked_ = function(e) {
    e.preventDefault();
    this.dispatchEvent(unisubs.RightPanel.EventType.SAVEANDEXIT);
};
unisubs.RightPanel.prototype.saveAndOpenInNewEditorClicked_ = function(e) {
    e.preventDefault();
    this.dispatchEvent(unisubs.RightPanel.EventType.SAVEANDOPENINNEWEDITOR);
};
unisubs.RightPanel.prototype.getDoneAnchor = function() {
    return this.doneAnchor_;
};
unisubs.RightPanel.prototype.updateLoginState = function() {
    goog.dom.removeChildren(this.loginDiv_);
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    if (this.serverModel_ && !this.serverModel_.currentUsername()) {
        var loginLink = $d('a', {'href':'#'}, "LOGIN");
        this.loginDiv_.appendChild(
            $d('div', 'unisubs-needLogin',
               goog.dom.createTextNode(
                   'To save your subtitling work, you need to '),
               loginLink));
        this.getHandler().listen(loginLink, 'click', this.loginClicked_);
    }
};
unisubs.RightPanel.prototype.appendsNotesForReview = function(jsonSubsFn) {

};
unisubs.RightPanel.prototype.showDownloadLink = function(jsonSubsFn) {
    goog.style.showElement(this.downloadLink_, true);
    this.jsonSubsFn_ = jsonSubsFn;
};
unisubs.RightPanel.prototype.downloadClicked_ = function(e) {
    e.preventDefault();

    var lang;

    // A translation
    if (this.dialog_.subtitleState_) {
        lang = this.dialog_.subtitleState_.LANGUAGE;
    
    // A transcription
    } else {
        lang = this.dialog_.subtitles_.LANGUAGE;
    }
    unisubs.finishfaildialog.CopyDialog.showForSubs(this.jsonSubsFn_(), lang);
};
unisubs.RightPanel.prototype.loginClicked_ = function(event) {
    this.serverModel_.logIn();
    event.preventDefault();
};

/**
 * @constructor
 * Sets contents at top part of right panel.
 *
 * @param {string} header
 * @param {Array.<string>} paragraphs
 * @param {number=} opt_numSteps
 * @param {number} opt_activeStep;
 */
unisubs.RightPanel.HelpContents = function(header, paragraphs, opt_numSteps, opt_activeStep) {
    this.header = header;
    this.paragraphs = paragraphs;
    this.numSteps = opt_numSteps;
    this.activeStep = opt_activeStep;
    // set html to override paragraphs with custom html.
    this.html = null;
};

/**
* @constructor
*/
unisubs.RightPanel.KeySpec = function(divClass, spanClass, keyText, legendText, keyCode, modifiers) {
    this.divClass = divClass;
    this.spanClass = spanClass;
    this.keyText = keyText;
    this.legendText = legendText;
    this.keyCode = keyCode;
    this.modifiers = modifiers;
};

unisubs.RightPanel.KeySpec.Modifier = {
    SHIFT : 1,
    ALT: 2,
    CTRL: 4
};

/**
* @constructor
*/
unisubs.RightPanel.LegendKeyEvent = function(keyCode, modifiers, eventType) {
    this.type = unisubs.RightPanel.EventType.LEGENDKEY;
    this.keyCode = keyCode;
    this.modifiers = modifiers;
    this.keyEventType = eventType;
};

/**
* @constructor
*/
unisubs.RightPanel.GoToStepEvent = function(stepNo) {
    this.type = unisubs.RightPanel.EventType.GOTOSTEP;
    this.stepNo = stepNo;
};

/* Since all panels might use this under review we abstract them here.
* Returns a json object with the title, help contents and extraHelp needed to populate this
* panel for review
*/
unisubs.RightPanel.createInternalContentsForReview = function($d, numSteps, currentStep, isOriginal){
    // return as a json literal, else the closure compiler will mangle this
    var bodyInput = $d('textarea', {'class': 'unisubs-review-notes', 'id': 'unisubs-review-notes', 'name': 'notes'});

    var title = isOriginal? "Review subtitles": "Review this translation";

    var helpContents;
    if (isOriginal) {
        // We're reviewing subtitles.

        if (currentStep === 0) {
            // We're on the first step (review / edit / sync subtitles).

            helpContents = new unisubs.RightPanel.HelpContents(title, [
                $d('p', {}, "Play the video and review the subtitles for both accuracy and timing."),
                $d('p', {}, "To make changes, use the controls on each subtitle to add, edit, or delete lines or to change their timing. You can also use the keyboard shortcuts shown below."),
                $d('p', {}, "If you are unable to complete the review now, click the red 'x' at the top right of this panel. You can restart this task again later."),
                $d('div', {'className': 'unisubs-extra'},
                   $d('p', {}, "Enter review notes here. ",
                      "They will be sent to all previous contributors ",
                      "and posted as a ",
                      $d('em', {}, "public comment"),
                      " to the subtitles."),
                   $d('span', {'className': 'unisubs-spanarrow'})),

                $d('label', {'class': 'unisubs-review-notes-label', 'for': 'unisubs-review-notes'}, 'Notes'),
                bodyInput
            ], numSteps, currentStep);
        } else {
            // We're on the second step (review title / description).

            helpContents = new unisubs.RightPanel.HelpContents(title, [
                $d('p', {}, "Review the video title and description."),
                $d('p', {}, "Once you've finished, you can either send the subtitles back to their creator for additional work, or accept them to be published."),
                $d('div', {'className': 'unisubs-extra'},
                   $d('p', {}, "Enter review notes here. ",
                      "They will be sent to all previous contributors ",
                      "and posted as a ",
                      $d('em', {}, "public comment"),
                      " to the subtitles."),
                   $d('span', {'className': 'unisubs-spanarrow'})),

                $d('label', {'class': 'unisubs-review-notes-label', 'for': 'unisubs-review-notes'}, 'Notes'),
                bodyInput
            ], numSteps, currentStep);
        }
    } else {
        // We're reviewing a translation.

        if (currentStep === 0) {
            // We're on the first step (review translation).

            helpContents = new unisubs.RightPanel.HelpContents(title, [
                $d('p', {}, "Review the translation for accuracy and make changes to the translated text, if necessary. If you are unable to complete the review now, click the red 'x' at the top right of this panel. You can restart this task again later."),
                $d('div', {'className': 'unisubs-extra'},
                   $d('p', {}, "Enter review notes here. ",
                      "They will be sent to all previous contributors ",
                      "and posted as a ",
                      $d('em', {}, "public comment"),
                      " to the subtitles."),
                   $d('span', {'className': 'unisubs-spanarrow'})),

                $d('label', {'class': 'unisubs-review-notes-label', 'for': 'unisubs-review-notes'}, 'Notes'),
                bodyInput
            ], numSteps, currentStep);
        } else {
            // We're on the second step (review title / description).

            helpContents = new unisubs.RightPanel.HelpContents(title, [
                $d('p', {}, "Review the video title and description."),
                $d('p', {}, "Once you've finished, you can either send the subtitles back to their creator for additional work, or accept them to be published."),
                $d('div', {'className': 'unisubs-extra'},
                   $d('p', {}, "Enter review notes here. ",
                      "They will be sent to all previous contributors ",
                      "and posted as a ",
                      $d('em', {}, "public comment"),
                      " to the subtitles."),
                   $d('span', {'className': 'unisubs-spanarrow'})),

                $d('label', {'class': 'unisubs-review-notes-label', 'for': 'unisubs-review-notes'}, 'Notes'),
                bodyInput
            ], numSteps, currentStep);
        }
    }

    return  {
        'bodyInput': bodyInput,
        'helpContents' : helpContents ,
        'extraHelp' :  [
        ]
    };
};

/* Since all panels might use this under approval, we abstract them here.
* Returns a json object with the title, help contents and extraHelp needed to populate this
* panel for approval.
*/
unisubs.RightPanel.createInternalContentsForApproval = function($d, numSteps, currentStep, isOriginal){
    // return as a json literal, else the closure compiler will mangle this

    var title = isOriginal? "Approve subtitles": "Approve this translation";
    var bodyInput = $d('textarea', {'class': 'unisubs-approve-notes', 'id': 'unisubs-approve-notes', 'name': 'notes'});

    var helpContents;
    if (isOriginal) {
        // We're reviewing subtitles.
        helpContents = new unisubs.RightPanel.HelpContents(title, [
            $d('p', {}, "Play the video and review the subtitles for both accuracy and timing."),
            $d('p', {}, "To make changes, use the controls on each subtitle to add, edit, or delete lines or to change their timing. You can also use the keyboard shortcuts shown below."),
            $d('p', {}, "If you are unable to complete the review now, click the red 'x' at the top right of this panel. You can restart this task again later."),
            $d('div', {'className': 'unisubs-extra'},
               $d('p', {}, "Enter review notes here. ",
                  "They will be sent to all previous contributors ",
                  "and posted as a ",
                  $d('em', {}, "public comment"),
                  " to the subtitles."),
               $d('span', {'className': 'unisubs-spanarrow'})),

            $d('label', {'class': 'unisubs-review-notes-label', 'for': 'unisubs-review-notes'}, 'Notes'),
            bodyInput
        ], numSteps, currentStep);
    } else {
        // We're reviewing a translation.
        helpContents = new unisubs.RightPanel.HelpContents(title, [
            $d('p', {}, "Review the translation for accuracy and make changes to the translated text, if necessary. If you are unable to complete the review now, click the red 'x' at the top right of this panel. You can restart this task again later."),
            $d('div', {'className': 'unisubs-extra'},
               $d('p', {}, "Enter review notes here. ",
                  "They will be sent to all previous contributors ",
                  "and posted as a ",
                  $d('em', {}, "public comment"),
                  " to the subtitles."),
               $d('span', {'className': 'unisubs-spanarrow'})),

            $d('label', {'class': 'unisubs-review-notes-label', 'for': 'unisubs-review-notes'}, 'Notes'),
            bodyInput
        ], numSteps, currentStep);
    }

    return {
        'bodyInput': bodyInput,
        'helpContents' : helpContents,
        'extraHelp' : [
        ]
    };
};
unisubs.RightPanel.createInternalContentsReviewOrApproval = function($d, reviewOrApprovalType, numSteps, currentStep, isOriginal){
    if (reviewOrApprovalType == unisubs.Dialog.REVIEW_OR_APPROVAL.REVIEW){
        return unisubs.RightPanel.createInternalContentsForReview($d, numSteps, currentStep, isOriginal);
    }else if(reviewOrApprovalType == unisubs.Dialog.REVIEW_OR_APPROVAL.APPROVAL){
        return unisubs.RightPanel.createInternalContentsForApproval($d, numSteps, currentStep, isOriginal);
    }
    return null;
};
