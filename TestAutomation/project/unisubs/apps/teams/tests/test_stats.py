import mock
import pytest

from django.core.cache import cache

from teams import stats
from utils.factories import *
from utils.test_utils import *

def add_hits(team, name, times):
    for time in times:
        mock_now.set(time)
        stats.increment(team, name)

def get_stats(team, now):
    mock_now.set(now)
    return stats.get_stats(team)

def test_increment(team):
    add_hits(team, 'test-stat', [
        '2017-01-31T00:00:00',
        '2017-12-31T00:00:00',
        '2018-01-01T00:00:00',
        '2018-01-01T00:08:00',
        '2018-01-02T00:07:00',
        '2018-01-03T00:05:00',
        '2018-01-05T00:08:00',
        '2018-01-07T00:00:00',
        '2018-01-08T00:00:00',
    ])
    assert get_stats(team, '2018-01-08T08:00:00') == {
        'test-stat': stats.StatSums(today=1, yesterday=1, last_week=6, last_month=7),
    }

def test_empty_counter(team):
    """
    Test get_stats with no stats in the system
    """
    mock_now.set('2018-01-08T00:00:00')
    assert stats.get_stats(team) == {}

def test_multiple_stats(team):
    add_hits(team, 'stat1', [
        '2018-01-03T00:05:00',
        '2018-01-05T00:08:00',
        '2018-01-07T00:01:10',
    ])
    add_hits(team, 'stat2', [
        '2018-01-02T00:07:00',
        '2018-01-07T00:01:10',
    ])
    assert get_stats(team, '2018-01-08T00:00:00') == {
        'stat1': stats.StatSums(yesterday=1, last_week=3, last_month=3),
        'stat2': stats.StatSums(yesterday=1, last_week=2, last_month=2),
    }

def test_caching(team):
    add_hits(team, 'test-stats', [
        '2018-01-03T00:05:00',
    ])
    assert get_stats(team, '2018-01-08T00:00:00') == {
        'test-stats': stats.StatSums(yesterday=0, last_week=1, last_month=1),
    }

    # Running get_stats a second time uses the cache.  Check that the result
    # is the same.

    assert get_stats(team, '2018-01-08T00:00:00') == {
        'test-stats': stats.StatSums(yesterday=0, last_week=1, last_month=1),
    }

def test_caching_expiration(team):
    patcher = mock.patch('django.core.cache.cache.set', wraps=cache.set)
    with patcher as mock_set:
        # Fetch the stats a half an hour before midnight.  The cache
        # should expire then
        get_stats(team, '2018-01-08T23:30:00')
        timeout = mock_set.call_args[0][2]
        assert timeout == 30 * 60

def test_cleanup(team, redis_connection):
    """
    The cleanup() method should clean up everything except the samples for the
    last 120 time periods
    """
    add_hits(team, 'stats', [
        # This old hit should be deleted
        '2018-01-01T00:00:00',
        # These recent hits should not be deleted
        '2018-02-01T00:00:00',
        '2018-02-02T00:00:00',
        '2018-03-01T00:00:00',
        '2018-03-01T00:30:00',
    ])
    mock_now.set('2018-03-03T00:00:00')
    stats.cleanup_counters()

    hash_keys = redis_connection.hkeys(stats.calc_hash_name(team))
    assert set(hash_keys) == set([
        'stats:2018-2-1',
        'stats:2018-2-2',
        'stats:2018-3-1',
    ])

    # the counter names should still be in our tracking set
    assert (redis_connection.smembers(stats.TRACKING_SET_KEY) ==
            set([stats.calc_hash_name(team)]))

def test_cleanup_counter(team, redis_connection):
    """
    If there have been no hits in the last 120 time periods, then we should
    delete the entire hash
    """
    add_hits(team, 'stats', [
        '2017-01-01T00:00:00',
    ])
    mock_now.set('2018-01-01T00:00:00')
    stats.cleanup_counters()
    assert not redis_connection.exists(stats.calc_hash_name(team))
    # All data is deleted, so we should remove the hash name from our tracking
    # set
    assert redis_connection.smembers(stats.TRACKING_SET_KEY) == set()
