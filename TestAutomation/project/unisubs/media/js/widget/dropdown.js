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

goog.provide('unisubs.widget.DropDown');

/**
 * @constructor
 * @param {unisubs.widget.DropDownContents} dropDownContents
 */
unisubs.widget.DropDown = function(videoID, videoFilename, dropDownContents, videoTab) {
    goog.ui.Component.call(this);

    this.videoID_ = videoID;
    this.videoFilename_ = videoFilename;
    this.setStats_(dropDownContents);
    this.videoTab_ = videoTab;
    /**
     * @type {?unisubs.widget.SubtitleState}
     */
    this.subtitleState_ = null;
    this.shown_ = false;
    this.languageClickHandler_ = new goog.events.EventHandler(this);
    this.showAddLanguageLink_ = false;
    this.showImproveSubtitlesLink_ = false;
};

goog.inherits(unisubs.widget.DropDown, goog.ui.Component);

unisubs.widget.DropDown.Selection = {
    ADD_LANGUAGE: "add_language",
    IMPROVE_SUBTITLES: "improve_subtitles",
    SUBTITLE_HOMEPAGE: "subtitle_homepage",
    DOWNLOAD_SUBTITLES: "download_subtitles",
    CREATE_ACCOUNT: "create_account",
    LANGUAGE_PREFERENCES: "language_preferences",
    SUBTITLES_OFF: "subtitles_off",
    LANGUAGE_SELECTED: "language_selected",
    USERNAME: "username",
    LOGOUT: "logout"
};

unisubs.widget.DropDown.prototype.hasSubtitles = function() {
    return goog.array.some(this.videoLanguages_, function(el){ return el.IS_PUBLIC });
};
unisubs.widget.DropDown.prototype.setStats_ = function(dropDownContents) {
    this.videoLanguages_ = dropDownContents.LANGUAGES;
    this.isModerated_ = dropDownContents.IS_MODERATED;
};

unisubs.widget.DropDown.prototype.isModerated = function() {
    return this.isModerated_;
};

unisubs.widget.DropDown.prototype.updateContents = function(dropDownContents) {
    this.setStats_(dropDownContents);
    this.updateSubtitleStats_();
    this.addLanguageLinkListeners_();
    this.setCurrentSubtitleState(this.subtitleState_);
};

unisubs.widget.DropDown.prototype.setCurrentSubtitleState = function(subtitleState) {
    this.clearCurrentLang_();
    this.subtitleState_ = subtitleState;
    this.setCurrentLangClassName_();
    unisubs.style.showElement(this.improveSubtitlesLink_, !!subtitleState);
    goog.dom.getFirstElementChild(this.downloadSubtitlesLink_).href =
        this.createDownloadSRTURL_();
};

unisubs.widget.DropDown.prototype.createDom = function() {
    unisubs.widget.DropDown.superClass_.createDom.call(this);
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    goog.dom.classes.add(
        this.getElement(), "cleanslate", "unisubs-dropdown");

    var languageListContainer = this.createLanguageList_($d);
    this.createActionList_($d);

    this.updateSubtitleStats_();
    this.updateActions_();

    this.getElement().appendChild(languageListContainer);
    this.getElement().appendChild(this.actions_);
};

unisubs.widget.DropDown.prototype.createLanguageList_ = function($d) {
    var container = $d('div', {'className': 'unisubs-languageList'});
    container.appendChild(this.languageList_ = $d('ul', null));

    this.subtitlesOff_ = $d('li', null, $d('a', {'href': '#'}, 'Subtitles Off'));
    this.subCountSpan_ = $d('span', 'unisubs-languageStatus');
    return container;
};

unisubs.widget.DropDown.prototype.setForStreamer = function(forStreamer) {
    this.forStreamer_ = forStreamer;
};

unisubs.widget.DropDown.prototype.updateSubtitleStats_ = function() {
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());
    this.getDomHelper().removeChildren(this.languageList_);

    goog.dom.setTextContent(this.addTranslationAnchor_, 'Add New Subtitles');

    goog.dom.setTextContent(
        this.subCountSpan_, '(' + this.subtitleCount_ + ' lines)');

    if (!this.forStreamer_) {
        // As Maggie pointed out, the "Subtitles off" link really has no
        // meaning in the streamer.
        goog.dom.append(
            this.languageList_,
            this.subtitlesOff_);
    }

    this.addVideoLanguagesLinks_($d);
};

