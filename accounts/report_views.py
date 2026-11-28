
import csv

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from assessments.models import AcademicProgram, Subject

from .administrator_views import administrator_only
from .report_services import (
    PERIOD_CHOICES,
    build_report,
)


def csv_safe(value):

    if value is None:
        return ""

    if isinstance(value, str):

        if value.lstrip().startswith(
            ("=", "+", "-", "@")
        ) or value.startswith(
            ("\t", "\r", "\n")
        ):

            return "'" + value

    return value


@administrator_only
@require_safe
@never_cache
def assessment_reports(request):

    report = build_report(request.GET)

    context = {
        **report,

        "period_choices": PERIOD_CHOICES,

        "programs": AcademicProgram.objects.order_by(
            "code"
        ),

        "available_subjects": (
            Subject.objects.select_related("program")
            .order_by("program__code", "code")
        ),

        "export_query": request.GET.urlencode(),

        "generated_at": timezone.now(),
    }

    return render(
        request,
        "accounts/assessment_reports.html",
        context,
        status=400 if report["filters"]["errors"] else 200,
    )


@administrator_only
@require_safe
@never_cache
def assessment_reports_export(request):

    report = build_report(request.GET)

    if report["filters"]["errors"]:

        return HttpResponse(
            "Invalid report filters.",
            status=400,
            content_type="text/plain",
        )

    filename = (
        "PathImpact_Assessment_Report_"
        f"{timezone.localdate():%Y-%m-%d}.csv"
    )

    response = HttpResponse(
        content_type="text/csv; charset=utf-8"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )

    # UTF-8 BOM for spreadsheet compatibility.
    response.write("\ufeff")

    writer = csv.writer(response)

    def write(*values):

        writer.writerow([
            csv_safe(value)
            for value in values
        ])

    filters = report["filters"]

    write("PATHIMPACT ASSESSMENT REPORT")
    write("Generated", timezone.localtime().isoformat())
    write("Period", filters["period"])
    write("Start date", filters["start"] or "All time")
    write("End date", filters["end"] or "All time")

    program = AcademicProgram.objects.filter(
        pk=filters["program_id"]
    ).first()

    subject = Subject.objects.filter(
        pk=filters["subject_id"]
    ).first()

    write(
        "Program",
        program.code if program else "All programs",
    )

    write(
        "Subject",
        subject.code if subject else "All subjects",
    )

    write()

    write("SUMMARY")
    write("Metric", "Value")

    write(
        "Total assessments",
        report["total_count"],
    )

    write(
        "Completed assessments",
        report["completed_count"],
    )

    write(
        "Participating students",
        report["student_count"],
    )

    write(
        "Completion rate (%)",
        report["completion_rate"],
    )

    write(
        "Average self-rating",
        report["average_rating"]
        if report["ratings_visible"]
        else "Suppressed",
    )

    write(
        "Rating responses",
        report["response_count"]
        if report["ratings_visible"]
        else "Suppressed",
    )

    write()

    write("ASSESSMENT ACTIVITY")
    write("Completion date", "Completed assessments")

    for row in report["activity"]:

        write(
            row["date"],
            row["total"],
        )

    write()

    write("RATING DISTRIBUTION")
    write("Rating", "Level", "Responses", "Percentage")

    for row in report["distribution"]:

        write(
            row["rating"],
            row["label"],
            row["count"],
            row["percentage"],
        )

    write()

    write("COMPETENCY GAP REPORT")

    write(
        "Code",
        "Competency",
        "Average rating",
        "Responses",
        "Distinct students",
    )

    for row in report["competencies"]:

        write(
            row["code"],
            row["name"],
            row["average"],
            row["responses"],
            row["students"],
        )

    write()

    write("SUBJECT ANALYSIS")

    write(
        "Program",
        "Subject code",
        "Subject",
        "Average rating",
        "Responses",
        "Distinct students",
    )

    for row in report["subjects"]:

        write(
            row["program"],
            row["code"],
            row["name"],
            row["average"],
            row["responses"],
            row["students"],
        )

    write()

    write("REPORT NOTES")

    write(
        "Rating statistics require at least "
        f"{report['privacy_threshold']} distinct students."
    )

    write(
        "Date filters apply to assessment start dates. "
        "Activity is grouped by completion date."
    )

    write(
        "Repeated assessments are included."
    )

    write(
        "Ratings are self-reported and do not "
        "represent official academic grades."
    )

    return response
