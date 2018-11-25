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

var angular = angular || null;

(function() {
    /*
     * amara.subtitles.models
     *
     * Define model classes that we use for subtitles
     */

    var module = angular.module('amara.SubtitleEditor.subtitles.models', []);

    // Add function to match by attributes with in the xml namespace
    $.fn.findXmlID = function(value) {
        return this.filter(function() {
            return $(this).attr('xml:id') == value
        });
    };

    function emptyDFXP(languageCode) {
        /* Get a DFXP string for an empty subtitle set */
        return '<tt xmlns="http://www.w3.org/ns/ttml" xmlns:tts="http://www.w3.org/ns/ttml#styling" xml:lang="' + languageCode + '">\
    <head>\
        <metadata xmlns:ttm="http://www.w3.org/ns/ttml#metadata">\
            <ttm:title/>\
            <ttm:description/>\
            <ttm:copyright/>\
        </metadata>\
        <styling>' + amaraStyle() + '</styling>\
        <layout>' + bottomRegion() + topRegion() + '</layout>\
    </head>\
    <body region="bottom"><div /></body>\
</tt>';
    };

    function amaraStyle() {
        return '<style xml:id="amara-style" tts:color="white" tts:fontFamily="proportionalSansSerif" tts:fontSize="18px" tts:backgroundColor="transparent" tts:textOutline="black 1px 0px" tts:textAlign="center"/>';
    }

    function bottomRegion() {
        return '<region xml:id="bottom" style="amara-style" tts:extent="100% 20%" tts:origin="0% 80%" />';
    }

    function topRegion() {
        return '<region xml:id="top" style="amara-style" tts:extent="100% 20%" tts:origin="0% 0%" />';
    }

    function preprocessDFXP(xml) {
        // Alter XML that we're loading to ensure that it can work with the editor.
        //
        // This means doing things like ensuring that our expected regions are present
        var doc = $($.parseXML(xml));
        var styling = doc.find('styling');
        var layout = doc.find('layout');
        if(styling.find("style").findXmlID('amara-style').length == 0) {
            styling.append($(amaraStyle()));
        }
        if(layout.find("region").findXmlID('bottom').length == 0) {
            layout.append($(bottomRegion()));
        }
        if(layout.find("region").findXmlID('top').length == 0) {
            layout.append($(topRegion()));
        }
        return doc[0];
    }

    /*
     * Manages a list of subtitles.
     *
     * For functions that return subtitle items, each item will have the
     * following properties:
     *   - startTime -- start time in seconds
     *   - endTime -- end time in seconds
     *   - content -- string of html for the subtitle content
     *   - startOfParagraph -- does this subtitle start a new paragraph?
     *   - region -- Region to position the subtitle (top, or undefined for bottom)
     *   - node -- DOM node from the DFXP XML
     *
     */

    module.service('SubtitleList', ['gettext', 'interpolate', 'SubtitleSoftLimits', function(gettext, interpolate, SubtitleSoftLimits) {
        var MAX_UNDO_ITEMS = 1000;

        function Subtitle(startTime, endTime, markdown, region, startOfParagraph) {
            /* Represents a subtitle in our system
             *
             * Subtitle has the following properties:
             *   - startTime -- start time in seconds
             *   - endTime -- end time in seconds
             *   - markdown -- subtitle content in our markdown-style format
             *   - region -- subtitle display region (top, or undefined for the default/bottom)
             *   - startOfParagraph -- Are we the start of a new paragraph?
             */
            this.startTime = startTime;
            this.endTime = endTime;
            this.markdown = markdown;
            this.region = region;
            this.startOfParagraph = startOfParagraph;
        }

        Subtitle.prototype.duration = function() {
            if(this.isSynced()) {
                return this.endTime - this.startTime;
            } else {
                return -1;
            }
        }

        Subtitle.prototype.hasWarning = function(type, data) {
            if ((type == "lines" || type == undefined) && (this.lineCount() > SubtitleSoftLimits.lines))
                return true;
            if ((type == "characterRate" || type == undefined) && (this.characterRate() > SubtitleSoftLimits.cps))
                return true;
            if ((type == "timing" || type == undefined) && ((this.startTime > -1) && (this.endTime > -1) && (this.endTime - this.startTime < SubtitleSoftLimits.minDuration)))
                return true;
            if (type == "longline" || type == undefined) {
                var counts = this.characterCountPerLine();
                var from = (data == undefined) ? 0 : data;
                var to = (data == undefined) ? (counts.length) : (data + 1);
                for (var i = from; i < to ; i++) {
                    if (counts[i] > SubtitleSoftLimits.cpl) {
                        return true;
                    }
                }
            }
            return false;
        }

        Subtitle.prototype.content = function() {
            /* Get the content of this subtitle as HTML */
            return dfxp.markdownToHTML(this.markdown);
        }

        Subtitle.prototype.isEmpty = function() {
            return this.markdown == '';
        }

        Subtitle.prototype.characterCount = function() {
            var rawContent = dfxp.markdownToPlaintext(this.markdown);
            // Newline characters are not counted
            return (rawContent.length - (rawContent.match(/\n/g) || []).length);
        }

        Subtitle.prototype.characterRate = function() {
            if(this.isSynced()) {
                return (this.characterCount() * 1000 / this.duration()).toFixed(1);
            } else {
                return "0.0";
            }
        }

        Subtitle.prototype.lineCount = function() {
            return this.markdown.split("\n").length;
        }

        Subtitle.prototype.characterCountPerLine = function() {
            var lines = this.markdown.split("\n");
            var counts = [];
            for(var i = 0; i < lines.length; i++) {
                counts.push(dfxp.markdownToPlaintext(lines[i]).length);
            }
            return counts;
            
        }

        Subtitle.prototype.isSynced = function() {
            return this.startTime >= 0 && this.endTime >= 0;
        }

        Subtitle.prototype.isAt = function(time) {
            return this.isSynced() && this.startTime <= time && this.endTime > time;
        }

        Subtitle.prototype.startTimeSeconds = function() {
            if(this.startTime >= 0) {
                return this.startTime / 1000;
            } else {
                return -1;
            }
        }

        Subtitle.prototype.endTimeSeconds = function() {
            if(this.endTime >= 0) {
                return this.endTime / 1000;
            } else {
                return -1;
            }
        }

        Subtitle.prototype.isWhiteSpaceOnly = function() {
            return !$.trim(this.markdown)
        }

        function StoredSubtitle(parser, node, id) {
            /* Subtitle stored in a SubtitleList
             *
             * You should never change the proporties on a stored subtitle directly.
             * Instead use the updateSubtitleContent() and updateSubtitleTime()
             * methods of SubtitleList.
             *
             * If you want a subtitle object that you can change the times/content
             * without saving them to the DFXP store, use the draftSubtitle() method
             * to get a DraftSubtitle.
             * */
            var text = $(node).text().trim();
            Subtitle.call(this, parser.startTime(node), parser.endTime(node),
                    text, parser.region(node), parser.startOfParagraph(node));
            this.node = node;
            this.id = id;
        }

        StoredSubtitle.prototype = Object.create(Subtitle.prototype);
        StoredSubtitle.prototype.draftSubtitle = function() {
            return new DraftSubtitle(this);
        }
        StoredSubtitle.prototype.isDraft = false;

        function DraftSubtitle(storedSubtitle) {
            /* Subtitle that we are currently changing */
            Subtitle.call(this, storedSubtitle.startTime, storedSubtitle.endTime,
                    storedSubtitle.markdown, storedSubtitle.region, storedSubtitle.startOfParagraph);
            this.storedSubtitle = storedSubtitle;
        }

        DraftSubtitle.prototype = Object.create(Subtitle.prototype);
        DraftSubtitle.prototype.isDraft = true;

        var SubtitleList = function() {
            this.parser = new AmaraDFXPParser();
            this.idCounter = 0;
            this.subtitles = [];
            this.syncedCount = 0;
            this.changeCallbacks = [];
            this.pendingChanges = [];

            this.undoStack = [];
            this.redoStack = [];
            // List of change items to undo all changes since the last
            // _changesDone() call.  This gets moved to the undoStack/redoStack
            // in _changesDone
            this.rollbackStack = [];
        }

        // Low-level methods to make changes to the list

        SubtitleList.prototype._makeItem = function(node) {
            var idKey = (this.idCounter++).toString(16);

            return new StoredSubtitle(this.parser, node, idKey);
        }

        SubtitleList.prototype._insertSubtitle = function(index, attrs) {
            if(attrs === undefined) {
                attrs = {};
            }
            if(index < 0 || index > this.subtitles.length) {
                throw 'Invalid insert index: ' + index;
            }
            // We insert the subtitle before the reference point, but AmaraDFXPParser
            // wants to insert it after, so we need to adjust things a bit.
            if(index > 0) {
                var after = this.subtitles[index-1].node;
            } else {
                var after = -1;
            }
            // Convert attrs to things that AmaraDFXPParser expects
            var nodeAttrs = {
                begin: attrs.startTime,
                end: attrs.endTime,
                region: attrs.region
            };
            var nextSubtitle = (index < this.subtitles.length) ? this.subtitles[index] : null;
            var node = this.parser.addSubtitle(after, nodeAttrs, attrs.content);
            if(attrs.startOfParagraph) {
                this.parser.startOfParagraph(node, true);
            }
            var subtitle = this._makeItem(node);
            this.subtitles.splice(index, 0, subtitle);
            if(subtitle.isSynced()) {
                this.syncedCount++;
            }
            this.rollbackStack.push([this._removeSubtitle, index, {}]);
            this._addChange('insert', subtitle, { 'before': nextSubtitle});
            return subtitle;
        }

        SubtitleList.prototype._removeSubtitle = function(index, attrs) {
            var subtitle = this.subtitles[index];
            var rollbackAttrs = {
                startTime: subtitle.startTime,
                endTime: subtitle.endTime,
                content: subtitle.markdown,
                startOfParagraph: subtitle.startOfParagraph,
                region: subtitle.region
            };
            this.parser.removeSubtitle(subtitle.node);
            this.subtitles.splice(index, 1);
            if(subtitle.isSynced()) {
                this.syncedCount--;
            }
            this.rollbackStack.push([this._insertSubtitle, index, rollbackAttrs]);
            this._addChange('remove', subtitle);
        }

        SubtitleList.prototype._updateSubtitle = function(index, attrs) {
            var subtitle = this.subtitles[index];
            var wasSynced = subtitle.isSynced();
            var rollbackAttrs = {};

            if('startTime' in attrs && subtitle.startTime != attrs.startTime) {
                rollbackAttrs.startTime = subtitle.startTime;
                this.parser.startTime(subtitle.node, attrs.startTime);
                subtitle.startTime = attrs.startTime;
            }
            if('endTime' in attrs && subtitle.endTime != attrs.endTime) {
                rollbackAttrs.endTime = subtitle.endTime;
                this.parser.endTime(subtitle.node, attrs.endTime);
                subtitle.endTime = attrs.endTime;
            }

            if('content' in attrs && subtitle.markdown != attrs.content) {
                rollbackAttrs.content = subtitle.markdown;
                this.parser.content(subtitle.node, attrs.content);
                subtitle.markdown = attrs.content;
            }

            if('region' in attrs && subtitle.region != attrs.region) {
                rollbackAttrs.region = subtitle.region;
                // Passing undefined change the region, so we need to do some more work.
                if(attrs.region) {
                    this.parser.region(subtitle.node, attrs.region);
                } else {
                    this.parser.region(subtitle.node, null);
                }
                subtitle.region = attrs.region;
            }

            if('startOfParagraph' in attrs && subtitle.startOfParagraph != attrs.startOfParagraph) {
                rollbackAttrs.startOfParagraph = subtitle.startOfParagraph;
                this.parser.startOfParagraph(subtitle.node, attrs.startOfParagraph);
                subtitle.startOfParagraph = attrs.startOfParagraph;
            }

            if(subtitle.isSynced() && !wasSynced) {
                this.syncedCount++;
            }
            if(!subtitle.isSynced() && wasSynced) {
                this.syncedCount--;
            }
            this.rollbackStack.push([this._updateSubtitle, index, rollbackAttrs]);
            this._addChange('update', subtitle);
        }

        /*
         * bulkChange -- Make multiple changes at once
         *
         * Pass this method a list of changes, each one should be a list with the following elements
         *   - function (_insertSubtitle, _removeSubtitle, or _updateSubtitle)
         *   - pos
         *   - attrs
         *
         * Returns a list of subtitles changed
         */
        SubtitleList.prototype._bulkChange = function(changes) {
            var self = this;
            _.each(changes, function(change) {
                change[0].call(self, change[1], change[2]);
            });
        }

        // Call this after you're done doing a group of changes.  It will:
        //   - Take the current rollback stack and append it to the undo stack
        //      - If changeGroup is the same as the changeGroup passed last
        //        time, then we will combine the current rollbackStack instead
        //        of creating a new entry.
        //   - Invoke registered change callbacks
        //
        SubtitleList.prototype._changesDone = function(changeDescription, changeGroup) {
            this.rollbackStack.reverse();

            if(changeGroup && this.lastChangeGroup() === changeGroup) {
                this.mergeRollbackStackIntoUndoStack();
            } else {
                this.undoStack.push([changeDescription, this.rollbackStack, changeGroup]);
                this.undoStack = _.last(this.undoStack, MAX_UNDO_ITEMS);
            }

            this.redoStack = [];
            this.rollbackStack = [];
            this._invokeChangeCallbacks();
        }

        SubtitleList.prototype.lastChangeGroup = function() {
            if(this.undoStack.length > 0) {
                return _.last(this.undoStack)[2];
            } else {
                return null;
            }
        }

        // Take the current changes in the rollback stack and merge them into the changes in the last undo stack entry.
        //
        // We do some basic optimizations to reduce the number of changes: If
        // there is a segment of the combined list that's all _updateSubtitle
        // calls, then combine the calls for the same subtitles.
        SubtitleList.prototype.mergeRollbackStackIntoUndoStack = function() {
            var mergedChanges = [];
            var updateMap = {}; // For _updateSubtitle changes, map the subtitle position to the index in mergedChanges
            var lastUndoStackEntry = _.last(this.undoStack);
            var self = this;

            function processChange(change) {
                if(change[0] === self._updateSubtitle) {
                    var pos = change[1];
                    if(pos in updateMap) {
                        // There was already an update for this subtitle, merge
                        // it with the last change.  Use _.defaults, because we
                        // want the values from the older change to take
                        // precedence.
                        _.defaults(mergedChanges[updateMap[pos]][2], change[2]);
                    } else {
                        // This is the first update for this subtitle, add it
                        // to mergedChanges and remember the position
                        mergedChanges.push(change)
                        updateMap[pos] = mergedChanges.length - 1;
                    }
                } else {
                    // Insert or removal, clear out updateMap since the values are no longer valid
                    updateMap = {};
                }
            }

            // Process existing changes
            _.each(lastUndoStackEntry[1], processChange);
            // Process new changes
            _.each(this.rollbackStack, processChange);
            // Replace the old changes with the merged changes
            lastUndoStackEntry[1] = mergedChanges;
        }

        SubtitleList.prototype._reloadDone = function() {
            this._addChange('reload', null);
            this._resetUndo();
            this._invokeChangeCallbacks();
        }

        // High-level functions
        SubtitleList.prototype.loadEmptySubs = function(languageCode) {
            this.loadXML(emptyDFXP(languageCode));
        }

        SubtitleList.prototype.loadXML = function(subtitlesXML) {
            this.parser.init(subtitlesXML);
            var syncedSubs = [];
            var unsyncedSubs = [];
            // Needed because each() changes the value of this
            var self = this;
            this.parser.getSubtitles().each(function(index, node) {
                var subtitle = self._makeItem(node);
                if(subtitle.isSynced()) {
                    syncedSubs.push(subtitle);
                } else {
                    unsyncedSubs.push(subtitle);
                }
            });
            syncedSubs.sort(function(s1, s2) {
                return s1.startTime - s2.startTime;
            });
            this.syncedCount = syncedSubs.length;
            // Start with synced subs to the list
            this.subtitles = syncedSubs;
            // append all unsynced subs to the list
            this.subtitles.push.apply(this.subtitles, unsyncedSubs);
            this._reloadDone();
        }

        SubtitleList.prototype.addSubtitlesFromBaseLanguage = function(xml) {
            /*
             * Used when we are translating from one language to another.
             * It loads the latest subtitles for xml and inserts blank subtitles
             * with the same timings and paragraphs into our subtitle list.
             */
            var baseLanguageParser = new AmaraDFXPParser();
            baseLanguageParser.init(xml);
            var baseAttributes = [];
            baseLanguageParser.getSubtitles().each(function(index, node) {
                startTime = baseLanguageParser.startTime(node);
                endTime = baseLanguageParser.endTime(node);
                if(startTime >= 0 && endTime >= 0) {
                    baseAttributes.push({
                        'startTime': startTime,
                        'endTime': endTime,
                        'startOfParagraph': baseLanguageParser.startOfParagraph(node),
                        'region': baseLanguageParser.region(node)
                    });
                }
            });
            baseAttributes.sort(function(s1, s2) {
                return s1.startTime - s2.startTime;
            });
            var that = this;
            _.forEach(baseAttributes, function(baseAttribute) {
                var node = that.parser.addSubtitle(null, {
                    begin: baseAttribute.startTime,
                    end: baseAttribute.endTime,
                });
                that.parser.startOfParagraph(node, baseAttribute.startOfParagraph);
                that.parser.region(node, baseAttribute.region);
                that.subtitles.push(that._makeItem(node));
                that.syncedCount++;
            });
            this._reloadDone();
        }

        SubtitleList.prototype.length = function() {
            return this.subtitles.length;
        }

        SubtitleList.prototype.needsAnyTranscribed = function() {
            var length = this.length();
            for(var i=0; i < length; i++) {
                if(this.subtitles[i].markdown == '') {
                    return this.subtitles[i];
                }
            }
            return false;
        }

        SubtitleList.prototype.getSubtitleById = function(id) {
            var length = this.length();
            for(var i=0; i < length; i++) {
                if(this.subtitles[i].id == id) {
                    return this.subtitles[i];
                }
            }
            return undefined;
        }

        SubtitleList.prototype.needsAnySynced = function() {
            return this.syncedCount < this.length();
        }

        SubtitleList.prototype.isComplete = function() {
            return (this.length() > 0 &&
                    !this.needsAnyTranscribed() &&
                    !this.needsAnySynced());
        }

        SubtitleList.prototype.firstInvalidTiming = function() {
            var length = this.length();
            for(var i=0; i < length; i++) {
                if((this.subtitles[i].startTime < 0) ||
                   (this.subtitles[i].endTime < 0)) {
                    return this.subtitles[i];
                }
            }
            for(var i=0; i < length; i++) {
                if(this.subtitles[i].startTime >= this.subtitles[i].endTime) {
                    return this.subtitles[i];
                }
            }
            var startTimes = {};
            for(var i=0; i < length; i++) {
                if(startTimes[this.subtitles[i].startTime]) {
                    return this.subtitles[i];
                } else {
                    startTimes[this.subtitles[i].startTime] = true;
                }
            }
            return undefined;
        }

        SubtitleList.prototype.toXMLString = function() {
            return this.parser.xmlToString(true, true);
        }

        SubtitleList.prototype.getIndex = function(subtitle) {
            // Maybe a binary search would be faster, but I think Array.indexOf should
            // be pretty optimized on most browsers.
            return this.subtitles.indexOf(subtitle);
        }

        SubtitleList.prototype.nextSubtitle = function(subtitle) {
            if(subtitle === this.subtitles[this.length() - 1]) {
                return null;
            } else {
                return this.subtitles[this.getIndex(subtitle) + 1];
            }
        }

        SubtitleList.prototype.prevSubtitle = function(subtitle) {
            if(subtitle === this.subtitles[0]) {
                return null;
            } else {
                return this.subtitles[this.getIndex(subtitle) - 1];
            }
        }

        SubtitleList.prototype.updateSubtitleTime = function(subtitle, startTime, endTime) {
            this._updateSubtitle(this.getIndex(subtitle), {startTime: startTime, endTime: endTime});
            this._changesDone(gettext('Time change'));
        }

        // Update multiple subtitle times at once
        // Pass a list of objects with the attributes: subtitle, startTime, and endtime
        //
        // Pass changeGroup to group together multiple calls into a single undo
        // entry.  For example when the user is dragging a subtitle in the
        // timeline, this causes many timing changes, but they should all be
        // groupd into a single unto entry.
        SubtitleList.prototype.updateSubtitleTimes = function(changes, changeGroup) {
            var self = this;
            _.each(changes, function(change) {
                self._updateSubtitle(self.getIndex(change.subtitle), {
                    startTime: change.startTime,
                    endTime: change.endTime
                });
            })
            this._changesDone(gettext('Time change'), changeGroup);
        }

        SubtitleList.prototype.clearAllTimings = function() {
            for(var i=0; i < this.subtitles.length; i++) {
                this._updateSubtitle(i, {
                    startTime: -1, endTime: -1
                });
            }
            this._changesDone(gettext('Clear timings'));
        }

        SubtitleList.prototype.clearAllText = function() {
            for(var i=0; i < this.subtitles.length; i++) {
                this._updateSubtitle(i, {content: ''});
            }
            this._changesDone(gettext('Clear text'));
        }

        SubtitleList.prototype.deleteEmptySubtitles = function () {
            for(var i=this.subtitles.length -1; i >= 0; i--) {
                if (this.subtitles[i].isWhiteSpaceOnly()) {
                    this._removeSubtitle(i, {})
                }
            }
            this._changesDone(gettext('Delete empty subtitles'));
        }

        // Copy the subtitle times from another subtitle list
        SubtitleList.prototype.copyTimingsFrom = function(otherSubtitleList) {
            var minLength = Math.min(this.subtitles.length, otherSubtitleList.subtitles.length);

            for(var i=0; i < minLength; i++) {
                var otherSubtitle = otherSubtitleList.subtitles[i];
                this._updateSubtitle(i, {
                    startTime: otherSubtitle.startTime,
                    endTime: otherSubtitle.endTime,
                    startOfParagraph: otherSubtitle.startOfParagraph
                });
            }

            for(var i=minLength; i < this.subtitles.length; i++) {
                this._updateSubtitle(i, {
                    startTime: -1,
                    endTime: -1
                });
            }

            this._changesDone(gettext('Copy timings'));
        }

        // Implements the shift-forward algorithm:
        // - Any subtitle after startTime is shifted forward by duration
        // - Any subtitle that overlays startTime is extended by duration
        //
        SubtitleList.prototype.shiftForward = function(startTime, duration) {
            var self = this;

            _.each(this.subtitles, function(sub, i) {
                if(!sub.isSynced()) {
                    return;
                }
                if(sub.startTime >= startTime) {
                    self._updateSubtitle(i, {
                        startTime: sub.startTime + duration,
                        endTime: sub.endTime + duration
                    });
                } else if(sub.isAt(startTime)) {
                    self._updateSubtitle(i, {
                        endTime: sub.endTime + duration
                    });
                }
            });

            this._changesDone(gettext('Shift forward'));
        }

        // Implements the shift-backward algorithm:
        // - Any subtitle after endTime is shifted backward by duration
        // - Any subtitle inside the time range is removed
        // - Any subtitle partially inside the time range is truncated
        //
        SubtitleList.prototype.shiftBackward = function(startTime, duration) {
            var endTime = startTime + duration;
            var self = this;

            // adjust a time on the time line based on cutting out the period [startTime, endTime].
            function adjustTime(time) {
                if(time > endTime) {
                    return time-duration;
                } else if(time > startTime) {
                    return startTime;
                } else {
                    return time;
                }
            }

            for(var i=0; i < this.subtitles.length; i++) {
                var sub = this.subtitles[i];
                if(!sub.isSynced()) {
                    continue;
                }
                var newStartTime = adjustTime(sub.startTime);
                var newEndTime = adjustTime(sub.endTime);
                if(newStartTime == newEndTime) {
                    self._removeSubtitle(i, {});
                    i--; // Reverse the i++, since we're removing a subtitle_
                    continue
                }

                var changes = {};

                if(newStartTime != sub.startTime) {
                    changes.startTime = newStartTime;
                }
                if(newEndTime != sub.endTime) {
                    changes.endTime = newEndTime;
                }
                if(!_.isEmpty(changes)) {
                    self._updateSubtitle(i, changes);
                }
            }

            this._changesDone(gettext('Shift backward'));
        }

        // Update the text for a subtitle
        //
        // Pass changeGroup to group together multiple calls into a single undo
        // entry.  For example when the user is typing keys in the text entry for a subtitle.
        // This creates many changes, but they should be grouped into a single unto entry.
        SubtitleList.prototype.updateSubtitleContent = function(subtitle, content, changeGroup) {
            this._updateSubtitle(this.getIndex(subtitle), {content: content});
            this._changesDone(gettext('Subtitle edit'), changeGroup);
        }

        SubtitleList.prototype.updateSubtitleParagraph = function(subtitle, startOfParagraph) {
            // If startOfParagraph is not given, it is toggled
            if(startOfParagraph === undefined) {
                startOfParagraph = !subtitle.startOfParagraph;
            }
            this._updateSubtitle(this.getIndex(subtitle), {startOfParagraph: startOfParagraph});
            this._changesDone(gettext('Paragraph change'));
        }

        SubtitleList.prototype.getSubtitleParagraph = function(subtitle) {
            return this.parser.startOfParagraph(subtitle.node);
        }

        SubtitleList.prototype.updateSubtitleRegion = function(subtitle, region) {
            this._updateSubtitle(this.getIndex(subtitle), {region: region});
            this._changesDone(gettext('Position change'));
        }

        SubtitleList.prototype.insertSubtitleBefore = function(otherSubtitle, region) {
            var attrs = {
                region: region
            }
            var defaultDuration = 1000;

            var index = (otherSubtitle === null) ? this.subtitles.length : this.getIndex(otherSubtitle);

            if(otherSubtitle && otherSubtitle.isSynced()) {
                // If we are inserting between before a synced subtitle, then we can set the time
                if(index > 0) {
                    var previousSubtitle = this.subtitles[index-1];
                    // Inserting a subtitle between two others.
                    var gapDuration = otherSubtitle.startTime - previousSubtitle.endTime;
                    if(gapDuration > defaultDuration) {
                        // The gap between the previousSubtitle and otherSubtitle is long enough to fit the new subtitle inside.  Put the subtitle in the middle of that gap
                        attrs.startTime = previousSubtitle.endTime + ((gapDuration - defaultDuration) / 2);
                        attrs.endTime = attrs.startTime + defaultDuration;
                    } else {
                        // The gap is not enough to fit new subtitle inside, move the previousSubtitle.endTime back to fit it.
                        attrs.startTime = otherSubtitle.startTime - defaultDuration
                        // but don't move it so far back that previousSubtitle is now shorter than the new subtitle
                        attrs.startTime = Math.max(attrs.startTime, (previousSubtitle.startTime + otherSubtitle.startTime) / 2);
                        // also, don't move it so far forward that we're now extending previousSubtitle
                        attrs.startTime = Math.min(attrs.startTime, previousSubtitle.endTime);
                        this._updateSubtitle(index-1, {endTime: attrs.startTime});
                        attrs.endTime = otherSubtitle.startTime;
                    }
                } else {
                    // Inserting a subtitle as the start of the list.
                    if(otherSubtitle.startTime >= defaultDuration) {
                        // The gap is large enough for the new subtitle, put it in the middle
                        attrs.startTime = (otherSubtitle.startTime - defaultDuration) / 2;
                        attrs.endTime = attrs.startTime + defaultDuration;
                    } else {
                        attrs.startTime = 0;
                        // The gap is not large enough for the new subtitle to fit inside, move otherSubtitle.startTime forward to fit it in
                        attrs.endTime = defaultDuration;
                        // but don't move it so far forward that otherSubtitle is now shorter than the new subtitle
                        attrs.endTime = Math.min(attrs.endTime, otherSubtitle.endTime / 2);
                        // also, don't move it so far forward that we're now extending previousSubtitle
                        attrs.endTime = Math.max(attrs.endTime, otherSubtitle.startTime);
                        this._updateSubtitle(0, {startTime: attrs.endTime});
                    }
                }
            }
            var subtitle = this._insertSubtitle(index, attrs);
            this._changesDone(gettext('Insert subtitle'));
            return subtitle;
        }

        SubtitleList.prototype.insertSubtitleAtEnd = function(changeGroup) {
            if(this.subtitles.length > 0) {
                var region = this.lastSubtitle().region;
            } else {
                var region = undefined;
            }
            var subtitle = this._insertSubtitle(this.subtitles.length, { region: region });
            this._changesDone(gettext('Insert subtitle'), changeGroup);
            return subtitle;
        }

        // Take a subtitle and split it in half.
        //
        // subtitle will now take up only the first half of the time and get firstSubtitleMarkdown as its content
        // A new subtitle will be created to take up the second half of the time and get secondSubtitleMarkdown as its content
        SubtitleList.prototype.splitSubtitle = function(subtitle, firstSubtitleMarkdown, secondSubtitleMarkdown) {
            var index = this.getIndex(subtitle);
            if(subtitle.isSynced()) {
                var midpointTime = (subtitle.startTime + subtitle.endTime) / 2;
                var newSubAttrs = {
                    startTime: midpointTime,
                    endTime: subtitle.endTime,
                    region: subtitle.region,
                    content: secondSubtitleMarkdown,
                }

                this._updateSubtitle(index, {
                    endTime: midpointTime,
                    content: firstSubtitleMarkdown
                });
            } else {
                var newSubAttrs = { region: subtitle.region, content: secondSubtitleMarkdown }
                this._updateSubtitle(index, {content: firstSubtitleMarkdown});
            }
            var newSubtitle = this._insertSubtitle(index + 1, newSubAttrs);
            this._changesDone(gettext('Split subtitle'));
            return newSubtitle;
        }

        SubtitleList.prototype.removeSubtitle = function(subtitle) {
            this._removeSubtitle(this.getIndex(subtitle));
            this._changesDone(gettext('Remove subtitle'));
        }

        SubtitleList.prototype.lastSyncedSubtitle = function() {
            if(this.syncedCount > 0) {
                return this.subtitles[this.syncedCount - 1];
            } else {
                return null;
            }
        }

        SubtitleList.prototype.firstUnsyncedSubtitle = function() {
            if(this.syncedCount < this.subtitles.length) {
                return this.subtitles[this.syncedCount];
            } else {
                return null;
            }
        }

        SubtitleList.prototype.secondUnsyncedSubtitle = function() {
            if(this.syncedCount + 1 < this.subtitles.length) {
                return this.subtitles[this.syncedCount + 1];
            } else {
                return null;
            }
        }

        SubtitleList.prototype.indexOfFirstSubtitleAfter = function(time) {
            /* Get the first subtitle whose end is after time
             *
             * returns index of the subtitle, or -1 if none are found.
             */

            // Do a binary search to find the sub
            var left = 0;
            var right = this.syncedCount-1;
            // First check that we are going to find any subtitle
            if(right < 0 || this.subtitles[right].endTime <= time) {
                return -1;
            }
            // Now do the binary search
            while(left < right) {
                var index = Math.floor((left + right) / 2);
                if(this.subtitles[index].endTime > time) {
                    right = index;
                } else {
                    left = index + 1;
                }
            }
            return left;
        }

        SubtitleList.prototype.firstSubtitle = function() {
            return this.subtitles[this.indexOfFirstSubtitleAfter(-1)] ||
                   this.firstUnsyncedSubtitle();
        }

        SubtitleList.prototype.lastSubtitle = function() {
            return this.subtitles[this.subtitles.length -1];
        }

        SubtitleList.prototype.subtitleAt = function(time) {
            /* Find the subtitle that occupies a given time.
             *
             * returns a StoredSubtitle, or null if no subtitle occupies the time.
             */
            var i = this.indexOfFirstSubtitleAfter(time);
            if(i == -1) {
                return null;
            }
            var subtitle = this.subtitles[i];
            if(subtitle.isAt(time)) {
                return subtitle;
            } else {
                return null;
            }
        }

        SubtitleList.prototype.getSubtitlesForTime = function(startTime, endTime) {
            var rv = [];
            var i = this.indexOfFirstSubtitleAfter(startTime);
            if(i == -1) {
                return rv;
            }
            for(; i < this.syncedCount; i++) {
                var subtitle = this.subtitles[i];
                if(subtitle.startTime < endTime) {
                    rv.push(subtitle);
                } else {
                    break;
                }
            }
            return rv;
        }

        // Change callbacks
        //
        // Use addChangeCallback if you want to get notified when the list changes

        SubtitleList.prototype.addChangeCallback = function(callback) {
            this.changeCallbacks.push(callback);
        }

        SubtitleList.prototype.removeChangeCallback = function(callback) {
            var pos = this.changeCallbacks.indexOf(callback);
            if(pos >= 0) {
                this.changeCallbacks.splice(pos, 1);
            }
        }

        SubtitleList.prototype._addChange = function(type, subtitle, extraProps) {
            changeObj = { type: type, subtitle: subtitle };
            if(extraProps) {
                for(key in extraProps) {
                    changeObj[key] = extraProps[key];
                }
            }
            this.pendingChanges.push(changeObj);
        }

        SubtitleList.prototype._invokeChangeCallbacks = function() {
            var changes = this.pendingChanges;
            this.pendingChanges = [];
            for(var i=0; i < this.changeCallbacks.length; i++) {
                this.changeCallbacks[i](changes);
            }
        }

        // Undo/redo stack related functions
        SubtitleList.prototype._resetUndo = function() {
            this.undoStack = [];
            this.redoStack = [];
            this.rollbackStack = [];
        }

        SubtitleList.prototype.canUndo = function() {
            return this.undoStack.length > 0;
        }

        SubtitleList.prototype.canRedo = function() {
            return this.redoStack.length > 0;
        }

        SubtitleList.prototype.undoText = function() {
            if(this.canUndo()) {
                var fmtString = gettext('Undo: %(command)s')
                return interpolate(fmtString, {command: _.last(this.undoStack)[0]}, true);
            } else {
                return gettext('Undo');
            }
        }

        SubtitleList.prototype.redoText = function() {
            if(this.canRedo()) {
                var fmtString = gettext('Redo: %(command)s')
                return interpolate(fmtString, {command: _.last(this.redoStack)[0]}, true);
            } else {
                return gettext('Redo');
            }
        }

        SubtitleList.prototype.undo = function () {
            var lastUndo = this.undoStack.pop();
            this._bulkChange(lastUndo[1]);
            this.rollbackStack.reverse();
            this.redoStack.push([lastUndo[0], this.rollbackStack]);
            this.rollbackStack = [];
            this._invokeChangeCallbacks();
        }

        SubtitleList.prototype.redo = function() {
            var lastRedo = this.redoStack.pop();
            this._bulkChange(lastRedo[1]);
            this.rollbackStack.reverse();
            this.undoStack.push([lastRedo[0], this.rollbackStack]);
            this.rollbackStack = [];
            this._invokeChangeCallbacks();
        }

        return SubtitleList;
    }]);

    /*
     * CurrentEditManager manages the current in-progress edit
     */
    module.service('CurrentEditManager', [function() {
        CurrentEditManager = function() {
            this.subtitle = null;
            this.counter = 0;
        }

        CurrentEditManager.prototype = {
            // Called when the user starts editing a subtitle
            start: function(subtitle, options) {
                if(options === undefined) {
                    options = {};
                }
                options = _.defaults(options, {
                    initialCaretPos: subtitle.markdown.length,
                });
                this.subtitle = subtitle;
                this.initialCaretPos = options.initialCaretPos;
                this.autoCreatChangeGroup = null;
                this.updateChangeGroup = 'text-edit-' + this.counter++;
            },
            // Called when the user hits enter from the last subtitle in typing
            // mode.  We automatically create a new subtitle at the end of the
            // subtitle list, then start editing it.  There's also some code in
            // to handle automatically undoing the insert if the user
            // immediately clicks away.
            appendAndStart: function(subtitleList) {
                this.autoCreatChangeGroup = 'text-auto-insert-' + this.counter;
                this.subtitle = subtitleList.insertSubtitleAtEnd(this.autoCreatChangeGroup);
                this.initialCaretPos = 0;
                this.updateChangeGroup = 'text-edit-' + this.counter++;
            },
            update: function(subtitleList, content) {
                if(this.hasChanges(content)) {
                    subtitleList.updateSubtitleContent(this.subtitle, content, this.updateChangeGroup);
                }
            },
            hasChanges: function(content) {
                return this.subtitle.markdown != content;
            },
            undoAutoCreatedSubtitle: function(subtitleList) {
                if(this.autoCreatChangeGroup &&
                        subtitleList.lastChangeGroup() === this.autoCreatChangeGroup) {
                    subtitleList.undo();
                    return true;
                }
                return false;
            },
            finish: function(subtitleList) {
                this.undoAutoCreatedSubtitle(subtitleList);
                this.subtitle = null;
            },
            isForSubtitle: function(subtitle) {
                return this.subtitle === subtitle;
            },
            inProgress: function() {
                return this.subtitle !== null;
            },
            lineCounts: function() {
                if(this.subtitle === null || this.subtitle.lineCount() < 2) {
                    // Only show the line counts if there are 2 or more lines
                    return null;
                } else {
                    return this.subtitle.characterCountPerLine();
                }
            },
        };

        return CurrentEditManager;
    }]);

    /*
     * SubtitleVersionManager: handle the active subtitle version for the
     * reference and working subs.
     *
     */

    module.service('SubtitleVersionManager', ['SubtitleList', function(SubtitleList) {
        SubtitleVersionManager = function(video, SubtitleStorage) {
            this.video = video;
            this.SubtitleStorage = SubtitleStorage;
            this.subtitleList = new SubtitleList();
            this.versionNumber = null;
            this.language = null;
            this.title = null;
            this.description = null;
            this.state = 'waiting';
            this.metadata = {};
        }

        SubtitleVersionManager.prototype = {
            getSubtitles: function(languageCode, versionNumber) {
                this.setLanguage(languageCode);
                this.versionNumber = versionNumber;
                this.state = 'loading';

                var that = this;

                this.SubtitleStorage.getSubtitles(languageCode, versionNumber,
                        function(subtitleData) {
                    that.state = 'loaded';
                    that.title = subtitleData.title;
                    that.initMetadataFromVideo();
                    for(key in subtitleData.metadata) {
                        that.metadata[key] = subtitleData.metadata[key];
                    }
                    that.description = subtitleData.description;
                    var subtitles = preprocessDFXP(subtitleData.subtitles);
                    that.subtitleList.loadXML(subtitles);
                });
            },
            initEmptySubtitles: function(languageCode, baseLanguage) {
                this.setLanguage(languageCode);
                this.versionNumber = null;
                this.title = '';
                this.description = '';
                this.subtitleList.loadEmptySubs(languageCode);
                this.state = 'loaded';
                this.initMetadataFromVideo();
                if(baseLanguage) {
                    this.addSubtitlesFromBaseLanguage(baseLanguage);
                }
            },
            initMetadataFromVideo: function() {
                this.metadata = {};
                for(key in this.video.metadata) {
                    this.metadata[key] = '';
                }
            },
            addSubtitlesFromBaseLanguage: function(baseLanguage) {
                var that = this;
                this.SubtitleStorage.getSubtitles(baseLanguage, null,
                        function(subtitleData) {
                    that.subtitleList.addSubtitlesFromBaseLanguage(
                        subtitleData.subtitles);
                });
            },
            setLanguage: function(code) {
                this.language = this.SubtitleStorage.getLanguage(code);
            },
            getTitle: function() {
                if(!this.language) {
                    return '';
                } else if(this.language.isPrimaryAudioLanguage) {
                    return this.title || this.video.title;
                } else {
                    return this.title;
                }
            },
            getDescription: function() {
                if(!this.language) {
                    return '';
                } else if(this.language.isPrimaryAudioLanguage) {
                    return this.description || this.video.description;
                } else {
                    return this.description;
                }
            },
            getMetadata: function() {
                var metadata = _.clone(this.metadata);
                if(this.language.isPrimaryAudioLanguage) {
                    for(key in metadata) {
                        if(!metadata[key]) {
                            metadata[key] = this.video.metadata[key];
                        }
                    }
                }
                return metadata;
            }
        };

        return SubtitleVersionManager;
    }]);

}(this));