unisubs.widget.DropDown.prototype.addVideoLanguagesLinks_ = function($d) {
    this.videoLanguagesLinks_ = [];

    for (var i = 0; i < this.videoLanguages_.length; i++) {
        var data = this.videoLanguages_[i];

        if(!data.IS_PUBLIC){
            continue
        }

        var link =
            $d('a', {'href': '#'},
               $d('span', 'unisubs-languageTitle',
                  unisubs.languageNameForCode(data.LANGUAGE)),
               $d('span', 'unisubs-languageStatus',
                  data.completionStatus()));
        var linkLi = $d('li', null, link);
        this.videoLanguagesLinks_.push(
            { link: link,
              linkLi: linkLi,
              videoLanguage: data});
        goog.dom.append(this.languageList_, linkLi);
    }
};

unisubs.widget.DropDown.prototype.createActionList_ = function($d) {
    this.actions_ = $d('div', {'className': 'unisubs-actions'});
    this.createActionLinks_($d);
    this.actions_.appendChild(this.unisubsLink_);
    this.actions_.appendChild($d('h4', null, 'THIS VIDEO'));
    this.actions_.appendChild(this.videoActions_);
    this.actions_.appendChild($d('h4', null, 'MY SETTINGS'));
    this.actions_.appendChild(this.settingsActions_);
};

unisubs.widget.DropDown.prototype.createSubtitleHomepageURL_ = function() {
    return unisubs.getSubtitleHomepageURL(this.videoID_);
};

unisubs.widget.DropDown.prototype.createDownloadSRTURL_ = function() {
    if(this.subtitleState_ === null) {
        return '#';
    }
    var filename = this.videoFilename_ + '.' + this.subtitleState_.LANGUAGE;
    var path = ("/subtitles/" + this.videoID_ + "/" +
            this.subtitleState_.LANGUAGE + "/download/" +
            encodeURIComponent(filename) + '.srt');
    var uri = new goog.Uri(unisubs.siteURL());
    uri.setPath(path);
    return uri.toString();
};

unisubs.widget.DropDown.prototype.createActionLinks_ = function($d) {
    this.videoActions_ = $d('ul', null);
    this.settingsActions_ = $d('ul', null);

    this.unisubsLink_ =
        $d('h5', 'unisubs-uniLogo', 'Amara');
    this.addTranslationAnchor_ =
        $d('a', {'href': '#'}, '');
    this.addLanguageLink_ =
        $d('li', 'unisubs-addTranslation', this.addTranslationAnchor_);
    this.improveSubtitlesLink_ =
        $d('li', 'unisubs-improveSubtitles',
           $d('a', {'href': '#'}, 'Improve These Subtitles'));
   this.subtitleHomepageLink_ =
        $d('li', 'unisubs-subtitleHomepage',
           $d('a', {'href': this.createSubtitleHomepageURL_()},
              'Subtitle Homepage'));
    this.downloadSubtitlesLink_ =
        $d('li', 'unisubs-downloadSubtitles',
           $d('a', {'href': '#'}, 'Download Subtitles'));

    this.moderatedNotice_ =
        $d('li', 'unisubs-moderated',
           $d('p', null,
                'These subtitles are moderated. Visit the ',
                $d('a', {'href': unisubs.getVideoHomepageURL(this.videoID_)},
                    'video page'),
                ' to contribute.'));

    this.createAccountLink_ =
        $d('li', 'unisubs-createAccount',
           $d('a', {'href': '#'}, 'Login or Create Account'));
    this.languagePreferencesLink_ =
        $d('li', 'unisubs-languagePreferences',
           $d('a', {'href': '#'}, 'Language Preferences'));
    this.usernameLink_ =
        $d('li', null,
           $d('a', {'href': '#'}, 'USERNAME'));
    this.logoutLink_ =
        $d('li', null,
           $d('a', {'href': '#'}, 'Logout'));
    this.getEmbedCodeLink_ =
        $d('li', null,
           $d('a', {'href': unisubs.getSubtitleHomepageURL(this.videoID_)}, 'Get Embed Code'));
};

unisubs.widget.DropDown.prototype.moderatedResponseReceived_ = function(jsonResult) {
    var $d = goog.bind(this.getDomHelper().createDom, this.getDomHelper());

    this.showAddLanguageLink_ = jsonResult['can_translate'];
    this.showImproveSubtitlesLink_ = jsonResult['can_subtitle'];
    this.addActionLinks_();
};
unisubs.widget.DropDown.prototype.addModeratedActionLinks_ = function() {
    unisubs.Rpc.call(
        'can_user_edit_video',
        { 'video_id': this.videoID_ },
        goog.bind(this.moderatedResponseReceived_, this));
};
unisubs.widget.DropDown.prototype.addModeratedNotice_ = function() {
    goog.dom.insertChildAt(this.videoActions_, this.moderatedNotice_, 0);
};
/**
 * Add action links to the drop-down menu.
 *
 * This should only be called after we have checked that the user has
 * permission to edit the subtitles.
 *
 * @this {DropDown}
 */
