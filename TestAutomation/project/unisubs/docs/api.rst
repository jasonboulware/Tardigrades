API Documentation
======================

Amara provides a REST API to interactive with the site.  Please contact us at
enterprise@amara.org if you’d like to use the Amara API for commercial
purposes.

Overview
--------

Authentication
**************

Before interacting with the API, you must have an API key. In order to get one,
create a user on the Amara website, then go to the `edit profile
<http://www.amara.org/en/profiles/edit/>`_ page. At the bottom of
the page you will find a "Generate new key" button . Clicking on it will fetch
your user the needed API key.

Every request must have the username and the API keys as headers. For example::

   X-api-username: my_username_here
   X-api-key: my_api_key_here

.. note:: You can also use the deprecated X-apikey header to specify your key

So a sample request would look like this:

.. http:get:: https://amara.org/api/videos/

  :reqheader X-api-username: <Username>
  :reqheader X-api-key: <API key>


.. _api-data-formats:

Data Formats
************

The API accepts request data in the several formats.  Use the ``Content-Type``
HTTP header to specify the format of your request:

====================  ==================
Format                Content-Type
====================  ==================
JSON *(recommended)*  application/json
XML                   application/xml
YAML                  application/yaml
====================  ==================

In this documentation, we use the term "Request JSON Object" to specify the
fields of the objects sent as the request body.  Replace "JSON" with "XML" or
"YAML" if you are using one of those input formats.

Here's an example of request data formated as JSON:

.. code-block:: json

    {"field1": "value1", "field2": "value2", ... }

By default we will return JSON output.  You can the ``Accept`` header to select
a different output format.  You can also use the ``format`` query param to
select the output formats.  The value is the format name in lower case (for
example ``format=json``).

We also support text/html as an output format and
application/x-www-form-urlencoded and multipart/form-data as input formats.
However, this is only to support browser friendly endpoints.  It should not be
used in API client code.

Paginated Responses
*******************

Many listing API endpoints are paginated to prevent too much data from being
fetched and returned at one time (for example the video listing API).  These
endpoints are marked with ``paginated`` in their descriptions.  Paginated
responses only return limited number of results per request, alongside links
to the next/previous page.

Here's an example paginated response from the Teams listing:

.. sourcecode:: http

    {
        "meta": {
            "previous": null,
            "next": "http://amara.org/api/teams?limit=20&offset=20", 
            "offset": 0,
            "limit": 20,
            "total_count": 151
        },
        "objects": [
            {
                "name": "",
                "slug": "tedx-import",
                "description": "",
                "is_visible": true,
                "membership_policy": "Open",
                "video_policy": "Any team member"
            },
            ...
        ]
    }

* The ``meta`` field contains pagination information, including next/previous
  links, the total number of results, and how many results are listed per page
* The ``objects`` field contains the objects for this particular page


Browser Friendly Endpoints
**************************

All our API endpoints can be viewed in a browser.  This can be very nice for
exploring the API and debugging issues.  To view API endpoints in your
browser simply log in to amara as usual then paste the API URL into your
address bar.

Value Formats
*************

- Dates/times use ISO 8601 formatting
- Language codes use BCP-47 formatting

Use HTTPS
*********

All API requests should go through https.  This is important since an HTTP
request will send your API key over the wire in plaintext.

The only exception is when exploring the API in a browser.  In this case you
will be using the same session-based authentication as when browsing the site.

API interaction overview
************************

All resources share a common structure when it comes to the basic data
operations.

* ``GET`` request is used to viewing data
* ``POST`` request is used for creating new items
* ``PUT`` request is used for updating existing items
* ``DELETE`` request is used for deleting existing items

To view a list of videos on the site you can use

.. http:get:: https://amara.org/api/videos/

To get info about the video with id "foo" you can use

.. http:get:: https://amara.org/api/videos/foo

Many of the available resources will allow you to filter the response by a
certain field.  Filters are specified as GET parameters on the request.  For
example, if you wanted to view all videos belong to a team called
"butterfly-club", you could do:

.. http:get:: https://amara.org/api/videos/?team=butterfly-club

In addition to filters, you can request that the response is ordered in some
way.  To order videos by title, you would do

.. http:get:: https://amara.org/api/videos/?order_by=title

To create a video you can use

.. http:post:: https://amara.org/api/videos/

To update the video with video id `foo` use:

.. http:put:: https://amara.org/api/videos/foo

API Changes / Versioning
************************

Sometimes we need to make backwards incompatible changes to the API.  Here's our system for allowing our partners and other API consumers to deal with them:

* All changes are announced on the `Amara Development Blog <https://about.amara.org/category/development-blog/>`_ and the `API Changes mailing list <https://groups.google.com/a/amara.org/d/forum/api-users>`_.
* When we make a change, we give clients between six weeks and three months of transition time, depending on the complexity of the changes, to update their code to work with the new system.
* During the transition time, we return an HTTP header to indicate that the API will be changing.  The name is ``X-API-DEPRECATED`` and the value is the date the API will change in ``YYYYMMDD`` format.
* Clients can start using the new API during the transition time by sending the ``X-API-FUTURE`` header.  The value should be the date of the API that you want to use, also in ``YYYYMMDD`` format.  If the ``X-API-FUTURE`` date is >= the switchover date then the new API code will be used.
* You can use ``X-API-FUTURE`` to test changes to your API client code and to deploy new code that works with the updated API.  Using this method you can ensure your integration works seamlessly through the API change.
* If you aren't able to change your request headers, then you can also use the api-future query parameter (for example ``/api/videos/?api-future=20151021``)

.. include:: api-autogenerated.txt
