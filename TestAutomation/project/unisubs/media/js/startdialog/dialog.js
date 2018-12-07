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

goog.provide('unisubs.startdialog.Dialog');

/**
 * @constructor
 * @param {string} videoID
 * @param {?unisubs.widget.SubtitleState} initialLanguageState The state
 * for the initial lang to be displayed.
 * @param {function(?string, string, ?number, ?number, function())}
 * callback When OK button is
 *     clicked, this will be called with: arg0: original language. This is
 *     non-null if and only if the user is presented with the original language
 *     dropdown in the dialog. arg1: to language: the code for the language
 *     to which we are translating. arg2: to language subtitle id, if they selected
 * an existing subtitlelanguage. arg3: from subtitle language id: the id for the
 * SubtitleLanguage to translate from. This will be null iff the user intends to make
 *     forked/original. arg4: function to close the dialog.
 */
unisubs.startdialog.Dialog = function(videoID, initialLanguageState, callback) {
    goog.ui.Dialog.call(this, 'unisubs-modal-lang', true);
    this.setButtonSet(null);
    this.setDisposeOnHide(true);
    this.videoID_ = videoID;
    this.fetchCompleted_ = false;
    this.model_ = null;
    this.initialLanguageState_ = initialLanguageState;
    this.callback_ = callback;
    this.startDialogJson_ = null;
    this.subtitleAllowed_ = true;
    this.translateAllowed_ = true;
};
goog.inherits(unisubs.startdialog.Dialog, goog.ui.Dialog);
unisubs.startdialog.Dialog.FORK_VALUE = 'forkk';

unisubs.startdialog.Dialog.prototype.createDom = function() {
    unisubs.startdialog.Dialog.superClass_.createDom.call(this);
    var $d = goog.bind(this.getDomHelper().createDom,
                       this.getDomHelper());
    var el = this.getElement();
    el.appendChild(
        $d('h3', null, 'Create subtitles'));
    this.contentDiv_ = $d('div', null, '');
    this.contentDiv_.innerHTML = "<p>Loading&hellip;</p>";
    el.appendChild(this.contentDiv_);
};
unisubs.startdialog.Dialog.prototype.enterDocument = function() {
    unisubs.startdialog.Dialog.superClass_.enterDocument.call(this);
    this.connectEvents_();
};
unisubs.startdialog.Dialog.prototype.setVisible = function(visible) {
    unisubs.startdialog.Dialog.superClass_.setVisible.call(this, visible);
    if (visible)
        unisubs.Rpc.call(
            'fetch_start_dialog_contents',
            { 'video_id': this.videoID_ },
            goog.bind(this.responseReceived_, this));
};

unisubs.startdialog.Dialog.prototype.makeDropdown_ = function($d, contents, opt_className) {
    var options = [];
    var attrs, lang, name, disabled;

    for (var i = 0; i < contents.length; i++) {
        lang = contents[i][0];
        name = contents[i][1];
        disabled = contents[i][3];

        attrs = { 'value': lang };
        if (disabled) {
            attrs['disabled'] = 'disabled';
        }

        options.push($d('option', attrs, name));
    }

    return $d('select', (opt_className || null), options);
};

