// Amara, universalsubtitles.org
//
// Copyright (C) 2015 Participatory Culture Foundation
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

var doSendAnalytics = function() {
    if (typeof sendAnalytics !== 'undefined')
	sendAnalytics.apply(this, Array.prototype.slice.call(arguments, 0));
};
var proamaraLink = '#proamara-link';

// Define JavaScript for each page variation of this experiment.
var pageVariations = [
    function() {}, // Original: Do nothing. This will render the default, Professional Services.
    function() { // Variation 1
	$(proamaraLink).html('Buy Subtitles');
    },
    function() { // Variation 2
	$(proamaraLink).html('Buy Captions');
    },
    function() { // Variation 3
	$(proamaraLink).html('Purchase Subtitles');
    }
];

$( document ).ready(function() {
    $(proamaraLink).click(function() {
	var destination = $(proamaraLink).attr('href');
	doSendAnalytics('outbound', 'click', 'pro.amara.conversion', { 'hitCallback': function() { document.location = destination; }});
	return false;
    }); 
});
