
beforeEach(function() {
    jasmine.addMatchers({
        toEqualIgnoringOrder: function(util, customEqualityTesters) {
            return {
                compare: function(actual, expected) {
                    var result = {};
                    result.pass = util.equals(actual.slice(0).sort(), expected.slice(0).sort());
                    return result;
                }
            };
        }
    });
});