unisubs.startdialog.Dialog.prototype.buildStartDialogContents_ = function() {
    this.fetchCompleted_ = true;
    this.model_ = new unisubs.startdialog.Model(this.startDialogJson_,
                                                this.initialLanguageState_);

    goog.dom.removeChildren(this.contentDiv_);
    var $d = goog.bind(this.getDomHelper().createDom,
                       this.getDomHelper());

    this.addOriginalLanguageSection_($d);
    this.addToLanguageSection_($d);
    this.addFromLanguageSection_($d);
    this.setFromContents_();
    this.warningElem_ = $d('p', 'warning');
    goog.dom.append(this.contentDiv_, this.warningElem_);
    goog.style.showElement(this.warningElem_, false);

    this.okButton_ =
        $d('a',
           {'href':'#',
            'className': "unisubs-green-button unisubs-big"},
           'Continue');
    goog.dom.append(this.contentDiv_, this.okButton_);
    var clearDiv = $d('div');
    unisubs.style.setProperty(clearDiv, 'clear', 'both');
    clearDiv.innerHTML = "&nbsp;";

    this.contentDiv_.appendChild(clearDiv);
    this.reposition();
    this.connectEvents_();
    this.maybeShowWarning_();
};
unisubs.startdialog.Dialog.prototype.buildPermissionDeniedMessage_ = function() {
    if (window.VIDEO_TEAM_NAME) {
        if (window.VIDEO_TEAM_NAME === 'Private') {
            this.contentDiv_.innerHTML = (
                "<p>Subtitles for this video are privately moderated.</p>");
        } else {
            this.contentDiv_.innerHTML = (
                "<p>Subtitles for this video are moderated by the " + window.VIDEO_TEAM_NAME + " team.</p>" +
                "<p>Learn more on the <a href=" + window.VIDEO_TEAM_URL + ">team's home page</a>.</p>" );
        }
    } else {
        this.contentDiv_.innerHTML = (
            "<p>These subtitles are moderated by a volunteer team.</p>" +
            "<p>View the video on <a href=" + unisubs.getVideoHomepageURL(this.videoID_) + ">Amara's website</a> to learn more:</p>");
    }
};
unisubs.startdialog.Dialog.prototype.buildModeratedMessage_ = function() {
    this.contentDiv_.innerHTML = (
        "<p>Subtitles for this video are moderated.</p>" +
        "<p>Please visit the " +
        "<a href='" + unisubs.getVideoHomepageURL(this.videoID_) + "'>video page</a> " +
        "to contribute.</p>" );
};
unisubs.startdialog.Dialog.prototype.moderatedResponseReceived_ = function(jsonResult) {
    this.subtitleAllowed_ = jsonResult['can_subtitle'];
    this.translateAllowed_ = jsonResult['can_translate'];

    if (!this.subtitleAllowed_) {
        // We do a bit of redundant work here to prevent accidentally showing
        // a start dialog when:
        //
        // * A user can translate, but not subtitle.
        // * This video cannot be translated (yet).
        var m = new unisubs.startdialog.Model(this.startDialogJson_, this.initialLanguageState_);
        var enabledFromLanguages = goog.array.filter(m.fromLanguages(), function(vl) {
            return !vl.DISABLED_FROM;
        });
        var subtitleOnly = enabledFromLanguages.length === 0;

        if (subtitleOnly) {
            this.buildPermissionDeniedMessage_();
        } else {
            this.buildStartDialogContents_();
        }
    } else if (this.subtitleAllowed_ || this.translateAllowed_) {
        this.buildStartDialogContents_();
    } else {
        this.buildPermissionDeniedMessage_();
    }
};
unisubs.startdialog.Dialog.prototype.responseReceived_ = function(jsonResult) {
    var isModerated = jsonResult['is_moderated'];
    this.startDialogJson_ = jsonResult;

    if (isModerated) {
        if (unisubs.isEmbeddedInDifferentDomain()) {
            this.buildModeratedMessage_();
        } else {
            unisubs.Rpc.call(
                'can_user_edit_video',
                { 'video_id': this.videoID_ },
                goog.bind(this.moderatedResponseReceived_, this));
        }
    } else {
        this.buildStartDialogContents_();
    }
};

