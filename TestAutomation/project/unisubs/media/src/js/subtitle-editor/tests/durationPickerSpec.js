describe('The duration picker', function() {
    var $scope;
    var $compile;
    var pgettext;

    beforeEach(module('amara.SubtitleEditor.mocks'));
    beforeEach(module('amara.SubtitleEditor.durationpicker'));

    beforeEach(inject(function($injector) {
        $scope = $injector.get('$rootScope').$new();
        $compile = $injector.get('$compile');
        pgettext = $injector.get('pgettext');
    }));

    function buildDurationPicker(html) {
        var picker = $compile(angular.element(html))($scope);
        $scope.$digest();
        return {
            picker: picker,
            inputs: $('input.durationPicker-input', picker),
            hours: $('input.durationPicker-input.hours', picker),
            minutes: $('input.durationPicker-input.minutes', picker),
            seconds: $('input.durationPicker-input.seconds', picker),
            milliseconds: $('input.durationPicker-input.milliseconds', picker),
        }
    }

    it('creates 4 inputs, one for each time unit', function() {
        var picker = buildDurationPicker('<div duration-picker></div>');
        expect(picker.hours.length).toEqual(1);
        expect(picker.minutes.length).toEqual(1);
        expect(picker.seconds.length).toEqual(1);
        expect(picker.milliseconds.length).toEqual(1);
    });

    it('validates inputs', function() {
        var picker = buildDurationPicker('<div duration-picker></div>');

        function validateInput(unit, value) {
            var input = picker[unit];
            input.val(value).change();
            return !input.hasClass('invalid');
        }
        expect(validateInput('hours', '5')).toBe(true);
        expect(validateInput('hours', '-1')).toBe(false);
        expect(validateInput('hours', 'five')).toBe(false);
        expect(validateInput('hours', '0')).toBe(true);
        expect(validateInput('hours', '0.5')).toBe(false);

        expect(validateInput('minutes', '5')).toBe(true);
        expect(validateInput('minutes', '-1')).toBe(false);
        expect(validateInput('minutes', 'five')).toBe(false);
        expect(validateInput('minutes', '0')).toBe(true);
        expect(validateInput('minutes', '59')).toBe(true);
        expect(validateInput('minutes', '60')).toBe(false);
        expect(validateInput('minutes', '0 0')).toBe(false);

        expect(validateInput('seconds', '5')).toBe(true);
        expect(validateInput('seconds', '-1')).toBe(false);
        expect(validateInput('seconds', 'five')).toBe(false);
        expect(validateInput('seconds', '0')).toBe(true);
        expect(validateInput('seconds', '59')).toBe(true);
        expect(validateInput('seconds', '60')).toBe(false);
        expect(validateInput('seconds', '0seconds')).toBe(false);

        expect(validateInput('milliseconds', '5')).toBe(true);
        expect(validateInput('milliseconds', '-1')).toBe(false);
        expect(validateInput('milliseconds', 'five')).toBe(false);
        expect(validateInput('milliseconds', '0')).toBe(true);
        expect(validateInput('milliseconds', '999')).toBe(true);
        expect(validateInput('milliseconds', '1000')).toBe(false);
    });

    it('supports ngModel', function() {
        var picker = buildDurationPicker('<div duration-picker ng-model="amount"></div>');
        $scope.$apply('amount = 18305005');
        expect(picker.hours.val()).toEqual('5');
        expect(picker.minutes.val()).toEqual('5');
        expect(picker.seconds.val()).toEqual('5');
        expect(picker.milliseconds.val()).toEqual('5');

        picker.hours.val('').change();
        expect($scope.amount).toEqual(305005);

        // any invalid value should make the value NaN
        picker.minutes.val('non-numeric').change();
        expect($scope.amount).toEqual(NaN);

        // blank values should be treated as 0
        picker.minutes.val('').change();
        expect($scope.amount).toEqual(5005);

    });
    it('supports ngDisable', function() {
        $scope.disabled = false;
        var picker = buildDurationPicker('<div duration-picker ng-disable="disabled"></div>');

        expect(picker.inputs.filter(':disabled').length).toEqual(0);
        expect(picker.picker.hasClass('disabled')).toBe(false);

        $scope.$apply('disabled = true');
        expect(picker.inputs.filter(':disabled').length).toEqual(4);
        expect(picker.picker.hasClass('disabled')).toBe(true);

    });

    it('supports ngChange', function() {
        $scope.amount = 0;
        $scope.onChange = jasmine.createSpy('onChange');
        var picker = buildDurationPicker('<div duration-picker ng-model="amount" ng-change="onChange()"></div>');

        expect($scope.onChange).not.toHaveBeenCalled();
        picker.minutes.trigger('change');
        expect($scope.onChange).toHaveBeenCalled();
    });

    it('calls the ngChange callaback on keyup', function() {
        $scope.amount = 0;
        $scope.onChange = jasmine.createSpy('onChange');
        var picker = buildDurationPicker('<div duration-picker ng-model="amount" ng-change="onChange()"></div>');

        expect($scope.onChange).not.toHaveBeenCalled();
        picker.minutes.trigger('keyup');
        expect($scope.onChange).toHaveBeenCalled();
    });
});

describe('The formatTime function', function() {
    var formatTime;

    beforeEach(module('amara.SubtitleEditor.mocks'));
    beforeEach(module('amara.SubtitleEditor.durationpicker'));

    beforeEach(inject(function($injector) {
        formatTime = $injector.get('formatTime');
    }));

    it('formats simple times', function() {
        expect(formatTime(5)).toEqual({
            text: '%(count)s milliseconds',
            data: {count: 5},
            named: true
        });
        expect(formatTime(5000)).toEqual({
            text: '%(count)s seconds',
            data: {count: 5},
            named: true
        });
        expect(formatTime(300000)).toEqual({
            text: '%(count)s minutes',
            data: {count: 5},
            named: true
        });
        expect(formatTime(18000000)).toEqual({
            text: '%(count)s hours',
            data: {count: 5},
            named: true
        });
    });

    it('formats complex times as h:mm:ss.ms', function() {
        expect(formatTime(18305005)).toEqual('5:05:05.005');
    });

    it('drops the trailing milliseconds when zero', function() {
        expect(formatTime(18305000)).toEqual('5:05:05');
    });

    it('supports flags to explicitly set the format', function() {
        expect(formatTime(18000000, {longFormat: true})).toEqual('5:00:00');
        expect(formatTime(18000000, {longFormat: true, includeMilliseconds: true})).toEqual('5:00:00.000');
    });
});
