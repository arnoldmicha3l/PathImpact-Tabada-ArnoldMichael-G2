
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from assessments.models import (
    AcademicProgram,
    Subject,
    SubjectPrerequisite,
    Competency,
    SubjectCompetency,
    CompetencyImpact,
    AssessmentSession,
    AssessmentResponse,
    ReadinessResult,
    ReviewRecommendation,
)


User = get_user_model()


class AdministratorHTTPSecurityTests(TestCase):
    """
    Verify HTTP method restrictions, CSRF protection,
    administrator authorization, safe GET requests,
    missing-record handling, and sensitive-page caching.

    Security checks also compare database records before
    and after unauthorized requests.
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="http_security_admin",
            email="http-admin@example.test",
            password="HTTP-Security!9274",
            role="administrator",
        )

        cls.student = User.objects.create_user(
            username="http_security_student",
            email="http-student@example.test",
            password="HTTP-Security!9274",
            role="student",
        )

        cls.program = AcademicProgram.objects.create(
            code="HTTP-PROG",
            name="HTTP Security Program",
        )

        cls.subject = Subject.objects.create(
            program=cls.program,
            code="HTTP-SUB",
            name="HTTP Security Subject",
        )

        cls.successor = Subject.objects.create(
            program=cls.program,
            code="HTTP-NEXT",
            name="HTTP Security Successor",
        )

        cls.prerequisite = SubjectPrerequisite.objects.create(
            prerequisite=cls.subject,
            successor=cls.successor,
        )

        cls.competency = Competency.objects.create(
            code="HTTP-COMP",
            name="HTTP Security Competency",
            description="Demonstrate secure system behavior.",
        )

        cls.mapping = SubjectCompetency.objects.create(
            subject=cls.subject,
            competency=cls.competency,
        )

        cls.impact = CompetencyImpact.objects.create(
            prerequisite=cls.prerequisite,
            subject_competency=cls.mapping,
            relevance=2,
        )

    def setUp(self):
        self.secure_client = Client(
            enforce_csrf_checks=True
        )

        self.secure_client.force_login(self.admin)

    # ==================================================
    # DATABASE SNAPSHOT HELPERS
    # ==================================================

    def database_snapshot(self):
        models = [
            User,
            AcademicProgram,
            Subject,
            SubjectPrerequisite,
            Competency,
            SubjectCompetency,
            CompetencyImpact,
            AssessmentSession,
            AssessmentResponse,
            ReadinessResult,
            ReviewRecommendation,
        ]

        return {
            model._meta.label: list(
                model.objects.order_by("pk").values()
            )
            for model in models
        }

    def assert_database_unchanged(self, before):
        self.assertEqual(
            self.database_snapshot(),
            before,
            "An unauthorized or read-only request modified "
            "application database records.",
        )

    # ==================================================
    # ENDPOINT DEFINITIONS
    # ==================================================

    def create_endpoints(self):
        return [
            ("accounts:program_create", []),
            ("accounts:subject_create", []),
            ("accounts:prerequisite_create", []),
            ("accounts:competency_create", []),
            ("accounts:mapping_create", []),
            ("accounts:impact_create", []),
        ]

    def edit_endpoints(self):
        return [
            (
                "accounts:program_edit",
                [self.program.pk],
            ),
            (
                "accounts:subject_edit",
                [self.subject.pk],
            ),
            (
                "accounts:prerequisite_edit",
                [self.prerequisite.pk],
            ),
            (
                "accounts:competency_edit",
                [self.competency.pk],
            ),
            (
                "accounts:mapping_edit",
                [self.mapping.pk],
            ),
            (
                "accounts:impact_edit",
                [self.impact.pk],
            ),
        ]

    def delete_endpoints(self):
        return [
            (
                "accounts:program_delete",
                [self.program.pk],
            ),
            (
                "accounts:subject_delete",
                [self.subject.pk],
            ),
            (
                "accounts:prerequisite_delete",
                [self.prerequisite.pk],
            ),
            (
                "accounts:competency_delete",
                [self.competency.pk],
            ),
            (
                "accounts:mapping_delete",
                [self.mapping.pk],
            ),
            (
                "accounts:impact_delete",
                [self.impact.pk],
            ),
        ]

    def account_status_endpoints(self):
        return [
            (
                "accounts:user_status",
                [self.student.pk, "deactivate"],
            ),
            (
                "accounts:user_status",
                [self.student.pk, "activate"],
            ),
        ]

    def mutation_endpoints(self):
        return (
            self.create_endpoints()
            + self.edit_endpoints()
            + self.delete_endpoints()
            + self.account_status_endpoints()
        )

    def read_endpoints(self):
        return [
            ("accounts:administrator_dashboard", []),
            ("accounts:programs", []),
            ("accounts:subjects", []),
            ("accounts:prerequisites", []),
            ("accounts:competencies", []),
            ("accounts:mappings", []),
            ("accounts:impacts", []),
            ("accounts:users", []),
            (
                "accounts:user_detail",
                [self.student.pk],
            ),
            ("accounts:assessment_reports", []),
            ("accounts:assessment_reports_export", []),
        ]

    # ==================================================
    # SECURITY ASSERTION HELPERS
    # ==================================================

    def assert_csrf_rejected(self, name, args, data=None):
        before = self.database_snapshot()

        response = self.secure_client.post(
            reverse(name, args=args),
            data or {},
        )

        self.assertEqual(
            response.status_code,
            403,
            f"{name} accepted a POST request without "
            "a valid CSRF token.",
        )

        self.assert_database_unchanged(before)

    def assert_safe_get_requests(
        self,
        endpoints,
        allowed_statuses=(200,),
    ):
        self.client.force_login(self.admin)

        before = self.database_snapshot()

        for name, args in endpoints:
            with self.subTest(endpoint=name):
                response = self.client.get(
                    reverse(name, args=args)
                )

                self.assertIn(
                    response.status_code,
                    allowed_statuses,
                )

                self.assert_database_unchanged(before)

    # ==================================================
    # 01 | CSRF PROTECTION - CREATE OPERATIONS
    # ==================================================

    def test_program_creation_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:program_create",
            [],
            {
                "code": "CSRF-PROG",
                "name": "Unauthorized Program",
            },
        )

    def test_subject_creation_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:subject_create",
            [],
            {
                "program": self.program.pk,
                "code": "CSRF-SUB",
                "name": "Unauthorized Subject",
                "year_level": 1,
                "semester": 1,
                "units": 3,
            },
        )

    def test_prerequisite_creation_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:prerequisite_create",
            [],
            {
                "prerequisite": self.subject.pk,
                "successor": self.successor.pk,
            },
        )

    def test_competency_creation_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:competency_create",
            [],
            {
                "code": "CSRF-COMP",
                "name": "Unauthorized Competency",
                "description": "Unauthorized creation.",
            },
        )

    def test_mapping_creation_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:mapping_create",
            [],
            {
                "subject": self.successor.pk,
                "competency": self.competency.pk,
            },
        )

    def test_impact_creation_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:impact_create",
            [],
            {
                "prerequisite": self.prerequisite.pk,
                "subject_competency": self.mapping.pk,
                "relevance": 3,
            },
        )

    # ==================================================
    # 02 | CSRF PROTECTION - UPDATE OPERATIONS
    # ==================================================

    def test_program_update_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:program_edit",
            [self.program.pk],
            {
                "code": "CSRF-UPDATE",
                "name": "Unauthorized Update",
            },
        )

    def test_subject_update_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:subject_edit",
            [self.subject.pk],
            {
                "program": self.program.pk,
                "code": "CSRF-SUB",
                "name": "Unauthorized Update",
                "year_level": 1,
                "semester": 1,
                "units": 3,
            },
        )

    def test_prerequisite_update_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:prerequisite_edit",
            [self.prerequisite.pk],
            {
                "prerequisite": self.successor.pk,
                "successor": self.subject.pk,
            },
        )

    def test_competency_update_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:competency_edit",
            [self.competency.pk],
            {
                "code": "CSRF-COMP",
                "name": "Unauthorized Update",
                "description": "Unauthorized change.",
            },
        )

    def test_mapping_update_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:mapping_edit",
            [self.mapping.pk],
            {
                "subject": self.successor.pk,
                "competency": self.competency.pk,
            },
        )

    def test_impact_update_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:impact_edit",
            [self.impact.pk],
            {
                "prerequisite": self.prerequisite.pk,
                "subject_competency": self.mapping.pk,
                "relevance": 3,
            },
        )

    # ==================================================
    # 03 | CSRF PROTECTION - DELETE OPERATIONS
    # ==================================================

    def test_program_deletion_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:program_delete",
            [self.program.pk],
        )

    def test_subject_deletion_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:subject_delete",
            [self.subject.pk],
        )

    def test_prerequisite_deletion_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:prerequisite_delete",
            [self.prerequisite.pk],
        )

    def test_competency_deletion_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:competency_delete",
            [self.competency.pk],
        )

    def test_mapping_deletion_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:mapping_delete",
            [self.mapping.pk],
        )

    def test_impact_deletion_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:impact_delete",
            [self.impact.pk],
        )

    # ==================================================
    # 04 | CSRF PROTECTION - ACCOUNT MANAGEMENT
    # ==================================================

    def test_account_deactivation_requires_csrf(self):
        self.assert_csrf_rejected(
            "accounts:user_status",
            [self.student.pk, "deactivate"],
        )

    def test_account_activation_requires_csrf(self):
        User.objects.filter(
            pk=self.student.pk
        ).update(is_active=False)

        self.assert_csrf_rejected(
            "accounts:user_status",
            [self.student.pk, "activate"],
        )

    # ==================================================
    # 05 | CSRF TOKEN VALIDATION
    # ==================================================

    def test_invalid_csrf_token_is_rejected(self):
        url = reverse("accounts:program_create")

        response = self.secure_client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "csrftoken",
            self.secure_client.cookies,
        )

        before = self.database_snapshot()

        response = self.secure_client.post(
            url,
            {
                "code": "INVALID-CSRF",
                "name": "Invalid CSRF Program",
                "csrfmiddlewaretoken": "invalid-token",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.assert_database_unchanged(before)

    def test_valid_csrf_token_allows_creation(self):
        url = reverse("accounts:program_create")

        response = self.secure_client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "csrftoken",
            self.secure_client.cookies,
        )

        token = self.secure_client.cookies[
            "csrftoken"
        ].value

        response = self.secure_client.post(
            url,
            {
                "code": "VALID-CSRF",
                "name": "Valid CSRF Program",
                "csrfmiddlewaretoken": token,
            },
        )

        self.assertRedirects(
            response,
            reverse("accounts:programs"),
        )

        self.assertTrue(
            AcademicProgram.objects.filter(
                code="VALID-CSRF",
                name="Valid CSRF Program",
            ).exists()
        )

    # ==================================================
    # 06 | HTTP METHOD RESTRICTIONS
    # ==================================================

    def test_read_endpoints_reject_post(self):
        self.client.force_login(self.admin)

        before = self.database_snapshot()

        for name, args in self.read_endpoints():
            with self.subTest(endpoint=name):
                response = self.client.post(
                    reverse(name, args=args),
                    {},
                )

                self.assertEqual(
                    response.status_code,
                    405,
                )

                self.assert_database_unchanged(before)

    def test_mutation_endpoints_reject_unsafe_methods(self):
        self.client.force_login(self.admin)

        before = self.database_snapshot()

        for name, args in self.mutation_endpoints():
            for method in ("PUT", "PATCH", "DELETE"):
                with self.subTest(
                    endpoint=name,
                    method=method,
                ):
                    response = self.client.generic(
                        method,
                        reverse(name, args=args),
                    )

                    self.assertEqual(
                        response.status_code,
                        405,
                    )

                    self.assert_database_unchanged(before)

    # ==================================================
    # 07 | SAFE GET REQUESTS
    # ==================================================

    def test_delete_confirmation_get_preserves_records(self):
        self.assert_safe_get_requests(
            self.delete_endpoints(),
            allowed_statuses=(200, 302),
        )

    def test_edit_get_preserves_records(self):
        self.assert_safe_get_requests(
            self.edit_endpoints(),
            allowed_statuses=(200, 302),
        )

    def test_create_get_preserves_records(self):
        self.assert_safe_get_requests(
            self.create_endpoints(),
        )

    def test_account_confirmation_get_preserves_status(self):
        self.assert_safe_get_requests(
            self.account_status_endpoints(),
            allowed_statuses=(200, 302),
        )

    def test_read_endpoints_do_not_modify_records(self):
        self.assert_safe_get_requests(
            self.read_endpoints(),
        )

    # ==================================================
    # 08 | ADMINISTRATOR AUTHORIZATION
    # ==================================================

    def test_student_cannot_submit_administrator_forms(self):
        self.client.force_login(self.student)

        before = self.database_snapshot()

        for name, args in self.mutation_endpoints():
            with self.subTest(endpoint=name):
                response = self.client.post(
                    reverse(name, args=args),
                    {},
                )

                self.assertEqual(
                    response.status_code,
                    403,
                )

                self.assert_database_unchanged(before)

    def test_guest_cannot_submit_administrator_forms(self):
        before = self.database_snapshot()

        for name, args in self.mutation_endpoints():
            with self.subTest(endpoint=name):
                response = self.client.post(
                    reverse(name, args=args),
                    {},
                )

                self.assertEqual(
                    response.status_code,
                    302,
                )

                self.assertIn(
                    reverse("accounts:login"),
                    response.url,
                )

                self.assert_database_unchanged(before)

    # ==================================================
    # 09 | MISSING RECORD HANDLING
    # ==================================================

    def test_missing_academic_records_return_404(self):
        self.client.force_login(self.admin)

        before = self.database_snapshot()

        missing_pk = 999999999

        endpoints = [
            "accounts:program_edit",
            "accounts:program_delete",
            "accounts:subject_edit",
            "accounts:subject_delete",
            "accounts:prerequisite_edit",
            "accounts:prerequisite_delete",
            "accounts:competency_edit",
            "accounts:competency_delete",
            "accounts:mapping_edit",
            "accounts:mapping_delete",
            "accounts:impact_edit",
            "accounts:impact_delete",
        ]

        for name in endpoints:
            with self.subTest(endpoint=name):
                response = self.client.get(
                    reverse(
                        name,
                        args=[missing_pk],
                    )
                )

                self.assertEqual(
                    response.status_code,
                    404,
                )

                self.assert_database_unchanged(before)

    # ==================================================
    # 10 | SENSITIVE PAGE CACHE PROTECTION
    # ==================================================

    def test_administrator_pages_are_not_cached(self):
        self.client.force_login(self.admin)

        for name, args in self.read_endpoints():
            with self.subTest(endpoint=name):
                response = self.client.get(
                    reverse(name, args=args)
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                cache_control = response.headers.get(
                    "Cache-Control",
                    "",
                )

                self.assertIn(
                    "no-store",
                    cache_control,
                    f"{name} is missing no-store.",
                )

                self.assertIn(
                    "private",
                    cache_control,
                    f"{name} is missing private.",
                )