unisubs.startdialog.Dialog.prototype.setFromContents_ = function() {
    var fromLanguages = this.model_.fromLanguages();

    var enabledFromLanguages = goog.array.filter(fromLanguages, function(vl) {
        return !vl.DISABLED_FROM;
    });

    goog.style.showElement(
        this.fromLanguageSection_, enabledFromLanguages.length > 0);

    var targetLanguageCode = this.toLanguageDropdown_.value;
    var videoLanguages = this.model_.videoLanguages_.videoLanguages_;
    var targetLanguage;

    for (var l in videoLanguages) {
        var lang = videoLanguages[l];
        // account for language codes having the PK attached if they are
        // incomplete
        if (lang.LANGUAGE == targetLanguageCode || lang.LANGUAGE+lang.PK == targetLanguageCode) {
            targetLanguage = lang;
            break;
        }
    }
    if (targetLanguage && !targetLanguage.IS_COMPLETE) {
        enabledFromLanguages = goog.array.filter(fromLanguages, function(l) {
            return targetLanguage.TRANSLATED_FROM == l.LANGUAGE;
        });
    }

    if (enabledFromLanguages.length > 0) {
        var fromLanguageContents = [];

        if (this.translateAllowed_) {
            fromLanguageContents = goog.array.map(
                //this.model_.fromLanguages(),
                enabledFromLanguages,
                function(l) {
                    return [l.LANGUAGE + '', l.toString(), null, l.DISABLED_FROM];
                });
        }

        var $d = goog.bind(this.getDomHelper().createDom,
                           this.getDomHelper());
        this.fromLanguageDropdown_ = this.makeDropdown_(
            $d, fromLanguageContents, "from-language");
        goog.dom.removeChildren(this.fromContainer_);
        this.fromContainer_.appendChild(this.fromLanguageDropdown_);
        this.getHandler().listen(
            this.fromLanguageDropdown_,
            goog.events.EventType.CHANGE,
            this.fromLanguageChanged_);
    }
    else {
        this.fromLanguageDropdown_ = null;
    }
};
unisubs.startdialog.Dialog.prototype.addToLanguageSection_ = function($d) {
    var blocked_languages = this.model_.blockedLanguages_ || [];

    var toLanguageContents = goog.array.map(
        this.model_.toLanguages(),
        function(l) {
            var disabled = false;
            if (l.VIDEO_LANGUAGE) {
                disabled = l.VIDEO_LANGUAGE.DISABLED_TO;
            } else if (goog.array.contains(blocked_languages, l.LANGUAGE)) {
                disabled = true;
            }

            return [l.KEY, l.toString(), l.LANGUAGE, disabled];
        });

    this.toLanguageDropdown_ = this.makeDropdown_(
        $d, toLanguageContents, "to-language");
    this.toLanguageDropdown_.value = this.model_.getSelectedLanguage().KEY;

    this.contentDiv_.appendChild(
        $d('p', null,
           $d('span', null, 'Subtitle into: '),
           this.toLanguageDropdown_));

    var renderedToLanguages = goog.dom.getElementByClass('to-language');
    var selected = goog.dom.getChildren(renderedToLanguages)[renderedToLanguages.selectedIndex];
    while (selected && selected.disabled) {
        var next = goog.dom.getNextElementSibling(selected);
        // let's not break if there's just a language. please.
        // thanks.
        if(next){
            goog.dom.forms.setValue(renderedToLanguages, next.value);
            selected = goog.dom.getChildren(renderedToLanguages)[renderedToLanguages.selectedIndex];
        }
    }

    // If this is a first-time translate task, set the to-language to the
    // language that we're translating into.
    if (window['TASK_TRANSLATE_TO_LANGUAGE']) {

        var toLanguageOptions = goog.dom.getChildren(renderedToLanguages);

        for (var tl = 0; tl < toLanguageOptions.length; tl++) {

            // Remove integers from the language code to get the real language code.
            // See: http://bit.ly/R4jdL3
            var toLanguageCode = toLanguageOptions[tl].value;
            var toLanguageCodeForReal = toLanguageCode.replace(/\d+/g, '');

            // If this for-real language code matches this task's language code,
            // let's preselect that option.
            if (window['TASK_TRANSLATE_TO_LANGUAGE'] == toLanguageCodeForReal) {
                goog.dom.forms.setValue(renderedToLanguages, toLanguageOptions[tl].value);
                break;
            }
        }
    }
};
unisubs.startdialog.Dialog.prototype.addFromLanguageSection_ = function($d) {
    this.fromContainer_ = $d('span');
    this.fromLanguageSection_ =
        $d('div', null,
           $d('p', null,
              $d('span', null, 'Translate from: '),
              this.fromContainer_));
    this.contentDiv_.appendChild(this.fromLanguageSection_);
};
unisubs.startdialog.Dialog.prototype.addOriginalLanguageSection_ = function($d) {
    if (this.model_.originalLanguageShown()) {

        var languages = unisubs.languages;
        languages.unshift(['', '--Select language--']);

        this.originalLangDropdown_ = this.makeDropdown_(
            $d, languages, "original-language");
        this.originalLangDropdown_.value = '';
        this.model_.selectOriginalLanguage('');
        this.contentDiv_.appendChild(
            $d('p', null,
               $d('span', null, 'This video is in: '),
               this.originalLangDropdown_));
        this.contentDiv_.appendChild(
        $d('p', "notice", "Please double check the primary spoken language. This step cannot be undone."));
    }
    else {
        this.contentDiv_.appendChild(
            $d('p', null, "This video is in " +
               unisubs.languageNameForCode(
                   this.model_.getOriginalLanguage())));
    }
};
unisubs.startdialog.Dialog.prototype.connectEvents_ = function() {
    if (!this.isInDocument() || !this.fetchCompleted_)
        return;
    this.getHandler().
        listen(
            this.toLanguageDropdown_,
            goog.events.EventType.CHANGE,
            this.toLanguageChanged_).
        listen(
            this.okButton_,
            goog.events.EventType.CLICK,
            this.okClicked_);
    if (this.originalLangDropdown_)
        this.getHandler().listen(
            this.originalLangDropdown_,
            goog.events.EventType.CHANGE,
            this.originalLangChanged_);
};
unisubs.startdialog.Dialog.prototype.originalLangChanged_ = function(e) {
    this.model_.selectOriginalLanguage(this.originalLangDropdown_.value);
    this.setFromContents_();
};

