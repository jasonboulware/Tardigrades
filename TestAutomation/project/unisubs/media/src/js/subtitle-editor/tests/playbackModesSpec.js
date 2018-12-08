describe('The playback mode controller', function() {
    var EditorData;
    var VideoPlayer;
    var PreferencesService;
    var $timeout;
    var $rootScope;
    var $scope;
    var playbackModes;

    function simulateContinuousTyping(msToSimulate) {
        var msPerStep = 200;
        var steps = Math.floor(msToSimulate / msPerStep);
        for(var i = 0; i < steps; ++i) {
            $rootScope.$emit('text-edit-keystroke');
            if(VideoPlayer._playing) {
                VideoPlayer._currentTime += msPerStep;
            }
            $timeout.simulateTime(msPerStep);
        }
    }

    function simulateTimeWithoutKeystrokes(msToSimulate) {
        var msPerStep = 200;
        var steps = Math.floor(msToSimulate / msPerStep);
        for(var i = 0; i < steps; ++i) {
            if(VideoPlayer._playing) {
                VideoPlayer._currentTime += msPerStep;
            }
            $timeout.simulateTime(msPerStep);
        }
    }

    beforeEach(module('amara.SubtitleEditor.mocks'));
    beforeEach(module('amara.SubtitleEditor.video.controllers'));

    beforeEach(inject(function($injector, $controller) {
        EditorData = $injector.get('EditorData');

        EditorData.playbackModes = [
            {
                'id': 0,
                'idStr': 'magic'
            },
            {
                'id': 1,
                'idStr': 'standard'
            },
            {
                'id': 2,
                'idStr': 'beginner'
            }
        ];

        playbackModes = {};
        $.each(EditorData.playbackModes, function(index, mode) {
            playbackModes[mode.idStr] = mode;
        });

        EditorData.preferences.playbackModeId = playbackModes.standard.id;

        VideoPlayer = $injector.get('VideoPlayer');
        PreferencesService = $injector.get('PreferencesService');
        $timeout = $injector.get('$timeout');
        $rootScope = $injector.get('$rootScope');
        $scope = $rootScope.$new();
        $scope.timelineShown = false;
        $controller('PlaybackModeController', {$scope: $scope});
        $scope.$digest();
        VideoPlayer.pause.calls.reset();
    }));

    it('sets playback mode to standard when constructed', function() {
        expect($scope.playbackMode).toBe(playbackModes.standard);
    });

    it('pauses when playback mode is switched', function() {
        $scope.playbackMode = playbackModes.magic;
        $scope.$digest();
        expect(VideoPlayer.pause).toHaveBeenCalled();
    });

    describe('beginner mode', function() {
        beforeEach(function() {
            $scope.playbackMode = playbackModes.beginner;
            $scope.$digest();
            VideoPlayer.pause.calls.reset();
        });

        it('sets the playback mode via the preference service', function() {
            expect(PreferencesService.setPlaybackMode).toHaveBeenCalledWith(playbackModes.beginner.id);
        });

        it('pauses after 4 seconds of playback', function() {
            VideoPlayer.play();
            $rootScope.$emit('video-playback-changes');

            simulateTimeWithoutKeystrokes(4000);
            expect(VideoPlayer.pause).toHaveBeenCalled();
        });

        it('pauses after 4 seconds after play/pause/play', function() {
            VideoPlayer.play();
            $rootScope.$emit('video-playback-changes');
            simulateTimeWithoutKeystrokes(1000);
            expect(VideoPlayer.pause).not.toHaveBeenCalled();

            VideoPlayer.pause();
            VideoPlayer.pause.calls.reset();
            $rootScope.$emit('video-playback-changes');

            VideoPlayer.play();
            $rootScope.$emit('video-playback-changes');
            simulateTimeWithoutKeystrokes(3000);
            expect(VideoPlayer.pause).not.toHaveBeenCalled();

            simulateTimeWithoutKeystrokes(3000);
            expect(VideoPlayer.pause).toHaveBeenCalled();
        });
    });

    describe('magic mode', function() {
        beforeEach(function() {
            $scope.playbackMode = playbackModes.magic;
            $scope.$digest();
            VideoPlayer.pause.calls.reset();
        });

        it('sets the playback mode via the preference service', function() {
            expect(PreferencesService.setPlaybackMode).toHaveBeenCalledWith(playbackModes.magic.id);
        });

        it('pauses playback after 4 seconds of typing', function() {
            VideoPlayer.play();
            simulateContinuousTyping(4000);
            expect(VideoPlayer.pause).toHaveBeenCalled();
        });
        
        it('does not pause without 4 seconds of typing', function() {
            VideoPlayer.play();
            simulateTimeWithoutKeystrokes(4000);
            expect(VideoPlayer.pause).not.toHaveBeenCalled();
        });

        it('does not pause if the user starts typing, but then stops for > 1 second', function() {
            VideoPlayer.play();
            simulateContinuousTyping(1000);
            simulateTimeWithoutKeystrokes(4000);
            expect(VideoPlayer.pause).not.toHaveBeenCalled();
        });

        it('pauses playback after intermittent typing, then 4 seconds of straight typing', function() {
            VideoPlayer.play();
            simulateContinuousTyping(1000);
            expect(VideoPlayer.pause).not.toHaveBeenCalled();
            simulateTimeWithoutKeystrokes(800);
            expect(VideoPlayer.pause).not.toHaveBeenCalled();
            simulateContinuousTyping(4000);
            expect(VideoPlayer.pause).toHaveBeenCalled();
        });

        it('seeks back 3 seconds and restarts playback once typing stops for a second after a magic pause', function() {
            VideoPlayer.play();
            simulateContinuousTyping(3000);
            expect(VideoPlayer.pause).not.toHaveBeenCalled();
            simulateContinuousTyping(1000);
            expect(VideoPlayer.pause).toHaveBeenCalled();

            var magicPauseStartTime = VideoPlayer._currentTime;
            VideoPlayer.play.calls.reset();

            simulateTimeWithoutKeystrokes(500);
            expect(VideoPlayer.play).not.toHaveBeenCalled();

            simulateContinuousTyping(2000);
            expect(VideoPlayer.play).not.toHaveBeenCalled();
            simulateTimeWithoutKeystrokes(1000);
            expect(VideoPlayer.seek).toHaveBeenCalledWith(magicPauseStartTime - 3000);
            expect(VideoPlayer.play).toHaveBeenCalled();
        });

        it('does not resume from a manual pause', function() {
            VideoPlayer.play();
            simulateContinuousTyping(3000);
            VideoPlayer.pause();
            VideoPlayer.play.calls.reset();
            simulateContinuousTyping(3000);
            simulateTimeWithoutKeystrokes(2000);
            expect(VideoPlayer.seek).not.toHaveBeenCalled();
            expect(VideoPlayer.play).not.toHaveBeenCalled();
        });
    });
});
