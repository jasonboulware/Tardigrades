/* Amara, universalsubtitles.org
 *
 * Copyright (C) 2013 Participatory Culture Foundation
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

    if($('html').attr('id') != 'team-settings-integration') {
        return;
    }

    // Track accounts that were enabled but are now disabled;
    var accountsToBeDisabled = {};

    function getAccountType(fieldset) {
        var classes = $(fieldset).attr('class').split(" ");
        for(var i=0; i < classes.length; i++) {
            if(classes[i] != 'disabled') {
                return classes[i];
            }
        }
        return "";
    }
    function accountWillBeDisabled() {
        for(var key in accountsToBeDisabled) {
            if(accountsToBeDisabled[key]) {
                return true;
            }
        }
        return false;
    }

    $('form input[type="checkbox"][name$="-enabled"]').change(function() {
        var fieldset = $(this).closest('fieldset');
        var accountFields = $('div.account-fields', fieldset);
        if(this.checked) {
            accountFields.slideDown();
            delete accountsToBeDisabled[getAccountType(fieldset)];
        } else {
            if(!fieldset.hasClass('disabled')) {
                accountsToBeDisabled[getAccountType(fieldset)] = true;
            }
            accountFields.slideUp();
        }
    });


    var form = $('form#external-accounts');
    form.submit(function(evt) {
        if(accountWillBeDisabled()) {
            evt.preventDefault();
            $('#confirm-delete-account-modal').openModal(evt);
            $('#confirm-delete-account-modal button.continue').click(function() {
                accountsToBeDisabled = {};
                form.submit();
            });

        }
    });

    function updateBrightcoveFeedInputs() {
        var cbx = $('#id_brightcove-feed_enabled');
        var feedFields = $('fieldset.brightcove fieldset.feed-fields input');
        if(cbx.prop('checked')) {
            feedFields.prop('disabled', false);
        } else {
            feedFields.prop('disabled', true);
        }
    }

    updateBrightcoveFeedInputs();
    $('#id_brightcove-feed_enabled').change(updateBrightcoveFeedInputs);

});

}(this));
