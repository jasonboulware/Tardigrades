describe('The Workflow class', function() {
    var subtitleList = null;
    var workflow = null;

    beforeEach(module('amara.SubtitleEditor.subtitles.models'));
    beforeEach(module('amara.SubtitleEditor.workflow'));
    beforeEach(module('amara.SubtitleEditor.mocks'));

    beforeEach(inject(function(SubtitleList, Workflow) {
        subtitleList = new SubtitleList();
        subtitleList.loadEmptySubs('en');
        workflow = new Workflow(subtitleList);
    }));

    it('starts in the typing stage', function() {
        expect(workflow.stage).toBe('typing');
    });

    it('starts in the review stage if we already have subs',
            inject(function(Workflow) {
        var sub = subtitleList.insertSubtitleBefore(null);
        subtitleList.updateSubtitleContent(sub, 'sub text');
        subtitleList.updateSubtitleTime(sub, 100, 200);
        workflow = new Workflow(subtitleList);
        expect(workflow.stage).toBe('review');
    }));

    it('can complete the typing stage once there is a subtitle with content', function() {
        expect(workflow.canCompleteStage('typing')).toBeFalsy();
        var sub = subtitleList.insertSubtitleBefore(null);
        expect(workflow.canCompleteStage('typing')).toBeFalsy();

        subtitleList.updateSubtitleContent(sub, 'content');
        expect(workflow.canCompleteStage('typing')).toBeTruthy();
    });

    it('can complete the syncing stage once subs are complete and synced', function() {
        workflow.stage = 'syncing';
        expect(workflow.canCompleteStage('syncing')).toBeFalsy();

        var sub = subtitleList.insertSubtitleBefore(null);
        expect(workflow.canCompleteStage('syncing')).toBeFalsy();

        subtitleList.updateSubtitleContent(sub, 'content');
        expect(workflow.canCompleteStage('syncing')).toBeFalsy();

        subtitleList.updateSubtitleTime(sub, 500, 1000);
        expect(workflow.canCompleteStage('syncing')).toBeTruthy();
    });

    it('moves to the syncing stage after typing', function() {
        var sub = subtitleList.insertSubtitleBefore(null);
        subtitleList.updateSubtitleContent(sub, 'content');
        subtitleList.updateSubtitleTime(sub, 500, 1000);

        workflow.completeStage('typing');
        expect(workflow.stage).toEqual('syncing');
    });

    it('moves to the review stage after syncing', function() {
        var sub = subtitleList.insertSubtitleBefore(null);
        subtitleList.updateSubtitleContent(sub, 'content');
        subtitleList.updateSubtitleTime(sub, 500, 1000);

        workflow.completeStage('typing');
        workflow.completeStage('syncing');
        expect(workflow.stage).toEqual('review');
    });

    it('handles the active/inactive CSS states', function() {
        workflow.stage = 'review';
        expect(workflow.stageCSSClass('typing')).toEqual('inactive');
        expect(workflow.stageCSSClass('syncing')).toEqual('inactive');
        expect(workflow.stageCSSClass('review')).toEqual('active');
    });
});

describe('NormalWorkflowController', function() {
    var $scope = null;
    var subtitleList = null;

    beforeEach(module('amara.SubtitleEditor.subtitles.models'));
    beforeEach(module('amara.SubtitleEditor.workflow'));
    beforeEach(module('amara.SubtitleEditor.mocks'));

    beforeEach(inject(function ($controller, $rootScope, SubtitleList, Workflow) {
        subtitleList = new SubtitleList();
        $scope = $rootScope;
        $scope.translating = function() { return false; }
        $scope.timelineShown = false;
        $scope.toggleTimelineShown = jasmine.createSpy();
        $scope.currentEdit = {
            'start': jasmine.createSpy()
        };
        $scope.dialogManager = {
            'showFreezeBox': jasmine.createSpy()
        };
        subtitleList.loadEmptySubs('en');
        $scope.workingSubtitles = { subtitleList: subtitleList };
        $scope.workflow = new Workflow(subtitleList);
        spyOn($scope, '$emit');
        $controller('NormalWorkflowController', {
            $scope: $scope,
        });

        // Create a subtitle so we can move to the next stage
        var sub = subtitleList.insertSubtitleBefore(null);
        subtitleList.updateSubtitleTime(sub, 500, 1000);
    }));

    it('shows the timeline for the sync step', function() {
        expect($scope.toggleTimelineShown.calls.count()).toBe(0);
        $scope.$apply('workflow.stage="syncing"');
        expect($scope.toggleTimelineShown.calls.count()).toBe(1);
    });

    it('restarts video playback when switching steps', inject(function(VideoPlayer) {
        $scope.$apply('workflow.stage="syncing"');
        expect(VideoPlayer.pause).toHaveBeenCalled();
        expect(VideoPlayer.seek).toHaveBeenCalledWith(0);
    }));
});

