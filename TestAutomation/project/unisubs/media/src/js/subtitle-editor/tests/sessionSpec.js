describe('The SessionBackend', function() {
    var $rootScope;
    var $scope;
    var subtitleList;
    var EditorData;
    var SubtitleStorage = SubtitleStorage;
    var initialVersion = 1;

    beforeEach(module('amara.SubtitleEditor.mocks'));
    beforeEach(module('amara.SubtitleEditor.subtitles.models'));
    beforeEach(module('amara.SubtitleEditor.session'));

    beforeEach(inject(function($controller, $injector) {
        EditorData = $injector.get('EditorData');
        SubtitleStorage = $injector.get('SubtitleStorage');
        subtitleList = new ($injector.get('SubtitleList'))();
        subtitleList.loadEmptySubs('en');
        $rootScope = $injector.get('$rootScope');
        $scope = $rootScope.$new();
        $scope.workingSubtitles = {
            language: {
                code: EditorData.languageCode,
            },
            versionNumber: initialVersion,
            subtitleList: subtitleList,
            title: 'test title',
            description: 'test description',
            metadata: {}
        };
        $scope.collab = {
            notes: 'test notes'
        };
        $scope.timeline = {
            duration: 25000,
        };
        $controller('SessionBackend', { $scope: $scope, });
    }));

    function saveSubtitlesResponse(versionNumber) {
        // Mock up the response from saveSubtitles.  Of course the actual
        // response has much more data, but this is all the we care about.
        return {
            data: {
                version_number: versionNumber
            }
        };

    }

    it('saves subtitles', function() {
        $scope.sessionBackend.saveSubtitles('action');
        expect(SubtitleStorage.saveSubtitles).toHaveBeenCalledWith(
            $scope.workingSubtitles.subtitleList.toXMLString(),
            $scope.workingSubtitles.title,
            $scope.timeline.duration / 1000,
            $scope.workingSubtitles.description,
            $scope.workingSubtitles.metadata,
            null, 'action', 'dfxp', false);
    });

    if('updates the version number after saving', function() {
        $scope.sessionBackend.saveSubtitles(true);
        // Once the SubtitleStorage.saveSubtitles completes, then we should
        // update the version number and the promise returned by
        // sessionBackend.saveSubtitles() should also complete
        SubtitleStorage.deferreds.saveSubtitles.resolve(
            saveSubtitlesResponse(initialVersion+1));
        $rootScope.$digest();
        expect($scope.workingSubtitles.versionNumber).toEqual(initialVersion+1);
    });

    it('calls back our callback after saving', function() {
        var callback = jasmine.createSpy();
        $scope.sessionBackend.saveSubtitles(true).then(callback);
        expect(callback).not.toHaveBeenCalled();
        SubtitleStorage.deferreds.saveSubtitles.resolve(
            saveSubtitlesResponse(initialVersion+1));
        $rootScope.$digest();
        expect(callback).toHaveBeenCalled();
    });

    it('performs actions', function() {
        $scope.sessionBackend.performAction('action');
        expect(SubtitleStorage.performAction).toHaveBeenCalledWith('action');
    });

});

