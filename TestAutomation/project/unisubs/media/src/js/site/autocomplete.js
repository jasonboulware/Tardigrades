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

$.fn.autocompleteTextbox = function(options) {
    this.each(function() {
        var field = $(this);
        var autocompleteList = $('<ul class="autocomplete">');
        var lastValue = null;
        var shown = false;
        var settings = $.extend({
            // default options
            queryParamName: 'query',
            url: field.data('autocompleteUrl'),
            extraFields: field.data('autocompleteExtraFields')
        }, options);


        field.on("keyup paste", function() {
            value = field.val();
            if(value == lastValue) {
                return;
            }
            data = {};
            data[settings.queryParamName] = value;
            if(settings.extraFields) {
                var form = field.closest('form');
                $.each(settings.extraFields.split(':'), function(i, name) {
                    data[name] = $('[name=' + name + ']', form).val();
                });
            }
            $.get(settings.url, data, function(responseData) {
                updateAutocomplete(responseData);
            });
            lastValue = value;
        }).on("focusout", function(evt) {
            hideAutocompleteList();
        }).on("focusin", function() {
            if($('li', autocompleteList).length > 0) {
                showAutocompleteList();
            }
        });

        function updateAutocomplete(responseData) {
            if(responseData.length == 0) {
                hideAutocompleteList();
                return;
            }
            showAutocompleteList();
            $('li', autocompleteList).remove();
            $.each(responseData, function(i, item) {
                var link = $('<a href="#">');
                link.text(item.label);
                var li = $('<li>').append(link);
                li.mousedown(function() {
                    field.val(item.value);
                    hideAutocompleteList();
                });
                autocompleteList.append(li);
            });
        }

        function showAutocompleteList() {
            if(!shown) {
                $(document.body).append(autocompleteList);
                shown = true;
                positionAutocompleteList();
                $(window).on('resize.autocomplete', positionAutocompleteList);
            }
        }

        function positionAutocompleteList() {
            if(field.closest('aside.modal').length) {
                autocompleteList.css('position', 'fixed');
            } else {
                autocompleteList.css('position', 'absolute');
            }
            offset = field.offset();
            autocompleteList.css('width', field.css('width'));
            autocompleteList.offset({
                left: offset.left,
                top: offset.top + field.height() + 5
            });
        }

        function hideAutocompleteList() {
            if(shown) {
                autocompleteList.detach();
                shown = false;
                $(window).off('resize.autocomplete');
            }
        }
    });
}

$(document).ready(function() {
    $('.autocomplete-textbox').autocompleteTextbox();
});

})();
