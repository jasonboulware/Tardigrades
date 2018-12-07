describe('Test our razor thin urls utils', function() {
    describe('displayTime', function() {

        it('Domain detection looks sane?', function(){
            var parser = new AmaraURI("http://www.example.com/some-path") ;
            expect(parser.domainEquals("example.com")).toBeFalsy();
            expect(parser.domainContains("example.com")).toBeTruthy();
            expect(parser.domainEquals("www.example.com")).toBeTruthy();
        });
        it("File type extension", function(){
            var parser = new AmaraURI('http://www.example.com/');
            expect(parser.fileExtension()).toBeNull();
            parser = new AmaraURI('http://www.example.com/no-extension');
            expect(parser.fileExtension()).toBeNull();
            parser = new AmaraURI('http://www.example.com/there.mp4');
            expect(parser.fileExtension()).toBe('mp4');
            parser = new AmaraURI('http://www.example.com/there-to/there.mp4');
            expect(parser.fileExtension()).toBe('mp4');
            parser = new AmaraURI('http://www.example.com/there-to/there.mp4?someValue=so.txt');
            expect(parser.fileExtension()).toBe('mp4');
        })

    });
});
