
from django.contrib import messages
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import (
    require_safe,
    require_http_methods,
)

from accounts.access import student_required

from .forms import AssessmentForm

from .models import (
    AssessmentSession,
    AssessmentResponse,
    SubjectCompetency,
)


# =========================================================
# ASSESSMENT OWNERSHIP
# =========================================================

def own(request):

    return AssessmentSession.objects.filter(
        user=request.user
    )


# =========================================================
# ASSESSMENT HISTORY
# =========================================================

@student_required
@require_safe
@never_cache
def index(request):

    return render(
        request,
        "assessments/index.html",
        {
            "items": own(request),
        },
    )


# =========================================================
# ASSESSMENT DETAILS
# =========================================================

@student_required
@require_safe
@never_cache
def detail(request, pk):

    attempt = get_object_or_404(
        own(request),
        pk=pk,
    )

    responses = attempt.responses.select_related(

        "subject_competency__competency",

        "subject_competency__subject",

    ).order_by(

        "subject_competency__subject__code",

        "subject_competency__competency__code",
    )

    return render(
        request,
        "assessments/detail.html",
        {
            "attempt": attempt,
            "responses": responses,
        },
    )


# =========================================================
# CREATE AND UPDATE SELF-ASSESSMENT
# =========================================================

@student_required
@require_http_methods(["GET", "POST"])
@never_cache
@transaction.atomic
def edit(request, pk=None):

    queryset = own(request)

    if request.method == "POST":

        queryset = queryset.select_for_update()

    attempt = (

        get_object_or_404(
            queryset,
            pk=pk,
        )

        if pk is not None
        else None
    )

    ratings = (

        dict(
            attempt.responses.values_list(
                "subject_competency_id",
                "self_rating",
            )
        )

        if attempt
        else {}
    )

    catalog = SubjectCompetency.objects.select_related(
        "competency",
        "subject",
    )

    if attempt:

        catalog = catalog.filter(
            pk__in=ratings
        )

    else:

        catalog = catalog.filter(
            subject__program__code="BSIT",
            subject__code="DB-FND",
        )

    catalog = list(catalog)

    form = AssessmentForm(

        request.POST
        if request.method == "POST"
        else None,

        competencies=catalog,

        ratings=ratings,
    )

    if request.method == "POST" and form.is_valid():

        if attempt is None:

            attempt = AssessmentSession.objects.create(
                user=request.user,
                completed_at=timezone.now(),
            )

        else:

            attempt.responses.all().delete()

            if attempt.completed_at is None:

                attempt.completed_at = timezone.now()

                attempt.save(
                    update_fields=["completed_at"]
                )

        AssessmentResponse.objects.bulk_create(
            form.responses(attempt)
        )

        messages.success(

            request,

            "Self-assessment saved."
            if pk is None
            else "Self-assessment updated.",
        )

        return redirect(
            "assessment_detail",
            pk=attempt.pk,
        )

    return render(
        request,
        "assessments/form.html",
        {
            "form": form,
            "attempt": attempt,
        },
    )


# =========================================================
# DELETE SELF-ASSESSMENT
# =========================================================

@student_required
@require_http_methods(["GET", "POST"])
@never_cache
@transaction.atomic
def delete(request, pk):

    queryset = own(request)

    if request.method == "POST":

        queryset = queryset.select_for_update()

    attempt = get_object_or_404(
        queryset,
        pk=pk,
    )

    if request.method == "POST":

        attempt.delete()

        messages.success(
            request,
            "Self-assessment deleted.",
        )

        return redirect(
            "assessment_index"
        )

    return render(
        request,
        "assessments/delete.html",
        {
            "attempt": attempt,
        },
    )
