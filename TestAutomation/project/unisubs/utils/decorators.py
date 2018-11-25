from functools import wraps
import logging
suspicious_logger = logging.getLogger("suspicious")

from django.http import  HttpResponseForbidden
from django.conf import settings
from django.contrib.auth.views import redirect_to_login

def never_in_prod(view):
    """
    Decorator that makes sure the view is never called
    on production environment.
    This is useful for exposing some functionalities to testers /
    other staff members.
    """
    def wrapper(request, *args, **kwargs):
        installation = getattr(settings, 'INSTALLATION', None)
        not_allwed_msg = "Not allowed in production"
        if installation is not None and  installation == settings.PRODUCTION:
            suspicious_logger.warn("A failed attempt at staff only testers", extra={
                    'request': request,
                    'view': view.__name__,
                    'data': {
                        'username': request.user
                     },
            })
            return HttpResponseForbidden(not_allwed_msg)
        return view(request, *args, **kwargs)
    return wraps(view)(wrapper)


def staff_member_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a staff
    member, displaying the login page if necessary.
    """
    @wraps(view_func)
    def _checklogin(request, *args, **kwargs):
        if request.user.is_active and request.user.is_staff:
            # The user is valid. Continue to the admin page.
            return view_func(request, *args, **kwargs)
        return redirect_to_login(request.path)
    return _checklogin
