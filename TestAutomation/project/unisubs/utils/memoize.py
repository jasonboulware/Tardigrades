# Amara, universalsubtitles.org
#
# Copyright (C) 2016 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

"""memoize -- simple memoization utilities."""

import functools

def memoize(func=None, key_func=None):
    """Memoize a function.

    We store the result of each call inside a dict.  If the function is called
    with the same args, then we return the stored value instead of computing
    it agin.

    Memoize works with both functions and methods.

    For this to work, we need to be able to compute a key for a function call.
    By default this is simply the *args value.  This works if the function is
    always called with hashable args and not with kwargs.  For more complex
    calls, pass in a key function that generates a key based on the function
    arguments.
    """
    def decorator(func):
        memoized_func = MemoizedFunction(func, key_func)
        return memoized_func
    # Kind of weird code, but it lets us either use the decorator directly, or
    # after calling it with key_func
    if key_func:
        return decorator
    else:
        return decorator(func)

class MemoizedFunction(object):
    def __init__(self, func, key_func):
        self.cache = {}
        self.func = func
        self.name = func.func_name
        if key_func is None:
            self.key_func = self.default_key_func
        else:
            self.key_func = key_func

    def __call__(self, *args, **kwargs):
        key = self.key_func(*args, **kwargs)
        if key not in self.cache:
            self.cache[key] = self.func(*args, **kwargs)
        return self.cache[key]

    def default_key_func(self, *args, **kwargs):
        if kwargs:
            raise TypeError("{} has been memoized and cannot accept kwargs.  "
                            "Add a key_func if you want to use them".format(
                                self.name))
        return args

    def clear_cache(self):
        self.cache.clear()

    # Implementing the descriptor protocol makes memoize() work with methods.
    #
    # When __get__ is called, we directly set the value in the object's
    # __dict__ attribute.  This makes it so subsequent lookups skip __get__
    # and get the MemoizedFunction already created.
    def __get__(self, obj, type=None):
        if obj is None:
            return self
        bound_method = self.func.__get__(obj)
        memoized_func = MemoizedFunction(bound_method, self.key_func)
        obj.__dict__[self.name] = memoized_func
        return memoized_func
