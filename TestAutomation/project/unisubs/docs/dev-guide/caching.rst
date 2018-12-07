Caching
=======

Varnish
-------
We use Varnish (http://varnish-cache.org/) as a reverse proxy/caching server in
front of our app.  The code is at github.com/pculture/amara-cache.  Our general system is:

  - Most pages use `cache-control: private` and are not cached by Varnish
  - Pages that are mostly static like the homepage and watch pages are cached.
  - We vary by Accept-Language and Cookie
  - In the Varnish VCL, we try to normalize/reduce those headers to improve
    cache hits.  We make it so:

    - Cookie only contains the sessionid
    - Accept-Language is normalized, so it only contains the language that we
      want to display the page in.

Caching App
-----------

.. automodule:: caching
