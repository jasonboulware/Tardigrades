"""
Django's URL validator is too strict and is causing us problems, see:
 - our ticket: https://unisubs.sifterapp.com/issues/2198
 - django's:  https://code.djangoproject.com/ticket/20264#ticket
"""
import re

from django.core.validators import URLValidator

URLValidator.regex = re.compile(
                             r'^(?:http|ftp)s?://'  # http:// or https://
                             r'(?:(?:[A-Z0-9_](?:[A-Z0-9-_]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
                             r'localhost|'  # localhost...
                             r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
                             r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
                             r'(?::\d+)?'  # optional port
                             r'(?:/?|[/?]\S+)$', re.IGNORECASE)
