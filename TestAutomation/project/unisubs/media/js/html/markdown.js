goog.provide('unisubs.html.markdownToHtml');
goog.provide('unisubs.html.MARKDOWN_REPLACE_SEQ');

unisubs.html.MARKDOWN_REPLACE_SEQ = [
    // ordrer matters, need to apply double markers first
    [/(\*\*)([^\*]+)(\*\*)/g, "<b>$2</b>"],
    [/(\*)([^\*]+)(\*{1})/g, "<i>$2</i>"],
    [/(_)([^_]+)(_{1})/g, "<u>$2</u>"]
];
/**
 * This is *not* a parser. Just a quick hack to convert
 * markdown emphasys and strong syntax to <b> and <i> tags.
 *  At some point we should use a correct parser for this.
 * Allow both * and _ to denote bold and italycs.
 */
function escapeMarkdown(text) {
    /* Escape HTML entities in markdown */
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

unisubs.html.markdownToHtml = function (input) { 
    input = escapeMarkdown(input);
    for (var i = 0; i < unisubs.html.MARKDOWN_REPLACE_SEQ.length; i ++){
        input = input.replace(unisubs.html.MARKDOWN_REPLACE_SEQ[i][0],
                              unisubs.html.MARKDOWN_REPLACE_SEQ[i][1]);
    }
    return input;
};

