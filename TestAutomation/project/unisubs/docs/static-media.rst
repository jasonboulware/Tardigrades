Static Media
============

Static media files are handled by the staticmedia app.  This app has several
goals:

- **Combine multiple files into a single "media bundle".**  Linking to a
  single JS file results in faster page loads than linking to multiple files.
- **Compress JS/CSS code.**
- **Support preprocessors like SASS.**
- **Support media files served from the local server or S3**
- **Store media files on S3 in a unique location for each deploy.**  This
  allows us to upload media for our next deploy without affecting our current
  one.  It also allows us to the set the expire header to the far future which
  is good for caching.

Settings
--------

Example
^^^^^^^

::

  MEDIA_BUNDLES = {
      "base.css": {
          "files": (
              "css/v1.scss",
              "css/bootstrap.css",
          ),
      },
      "site.js": {
          "files": (
              "js/jquery-1.4.3.js",
              "js/unisubs.site.js",
          ),
      },
  }
  STATIC_MEDIA_COMPRESSED = True

  STATIC_MEDIA_USES_S3 = True
  AWS_ACCESS_KEY_ID = 'abcdef'
  AWS_SECRET_ACCESS_KEY = 'abcdef
  STATIC_MEDIA_S3_BUCKET = 'bucket.name'
  STATIC_MEDIA_S3_URL_BASE = '//s3.amazonaws.com/bucket.name'

MEDIA_BUNDLES
^^^^^^^^^^^^^

``MEDIA_BUNDLES`` defines our Javascript/CSS media bundles.

The keys are the filename that we will generate.  The extension of the
filename controls what type of media and should either by ``js`` or ``css``.

The values are dicts that determine how we build the bundle.  They can have
these properties:

.. attribute:: files

    list of files to bundle together (paths are relative to the media directory)

.. attribute:: add_amara_conf (optional)

    If True, we will prepend javascript code to the source JS files.  THis
    will create global object called ``_amaraConf`` with these properties:

  - ``baseURL``: base URL for the amara website
  - ``staticURL``: base URL to the static media

STATIC_MEDIA_COMPRESSED
^^^^^^^^^^^^^^^^^^^^^^^

Set to False to disable compressing/minifying Javascript and CSS

STATIC_MEDIA_USES_S3
^^^^^^^^^^^^^^^^^^^^

If True we Will Serve media files from amazon S3.  This will change the URLs
that our template tags create for links to the media bundles.
``STATIC_MEDIA_USES_S3`` is usually True for production and False for
development.

If ``STATIC_MEDIA_USES_S3`` is enabled, the following settings are available:

- ``AWS_ACCESS_KEY_ID``: S3 access key.
- ``AWS_SECRET_ACCESS_KEY``: S3 secret key.
- ``STATIC_MEDIA_S3_BUCKET``: S3 bucket to store media in.
- ``STATIC_MEDIA_S3_URL_BASE``: Base URL for S3 media.

Compilation & Minification
--------------------------

We use uglifyjs for Javascript files and SASS for CSS files.  Using the SASS
extensions is optional.  If you just have regular CSS files that SASS will
function simply as a CSS compressor.


Media Directory Structure
-------------------------

Regardless if media is uploaded to S3 or we are serving it from the local
instance, we structure the files the same way:

- css/ - CSS bundles
- js/ - Javascript bundles
- images/ - Image files
- fonts/ - font files

When serving media from the local server, the root URL for media files
will be ``/media/``.

When serving media from S3, the root URL for media files will be
``<STATIC_MEDIA_S3_URL_BASE><git-commit-id/``

Development, Media Bundles, and Caching
---------------------------------------

For development servers, STATIC_MEDIA_USES_S3 is usually False, which causes
us to serve up the media bundles from the local server.  It takes long enough
to compile media bundles that we don't want to re-do it on every page request.
So we cache the result and use that for subsequent requests.  Before using a
cached result, we check the mtime of all source files, and if any one is later
than when the cache was created, we rebuild.

This works fine for most use cases, but there are a couple ways that it will
fail.  For example removing a file from the sources list won't trigger a
rebuild.  If you think this may be happening, just update the mtime on any
source file to trigger the rebuild manually.

In Templates
------------

To link to media files in templates load the ``media_bundle`` library.  Then
you can use these tags:

- ``media_bundle`` -- include a CSS/JS media bundle (generates the entire
  script/link tag)
- ``url_for`` -- Get the URL to a media bundle.
- ``static_url`` -- Get the base URL for static media.
