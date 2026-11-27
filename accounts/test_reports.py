
import csv
import io

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assessments.models import (
    AcademicProgram,
    Subject,
    Competency,
    SubjectCompetency,
    AssessmentSession,
    AssessmentResponse,
)

from .models import CustomUser
from .report_services import build_report
from .report_views import csv_safe


class AssessmentReportTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.admin = CustomUser.objects.create_user(
            username="report_admin",
            role=CustomUser.Role.ADMINISTRATOR,
        )

        cls.program = AcademicProgram.objects.create(
            code="AR-TEST",
            name="Assessment Report Test Program",
        )

        cls.subject = Subject.objects.create(
            program=cls.program,
            code="AR-SUB",
            name="Report Test Subject",
        )

        cls.competency = Competency.objects.create(
            code="AR-COMP",
            name="Report Test Competency",
            description="Test competency.",
        )

        cls.mapping = SubjectCompetency.objects.create(
            subject=cls.subject,
            competency=cls.competency,
        )

        cls.other_program = AcademicProgram.objects.create(
            code="AR-OTHER",
            name="Other Report Program",
        )

        cls.other_subject = Subject.objects.create(
            program=cls.other_program,
            code="AR-OTHER-SUB",
            name="Other Report Subject",
        )

        cls.other_mapping = SubjectCompetency.objects.create(
            subject=cls.other_subject,
            competency=cls.competency,
        )

        cls.students = []

        now = timezone.now()

        for rating in range(1, 6):

            student = CustomUser.objects.create_user(
                username=f"report_student_{rating}",
                role=CustomUser.Role.STUDENT,
            )

            cls.students.append(student)

            session = AssessmentSession.objects.create(
                user=student,
                started_at=now,
                completed_at=now,
            )

            AssessmentResponse.objects.create(
                assessment=session,
                subject_competency=cls.mapping,
                self_rating=rating,
            )

        cls.incomplete = AssessmentSession.objects.create(
            user=cls.students[0],
            started_at=now,
        )

        AssessmentResponse.objects.create(
            assessment=cls.incomplete,
            subject_competency=cls.mapping,
            self_rating=5,
        )

        cls.old_session = AssessmentSession.objects.create(
            user=cls.students[0],
            started_at=now - timedelta(days=60),
            completed_at=now - timedelta(days=60),
        )

        AssessmentResponse.objects.create(
            assessment=cls.old_session,
            subject_competency=cls.mapping,
            self_rating=5,
        )

        cls.other_session = AssessmentSession.objects.create(
            user=cls.students[0],
            started_at=now,
            completed_at=now,
        )

        AssessmentResponse.objects.create(
            assessment=cls.other_session,
            subject_competency=cls.other_mapping,
            self_rating=2,
        )

    def report_url(self):

        return reverse("accounts:assessment_reports")

    def export_url(self):

        return reverse("accounts:assessment_reports_export")

    def login_admin(self):

        self.client.force_login(self.admin)

    def filters(self, **extra):

        return {
            "period": "30days",
            "subject": str(self.subject.pk),
            **extra,
        }

    # ACCESS CONTROL

    def test_guest_report_redirect(self):

        response = self.client.get(self.report_url())

        self.assertEqual(response.status_code, 302)

    def test_student_report_forbidden(self):

        self.client.force_login(self.students[0])

        response = self.client.get(self.report_url())

        self.assertEqual(response.status_code, 403)

    def test_guest_export_redirect(self):

        response = self.client.get(self.export_url())

        self.assertEqual(response.status_code, 302)

    def test_student_export_forbidden(self):

        self.client.force_login(self.students[0])

        response = self.client.get(self.export_url())

        self.assertEqual(response.status_code, 403)

    def test_admin_report_access(self):

        self.login_admin()

        response = self.client.get(
            self.report_url(),
            self.filters(),
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Assessment Reports",
        )

    def test_report_rejects_post(self):

        self.login_admin()

        response = self.client.post(self.report_url())

        self.assertEqual(response.status_code, 405)

    # REPORT ACCURACY

    def test_total_assessments(self):

        report = build_report(self.filters())

        self.assertEqual(report["total_count"], 6)

    def test_completed_assessments(self):

        report = build_report(self.filters())

        self.assertEqual(report["completed_count"], 5)

    def test_distinct_participating_students(self):

        report = build_report(self.filters())

        self.assertEqual(report["student_count"], 5)

    def test_average_rating(self):

        report = build_report(self.filters())

        self.assertEqual(report["average_rating"], 3.0)

    def test_incomplete_responses_excluded(self):

        report = build_report(self.filters())

        self.assertEqual(report["response_count"], 5)

    def test_rating_distribution(self):

        report = build_report(self.filters())

        self.assertEqual(
            [row["count"] for row in report["distribution"]],
            [1, 1, 1, 1, 1],
        )

        self.assertEqual(
            [row["percentage"] for row in report["distribution"]],
            [20.0] * 5,
        )

    def test_competency_aggregation(self):

        report = build_report(self.filters())

        self.assertEqual(len(report["competencies"]), 1)

        row = report["competencies"][0]

        self.assertEqual(row["average"], 3.0)
        self.assertEqual(row["students"], 5)
        self.assertEqual(row["responses"], 5)

    def test_subject_aggregation(self):

        report = build_report(self.filters())

        self.assertEqual(len(report["subjects"]), 1)

        self.assertEqual(
            report["subjects"][0]["code"],
            self.subject.code,
        )

    def test_completion_activity(self):

        report = build_report(self.filters())

        self.assertEqual(
            sum(row["total"] for row in report["activity"]),
            5,
        )

    # FILTERING

    def test_all_time_includes_old_assessment(self):

        report = build_report(
            self.filters(period="all")
        )

        self.assertEqual(report["total_count"], 7)
        self.assertEqual(report["completed_count"], 6)

    def test_program_filter(self):

        report = build_report({
            "period": "30days",
            "program": str(self.program.pk),
        })

        self.assertEqual(report["total_count"], 6)

    def test_custom_date_range(self):

        today = timezone.localdate().isoformat()

        report = build_report(
            self.filters(
                period="custom",
                start=today,
                end=today,
            )
        )

        self.assertEqual(report["filters"]["errors"], [])
        self.assertEqual(report["completed_count"], 5)

    def test_invalid_date_range(self):

        self.login_admin()

        response = self.client.get(
            self.report_url(),
            self.filters(
                period="custom",
                start="2026-11-20",
                end="2026-11-01",
            ),
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_program_subject_combination(self):

        self.login_admin()

        response = self.client.get(
            self.report_url(),
            self.filters(
                program=str(self.other_program.pk)
            ),
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_subject_identifier(self):

        self.login_admin()

        response = self.client.get(
            self.report_url(),
            {"subject": "invalid"},
        )

        self.assertEqual(response.status_code, 400)

    # PRIVACY

    def test_small_group_rating_suppression(self):

        report = build_report(
            self.filters(
                subject=str(self.other_subject.pk)
            )
        )

        self.assertFalse(report["ratings_visible"])
        self.assertIsNone(report["average_rating"])
        self.assertIsNone(report["response_count"])
        self.assertEqual(report["distribution"], [])
        self.assertEqual(report["competencies"], [])
        self.assertEqual(report["subjects"], [])

    def test_small_subject_group_excluded(self):

        report = build_report({
            "period": "30days",
        })

        subject_codes = [
            row["code"]
            for row in report["subjects"]
        ]

        self.assertIn(
            self.subject.code,
            subject_codes,
        )

        self.assertNotIn(
            self.other_subject.code,
            subject_codes,
        )

    def test_report_does_not_display_student_username(self):

        self.login_admin()

        response = self.client.get(
            self.report_url(),
            self.filters(),
        )

        for student in self.students:

            self.assertNotContains(
                response,
                student.username,
            )

    # CSV EXPORT

    def test_csv_export(self):

        self.login_admin()

        response = self.client.get(
            self.export_url(),
            self.filters(),
        )

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "text/csv",
            response["Content-Type"],
        )

        self.assertIn(
            "attachment;",
            response["Content-Disposition"],
        )

        rows = list(
            csv.reader(
                io.StringIO(
                    response.content.decode("utf-8-sig")
                )
            )
        )

        self.assertIn(
            ["Total assessments", "6"],
            rows,
        )

        self.assertIn(
            ["Completed assessments", "5"],
            rows,
        )

        self.assertIn(
            ["Average self-rating", "3.0"],
            rows,
        )

    def test_csv_privacy_suppression(self):

        self.login_admin()

        response = self.client.get(
            self.export_url(),
            self.filters(
                subject=str(self.other_subject.pk)
            ),
        )

        rows = list(
            csv.reader(
                io.StringIO(
                    response.content.decode("utf-8-sig")
                )
            )
        )

        self.assertIn(
            ["Average self-rating", "Suppressed"],
            rows,
        )

        self.assertNotContains(
            response,
            self.students[0].username,
        )

    def test_csv_formula_protection(self):

        self.assertEqual(
            csv_safe("=1+1"),
            "'=1+1",
        )

        self.assertEqual(
            csv_safe("@SUM(A1:A2)"),
            "'@SUM(A1:A2)",
        )

        self.assertEqual(
            csv_safe("Normal subject"),
            "Normal subject",
        )

        self.assertEqual(csv_safe(5), 5)

    def test_invalid_export_filters(self):

        self.login_admin()

        response = self.client.get(
            self.export_url(),
            {"subject": "invalid"},
        )

        self.assertEqual(response.status_code, 400)

    # DATA INTEGRITY

    def test_reports_do_not_modify_records(self):

        self.login_admin()

        sessions_before = list(
            AssessmentSession.objects.order_by("pk")
            .values_list("pk", "completed_at")
        )

        responses_before = list(
            AssessmentResponse.objects.order_by("pk")
            .values_list("pk", "self_rating")
        )

        self.client.get(
            self.report_url(),
            self.filters(),
        )

        self.client.get(
            self.export_url(),
            self.filters(),
        )

        self.assertEqual(
            sessions_before,
            list(
                AssessmentSession.objects.order_by("pk")
                .values_list("pk", "completed_at")
            ),
        )

        self.assertEqual(
            responses_before,
            list(
                AssessmentResponse.objects.order_by("pk")
                .values_list("pk", "self_rating")
            ),
        )
