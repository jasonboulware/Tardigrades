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

goog.provide('unisubs.SRTWriter');

unisubs.SRTWriter.toSRT = function(jsonSubs) {
    var stringBuffer = new goog.string.StringBuffer();
    for (var i = 0; i < jsonSubs.length; i++)
        unisubs.SRTWriter.subToSrt_(jsonSubs[i], i, stringBuffer);
    return stringBuffer.toString();
};

unisubs.SRTWriter.subToSrt_ = function(sub, index, stringBuffer) {
    stringBuffer.
        append(index + 1).
        append("\n");
    unisubs.SRTWriter.writeSrtTimeLine_(sub, stringBuffer);
    stringBuffer.
        append(sub['text']).
        append("\n\n");
};

unisubs.SRTWriter.writeSrtTimeLine_ = function(sub, stringBuffer) {
    unisubs.SRTWriter.writeSrtTime_(sub['start_time'], stringBuffer);
    stringBuffer.append(' --> ');
    unisubs.SRTWriter.writeSrtTime_(sub['end_time'], stringBuffer);
    stringBuffer.append('\n');
};

unisubs.SRTWriter.writeSrtTime_ = function(milliseconds, stringBuffer) {
    // be paranoid if we passed float as a milliseconds
    milliseconds = parseInt(milliseconds);
    if (milliseconds == -1 || !goog.isDefAndNotNull(milliseconds)) {
        stringBuffer.append("99:59:59,000");
    }
    else {
    var time = Math.floor(milliseconds / 1000);
    var hours = ~~ (time / 3600);
    var minutes = ~~ ((time % 3600) / 60);
    var fraction = milliseconds % 1000;
    var p = goog.string.padNumber;
    var seconds = time % 60;
        stringBuffer.
            append(p(hours , 2)).
            append(':').
            append(p(minutes, 2)).
            append(':').
            append(p(seconds, 2)).
            append(',').
            append(p(fraction, 3));
    }
};
