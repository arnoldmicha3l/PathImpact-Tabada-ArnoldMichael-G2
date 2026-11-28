from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
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
    Subject,
    Competency,
    SubjectCompetency,
    AssessmentResponse,
    CompetencyImpact,
)

from .academic_views import paginate
from .administrator_views import administrator_only
from .mapping_forms import MappingForm


def valid_filter(value):

    return (
        value.isascii()
        and value.isdecimal()
        and len(value) <= 18
    )


def protected_mapping(pk):

    return (
        AssessmentResponse.objects.filter(
            subject_competency_id=pk
        ).exists()
        or CompetencyImpact.objects.filter(
            subject_competency_id=pk
        ).exists()
    )


def lock_programs():

    list(
        AcademicProgram.objects
        .select_for_update()
        .order_by("pk")
        .values_list("pk", flat=True)
    )


@administrator_only
@require_safe
def mappings(request):

    query = request.GET.get("q", "").strip()

    selected_program = request.GET.get(
        "program", ""
    )

    selected_subject = request.GET.get(
        "subject", ""
    )

    selected_status = request.GET.get(
        "status", ""
    )

    catalog = SubjectCompetency.objects.select_related(
        "subject__program",
        "competency",
    ).annotate(
        is_protected=(
            Exists(
                AssessmentResponse.objects.filter(
                    subject_competency_id=OuterRef("pk")
                )
            )
            | Exists(
                CompetencyImpact.objects.filter(
                    subject_competency_id=OuterRef("pk")
                )
            )
        )
    )

    total_count = catalog.count()

    subject_count = Subject.objects.count()

    mapped_count = Subject.objects.filter(
        Exists(
            SubjectCompetency.objects.filter(
                subject_id=OuterRef("pk")
            )
        )
    ).count()

    unmapped_count = subject_count - mapped_count

    unmapped_subjects = Subject.objects.select_related(
        "program"
    ).filter(
        ~Exists(
            SubjectCompetency.objects.filter(
                subject_id=OuterRef("pk")
            )
        )
    ).order_by(
        "program__code",
        "code",
    )

    records = catalog.order_by(
        "subject__program__code",
        "subject__code",
        "competency__code",
        "pk",
    )

    subjects = Subject.objects.select_related(
        "program"
    ).order_by(
        "program__code",
        "code",
    )

    if query:

        records = records.filter(
            Q(subject__code__icontains=query)
            | Q(subject__name__icontains=query)
            | Q(competency__code__icontains=query)
            | Q(competency__name__icontains=query)
            | Q(subject__program__code__icontains=query)
        )

    if valid_filter(selected_program):

        records = records.filter(
            subject__program_id=int(selected_program)
        )

        subjects = subjects.filter(
            program_id=int(selected_program)
        )

        unmapped_subjects = unmapped_subjects.filter(
            program_id=int(selected_program)
        )

    else:

        selected_program = ""

    if valid_filter(selected_subject):

        records = records.filter(
            subject_id=int(selected_subject)
        )

    else:

        selected_subject = ""

    if selected_status == "protected":

        records = records.filter(
            is_protected=True
        )

    elif selected_status == "editable":

        records = records.filter(
            is_protected=False
        )

    else:

        selected_status = ""

    context = {
        "page": paginate(request, records),
        "query": query,
        "programs": AcademicProgram.objects.order_by("code"),
        "subjects": subjects,
        "selected_program": selected_program,
        "selected_subject": selected_subject,
        "selected_status": selected_status,
        "total_count": total_count,
        "mapped_count": mapped_count,
        "unmapped_count": unmapped_count,
        "filtered_count": records.count(),
        "unmapped_subjects": unmapped_subjects[:10],
        "unmapped_filtered_count": unmapped_subjects.count(),
    }

    return render(
        request,
        "accounts/mapping_list.html",
        context,
    )


