
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

from assessments.models import (
    AcademicProgram,
    AssessmentSession,
    Competency,
    Subject,
)

from .access import (
    active_account_required,
    administrator_required,
    student_required,
)

from .forms import ProfileForm, RegistrationForm
from .models import CustomUser


# =========================================================
# PUBLIC ACCOUNT FUNCTIONS
# =========================================================

@require_safe
def home(request):

    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    return redirect("accounts:login")


@sensitive_post_parameters("password1", "password2")
@require_http_methods(["GET", "POST"])
@never_cache
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

@active_account_required
@require_safe
@never_cache
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

@student_required
@require_safe
@never_cache
def student_dashboard(request):

    assessments = AssessmentSession.objects.filter(
        user=request.user
    )

    completed = assessments.filter(
        completed_at__isnull=False
    )

    context = {

        "page_title": "Student dashboard",

        "description": (
            "Review your academic competencies "
            "and manage your self-assessments."
        ),

        "role_view": "student",

        "stats": [
            (
                "01",
                "Self-assessments",
                assessments.count(),
            ),
            (
                "02",
                "Completed",
                completed.count(),
            ),
            (
                "03",
                "In progress",
                assessments.filter(
                    completed_at__isnull=True
                ).count(),
            ),
        ],

        "recent_assessments": assessments.order_by(
            "-started_at",
            "-pk",
        )[:5],
    }

    return render(
        request,
        "accounts/dashboard.html",
        context,
    )


# =========================================================
# ADMINISTRATOR DASHBOARD
# =========================================================

@administrator_required
@require_safe
@never_cache
def administrator_dashboard(request):

    context = {

        "page_title": "Administrator dashboard",

        "description": (
            "Monitor academic reference data "
            "and student assessment activity."
        ),

        "role_view": "administrator",

        "stats": [
            (
                "01",
                "Registered students",
                CustomUser.objects.filter(
                    role=CustomUser.Role.STUDENT
                ).count(),
            ),
            (
                "02",
                "Academic programs",
                AcademicProgram.objects.count(),
            ),
            (
                "03",
                "Academic subjects",
                Subject.objects.count(),
            ),
            (
                "04",
                "Competencies",
                Competency.objects.count(),
            ),
        ],

        "completed_count": AssessmentSession.objects.filter(
            user__role=CustomUser.Role.STUDENT,
            completed_at__isnull=False,
        ).count(),
    }

    return render(
        request,
        "accounts/dashboard.html",
        context,
    )


# =========================================================
# ACCOUNT PROFILE
# =========================================================

@active_account_required
@require_safe
@never_cache
def profile(request):

    return render(
        request,
        "accounts/profile.html",
    )


@active_account_required
@require_http_methods(["GET", "POST"])
@never_cache
def edit_profile(request):

    form = ProfileForm(

        request.POST
        if request.method == "POST"
        else None,

        instance=request.user,
    )

    if request.method == "POST" and form.is_valid():

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

            email = form.cleaned_data["email"]

            email_taken = CustomUser.objects.exclude(
                pk=request.user.pk
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

    return render(
        request,
        "accounts/edit_profile.html",
        {"form": form},
    )