describe('when up and down sync subtitles', function() {
    var $scope;

    beforeEach(module('amara.SubtitleEditor'));
    beforeEach(module('amara.SubtitleEditor.subtitles.models'));
    beforeEach(module('amara.SubtitleEditor.mocks'));

    beforeEach(inject(function($rootScope, $controller, Workflow) {
        $scope = $rootScope;
        $scope.timelineShown = false;
        $controller("AppControllerEvents", {
            $scope: $scope,
        });
        spyOn($scope, '$emit');
    }));

    it('syncs when the timeline is shown', inject(function(MockEvents) {
        $scope.handleAppKeyDown(MockEvents.keydown(40));
        expect($scope.$root.$emit).not.toHaveBeenCalledWith("sync-next-start-time");
        expect($scope.$root.$emit).not.toHaveBeenCalledWith("sync-next-end-time");
        $scope.handleAppKeyDown(MockEvents.keydown(38));
        expect($scope.$root.$emit).not.toHaveBeenCalledWith("sync-next-start-time");
        expect($scope.$root.$emit).not.toHaveBeenCalledWith("sync-next-end-time");

        $scope.timelineShown = true;
        $scope.handleAppKeyDown(MockEvents.keydown(40));
        expect($scope.$root.$emit).toHaveBeenCalledWith("sync-next-start-time");
        $scope.handleAppKeyDown(MockEvents.keydown(38));
        expect($scope.$root.$emit).toHaveBeenCalledWith("sync-next-end-time");
    }));
});

describe('when the enter key creates a new subtitle', function() {
    var keyCodeForEnter = 13;
    var subtitleList;
    var $scope;

    beforeEach(module('amara.SubtitleEditor.subtitles.controllers'));
    beforeEach(module('amara.SubtitleEditor.subtitles.models'));
    beforeEach(module('amara.SubtitleEditor.mocks'));

    beforeEach(inject(function($rootScope, $controller, CurrentEditManager, SubtitleList) {
        $scope = $rootScope;
        subtitleList = new SubtitleList();
        subtitleList.loadEmptySubs('en');
        $scope.workingSubtitles = {
            subtitleList: subtitleList,
        }
        $scope.timelineShown = false;
        $scope.currentEdit = new CurrentEditManager();
        $scope.getSubtitleRepeatItem = function() {
            return null;
        }
        subtitleList.insertSubtitleBefore(null);
        // FIXME: we should mock window, but that's tricky to do.  Especially
        // since we wrap it in jquery.
        $controller('WorkingSubtitlesController', {
            $scope: $scope,
        });
        spyOn(subtitleList, 'insertSubtitleBefore').and.callThrough();
        spyOn(subtitleList, 'insertSubtitleAtEnd').and.callThrough();
    }));

    it('creates a new subtitle when the timeline is hidden',
            inject(function(MockEvents) {
        $scope.currentEdit.start(subtitleList.subtitles[0]);
        var evt = MockEvents.keydown(keyCodeForEnter);
        $scope.onEditKeydown(evt);
        expect(subtitleList.insertSubtitleAtEnd).toHaveBeenCalled();
        expect(evt.preventDefault).toHaveBeenCalled();

        subtitleList.insertSubtitleAtEnd.calls.reset();
        $scope.timelineShown = true;
        $scope.onEditKeydown(MockEvents.keydown(keyCodeForEnter));
        expect(subtitleList.insertSubtitleAtEnd).not.toHaveBeenCalled();
    }));
});

describe('The WorkflowController', function() {
    // Create a mock NormalWorkflowController and ReviewWorkflowController.
    //
    // All they do is set a scope variable that says that they were created.
    // This is used to test that the WorkflowController creates the correct
    // subcontroller based on the work_mode.
    angular.module('MockWorkflowSubControllers', [])
        .controller('NormalWorkflowController', function($scope) {
            $scope.subController = 'NormalWorkflowController';
        })
    .controller('ReviewWorkflowController', function($scope) {
        $scope.subController = 'ReviewWorkflowController';
    });

    beforeEach(module('amara.SubtitleEditor.mocks'));
    beforeEach(module('amara.SubtitleEditor.workflow'));
    beforeEach(module('MockWorkflowSubControllers'));

    it('creates a NormalWorkflowController for normal work mode', inject(function($controller, EditorData) {
        EditorData.work_mode = { type: 'normal' };
        $scope = {};
        $controller('WorkflowController', { $scope: $scope, });

        expect($scope.subController).toEqual('NormalWorkflowController');
        expect($scope.workMode.type).toEqual('normal');
    }));

    it('creates a ReviewWorkflowController for normal work mode', inject(function($controller, EditorData) {
        EditorData.work_mode = { type: 'review' };
        $scope = {};

        $controller('WorkflowController', { $scope: $scope, });
        expect($scope.subController).toEqual('ReviewWorkflowController');
        expect($scope.workMode.type).toEqual('review');
    }));
});
