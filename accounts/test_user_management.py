
from django.test import Client, TestCase
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


class UserManagementTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.admin = CustomUser.objects.create_user(
            username="um_admin",
            email="um_admin@example.com",
            role=CustomUser.Role.ADMINISTRATOR,
        )

        cls.other_admin = CustomUser.objects.create_user(
            username="um_other_admin",
            email="um_other_admin@example.com",
            role=CustomUser.Role.ADMINISTRATOR,
        )

        cls.student = CustomUser.objects.create_user(
            username="um_student",
            email="um_student@example.com",
            first_name="Sample",
            last_name="Student",
            password="Testing-Only-482!",
            role=CustomUser.Role.STUDENT,
        )

        cls.inactive_student = CustomUser.objects.create_user(
            username="um_inactive",
            email="um_inactive@example.com",
            role=CustomUser.Role.STUDENT,
            is_active=False,
        )

        cls.staff_student = CustomUser.objects.create_user(
            username="um_staff",
            email="um_staff@example.com",
            role=CustomUser.Role.STUDENT,
            is_staff=True,
        )

        cls.superuser_student = CustomUser.objects.create_user(
            username="um_superuser",
            email="um_superuser@example.com",
            role=CustomUser.Role.STUDENT,
            is_superuser=True,
            is_staff=True,
        )

        cls.program = AcademicProgram.objects.create(
            code="UM-TEST",
            name="User Management Test Program",
        )

        cls.subject = Subject.objects.create(
            program=cls.program,
            code="UM-SUB",
            name="User Management Test Subject",
        )

        cls.competency = Competency.objects.create(
            code="UM-COMP",
            name="Test Competency",
            description="Test competency description.",
        )

        cls.mapping = SubjectCompetency.objects.create(
            subject=cls.subject,
            competency=cls.competency,
        )

        cls.assessment = AssessmentSession.objects.create(
            user=cls.student,
            completed_at=timezone.now(),
        )

        cls.assessment_response = AssessmentResponse.objects.create(
            assessment=cls.assessment,
            subject_competency=cls.mapping,
            self_rating=4,
        )

    def login_admin(self):

        self.client.force_login(self.admin)

    def directory_url(self):

        return reverse("accounts:users")

    def detail_url(self, account):

        return reverse(
            "accounts:user_detail",
            args=[account.pk],
        )

    def status_url(self, account, action):

        return reverse(
            "accounts:user_status",
            args=[account.pk, action],
        )

    # ACCESS CONTROL

    def test_guest_directory_redirect(self):

        response = self.client.get(
            self.directory_url()
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_student_directory_forbidden(self):

        self.client.force_login(self.student)

        response = self.client.get(
            self.directory_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_student_detail_forbidden(self):

        self.client.force_login(self.student)

        response = self.client.get(
            self.detail_url(self.other_admin)
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_student_status_change_forbidden(self):

        self.client.force_login(self.student)

        response = self.client.post(
            self.status_url(
                self.inactive_student,
                "activate",
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.inactive_student.refresh_from_db()

        self.assertFalse(
            self.inactive_student.is_active
        )

    def test_admin_directory_access(self):

        self.login_admin()

        response = self.client.get(
            self.directory_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "User Management",
        )

    def test_admin_detail_access(self):

        self.login_admin()

        response = self.client.get(
            self.detail_url(self.student)
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            self.student.username,
        )

        self.assertNotContains(
            response,
            self.student.password,
        )

    # DIRECTORY AND FILTERS

    def test_summary_statistics(self):

        self.login_admin()

        response = self.client.get(
            self.directory_url()
        )

        self.assertEqual(
            response.context["total_count"],
            CustomUser.objects.count(),
        )

        self.assertEqual(
            response.context["student_count"],
            CustomUser.objects.filter(
                role=CustomUser.Role.STUDENT
            ).count(),
        )

        self.assertEqual(
            response.context["active_count"],
            CustomUser.objects.filter(
                is_active=True
            ).count(),
        )

        self.assertEqual(
            response.context["inactive_count"],
            CustomUser.objects.filter(
                is_active=False
            ).count(),
        )

    def test_search_username(self):

        self.login_admin()

        response = self.client.get(
            self.directory_url(),
            {"q": self.student.username},
        )

        records = list(
            response.context["page"].object_list
        )

        self.assertEqual(
            records,
            [self.student],
        )

    def test_search_email(self):

        self.login_admin()

        response = self.client.get(
            self.directory_url(),
            {"q": self.student.email},
        )

        records = list(
            response.context["page"].object_list
        )

        self.assertEqual(
            records,
            [self.student],
        )

    def test_search_name(self):

        self.login_admin()

        response = self.client.get(
            self.directory_url(),
            {"q": "Sample"},
        )

        self.assertIn(
            self.student,
            response.context["page"].object_list,
        )

    def test_role_filter(self):

        self.login_admin()

        response = self.client.get(
            self.directory_url(),
            {"role": CustomUser.Role.ADMINISTRATOR},
        )

        records = response.context["page"].object_list

        self.assertIn(self.admin, records)

        for account in records:

            self.assertEqual(
                account.role,
                CustomUser.Role.ADMINISTRATOR,
            )

    def test_status_filter(self):

        self.login_admin()

        response = self.client.get(
            self.directory_url(),
            {"status": "inactive"},
        )

        records = response.context["page"].object_list

        self.assertIn(
            self.inactive_student,
            records,
        )

        for account in records:

            self.assertFalse(account.is_active)

    def test_invalid_filters(self):

        self.login_admin()

        response = self.client.get(
            self.directory_url(),
            {
                "role": "invalid",
                "status": "invalid",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["selected_role"],
            "",
        )

        self.assertEqual(
            response.context["selected_status"],
            "",
        )

    # ACCOUNT STATUS MANAGEMENT

    def test_confirmation_does_not_change_status(self):

        self.login_admin()

        response = self.client.get(
            self.status_url(
                self.student,
                "deactivate",
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.student.refresh_from_db()

        self.assertTrue(self.student.is_active)

    def test_admin_deactivate_student(self):

        self.login_admin()

        response = self.client.post(
            self.status_url(
                self.student,
                "deactivate",
            )
        )

        self.assertRedirects(
            response,
            self.detail_url(self.student),
        )

        self.student.refresh_from_db()

        self.assertFalse(self.student.is_active)

    def test_admin_activate_student(self):

        self.login_admin()

        response = self.client.post(
            self.status_url(
                self.inactive_student,
                "activate",
            )
        )

        self.assertRedirects(
            response,
            self.detail_url(self.inactive_student),
        )

        self.inactive_student.refresh_from_db()

        self.assertTrue(
            self.inactive_student.is_active
        )

    def test_inactive_student_cannot_authenticate(self):

        self.login_admin()

        self.client.post(
            self.status_url(
                self.student,
                "deactivate",
            )
        )

        student_client = Client()

        authenticated = student_client.login(
            username=self.student.username,
            password="Testing-Only-482!",
        )

        self.assertFalse(authenticated)

    def test_deactivation_preserves_assessments(self):

        self.login_admin()

        self.client.post(
            self.status_url(
                self.student,
                "deactivate",
            )
        )

        self.assertTrue(
            AssessmentSession.objects.filter(
                pk=self.assessment.pk,
                user=self.student,
            ).exists()
        )

        self.assessment_response.refresh_from_db()

        self.assertEqual(
            self.assessment_response.self_rating,
            4,
        )

        self.assertEqual(
            self.assessment_response.subject_competency_id,
            self.mapping.pk,
        )

    # PRIVILEGED ACCOUNT PROTECTION

    def test_admin_cannot_deactivate_self(self):

        self.login_admin()

        response = self.client.post(
            self.status_url(
                self.admin,
                "deactivate",
            )
        )

        self.assertRedirects(
            response,
            self.detail_url(self.admin),
        )

        self.admin.refresh_from_db()

        self.assertTrue(self.admin.is_active)

    def test_admin_cannot_deactivate_other_admin(self):

        self.login_admin()

        self.client.post(
            self.status_url(
                self.other_admin,
                "deactivate",
            )
        )

        self.other_admin.refresh_from_db()

        self.assertTrue(
            self.other_admin.is_active
        )

    def test_staff_account_is_protected(self):

        self.login_admin()

        self.client.post(
            self.status_url(
                self.staff_student,
                "deactivate",
            )
        )

        self.staff_student.refresh_from_db()

        self.assertTrue(
            self.staff_student.is_active
        )

    def test_superuser_account_is_protected(self):

        self.login_admin()

        self.client.post(
            self.status_url(
                self.superuser_student,
                "deactivate",
            )
        )

        self.superuser_student.refresh_from_db()

        self.assertTrue(
            self.superuser_student.is_active
        )

    # REQUEST VALIDATION

    def test_invalid_status_action(self):

        self.login_admin()

        response = self.client.post(
            self.status_url(
                self.student,
                "delete",
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_nonexistent_account(self):

        self.login_admin()

        response = self.client.get(
            reverse(
                "accounts:user_detail",
                args=[999999999],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_status_change_requires_csrf(self):

        client = Client(
            enforce_csrf_checks=True
        )

        client.force_login(self.admin)

        response = client.post(
            self.status_url(
                self.student,
                "deactivate",
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.student.refresh_from_db()

        self.assertTrue(
            self.student.is_active
        )
