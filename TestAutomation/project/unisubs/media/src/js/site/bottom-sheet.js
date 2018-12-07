/* Amara, universalsubtitles.org
 *
 * Copyright (C) 2015 Participatory Culture Foundation
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see
 * http://www.gnu.org/licenses/agpl-3.0.html.
 */
(function() {

/*
 * Define the bottomSheet object.  Other components use this to manipulate the
 * bottom sheet.
 *
 * See bottom-sheet.scss for an explanation of what we use it for.
 */

window.bottomSheet = {
    show: function() {
        $('.bottom-sheet').addClass('shown');
    },
    hide: function() {
        $('.bottom-sheet').removeClass('shown');
    },
    setHeading: function(text) {
        var heading = $('.bottom-sheet h3');
        if(heading.length == 0) {
            heading = $('<h3>').prependTo($('.bottom-sheet'));
        }
        heading.text(text);
    }
}

})();

