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

/**
 * @fileoverview ServerModel implementation for unisubs server.
 *
 */

goog.provide('unisubs.subtitle.MSServerModel');

/**
 *
 *
 * @constructor
 * @implements {unisubs.subtitle.ServerModel}
 * @extends {goog.Disposable}
 * @param {string} sessionPK Amara subtitling session primary key
 * @param {string} videoID Amara video id
 * @param {string} videoURL url for the video
 * @param {unisubs.subtitle.EditableCaptionSet} editableCaptionSet
 */
unisubs.subtitle.MSServerModel = function( sessionPK, videoID, videoURL, editableCaptionSet) {
    goog.Disposable.call(this);
    this.sessionPK_ = sessionPK;
    this.videoID_ = videoID;
    this.videoURL_ = videoURL;
    this.captionSet_ = editableCaptionSet;
    this.initialized_ = false;
    this.finished_ = false;
    this.timerTickCount_ = 0;
    this.timer_ = new goog.Timer(
        (unisubs.LOCK_EXPIRATION - 5) * 1000);
    goog.events.listen(
        this.timer_,
        goog.Timer.TICK,
        goog.bind(this.timerTick_, this));
    unisubs.subtitle.MSServerModel.currentInstance = this;
    // task attributes for both review / approve
    this.taskId = null;
    this.taskNotes = null;
    this.taskApproved = null;
    this.taskType = null;
    window.server = this;
};

goog.inherits(unisubs.subtitle.MSServerModel, goog.Disposable);

unisubs.subtitle.MSServerModel.currentInstance = null;

/*
 * URL for the widget's embed javascript.
 * Set by unisubs.EmbeddableWidget when widget first loads.
 * @type {string}
 */

unisubs.subtitle.MSServerModel.EMBED_JS_URL = null;

/**
 * @return {?unisubs.widget.SavedSubtitles}
 */
unisubs.subtitle.MSServerModel.prototype.fetchInitialSubs_ = function() {
    return unisubs.widget.SavedSubtitles.fetchInitial();
};
unisubs.subtitle.MSServerModel.prototype.init = function() {
    if (!this.initialized_) {
        this.initialized_ = true;
        this.startTimer();
    }
};
unisubs.subtitle.MSServerModel.prototype.startTimer = function() {
    this.timer_.start();
};
unisubs.subtitle.MSServerModel.prototype.timerTick_ = function(e) {
    unisubs.Rpc.call(
        'regain_lock',
        { 'session_pk': this.sessionPK_  },
        function(result) {
            if (result['response'] != 'ok') {
                // this should never happen.
                alert("You lost the lock on these subtitles. This " +
                      "probably happened because your network connection disappeared for too long.");
            }
        },
        function() {
            // TODO: this means there was an error -- probably bad network connection.
            // we should communicate this to the user, since the user is in danger
            // of losing subtitling work.
        });
    this.timerTickCount_++;
    if ((this.timerTickCount_ % 4) == 0) {
        this.saveSubsLocally_();
    }
};
unisubs.subtitle.MSServerModel.prototype.saveSubsLocally_ = function() {
    // for 2k subs, this takes about 20-40ms on FF and Chrome on my Macbook.
    var savedSubs = new unisubs.widget.SavedSubtitles(
        this.sessionPK_, this.captionSet_);
    unisubs.widget.SavedSubtitles.saveLatest(savedSubs);
};
unisubs.subtitle.MSServerModel.prototype.anySubtitlingWorkDone = function() {
    return this.captionSet_.count() > 0;
};
unisubs.subtitle.MSServerModel.prototype.setPristineSubtitles = function(pristineSubtitlesJSON) {
    this.pristineSubtitlesJSON = pristineSubtitlesJSON;
};

/**
 * @param {unisubs.widget.SubtitleState} standardSubState SubtitleState for original language subs
 */
unisubs.subtitle.MSServerModel.prototype.fork = function(standardSubState) {
    this.captionSet_.fork(standardSubState);
    this.saveSubsLocally_();
};

