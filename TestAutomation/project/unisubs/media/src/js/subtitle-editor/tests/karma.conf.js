// Karma configuration
// Generated on Mon Aug 25 2014 18:02:59 GMT+0000 (UTC)

module.exports = function(config) {
  config.set({

    // base path that will be used to resolve all patterns (eg. files, exclude)
    basePath: '../..',


    // frameworks to use
    // available frameworks: https://npmjs.org/browse/keyword/karma-adapter
    frameworks: ['jasmine'],


    // list of files / patterns to load in the browser
    files: [
        'third-party/jquery-1.10.1.js',
        'third-party/angular.*.js',
        'third-party/angular-mocks.*.js',
        'third-party/angular-cookies.js',
        'third-party/jquery.autosize.js',
        'third-party/underscore.1.8.3.js',
        'third-party/popcorn.js',
        'dfxp/dfxp.js',
        'tests/*.tests.js',
        'uri.js',
        'subtitle-editor/*.js',
        'subtitle-editor/**/*.js',
        'subtitle-editor/tests/*Spec.js',
        'subtitle-editor/tests/mocks.js',
        'subtitle-editor/tests/helpers.js',
    ],


    // list of files to exclude
    exclude: [
    ],


    // preprocess matching files before serving them to the browser
    // available preprocessors: https://npmjs.org/browse/keyword/karma-preprocessor
    preprocessors: {
    },


    // test results reporter to use
    // possible values: 'dots', 'progress'
    // available reporters: https://npmjs.org/browse/keyword/karma-reporter
    reporters: ['progress'],


    // web server port
    port: 9876,
    ip: "0.0.0.0",


    // enable / disable colors in the output (reporters and logs)
    colors: true,


    // level of logging
    // possible values: config.LOG_DISABLE || config.LOG_ERROR || config.LOG_WARN || config.LOG_INFO || config.LOG_DEBUG
    logLevel: config.LOG_INFO,


    // enable / disable watching file and executing tests whenever any file changes
    autoWatch: true,


    // start these browsers
    // available browser launchers: https://npmjs.org/browse/keyword/karma-launcher
    browsers: [],


    // Continuous Integration mode
    // if true, Karma captures browsers, runs the tests and exits
    singleRun: false
  });
};
