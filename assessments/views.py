from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_safe, require_http_methods

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

def student_only(view):
    @login_required(login_url="accounts:login")
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.user.role != "student":
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped
from .forms import AssessmentForm
from .models import AssessmentSession, AssessmentResponse, SubjectCompetency


def own(request):
    return AssessmentSession.objects.filter(user=request.user)


@student_only
@require_safe
def index(request):
    return render(request, "assessments/index.html", {"items": own(request)})


@student_only
@require_safe
def detail(request, pk):
    attempt = get_object_or_404(own(request), pk=pk)
    return render(request, "assessments/detail.html", {
        "attempt": attempt,
        "responses": attempt.responses.select_related("subject_competency__competency", "subject_competency__subject")
        .order_by("subject_competency__subject__code", "subject_competency__competency__code"),
    })


@student_only
@require_http_methods(["GET", "POST"])
@transaction.atomic
def edit(request, pk=None):
    queryset = own(request)
    if request.method == "POST":
        queryset = queryset.select_for_update()
    attempt = get_object_or_404(queryset, pk=pk) if pk is not None else None
    ratings = dict(attempt.responses.values_list("subject_competency_id", "self_rating")) if attempt else {}
    catalog = SubjectCompetency.objects.select_related("competency", "subject")
    catalog = list(catalog.filter(pk__in=ratings) if attempt else catalog.filter(subject__program__code="BSIT", subject__code="DB-FND"))
    form = AssessmentForm(request.POST if request.method == "POST" else None, competencies=catalog, ratings=ratings)
    if request.method == "POST" and form.is_valid():
        if attempt is None:
            attempt = AssessmentSession.objects.create(user=request.user, completed_at=timezone.now())
        else:
            attempt.responses.all().delete()
        AssessmentResponse.objects.bulk_create(form.responses(attempt))
        messages.success(request, "Self-assessment saved." if pk is None else "Self-assessment updated.")
        return redirect("assessment_detail", pk=attempt.pk)
    return render(request, "assessments/form.html", {"form": form, "attempt": attempt})


@student_only
@require_http_methods(["GET", "POST"])
@transaction.atomic
def delete(request, pk):
    queryset = own(request)
    if request.method == "POST":
        queryset = queryset.select_for_update()
    attempt = get_object_or_404(queryset, pk=pk)
    if request.method == "POST":
        attempt.delete()
        messages.success(request, "Self-assessment deleted.")
        return redirect("assessment_index")
    return render(request, "assessments/delete.html", {"attempt": attempt})
