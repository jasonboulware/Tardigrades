import mock

from django.core.cache import cache

from caching.utils import get_or_calc, get_or_calc_many

def test_get_or_calc():
    # test calling get_or_calc without any data stored.  We should call
    # our function, then store the data
    func = mock.Mock(return_value=1)
    result = get_or_calc('key', func)
    assert result == 1
    assert cache.get('key') == 1

def test_get_or_calc_cache_hit():
    # test get_or_calc with a cache hit.  We should avoid calling the
    # function in this case
    func = mock.Mock(return_value=1)
    cache.set('key', 2)
    result = get_or_calc('key', func)
    assert result == 2
    assert func.call_count == 0

def test_get_or_calc_many():
    func = mock.Mock(side_effect=lambda keys: [1] * len(keys))
    cache.set('key2', 2)
    result = get_or_calc_many(['key1', 'key2'], func)
    assert result == [1, 2]
    assert func.call_count == 1
