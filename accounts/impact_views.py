from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import (
    require_http_methods,
    require_safe,
)

from assessments.models import (
    AcademicProgram,
    AssessmentResponse,
    CompetencyImpact,
    SubjectCompetency,
    SubjectPrerequisite,
)

from .academic_views import paginate
from .administrator_views import administrator_only
from .impact_forms import ImpactForm


def impact_catalog():

    return CompetencyImpact.objects.select_related(
        "prerequisite__prerequisite__program",
        "prerequisite__successor",
        "subject_competency__competency",
        "subject_competency__subject",
    )


def lock_programs():

    list(
        AcademicProgram.objects
        .select_for_update()
        .order_by("pk")
        .values_list("pk", flat=True)
    )


def has_assessment_responses(mapping_id):

    return AssessmentResponse.objects.filter(
        subject_competency_id=mapping_id
    ).exists()


@administrator_only
@require_safe
def impacts(request):

    query = request.GET.get("q", "").strip()
    program = request.GET.get("program", "")
    relevance = request.GET.get("relevance", "")

    catalog = impact_catalog()

    total_count = catalog.count()

    affected_count = (
        catalog.order_by()
        .values("prerequisite__successor_id")
        .distinct()
        .count()
    )

    high_count = catalog.filter(
        relevance=CompetencyImpact.Relevance.HIGH
    ).count()

    records = catalog

    if query:

        records = records.filter(
            Q(
                prerequisite__prerequisite__code__icontains=query
            )
            | Q(
                prerequisite__prerequisite__name__icontains=query
            )
            | Q(
                prerequisite__successor__code__icontains=query
            )
            | Q(
                prerequisite__successor__name__icontains=query
            )
            | Q(
                subject_competency__competency__code__icontains=query
            )
            | Q(
                subject_competency__competency__name__icontains=query
            )
        )

    if (
        program.isascii()
        and program.isdecimal()
        and len(program) <= 9
    ):

        records = records.filter(
            prerequisite__prerequisite__program_id=int(program)
        )

    else:

        program = ""

    if relevance in ["1", "2", "3"]:

        records = records.filter(
            relevance=int(relevance)
        )

    else:

        relevance = ""

    return render(
        request,
        "accounts/impact_list.html",
        {
            "page": paginate(request, records),
            "query": query,
            "programs": AcademicProgram.objects.order_by("code"),
            "selected_program": program,
            "selected_relevance": relevance,
            "relevance_choices": CompetencyImpact.Relevance.choices,
            "total_count": total_count,
            "affected_count": affected_count,
            "high_count": high_count,
            "filtered_count": records.count(),
        },
    )


@administrator_only
@require_http_methods(["GET", "POST"])
def impact_edit(request, pk=None):

    instance = (
        get_object_or_404(
            CompetencyImpact,
            pk=pk,
        )
        if pk is not None
        else None
    )

    if request.method == "POST":

        try:

            with transaction.atomic():

                lock_programs()

                if pk is not None:

                    instance = get_object_or_404(
                        CompetencyImpact.objects.select_for_update(),
                        pk=pk,
                    )

                    old_mapping_id = (
                        instance.subject_competency_id
                    )

                else:

                    old_mapping_id = None

                form = ImpactForm(
                    request.POST,
                    instance=instance,
                )

                if form.is_valid():

                    relationship = (
                        SubjectPrerequisite.objects
                        .select_for_update()
                        .get(
                            pk=form.cleaned_data[
                                "prerequisite"
                            ].pk
                        )
                    )

                    mapping_ids = [
                        form.cleaned_data[
                            "subject_competency"
                        ].pk
                    ]

                    if old_mapping_id is not None:

                        mapping_ids.append(
                            old_mapping_id
                        )

                    locked_mappings = {
                        item.pk: item
                        for item in (
                            SubjectCompetency.objects
                            .select_for_update()
                            .filter(pk__in=mapping_ids)
                            .order_by("pk")
                        )
                    }

                    mapping = locked_mappings.get(
                        form.cleaned_data[
                            "subject_competency"
                        ].pk
                    )

                    if (
                        mapping is None
                        or mapping.subject_id
                        != relationship.prerequisite_id
                    ):

                        form.add_error(
                            "subject_competency",
                            "The academic relationship "
                            "is no longer compatible.",
                        )

                    elif (
                        old_mapping_id is not None
                        and form.has_changed()
                        and has_assessment_responses(
                            old_mapping_id
                        )
                    ):

                        form.add_error(
                            None,
                            "This impact is protected by "
                            "existing assessment responses.",
                        )

                    else:

                        impact = form.save(commit=False)

                        impact.prerequisite = relationship
                        impact.subject_competency = mapping

                        impact.save()

                        messages.success(
                            request,
                            "Competency impact saved successfully.",
                        )

                        return redirect(
                            "accounts:impacts"
                        )

        except (
            IntegrityError,
            SubjectPrerequisite.DoesNotExist,
        ):

            instance = (
                get_object_or_404(
                    CompetencyImpact,
                    pk=pk,
                )
                if pk is not None
                else None
            )

            form = ImpactForm(
                request.POST,
                instance=instance,
            )

            form.is_valid()

            form.add_error(
                None,
                "The impact could not be saved safely. "
                "Check the selected relationships.",
            )

    else:

        form = ImpactForm(
            instance=instance
        )

    return render(
        request,
        "accounts/academic_form.html",
        {
            "form": form,
            "instance": instance,
            "heading": (
                "Edit competency impact"
                if pk is not None
                else "Add competency impact"
            ),
            "list_url": "accounts:impacts",
            "item_name": "competency impact",
        },
    )


@administrator_only
@require_http_methods(["GET", "POST"])
def impact_delete(request, pk):

    record = get_object_or_404(
        impact_catalog(),
        pk=pk,
    )

    if request.method == "POST":

        try:

            with transaction.atomic():

                lock_programs()

                record = get_object_or_404(
                    CompetencyImpact.objects.select_for_update(),
                    pk=pk,
                )

                SubjectCompetency.objects.select_for_update().get(
                    pk=record.subject_competency_id
                )

                if has_assessment_responses(
                    record.subject_competency_id
                ):

                    messages.error(
                        request,
                        "This impact is protected by "
                        "existing assessment responses.",
                    )

                    return redirect(
                        "accounts:impacts"
                    )

                record.delete()

        except (ProtectedError, IntegrityError):

            messages.error(
                request,
                "The impact could not be removed safely.",
            )

        else:

            messages.success(
                request,
                "Competency impact removed successfully.",
            )

        return redirect(
            "accounts:impacts"
        )

    return render(
        request,
        "accounts/impact_delete.html",
        {
            "record": record,
            "is_protected": has_assessment_responses(
                record.subject_competency_id
            ),
        },
    )