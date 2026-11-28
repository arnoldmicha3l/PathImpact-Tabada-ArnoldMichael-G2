
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date

from assessments.models import (
    AcademicProgram,
    Subject,
    AssessmentSession,
    AssessmentResponse,
)


MIN_REPORT_STUDENTS = 5

PERIOD_CHOICES = (
    ("today", "Today"),
    ("7days", "Last 7 days"),
    ("30days", "Last 30 days"),
    ("all", "All time"),
    ("custom", "Custom range"),
)

RATING_LABELS = {
    1: "Beginning",
    2: "Developing",
    3: "Practicing",
    4: "Confident",
    5: "Explaining",
}


def valid_id(value):

    value = str(value or "")

    if (
        value.isascii()
        and value.isdecimal()
        and len(value) <= 9
        and int(value) > 0
    ):
        return int(value)

    return None


def safe_date(value):

    try:
        return parse_date(value or "")
    except (ValueError, TypeError):
        return None


def rounded(value):

    if value is None:
        return None

    return round(float(value), 2)


def report_filters(params):

    today = timezone.localdate()

    period = params.get("period", "30days")

    if period not in dict(PERIOD_CHOICES):
        period = "30days"

    start = None
    end = None
    errors = []

    if period == "today":

        start = today
        end = today

    elif period == "7days":

        start = today - timedelta(days=6)
        end = today

    elif period == "30days":

        start = today - timedelta(days=29)
        end = today

    elif period == "custom":

        start = safe_date(params.get("start"))
        end = safe_date(params.get("end"))

        if start is None or end is None:

            errors.append(
                "Provide a valid start and end date."
            )

        elif start > end:

            errors.append(
                "The start date cannot be after the end date."
            )

        elif end > today:

            errors.append(
                "The end date cannot be in the future."
            )

    program_id = valid_id(params.get("program"))
    subject_id = valid_id(params.get("subject"))

    if params.get("program") and program_id is None:

        errors.append("Invalid academic program.")

    if params.get("subject") and subject_id is None:

        errors.append("Invalid academic subject.")

    if program_id and not AcademicProgram.objects.filter(
        pk=program_id
    ).exists():

        errors.append("Academic program was not found.")

    if subject_id:

        subject = Subject.objects.filter(
            pk=subject_id
        ).first()

        if subject is None:

            errors.append("Academic subject was not found.")

        elif program_id and subject.program_id != program_id:

            errors.append(
                "The selected subject does not belong "
                "to the selected program."
            )

    return {
        "period": period,
        "start": start,
        "end": end,
        "program_id": program_id,
        "subject_id": subject_id,
        "errors": errors,
    }


def build_report(params):

    filters = report_filters(params)

    sessions = AssessmentSession.objects.filter(
        user__role="student"
    )

    responses = AssessmentResponse.objects.filter(
        assessment__user__role="student",
        assessment__completed_at__isnull=False,
    )

    academic_filter = Q()

    if filters["program_id"]:

        academic_filter &= Q(
            subject_competency__subject__program_id=(
                filters["program_id"]
            )
        )

    if filters["subject_id"]:

        academic_filter &= Q(
            subject_competency__subject_id=(
                filters["subject_id"]
            )
        )

    if filters["start"]:

        sessions = sessions.filter(
            started_at__date__gte=filters["start"]
        )

    if filters["end"]:

        sessions = sessions.filter(
            started_at__date__lte=filters["end"]
        )

    if filters["program_id"] or filters["subject_id"]:

        matching_sessions = (
            AssessmentResponse.objects
            .filter(academic_filter)
            .values("assessment_id")
        )

        sessions = sessions.filter(
            pk__in=matching_sessions
        )

    if filters["errors"]:

        sessions = sessions.none()

    completed = sessions.filter(
        completed_at__isnull=False
    )

    responses = responses.filter(
        assessment_id__in=completed.values("pk")
    ).filter(academic_filter)

    total_count = sessions.count()
    completed_count = completed.count()

    student_count = sessions.values(
        "user_id"
    ).distinct().count()

    rating_students = responses.values(
        "assessment__user_id"
    ).distinct().count()

    ratings_visible = (
        rating_students >= MIN_REPORT_STUDENTS
    )

    average_rating = None
    response_count = None
    distribution = []
    competencies = []
    subjects = []

    if ratings_visible:

        statistics = responses.aggregate(
            average=Avg("self_rating"),
            total=Count("pk"),
        )

        average_rating = rounded(
            statistics["average"]
        )

        response_count = statistics["total"]

        counts = dict(
            responses.values("self_rating")
            .annotate(total=Count("pk"))
            .values_list("self_rating", "total")
        )

        for rating in range(1, 6):

            count = counts.get(rating, 0)

            distribution.append({
                "rating": rating,
                "label": RATING_LABELS[rating],
                "count": count,
                "percentage": (
                    round(count / response_count * 100, 1)
                    if response_count else 0
                ),
            })

        competency_rows = (
            responses.values(
                "subject_competency__competency_id",
                "subject_competency__competency__code",
                "subject_competency__competency__name",
            )
            .annotate(
                average=Avg("self_rating"),
                response_count=Count("pk"),
                students=Count(
                    "assessment__user_id",
                    distinct=True,
                ),
            )
            .filter(students__gte=MIN_REPORT_STUDENTS)
            .order_by(
                "average",
                "subject_competency__competency__code",
            )
        )

        for row in competency_rows:

            competencies.append({
                "code": row[
                    "subject_competency__competency__code"
                ],
                "name": row[
                    "subject_competency__competency__name"
                ],
                "average": rounded(row["average"]),
                "responses": row["response_count"],
                "students": row["students"],
            })

        subject_rows = (
            responses.values(
                "subject_competency__subject_id",
                "subject_competency__subject__code",
                "subject_competency__subject__name",
                "subject_competency__subject__program__code",
            )
            .annotate(
                average=Avg("self_rating"),
                response_count=Count("pk"),
                students=Count(
                    "assessment__user_id",
                    distinct=True,
                ),
            )
            .filter(students__gte=MIN_REPORT_STUDENTS)
            .order_by(
                "subject_competency__subject__program__code",
                "subject_competency__subject__code",
            )
        )

        for row in subject_rows:

            subjects.append({
                "program": row[
                    "subject_competency__subject__program__code"
                ],
                "code": row[
                    "subject_competency__subject__code"
                ],
                "name": row[
                    "subject_competency__subject__name"
                ],
                "average": rounded(row["average"]),
                "responses": row["response_count"],
                "students": row["students"],
            })

    activity = list(
        completed.annotate(
            date=TruncDate("completed_at")
        )
        .values("date")
        .annotate(total=Count("pk"))
        .order_by("date")
    )

    # Keep the dashboard compact while retaining
    # the complete activity data for CSV exports.

    activity_preview = activity[-30:]

    peak = max(
        (row["total"] for row in activity_preview),
        default=1,
    )

    for row in activity_preview:

        row["height"] = round(
            row["total"] / peak * 100
        )

    return {
        "filters": filters,
        "total_count": total_count,
        "completed_count": completed_count,
        "student_count": student_count,
        "completion_rate": (
            round(completed_count / total_count * 100, 1)
            if total_count else 0
        ),
        "average_rating": average_rating,
        "response_count": response_count,
        "ratings_visible": ratings_visible,
        "privacy_threshold": MIN_REPORT_STUDENTS,
        "distribution": distribution,
        "competencies": competencies,
        "subjects": subjects,
        "activity": activity,
        "activity_preview": activity_preview,
        "activity_truncated": len(activity) > 30,
    }
