
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
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
    Competency,
    SubjectCompetency,
)

from .academic_views import paginate
from .administrator_views import administrator_only
from .competency_forms import CompetencyForm


@administrator_only
@require_safe
def competencies(request):

    query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "")

    catalog = Competency.objects.annotate(
        subject_count=Count(
            "subjectcompetency",
            distinct=True,
        )
    )

    total_count = catalog.count()

    mapped_count = catalog.filter(
        subject_count__gt=0
    ).count()

    unmapped_count = total_count - mapped_count

    records = catalog.order_by("code", "pk")

    if query:

        records = records.filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
            | Q(description__icontains=query)
        )

    if selected_status == "mapped":

        records = records.filter(
            subject_count__gt=0
        )

    elif selected_status == "unmapped":

        records = records.filter(
            subject_count=0
        )

    else:
        selected_status = ""

    context = {
        "page": paginate(request, records),
        "query": query,
        "selected_status": selected_status,
        "total_count": total_count,
        "mapped_count": mapped_count,
        "unmapped_count": unmapped_count,
        "filtered_count": records.count(),
    }

    return render(
        request,
        "accounts/competency_list.html",
        context,
    )


@administrator_only
@require_http_methods(["GET", "POST"])
def competency_edit(request, pk=None):

    instance = None

    if pk is not None:

        instance = get_object_or_404(
            Competency,
            pk=pk,
        )

    if request.method == "POST":

        try:

            with transaction.atomic():

                if pk is not None:

                    instance = get_object_or_404(
                        Competency.objects.select_for_update(),
                        pk=pk,
                    )

                form = CompetencyForm(
                    request.POST,
                    instance=instance,
                )

                if form.is_valid():

                    form.save()

                    if pk is None:
                        messages.success(
                            request,
                            "Competency created successfully.",
                        )
                    else:
                        messages.success(
                            request,
                            "Competency updated successfully.",
                        )

                    return redirect(
                        "accounts:competencies"
                    )

        except IntegrityError:

            form = CompetencyForm(
                request.POST,
                instance=instance,
            )

            form.is_valid()

            form.add_error(
                None,
                "The competency could not be saved. "
                "Check for duplicate or conflicting records.",
            )

    else:

        form = CompetencyForm(
            instance=instance
        )

    is_mapped = False

    if instance is not None:

        is_mapped = SubjectCompetency.objects.filter(
            competency=instance
        ).exists()

    context = {
        "form": form,
        "instance": instance,
        "is_mapped": is_mapped,
        "heading": (
            "Edit competency"
            if pk is not None
            else "Add competency"
        ),
    }

    return render(
        request,
        "accounts/competency_form.html",
        context,
    )


@administrator_only
@require_http_methods(["GET", "POST"])
def competency_delete(request, pk):

    record = get_object_or_404(
        Competency,
        pk=pk,
    )

    if request.method == "POST":

        try:

            with transaction.atomic():

                record = get_object_or_404(
                    Competency.objects.select_for_update(),
                    pk=pk,
                )

                if SubjectCompetency.objects.filter(
                    competency=record
                ).exists():

                    messages.error(
                        request,
                        "This competency cannot be deleted "
                        "because it is mapped to a subject.",
                    )

                    return redirect(
                        "accounts:competencies"
                    )

                record.delete()

        except (ProtectedError, IntegrityError):

            messages.error(
                request,
                "This competency is referenced by other "
                "records and cannot be deleted.",
            )

        else:

            messages.success(
                request,
                "Competency deleted successfully.",
            )

        return redirect(
            "accounts:competencies"
        )

    mapping_count = SubjectCompetency.objects.filter(
        competency=record
    ).count()

    context = {
        "record": record,
        "mapping_count": mapping_count,
    }

    return render(
        request,
        "accounts/competency_delete.html",
        context,
    )
