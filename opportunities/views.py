from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import CustomUser

from .forms import ApplicationForm, OpportunityForm, ReviewForm
from .models import Application, Opportunity
from .permissions import role_required

STUDENT = CustomUser.Role.STUDENT
ADMIN = CustomUser.Role.ADMINISTRATOR


# ---------- Shared: browse + detail (READ) ----------
@login_required(login_url="accounts:login")
def opportunity_list(request):
    qs = Opportunity.objects.select_related("created_by")
    is_admin = request.user.role == ADMIN
    if not is_admin:
        qs = qs.filter(status=Opportunity.Status.OPEN)
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(location__icontains=q) | Q(description__icontains=q))
    if category in Opportunity.Category.values:
        qs = qs.filter(category=category)
    applied_ids = set()
    if not is_admin:
        applied_ids = set(
            request.user.applications.values_list("opportunity_id", flat=True)
        )
    return render(request, "opportunities/opportunity_list.html", {
        "opportunities": qs,
        "q": q,
        "category": category,
        "categories": Opportunity.Category.choices,
        "applied_ids": applied_ids,
        "is_admin": is_admin,
    })


@login_required(login_url="accounts:login")
def opportunity_detail(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk)
    if request.user.role != ADMIN and opp.status != Opportunity.Status.OPEN:
        my_app = request.user.applications.filter(opportunity=opp).first()
        if not my_app:
            raise Http404("Opportunity not found.")
    my_application = None
    if request.user.role == STUDENT:
        my_application = request.user.applications.filter(opportunity=opp).first()
    return render(request, "opportunities/opportunity_detail.html", {
        "opp": opp,
        "my_application": my_application,
        "is_admin": request.user.role == ADMIN,
    })




# ---------- Administrator: CREATE / UPDATE / DELETE opportunities ----------
@role_required(ADMIN)
@require_http_methods(["GET", "POST"])
def opportunity_create(request):
    form = OpportunityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        opp = form.save(commit=False)
        opp.created_by = request.user
        opp.save()
        messages.success(request, f"“{opp.title}” was published.")
        return redirect("opportunities:detail", pk=opp.pk)
    if request.method == "POST":
        messages.error(request, "Please fix the errors below.")
    return render(request, "opportunities/opportunity_form.html", {"form": form, "mode": "Create"})


@role_required(ADMIN)
@require_http_methods(["GET", "POST"])
def opportunity_edit(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk)
    form = OpportunityForm(request.POST or None, instance=opp)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Opportunity updated.")
        return redirect("opportunities:detail", pk=opp.pk)
    if request.method == "POST":
        messages.error(request, "Please fix the errors below.")
    return render(request, "opportunities/opportunity_form.html", {"form": form, "mode": "Edit", "opp": opp})


@role_required(ADMIN)
@require_http_methods(["GET", "POST"])
def opportunity_delete(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk)
    if request.method == "POST":
        title = opp.title
        opp.delete()
        messages.success(request, f"“{title}” and its applications were deleted.")
        return redirect("opportunities:list")
    return render(request, "opportunities/confirm_delete.html", {
        "title": f"Delete “{opp.title}”?",
        "detail": f"This also removes {opp.applications.count()} application(s). This cannot be undone.",
        "cancel_url": "opportunities:detail",
        "cancel_pk": opp.pk,
    })


# ---------- Student: CREATE / READ / UPDATE / DELETE own applications ----------
@role_required(STUDENT)
@require_http_methods(["GET", "POST"])
def apply(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk)
    if request.user.applications.filter(opportunity=opp).exists():
        messages.info(request, "You already applied to this opportunity.")
        return redirect("opportunities:my_applications")
    if not opp.is_accepting:
        messages.error(request, opp.closed_reason or "Applications are closed.")
        return redirect("opportunities:detail", pk=opp.pk)
    form = ApplicationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        app = form.save(commit=False)
        app.opportunity, app.applicant = opp, request.user
        app.save()
        messages.success(request, f"Application sent for “{opp.title}”. Good luck!")
        return redirect("opportunities:my_applications")
    if request.method == "POST":
        messages.error(request, "Please fix the errors below.")
    return render(request, "opportunities/application_form.html", {"form": form, "opp": opp, "mode": "Apply"})


@role_required(STUDENT)
def my_applications(request):
    apps = request.user.applications.select_related("opportunity")
    status = request.GET.get("status", "")
    if status in Application.Status.values:
        apps = apps.filter(status=status)
    return render(request, "opportunities/my_applications.html", {
        "applications": apps, "status": status, "statuses": Application.Status.choices,
    })


@role_required(STUDENT)
@require_http_methods(["GET", "POST"])
def application_edit(request, pk):
    app = get_object_or_404(Application, pk=pk, applicant=request.user)
    if app.status != Application.Status.PENDING:
        messages.error(request, "Only pending applications can be edited.")
        return redirect("opportunities:my_applications")
    form = ApplicationForm(request.POST or None, instance=app)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Application updated.")
        return redirect("opportunities:my_applications")
    if request.method == "POST":
        messages.error(request, "Please fix the errors below.")
    return render(request, "opportunities/application_form.html", {"form": form, "opp": app.opportunity, "mode": "Edit"})


@role_required(STUDENT)
@require_http_methods(["GET", "POST"])
def application_withdraw(request, pk):
    app = get_object_or_404(Application, pk=pk, applicant=request.user)
    if app.status == Application.Status.APPROVED:
        messages.error(request, "Approved applications cannot be withdrawn here. Contact an administrator.")
        return redirect("opportunities:my_applications")
    if request.method == "POST":
        app.delete()
        messages.success(request, "Application withdrawn.")
        return redirect("opportunities:my_applications")
    return render(request, "opportunities/confirm_delete.html", {
        "title": "Withdraw this application?",
        "detail": f"Your application to “{app.opportunity.title}” will be removed.",
        "cancel_url": "opportunities:my_applications",
    })


# ---------- Administrator: review applications ----------
@role_required(ADMIN)
def review_list(request):
    apps = Application.objects.select_related("opportunity", "applicant")
    status = request.GET.get("status", "")
    opp_id = request.GET.get("opportunity", "")
    if status in Application.Status.values:
        apps = apps.filter(status=status)
    if opp_id.isdigit():
        apps = apps.filter(opportunity_id=opp_id)
    return render(request, "opportunities/review_list.html", {
        "applications": apps, "status": status, "opp_id": opp_id,
        "statuses": Application.Status.choices,
        "all_opportunities": Opportunity.objects.all(),
    })


@role_required(ADMIN)
@require_http_methods(["GET", "POST"])
def review_application(request, pk):
    with transaction.atomic():
        app = get_object_or_404(
            Application.objects.select_related("opportunity", "applicant").select_for_update(of=("self",)),
            pk=pk,
        )
        form = ReviewForm(request.POST or None, instance=app)
        if request.method == "POST" and form.is_valid():
            form.save()
            messages.success(request, f"Application from {app.applicant.username} marked {app.get_status_display().lower()}.")
            return redirect("opportunities:review_list")
    if request.method == "POST":
        messages.error(request, "Please fix the errors below.")
    return render(request, "opportunities/review_form.html", {"form": form, "app": app})
