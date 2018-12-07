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

$(document).ready(function() {
    $('ul.thumb-list.bulk-mode').each(handleThumbListSelection);
});

function handleThumbListSelection() {
    var thumbList = $(this);
    var thumbnails = $('.thumb', thumbList);
    var checkboxes = $('.selection', thumbnails);
    var selectAll = $('.select-all-thumbs input').eq(0);
    var deselectAll = $('button.deselect-all');
    onSelectionChanged();
    thumbnails.click(onThumbClicked);
    selectAll.change(onSelectAllChange);
    deselectAll.click(onDeselectAll);

    function onThumbClicked(evt) {
        var checkbox = $('input.selection', this);
        if(checkbox.length > 0) {
            if(evt.target != checkbox[0]) {
                checkbox.prop('checked', !checkbox.prop('checked'));
                evt.preventDefault();
                evt.stopPropagation();
            }
            onSelectionChanged();
        }
    }

    function onSelectAllChange(evt) {
        checkboxes.prop('checked', selectAll.prop('checked'));
        onSelectionChanged();
    }

    function onDeselectAll(evt) {
        checkboxes.prop('checked', false);
        onSelectionChanged();
    }

    function setComponentsEnabled(selector, enabled) {
        if(enabled) {
            selector.removeClass('hidden');
        } else {
            selector.addClass('hidden');
        }
        $('input', selector).prop('disabled', !enabled);
    }

    function onSelectionChanged() {
        var selection = checkboxes.filter(':checked').closest('li');
        var checkCount = selection.length;
        setComponentsEnabled($('.needs-one-selected'), checkCount > 0);
        setComponentsEnabled($('.needs-multiple-selected'), checkCount > 1);
        setComponentsEnabled($('.needs-all-selected'),
                checkCount == checkboxes.length);
        selectAll.prop('checked', checkCount == checkboxes.length);
        updateButtomSheet(checkCount);
        thumbList.trigger('selectionChange', [selection]);
    }

    function updateButtomSheet(checkCount) {
        if(checkCount > 0) {
            bottomSheet.show();
        } else {
            bottomSheet.hide();
        }
    }
}

})();
