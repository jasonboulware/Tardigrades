from django import dispatch

before_tests = dispatch.Signal()

__all__ = [
    'before_tests',
]
