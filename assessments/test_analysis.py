
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from .analysis_rules import (
    classify_readiness,
    display_score,
    gap_description,
    is_competency_gap,
    priority_score,
    relevance_weight,
    validate_rating,
    weighted_readiness,
)

from .analysis_services import analyze_assessment

from .models import (
    AcademicProgram,
    Subject,
    Competency,
    SubjectCompetency,
    SubjectPrerequisite,
    CompetencyImpact,
    AssessmentSession,
    AssessmentResponse,
)


class AnalysisRuleTests(SimpleTestCase):

    def test_valid_ratings(self):

        for rating in range(1, 6):

            self.assertEqual(
                validate_rating(rating),
                rating,
            )

    def test_invalid_ratings(self):

        for rating in (0, 6, -1, "3", None, True, 2.5):

            with self.subTest(rating=rating):

                with self.assertRaises(ValueError):

                    validate_rating(rating)

    def test_valid_relevance(self):

        for relevance in (1, 2, 3):

            self.assertEqual(
                relevance_weight(relevance),
                relevance,
            )

    def test_invalid_relevance(self):

        for relevance in (0, 4, None, "2", True):

            with self.subTest(relevance=relevance):

                with self.assertRaises(ValueError):

                    relevance_weight(relevance)

    def test_gap_threshold(self):

        for rating in (1, 2, 3):

            self.assertTrue(
                is_competency_gap(rating)
            )

        for rating in (4, 5):

            self.assertFalse(
                is_competency_gap(rating)
            )

    def test_gap_descriptions(self):

        self.assertEqual(
            gap_description(3),
            "Further practice recommended",
        )

    def test_weighted_readiness(self):

        score = weighted_readiness([
            (2, 3),
            (3, 2),
            (4, 1),
        ])

        self.assertEqual(
            score,
            Decimal(16) / Decimal(6),
        )

    def test_equal_weight_readiness(self):

        self.assertEqual(
            weighted_readiness([
                (2, 1),
                (4, 1),
            ]),
            Decimal("3"),
        )

    def test_missing_rating(self):

        self.assertIsNone(
            weighted_readiness([
                (3, 2),
                (None, 3),
            ])
        )

    def test_empty_readiness_inputs(self):

        self.assertIsNone(
            weighted_readiness([])
        )

    def test_readiness_boundaries(self):

        cases = [
            ("1", "Needs strengthening"),
            ("2.999", "Needs strengthening"),
            ("3", "Developing readiness"),
            ("3.999", "Developing readiness"),
            ("4", "Higher readiness"),
            ("5", "Higher readiness"),
        ]

        for score, expected in cases:

            with self.subTest(score=score):

                self.assertEqual(
                    classify_readiness(
                        Decimal(score)
                    ),
                    expected,
                )

    def test_missing_readiness(self):

        self.assertEqual(
            classify_readiness(None),
            "Insufficient information",
        )

    def test_unavailable_readiness(self):

        self.assertEqual(
            classify_readiness(
                None,
                has_impacts=False,
            ),
            "Analysis unavailable",
        )

    def test_invalid_readiness_score(self):

        for score in ("0", "6", "NaN", "Infinity"):

            with self.subTest(score=score):

                with self.assertRaises(ValueError):

                    classify_readiness(
                        Decimal(score)
                    )

    def test_display_rounding(self):

        self.assertEqual(
            display_score(Decimal("2.665")),
            Decimal("2.67"),
        )

        self.assertIsNone(
            display_score(None)
        )

    def test_priority_scores(self):

        self.assertEqual(
            priority_score(1, 3),
            12,
        )

        self.assertEqual(
            priority_score(2, 3),
            9,
        )

        self.assertEqual(
            priority_score(3, 2),
            4,
        )

    def test_no_priority_without_gap(self):

        self.assertEqual(
            priority_score(4, 3),
            0,
        )

        self.assertEqual(
            priority_score(5, 3),
            0,
        )


class AnalysisServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        users = get_user_model().objects

        cls.student = users.create_user(
            username="analysis_student",
            email="analysis_student@example.test",
        )

        cls.other = users.create_user(
            username="analysis_other",
            email="analysis_other@example.test",
        )

        cls.administrator = users.create_user(
            username="analysis_admin",
            email="analysis_admin@example.test",
            role="administrator",
        )

        cls.program = AcademicProgram.objects.create(
            code="ANALYSIS-TEST",
            name="Analysis Test Program",
        )

        cls.foundation = Subject.objects.create(
            program=cls.program,
            code="AN-FND",
            name="Database Foundations",
        )

        cls.advanced = Subject.objects.create(
            program=cls.program,
            code="AN-ADV",
            name="Advanced Databases",
        )

        cls.unlinked = Subject.objects.create(
            program=cls.program,
            code="AN-OTHER",
            name="Unlinked Subject",
        )

        cls.relationship = SubjectPrerequisite.objects.create(
            prerequisite=cls.foundation,
            successor=cls.advanced,
        )

        cls.mappings = []

        definitions = [
            ("AN-SQL", "SQL Queries"),
            ("AN-DESIGN", "Database Design"),
            ("AN-NORM", "Data Normalization"),
        ]

        for code, name in definitions:

            competency = Competency.objects.create(
                code=code,
                name=name,
                description=f"Test competency: {name}",
            )

            mapping = SubjectCompetency.objects.create(
                subject=cls.foundation,
                competency=competency,
            )

            cls.mappings.append(mapping)

        for mapping, relevance in zip(
            cls.mappings,
            (3, 2, 1),
        ):

            CompetencyImpact.objects.create(
                prerequisite=cls.relationship,
                subject_competency=mapping,
                relevance=relevance,
            )

        cls.assessment = AssessmentSession.objects.create(
            user=cls.student,
            completed_at=timezone.now(),
        )

        for mapping, rating in zip(
            cls.mappings,
            (2, 3, 4),
        ):

            AssessmentResponse.objects.create(
                assessment=cls.assessment,
                subject_competency=mapping,
                self_rating=rating,
            )

    def analyze(self):

        return analyze_assessment(
            user=self.student,
            assessment_id=self.assessment.pk,
        )

    def test_actual_response_count(self):

        result = self.analyze()

        self.assertEqual(
            result["response_count"],
            3,
        )

    def test_identified_gaps(self):

        result = self.analyze()

        self.assertEqual(
            result["gap_count"],
            2,
        )

    def test_affected_subject(self):

        result = self.analyze()

        self.assertEqual(
            result["affected_subject_count"],
            1,
        )

        self.assertEqual(
            result["subjects"][0]["subject_id"],
            self.advanced.pk,
        )

    def test_unlinked_subject_excluded(self):

        result = self.analyze()

        subject_ids = [
            subject["subject_id"]
            for subject in result["subjects"]
        ]

        self.assertNotIn(
            self.unlinked.pk,
            subject_ids,
        )

    def test_subject_readiness(self):

        result = self.analyze()

        subject = result["subjects"][0]

        self.assertEqual(
            subject["readiness_score"],
            Decimal("2.67"),
        )

        self.assertEqual(
            subject["readiness_level"],
            "Needs strengthening",
        )

    def test_priority_order(self):

        result = self.analyze()

        recommendations = result["recommendations"]

        self.assertEqual(
            len(recommendations),
            2,
        )

        self.assertEqual(
            recommendations[0]["priority_score"],
            9,
        )

        self.assertEqual(
            recommendations[0]["priority_rank"],
            1,
        )

        self.assertEqual(
            recommendations[1]["priority_score"],
            4,
        )

        self.assertEqual(
            recommendations[1]["priority_rank"],
            2,
        )

    def test_no_gaps_when_all_ratings_high(self):

        self.assessment.responses.update(
            self_rating=5
        )

        result = self.analyze()

        self.assertEqual(
            result["gap_count"],
            0,
        )

        self.assertEqual(
            result["affected_subject_count"],
            0,
        )

        self.assertEqual(
            result["recommendations"],
            [],
        )

        self.assertEqual(
            result["subjects"][0]["readiness_score"],
            Decimal("5.00"),
        )

    def test_missing_required_rating(self):

        self.assessment.responses.filter(
            subject_competency=self.mappings[2]
        ).delete()

        result = self.analyze()

        subject = result["subjects"][0]

        self.assertIsNone(
            subject["readiness_score"]
        )

        self.assertEqual(
            subject["missing_count"],
            1,
        )

        self.assertEqual(
            subject["readiness_level"],
            "Insufficient information",
        )

        self.assertEqual(
            result["status"],
            "partial_information",
        )

    def test_no_defined_impacts(self):

        CompetencyImpact.objects.filter(
            prerequisite=self.relationship
        ).delete()

        result = self.analyze()

        self.assertEqual(
            result["status"],
            "no_defined_impacts",
        )

        self.assertEqual(
            result["subjects"],
            [],
        )

        self.assertEqual(
            result["recommendations"],
            [],
        )

        self.assertEqual(
            result["gap_count"],
            2,
        )

    def test_incomplete_assessment(self):

        self.assessment.completed_at = None

        self.assessment.save(
            update_fields=["completed_at"]
        )

        result = self.analyze()

        self.assertEqual(
            result["status"],
            "incomplete_assessment",
        )

        self.assertEqual(
            result["recommendations"],
            [],
        )

    def test_no_responses(self):

        self.assessment.responses.all().delete()

        result = self.analyze()

        self.assertEqual(
            result["status"],
            "no_responses",
        )

    def test_other_student_denied(self):

        with self.assertRaises(Http404):

            analyze_assessment(
                user=self.other,
                assessment_id=self.assessment.pk,
            )

    def test_administrator_denied(self):

        with self.assertRaises(PermissionDenied):

            analyze_assessment(
                user=self.administrator,
                assessment_id=self.assessment.pk,
            )

    def test_inactive_student_denied(self):

        self.student.is_active = False

        with self.assertRaises(PermissionDenied):

            self.analyze()

    def test_analysis_does_not_modify_responses(self):

        before = list(
            self.assessment.responses.order_by(
                "pk"
            ).values()
        )

        self.analyze()

        after = list(
            self.assessment.responses.order_by(
                "pk"
            ).values()
        )

        self.assertEqual(
            before,
            after,
        )

    def test_disclaimer_present(self):

        result = self.analyze()

        self.assertIn(
            "advisory",
            result["disclaimer"],
        )

    def test_repeat_analysis_is_deterministic(self):

        self.assertEqual(
            self.analyze(),
            self.analyze(),
        )