@administrator_only
@require_http_methods(["GET", "POST"])
def mapping_edit(request, pk=None):

    instance = None

    if pk is not None:

        instance = get_object_or_404(
            SubjectCompetency.objects.select_related(
                "subject__program",
                "competency",
            ),
            pk=pk,
        )

    if request.method == "POST":

        try:

            with transaction.atomic():

                lock_programs()

                old_subject_id = None
                old_competency_id = None

                if pk is not None:

                    instance = get_object_or_404(
                        SubjectCompetency.objects.select_for_update(),
                        pk=pk,
                    )

                    old_subject_id = instance.subject_id

                    old_competency_id = (
                        instance.competency_id
                    )

                    if protected_mapping(pk):

                        messages.error(
                            request,
                            "This mapping is protected by "
                            "existing assessment responses "
                            "or competency impacts.",
                        )

                        return redirect(
                            "accounts:mapping_edit",
                            pk=pk,
                        )

                form = MappingForm(
                    request.POST,
                    instance=instance,
                )

                if form.is_valid():

                    new_subject = (
                        form.cleaned_data["subject"]
                    )

                    competency_ids = [
                        form.cleaned_data["competency"].pk
                    ]

                    if old_competency_id is not None:

                        competency_ids.append(
                            old_competency_id
                        )

                    list(
                        Competency.objects.select_for_update()
                        .filter(pk__in=competency_ids)
                        .order_by("pk")
                    )

                    removes_last_prototype_mapping = (
                        old_subject_id is not None
                        and old_subject_id != new_subject.pk
                        and Subject.objects.filter(
                            pk=old_subject_id,
                            program__code="BSIT",
                            code="DB-FND",
                        ).exists()
                        and not SubjectCompetency.objects.filter(
                            subject_id=old_subject_id
                        ).exclude(pk=pk).exists()
                    )

                    if removes_last_prototype_mapping:

                        form.add_error(
                            "subject",
                            "The last competency mapping "
                            "for the current self-assessment "
                            "subject cannot be moved.",
                        )

                    else:

                        form.save()

                        messages.success(
                            request,
                            (
                                "Competency mapping created successfully."
                                if pk is None
                                else "Competency mapping updated successfully."
                            ),
                        )

                        return redirect(
                            "accounts:mappings"
                        )

        except IntegrityError:

            original = (
                get_object_or_404(
                    SubjectCompetency,
                    pk=pk,
                )
                if pk is not None
                else None
            )

            instance = original

            form = MappingForm(
                request.POST,
                instance=original,
            )

            form.is_valid()

            form.add_error(
                None,
                "The mapping could not be saved. "
                "Check for duplicate or conflicting records.",
            )

    else:

        initial = {}

        subject_id = request.GET.get(
            "subject", ""
        )

        if pk is None and valid_filter(subject_id):

            initial["subject"] = int(subject_id)

        form = MappingForm(
            instance=instance,
            initial=initial,
        )

    is_protected = (
        protected_mapping(pk)
        if pk is not None
        else False
    )

    if pk is not None:

        instance = get_object_or_404(
            SubjectCompetency.objects.select_related(
                "subject__program",
                "competency",
            ),
            pk=pk,
        )

    context = {
        "form": form,
        "instance": instance,
        "is_protected": is_protected,
        "heading": (
            "Edit competency mapping"
            if pk is not None
            else "Add competency mapping"
        ),
    }

    return render(
        request,
        "accounts/mapping_form.html",
        context,
    )


@administrator_only
@require_http_methods(["GET", "POST"])
def mapping_delete(request, pk):

    record = get_object_or_404(
        SubjectCompetency.objects.select_related(
            "subject__program",
            "competency",
        ),
        pk=pk,
    )

    if request.method == "POST":

        try:

            with transaction.atomic():

                lock_programs()

                record = get_object_or_404(
                    SubjectCompetency.objects.select_for_update(),
                    pk=pk,
                )

                Competency.objects.select_for_update().get(
                    pk=record.competency_id
                )

                if protected_mapping(pk):

                    messages.error(
                        request,
                        "This mapping cannot be removed "
                        "because assessment responses or "
                        "competency impacts reference it.",
                    )

                    return redirect(
                        "accounts:mappings"
                    )

                is_prototype_mapping = (
                    Subject.objects.filter(
                        pk=record.subject_id,
                        program__code="BSIT",
                        code="DB-FND",
                    ).exists()
                )

                if (
                    is_prototype_mapping
                    and not SubjectCompetency.objects.filter(
                        subject_id=record.subject_id
                    ).exclude(pk=pk).exists()
                ):

                    messages.error(
                        request,
                        "The last competency mapping "
                        "for the current self-assessment "
                        "subject cannot be removed.",
                    )

                    return redirect(
                        "accounts:mappings"
                    )

                record.delete()

        except (ProtectedError, IntegrityError):

            messages.error(
                request,
                "This mapping is referenced by other records "
                "and cannot be removed.",
            )

        else:

            messages.success(
                request,
                "Competency mapping removed successfully.",
            )

        return redirect(
            "accounts:mappings"
        )

    return render(
        request,
        "accounts/mapping_delete.html",
        {
            "record": record,
            "is_protected": protected_mapping(pk),
        },
    )