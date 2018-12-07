import re, htmlentitydefs

def htmlentitydecode(s):
    # From: http://codeunivers.com/codes/python/decode_html_entities_unicode_characters
    # (Inspired from http://mail.python.org/pipermail/python-list/2007-June/443813.html)
    def entity2char(m):
        entity = m.group(1)
        if entity in htmlentitydefs.name2codepoint:
            return unichr(htmlentitydefs.name2codepoint[entity])
        return " "  # Unknown entity: We replace with a space.
    t = re.sub('&(%s);' % u'|'.join(htmlentitydefs.name2codepoint), entity2char, s)

    # Then convert numerical entities
    t = re.sub('&', "&amp;", t)
    #t = re.sub('[&#[\d];]', lambda x: unichr(int(x.group(1))), t)
    # Then convert hexa entities
    #re.sub('[&#x[\w];]', lambda x: unichr(int(x.group(1),16)), t)
    return t

remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')

def clean_xml(body):
    #Is not finished. Should clean XML below for parsing with lxml
    return remove_re.sub('', htmlentitydecode(body))

class LXMLAdapter(object):
    def __init__(self, miniNode):
        self.miniNode = miniNode

    def getAttribute(self, att_name):
        return  self.miniNode.attrib.get(att_name, None)

