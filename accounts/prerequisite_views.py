
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import (
    require_safe,
    require_http_methods,
)

from assessments.models import (
    AcademicProgram,
    SubjectPrerequisite,
)

from .academic_views import paginate
from .administrator_views import administrator_only
from .prerequisite_forms import PrerequisiteForm


@administrator_only
@require_safe
def prerequisites(request):

    query = request.GET.get("q", "").strip()
    program = request.GET.get("program", "")

    records = SubjectPrerequisite.objects.select_related(
        "prerequisite__program",
        "successor",
    )

    if query:
        records = records.filter(
            Q(prerequisite__code__icontains=query)
            | Q(prerequisite__name__icontains=query)
            | Q(successor__code__icontains=query)
            | Q(successor__name__icontains=query)
        )

    if (
        program.isascii()
        and program.isdecimal()
        and len(program) <= 9
    ):
        records = records.filter(
            prerequisite__program_id=int(program)
        )

    return render(
        request,
        "accounts/prerequisite_list.html",
        {
            "page": paginate(request, records),
            "query": query,
            "selected_program": program,
            "programs": AcademicProgram.objects.all(),
            "total": records.count(),
            "successor_count": (
                records.values("successor_id")
                .distinct()
                .count()
            ),
        },
    )


@administrator_only
@require_http_methods(["GET", "POST"])
@transaction.atomic
def prerequisite_edit(request, pk=None):

    if request.method == "POST":

        # Serialize graph edits through this workspace.
        list(
            AcademicProgram.objects
            .select_for_update()
            .order_by("pk")
            .values_list("pk", flat=True)
        )

    instance = (
        get_object_or_404(
            SubjectPrerequisite,
            pk=pk,
        )
        if pk is not None
        else None
    )

    form = PrerequisiteForm(
        request.POST if request.method == "POST" else None,
        instance=instance,
    )

    if request.method == "POST" and form.is_valid():

        try:
            with transaction.atomic():
                form.save()

        except IntegrityError:
            form.add_error(
                None,
                "The relationship conflicts with "
                "an existing record.",
            )

        else:
            messages.success(
                request,
                "Prerequisite saved successfully.",
            )

            return redirect("accounts:prerequisites")

    return render(
        request,
        "accounts/academic_form.html",
        {
            "form": form,
            "instance": instance,
            "heading": (
                "Edit prerequisite"
                if pk is not None
                else "Add prerequisite"
            ),
            "list_url": "accounts:prerequisites",
            "item_name": "prerequisite",
        },
    )


@administrator_only
@require_http_methods(["GET", "POST"])
@transaction.atomic
def prerequisite_delete(request, pk):

    if request.method == "POST":

        list(
            AcademicProgram.objects
            .select_for_update()
            .order_by("pk")
            .values_list("pk", flat=True)
        )

    record = get_object_or_404(
        SubjectPrerequisite.objects.select_related(
            "prerequisite",
            "successor",
        ),
        pk=pk,
    )

    if request.method == "POST":

        record.delete()

        messages.success(
            request,
            "Prerequisite deleted successfully.",
        )

        return redirect("accounts:prerequisites")

    return render(
        request,
        "accounts/prerequisite_delete.html",
        {"record": record},
    )
