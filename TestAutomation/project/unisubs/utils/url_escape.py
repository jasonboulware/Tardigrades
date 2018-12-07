from django.utils.encoding import iri_to_uri

def url_escape(url):
    if isinstance(url, basestring):
        return iri_to_uri(url)
    return url
