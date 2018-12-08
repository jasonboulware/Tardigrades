describe('Test display time filter', function() {
    beforeEach(module('amara.SubtitleEditor.subtitles.filters'));
    var minuteInMilliseconds = 60 * 1000;
    var hourInMilliseconds = 60 * minuteInMilliseconds;
    describe('displayTime', function() {
        it('Formats invalid values as "--"',
            inject(function(displayTimeFilter) {
                expect(displayTimeFilter(null)).toBe("--");
                expect(displayTimeFilter(-1)).toBe("--");
                expect(displayTimeFilter("a")).toBe("--");
        }));

        it('Rounds milliseconds to 2 digits', 
            inject(function(displayTimeFilter) {
                expect(displayTimeFilter(5123)).toBe("0:05.12");
                expect(displayTimeFilter(5128)).toBe("0:05.13");
        }));

        it('Always displays minutes',
            inject(function(displayTimeFilter) {
                expect(displayTimeFilter(123)).toBe("0:00.12");
                expect(displayTimeFilter(5123)).toBe("0:05.12");
                expect(displayTimeFilter(55123)).toBe("0:55.12");
        }));

        it('pads components',
            inject(function(displayTimeFilter) {
                expect(displayTimeFilter(60512)).toBe("1:00.51");
        }));

        it('Only shows hours if they are needed', 
            inject(function(displayTimeFilter) {
                // If the time is lass than 1 hour, we don't need to display
                // the hour component
                expect(displayTimeFilter(hourInMilliseconds - 1000))
                    .toBe('59:59.00');
                // Ift it's over an hour, we do display it
                expect(displayTimeFilter(hourInMilliseconds +
                        minuteInMilliseconds * 10 + 120))
                    .toBe("1:10:00.12");
        }));
    });

    describe('displayTimeSeconds', function() {
        it('Does not include milliseconds',
            inject(function(displayTimeSecondsFilter) {
                expect(displayTimeSecondsFilter(5123)).toBe("0:05");
        }));
    });
});

describe('Drop down shows the right labels', function() {
    beforeEach(module('amara.SubtitleEditor.subtitles.filters'));
    describe('versionDropDownDisplay', function() {

        var versionData = {
            'version_no':1
        };
        it('Are we showing the right thing?',
            inject(function(versionDropDownDisplayFilter) {
                versionData.visibility = 'public';
                expect(versionDropDownDisplayFilter(versionData)).
                    toBe('Version 1');
                versionData.visibility = 'private';
                expect(versionDropDownDisplayFilter(versionData)).
                    toBe('Version 1 (private)');
                versionData.visibility = 'deleted';
                expect(versionDropDownDisplayFilter(versionData)).
                    toBe('Version 1 (deleted)');
            }));
    });
});
