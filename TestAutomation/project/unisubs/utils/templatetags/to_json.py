# See http://djangosnippets.org/snippets/201/

import json

from django.core.serializers import serialize
from django.db.models.query import QuerySet
from django.template import Library

register = Library()

def to_json(object):
    if isinstance(object, QuerySet):
        return serialize('json', object)
    return json.dumps(object)

register.filter('to_json', to_json)
