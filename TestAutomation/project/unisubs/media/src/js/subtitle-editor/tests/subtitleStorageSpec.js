describe('The SubtitleStorage service', function() {
    var $httpBackend;
    var $rootScope;
    var videoId;
    var languageCode;
    var SubtitleStorage;
    var subtitlesURL;
    var actionsURL;
    var notesURL;


    beforeEach(module('amara.SubtitleEditor.mocks'));
    beforeEach(module('amara.SubtitleEditor.subtitles.services'));

    beforeEach(inject(function ($injector, EditorData) {
        $httpBackend = $injector.get('$httpBackend');
        $rootScope = $injector.get('$rootScope');
        SubtitleStorage = $injector.get('SubtitleStorage');
        videoId = EditorData.video.id;
        languageCode = EditorData.editingVersion.languageCode;

        subtitlesURL = ('/api/videos/' + videoId + '/languages/' +
            languageCode + '/subtitles/');
        actionsURL = subtitlesURL + 'actions/';
        notesURL = subtitlesURL + 'notes/';
    }));

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });

    it('saves subtitles with actions', function() {
        SubtitleStorage.saveSubtitles('dfxp-string', 'title', 1000, 'description',
            'metadata', true, 'test-action', 'dfxp', false);
        $httpBackend.expectPOST(subtitlesURL, {
            video: videoId,
            language: languageCode,
            subtitles: 'dfxp-string',
            sub_format: 'dfxp',
            title: 'title',
            duration: 1000,
            description: 'description',
            origin: 'editor',
            metadata: 'metadata',
            action: 'test-action',
        }).respond('200', '');
        $rootScope.$digest();
        $httpBackend.flush();
    });

    it('saves uploaded subtitles with actions', function() {
        SubtitleStorage.saveSubtitles('dfxp-string', 'title', 1000, 'description',
            'metadata', true, 'test-action', 'dfxp', true);
        $httpBackend.expectPOST(subtitlesURL, {
            video: videoId,
            language: languageCode,
            subtitles: 'dfxp-string',
            sub_format: 'dfxp',
            title: 'title',
            duration: 1000,
            description: 'description',
            origin: 'upload',
            metadata: 'metadata',
            action: 'test-action',
        }).respond('200', '');
        $rootScope.$digest();
        $httpBackend.flush();
    });

    it('performs actions', function() {
        SubtitleStorage.performAction('action-name');
        $httpBackend.expectPOST(actionsURL, {
            'action': 'action-name'
        }).respond('200', '');
        $rootScope.$digest();
        $httpBackend.flush();
    });

    it('posts notes', function() {
        SubtitleStorage.postNote('note text');
        $httpBackend.expectPOST(notesURL, {
            'body': 'note text'
        }).respond('200', '');
        $rootScope.$digest();
        $httpBackend.flush();
    });
});

