
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import CustomUser


def active_account_required(view):

    @login_required(login_url="accounts:login")
    @wraps(view)
    def wrapped(request, *args, **kwargs):

        if not request.user.is_active:
            raise PermissionDenied

        if request.user.role not in (
            CustomUser.Role.STUDENT,
            CustomUser.Role.ADMINISTRATOR,
        ):
            raise PermissionDenied

        return view(request, *args, **kwargs)

    return wrapped


def role_required(*allowed_roles):

    def decorator(view):

        @active_account_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):

            if request.user.role not in allowed_roles:
                raise PermissionDenied

            return view(request, *args, **kwargs)

        return wrapped

    return decorator


student_required = role_required(
    CustomUser.Role.STUDENT
)


administrator_required = role_required(
    CustomUser.Role.ADMINISTRATOR
)