unisubs.widget.DropDown.prototype.addActionLinks_ = function() {
    if(this.showImproveSubtitlesLink_) {
      goog.dom.insertChildAt(this.videoActions_, this.improveSubtitlesLink_, 0);
    }
    if(this.showAddLanguageLink_) {
      goog.dom.insertChildAt(this.videoActions_, this.addLanguageLink_, 0);
    }
    if(!(this.showAddLanguageLink_ || this.showImproveSubtitlesLink_)) {
      this.addModeratedNotice_();
    }
};
unisubs.widget.DropDown.prototype.updateActions_ = function() {
    this.getDomHelper().removeChildren(this.videoActions_);
    this.getDomHelper().removeChildren(this.settingsActions_);

    if (this.isModerated()) {
        if (unisubs.isEmbeddedInDifferentDomain()) {
            this.addModeratedNotice_();
        } else {
            this.addModeratedActionLinks_();
        }
    } else {
        this.showAddLanguageLink_ = true;
        this.showImproveSubtitlesLink_ = true;
        this.addActionLinks_();
    }

    goog.dom.append(this.videoActions_,
                    this.subtitleHomepageLink_,
                    this.getEmbedCodeLink_,
                    this.downloadSubtitlesLink_);

    if (unisubs.currentUsername === null) {
        this.settingsActions_.appendChild(this.createAccountLink_);
    } else {
        goog.dom.setTextContent(
            goog.dom.getFirstElementChild(this.usernameLink_),
            unisubs.currentUsername);
        this.settingsActions_.appendChild(this.usernameLink_);
        this.settingsActions_.appendChild(this.logoutLink_);
    }
    this.settingsActions_.appendChild(this.languagePreferencesLink_);
};

unisubs.widget.DropDown.prototype.enterDocument = function() {
    unisubs.widget.DropDown.superClass_.enterDocument.call(this);
    var s = unisubs.widget.DropDown.Selection;
    var click = goog.events.EventType.CLICK;
    this.getHandler().
        listen(this.unisubsLink_, click,
            function(e) { window.open('http://www.universalsubtitles.org'); }).
        listen(this.addLanguageLink_, click,
               goog.bind(this.menuItemClicked_, this, s.ADD_LANGUAGE)).
        listen(this.improveSubtitlesLink_, click,
               goog.bind(this.menuItemClicked_, this, s.IMPROVE_SUBTITLES)).
        listen(this.subtitleHomepageLink_, click,
               goog.bind(this.menuItemClicked_, this, s.SUBTITLE_HOMEPAGE)).
        listen(this.downloadSubtitlesLink_, click,
               goog.bind(this.menuItemClicked_, this, s.DOWNLOAD_SUBTITLES)).
        listen(this.createAccountLink_, click,
               goog.bind(this.menuItemClicked_, this, s.CREATE_ACCOUNT)).
        listen(this.languagePreferencesLink_, click,
               goog.bind(this.menuItemClicked_, this, s.LANGUAGE_PREFERENCES)).
        listen(this.subtitlesOff_, click,
               goog.bind(this.menuItemClicked_, this, s.SUBTITLES_OFF)).
        listen(this.usernameLink_, click,
               goog.bind(this.menuItemClicked_, this, s.USERNAME)).
        listen(this.logoutLink_, click,
               goog.bind(this.menuItemClicked_, this, s.LOGOUT)).
        listen(unisubs.userEventTarget,
               goog.object.getValues(unisubs.EventType),
               this.loginStatusChanged).
        listen(this.getDomHelper().getDocument(),
               goog.events.EventType.MOUSEDOWN,
               this.onDocClick_, true);

    // Webkit doesn't fire a mousedown event when opening the context menu,
    // but we need one to update menu visibility properly. So in Safari handle
    // contextmenu mouse events like mousedown.
    // {@link http://bugs.webkit.org/show_bug.cgi?id=6595}
    if (goog.userAgent.WEBKIT)
        this.getHandler().listen(
            this.getDomHelper().getDocument(),
            goog.events.EventType.CONTEXTMENU,
            this.onDocClick_, true);

    this.addLanguageLinkListeners_();
};

