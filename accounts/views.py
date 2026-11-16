from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from .forms import ProfileForm, RegistrationForm
from .models import CustomUser


def home(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    return redirect("accounts:login")


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
            email_taken = CustomUser.objects.filter(email__iexact=email).exists()

            if username_taken:
                form.add_error("username", "This username is already taken.")
            if email_taken:
                form.add_error("email", "This email is already registered.")
            if not username_taken and not email_taken:
                raise
        else:
            messages.success(request, "Your PathImpact account was created. You can now sign in.")
            return redirect("accounts:login")

    return render(request, "accounts/register.html", {"form": form})


@login_required(login_url="accounts:login")
def dashboard(request):
    if request.user.role == CustomUser.Role.STUDENT:
        return redirect("accounts:student_dashboard")
    if request.user.role == CustomUser.Role.ADMINISTRATOR:
        return redirect("accounts:administrator_dashboard")
    raise PermissionDenied


@login_required(login_url="accounts:login")
def student_dashboard(request):
    if request.user.role != CustomUser.Role.STUDENT:
        raise PermissionDenied
    return render(
        request,
        "accounts/dashboard.html",
        {
            "page_title": "Student dashboard",
            "description": "View and update your personal PathImpact profile.",
        },
    )


@login_required(login_url="accounts:login")
def administrator_dashboard(request):
    if request.user.role != CustomUser.Role.ADMINISTRATOR:
        raise PermissionDenied
    return render(
        request,
        "accounts/dashboard.html",
        {
            "page_title": "Administrator dashboard",
            "description": "Review your administrator account and profile.",
        },
    )


@login_required(login_url="accounts:login")
def profile(request):
    return render(request, "accounts/profile.html")


@login_required(login_url="accounts:login")
@require_http_methods(["GET", "POST"])
def edit_profile(request):
    form = ProfileForm(
        request.POST if request.method == "POST" else None,
        instance=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile was updated.")
        return redirect("accounts:profile")

    return render(request, "accounts/edit_profile.html", {"form": form})

