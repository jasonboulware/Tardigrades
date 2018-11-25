"""
Associate data with the current request.

This module is a wrapper around the newrelic attributes code.  The idea is
that you set key/value pairs for each request to track what's going on better.
This is separated out into a module to make it easy to change things if we
ever switch away from newrelic

Currently we track the username of the logged in user.

"""
import newrelic.agent

def log(name, value):
    newrelic.agent.add_custom_parameter(name, value)
