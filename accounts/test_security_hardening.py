
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from assessments.models import AssessmentSession


User = get_user_model()


class SecurityHardeningTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.student = User.objects.create_user(
            username="hardening_student",
            email="hardening_student@example.test",
            password="Security-Test!9274",
            role="student",
        )

        cls.administrator = User.objects.create_user(
            username="hardening_admin",
            email="hardening_admin@example.test",
            password="Security-Test!9274",
            role="administrator",
        )

        cls.other = User.objects.create_user(
            username="hardening_other",
            email="hardening_other@example.test",
            password="Security-Test!9274",
            role="student",
        )

        cls.attempt = AssessmentSession.objects.create(
            user=cls.student
        )

    # =====================================================
    # CACHE PROTECTION
    # =====================================================

    def assert_private_response(self, response):

        self.assertEqual(response.status_code, 200)

        cache_control = response.headers.get(
            "Cache-Control",
            "",
        )

        self.assertIn("no-store", cache_control)
        self.assertIn("private", cache_control)

    def test_student_dashboard_not_cached(self):

        self.client.force_login(self.student)

        self.assert_private_response(
            self.client.get(
                reverse("accounts:student_dashboard")
            )
        )

    def test_administrator_dashboard_not_cached(self):

        self.client.force_login(self.administrator)

        self.assert_private_response(
            self.client.get(
                reverse("accounts:administrator_dashboard")
            )
        )

    def test_profile_not_cached(self):

        self.client.force_login(self.student)

        self.assert_private_response(
            self.client.get(
                reverse("accounts:profile")
            )
        )

    def test_edit_profile_not_cached(self):

        self.client.force_login(self.student)

        self.assert_private_response(
            self.client.get(
                reverse("accounts:edit_profile")
            )
        )

    def test_assessment_history_not_cached(self):

        self.client.force_login(self.student)

        self.assert_private_response(
            self.client.get(
                reverse("assessment_index")
            )
        )

    def test_assessment_detail_not_cached(self):

        self.client.force_login(self.student)

        self.assert_private_response(
            self.client.get(
                reverse(
                    "assessment_detail",
                    args=[self.attempt.pk],
                )
            )
        )

    # =====================================================
    # ROLE AUTHORIZATION
    # =====================================================

    def test_administrator_cannot_access_history(self):

        self.client.force_login(self.administrator)

        response = self.client.get(
            reverse("assessment_index")
        )

        self.assertEqual(response.status_code, 403)

    def test_administrator_cannot_view_assessment(self):

        self.client.force_login(self.administrator)

        response = self.client.get(
            reverse(
                "assessment_detail",
                args=[self.attempt.pk],
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_administrator_cannot_edit_assessment(self):

        self.client.force_login(self.administrator)

        url = reverse(
            "assessment_edit",
            args=[self.attempt.pk],
        )

        before = AssessmentSession.objects.values().get(
            pk=self.attempt.pk
        )

        self.assertEqual(
            self.client.get(url).status_code,
            403,
        )

        self.assertEqual(
            self.client.post(url, {}).status_code,
            403,
        )

        self.assertEqual(
            AssessmentSession.objects.values().get(
                pk=self.attempt.pk
            ),
            before,
        )

    def test_administrator_cannot_delete_assessment(self):

        self.client.force_login(self.administrator)

        url = reverse(
            "assessment_delete",
            args=[self.attempt.pk],
        )

        self.assertEqual(
            self.client.get(url).status_code,
            403,
        )

        self.assertEqual(
            self.client.post(url).status_code,
            403,
        )

        self.assertTrue(
            AssessmentSession.objects.filter(
                pk=self.attempt.pk
            ).exists()
        )

    # =====================================================
    # PROFILE VALIDATION
    # =====================================================

    def test_duplicate_profile_email_rejected(self):

        self.client.force_login(self.student)

        original_email = self.student.email

        response = self.client.post(
            reverse("accounts:edit_profile"),
            {
                "first_name": "Updated",
                "last_name": "Student",
                "email": self.other.email.upper(),
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "email",
            response.context["form"].errors,
        )

        self.student.refresh_from_db()

        self.assertEqual(
            self.student.email,
            original_email,
        )

    def test_profile_cannot_change_activation_status(self):

        self.client.force_login(self.student)

        response = self.client.post(
            reverse("accounts:edit_profile"),
            {
                "first_name": "Updated",
                "last_name": "Student",
                "email": self.student.email,
                "is_active": "false",
                "role": "administrator",
                "is_staff": "true",
                "is_superuser": "true",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.student.refresh_from_db()

        self.assertEqual(
            self.student.first_name,
            "Updated",
        )

        self.assertTrue(self.student.is_active)
        self.assertEqual(self.student.role, "student")
        self.assertFalse(self.student.is_staff)
        self.assertFalse(self.student.is_superuser)

    # =====================================================
    # CSRF PROTECTION
    # =====================================================

    def test_profile_update_requires_csrf(self):

        client = Client(enforce_csrf_checks=True)

        client.force_login(self.student)

        original_name = self.student.first_name

        response = client.post(
            reverse("accounts:edit_profile"),
            {
                "first_name": "Unauthorized",
                "last_name": "Student",
                "email": self.student.email,
            },
        )

        self.assertEqual(response.status_code, 403)

        self.student.refresh_from_db()

        self.assertEqual(
            self.student.first_name,
            original_name,
        )

    def test_assessment_creation_requires_csrf(self):

        client = Client(enforce_csrf_checks=True)

        client.force_login(self.student)

        before = AssessmentSession.objects.count()

        response = client.post(
            reverse("assessment_create"),
            {},
        )

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            AssessmentSession.objects.count(),
            before,
        )

    def test_assessment_edit_requires_csrf(self):

        client = Client(enforce_csrf_checks=True)

        client.force_login(self.student)

        before = AssessmentSession.objects.values().get(
            pk=self.attempt.pk
        )

        response = client.post(
            reverse(
                "assessment_edit",
                args=[self.attempt.pk],
            ),
            {},
        )

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            AssessmentSession.objects.values().get(
                pk=self.attempt.pk
            ),
            before,
        )

    def test_assessment_delete_requires_csrf(self):

        client = Client(enforce_csrf_checks=True)

        client.force_login(self.student)

        response = client.post(
            reverse(
                "assessment_delete",
                args=[self.attempt.pk],
            )
        )

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            AssessmentSession.objects.filter(
                pk=self.attempt.pk
            ).exists()
        )

    def test_logout_requires_csrf(self):

        client = Client(enforce_csrf_checks=True)

        client.force_login(self.student)

        response = client.post(
            reverse("accounts:logout")
        )

        self.assertEqual(response.status_code, 403)

        self.assertIn(
            "_auth_user_id",
            client.session,
        )

    def test_registration_requires_csrf(self):

        client = Client(enforce_csrf_checks=True)

        before = User.objects.count()

        response = client.post(
            reverse("accounts:register"),
            {
                "username": "unauthorized_registration",
                "email": "unauthorized@example.test",
                "password1": "Security-Test!9274",
                "password2": "Security-Test!9274",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            User.objects.count(),
            before,
        )

    # =====================================================
    # HTTP METHOD RESTRICTIONS
    # =====================================================

    def test_profile_rejects_post(self):

        self.client.force_login(self.student)

        response = self.client.post(
            reverse("accounts:profile")
        )

        self.assertEqual(response.status_code, 405)

    def test_assessment_history_rejects_post(self):

        self.client.force_login(self.student)

        response = self.client.post(
            reverse("assessment_index")
        )

        self.assertEqual(response.status_code, 405)

    def test_assessment_detail_rejects_post(self):

        self.client.force_login(self.student)

        response = self.client.post(
            reverse(
                "assessment_detail",
                args=[self.attempt.pk],
            )
        )

        self.assertEqual(response.status_code, 405)

    def test_administrator_dashboard_rejects_post(self):

        self.client.force_login(self.administrator)

        response = self.client.post(
            reverse("accounts:administrator_dashboard")
        )

        self.assertEqual(response.status_code, 405)
