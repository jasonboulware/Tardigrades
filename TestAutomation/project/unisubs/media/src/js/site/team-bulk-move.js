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

$.behaviors('form.team-bulk-move', handleTeamBulkMove);

function handleTeamBulkMove(form) {
    var projectField = $('select[name=project]', form);
    var teamField = $('select[name=new_team]', form);
    var projectChoices = $('option', projectField).clone();
    var selectAll = $('#select-all input', form);

    teamField.change(updateProjectChoices);
    updateProjectChoices();
    selectAll.change(onSelectAllChanged);
    $('.wrapper', form).click(onVideoClick);

    function updateProjectChoices() {
        var team = teamField.val();
        $('option', projectField).remove();
        projectChoices.each(function() {
            option = $(this);
            if(option.data('team') == 0 || option.data('team') == team) {
                projectField.append(option.clone());
            }
        });
    }

    function onVideoClick() {
        var li = $(this).closest('li');
        var input = $('input[name=team_videos]', this);

        if(input.prop('disabled')) {
            input.prop('disabled', false);
            li.addClass('selected');
        } else {
            input.prop('disabled', true);
            li.removeClass('selected');
        }
        if($('.video-card-list li').is(':not(.selected)')) {
            selectAll.prop('checked', false);
        } else {
            selectAll.prop('checked', true);
        }
    }

    function onSelectAllChanged() {
        if(selectAll.prop('checked')) {
            $('.video-card-list li', form).addClass('selected');
            $('input[name=team_videos]', form).prop('disabled', false);
        } else {
            $('.video-card-list li', form).removeClass('selected');
            $('input[name=team_videos]', form).prop('disabled', true);
        }
    }
}

})();
