from __future__ import absolute_import

import pytest

from utils.factories import *

@pytest.fixture
def team():
    return TeamFactory()

