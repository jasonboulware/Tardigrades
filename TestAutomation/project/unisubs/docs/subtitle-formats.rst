Babelsubs
=========

We've split the subtitle handling into it's own separate project, `Babelsubs <https://github.com/pculture/babelsubs/>`_. Anything that has do to with parsing, generating and formatting subtitles should be handled over there. The main unisubs repo should only make calls to babelsubs with the desired operations / data.

Storage
-----------
Internally, we're storing subtitles as the DFXP format. DFXP is the most complex, and most capable format of all. It's also the only one with a real spec. The advantage is that it lets us tell our users that they can input DFXP, process it throughout our system and get their data out correctly, even for features we don't currently support (like advanced styles).

Formatting
----------
Formatting we **do** support:

- Bold text
- Italic text
- Underline
- Like breaks

Each format handles those different. On DFXP you have attributes on the xmlnodes (span, p and div) such as fontWeigh='bold' and textStyle='italic'. Line breaks are <br/> tags.

For SRT and friends, we have the 'b', 'i' and 'u' tags. Line breaks are displayed with the right line separator.

For HTML (which is not a download format, but it's displayed on the website), we have 'em', 'strong' and 'style' tags, and 'br' for line breaks.

Ideally, for testing a complete set of features we need to test:

- The forementioned formats (italics, bold, underline)
- Line breaks
- Single ">" and doubles ">>" . This is used to denote speaker changes and is widely used by our customers. They must come out correctly both when displayed on the website (subtitle view, the widget, the dialogs) and when downloaded. On DFXP those should use character entities.

For anything other than these tags, let's say you have a video on web development, and they write a '<script>alert();</script> ' tag. Here's what should happen:

- Should be stored with the tag chars escaped
- Should show up on the website (dialog, subtitle view and the widget) as is, but escaped (javascript shouldn't run) , but it should be editable
- Non html / xml formats (such as srt) should display them as is

In general, here's the intended workflow:

- On intake convert what we can to dfxp (such as a line break to <br/>). Do not strip tags.
- On output (for the website only) escape anything other than the tags we expect (<script>, etc)
