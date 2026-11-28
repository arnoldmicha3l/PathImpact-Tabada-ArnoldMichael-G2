
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from assessments.models import (
    AssessmentSession,
    AssessmentResponse,
    SubjectCompetency,
)


User = get_user_model()


class AccessControlTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.password = "PathImpact-Test!9274"

        cls.student = User.objects.create_user(
            username="security_student",
            email="student@example.test",
            password=cls.password,
            role="student",
        )

        cls.other = User.objects.create_user(
            username="security_other",
            email="other@example.test",
            password=cls.password,
            role="student",
        )

        cls.admin = User.objects.create_user(
            username="security_admin",
            email="admin@example.test",
            password=cls.password,
            role="administrator",
        )

        cls.inactive = User.objects.create_user(
            username="security_inactive",
            email="inactive@example.test",
            password=cls.password,
            role="student",
            is_active=False,
        )

        cls.attempt = AssessmentSession.objects.create(
            user=cls.student
        )

        cls.mapping = SubjectCompetency.objects.filter(
            subject__program__code="BSIT",
            subject__code="DB-FND",
        ).first()

        if cls.mapping is not None:

            AssessmentResponse.objects.create(
                assessment=cls.attempt,
                subject_competency=cls.mapping,
                self_rating=3,
            )

    # =====================================================
    # AUTHENTICATION
    # =====================================================

    def test_guest_cannot_access_dashboard(self):

        response = self.client.get(
            reverse("accounts:dashboard")
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            response.url.startswith(
                reverse("accounts:login")
            )
        )

    def test_guest_cannot_access_profile(self):

        for name in (
            "accounts:profile",
            "accounts:edit_profile",
        ):

            with self.subTest(name=name):

                response = self.client.get(
                    reverse(name)
                )

                self.assertEqual(
                    response.status_code,
                    302,
                )

    def test_guest_cannot_access_assessments(self):

        for name in (
            "assessment_index",
            "assessment_create",
        ):

            with self.subTest(name=name):

                response = self.client.get(
                    reverse(name)
                )

                self.assertEqual(
                    response.status_code,
                    302,
                )

    def test_inactive_user_cannot_login(self):

        authenticated = self.client.login(
            username=self.inactive.username,
            password=self.password,
        )

        self.assertFalse(authenticated)

    def test_deactivated_session_loses_access(self):

        self.client.force_login(self.student)

        User.objects.filter(
            pk=self.student.pk
        ).update(
            is_active=False
        )

        response = self.client.get(
            reverse("accounts:dashboard")
        )

        self.assertIn(
            response.status_code,
            (302, 403),
        )

    # =====================================================
    # ROLE AUTHORIZATION
    # =====================================================

    def test_student_cannot_access_admin_dashboard(self):

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "accounts:administrator_dashboard"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_admin_cannot_access_student_dashboard(self):

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("accounts:student_dashboard")
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_admin_cannot_create_student_assessment(self):

        self.client.force_login(self.admin)

        before = AssessmentSession.objects.count()

        response = self.client.post(
            reverse("assessment_create"),
            {},
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            AssessmentSession.objects.count(),
            before,
        )

    def test_student_dashboard_redirect(self):

        self.client.force_login(self.student)

        response = self.client.get(
            reverse("accounts:dashboard")
        )

        self.assertRedirects(
            response,
            reverse("accounts:student_dashboard"),
            fetch_redirect_response=False,
        )

    def test_admin_dashboard_redirect(self):

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("accounts:dashboard")
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:administrator_dashboard"
            ),
            fetch_redirect_response=False,
        )

    # =====================================================
    # REGISTRATION SECURITY
    # =====================================================

    def test_registration_cannot_assign_admin_role(self):

        password = "Secure-Registration!8624"

        response = self.client.post(

            reverse("accounts:register"),

            {
                "username": "security_new_user",
                "email": "newuser@example.test",
                "password1": password,
                "password2": password,

                # Unauthorized submitted fields
                "role": "administrator",
                "is_staff": "true",
                "is_superuser": "true",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        user = User.objects.get(
            username="security_new_user"
        )

        self.assertEqual(user.role, "student")

        self.assertFalse(user.is_staff)

        self.assertFalse(user.is_superuser)

        self.assertTrue(
            user.check_password(password)
        )

    # =====================================================
    # PROFILE SECURITY
    # =====================================================

    def test_profile_cannot_change_role(self):

        self.client.force_login(self.student)

        response = self.client.post(

            reverse("accounts:edit_profile"),

            {
                "first_name": "Updated",
                "last_name": "Student",
                "email": self.student.email,
                "role": "administrator",
                "is_staff": "true",
                "is_superuser": "true",
                "username": "changed_username",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.student.refresh_from_db()

        self.assertEqual(
            self.student.first_name,
            "Updated",
        )

        self.assertEqual(
            self.student.role,
            "student",
        )

        self.assertEqual(
            self.student.username,
            "security_student",
        )

        self.assertFalse(
            self.student.is_staff
        )

        self.assertFalse(
            self.student.is_superuser
        )

    def test_profile_cannot_modify_another_user(self):

        self.client.force_login(self.student)

        self.client.post(

            reverse("accounts:edit_profile"),

            {
                "first_name": "Updated",
                "last_name": "Student",
                "email": self.student.email,
                "user_id": self.other.pk,
                "id": self.other.pk,
            },
        )

        self.other.refresh_from_db()

        self.assertEqual(
            self.other.first_name,
            "",
        )

    # =====================================================
    # ASSESSMENT OWNERSHIP
    # =====================================================

    def test_other_student_cannot_view_assessment(self):

        self.client.force_login(self.other)

        response = self.client.get(

            reverse(
                "assessment_detail",
                args=[self.attempt.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_other_student_cannot_edit_assessment(self):

        self.client.force_login(self.other)

        url = reverse(
            "assessment_edit",
            args=[self.attempt.pk],
        )

        self.assertEqual(
            self.client.get(url).status_code,
            404,
        )

        before = list(
            self.attempt.responses.values()
        )

        self.assertEqual(
            self.client.post(url, {}).status_code,
            404,
        )

        self.assertEqual(

            list(
                self.attempt.responses.values()
            ),

            before,
        )

    def test_other_student_cannot_delete_assessment(self):

        self.client.force_login(self.other)

        url = reverse(
            "assessment_delete",
            args=[self.attempt.pk],
        )

        self.assertEqual(
            self.client.get(url).status_code,
            404,
        )

        self.assertEqual(
            self.client.post(url).status_code,
            404,
        )

        self.assertTrue(
            AssessmentSession.objects.filter(
                pk=self.attempt.pk
            ).exists()
        )

    def test_history_only_contains_owned_assessments(self):

        self.client.force_login(self.student)

        other_attempt = AssessmentSession.objects.create(
            user=self.other
        )

        response = self.client.get(
            reverse("assessment_index")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        items = response.context["items"]

        self.assertIn(
            self.attempt,
            items,
        )

        self.assertNotIn(
            other_attempt,
            items,
        )

    # =====================================================
    # HTTP METHODS AND SESSION SECURITY
    # =====================================================

    def test_dashboard_rejects_post(self):

        self.client.force_login(self.student)

        response = self.client.post(
            reverse("accounts:student_dashboard")
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_logout_requires_post(self):

        self.client.force_login(self.student)

        response = self.client.get(
            reverse("accounts:logout")
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_invalidates_session(self):

        self.client.force_login(self.student)

        response = self.client.post(
            reverse("accounts:logout")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        response = self.client.get(
            reverse("accounts:dashboard")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_delete_confirmation_does_not_delete(self):

        self.client.force_login(self.student)

        response = self.client.get(

            reverse(
                "assessment_delete",
                args=[self.attempt.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            AssessmentSession.objects.filter(
                pk=self.attempt.pk
            ).exists()
        )
