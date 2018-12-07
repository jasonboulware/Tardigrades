#!/bin/bash

jshint media/src/js/embedder/embedder.js

cat media/src/js/third-party/json2.min.js \
    media/src/js/third-party/underscore.min.js \
    media/src/js/third-party/zepto.min.js \
    media/src/js/third-party/backbone.min.js \
    media/src/js/third-party/popcorn.js \
    media/src/js/popcorn/popcorn.amaratranscript.js \
    media/src/js/popcorn/popcorn.amarasubtitle.js \
    media/src/js/embedder/conf-dev.js \
    media/src/js/embedder/embedder.js \
  > media/release/public/embedder.js

scss -t compressed media/src/css/embedder/embedder.scss media/src/css/embedder/embedder-dev.css

# This is just for local development.
cp media/src/css/embedder/embedder-dev.css media/release/public/embedder.css