unisubs.subtitle.MSServerModel.prototype.makeFinishArgs_ = function() {
    /**
     * @type {unisubs.widget.SavedSubtitles}
     */
    var initialSubs = this.fetchInitialSubs_();
    var initialCaptionSet = initialSubs.CAPTION_SET;
    
    var subtitles = null;

    if (this.anySubtitlingWorkDone() || this.captionSet_.forkedDuringEdits_) {
        subtitles = this.captionSet_.nonblankSubtitles();
    }

    var args = { 'session_pk': this.sessionPK_ };
    var atLeastOneThingChanged = false;

    if (!goog.isNull(subtitles)) {
        args['subtitles'] = this.captionSet_.x['xmlToString'](true, true);
        atLeastOneThingChanged = true;
    }

    if (goog.isDefAndNotNull(this.captionSet_.title) &&
        this.captionSet_.title != initialCaptionSet.title) {
        args['new_title'] = this.captionSet_.title;
        atLeastOneThingChanged = true;
    }

    if (goog.isDefAndNotNull(this.captionSet_.description) &&
        this.captionSet_.description != initialCaptionSet.description) {
        args['new_description'] = this.captionSet_.description;
        atLeastOneThingChanged = true;
    }

    var newMetadata = {}
    for(key in this.captionSet_.metadata) {
        var newValue = this.captionSet_.metadata[key];
        var oldValue = initialCaptionSet.metadata[key];
        if(goog.isDefAndNotNull(newValue) && newValue != oldValue) {
            newMetadata[key] = newValue;
        }
    }
    if(newMetadata) {
        args['new_metadata'] = newMetadata;
    }

    if (goog.isDefAndNotNull(this.captionSet_.completed) &&
        this.captionSet_.completed != initialCaptionSet.completed) {
        args['completed'] = this.captionSet_.completed;
        atLeastOneThingChanged = true;
    }

    if (this.captionSet_.wasForkedDuringEdits()) {
        args['forked'] = true;
        atLeastOneThingChanged = true;
        // a fork alone isn't sufficient to trigger a save,
        // so not setting atLeastOneThingChanged.
    }

    if (window['UNISUBS_THROW_EXCEPTION']) {
        args['throw_exception'] = true;
    }

    // add task arguments, if they are all null, it will be harmless on the 
    // backend
    args['task_id'] = this.taskId;
    args['task_notes'] = this.taskNotes;
    if (this.taskApproved != undefined){
        atLeastOneThingChanged = true;
    }
    // if the save and exit button was created, we must pass this as a value
    if (! this.taskApproved && this.taskId ){
        this.taskApproved = unisubs.Dialog.MODERATION_OUTCOMES.SAVE_FOR_LATER;
    }
    args['task_approved'] = this.taskApproved;

    args['task_type'] = this.taskType;
    return atLeastOneThingChanged ? args : null;
};
unisubs.subtitle.MSServerModel.prototype.finish = function(successCallback, failureCallback, opt_cancelCallback, saveForLater) {
    goog.asserts.assert(this.initialized_);
    goog.asserts.assert(!this.finished_);

    this.saveSubsLocally_();

    this.stopTimer();

    var that = this;
    var args = this.makeFinishArgs_();
    args['save_for_later'] = saveForLater;  // TODO: Pass this in a more elegant way?

    if (goog.isNull(args)) { // no changes.
        successCallback("Saved"); // TODO: is this the right ux?
        return;
    }

    unisubs.Rpc.call(
        'finished_subtitles',
        args,
        function(result) {
            if (result['response'] != 'ok') {
                // this should never happen.
                alert('Problem saving subtitles. Response: ' +
                      result["response"]);
                failureCallback(200);
            }
            else {
                that.finished_ = true;
                successCallback(result["user_message"]);
            }
        },
        function(opt_status) {
            failureCallback(opt_status);
        },
        true);
};
unisubs.subtitle.MSServerModel.prototype.setComplete = function(isComplete){
    this.captionSet_.completed = isComplete;
};
unisubs.subtitle.MSServerModel.prototype.fetchReviewData = function(taskId, successCallback) {
    var that = this;
    unisubs.Rpc.call(
        'fetch_review_data',
        {'task_id': taskId},
        function(result) {
            if (result['response'] != 'ok') {
                // this should never happen.
                alert('Problem fetching review data. Response: ' + result["response"]);
                failureCallback(200);
            } else {
                that.taskId = taskId;
                that.taskType = 'review';
                successCallback(result['body']);
            }
        }, function(opt_status) {
            failureCallback(opt_status);
        }, true);

};
unisubs.subtitle.MSServerModel.prototype.fetchApproveData = function(taskId, successCallback) {
    var that = this;
    unisubs.Rpc.call(
        'fetch_approve_data',
        {'task_id': taskId},
        function(result) {
            if (result['response'] != 'ok') {
                // this should never happen.
                alert('Problem fetching approval data. Response: ' + result["response"]);
                failureCallback(200);
            } else {
                that.taskId = taskId;
                that.taskType = 'approve';
                successCallback(result['body']);
            }
        }, function(opt_status) {
            failureCallback(opt_status);
        }, true);

};

/** 
* Store the review notes. This should get called by the proper panel before calling finish
*/
unisubs.subtitle.MSServerModel.prototype.setTaskNotes = function(notes) {
    this.taskNotes = notes;
};

/** 
* Store the review /approval status. This should get called by the proper panel before calling finish
*/
unisubs.subtitle.MSServerModel.prototype.setTaskApproved  = function(approvalCode) {
    this.taskApproved = approvalCode;
};
unisubs.subtitle.MSServerModel.prototype.getEmbedCode = function() {
    return [
        '<sc',
        'ript type="text/javascript" src="',
        unisubs.staticURL(),
        'embed', unisubs.embedVersion, '.js',
        '">\n',
        '({\n',
        '   video_url: "', this.videoURL_, '"\n',
        '})\n',
        '</script>'].join('');
};
unisubs.subtitle.MSServerModel.prototype.stopTimer = function() {
    this.timer_.stop();
};
unisubs.subtitle.MSServerModel.prototype.disposeInternal = function() {
    unisubs.subtitle.MSServerModel.superClass_.disposeInternal.call(this);
    this.stopTimer();
    this.timer_.dispose();
};
unisubs.subtitle.MSServerModel.prototype.currentUsername = function() {
    return unisubs.currentUsername;
};
unisubs.subtitle.MSServerModel.prototype.logIn = function() {
    unisubs.login();
};
unisubs.subtitle.MSServerModel.prototype.getPermalink = function() {
    return unisubs.getVideoHomepageURL(this.videoID_);
};
unisubs.subtitle.MSServerModel.prototype.getVideoID = function() {
    return this.videoID_;
};
unisubs.subtitle.MSServerModel.prototype.getCaptionSet = function() {
    return this.captionSet_;
};
unisubs.subtitle.MSServerModel.prototype.getSessionPK = function() {
    return this.sessionPK_;
};
