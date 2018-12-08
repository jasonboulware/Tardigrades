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
    function addURLParameter(url, parameter, value) {
        if (url.indexOf('?') == -1) {
            return url + ('?' + parameter + '=' + value)
        } else {
            return url + ('&' + parameter + '=' + value)
        }
    }

    Popcorn.amara = function(id, urls, primaryVideoType, options) {
        // For youtube, we need to alter the URL to enable controls and hide captions.
        if(primaryVideoType == 'Y') {
            if (options.controls) {
                urls[0] = addURLParameter(urls[0], 'controls', '1')    
            }
            
            if (options.hide_subtitles) {
                urls[0] = addURLParameter(urls[0], 'cc_load_policy', '3')
            }
        }
        return Popcorn.smart(id, urls, options);
    }
})(Popcorn);
