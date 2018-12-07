
from nose.tools import *

from django.conf import settings

def test_commit_id_set():
    # Check that LAST_COMMIT_GUID is set, which means we recorded the git
    # commit correctly
    assert_not_equal(settings.LAST_COMMIT_GUID, 'dev')
    assert_not_equal(settings.LAST_COMMIT_GUID, None)
