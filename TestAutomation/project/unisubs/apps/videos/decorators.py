from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import models
from django.http import Http404
from django.utils.functional import wraps

from videos.models import Video
from subtitles.models import SubtitleVersion

def get_object_or_403(request, qs, **params):
    """Get an object or throw a PermissionDenied error

    This function works similarly to Django's get_object_or_404.  However, if
    the object is not found it will:
        * Return a 403 error for non-staff users
        * Return a 404 error for other users

    This prevents telling non-staff users if a video id exists or not, which
    is somewhat of a security concern (see pculture/amara-enteprise#97)
    """
    if isinstance(qs, type) and issubclass(qs, models.Model):
        qs = qs.objects.all()
    try:
        return qs.get(**params)
    except ObjectDoesNotExist:
        if request.user.is_staff:
            raise Http404()
        else:
            raise PermissionDenied()

def get_video_from_code(func):
    """
    Wraps a view with a signature such as view(request, video_id, ...)
    to -> view(request, video, ...), where video is a Video instance
    and authorization credentials for viewing have been checked
    for the user on that request.
    """
    def wrapper(request, video_id, *args, **kwargs):
        qs = Video.objects.select_related('teamvideo')
        video = get_object_or_403(request, qs, video_id=video_id)
        if not video.can_user_see(request.user):
            raise PermissionDenied()
        return func(request, video, *args, **kwargs)
    return wraps(func)(wrapper)

def get_cached_video_from_code(cache_pattern):
    """
    Like get_video_from_code(), but uses Video.cache.get_instance() to get a
    cached version of the video.
    """
    def decorator(func):
        def wrapper(request, video_id, *args, **kwargs):
            try:
                video = Video.cache.get_instance_by_video_id(video_id,
                                                             cache_pattern)
            except Video.DoesNotExist:
                raise Http404
            request.use_cached_user()
            if not video.can_user_see(request.user):
                raise PermissionDenied()
            return func(request, video, *args, **kwargs)
        return wraps(func)(wrapper)
    return decorator

def get_video_revision(func):
    """
    Wraps a view with a signature such as view(request, pk, ...)
    to -> view(request, version, ...), where version is a SubtitleVersion instance
    and authorization credentials for viewing have been checked
    for the user on that request.
    """
    def wrapper(request, video_id=None, pk=None, *args, **kwargs):
        version = get_object_or_403(request, SubtitleVersion.objects.extant(),
                                    pk=pk)
        id = video_id if video_id else version.video.video_id
        video = get_object_or_403(request, Video, video_id=id)

        if not video.can_user_see(request.user):
            raise Http404

        return func(request, version, *args, **kwargs)
    return wraps(func)(wrapper)