unisubs.widget.DropDown.prototype.addLanguageLinkListeners_ = function() {
    this.languageClickHandler_.removeAll();
    var that = this;
    goog.array.forEach(this.videoLanguagesLinks_,
        function(tLink) {
            that.languageClickHandler_.listen(tLink.link, 'click',
               goog.bind(
                    that.languageSelected_,
                    that,
                    tLink.videoLanguage));
        });
};

unisubs.widget.DropDown.prototype.onDocClick_ = function(e) {
    if (this.shown_ &&
        !goog.dom.contains(this.getElement(), e.target) &&
        !goog.dom.contains(this.videoTab_.getElement(), e.target))
        this.hide();
};

unisubs.widget.DropDown.prototype.menuItemClicked_ = function(type, e) {
    e.preventDefault();
    e.stopPropagation();

    var s = unisubs.widget.DropDown.Selection;
    if (type == s.CREATE_ACCOUNT)
        unisubs.login();
    else if (type == s.LOGOUT)
        unisubs.logout();
    else if (type == s.USERNAME)
        window.open(unisubs.siteURL() + '/profiles/mine');
    else if (type == s.LANGUAGE_PREFERENCES)
        window.open(unisubs.siteURL() + '/profiles/mine');
    else if (type == s.SUBTITLE_HOMEPAGE)
        window.location.replace(goog.dom.getFirstElementChild(this.subtitleHomepageLink_).href);
    else if (type == s.DOWNLOAD_SUBTITLES){
        window.open(goog.dom.getFirstElementChild(this.downloadSubtitlesLink_).href);
    }

    else if (type == s.ADD_LANGUAGE || type == s.IMPROVE_SUBTITLES ||
             type == s.SUBTITLES_OFF)
        this.dispatchEvent(type);

    this.hide();
};

unisubs.widget.DropDown.prototype.languageSelected_ = function(videoLanguage, e) {
    if (e){
        e.preventDefault();
    }
    this.dispatchLanguageSelection_(videoLanguage);
    goog.dom.getFirstElementChild(this.downloadSubtitlesLink_).href =
        this.createDownloadSRTURL_();
};

unisubs.widget.DropDown.prototype.dispatchLanguageSelection_ = function(videoLanguage) {
    this.dispatchEvent(
        new unisubs.widget.DropDown.LanguageSelectedEvent(videoLanguage));
};

unisubs.widget.DropDown.prototype.clearCurrentLang_ = function() {
    this.subtitlesOff_.className = '';
    for (var i = 0; i < this.videoLanguagesLinks_.length; i++)
        this.videoLanguagesLinks_[i].linkLi.className = '';
};

unisubs.widget.DropDown.prototype.setCurrentLangClassName_ = function() {
    var className = 'unisubs-activeLanguage';
    var that = this;
    if (!this.subtitleState_)
        this.subtitlesOff_.className = className;
    else {
        var transLink = goog.array.find(this.videoLanguagesLinks_, function(elt) {
            return elt.videoLanguage.PK == that.subtitleState_.LANGUAGE_PK;
        });
        if (transLink)
            transLink.linkLi.className = className;
    }
};

unisubs.widget.DropDown.prototype.getVideoLanguages = function() {
    return this.videoLanguages_;
};

unisubs.widget.DropDown.prototype.setVideoLanguages =
    function(videoLanguages) {
    this.videoLanguages_ = videoLanguages;
};

unisubs.widget.DropDown.prototype.toggleShow = function() {
    if (this.shown_)
        this.hide();
    else
        this.show();
};

unisubs.widget.DropDown.prototype.hide = function() {
    unisubs.style.showElement(this.getElement(), false);
    this.shown_ = false;
};

unisubs.widget.DropDown.prototype.show = function() {
    unisubs.attachToLowerLeft(this.videoTab_.getAnchorElem(),
                               this.getElement());
    this.shown_ = true;
};

unisubs.widget.DropDown.prototype.loginStatusChanged = function() {
    this.updateActions_();
};

unisubs.widget.DropDown.prototype.disposeInternal = function() {
    unisubs.widget.DropDown.superClass_.disposeInternal.call(this);
    this.languageClickHandler_.dispose();
};

/**
* @constructor
* @param {unisubs.startdialog.VideoLanguage} videoLanguage
*/
unisubs.widget.DropDown.LanguageSelectedEvent = function(videoLanguage) {
    this.type = unisubs.widget.DropDown.Selection.LANGUAGE_SELECTED;
    this.videoLanguage = videoLanguage;
};
