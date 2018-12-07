/*
 * See https://github.com/vojtajina/testacular/blob/master/test/client/testacular.conf.js
 */

// All file references here will be relative to this.
basePath = 'media/src/js';

// Files to include.
files = [
    JASMINE,
    JASMINE_ADAPTER,
    'third-party/amara-jquery.min.js',
    'dfxp/sample.dfxp.xml.js',
    'dfxp/dfxp.js',
    'tests/dfxp.tests.js'
];

// Files to exclude.
exclude = [];

reporters = ['progress', 'junit'];

junitReporter = {
    outputFile: 'testacular-test-results.xml'
};

// Web server port.
port = 9876;

// CLI runner port.
runnerPort = 9100;

// CLI colors?
colors = true;

/* Logging level.
 *
 * One of [LOG_DISABLE, LOG_ERROR, LOG_WARN, LOG_INFO, LOG_DEBUG]
 */
logLevel = LOG_INFO;

// Executes tests when any files change.
autoWatch = true;

/* Browsers to start.
 *
 * One of: [
 *   Chrome,
 *   ChromeCanary,
 *   Firefox,
 *   Opera,
 *   Safari,
 *   PhantomJS,
 *   IE,
 * ]
 */
browsers = ['ChromeCanary'];

captureTimeout = 5000;

// Auto-run tests on start and exit?
singleRun = false;

// Report specs slower than this.
reportSlowerThan = 500;
