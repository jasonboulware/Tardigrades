# Amara, universalsubtitles.org
#
# Copyright (C) 2017 Participatory Culture Foundation
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

def chunkedqs(queryset, size=1000):
    """
    iterate through a queryset one chunk at a time

    Please take note that this yields in order by primary key so 
    the result might be different from what you expect when you pass in
    a queryset that is ordered_by something other than the pk

    Adapted from https://djangosnippets.org/snippets/1949/
    """
    last_pk = -1
    while True:
        chunk_qs = queryset.filter(pk__gt=last_pk).order_by('pk')[:size]
        if chunk_qs:
            for obj in chunk_qs:
                yield obj
                last_pk = obj.pk
        else:
            return

def batch_qs(qs, batch_size=1000):
    """
    Iterate through a queryset in batches (similar to chunkedqs)
    The difference of this with chunkedqs is that this should
     work properly with ordered querysets

    Please be careful when using this:

    Note that you'll want to order the queryset, as ordering is not guaranteed by the 
    database and you might end up iterating over some items twice, and some not at all. 
    Also, if your database is being written to in between the time you start and finish 
    your script, you might miss some items or process them twice.

    Don't use this for sensitive transactions, i.e. don't use this when you will
    be modifying results from the queryset

    Slight modification of https://djangosnippets.org/snippets/1170/

    """
    total = qs.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield qs[start:end]