unisubs.startdialog.Dialog.prototype.toLanguageChanged_ = function(e) {
    this.model_.selectLanguage(this.toLanguageDropdown_.value);
    this.setFromContents_();
    this.maybeShowWarning_();
};
unisubs.startdialog.Dialog.prototype.fromLanguageChanged_ = function(e) {
    this.maybeShowWarning_();
};
unisubs.startdialog.Dialog.prototype.maybeShowWarning_ = function() {
    var warning = null;
    // We used to have code that showed a warning under certain circumstances,
    // but now we don't need it.  However, this method seems good to keep
    // around if we need it in the future.
    this.showWarning_(warning);
};
unisubs.startdialog.Dialog.prototype.showWarning_ = function(warning) {
    goog.dom.setTextContent(this.warningElem_, warning || '');
    goog.style.showElement(this.warningElem_, !!warning);
};
unisubs.startdialog.Dialog.prototype.okClicked_ = function(e) {
    e.preventDefault();
    if (this.okHasBeenClicked_)
        return;
    this.okHasBeenClicked_ = true;
    var fromLanguageCode = null;
    if (this.fromLanguageDropdown_ &&
        this.fromLanguageDropdown_.value !=
            unisubs.startdialog.Dialog.FORK_VALUE)
        fromLanguageCode = this.fromLanguageDropdown_.value;
    var toLanguage = this.model_.toLanguageForKey(
        this.toLanguageDropdown_.value);
    var that = this;

    if (this.model_.originalLanguageShown()) {
        if (this.originalLangDropdown_.value === '') {
            this.okHasBeenClicked_ = false;
            alert('You must select a language first.');
            return false;
        };
    };

    this.callback_(
        this.model_.originalLanguageShown() ?
            this.originalLangDropdown_.value : null,
        toLanguage.LANGUAGE,
        toLanguage.VIDEO_LANGUAGE ? toLanguage.VIDEO_LANGUAGE.PK : null,
        fromLanguageCode,
        function() { that.setVisible(false); });
    goog.dom.setTextContent(this.okButton_, "Loading...");
    goog.dom.classes.add(this.okButton_, "unisubs-button-disabled");
};
