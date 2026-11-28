from .result_services import generate_assessment_results


from django.contrib import messages
from django.views.decorators.cache import never_cache
from accounts.access import student_required
from django.db import transaction
from django.db.models import Avg, Count

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.utils import timezone

from django.views.decorators.http import (
    require_safe,
    require_http_methods,
)

from .forms import AssessmentForm

from .models import (
    AcademicProgram,
    AssessmentSession,
    AssessmentResponse,
    SubjectCompetency,
)


def student_only(view):
    return never_cache(student_required(view))


def own(request):

    return AssessmentSession.objects.filter(
        user=request.user
    )


def lock_academic_catalog():

    list(
        AcademicProgram.objects
        .select_for_update()
        .order_by("pk")
        .values_list("pk", flat=True)
    )


@student_only
@require_safe
def index(request):

    items = own(request).annotate(
        average_rating=Avg("responses__self_rating"),
        response_count=Count("responses"),
    ).order_by(
        "-started_at",
        "-pk",
    )

    return render(
        request,
        "assessments/index.html",
        {
            "items": items,
        },
    )


@student_only
@require_safe
def detail(request, pk):

    attempt = get_object_or_404(
        own(request),
        pk=pk,
    )

    responses = list(
        attempt.responses.select_related(
            "subject_competency__competency",
            "subject_competency__subject",
        ).order_by(
            "subject_competency__subject__code",
            "subject_competency__competency__code",
        )
    )

    response_count = len(responses)

    average_rating = (
        sum(
            response.self_rating
            for response in responses
        ) / response_count
        if response_count
        else None
    )

    rating_distribution = [
        {
            "rating": rating,
            "count": sum(
                response.self_rating == rating
                for response in responses
            ),
        }
        for rating in range(1, 6)
    ]

    return render(
        request,
        "assessments/detail.html",
        {
            "attempt": attempt,
            "responses": responses,
            "response_count": response_count,
            "average_rating": average_rating,
            "rating_distribution": rating_distribution,
        },
    )


@student_only
@require_http_methods(["GET", "POST"])
@transaction.atomic
def edit(request, pk=None):

    queryset = own(request)

    if request.method == "POST":

        lock_academic_catalog()

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

    if request.method == "POST":

        catalog = catalog.select_for_update(
            of=("self",)
        ).order_by("pk")

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

        generate_assessment_results(
            user=request.user,
            assessment_id=attempt.pk,
        )

        messages.success(
            request,
            (
                "Self-assessment saved."
                if pk is None
                else "Self-assessment updated."
            ),
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


@student_only
@require_http_methods(["GET", "POST"])
@transaction.atomic
def delete(request, pk):

    queryset = own(request)

    if request.method == "POST":

        lock_academic_catalog()

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