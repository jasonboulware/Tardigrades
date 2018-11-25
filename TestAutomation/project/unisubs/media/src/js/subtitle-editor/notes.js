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

var angular = angular || null;

(function() {
    var module = angular.module('amara.SubtitleEditor.notes', []);


    module.controller('NotesController', ["$sce", "$scope", "$timeout", "EditorData", "SubtitleStorage", function($sce, $scope, $timeout, EditorData, SubtitleStorage) {
        $scope.heading = EditorData.notesHeading;
        $scope.newNoteText = "";
        $scope.enabled = EditorData.notesEnabled;
	$scope.$root.$on('set-note-heading', function(evt, heading) {
            $scope.newNoteText = heading + "\n";
	});
        $scope.notes = _.map(EditorData.notes, function(note) {
            return {
                user: note.user,
                created: note.created,
                body: convertBody(note.body)
            }
        });

        function convertBody(body) {
            body = _.escape(body);
            body = body.replace(/\n/g, "<br />");
            body = body.replace(/^([\d\:\.]+)/, '<a class="note-link" data-target="$1" href="#">$1</a>');
            return $sce.trustAsHtml(body);
        }

        $scope.postNote = function() {
            if ($scope.newNoteText != "") {
                SubtitleStorage.postNote($scope.newNoteText);
                $scope.notes.push({
                    user: EditorData.user_fullname,
                    created: 'Just now',
                    body: convertBody($scope.newNoteText)
                });
                $scope.newNoteText = "";
                $timeout(function() {
                    $scope.scrollToBottom();
                    $scope.fadeInLastNote();
                });
            }
        }

        $scope.onPostClicked = function($event) {
            $scope.postNote();
            $event.preventDefault();
        }

        $scope.onNoteClicked = function($event) {
	    var node = $event.target;
	    var topLevelNode = $event.currentTarget;
	    while(node && node != topLevelNode) {
                if((node.tagName == 'A') && (node.className == "note-link") && (node.dataset) && (node.dataset.target)) {
		    $scope.$root.$emit('jump-to-time', node.dataset.target);
		}
                node = node.parentNode;
            }
        }

        $timeout(function() {
            $scope.scrollToBottom();
        });


    }]);

    module.directive('newNoteFocus', function() {
        return function(scope, elem, attr) {
            scope.$root.$on('set-focus', function(e, name) {
                if(name === attr.newNoteFocus) {
                    elem[0].focus();
                }
             });
        };
    });

    module.directive('noteScroller', function() {
        return function link($scope, elm, attrs) {
            // For some reason using ng-keydown at the HTML tag doesn't work.
            // Use jquery instead.
            $scope.scrollToBottom = function() {
                elm.scrollTop(elm.prop('scrollHeight'));
            }

            $scope.fadeInLastNote = function() {
                var lastNote = $('li:last', elm);
                lastNote.css({'opacity': '0.5'});
                lastNote.fadeTo(1000, 1.0);
            }
        };
    });
})(this);
