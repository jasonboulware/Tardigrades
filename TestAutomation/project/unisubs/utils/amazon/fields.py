from StringIO import StringIO
from hashlib import sha1
from time import time
from uuid import uuid4
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.fields.files import FieldFile
from easy_thumbnails.processors import scale_and_crop
from PIL import Image
from storages.backends.s3boto3 import S3Boto3Storage

THUMB_SIZES = getattr(settings, 'THUMBNAILS_SIZE', ())

class S3ImageFieldFile(FieldFile):
    def thumb_url(self, width, height):
        if not self.name:
            return ''

        size = (width, height)
        name = self._get_thumbnail_name(size)

        if not settings.USE_AMAZON_S3 and not self.storage.exists(name):
            try:
                self._create_thumbnail(self._open_image(), size)
            except IOError:
                pass
        return self.storage.url(name)

    def _open_image(self):
        content = self.storage.open(self.name).read()
        return Image.open(StringIO(content))

    def generate_file_name(self):
        return sha1(settings.SECRET_KEY+str(time())+str(uuid4())).hexdigest()

    def _get_thumbnail_name(self, size):
        """"Get the name for a thumbnail.

        Args:
            name: name of the original file
            size: width/height of the thumbnail as a tuple

        Returns: filename
        """
        if self.field.legacy_filenames:
            return self._get_thumbnail_name_legacy(size)

        basename, ext = os.path.splitext(self.name)
        return '{}_{}x{}{}'.format(basename, size[0], size[1], ext)

    def _get_thumbnail_name_legacy(self, size):
        """Legacy version of _get_thumbnail_name

        This method employs some extremely wonkey logic to duplicate the
        thumbnail names that solr-thumbnail created for us
        """
        return "%s_%sx%s_crop-smart_upscale-True_q85.jpg" % (
            self.name.replace('.', '_'), size[0], size[1])

    def recreate_all_thumbnails(self):
        """Recreate thumbnails for each size for our field's thumb_sizes """
        self._create_all_thumbnails(self._open_image())

    def _create_all_thumbnails(self, image):
        """Create thumbnails for each size for our field's thumb_sizes """

        for size in self.field.thumb_sizes:
            self._create_thumbnail(image, size)

    def _create_thumbnail(self, image, size):
        """Create a thumbnail for a given size

        This method creates thumbnail for the given width/height then saves them
        using field's storage.

        :param image: PIL source image
        :param size: width/height as a tuple
        """

        if image.size != size:
            dest_image = scale_and_crop(image, size, crop='smart', upscale=True)
        else:
            dest_image = image

        dest_bytes = StringIO()

        if self.field.legacy_filenames:
            # Need to convert the file to a jpeg
            if dest_image.mode != "RGB":
                dest_image = dest_image.convert("RGB")
            dest_image.save(dest_bytes, format="JPEG")
        else:
            dest_image.save(dest_bytes, image.format)

        self.storage.save(self._get_thumbnail_name(size),
                          ContentFile(dest_bytes.getvalue()))

    def save(self, name, content, save=True):
        ext = name.split('.')[-1]
        # try to sanity check the extension a bit.  Some filenames have
        # periods in random places which we don't want to interpret as a 100
        # char extension.
        if ext < 6:
            name = '%s.%s' % (self.generate_file_name(), ext)
        else:
            name = self.generate_file_name()
        name = self.field.generate_filename(self.instance, name)
        self.name = self.storage.save(name, content)
        setattr(self.instance, self.field.name, self.name)

        # Update the filesize cache
        self._size = len(content)
        self._committed = True

        content = self.storage.open(self.name)
        self._create_all_thumbnails(Image.open(content))

        # Save the object because it has changed, unless save is False
        if save:
            self.instance.save()
    save.alters_data = True

    def delete(self, save=True):
        # Only close the file if it's already open, which we know by the
        # presence of self._file
        if hasattr(self, '_file'):
            self.close()
            del self.file

        self.storage.delete(self.name)

        for size in self.field.thumb_sizes:
            name = self._get_thumbnail_name(size)
            self.storage.delete(name)

        self.name = None
        setattr(self.instance, self.field.name, self.name)

        # Delete the filesize cache
        if hasattr(self, '_size'):
            del self._size
        self._committed = False

        if save:
            self.instance.save()
    delete.alters_data = True

class S3EnabledImageField(models.ImageField):
    attr_class = S3ImageFieldFile

    def __init__(self, bucket=settings.AWS_USER_DATA_BUCKET_NAME,
                 thumb_sizes=THUMB_SIZES, verbose_name=None, name=None,
                 width_field=None, height_field=None, legacy_filenames=True,
                 acl='public-read', **kwargs):
        self.thumb_sizes = thumb_sizes
        self.bucket_name = bucket
        self.legacy_filenames = legacy_filenames

        if settings.USE_AMAZON_S3:
            kwargs['storage'] = S3Boto3Storage(bucket_name=self.bucket_name,
                                               default_acl=acl,
                                               querystring_auth=False)
        super(S3EnabledImageField, self).__init__(verbose_name, name, width_field, height_field, **kwargs)

class S3EnabledFileField(models.FileField):
    def __init__(self, bucket=settings.AWS_USER_DATA_BUCKET_NAME,
                 verbose_name=None, name=None, upload_to='', storage=None,
                 acl='public-read', **kwargs):
        self.bucket_name = bucket

        if settings.USE_AMAZON_S3:
            storage = S3Boto3Storage(bucket_name=self.bucket_name,
                                     default_acl=acl,
                                     querystring_auth=False)
        super(S3EnabledFileField, self).__init__(verbose_name, name, upload_to, storage, **kwargs)
