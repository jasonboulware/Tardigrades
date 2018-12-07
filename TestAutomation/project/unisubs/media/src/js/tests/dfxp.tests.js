describe('dfxpToMarkdown', function() {
    function callDFXPToMarkdown(dfxpString) {
        return dfxp.dfxpToMarkdown($(dfxpString)[0]);
    }
    it('leaves simple text alone', function() {
        expect(callDFXPToMarkdown('<p>simple text</p>')).toBe('simple text');
    });
    it('converts bold spans', function() {
        var dfxpString = '<p><span tts:fontWeight="bold">text</span></p>';
        expect(callDFXPToMarkdown(dfxpString)).toBe('**text**');
    });
    it('converts italic spans', function() {
        var dfxpString = '<p><span tts:fontStyle="italic">text</span></p>';
        expect(callDFXPToMarkdown(dfxpString)).toBe('*text*');
    });
    it('converts underline spans', function() {
        var dfxpString = '<p><span tts:textDecoration="underline">text</span></p>';
        expect(callDFXPToMarkdown(dfxpString)).toBe('_text_');
    });
    it('converts BRs:', function() {
        var dfxpString = '<p>line1<br />line2</p>';
        expect(callDFXPToMarkdown(dfxpString)).toBe('line1\nline2');
    });
    it('handles lowercase attributes', function() {
        var dfxpString = '<p><span tts:textdecoration="underline">text</span></p>';
        expect(callDFXPToMarkdown(dfxpString)).toBe('_text_');
    });
    it('handles attributes without tts:', function() {
        var dfxpString = '<p><span textDecoration="underline">text</span></p>';
        expect(callDFXPToMarkdown(dfxpString)).toBe('_text_');
    });
    it('handles nested spans:', function() {
        var dfxpString = ('<p><span textDecoration="underline">underline ' +
            '<span fontWeight="bold">bold</span></span></p>)');
        expect(callDFXPToMarkdown(dfxpString)).toBe('_underline **bold**_');
    });
    it('handles BRs nested in spans:', function() {
        var dfxpString = ('<p><span textDecoration="underline">line1' +
            '<br />line2</span></p>)');
        expect(callDFXPToMarkdown(dfxpString)).toBe('_line1\nline2_');
    });
});

describe('AmaraDFXPParser', function() {
    var parser = null;
    beforeEach(function() {
        parser = new AmaraDFXPParser();
        parser.init('<tt xmlns="http://www.w3.org/ns/ttml" xmlns:tts="http://www.w3.org/ns/ttml#styling" xml:lang="en">\
        <head>\
            <metadata xmlns:ttm="http://www.w3.org/ns/ttml#metadata">\
                <ttm:title/>\
                <ttm:description/>\
                <ttm:copyright/>\
            </metadata>\
            <styling xmlns:tts="http://www.w3.org/ns/ttml#styling">\
                <style xml:id="amara-style" tts:color="white" tts:fontFamily="proportionalSansSerif" tts:fontSize="18px" tts:textAlign="center"/>\
            </styling>\
            <layout xmlns:tts="http://www.w3.org/ns/ttml#styling">\
                <region xml:id="amara-subtitle-area" style="amara-style" tts:extent="560px 62px" tts:padding="5px 3px" tts:backgroundColor="black" tts:displayAlign="after"/>\
            </layout>\
        </head>\
        <body region="amara-subtitle-area">\
            <div></div>\
        </body>\
    </tt>');
    });

    it('formats times as <hours>:<mins>:<secs>.<ms>', function() {
        var second = 1000;
        var minute = second * 60;
        var hour = minute * 60;
        parser.addSubtitle(null, {
            content: 'test',
            begin: 500,
            end: 3 * hour + 2 * minute + 1 * second + 500,
        })
        var output = $(parser.xmlToString(true, true));
        var pTags = $('p', output);
        expect(pTags.length).toEqual(1);
        var p = pTags.eq(0);
        expect(p.attr('begin')).toBe("00:00:00.500");
        expect(p.attr('end')).toBe("03:02:01.500");

    });
});
