(function (Popcorn) {
    Popcorn.plugin('amaratranscript', {
        _setup : function(options) {

            options.pop = this;

            // Construct the transcript line.
            options.line = document.createElement('a');
            options.line.href = '#';
            options.line.classList.add('amara-transcript-line');
            options.line.innerHTML = options.text;

            // If this subtitle has indicated that it's the beginning of a paragraph,
            // prepend two line breaks before the subtitle.
            if (options.startOfParagraph) {
                options.container.appendChild(document.createElement('br'));
                options.container.appendChild(document.createElement('br'));
            }

            // Add the subtitle to the transcript container.
            options.container.appendChild(options.line);

            // Upon clicking the line, we should set the video playhead to this line's
            // start time.
            options.line.addEventListener('click', function(e) {
                options.pop.currentTime(options.start);
            }, false);

        },
        start: function(event, options){

            // When we reach this subtitle, add this class.
            options.line.classList.add('current-subtitle');
            options.view.autoScrollToLine(options.line);
        },
        end: function(event, options){

            // When we're no longer on this subtitle, remove this class.
            options.line.classList.remove('current-subtitle');
        },
        _teardown: function(options, start) {
            options.container.removeChild(options.line);
        }
    });
})(Popcorn);
