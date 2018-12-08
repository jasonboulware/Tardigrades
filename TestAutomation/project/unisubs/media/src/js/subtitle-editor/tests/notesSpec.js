describe('The Notes Controller', function() {
    var EditorData;
    var SubtitleStorage;
    var $sce;
    var $scope;
    var $timeout;

    beforeEach(module('amara.SubtitleEditor.mocks'));
    beforeEach(module('amara.SubtitleEditor.notes'));

    beforeEach(inject(function($rootScope, $injector, $controller) {
        $scope = $rootScope.$new();
        $scope.scrollToBottom = jasmine.createSpy('scrollToBottom');
        $scope.fadeInLastNote = jasmine.createSpy('fadeInLastNote');

        $timeout = $injector.get('$timeout');
        $sce = $injector.get('$sce');
        EditorData = $injector.get('EditorData');
        EditorData.notes = [
            {
                user: 'ben',
                created: '3pm',
                body: 'note content'
            }
        ];
        EditorData.notesHeading = 'Note heading';
        SubtitleStorage = $injector.get('SubtitleStorage');

        $controller('NotesController', {
            $scope: $scope,
        });
    }));

    it('gets the heading from EditorData', function() {
        expect($scope.heading).toEqual(EditorData.notesHeading);
    });

    it('gets the notes from EditorData', function() {
        var noteData = _.map($scope.notes, function(note) {
            return {
                user: note.user,
                created: note.created,
                body: $sce.getTrustedHtml(note.body)
            }
        });
        expect(noteData).toEqual(EditorData.notes);
    });

    it('posts notes to the API', function() {
        $scope.newNoteText = 'new note';
        $scope.postNote();
        expect(SubtitleStorage.postNote).toHaveBeenCalledWith('new note');
    });

    it('converts linebreaks to <br>s', function() {
        $scope.newNoteText = 'line 1\nline2\nline3';
        $scope.postNote();
        var lastNote = $scope.notes[$scope.notes.length-1];
        expect($sce.getTrustedHtml(lastNote.body)).toEqual('line 1<br />line2<br />line3');
    });

    it('escapes html', function() {
        $scope.newNoteText = '<script>';
        $scope.postNote();
        var lastNote = $scope.notes[$scope.notes.length-1];
        expect($sce.getTrustedHtml(lastNote.body)).toEqual('&lt;script&gt;');
    });

    it('adds new notes to the list', function() {
        $scope.newNoteText = 'new note';
        $scope.postNote();
        expect($scope.notes.length).toEqual(2);
        // the note should be added to the end of the list
        expect($sce.getTrustedHtml($scope.notes[1].body)).toEqual('new note');
        expect($scope.notes[1].user).toEqual(EditorData.user_fullname);
        expect($scope.notes[1].created).toEqual('Just now');
    });

    it('clears the note text after adding a new', function() {
        $scope.newNoteText = 'new note';
        $scope.postNote();
        expect($scope.newNoteText).toEqual("");
    });

    it('scrolls to the bottom on startup', function() {
        $timeout.flush();
        expect($scope.scrollToBottom).toHaveBeenCalled();
    });

    it('scrolls to the bottom after posting a new', function() {
        $scope.scrollToBottom.calls.reset();
        $scope.newNoteText = 'new note';
        $scope.postNote();
        $timeout.flush();
        expect($scope.scrollToBottom).toHaveBeenCalled();
    });

    it('fades new notes in', function() {
        $scope.newNoteText = 'new note';
        $scope.postNote();
        $timeout.flush();
        expect($scope.fadeInLastNote).toHaveBeenCalled();
    });
});


