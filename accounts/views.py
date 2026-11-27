from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from assessments.models import AssessmentSession

from .forms import ProfileForm, RegistrationForm
from .models import CustomUser


# Dashboard statistics

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


# Home

def home(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    return redirect("accounts:login")


# Registration

@sensitive_post_parameters("password1", "password2")
@require_http_methods(["GET", "POST"])
def register(request):

    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    form = RegistrationForm(
        request.POST if request.method == "POST" else None
    )

    if request.method == "POST" and form.is_valid():

        username = form.cleaned_data["username"]
        email = form.cleaned_data["email"]

        try:
            with transaction.atomic():
                form.save()

        except IntegrityError as exc:

            if getattr(exc.__cause__, "sqlstate", None) != "23505":
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
                    "This username is already taken."
                )

            if email_taken:
                form.add_error(
                    "email",
                    "This email is already registered."
                )

            if not username_taken and not email_taken:
                raise

        else:
            messages.success(
                request,
                "Your PathImpact account was created. "
                "You can now sign in."
            )

            return redirect("accounts:login")

    return render(
        request,
        "accounts/register.html",
        {"form": form}
    )


# Role-based dashboard routing

@login_required(login_url="accounts:login")
@require_http_methods(["GET"])
def dashboard(request):

    if request.user.role == CustomUser.Role.STUDENT:
        return redirect("accounts:student_dashboard")

    if request.user.role == CustomUser.Role.ADMINISTRATOR:
        return redirect("accounts:administrator_dashboard")

    raise PermissionDenied


# Student dashboard

@login_required(login_url="accounts:login")
@require_http_methods(["GET"])
def student_dashboard(request):

    if request.user.role != CustomUser.Role.STUDENT:
        raise PermissionDenied

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
        context
    )


# Administrator dashboard

@login_required(login_url="accounts:login")
@require_http_methods(["GET"])
def administrator_dashboard(request):

    if request.user.role != CustomUser.Role.ADMINISTRATOR:
        raise PermissionDenied

    context = {
        "page_title": "Administrator dashboard",
        "description": (
            "Access your administrator account "
            "and manage your personal profile."
        ),
        "role_view": "administrator",
    }

    return render(
        request,
        "accounts/dashboard.html",
        context
    )


# User profile

@login_required(login_url="accounts:login")
@require_http_methods(["GET"])
def profile(request):

    return render(
        request,
        "accounts/profile.html"
    )


# Edit profile

@login_required(login_url="accounts:login")
@require_http_methods(["GET", "POST"])
def edit_profile(request):

    form = ProfileForm(
        request.POST if request.method == "POST" else None,
        instance=request.user,
    )

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Your profile was updated."
        )

        return redirect("accounts:profile")

    return render(
        request,
        "accounts/edit_profile.html",
        {"form": form}
    )