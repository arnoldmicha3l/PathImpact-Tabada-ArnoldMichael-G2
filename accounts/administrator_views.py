
from datetime import timedelta
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_safe

from assessments.models import (
    AcademicProgram,
    Subject,
    Competency,
    SubjectCompetency,
    AssessmentSession,
)

from .models import CustomUser


def administrator_only(view):

    @login_required(login_url="accounts:login")
    @wraps(view)
    def wrapped(request, *args, **kwargs):

        if (
            not request.user.is_active
            or request.user.role
            != CustomUser.Role.ADMINISTRATOR
        ):
            raise PermissionDenied

        return view(request, *args, **kwargs)

    return wrapped


@administrator_only
@require_safe
def dashboard(request):

    students = CustomUser.objects.filter(
        role=CustomUser.Role.STUDENT
    )

    completed = AssessmentSession.objects.filter(
        completed_at__isnull=False,
        user__role=CustomUser.Role.STUDENT,
    )

    subject_count = Subject.objects.count()

    mapped_subject_count = (
        SubjectCompetency.objects
        .values("subject_id")
        .distinct()
        .count()
    )

    coverage = (
        round(mapped_subject_count / subject_count * 100)
        if subject_count
        else 0
    )

    today = timezone.localdate()
    first_day = today - timedelta(days=6)

    daily_records = (
        completed.filter(
            completed_at__date__gte=first_day,
            completed_at__date__lte=today,
        )
        .annotate(day=TruncDate("completed_at"))
        .values("day")
        .annotate(total=Count("pk"))
        .order_by("day")
    )

    daily_counts = {
        item["day"]: item["total"]
        for item in daily_records
    }

    days = [
        first_day + timedelta(days=offset)
        for offset in range(7)
    ]

    maximum = max(
        [daily_counts.get(day, 0) for day in days] + [1]
    )

    activity = [
        {
            "label": day.strftime("%a"),
            "date": day,
            "count": daily_counts.get(day, 0),
            "height": round(
                daily_counts.get(day, 0) / maximum * 100
            ),
        }
        for day in days
    ]

    recent_activity = []

    for student in students.order_by(
        "-date_joined", "-pk"
    )[:5]:

        recent_activity.append({
            "title": "New student registered",
            "category": "Account",
            "timestamp": student.date_joined,
        })

    for assessment in completed.order_by(
        "-completed_at", "-pk"
    )[:5]:

        recent_activity.append({
            "title": "Self-assessment completed",
            "category": "Assessment",
            "timestamp": assessment.completed_at,
        })

    recent_activity.sort(
        key=lambda item: item["timestamp"],
        reverse=True,
    )

    context = {
        "role_view": "administrator",
        "page_title": "Administrator dashboard",

        "student_count": students.count(),
        "subject_count": subject_count,
        "competency_count": Competency.objects.count(),
        "completed_count": completed.count(),

        "program_count": AcademicProgram.objects.count(),
        "mapping_count": SubjectCompetency.objects.count(),
        "mapped_subject_count": mapped_subject_count,
        "unmapped_subject_count": (
            subject_count - mapped_subject_count
        ),
        "coverage": coverage,

        "activity": activity,
        "weekly_total": sum(daily_counts.values()),
        "recent_activity": recent_activity[:6],
    }

    return render(
        request,
        "accounts/administrator_dashboard.html",
        context,
    )
