from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat as fs_format
from django.utils.translation import ugettext_lazy as _

class MaxFileSizeValidator(object):
    def __init__(self, max_size, message=_(u'Please keep file size under %(required_size)s. Current file size %(current_size)s')):
        self.max_size = max_size
        self.message = message

    def __call__(self, content):
        if content._size > self.max_size:
            params = dict(required_size=fs_format(self.max_size), current_size=fs_format(content._size))
            raise ValidationError(self.message % params)
