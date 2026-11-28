
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import (
    require_http_methods,
    require_safe,
)

from assessments.models import AssessmentSession

from .access import (
    active_account_required,
    student_required,
    administrator_required,
)

from .forms import ProfileForm, RegistrationForm
from .models import CustomUser


# =========================================================
# STUDENT DASHBOARD STATISTICS
# =========================================================

def _student_context(user):

    assessments = AssessmentSession.objects.filter(
        user=user
    ).order_by("-started_at", "-pk")

    recent_assessments = list(assessments[:5])

    return {
        "assessment_count": assessments.count(),

        "completed_count": assessments.filter(
            completed_at__isnull=False
        ).count(),

        "latest_assessment": (
            recent_assessments[0]
            if recent_assessments
            else None
        ),

        "recent_assessments": recent_assessments,
    }


# =========================================================
# HOME
# =========================================================

@never_cache
@require_safe
def home(request):

    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    return redirect("accounts:login")


# =========================================================
# REGISTRATION
# =========================================================

@never_cache
@sensitive_post_parameters("password1", "password2")
@require_http_methods(["GET", "POST"])
def register(request):

    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    form = RegistrationForm(
        request.POST
        if request.method == "POST"
        else None
    )

    if request.method == "POST" and form.is_valid():

        username = form.cleaned_data["username"]
        email = form.cleaned_data["email"]

        try:

            with transaction.atomic():
                form.save()

        except IntegrityError as exc:

            if getattr(
                exc.__cause__,
                "sqlstate",
                None,
            ) != "23505":
                raise

            username_taken = CustomUser.objects.filter(
                username__iexact=username
            ).exists()

            email_taken = CustomUser.objects.filter(
                email__iexact=email
            ).exists()

            if username_taken:
                form.add_error(
                    "username",
                    "This username is already taken.",
                )

            if email_taken:
                form.add_error(
                    "email",
                    "This email is already registered.",
                )

            if not username_taken and not email_taken:
                raise

        else:

            messages.success(
                request,
                "Your PathImpact account was created. "
                "You can now sign in.",
            )

            return redirect("accounts:login")

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


# =========================================================
# ROLE-BASED DASHBOARD ROUTING
# =========================================================

@never_cache
@active_account_required
@require_safe
def dashboard(request):

    if request.user.role == CustomUser.Role.STUDENT:

        return redirect(
            "accounts:student_dashboard"
        )

    if request.user.role == CustomUser.Role.ADMINISTRATOR:

        return redirect(
            "accounts:administrator_dashboard"
        )

    raise PermissionDenied


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@never_cache
@student_required
@require_safe
def student_dashboard(request):

    context = {
        "page_title": "Dashboard",

        "description": (
            "Manage your competency self-assessments."
        ),

        "role_view": "student",

        **_student_context(request.user),
    }

    return render(
        request,
        "accounts/dashboard.html",
        context,
    )


# =========================================================
# LEGACY ADMINISTRATOR DASHBOARD
# =========================================================

@never_cache
@administrator_required
@require_safe
def administrator_dashboard(request):

    return redirect(
        "accounts:administrator_dashboard"
    )


# =========================================================
# USER PROFILE
# =========================================================

@never_cache
@active_account_required
@require_safe
def profile(request):

    return render(
        request,
        "accounts/profile.html",
    )


# =========================================================
# EDIT PROFILE
# =========================================================

@never_cache
@active_account_required
@require_http_methods(["GET", "POST"])
def edit_profile(request):

    if request.method == "POST":

        with transaction.atomic():

            account = CustomUser.objects.select_for_update().get(
                pk=request.user.pk
            )

            if not account.is_active:

                raise PermissionDenied

            if account.role not in CustomUser.Role.values:

                raise PermissionDenied

            form = ProfileForm(
                request.POST,
                instance=account,
            )

            if form.is_valid():

                updated_account = form.save(
                    commit=False
                )

                email = form.cleaned_data["email"]

                try:

                    with transaction.atomic():

                        updated_account.save(
                            update_fields=[
                                "first_name",
                                "last_name",
                                "email",
                            ]
                        )

                except IntegrityError as exc:

                    if getattr(
                        exc.__cause__,
                        "sqlstate",
                        None,
                    ) != "23505":

                        raise

                    email_taken = CustomUser.objects.exclude(
                        pk=account.pk
                    ).filter(
                        email__iexact=email
                    ).exists()

                    if not email_taken:

                        raise

                    form.add_error(
                        "email",
                        "This email is already registered.",
                    )

                else:

                    messages.success(
                        request,
                        "Your profile was updated.",
                    )

                    return redirect(
                        "accounts:profile"
                    )

    else:

        form = ProfileForm(
            instance=request.user
        )

    return render(
        request,
        "accounts/edit_profile.html",
        {"form": form},
    )
