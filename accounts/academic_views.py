
from django.contrib import messages
from django.core.paginator import Paginator
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

from assessments.models import AcademicProgram, Subject

from .academic_forms import ProgramForm, SubjectForm
from .administrator_views import administrator_only


def lock_academic_catalog():

    list(
        AcademicProgram.objects
        .select_for_update()
        .order_by("pk")
        .values_list("pk", flat=True)
    )


def paginate(request, queryset):

    paginator = Paginator(queryset, 10)

    return paginator.get_page(
        request.GET.get("page")
    )


@administrator_only
@require_safe
def programs(request):

    query = request.GET.get("q", "").strip()

    records = AcademicProgram.objects.annotate(
        subject_count=Count("subject")
    ).order_by("code", "pk")

    if query:

        records = records.filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
        )

    page = paginate(request, records)

    return render(
        request,
        "accounts/academic_list.html",
        {
            "module": "programs",
            "heading": "Programs",
            "description": "Manage supported academic programs.",
            "page": page,
            "query": query,
            "total": records.count(),
            "create_url": "accounts:program_create",
            "edit_url": "accounts:program_edit",
            "delete_url": "accounts:program_delete",
            "list_url": "accounts:programs",
            "item_name": "program",
        },
    )


@administrator_only
@require_safe
def subjects(request):

    query = request.GET.get("q", "").strip()

    program = request.GET.get("program", "")
    year = request.GET.get("year", "")
    semester = request.GET.get("semester", "")

    records = Subject.objects.select_related(
        "program"
    ).order_by(
        "program__code",
        "year_level",
        "semester",
        "code",
        "pk",
    )

    if query:

        records = records.filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
        )

    if (
        program.isascii()
        and program.isdecimal()
        and len(program) <= 18
    ):

        records = records.filter(
            program_id=int(program)
        )

    if year in ["1", "2", "3", "4"]:

        records = records.filter(
            year_level=int(year)
        )

    if semester in ["1", "2", "3"]:

        records = records.filter(
            semester=int(semester)
        )

    page = paginate(request, records)

    return render(
        request,
        "accounts/academic_list.html",
        {
            "module": "subjects",
            "heading": "Subjects",
            "description": "Manage academic reference subjects.",
            "page": page,
            "query": query,
            "total": records.count(),
            "programs": AcademicProgram.objects.all(),
            "years": Subject.YearLevel.choices,
            "semesters": Subject.Semester.choices,
            "selected_program": program,
            "selected_year": year,
            "selected_semester": semester,
            "create_url": "accounts:subject_create",
            "edit_url": "accounts:subject_edit",
            "delete_url": "accounts:subject_delete",
            "list_url": "accounts:subjects",
            "item_name": "subject",
        },
    )


def save_record(
    request,
    pk,
    model,
    form_class,
    label,
    list_url,
):

    if request.method == "POST":

        with transaction.atomic():

            lock_academic_catalog()

            instance = (
                get_object_or_404(
                    model.objects.select_for_update(),
                    pk=pk,
                )
                if pk is not None
                else None
            )

            form = form_class(
                request.POST,
                instance=instance,
            )

            if form.is_valid():

                try:

                    with transaction.atomic():

                        form.save()

                except IntegrityError:

                    form.add_error(
                        None,
                        "The record could not be saved. "
                        "Check for duplicate or conflicting "
                        "information.",
                    )

                else:

                    messages.success(
                        request,
                        f"{label} updated successfully."
                        if pk is not None
                        else f"{label} created successfully.",
                    )

                    return redirect(list_url)

    else:

        instance = (
            get_object_or_404(model, pk=pk)
            if pk is not None
            else None
        )

        form = form_class(
            instance=instance,
        )

    return render(
        request,
        "accounts/academic_form.html",
        {
            "form": form,
            "heading": (
                f"Edit {label.lower()}"
                if pk is not None
                else f"Add {label.lower()}"
            ),
            "instance": instance,
            "list_url": list_url,
            "item_name": label.lower(),
        },
    )


@administrator_only
@require_http_methods(["GET", "POST"])
def program_edit(request, pk=None):

    return save_record(
        request,
        pk,
        AcademicProgram,
        ProgramForm,
        "Program",
        "accounts:programs",
    )


@administrator_only
@require_http_methods(["GET", "POST"])
def subject_edit(request, pk=None):

    return save_record(
        request,
        pk,
        Subject,
        SubjectForm,
        "Subject",
        "accounts:subjects",
    )


def protected_record_reason(record):

    if isinstance(record, AcademicProgram):

        if record.code == "BSIT":

            return (
                "The BSIT program is required by "
                "the current self-assessment configuration "
                "and cannot be deleted."
            )

    if isinstance(record, Subject):

        if (
            record.program.code == "BSIT"
            and record.code == "DB-FND"
        ):

            return (
                "This subject is required by the current "
                "self-assessment configuration "
                "and cannot be deleted."
            )

    return None


def delete_record(
    request,
    pk,
    model,
    label,
    list_url,
):

    if request.method == "POST":

        try:

            with transaction.atomic():

                lock_academic_catalog()

                record = get_object_or_404(
                    model.objects.select_for_update(),
                    pk=pk,
                )

                reason = protected_record_reason(record)

                if reason:

                    messages.error(
                        request,
                        reason,
                    )

                    return redirect(list_url)

                record.delete()

        except ProtectedError:

            messages.error(
                request,
                f"This {label.lower()} cannot be deleted "
                "because other academic records depend on it.",
            )

        except IntegrityError:

            messages.error(
                request,
                "The record could not be deleted safely.",
            )

        else:

            messages.success(
                request,
                f"{label} deleted successfully.",
            )

        return redirect(list_url)

    record = get_object_or_404(
        model,
        pk=pk,
    )

    return render(
        request,
        "accounts/academic_delete.html",
        {
            "record": record,
            "heading": f"Delete {label.lower()}",
            "item_name": label.lower(),
            "list_url": list_url,
        },
    )


@administrator_only
@require_http_methods(["GET", "POST"])
def program_delete(request, pk):

    return delete_record(
        request,
        pk,
        AcademicProgram,
        "Program",
        "accounts:programs",
    )


@administrator_only
@require_http_methods(["GET", "POST"])
def subject_delete(request, pk):

    return delete_record(
        request,
        pk,
        Subject,
        "Subject",
        "accounts:subjects",
    )
