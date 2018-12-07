/*
 * Amara, universalsubtitles.org
 *
 * Copyright (C) 2018 Participatory Culture Foundation
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


var angular = angular || null;

(function() {
    var module = angular.module('amara.SubtitleEditor.toolbar', []);

    module.controller("ToolbarController", ['$scope', function($scope) {
        // Map menu names to the ID of the DOM element
        menuIds = {
            'timing': '.toolbox-menu-timing',
            'tools': '.toolbox-menu-subs'
        };
        // Map menu names to the ID of the icon for the menu
        menuIcons = {
            'timing': '.timingIcon',
            'tools': '.toolIcon'
        };
        currentMenu = null;

        function showMenu(name) {
            hideCurrentMenu();
            $(menuIds[name]).removeClass('hidden');
            $(menuIcons[name]).addClass('active');
            enableClickHandler();
            currentMenu = name;
        }

        function hideCurrentMenu() {
            $(menuIds[currentMenu]).addClass('hidden');
            $(menuIcons[currentMenu]).removeClass('active');
            disableClickHandler();
            currentMenu = null;
        }

        function toggleMenu(name) {
            if(currentMenu == name) {
                hideCurrentMenu();
            } else {
                showMenu(name);
            }
        }

        function enableClickHandler() {
            disableClickHandler();
            $(window).on('click.hide-toolbar', function($event) {
                hideCurrentMenu();
                $event.preventDefault();
                $event.stopPropagation();
            });
        }

        function disableClickHandler() {
            $(window).off('click.hide-toolbar');
        }

        $scope.onTimingToolIconClicked = function($event) {
            toggleMenu('timing');
            $event.preventDefault();
            $event.stopPropagation();
        };
        $scope.onSubtitleToolIconClicked = function($event) {
            toggleMenu('tools');
            $event.preventDefault();
            $event.stopPropagation();
        };
        $scope.canUndo = function() {
            return $scope.workingSubtitles.subtitleList.canUndo();
        }
        $scope.undoText = function() {
            return $scope.workingSubtitles.subtitleList.undoText();
        }
        $scope.onUndoClicked = function($event) {
            $scope.workingSubtitles.subtitleList.undo();
            $scope.$root.$emit('work-done');
        }
        $scope.canRedo = function() {
            return $scope.workingSubtitles.subtitleList.canRedo();
        }
        $scope.redoText = function() {
            return $scope.workingSubtitles.subtitleList.redoText();
        }
        $scope.onRedoClicked = function($event) {
            $scope.workingSubtitles.subtitleList.redo();
            $scope.$root.$emit('work-done');
        }

        $scope.$root.$on('dialog-opened', function() {
            hideCurrentMenu();
        });
    }]);

}).call(this);
