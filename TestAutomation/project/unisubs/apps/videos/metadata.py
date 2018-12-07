# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
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

"""videos.metadata - Handle metadata fields stored for videos and versions

Videos store metadata fields using the meta_N_type and meta_N_content columns.

Types for metadata fields have several different representations:
    - They are stored in the database as integers.
    - The getter/setter methods use a string machine name (these are nicer for
      using in JSON dicts and the like).
    - When displaying them, we use a human-friendly, translated, labels.

There is also support for an having other models use the fields from video and
optionally override them.  To implement that, you need to add the
meta_N_content columns to your model, and use update_child_and_video()
and get_child_metadata() functions to get/set the metadata data.
This is currently used by SubtitleVersion
"""

from django.db import models
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_noop

METADATA_FIELD_COUNT = 3

# Define possible values for the metadata type fields.  List of
# (db_value, slug, label) tuples.
metadata_type_defs = [
    (0, 'speaker-name', ugettext_noop('Speaker')),
    (1, 'location', ugettext_noop('Location')),
]

type_value_to_name = dict((val, slug)
                         for val, slug, label in metadata_type_defs)
name_to_type_value = dict((slug, val)
                         for val, slug, label in metadata_type_defs)
name_to_label = dict((slug, label)
                     for val, slug, label in metadata_type_defs)
metadata_type_choices = [
    (val, label)
    for val, slug, label in metadata_type_defs
]

def all_names():
    return name_to_type_value.keys()

def type_name_is_valid(name):
    return name in name_to_type_value

def type_field(index):
    return 'meta_%s_type' % (index+1)

def content_field(index):
    return 'meta_%s_content' % (index+1)

class MetadataTypeField(models.PositiveIntegerField):
    def __init__(self, **kwargs):
        kwargs.update({
            'null': True,
            'blank': True,
            'choices': metadata_type_choices,
        })
        models.PositiveIntegerField.__init__(self, **kwargs)

class MetadataContentField(models.CharField):
    def __init__(self, **kwargs):
        kwargs.update({
            'blank': True,
            'max_length': 255,
            'default': '',
        })
        models.CharField.__init__(self, **kwargs)

class MetadataDict(dict):
    def convert_for_display(self):
        """Convert the types in this list to human-friendly labels.

        Also converts the tuples to a dict for easy use in the template system
        """

        return [{
            'label': _(name_to_label[name]),
            'content': content,
        }
            for (name, content) in self.items()
            if content != ''
        ]

def get_metadata_for_video(video):
    """Get a list of metadata for a video

    :returns: dict mapping metadata names to their contents
    """
    rv = MetadataDict()
    for i in xrange(METADATA_FIELD_COUNT):
        type_val = getattr(video, type_field(i))
        if type_val is None:
            break
        else:
            name = type_value_to_name[type_val]
            value = getattr(video, content_field(i))
            rv[name] = value
    return rv

def update_video(video, new_metadata, commit=True):
    """Update a video object bassed on a list of field data

    This method sets the type/content fields on video if needed, then returns
    the content so that it can be set for on the fields of SubtitleVersion.

    :param video: Video object to update
    :param new_metadata: data for the fields as a list of (name, content) tuples
    :param commit: Should we save the video after the update?
    """
    type_names = update_video_types(video, new_metadata.keys(), commit=False)
    for i, name in enumerate(type_names):
        if name in new_metadata:
            setattr(video, content_field(i), new_metadata[name])
    if commit:
        video.save()

def update_video_types(video, metadata_types, commit=True):
    """Update the metadata types for a video.

    This method ensures that a video has a field for all types listed in
    metadata_types.  If the video doesn't currently have metadata for one of
    the types, then the content will be set to an empty string.

    :param video: Video object to update
    :param metadata_types: list of metadata type names
    :param commit: Should we save the video after the update?
    :returns: a list of metadata_types for the video, in the order of the
    fields.  (rv[N] corrsponds for the meta_N_type on video).
    """
    current_types = set()
    rv = []
    # go through metadata already stored in the video
    for field_index in xrange(METADATA_FIELD_COUNT):
        type_value = getattr(video, type_field(field_index))
        if type_value is None:
            break
        type_name = type_value_to_name[type_value]
        current_types.add(type_name)
        rv.append(type_name)
    # go through metadata not yet stored in the video
    # NOTE: after the loop, field_index points to the first metadata that's
    # unused
    changed_video = False
    for name in metadata_types:
        if name in current_types:
            continue
        type_value = name_to_type_value[name]
        if field_index >= METADATA_FIELD_COUNT:
            raise ValueError("Can only store %s metadata" %
                             METADATA_FIELD_COUNT)
        setattr(video, type_field(field_index), type_value)
        setattr(video, content_field(field_index), '')
        rv.append(name)
        field_index += 1
        changed_video = True
    if changed_video and commit:
        video.save()
    return rv

def update_child_and_video(child, video, new_metadata, commit=True):
    """Update metadata for both a video and a child object """
    video_types = update_video_types(video, new_metadata.keys(), commit)
    for i, metadata_type in enumerate(video_types):
        setattr(child, content_field(i), new_metadata.get(metadata_type, ''))
    if commit:
        child.save()

def get_child_metadata(child, video, fallback_to_video=False):
    """Get the metadata data for a child.

    Params:
        child: Child object
        video: Video object
        fallback_to_video: if True then for values that aren't set for child
            we will use the value from video instead.
    """
    rv = MetadataDict()

    for i in xrange(METADATA_FIELD_COUNT):
        type_val = getattr(video, type_field(i))
        if type_val is None:
            break
        name = type_value_to_name[type_val]
        value = getattr(child, content_field(i))
        if not value and fallback_to_video:
            value = getattr(video, content_field(i))
        rv[name] = value
    return rv
