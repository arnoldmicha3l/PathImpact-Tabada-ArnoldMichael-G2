from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import Http404
from django.test import TestCase
from django.utils import timezone

from .models import (
    AcademicProgram,
    Subject,
    Competency,
    SubjectCompetency,
    SubjectPrerequisite,
    CompetencyImpact,
    AssessmentSession,
    AssessmentResponse,
    ReadinessResult,
    ReviewRecommendation,
)

from .result_services import (
    generate_assessment_results,
    get_saved_assessment_results,
)


class PersistentResultTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        users = get_user_model().objects

        cls.student = users.create_user(
            username="result_student",
            email="result_student@example.test",
        )

        cls.other = users.create_user(
            username="result_other",
            email="result_other@example.test",
        )

        cls.admin = users.create_user(
            username="result_admin",
            email="result_admin@example.test",
            role="administrator",
        )

        cls.program = AcademicProgram.objects.create(
            code="RESULT-TEST",
            name="Result Test Program",
        )

        cls.foundation = Subject.objects.create(
            program=cls.program,
            code="RT-FND",
            name="Foundation Subject",
        )

        cls.successor = Subject.objects.create(
            program=cls.program,
            code="RT-ADV",
            name="Advanced Subject",
        )

        cls.competency = Competency.objects.create(
            code="RT-SQL",
            name="SQL Queries",
            description="SQL query preparation.",
        )

        cls.mapping = SubjectCompetency.objects.create(
            subject=cls.foundation,
            competency=cls.competency,
        )

        cls.relationship = SubjectPrerequisite.objects.create(
            prerequisite=cls.foundation,
            successor=cls.successor,
        )

        cls.impact = CompetencyImpact.objects.create(
            prerequisite=cls.relationship,
            subject_competency=cls.mapping,
            relevance=3,
        )

        cls.assessment = AssessmentSession.objects.create(
            user=cls.student,
            completed_at=timezone.now(),
        )

        cls.response = AssessmentResponse.objects.create(
            assessment=cls.assessment,
            subject_competency=cls.mapping,
            self_rating=2,
        )

    # =========================================================
    # HELPER METHODS
    # =========================================================

    def generate(self):

        return generate_assessment_results(
            user=self.student,
            assessment_id=self.assessment.pk,
        )

    def saved(self):

        return get_saved_assessment_results(
            user=self.student,
            assessment_id=self.assessment.pk,
        )

    # =========================================================
    # RESULT GENERATION
    # =========================================================

    def test_readiness_result_created(self):

        self.generate()

        result = ReadinessResult.objects.get(
            assessment=self.assessment
        )

        self.assertEqual(
            result.succeeding_subject_id,
            self.successor.pk,
        )

        self.assertEqual(
            result.readiness_score,
            Decimal("2.00"),
        )

        self.assertEqual(
            result.readiness_level,
            "Needs strengthening",
        )

    def test_recommendation_created(self):

        self.generate()

        recommendation = (
            ReviewRecommendation.objects.get(
                response=self.response
            )
        )

        self.assertEqual(
            recommendation.priority_rank,
            1,
        )

        self.assertEqual(
            recommendation.priority_score,
            9,
        )

        self.assertEqual(
            recommendation.relevance,
            3,
        )

    def test_repeated_generation_no_duplicates(self):

        self.generate()

        self.generate()

        self.assertEqual(
            self.assessment.readiness_results.count(),
            1,
        )

        self.assertEqual(
            self.response.review_recommendations.count(),
            1,
        )

    def test_updated_rating_replaces_results(self):

        self.generate()

        self.response.self_rating = 5

        self.response.save(
            update_fields=["self_rating"]
        )

        self.generate()

        result = self.assessment.readiness_results.get()

        self.assertEqual(
            result.readiness_score,
            Decimal("5.00"),
        )

        self.assertFalse(
            result.is_affected
        )

        self.assertFalse(
            self.response.review_recommendations.exists()
        )

    # =========================================================
    # CASCADE DELETION
    # =========================================================

    def test_assessment_delete_cascades_results(self):

        self.generate()

        assessment_id = self.assessment.pk

        response_id = self.response.pk

        self.assessment.delete()

        self.assertFalse(
            ReadinessResult.objects.filter(
                assessment_id=assessment_id
            ).exists()
        )

        self.assertFalse(
            ReviewRecommendation.objects.filter(
                response_id=response_id
            ).exists()
        )

    def test_response_delete_cascades_recommendation(self):

        self.generate()

        response_id = self.response.pk

        self.response.delete()

        self.assertFalse(
            ReviewRecommendation.objects.filter(
                response_id=response_id
            ).exists()
        )

    # =========================================================
    # HISTORICAL SNAPSHOT CONSISTENCY
    # =========================================================

    def test_saved_relevance_snapshot(self):

        self.generate()

        self.impact.relevance = 1

        self.impact.save(
            update_fields=["relevance"]
        )

        saved = self.saved()

        recommendation = saved["recommendations"][0]

        self.assertEqual(
            recommendation.relevance,
            3,
        )

        self.assertEqual(
            recommendation.priority_score,
            9,
        )

    def test_subject_name_snapshot(self):

        self.generate()

        original_name = self.successor.name

        self.successor.name = "Renamed Subject"

        self.successor.save(
            update_fields=["name"]
        )

        result = self.saved()["readiness_results"][0]

        self.assertEqual(
            result.subject_name_snapshot,
            original_name,
        )

    # =========================================================
    # MISSING AND INCOMPLETE INFORMATION
    # =========================================================

    def test_no_impacts_no_saved_results(self):

        self.impact.delete()

        self.generate()

        self.assertEqual(
            self.assessment.readiness_results.count(),
            0,
        )

        self.assertEqual(
            self.saved()["status"],
            "no_saved_results",
        )

    def test_incomplete_assessment_no_results(self):

        self.assessment.completed_at = None

        self.assessment.save(
            update_fields=["completed_at"]
        )

        self.generate()

        self.assertFalse(
            self.assessment.readiness_results.exists()
        )

        self.assertEqual(
            self.saved()["status"],
            "incomplete_assessment",
        )

    # =========================================================
    # SECURITY AND OWNERSHIP
    # =========================================================

    def test_other_student_cannot_generate(self):

        with self.assertRaises(Http404):

            generate_assessment_results(
                user=self.other,
                assessment_id=self.assessment.pk,
            )

    def test_other_student_cannot_read(self):

        self.generate()

        with self.assertRaises(Http404):

            get_saved_assessment_results(
                user=self.other,
                assessment_id=self.assessment.pk,
            )

    def test_administrator_cannot_generate(self):

        with self.assertRaises(PermissionDenied):

            generate_assessment_results(
                user=self.admin,
                assessment_id=self.assessment.pk,
            )

    def test_administrator_cannot_read(self):

        self.generate()

        with self.assertRaises(PermissionDenied):

            get_saved_assessment_results(
                user=self.admin,
                assessment_id=self.assessment.pk,
            )

    def test_inactive_student_cannot_read(self):

        self.generate()

        self.student.is_active = False

        with self.assertRaises(PermissionDenied):

            self.saved()

    # =========================================================
    # DATABASE CONSTRAINTS
    # =========================================================

    def test_duplicate_readiness_rejected(self):

        self.generate()

        record = self.assessment.readiness_results.get()

        record.pk = None

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                record.save(
                    force_insert=True
                )

    def test_duplicate_recommendation_rejected(self):

        self.generate()

        record = self.response.review_recommendations.get()

        record.pk = None

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                record.save(
                    force_insert=True
                )

    def test_invalid_readiness_score_rejected(self):

        self.generate()

        record = self.assessment.readiness_results.get()

        record.readiness_score = Decimal("6.00")

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                record.save(
                    update_fields=["readiness_score"]
                )

    def test_invalid_priority_rank_rejected(self):

        self.generate()

        record = self.response.review_recommendations.get()

        record.priority_rank = 0

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                record.save(
                    update_fields=["priority_rank"]
                )

    def test_invalid_recommendation_rating_rejected(self):

        self.generate()

        record = self.response.review_recommendations.get()

        record.self_rating_snapshot = 5

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                record.save(
                    update_fields=["self_rating_snapshot"]
                )

    # =========================================================
    # RULE VERSION AND RESULT METADATA
    # =========================================================

    def test_rule_version_saved(self):

        self.generate()

        self.assertEqual(
            self.assessment.readiness_results.get()
            .rule_version,
            "1.0.0",
        )

        self.assertEqual(
            self.response.review_recommendations.get()
            .rule_version,
            "1.0.0",
        )

    def test_saved_results_are_read_only(self):

        self.generate()

        before = list(
            self.assessment.readiness_results.values()
        )

        self.saved()

        self.saved()

        after = list(
            self.assessment.readiness_results.values()
        )

        self.assertEqual(
            before,
            after,
        )

    def test_generated_timestamp_present(self):

        self.generate()

        result = self.saved()

        self.assertIsNotNone(
            result["generated_at"]
        )

    # =========================================================
    # TRANSACTIONAL INTEGRITY
    # =========================================================

    def test_failed_generation_preserves_results(self):

        self.generate()

        before = list(
            self.assessment.readiness_results.values()
        )

        with patch(
            "assessments.result_services."
            "ReviewRecommendation.objects.bulk_create",
            side_effect=RuntimeError("Simulated failure"),
        ):

            with self.assertRaises(RuntimeError):

                self.generate()

        after = list(
            self.assessment.readiness_results.values()
        )

        self.assertEqual(
            before,
            after,
        )

        self.assertEqual(
            self.response.review_recommendations.count(),
            1,
        )