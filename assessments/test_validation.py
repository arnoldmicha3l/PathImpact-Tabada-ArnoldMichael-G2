
from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse

from .forms import AssessmentForm

from .models import (
    AcademicProgram,
    Subject,
    Competency,
    SubjectCompetency,
    AssessmentSession,
    AssessmentResponse,
)


User = get_user_model()


class AssessmentValidationTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.student = User.objects.create_user(
            username="validation_learner",
            email="learner-validation@example.test",
        )

        cls.program, _ = (
            AcademicProgram.objects.get_or_create(
                code="BSIT",
                defaults={
                    "name": (
                        "Bachelor of Science in "
                        "Information Technology"
                    ),
                },
            )
        )

        cls.subject, _ = Subject.objects.get_or_create(
            program=cls.program,
            code="DB-FND",
            defaults={
                "name": "Database Foundations",
            },
        )

        cls.competency = Competency.objects.create(
            code="VALIDATION-DB-01",
            name="Validation competency",
            description="Demonstrate database fundamentals.",
        )

        cls.mapping = SubjectCompetency.objects.create(
            subject=cls.subject,
            competency=cls.competency,
        )

        cls.catalog = list(
            SubjectCompetency.objects.filter(
                subject=cls.subject
            ).select_related("competency")
        )

        cls.ratings = {
            f"rating_{item.pk}": "3"
            for item in cls.catalog
        }

    def test_valid_assessment_form(self):

        form = AssessmentForm(
            data=self.ratings,
            competencies=self.catalog,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_empty_catalog_rejected(self):

        form = AssessmentForm(
            data={},
            competencies=[],
        )

        self.assertFalse(form.is_valid())

        self.assertEqual(
            form.non_field_errors().as_data()[0].code,
            "empty_catalog",
        )

    def test_unexpected_competency_rejected(self):

        data = self.ratings.copy()
        data["rating_invalid"] = "5"

        form = AssessmentForm(
            data=data,
            competencies=self.catalog,
        )

        self.assertFalse(form.is_valid())

        self.assertEqual(
            form.non_field_errors().as_data()[0].code,
            "unexpected_competency",
        )

    def test_duplicate_rating_rejected(self):

        data = QueryDict("", mutable=True)
        data.update(self.ratings)

        field_name = f"rating_{self.mapping.pk}"

        data.setlist(field_name, ["1", "5"])

        form = AssessmentForm(
            data=data,
            competencies=self.catalog,
        )

        self.assertFalse(form.is_valid())

        self.assertEqual(
            form.errors.as_data()[field_name][0].code,
            "duplicate_rating",
        )

    def test_fractional_rating_rejected(self):

        data = self.ratings.copy()
        data[f"rating_{self.mapping.pk}"] = "3.5"

        form = AssessmentForm(
            data=data,
            competencies=self.catalog,
        )

        self.assertFalse(form.is_valid())

    def test_invalid_form_cannot_generate_responses(self):

        form = AssessmentForm(
            data={},
            competencies=self.catalog,
        )

        attempt = AssessmentSession.objects.create(
            user=self.student
        )

        with self.assertRaises(ValueError):

            form.responses(attempt)

        self.assertFalse(attempt.responses.exists())

    def test_unexpected_rating_creates_no_assessment(self):

        self.client.force_login(self.student)

        data = self.ratings.copy()
        data["rating_invalid"] = "5"

        before = AssessmentSession.objects.count()

        response = self.client.post(
            reverse("assessment_create"),
            data,
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            response.context["form"].non_field_errors()
        )

        self.assertEqual(
            AssessmentSession.objects.count(),
            before,
        )

    def test_duplicate_rating_creates_no_assessment(self):

        self.client.force_login(self.student)

        data = self.ratings.copy()

        data[f"rating_{self.mapping.pk}"] = ["1", "5"]

        before = AssessmentSession.objects.count()

        response = self.client.post(
            reverse("assessment_create"),
            data,
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            AssessmentSession.objects.count(),
            before,
        )

    def test_invalid_edit_preserves_existing_responses(self):

        self.client.force_login(self.student)

        attempt = AssessmentSession.objects.create(
            user=self.student
        )

        AssessmentResponse.objects.create(
            assessment=attempt,
            subject_competency=self.mapping,
            self_rating=3,
        )

        before = list(
            attempt.responses.values()
        )

        response = self.client.post(
            reverse(
                "assessment_edit",
                args=[attempt.pk],
            ),
            {
                f"rating_{self.mapping.pk}": "9",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            list(attempt.responses.values()),
            before,
        )

        attempt.refresh_from_db()

        self.assertIsNone(attempt.completed_at)

    def test_valid_rating_boundaries(self):

        for rating in ("1", "5"):

            with self.subTest(rating=rating):

                form = AssessmentForm(
                    data={
                        key: rating
                        for key in self.ratings
                    },
                    competencies=self.catalog,
                )

                self.assertTrue(
                    form.is_valid(),
                    form.errors,
                )
