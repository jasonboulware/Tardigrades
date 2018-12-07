/*
 * Amara, universalsubtitles.org
 *
 * Copyright (C) 2017 Participatory Culture Foundation
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

/*
 * popcorn.amara.js -- Amara popcorn loader
 */

(function(Popcorn) {
    Popcorn.amara = function(id, urls, primaryVideoType, options) {
        // For youtube, we need to alter the URL to enable controls.
        if(primaryVideoType == 'Y' && options.controls) {
            if(urls[0].indexOf('?') == -1) {
                urls[0] += '?controls=1';
            } else {
                urls[0] += '&controls=1';
            }
        }
        return Popcorn.smart(id, urls, options);
    }
})(Popcorn);
