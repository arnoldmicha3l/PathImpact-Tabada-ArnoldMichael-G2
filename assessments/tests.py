
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import (
    AssessmentResponse,
    AssessmentSession,
    SubjectCompetency,
)


class AssessmentTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        users = get_user_model().objects

        cls.student = users.create_user(
            "learner",
            "learner@example.test",
        )

        cls.other = users.create_user(
            "other",
            "other@example.test",
        )

        cls.staff = users.create_user(
            "staff",
            "staff@example.test",
            role="administrator",
        )

        cls.mapping_ids = list(
            SubjectCompetency.objects.filter(
                subject__program__code="BSIT",
                subject__code="DB-FND",
            )
            .order_by("pk")
            .values_list("pk", flat=True)
        )

        cls.ratings = {
            f"rating_{mapping_id}": "3"
            for mapping_id in cls.mapping_ids
        }

    def test_ui_create_read_edit_delete(self):

        self.client.force_login(self.student)

        self.assertTrue(self.mapping_ids)

        # Verify student dashboard and navigation.

        dashboard = self.client.get(
            reverse("accounts:student_dashboard")
        )

        self.assertEqual(dashboard.status_code, 200)

        self.assertContains(
            dashboard,
            "New assessment",
        )

        self.assertContains(
            dashboard,
            f'href="{reverse("assessment_create")}"',
        )

        self.assertContains(
            dashboard,
            f'href="{reverse("assessment_index")}"',
        )

        # Verify assessment creation page.

        create_url = reverse("assessment_create")

        create_page = self.client.get(create_url)

        self.assertEqual(create_page.status_code, 200)

        self.assertContains(
            create_page,
            "New self-assessment",
        )

        # Create a valid assessment.

        response = self.client.post(
            create_url,
            self.ratings,
            follow=True,
        )

        attempt = AssessmentSession.objects.get(
            user=self.student
        )

        self.assertIsNotNone(attempt.completed_at)

        self.assertRedirects(
            response,
            reverse(
                "assessment_detail",
                args=[attempt.pk],
            ),
        )

        self.assertContains(
            response,
            "Self-assessment saved",
        )

        self.assertEqual(
            attempt.responses.count(),
            len(self.mapping_ids),
        )

        self.assertEqual(
            set(
                attempt.responses.values_list(
                    "subject_competency_id",
                    flat=True,
                )
            ),
            set(self.mapping_ids),
        )

        self.assertTrue(
            all(
                rating == 3
                for rating in attempt.responses.values_list(
                    "self_rating",
                    flat=True,
                )
            )
        )

        # Verify assessment history.

        history = self.client.get(
            reverse("assessment_index")
        )

        self.assertEqual(history.status_code, 200)

        self.assertContains(
            history,
            f"Assessment #{attempt.pk}",
        )

        # Verify assessment details.

        detail_url = reverse(
            "assessment_detail",
            args=[attempt.pk],
        )

        detail = self.client.get(detail_url)

        self.assertEqual(detail.status_code, 200)

        self.assertContains(
            detail,
            "Assessment results",
        )

        self.assertEqual(
            detail.context["average_rating"],
            3,
        )

        self.assertEqual(
            detail.context["response_count"],
            len(self.mapping_ids),
        )

        # Verify saved ratings are preselected.

        edit_url = reverse(
            "assessment_edit",
            args=[attempt.pk],
        )

        edit_page = self.client.get(edit_url)

        self.assertEqual(edit_page.status_code, 200)

        form = edit_page.context["form"]

        for mapping_id in self.mapping_ids:

            field_name = f"rating_{mapping_id}"

            self.assertEqual(
                str(form[field_name].value()),
                "3",
            )

            selected_options = [
                option
                for option in form[field_name]
                if option.data["selected"]
            ]

            self.assertEqual(
                len(selected_options),
                1,
            )

            self.assertEqual(
                str(selected_options[0].data["value"]),
                "3",
            )

        # Update the existing assessment.

        updated_ratings = {
            key: "5"
            for key in self.ratings
        }

        updated = self.client.post(
            edit_url,
            updated_ratings,
            follow=True,
        )

        self.assertRedirects(
            updated,
            detail_url,
        )

        self.assertContains(
            updated,
            "Self-assessment updated",
        )

        self.assertEqual(
            AssessmentSession.objects.filter(
                user=self.student
            ).count(),
            1,
        )

        self.assertEqual(
            list(
                attempt.responses.values_list(
                    "self_rating",
                    flat=True,
                )
            ),
            [5] * len(self.mapping_ids),
        )

        # Verify GET displays confirmation without deletion.

        delete_url = reverse(
            "assessment_delete",
            args=[attempt.pk],
        )

        confirmation = self.client.get(delete_url)

        self.assertEqual(
            confirmation.status_code,
            200,
        )

        self.assertContains(
            confirmation,
            "Confirm deletion",
        )

        self.assertTrue(
            AssessmentSession.objects.filter(
                pk=attempt.pk
            ).exists()
        )

        self.assertEqual(
            attempt.responses.count(),
            len(self.mapping_ids),
        )

        # Verify POST deletes the assessment and responses.

        deleted = self.client.post(
            delete_url,
            follow=True,
        )

        self.assertRedirects(
            deleted,
            reverse("assessment_index"),
        )

        self.assertContains(
            deleted,
            "Self-assessment deleted",
        )

        self.assertFalse(
            AssessmentSession.objects.filter(
                pk=attempt.pk
            ).exists()
        )

        self.assertFalse(
            AssessmentResponse.objects.filter(
                assessment_id=attempt.pk
            ).exists()
        )

    def test_reject_missing_and_out_of_bounds_ratings(self):

        self.client.force_login(self.student)

        self.assertTrue(self.mapping_ids)

        url = reverse("assessment_create")

        # Missing required rating.

        values = self.ratings.copy()

        missing_field = next(iter(values))

        values.pop(missing_field)

        missing_response = self.client.post(
            url,
            values,
        )

        self.assertEqual(
            missing_response.status_code,
            200,
        )

        self.assertContains(
            missing_response,
            "Select a rating for this competency.",
        )

        missing_errors = (
            missing_response.context["form"]
            .errors.as_data()
        )

        self.assertIn(
            missing_field,
            missing_errors,
        )

        self.assertEqual(
            missing_errors[missing_field][0].code,
            "required",
        )

        self.assertFalse(
            AssessmentSession.objects.exists()
        )

        self.assertFalse(
            AssessmentResponse.objects.exists()
        )

        # Reject ratings outside the allowed range.

        for invalid_rating in ("0", "6", "9", "-1", "abc"):

            with self.subTest(rating=invalid_rating):

                invalid_values = {
                    key: invalid_rating
                    for key in self.ratings
                }

                invalid_response = self.client.post(
                    url,
                    invalid_values,
                )

                self.assertEqual(
                    invalid_response.status_code,
                    200,
                )

                self.assertContains(
                    invalid_response,
                    "Select a valid rating from 1 to 5.",
                )

                errors = (
                    invalid_response.context["form"]
                    .errors.as_data()
                )

                for field_name in self.ratings:

                    self.assertIn(
                        field_name,
                        errors,
                    )

                    self.assertEqual(
                        errors[field_name][0].code,
                        "invalid_choice",
                    )

                self.assertFalse(
                    AssessmentSession.objects.exists()
                )

                self.assertFalse(
                    AssessmentResponse.objects.exists()
                )

    def test_guest_staff_and_other_student_access(self):

        attempt = AssessmentSession.objects.create(
            user=self.student
        )

        routes = [
            reverse(name, args=[attempt.pk])
            for name in (
                "assessment_detail",
                "assessment_edit",
                "assessment_delete",
            )
        ]

        # Guests must authenticate.

        guest_routes = [
            reverse("assessment_index"),
            reverse("assessment_create"),
            *routes,
        ]

        for url in guest_routes:

            with self.subTest(guest_url=url):

                self.assertRedirects(
                    self.client.get(url),
                    reverse("accounts:login")
                    + "?next="
                    + url,
                )

        # Administrators cannot access student assessments.

        self.client.force_login(self.staff)

        for url in guest_routes:

            with self.subTest(administrator_url=url):

                self.assertEqual(
                    self.client.get(url).status_code,
                    403,
                )

        self.assertEqual(
            self.client.post(
                reverse("assessment_create"),
                self.ratings,
            ).status_code,
            403,
        )

        self.assertEqual(
            self.client.post(
                routes[1],
                self.ratings,
            ).status_code,
            403,
        )

        self.assertEqual(
            self.client.post(routes[2]).status_code,
            403,
        )

        self.assertNotContains(
            self.client.get(
                reverse(
                    "accounts:administrator_dashboard"
                )
            ),
            "Self-assessments",
        )

        # Students cannot access another student's assessment.

        self.client.force_login(self.other)

        for url in routes:

            with self.subTest(other_student_url=url):

                self.assertEqual(
                    self.client.get(url).status_code,
                    404,
                )

        self.assertEqual(
            self.client.post(
                routes[1],
                self.ratings,
            ).status_code,
            404,
        )

        self.assertEqual(
            self.client.post(routes[2]).status_code,
            404,
        )

        self.assertTrue(
            AssessmentSession.objects.filter(
                pk=attempt.pk,
                user=self.student,
            ).exists()
        )

    def test_database_rejects_duplicate_and_invalid_ratings(self):

        self.assertTrue(self.mapping_ids)

        attempt = AssessmentSession.objects.create(
            user=self.student
        )

        competency = SubjectCompetency.objects.get(
            pk=self.mapping_ids[0]
        )

        data = {
            "assessment": attempt,
            "subject_competency": competency,
        }

        # Database must reject ratings outside 1 to 5.

        for invalid_rating in (0, 6):

            with self.subTest(rating=invalid_rating):

                with self.assertRaises(IntegrityError):

                    with transaction.atomic():

                        AssessmentResponse.objects.create(
                            **data,
                            self_rating=invalid_rating,
                        )

        # A valid response must be accepted.

        AssessmentResponse.objects.create(
            **data,
            self_rating=2,
        )

        # Duplicate competency responses must be rejected.

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                AssessmentResponse.objects.create(
                    **data,
                    self_rating=4,
                )

        self.assertEqual(
            attempt.responses.count(),
            1,
        )

        self.assertEqual(
            attempt.responses.get().self_rating,
            2,
        )