describe('The SessionController', function() {
    var $sce;
    var $scope;
    var $rootScope;
    var $window;
    var EditorData;
    var session;
    var backendMethodsCalled;
    var simulateSaveError;
    var actionArg;

    beforeEach(module('amara.SubtitleEditor.mocks'));
    beforeEach(module('amara.SubtitleEditor.subtitles.models'));
    beforeEach(module('amara.SubtitleEditor.session'));

    beforeEach(inject(function($controller, $injector) {
        $sce = $injector.get('$sce');
        $rootScope = $injector.get('$rootScope');
        EditorData = $injector.get('EditorData');
        EditorData.actions = [
            {
                name: 'action1',
                label: 'Action 1',
                in_progress_text: 'Doing Action 1',
                requireSyncedSubtitles: true
            },
            {
                name: 'action2',
                label: 'Action 2',
                in_progress_text: 'Doing Action 2',
                requireSyncedSubtitles: false
            },
            {
                name: 'action3',
                label: 'Action 3',
                in_progress_text: 'Doing Action 3',
                requireSyncedSubtitles: null
            },
            {
                name: 'save-draft',
                label: 'Save Draft',
                in_progress_text: 'Saving...',
                requireSyncedSubtitles: false
            }
        ];
        $scope = $rootScope.$new();
        $scope.overrides = {
            forceSaveError: false
        };
        $window = {};
        $scope.dialogManager = jasmine.createSpyObj('dialogManager', [
            'open', 'close', 'openDialog', 'showFreezeBox', 'closeFreezeBox'
        ]);
        $controller('SessionController', {
            $scope: $scope,
            $window: $window
        });
        session = $scope.session;
        $scope.exitEditor = jasmine.createSpy('exitEditor');
        $scope.exitToLegacyEditor = jasmine.createSpy('exitToLegacyEditor');
    }));

    beforeEach(inject(function($q) {
        backendMethodsCalled = [];
        actionArg = null;
        simulateSaveError = false;
        var backendMethods = [ 
            'saveSubtitles',
            'saveSubtitlesWithAction',
            'performAction',
        ];
        $scope.sessionBackend = {};
        $scope.analytics = jasmine.createSpy('analytics');
        _.each(backendMethods, function(methodName) {
            var spy = jasmine.createSpy().and.callFake(function(arg) {
                if(methodName == 'saveSubtitles'
                    || methodName == 'performAction') {
                    actionArg = arg;
                }
                backendMethodsCalled.push(methodName);
                var deferred = $q.defer();
                if(simulateSaveError) {
                    deferred.reject("error");
                } else {
                    deferred.resolve(true);
                }
                return deferred.promise;
            });
            $scope.sessionBackend[methodName] = spy;
        });
        $scope.sessionBackend.subtitlesComplete =
            jasmine.createSpy().and.returnValue(true);
    }));

    beforeEach(function() {
        jasmine.addMatchers({
            toHaveBeenCalledWithTrusted: function(util, customEqualityTesters) {

                return {
                    compare: function(actual, expected) {
                        var result = {};
                        if(actual.calls.count() == 0) {
                            result.pass = false;
                            result.message = 'method not called';
                            return result;
                        }
                        var arg = actual.calls.mostRecent().args[0];
                        result.pass = util.equals(expected, $sce.getTrustedHtml(arg));
                        return result;
                    }
                };
            }
        });
    });

    function expectRedirectToVideoPage() {
        expect($scope.exitEditor).toHaveBeenCalled();
        expect($scope.exitToLegacyEditor).not.toHaveBeenCalled();
    }

    function expectRedirectToLegacyEditor() {
        expect($scope.exitToLegacyEditor).toHaveBeenCalled();
        expect($scope.exitEditor).not.toHaveBeenCalled();
    }

    function expectNoRedirect() {
        expect($scope.exitToLegacyEditor).not.toHaveBeenCalled();
        expect($scope.exitEditor).not.toHaveBeenCalled();
    }

    it('handles exiting', function() {
        session.exit();
        expectRedirectToVideoPage();
    });

    it('shows the unsaved changes dialog', function() {
        session.subtitlesChanged = true;
        session.exit();
        expectNoRedirect();
        expect($scope.dialogManager.openDialog).toHaveBeenCalledWith(
            'unsavedWork', jasmine.any(Object));
    });

    it('handles the exit button on the unsaved work dialog', function() {
        session.subtitlesChanged = true;
        session.exit();
        var callbacks = $scope.dialogManager.openDialog.calls.mostRecent().args[1];
        callbacks.exit();
        expectRedirectToVideoPage();
    });

    it('handles exiting to the legacy editor', function() {
        session.exitToLegacyEditor();
        expectRedirectToLegacyEditor();
    });

    it('shows the unsaved changes dialog when exiting to the legacy editor', function() {
        session.subtitlesChanged = true;
        session.exitToLegacyEditor();
        expectNoRedirect();
        expect($scope.dialogManager.openDialog).toHaveBeenCalledWith(
            'legacyEditorUnsavedWork', jasmine.any(Object));
    });

    it('handles the exit button on the legacy editor unsaved work dialog', function() {
        session.subtitlesChanged = true;
        session.exitToLegacyEditor();
        var callbacks = $scope.dialogManager.openDialog.calls.mostRecent().args[1];
        callbacks.discardChangesAndOpenLegacyEditor();
        expectRedirectToLegacyEditor();
    });

    it('handles saving drafts', function() {
        session.subtitlesChanged = true;
        session.saveDraft();
        // While the save is in-progress we should show a freeze box
        expect($scope.dialogManager.showFreezeBox).toHaveBeenCalledWithTrusted('Saving&hellip;');
        // After the save is complete, we should close the freezebox and show
        // the subtitles saved dialog
        $rootScope.$digest();
        expect(backendMethodsCalled).toEqual(['saveSubtitles']);
        expect(actionArg).toBe('save-draft');
        expect($scope.dialogManager.closeFreezeBox).toHaveBeenCalled();
        expect($scope.dialogManager.openDialog).toHaveBeenCalledWith(
            'changesSaved', jasmine.any(Object));
    });

    it('handles the exit button after saving subtitles', function() {
        session.subtitlesChanged = true;
        session.saveDraft();
        $rootScope.$digest();
        var callbacks = $scope.dialogManager.openDialog.calls.mostRecent().args[1];
        callbacks.exit();
        expectRedirectToVideoPage();
    });

    it('handles errors while saving subtitles', function() {
        simulateSaveError = true;
        session.subtitlesChanged = true;
        session.saveDraft();
        $rootScope.$digest();
        expect($scope.dialogManager.closeFreezeBox).toHaveBeenCalled();
        expect($scope.dialogManager.open).toHaveBeenCalledWith('save-error');
    });

    it('lists actions, but excludes save draft', function() {
        expect($scope.actions[0].label).toEqual('Action 1');
        expect($scope.actions[1].label).toEqual('Action 2');
        expect($scope.actions[2].label).toEqual('Action 3');
        expect($scope.actions.length).toEqual(3);
    });

    it('handles performing actions', function() {
        $scope.actions[0].perform();
        // While the save is in-progress we should show a freeze box
        expect($scope.dialogManager.showFreezeBox).toHaveBeenCalledWithTrusted('Doing Action 1&hellip;');
        // After the save is complete, we should close the freezebox and show
        // the subtitles saved dialog
        $rootScope.$digest();
        expect(backendMethodsCalled).toEqual(['performAction']);
        expect(actionArg).toEqual(EditorData.actions[0].name);
        expect($scope.dialogManager.closeFreezeBox).toHaveBeenCalled();
        expectRedirectToVideoPage();
    });

    it('handles errors while performing actions', function() {
        simulateSaveError = true;
        $scope.actions[0].perform();
        $rootScope.$digest();
        expect($scope.dialogManager.closeFreezeBox).toHaveBeenCalled();
        expect($scope.dialogManager.open).toHaveBeenCalledWith('save-error');
    });

    it('handles performing actions with subtitle changes', function() {
        session.subtitlesChanged = true;
        $scope.actions[0].perform();
        // While the save is in-progress we should show a freeze box
        expect($scope.dialogManager.showFreezeBox).toHaveBeenCalledWithTrusted('Doing Action 1&hellip;');
        // After the save is complete, we should close the freezebox and show
        // the subtitles saved dialog
        $rootScope.$digest();
        expect(backendMethodsCalled).toEqual(['saveSubtitles']);
        expect(actionArg).toEqual(EditorData.actions[0].name);
        expect($scope.dialogManager.closeFreezeBox).toHaveBeenCalled();
        expectRedirectToVideoPage();
    });

    it('prevents actions with requireSyncedSubtitles=true to be performed with incomplete subtitles', function() {
        $scope.sessionBackend.subtitlesComplete.and.returnValue(false);
        expect($scope.actions[0].canPerform()).toBeFalsy();
    });

    it('allows actions with requireSyncedSubtitles=true to be performed with complete subtitles', function() {
        $scope.sessionBackend.subtitlesComplete.and.returnValue(true);
        expect($scope.actions[0].canPerform()).toBeTruthy();
    });

    it('always allows actions with requireSyncedSubtitles=false to be performed', function() {
        $scope.sessionBackend.subtitlesComplete.and.returnValue(false);
        expect($scope.actions[1].canPerform()).toBeTruthy();
    });

    it('always allows actions with requireSyncedSubtitles=null to be performed', function() {
        $scope.sessionBackend.subtitlesComplete.and.returnValue(false);
        expect($scope.actions[2].canPerform()).toBeTruthy();
    });

    it('prevents closing the window with unsaved changes', function() {
        // No changes yet
        expect($window.onbeforeunload()).toBe(null);
        session.subtitlesChanged = true;
        expect($window.onbeforeunload()).toBeTruthy();
        session.saveDraft()
        $rootScope.$digest();
        expect($window.onbeforeunload()).toBe(null);
    });
});
