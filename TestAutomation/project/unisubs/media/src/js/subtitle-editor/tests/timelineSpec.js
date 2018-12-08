describe('TimelineController', function() {
    var subtitleList = null;
    var willSyncChangedSpy = null;
    var $scope = null;
    var subtitles = [];
    var MIN_DURATION = null;
    var VideoPlayer = null;

    beforeEach(module('amara.SubtitleEditor.timeline.controllers'));
    beforeEach(module('amara.SubtitleEditor.subtitles.models'));
    beforeEach(module('amara.SubtitleEditor.mocks'));

    beforeEach(inject(function(SubtitleList) {
        subtitleList = new SubtitleList();
        subtitleList.loadEmptySubs('en');
        for(var i = 0; i < 5; i++) {
            var sub = subtitleList.insertSubtitleBefore(null);
            subtitleList.updateSubtitleContent(sub, 'subtitle ' + i);
            subtitleList.updateSubtitleTime(sub, i * 1000, i * 1000 + 500);
        }
        // Insert a bunch of unsynced subs
        for(var i = 0; i < 5; i++) {
            subtitleList.insertSubtitleBefore(null);
        }
        subtitles = subtitleList.subtitles;
    }));

    beforeEach(inject(function($controller, $rootScope, $injector) {
        $scope = $rootScope;
        $scope.timelineShown = true;
        $scope.timeline = {
            shownSubtitle: null,
            currentTime: null,
            duration: null
        };
        $scope.workingSubtitles = {
            'subtitleList': subtitleList,
        }
        MIN_DURATION = 250;
        var controller = $controller('TimelineController', {
            $scope: $scope,
            MIN_DURATION: MIN_DURATION,
        });
        // in our tests, we make will sync happen by emitting work-done.  In
        // that case, the TimelineController also calls redrawSubtitles/redrawCanvas, so we
        // need to mock it.
        $scope.redrawCanvas = jasmine.createSpy('redrawCanvas');
        $scope.redrawSubtitles = jasmine.createSpy('redrawSubtitles');
        willSyncChangedSpy = jasmine.createSpy('willSyncChanged');
        $scope.$root.$on('will-sync-changed', willSyncChangedSpy);
        VideoPlayer = $injector.get('VideoPlayer');
    }));

    beforeEach(function() {
        jasmine.addMatchers({
            toHaveStartSub: function(util, customEqualityTesters) {
                return {
                    compare: function(actual, expected) {
                        var start = actual.calls.mostRecent().args[1].start;
                        return {
                            pass: util.equals(start, expected)
                        };
                    }
                };
            },
            toHaveEndSub: function(util, customEqualityTesters) {
                return {
                    compare: function(actual, expected) {
                        var end = actual.calls.mostRecent().args[1].end;
                        return {
                            pass: util.equals(end, expected)
                        };
                    }
                };
            }
        });
    });

    describe('Subtitle syncing', function() {
        it("Emits will-sync-changed on changes", function() {
            VideoPlayer.seek(1800);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy.calls.count()).toBe(1);
            // If the start/end subs stay the same, we shouldn't emit
            // will-sync again.
            VideoPlayer.seek(1900);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy.calls.count()).toBe(1);
        });

        it("Calculates start as the first sub after the current time", function() {
            VideoPlayer.seek(1800);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveStartSub(subtitles[2]);
            // If a subtitle occupies currentTime, then it should be the start sub
            VideoPlayer.seek(2300);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveStartSub(subtitles[2]);
        });

        it("Calculates end as the first sub before the current time", function() {
            VideoPlayer.seek(1800);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveEndSub(subtitles[1]);
            // If a subtitle occupies currentTime, then it should be the end sub
            VideoPlayer.seek(2300);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveEndSub(subtitles[2]);
        });

        it("syncs the start sub on sync-next-start-time", function() {
            VideoPlayer.seek(1800);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveStartSub(subtitles[2]);
            $scope.$emit("sync-next-start-time");
            expect(subtitleList.subtitles[2].startTime).toBe(1800);
        });

        it("syncs the end sub on sync-next-end-time", function() {
            VideoPlayer.seek(1800);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveEndSub(subtitles[1]);
            $scope.$emit("sync-next-end-time");
            expect(subtitleList.subtitles[1].endTime).toBe(1800);
        });

        it("respects MIN_DURATION when syncing start time", function() {
            VideoPlayer.seek(subtitles[2].endTime-1);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveStartSub(subtitles[2]);
            $scope.$emit("sync-next-start-time");
            expect(subtitleList.subtitles[2].startTime)
                .toBe(subtitles[2].endTime - MIN_DURATION);
        });

        it("respects MIN_DURATION when syncing end time", function() {
            VideoPlayer.seek(subtitles[2].startTime);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveStartSub(subtitles[2]);
            $scope.$emit("sync-next-end-time");
            expect(subtitleList.subtitles[2].endTime)
                .toBe(subtitles[2].startTime + MIN_DURATION);
        });
    });

    describe('Subtitle syncing after the end of synced subs', function() {
        it("Calculates start as the first sub without a start time", function() {
            VideoPlayer.seek(50000);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveStartSub(
                subtitleList.firstUnsyncedSubtitle());
            // Set startTime for the first unsynced sub
            subtitleList.updateSubtitleTime(
                subtitleList.firstUnsyncedSubtitle(),
                50000, -1);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveStartSub(
                subtitleList.secondUnsyncedSubtitle());
        });

        it("Calculates end as the last sub with a start time", function() {
            VideoPlayer.seek(50000);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveEndSub(subtitles[4]);
            // Set startTime for the first unsynced sub
            subtitleList.updateSubtitleTime(
                subtitleList.firstUnsyncedSubtitle(),
                50000, -1);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveEndSub(
                subtitleList.firstUnsyncedSubtitle());
        });

        it("syncs the first unysnced sub when the second's start time is set", function() {
            var firstIndex = subtitleList.getIndex(
                subtitleList.firstUnsyncedSubtitle());
            subtitleList.updateSubtitleTime(
                subtitleList.firstUnsyncedSubtitle(), 50000, -1);
            VideoPlayer.seek(50500);
            $scope.$emit('work-done');
            $scope.$emit('sync-next-start-time');
            expect(subtitles[firstIndex].endTime).toBe(50500);
            expect(subtitles[firstIndex + 1].startTime).toBe(50500);
        });

        it("respects MIN_DURATION when syncing end time", function() {
            var firstIndex = subtitleList.getIndex(
                subtitleList.firstUnsyncedSubtitle());
            VideoPlayer.seek(50000);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveStartSub(subtitles[firstIndex]);
            $scope.$emit('sync-next-start-time');
            $scope.$emit('sync-next-end-time');
            expect(subtitles[firstIndex].startTime).toBe(50000);
            expect(subtitles[firstIndex].endTime).toBe(50000 + MIN_DURATION);
        });

        it("respects MIN_DURATION when syncing start time", function() {
            var firstIndex = subtitleList.getIndex(
                subtitleList.firstUnsyncedSubtitle());
            VideoPlayer.seek(50000);
            $scope.$emit('work-done');
            expect(willSyncChangedSpy).toHaveStartSub(subtitles[firstIndex]);
            $scope.$emit('sync-next-start-time');
            expect(subtitles[firstIndex].startTime).toBe(50000);
            expect(willSyncChangedSpy).toHaveStartSub(subtitles[firstIndex + 1]);
            // If we sync the next start time to be the same time, we should
            // set the end time for the first sub, so that it has the minimum
            // duration.
            $scope.$emit('sync-next-start-time');
            expect(subtitles[firstIndex].endTime).toBe(50000 + MIN_DURATION);
            expect(subtitles[firstIndex+1].startTime).toBe(50000 +
                MIN_DURATION)
        });
    });
});

