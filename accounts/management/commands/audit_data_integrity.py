
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, F, Q
from django.db.models.functions import Lower, Trim

from assessments.models import (
    AcademicProgram,
    Subject,
    SubjectPrerequisite,
    SubjectCompetency,
    CompetencyImpact,
    AssessmentSession,
    AssessmentResponse,
    ReadinessResult,
    ReviewRecommendation,
)


User = get_user_model()


class Command(BaseCommand):

    help = "Perform a read-only PathImpact database integrity audit."

    def handle(self, *args, **options):

        issues = []

        def check(label, count):

            if count:
                issues.append((label, count))

                self.stdout.write(
                    self.style.ERROR(
                        f"[FAIL] {label}: {count}"
                    )
                )

            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[PASS] {label}: 0 issues"
                    )
                )

        def heading(label):

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"\n{label}"
                )
            )

        heading("PATHIMPACT DATABASE INTEGRITY AUDIT")

        heading("01 | ACCOUNT INTEGRITY")

        check(
            "Case-insensitive duplicate usernames",
            User.objects.annotate(
                normalized=Lower("username")
            )
            .values("normalized")
            .annotate(total=Count("pk"))
            .filter(total__gt=1)
            .count(),
        )

        check(
            "Case-insensitive duplicate nonblank emails",
            User.objects.annotate(
                normalized=Lower(Trim("email"))
            )
            .exclude(email__regex=r"^\s*$")
            .values("normalized")
            .annotate(total=Count("pk"))
            .filter(total__gt=1)
            .count(),
        )

        check(
            "Invalid account roles",
            User.objects.exclude(
                role__in=["student", "administrator"]
            ).count(),
        )

        check(
            "Student accounts with privileged flags",
            User.objects.filter(
                role="student"
            ).filter(
                Q(is_staff=True) | Q(is_superuser=True)
            ).count(),
        )

        heading("02 | ACADEMIC INTEGRITY")

        check(
            "Duplicate normalized program codes",
            AcademicProgram.objects.annotate(
                normalized=Lower("code")
            )
            .values("normalized")
            .annotate(total=Count("pk"))
            .filter(total__gt=1)
            .count(),
        )

        check(
            "Duplicate normalized program names",
            AcademicProgram.objects.annotate(
                normalized=Lower("name")
            )
            .values("normalized")
            .annotate(total=Count("pk"))
            .filter(total__gt=1)
            .count(),
        )

        check(
            "Duplicate subject codes within programs",
            Subject.objects.annotate(
                normalized=Lower("code")
            )
            .values("program_id", "normalized")
            .annotate(total=Count("pk"))
            .filter(total__gt=1)
            .count(),
        )

        check(
            "Invalid subject year levels",
            Subject.objects.exclude(
                Q(year_level__isnull=True)
                | Q(year_level__in=[1, 2, 3, 4])
            ).count(),
        )

        check(
            "Invalid subject semesters",
            Subject.objects.exclude(
                Q(semester__isnull=True)
                | Q(semester__in=[1, 2, 3])
            ).count(),
        )

        check(
            "Negative academic units",
            Subject.objects.filter(
                units__lt=0
            ).count(),
        )

        prototype = Subject.objects.filter(
            program__code="BSIT",
            code="DB-FND",
        ).first()

        check(
            "Missing configured assessment subject",
            int(prototype is None),
        )

        if prototype is not None:

            check(
                "Configured assessment subject has no competencies",
                int(
                    not SubjectCompetency.objects.filter(
                        subject=prototype
                    ).exists()
                ),
            )

        heading("03 | RELATIONSHIP INTEGRITY")

        check(
            "Self-referencing prerequisites",
            SubjectPrerequisite.objects.filter(
                prerequisite_id=F("successor_id")
            ).count(),
        )

        check(
            "Cross-program prerequisites",
            SubjectPrerequisite.objects.exclude(
                prerequisite__program_id=F(
                    "successor__program_id"
                )
            ).count(),
        )

        check(
            "Duplicate prerequisite relationships",
            SubjectPrerequisite.objects.values(
                "prerequisite_id",
                "successor_id",
            )
            .annotate(total=Count("pk"))
            .filter(total__gt=1)
            .count(),
        )

        check(
            "Duplicate competency mappings",
            SubjectCompetency.objects.values(
                "subject_id",
                "competency_id",
            )
            .annotate(total=Count("pk"))
            .filter(total__gt=1)
            .count(),
        )

        check(
            "Incompatible competency impacts",
            CompetencyImpact.objects.exclude(
                subject_competency__subject_id=F(
                    "prerequisite__prerequisite_id"
                )
            ).count(),
        )

        check(
            "Invalid competency impact relevance",
            CompetencyImpact.objects.exclude(
                relevance__in=[1, 2, 3]
            ).count(),
        )

        heading("04 | ASSESSMENT INTEGRITY")

        check(
            "Invalid assessment ratings",
            AssessmentResponse.objects.exclude(
                self_rating__in=[1, 2, 3, 4, 5]
            ).count(),
        )

        check(
            "Assessments completed before their start time",
            AssessmentSession.objects.filter(
                completed_at__lt=F("started_at")
            ).count(),
        )

        heading("05 | RESULT INTEGRITY")

        check(
            "Invalid readiness scores",
            ReadinessResult.objects.filter(
                Q(readiness_score__lt=1)
                | Q(readiness_score__gt=5)
            ).count(),
        )

        check(
            "Invalid recommendation ranks",
            ReviewRecommendation.objects.filter(
                priority_rank__lt=1
            ).count(),
        )

        heading("06 | AUDIT SUMMARY")

        totals = [
            ("Accounts", User.objects.count()),
            ("Academic programs", AcademicProgram.objects.count()),
            ("Subjects", Subject.objects.count()),
            ("Assessments", AssessmentSession.objects.count()),
            ("Assessment responses", AssessmentResponse.objects.count()),
            ("Readiness results", ReadinessResult.objects.count()),
            ("Review recommendations", ReviewRecommendation.objects.count()),
        ]

        for label, total in totals:

            self.stdout.write(
                f"{label}: {total}"
            )

        if issues:

            raise CommandError(
                f"Audit detected {len(issues)} categories "
                "requiring review. "
                "No database records were modified."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nAUDIT PASSED: "
                "No integrity issues detected "
                "by the implemented checks."
            )
        )

        self.stdout.write(
            "No database records were modified."
        )
