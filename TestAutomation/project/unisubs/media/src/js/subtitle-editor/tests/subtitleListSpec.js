describe('Test the SubtitleList class', function() {
    var subtitleList = null;

    beforeEach(module('amara.SubtitleEditor.subtitles.models'));
    beforeEach(module('amara.SubtitleEditor.mocks'));

    beforeEach(inject(function(SubtitleList) {
        subtitleList = new SubtitleList();
        subtitleList.loadEmptySubs('en');

        jasmine.addMatchers({
            toHaveTimes: function(util, customEqualityTesters) {
                return {
                    compare: function(actual, expected) {
                        var result = {};
                        result.pass = util.equals([actual.startTime, actual.endTime], expected);
                        return result;
                    }
                };
            }
        });
    }));

    // This is the best way to track changes to the list.  It intercepts all
    // calls to the low-level mutator functions and updates a list of changes
    // based on them
    function trackChanges(subtitleList) {
        var origInsertSubtitles = subtitleList._insertSubtitle;
        var origRemoveSubtitles = subtitleList._removeSubtitle;
        var origUpdateSubtitles = subtitleList._updateSubtitle;

        var changes = [];

        spyOn(subtitleList, '_insertSubtitle').and.callFake(function(index, attrs) {
            changes.push(['insert', index, attrs]);
            return origInsertSubtitles.call(subtitleList, index, attrs);
        });
        spyOn(subtitleList, '_removeSubtitle').and.callFake(function(index, attrs) {
            changes.push(['remove', index, attrs]);
            return origRemoveSubtitles.call(subtitleList, index, attrs);
        });
        spyOn(subtitleList, '_updateSubtitle').and.callFake(function(index, attrs) {
            changes.push(['update', index, attrs]);
            return origUpdateSubtitles.call(subtitleList, index, attrs);
        });

        return changes;
    }

    describe('low level change functions', function() {
        it('inserts subtitles', function() {
            var sub1 = subtitleList._insertSubtitle(0);
            var sub2 = subtitleList._insertSubtitle(0, {
                startTime: 0,
                endTime: 100,
                region: 'top',
                content: 'test-content'
            });
            var sub3 = subtitleList._insertSubtitle(2, {startOfParagraph: true, content: 'test-content2'});
            expect(subtitleList.subtitles).toEqual([sub2, sub1, sub3]);
            expect(subtitleList.syncedCount).toEqual(1);

            expect(sub1).toHaveTimes([-1, -1]);
            expect(sub1.region).toEqual(undefined);
            expect(sub1.startOfParagraph).toEqual(true); // sub1 was the first subtitle, so startOfParagraph is true 
            expect(sub1.markdown).toEqual('');

            expect(sub2).toHaveTimes([0, 100]);
            expect(sub2.region).toEqual('top');
            expect(sub2.startOfParagraph).toEqual(true);
            expect(sub2.markdown).toEqual('test-content');

            expect(sub3).toHaveTimes([-1, -1]);
            expect(sub3.region).toEqual(undefined);
            expect(sub3.startOfParagraph).toEqual(true);
            expect(sub3.markdown).toEqual('test-content2');
        });

        it('updates subtitles', function() {
            subtitleList._insertSubtitle(0);
            var sub = subtitleList._insertSubtitle(1);

            subtitleList._updateSubtitle(1, {
                startTime: 500,
                endTime: 1000,
                region: 'top',
                startOfParagraph: true,
                content: 'test'
            });

            expect(sub.startTime).toEqual(500);
            expect($(sub.node).attr('begin')).toEqual('500');
            expect(sub.endTime).toEqual(1000);
            expect($(sub.node).attr('end')).toEqual('1000');
            expect(sub.region).toEqual('top');
            expect($(sub.node).attr('region')).toEqual('top');
            expect(sub.markdown).toEqual('test');
            expect($(sub.node).text()).toEqual('test');
        });

        it('removes subtitles', function() {
            var sub1 = subtitleList._insertSubtitle(0, {startTime: 500, endTime: 1000});
            var sub2 = subtitleList._insertSubtitle(1);
            var sub3 = subtitleList._insertSubtitle(2);
            expect(subtitleList.subtitles).toEqual([sub1, sub2, sub3]);
            expect(subtitleList.syncedCount).toEqual(1);

            subtitleList._removeSubtitle(1);
            expect(subtitleList.subtitles).toEqual([sub1, sub3]);
            expect(subtitleList.syncedCount).toEqual(1);

            subtitleList._removeSubtitle(1);
            expect(subtitleList.subtitles).toEqual([sub1]);
            expect(subtitleList.syncedCount).toEqual(1);

            subtitleList._removeSubtitle(0);
            expect(subtitleList.subtitles).toEqual([]);
            expect(subtitleList.syncedCount).toEqual(0);
        });

        it('supports bulk changes', function() {
            subtitleList._bulkChange([
                [subtitleList._insertSubtitle, 0, {startTime: 0, endTime: 100}],
                [subtitleList._insertSubtitle, 1, {startTime: 100, endTime: 200}],
                [subtitleList._insertSubtitle, 2, {startTime: 200, endTime:300}],
                [subtitleList._updateSubtitle, 2, {content: 'test-content'}],
                [subtitleList._removeSubtitle, 1, {}],
            ]);
            expect(subtitleList.subtitles.length).toEqual(2);
            expect(subtitleList.subtitles[0]).toHaveTimes([0, 100]);
            expect(subtitleList.subtitles[1]).toHaveTimes([200, 300]);
            expect(subtitleList.subtitles[1].markdown).toEqual('test-content');
        });


        it('invokes change callbacks', function() {
            var handler = jasmine.createSpyObj('handler', ['onChange']);
            subtitleList.addChangeCallback(handler.onChange);

            var sub = subtitleList._insertSubtitle(0);
            subtitleList._invokeChangeCallbacks();
            expect(handler.onChange).toHaveBeenCalledWith([{
                type: 'insert',
                subtitle: sub,
                before: null,
            }]);

            handler.onChange.calls.reset();
            var sub2 = subtitleList._insertSubtitle(0);
            subtitleList._invokeChangeCallbacks();
            expect(handler.onChange).toHaveBeenCalledWith([{
                type: 'insert',
                subtitle: sub2,
                before: sub
            }]);

            handler.onChange.calls.reset();
            subtitleList.updateSubtitleTime(sub, 500, 1500);
            subtitleList._invokeChangeCallbacks();
            expect(handler.onChange).toHaveBeenCalledWith([{
                type: 'update',
                subtitle: sub,
            }]);

            handler.onChange.calls.reset();
            subtitleList.updateSubtitleTime(sub, 500, 1500);
            subtitleList._invokeChangeCallbacks();
            expect(handler.onChange).toHaveBeenCalledWith([{
                type: 'update',
                subtitle: sub,
            }]);

            handler.onChange.calls.reset();
            subtitleList.updateSubtitleContent(sub, 'content');
            subtitleList._invokeChangeCallbacks();
            expect(handler.onChange).toHaveBeenCalledWith([{
                type: 'update',
                subtitle: sub,
            }]);

            handler.onChange.calls.reset();
            subtitleList._removeSubtitle(1);
            subtitleList._invokeChangeCallbacks();
            expect(handler.onChange).toHaveBeenCalledWith([{
                type: 'remove',
                subtitle: sub,
            }]);

            handler.onChange.calls.reset();
            subtitleList.removeChangeCallback(handler.onChange);
            var sub3 = subtitleList._insertSubtitle(0);
            subtitleList.updateSubtitleTime(sub3, 500, 1500);
            subtitleList.updateSubtitleContent(sub3, 'content');
            subtitleList._removeSubtitle(0);
            expect(handler.onChange.calls.count()).toEqual(0);
        });

    });

    it('updates timings', function() {
        var sub1 = subtitleList.insertSubtitleBefore(null);
        var sub2 = subtitleList.insertSubtitleBefore(null);
        expect(subtitleList.syncedCount).toEqual(0);
        subtitleList.updateSubtitleTime(sub1, 500, 1500);
        expect(sub1).toHaveTimes([500, 1500]);
        expect(subtitleList.syncedCount).toEqual(1);
        subtitleList.updateSubtitleTime(sub1, 1000, 1500);
        expect(sub1).toHaveTimes([1000, 1500]);
        expect(subtitleList.syncedCount).toEqual(1);
        subtitleList.updateSubtitleTime(sub2, 2000, 2500);
        expect(sub2).toHaveTimes([2000, 2500]);
        expect(subtitleList.syncedCount).toEqual(2);
    });

    it('updates multiple timings at once', function() {
        var sub1 = subtitleList.insertSubtitleBefore(null);
        var sub2 = subtitleList.insertSubtitleBefore(null);
        subtitleList.updateSubtitleTimes([
            {
                subtitle: sub1,
                startTime: 100,
                endTime: 200
            },
            {
                subtitle: sub2,
                startTime: 200,
                endTime: 300
            },
        ]);
        expect(sub1).toHaveTimes([100, 200]);
        expect(sub2).toHaveTimes([200, 300]);
        expect(subtitleList.syncedCount).toEqual(2);
    });

    it('clears all timings', function() {
        var sub1 = subtitleList.insertSubtitleBefore(null);
        var sub2 = subtitleList.insertSubtitleBefore(null);
        subtitleList.updateSubtitleTimes([
            {
                subtitle: sub1,
                startTime: 100,
                endTime: 200
            },
            {
                subtitle: sub2,
                startTime: 200,
                endTime: 300
            },
        ]);
        subtitleList.clearAllTimings();
        expect(sub1).toHaveTimes([-1, -1]);
        expect(sub2).toHaveTimes([-1, -1]);
        expect(subtitleList.syncedCount).toEqual(0);
    });

    it('clears all text', function() {
        var sub1 = subtitleList.insertSubtitleBefore(null);
        var sub2 = subtitleList.insertSubtitleBefore(null);
        subtitleList.updateSubtitleContent(sub1, 'test');
        subtitleList.updateSubtitleContent(sub2, 'test2');
        subtitleList.clearAllText();
        expect(sub1.markdown).toEqual('');
        expect(sub2.markdown).toEqual('');
    });

    it('should get and update regions', function() {
        var sub = subtitleList.insertSubtitleBefore(null);
        expect(sub.region).toEqual(undefined);
        subtitleList.updateSubtitleRegion(sub, 'top');
        expect($(sub.node).attr('region')).toEqual('top');
        expect(sub.region).toEqual('top');

        subtitleList.updateSubtitleRegion(sub, undefined);
        expect($(sub.node).attr('region')).toEqual(undefined);
        expect(sub.region).toEqual(undefined);
    });

    describe('insertBefore unsynced subtitle', function() {
        it('appends at the end if otherSubtitle is null', function() {
            var sub1 = subtitleList.insertSubtitleBefore(null);
            var sub2 = subtitleList.insertSubtitleBefore(null);
            expect(subtitleList.subtitles).toEqual([sub1, sub2]);
        });

        it('inserts unsynced subtitles otherSubtitle is unsynced', function() {
            var sub1 = subtitleList.insertSubtitleBefore(null);
            var sub2 = subtitleList.insertSubtitleBefore(sub1);
            expect(subtitleList.subtitles).toEqual([sub2, sub1]);
            expect(sub2.startTime).toEqual(-1);
            expect(sub2.endTime).toEqual(-1);
        });
    });

    describe('insertBefore with two synced subtitles', function() {
        var sub1, sub2;
        beforeEach(function() {
            sub1 = subtitleList._insertSubtitle(0);
            sub2 = subtitleList._insertSubtitle(1);
        });

        it('inserts a 1 second subtitle in the between otherSubtitle and the previous subtitle, if there is at least a 1 second gap', function() {
            subtitleList.updateSubtitleTime(sub1, 0, 1000);
            subtitleList.updateSubtitleTime(sub2, 5000, 6000);
            var newSub = subtitleList.insertSubtitleBefore(sub2);

            expect(subtitleList.subtitles).toEqual([sub1, newSub, sub2]);
            expect(newSub).toHaveTimes([2500, 3500]);
        });

        it('adjusts the end time of the previous subtitle to make room for the new subtitle, if there is less than a 1 second gap', function() {
            subtitleList.updateSubtitleTime(sub1, 0, 5500);
            subtitleList.updateSubtitleTime(sub2, 6000, 7000);
            var newSub = subtitleList.insertSubtitleBefore(sub2);

            expect(subtitleList.subtitles).toEqual([sub1, newSub, sub2]);
            expect(sub1).toHaveTimes([0, 5000]);
            expect(newSub).toHaveTimes([5000, 6000]);
        });

        it('splits the time between the previous subtitle and the new subtitle if there is less than 2 seconds for them both', function() {
            subtitleList.updateSubtitleTime(sub1, 0, 1000);
            subtitleList.updateSubtitleTime(sub2, 1500, 2500);
            var newSub = subtitleList.insertSubtitleBefore(sub2);

            expect(subtitleList.subtitles).toEqual([sub1, newSub, sub2]);
            expect(sub1).toHaveTimes([0, 750]);
            expect(newSub).toHaveTimes([750, 1500]);
        });

        it('never lengthens the previous subtitle', function() {
            subtitleList.updateSubtitleTime(sub1, 0, 400);
            subtitleList.updateSubtitleTime(sub2, 1000, 7000);
            var newSub = subtitleList.insertSubtitleBefore(sub2);
            // when we insert the subtitle, don't split the time since that
            // would cause sub1 to be longer than before.  Instead just newSub
            // should just take up the entire 2 second gap.

            expect(subtitleList.subtitles).toEqual([sub1, newSub, sub2]);
            expect(sub1).toHaveTimes([0, 400]);
            expect(newSub).toHaveTimes([400, 1000]);
        });
    });

    describe('insertBefore with first synced subtitle', function() {
        var sub1;
        beforeEach(function() {
            sub1 = subtitleList.insertSubtitleBefore(null);
        });

        it('inserts a 1 second subtitle in the middle of the initial empty time, if there is at least a 1 second gap', function() {
            subtitleList.updateSubtitleTime(sub1, 2000, 5000);
            var newSub = subtitleList.insertSubtitleBefore(sub1);

            expect(subtitleList.subtitles).toEqual([newSub, sub1]);
            expect(newSub).toHaveTimes([500, 1500]);
        });

        it('adjusts the start time of the next subtitle to make room for the new subtitle, if there is less than a 1 second gap', function() {
            subtitleList.updateSubtitleTime(sub1, 700, 7000);
            var newSub = subtitleList.insertSubtitleBefore(sub1);

            expect(subtitleList.subtitles).toEqual([newSub, sub1]);
            expect(newSub).toHaveTimes([0, 1000]);
            expect(sub1).toHaveTimes([1000, 7000]);
        });

        it('splits the time between the next subtitle and the new subtitle if there is less than 2 seconds for them both', function() {
            subtitleList.updateSubtitleTime(sub1, 0, 800);
            var newSub = subtitleList.insertSubtitleBefore(sub1);

            expect(subtitleList.subtitles).toEqual([newSub, sub1]);
            expect(newSub).toHaveTimes([0, 400]);
            expect(sub1).toHaveTimes([400, 800]);
        });

        it('never lengthens the next subtitle', function() {
            subtitleList.updateSubtitleTime(sub1, 800, 1000);
            var newSub = subtitleList.insertSubtitleBefore(sub1);
            // when we insert the subtitle, don't split the time since that
            // would cause sub1 to be longer than before.  Instead just newSub
            // should just take up the entire 2 second gap.

            expect(subtitleList.subtitles).toEqual([newSub, sub1]);
            expect(newSub).toHaveTimes([0, 800]);
            expect(sub1).toHaveTimes([800, 1000]);
        });
    });

    describe('split subtitles', function() {
        it('splits subtitles', function() {
            var sub1 = subtitleList.insertSubtitleBefore(null);
            subtitleList.updateSubtitleTime(sub1, 0, 8000);

            var sub2 = subtitleList.splitSubtitle(sub1, 'foo', 'bar');

            expect(sub1).toHaveTimes([0, 4000]);
            expect(sub1.markdown).toEqual('foo');
            expect(sub2).toHaveTimes([4000, 8000]);
            expect(sub2.markdown).toEqual('bar');
            expect(subtitleList.syncedCount).toEqual(2);
            expect(subtitleList.firstSubtitle()).toBe(sub1);
            expect(subtitleList.nextSubtitle(sub1)).toBe(sub2);
            expect(subtitleList.nextSubtitle(sub2)).toBe(null);

            var sub3 = subtitleList.splitSubtitle(sub2, 'b', 'ar');

            expect(sub2).toHaveTimes([4000, 6000]);
            expect(sub2.markdown).toEqual('b');
            expect(sub3).toHaveTimes([6000, 8000]);
            expect(sub3.markdown).toEqual('ar');
            expect(subtitleList.syncedCount).toEqual(3);
            expect(subtitleList.firstSubtitle()).toBe(sub1);
            expect(subtitleList.nextSubtitle(sub1)).toBe(sub2);
            expect(subtitleList.nextSubtitle(sub2)).toBe(sub3);
            expect(subtitleList.nextSubtitle(sub3)).toBe(null);
        });

        it('splits unsynced subtitles', function() {
            var sub = subtitleList.insertSubtitleBefore(null);
            var sub2 = subtitleList.splitSubtitle(sub, 'one', 'two');

            expect(sub).toHaveTimes([-1, -1]);
            expect(sub2).toHaveTimes([-1, -1]);
            expect(sub.markdown).toEqual('one')
            expect(sub2.markdown).toEqual('two')
            expect(subtitleList.syncedCount).toEqual(0);
        });

        it('preserves region when splitting subtitles', function() {
            var sub1 = subtitleList.insertSubtitleBefore(null);
            subtitleList.updateSubtitleTime(sub1, 0, 8000);
            subtitleList.updateSubtitleRegion(sub1, 'top');

            var sub2 = subtitleList.splitSubtitle(sub1, 'foo', 'bar');
            expect(sub2.region).toBe('top');
        });
    });

    describe('copyTiming', function() {
        var referenceSubs;
        beforeEach(inject(function(SubtitleList) {
            referenceSubs = new SubtitleList();
            referenceSubs.loadEmptySubs('en');
            referenceSubs._insertSubtitle(0, {
                startTime: 100,
                endTime: 200,
                startOfParagraph: true

            });
            referenceSubs._insertSubtitle(1, {
                startTime: 200,
                endTime: 300,
                startOfParagraph: true
            });
            referenceSubs._changesDone('insert');

            subtitleList.insertSubtitleBefore(null);
            subtitleList.insertSubtitleBefore(null);
        }));

        it('copies timings from another subtitleList', function() {
            subtitleList.copyTimingsFrom(referenceSubs);
            expect(subtitleList.subtitles[0]).toHaveTimes([100, 200]);
            expect(subtitleList.subtitles[1]).toHaveTimes([200, 300]);
        });

        it('copies paragraph starts too', function() {
            subtitleList.copyTimingsFrom(referenceSubs);
            expect(subtitleList.subtitles[0].startOfParagraph).toEqual(true);
            expect(subtitleList.subtitles[1].startOfParagraph).toEqual(true);
        });

        it('unsets timings past the last subtitle of the reference subs', function() {
            subtitleList.insertSubtitleBefore(null);
            _.each(subtitleList.subtitles, function(sub, i) {
                subtitleList.updateSubtitleTime(sub, i * 100, i * 100 + 50);
            });
            subtitleList.copyTimingsFrom(referenceSubs);
            expect(subtitleList.subtitles[2]).toHaveTimes([-1, -1]);
        });
    });

    it('shift subtitles forward', function() {
        subtitleList._insertSubtitle(0, {
            startTime: 100,
            endTime: 200
        });
        subtitleList._insertSubtitle(1, {
            startTime: 300,
            endTime: 400
        });
        subtitleList._insertSubtitle(2, {
            startTime: 500,
            endTime: 600
        });
        subtitleList._insertSubtitle(3, {});
        subtitleList._changesDone('init');

        var changes = trackChanges(subtitleList);

        subtitleList.shiftForward(350, 1000);
        // Subtitle 0 should be unchanged, since it's before start time
        // Subtitle 1 should be lengthed, since it overlaps start time
        // Subtitle 2 should be shifted forward in time, since it's after start time
        // Subtitle 3 should be unchanged, since it's unsynced
        expect(changes).toEqual([
                ['update', 1, {endTime: 1400}],
                ['update', 2, {startTime: 1500, endTime: 1600}],
        ]);
    });

    it('shift subtitles backward', function() {
        subtitleList._insertSubtitle(0, {
            startTime: 100,
            endTime: 200
        });
        subtitleList._insertSubtitle(1, {
            startTime: 300,
            endTime: 400
        });
        subtitleList._insertSubtitle(2, {
            startTime: 500,
            endTime: 600
        });
        subtitleList._insertSubtitle(3, {
            startTime: 700,
            endTime: 800
        });
        subtitleList._insertSubtitle(4, {
            startTime: 900,
            endTime: 1000
        });
        subtitleList._insertSubtitle(5, {});
        subtitleList._changesDone('init');

        var changes = trackChanges(subtitleList);

        subtitleList.shiftBackward(350, 400);
        // Subtitle 0 should be unchanged, since it's before the removed time
        // Subtitle 1 should be shortened, since it's end time is inside the removed time
        // Subtitle 2 should be removed, since all of it is contained in the removed time
        // Subtitle 3 should be shortened and moved back, since it's start time is inside the removed time
        // Subtitle 4 should be moved back, since it's after the removed time
        // Subtitle 5 should be unchanged, since it's unsynced
        expect(changes).toEqual([
                ['update', 1, {endTime: 350}],
                ['remove', 2, {}], // Note, this decriments all indexs after 2
                ['update', 2, {startTime: 350, endTime: 400}],
                ['update', 3, {startTime: 500, endTime: 600}],
        ]);
    });

    describe('undo', function() {
        it('can undo operations', function() {
            var sub = subtitleList._insertSubtitle(0, {
                startTime: 0, endTime: 100, content: 'test-content'
            });
            subtitleList._resetUndo();

            subtitleList.splitSubtitle(sub, 'test', 'content');
            expect(subtitleList.canUndo()).toEqual(true);
            subtitleList.undo();

            expect(subtitleList.subtitles.length).toEqual(1);
            expect(subtitleList.subtitles[0]).toHaveTimes([0, 100]);
            expect(subtitleList.subtitles[0].markdown).toEqual('test-content');
            expect(subtitleList.canUndo()).toEqual(false);
        });

        it('can redo operations', function() {
            var sub = subtitleList._insertSubtitle(0, {
                startTime: 0, endTime: 100, content: 'test-content'
            });
            subtitleList._resetUndo();

            subtitleList.splitSubtitle(sub, 'test', 'content');
            subtitleList.undo();

            expect(subtitleList.canRedo()).toEqual(true);
            subtitleList.redo();

            expect(subtitleList.subtitles.length).toEqual(2);
            expect(subtitleList.subtitles[0]).toHaveTimes([0, 50]);
            expect(subtitleList.subtitles[0].markdown).toEqual('test');

            expect(subtitleList.subtitles[1]).toHaveTimes([50, 100]);
            expect(subtitleList.subtitles[1].markdown).toEqual('content');

            expect(subtitleList.canUndo()).toEqual(true);
            expect(subtitleList.canRedo()).toEqual(false);
        });

        it('can recreate removed subtitles', function() {
            subtitleList._insertSubtitle(0, { startTime: 0, endTime: 100 });
            subtitleList._resetUndo();

            var sub = subtitleList.insertSubtitleBefore(null);
            subtitleList.updateSubtitleContent(sub, 'test-content');
            subtitleList.updateSubtitleTime(sub, 200, 300);
            subtitleList.updateSubtitleParagraph(sub, true);
            subtitleList.updateSubtitleRegion(sub, 'top');
            subtitleList.removeSubtitle(sub);

            subtitleList.undo();

            // test that all attributes were successfully recreated
            var sub = subtitleList.subtitles[1];
            expect(sub.startTime).toEqual(200);
            expect(sub.endTime).toEqual(300);
            expect(sub.markdown).toEqual('test-content');
            expect(sub.startOfParagraph).toEqual(true);
            expect(sub.region).toEqual('top');
        });

        it('can recreate updated subtitles', function() {
            subtitleList._insertSubtitle(0, { startTime: 0, endTime: 100 });
            subtitleList._resetUndo();

            var sub = subtitleList.insertSubtitleBefore(null);

            subtitleList.updateSubtitleContent(sub, 'changed');
            subtitleList.updateSubtitleTime(sub, 1000, 2000);
            subtitleList.updateSubtitleParagraph(sub, true);
            subtitleList.updateSubtitleRegion(sub, 'top');

            subtitleList.undo();
            subtitleList.undo();
            subtitleList.undo();
            subtitleList.undo();

            // test that all attributes were successfully recreated

            var sub = subtitleList.subtitles[1];
            expect(sub).toHaveTimes([-1, -1]);
            expect(sub.markdown).toEqual('');
            expect(sub.startOfParagraph).toEqual(false);
            expect(sub.region).toEqual(undefined);
        });

        it('undos operations in the correct order', function() {
            subtitleList._insertSubtitle(0, {
                startTime: 0, endTime: 100, content: 'test-content'
            });
            subtitleList._removeSubtitle(0, {});
            subtitleList._changesDone('test');

            // When we undo multiple changes, we need to undo them in reverse
            // order.  If we try to undo the insert before undoing the remove,
            // then things will fail
            subtitleList.undo();
            expect(subtitleList.subtitles).toEqual([]);

            // Try redo and undo again to test the code there
            subtitleList.redo();
            subtitleList.undo();

            expect(subtitleList.subtitles).toEqual([]);
        });

        it('has helper methods for the undo/redo menu items', function() {
            expect(subtitleList.canUndo()).toEqual(false);
            expect(subtitleList.canRedo()).toEqual(false);

            subtitleList._insertSubtitle(0, {});
            subtitleList._changesDone('change 1');
            expect(subtitleList.canUndo()).toEqual(true);
            expect(subtitleList.canRedo()).toEqual(false);
            expect(subtitleList.undoText().data.command).toEqual('change 1');

            subtitleList._insertSubtitle(0, {});
            subtitleList._changesDone('change 2');
            expect(subtitleList.canUndo()).toEqual(true);
            expect(subtitleList.canRedo()).toEqual(false);
            expect(subtitleList.undoText().data.command).toEqual('change 2');

            subtitleList.undo();
            expect(subtitleList.canUndo()).toEqual(true);
            expect(subtitleList.canRedo()).toEqual(true);
            expect(subtitleList.undoText().data.command).toEqual('change 1');
            expect(subtitleList.redoText().data.command).toEqual('change 2');

            subtitleList.undo();
            expect(subtitleList.canUndo()).toEqual(false);
            expect(subtitleList.canRedo()).toEqual(true);
            expect(subtitleList.redoText().data.command).toEqual('change 1');

        });

        it('can handle complex undo/redo stacks', function() {
            var sub = subtitleList._insertSubtitle(0, {
                startTime: 0, endTime: 100, content: 'test-content'
            });
            subtitleList._resetUndo();

            subtitleList.splitSubtitle(sub, 'test', 'content');
            subtitleList.insertSubtitleBefore(null);

            subtitleList.undo();
            subtitleList.undo();
            subtitleList.redo();
            subtitleList.undo();

            subtitleList.updateSubtitleContent(sub, 'test-content2');

            expect(subtitleList.subtitles.length).toEqual(1);
            expect(subtitleList.subtitles[0]).toHaveTimes([0, 100]);
            expect(subtitleList.subtitles[0].markdown).toEqual('test-content2');

            subtitleList.undo();
            expect(subtitleList.subtitles.length).toEqual(1);
            expect(subtitleList.subtitles[0]).toHaveTimes([0, 100]);
            expect(subtitleList.subtitles[0].markdown).toEqual('test-content');
        });
    });

    describe('the changeGroup parameter of updateSubtitleTimes', function() {
        var sub1, sub2, sub3, changes;

        beforeEach(function() {
            sub1 = subtitleList.insertSubtitleBefore(null);
            sub2 = subtitleList.insertSubtitleBefore(null);
            sub3 = subtitleList.insertSubtitleBefore(null);
            subtitleList.updateSubtitleTimes([
                    {
                        subtitle: sub1,
                        startTime: 1000,
                        endTime: 1001
                    },
                    {
                        subtitle: sub2,
                        startTime: 2000,
                        endTime: 2001
                    },
            ]);
            subtitleList._resetUndo();
            changes = trackChanges(subtitleList);
        });

        it('groups multiple changes into a single undo', function() {
            subtitleList.updateSubtitleTimes([
                    {
                        subtitle: sub1,
                        startTime: 1001,
                        endTime: 1002
                    }
            ], 'changegroup1');
            subtitleList.updateSubtitleTimes([
                    {
                        subtitle: sub1,
                        startTime: 1002,
                        endTime: 1003,
                    }
            ], 'changegroup1');

            expect(subtitleList.subtitles[0]).toHaveTimes([1002, 1003]);
            expect(subtitleList.canUndo()).toBe(true);

            // Undo should undo both changes at once, and do it efficiently (not updating the same subtitle more than once)
            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {startTime: 1000, endTime: 1001}],
            ]);
            expect(subtitleList.canUndo()).toBe(false);
        });

        it('handles changes that involve multiple subtitles', function() {
            // Do the same test as before, but with multiple subtitles involved
            subtitleList.updateSubtitleTimes([
                    {
                        subtitle: sub1,
                        startTime: 1001,
                        endTime: 1002,
                    },
                    {
                        subtitle: sub2,
                        startTime: 2001,
                        endTime: 2002
                    }
            ], 'changegroup1');
            subtitleList.updateSubtitleTimes([
                    {
                        subtitle: sub1,
                        startTime: 1002,
                        endTime: 1003
                    }
            ], 'changegroup1');
            subtitleList.updateSubtitleTimes([
                    {
                        subtitle: sub1,
                        startTime: 1003,
                        endTime: 1004,
                    },
                    {
                        subtitle: sub2,
                        startTime: 2002,
                        endTime: 2003
                    },
                    {
                        subtitle: sub3,
                        startTime: 3000,
                        endTime: 3001
                    }
            ], 'changegroup1');

            expect(subtitleList.subtitles[0]).toHaveTimes([1003, 1004]);
            expect(subtitleList.subtitles[1]).toHaveTimes([2002, 2003]);
            expect(subtitleList.subtitles[2]).toHaveTimes([3000, 3001]);
            expect(subtitleList.canUndo()).toBe(true);

            // Undo should undo both changes at once, and do it efficiently (not updating the same subtitle more than once)
            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 1, {startTime: 2000, endTime: 2001}],
                    ['update', 0, {startTime: 1000, endTime: 1001}],
                    ['update', 2, {startTime: -1, endTime: -1}],
            ]);
            expect(subtitleList.canUndo()).toBe(false);
        });

        it('does not group changes when changeGroup is different', function() {
            subtitleList.updateSubtitleTimes([
                    {
                        subtitle: sub1,
                        startTime: 1001,
                        endTime: 1002
                    }
            ], 'changegroup1');
            subtitleList.updateSubtitleTimes([
                    {
                        subtitle: sub1,
                        startTime: 1002,
                        endTime: 1003,
                    }
            ], 'changegroup2');

            // Undo should only undo 1 change at once since the changeGroup ids were different
            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {startTime: 1001, endTime: 1002}],
            ]);

            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {startTime: 1000, endTime: 1001}],
            ]);
        });

        it('does not group changes when another operation is in the middle', function() {
            subtitleList.updateSubtitleTimes([
                    {
                        subtitle: sub1,
                        startTime: 1001,
                        endTime: 1002
                    }
            ], 'changegroup1');
            subtitleList.updateSubtitleContent(sub1, "content");

            subtitleList.updateSubtitleTimes([
                    {
                        subtitle: sub1,
                        startTime: 1002,
                        endTime: 1003,
                    }
            ], 'changegroup1');

            // Undo should only undo 1 change at once since the changeGroup ids were different
            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {startTime: 1001, endTime: 1002}],
            ]);

            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {content: ''}],
            ]);

            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {startTime: 1000, endTime: 1001}],
            ]);
        });
    });

    describe('the changeGroup parameter of updateSubtitleContent', function() {
        var sub1, sub2, sub3, changes;

        beforeEach(function() {
            sub1 = subtitleList.insertSubtitleBefore(null);
            sub2 = subtitleList.insertSubtitleBefore(null);
            sub3 = subtitleList.insertSubtitleBefore(null);
            subtitleList.updateSubtitleContent(sub1, 'content');
            subtitleList.updateSubtitleContent(sub2, 'content2');
            subtitleList.updateSubtitleContent(sub3, 'content3');
            subtitleList._resetUndo();
            changes = trackChanges(subtitleList);
        });

        it('groups multiple changes into a single undo', function() {
            subtitleList.updateSubtitleContent(sub1, 'new-content', 'changegroup1');
            subtitleList.updateSubtitleContent(sub1, 'new-content2', 'changegroup1');

            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {content: 'content'}],
            ]);
            expect(subtitleList.canUndo()).toBe(false);
        });

        it('handles changes that involve multiple subtitles', function() {
            subtitleList.updateSubtitleContent(sub1, 'new-content', 'changegroup1');
            subtitleList.updateSubtitleContent(sub2, 'new-content2', 'changegroup1');
            subtitleList.updateSubtitleContent(sub1, 'new-content3', 'changegroup1');

            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {content: 'content'}],
                    ['update', 1, {content: 'content2'}],
            ]);
            expect(subtitleList.canUndo()).toBe(false);
        });

        it('does not group changes when changeGroup is different', function() {
            subtitleList.updateSubtitleContent(sub1, 'new-content', 'changegroup1');
            subtitleList.updateSubtitleContent(sub1, 'new-content2', 'changegroup2');

            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {content: 'new-content'}],
            ]);

            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {content: 'content'}],
            ]);
        });

        it('does not group changes when another operation is in the middle', function() {
            subtitleList.updateSubtitleContent(sub1, 'new-content', 'changegroup1');
            subtitleList.insertSubtitleBefore(null);
            subtitleList.updateSubtitleContent(sub1, 'new-content2', 'changegroup1');

            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {content: 'new-content'}],
            ]);

            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['remove', 3, {}],
            ]);

            changes.length = 0;
            subtitleList.undo();
            expect(changes).toEqual([
                    ['update', 0, {content: 'content'}],
            ]);
        });
    });
});
