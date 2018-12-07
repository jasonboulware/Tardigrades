#!/usr/bin/python

"""add_url.py -- add a URL to testdata directory.

Inside the test we monkeypatch urllib.open and feedparser.parse.  Instead of
downloading the URL, we use the contents of the corresponding file in the
testdata directory.
"""

import hashlib
import urllib
import sys

def main(argv):
    try:
        url = argv[1]
    except IndexError:
        print "Usage: python add_url.py [url]"
        sys.exit(1)
    filename = hashlib.md5(url).hexdigest()
    source = urllib.urlopen(url)
    dest = open(filename, 'w')
    dest.write(source.read())
    source.close()
    dest.close()
    print 'success!'
    print 'filename is %s' % filename

if __name__ == '__main__':
    main(sys.argv)
