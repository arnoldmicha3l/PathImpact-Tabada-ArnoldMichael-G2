from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assessments.models import (
    AcademicProgram,
    AssessmentResponse,
    AssessmentSession,
    Competency,
    CompetencyImpact,
    Subject,
    SubjectCompetency,
    SubjectPrerequisite,
)

from .impact_forms import ImpactForm
from .mapping_forms import MappingForm
from .models import CustomUser
from .prerequisite_forms import PrerequisiteForm


class CompetencyImpactTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.admin = CustomUser.objects.create_user(
            username="impact_admin",
            email="impact-admin@example.com",
            role=CustomUser.Role.ADMINISTRATOR,
        )

        cls.student = CustomUser.objects.create_user(
            username="impact_student",
            email="impact-student@example.com",
            role=CustomUser.Role.STUDENT,
        )

        cls.program = AcademicProgram.objects.create(
            code="IMPACT-TEST",
            name="Impact Test Program",
        )

        cls.subject_a = Subject.objects.create(
            program=cls.program,
            code="IMP-A",
            name="Database Foundations",
        )

        cls.subject_b = Subject.objects.create(
            program=cls.program,
            code="IMP-B",
            name="Advanced Databases",
        )

        cls.subject_c = Subject.objects.create(
            program=cls.program,
            code="IMP-C",
            name="Application Development",
        )

        cls.competency = Competency.objects.create(
            code="IMP-SQL",
            name="SQL Queries",
            description="Construct basic SQL queries.",
        )

        cls.second_competency = Competency.objects.create(
            code="IMP-DESIGN",
            name="Database Design",
            description="Design relational databases.",
        )

        cls.relationship = SubjectPrerequisite.objects.create(
            prerequisite=cls.subject_a,
            successor=cls.subject_b,
        )

        cls.mapping = SubjectCompetency.objects.create(
            subject=cls.subject_a,
            competency=cls.competency,
        )

        cls.other_mapping = SubjectCompetency.objects.create(
            subject=cls.subject_c,
            competency=cls.second_competency,
        )

    def valid_data(self):

        return {
            "prerequisite": self.relationship.pk,
            "subject_competency": self.mapping.pk,
            "relevance": 3,
        }

    def create_impact(self):

        return CompetencyImpact.objects.create(
            prerequisite=self.relationship,
            subject_competency=self.mapping,
            relevance=3,
        )

    def create_response(self):

        assessment = AssessmentSession.objects.create(
            user=self.student,
            completed_at=timezone.now(),
        )

        return AssessmentResponse.objects.create(
            assessment=assessment,
            subject_competency=self.mapping,
            self_rating=2,
        )

    # ========================================
    # FORM AND MODEL VALIDATION
    # ========================================

    def test_valid_impact_form(self):

        form = ImpactForm(
            self.valid_data()
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_incompatible_mapping_rejected(self):

        data = self.valid_data()

        data["subject_competency"] = (
            self.other_mapping.pk
        )

        form = ImpactForm(data)

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "subject_competency",
            form.errors,
        )

    def test_duplicate_impact_rejected(self):

        self.create_impact()

        form = ImpactForm(
            self.valid_data()
        )

        self.assertFalse(
            form.is_valid()
        )

    def test_invalid_relevance_rejected(self):

        data = self.valid_data()

        data["relevance"] = 4

        form = ImpactForm(data)

        self.assertFalse(
            form.is_valid()
        )

    def test_missing_mapping_rejected(self):

        data = self.valid_data()

        data["subject_competency"] = ""

        form = ImpactForm(data)

        self.assertFalse(
            form.is_valid()
        )

    def test_model_validation_rejects_incompatible_mapping(self):

        impact = CompetencyImpact(
            prerequisite=self.relationship,
            subject_competency=self.other_mapping,
            relevance=3,
        )

        with self.assertRaises(ValidationError):

            impact.full_clean()

    # ========================================
    # ACCESS CONTROL
    # ========================================

    def test_guest_requires_login(self):

        response = self.client.get(
            reverse("accounts:impacts")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_student_cannot_access_directory(self):

        self.client.force_login(
            self.student
        )

        response = self.client.get(
            reverse("accounts:impacts")
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_student_cannot_create_impact(self):

        self.client.force_login(
            self.student
        )

        response = self.client.post(
            reverse("accounts:impact_create"),
            self.valid_data(),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            CompetencyImpact.objects.count(),
            0,
        )

    # ========================================
    # IMPACT MANAGEMENT
    # ========================================

    def test_administrator_can_view_directory(self):

        self.create_impact()

        self.client.force_login(
            self.admin
        )

        response = self.client.get(
            reverse("accounts:impacts")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["total_count"],
            1,
        )

    def test_administrator_can_create_impact(self):

        self.client.force_login(
            self.admin
        )

        response = self.client.post(
            reverse("accounts:impact_create"),
            self.valid_data(),
        )

        self.assertRedirects(
            response,
            reverse("accounts:impacts"),
        )

        self.assertEqual(
            CompetencyImpact.objects.count(),
            1,
        )

    def test_administrator_can_edit_unused_impact(self):

        impact = self.create_impact()

        self.client.force_login(
            self.admin
        )

        data = self.valid_data()

        data["relevance"] = 2

        response = self.client.post(
            reverse(
                "accounts:impact_edit",
                args=[impact.pk],
            ),
            data,
        )

        self.assertRedirects(
            response,
            reverse("accounts:impacts"),
        )

        impact.refresh_from_db()

        self.assertEqual(
            impact.relevance,
            2,
        )

    def test_get_does_not_delete_impact(self):

        impact = self.create_impact()

        self.client.force_login(
            self.admin
        )

        response = self.client.get(
            reverse(
                "accounts:impact_delete",
                args=[impact.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            CompetencyImpact.objects.filter(
                pk=impact.pk
            ).exists()
        )

    def test_administrator_can_remove_unused_impact(self):

        impact = self.create_impact()

        self.client.force_login(
            self.admin
        )

        response = self.client.post(
            reverse(
                "accounts:impact_delete",
                args=[impact.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("accounts:impacts"),
        )

        self.assertFalse(
            CompetencyImpact.objects.filter(
                pk=impact.pk
            ).exists()
        )

    # ========================================
    # RELATIONSHIP PROTECTION
    # ========================================

    def test_referenced_prerequisite_cannot_be_deleted(self):

        self.create_impact()

        with self.assertRaises(ProtectedError):

            self.relationship.delete()

    def test_referenced_mapping_cannot_be_deleted(self):

        self.create_impact()

        with self.assertRaises(ProtectedError):

            self.mapping.delete()

    def test_referenced_prerequisite_cannot_be_edited(self):

        self.create_impact()

        form = PrerequisiteForm(
            {
                "prerequisite": self.subject_a.pk,
                "successor": self.subject_c.pk,
            },
            instance=self.relationship,
        )

        self.assertFalse(
            form.is_valid()
        )

    def test_referenced_mapping_cannot_be_edited(self):

        self.create_impact()

        form = MappingForm(
            {
                "subject": self.subject_b.pk,
                "competency": self.competency.pk,
            },
            instance=self.mapping,
        )

        self.assertFalse(
            form.is_valid()
        )

    def test_assessed_impact_cannot_be_removed(self):

        impact = self.create_impact()

        self.create_response()

        self.client.force_login(
            self.admin
        )

        response = self.client.post(
            reverse(
                "accounts:impact_delete",
                args=[impact.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("accounts:impacts"),
        )

        self.assertTrue(
            CompetencyImpact.objects.filter(
                pk=impact.pk
            ).exists()
        )

    def test_assessed_impact_cannot_be_modified(self):

        impact = self.create_impact()

        self.create_response()

        self.client.force_login(
            self.admin
        )

        data = self.valid_data()

        data["relevance"] = 1

        response = self.client.post(
            reverse(
                "accounts:impact_edit",
                args=[impact.pk],
            ),
            data,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        impact.refresh_from_db()

        self.assertEqual(
            impact.relevance,
            3,
        )

    # ========================================
    # FILTERING
    # ========================================

    def test_relevance_filter(self):

        impact = self.create_impact()

        self.client.force_login(
            self.admin
        )

        response = self.client.get(
            reverse("accounts:impacts"),
            {
                "relevance": "3",
            },
        )

        self.assertEqual(
            list(
                response.context["page"].object_list
            ),
            [impact],
        )

        response = self.client.get(
            reverse("accounts:impacts"),
            {
                "relevance": "1",
            },
        )

        self.assertEqual(
            response.context["filtered_count"],
            0,
        )

    # ========================================
    # INTEGRATION TESTS
    # ========================================

    def test_prerequisite_delete_view_preserves_dependency(self):

        self.create_impact()

        self.client.force_login(
            self.admin
        )

        response = self.client.post(
            reverse(
                "accounts:prerequisite_delete",
                args=[self.relationship.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("accounts:prerequisites"),
        )

        self.assertTrue(
            SubjectPrerequisite.objects.filter(
                pk=self.relationship.pk
            ).exists()
        )

    def test_prerequisite_edit_view_preserves_dependency(self):

        self.create_impact()

        self.client.force_login(
            self.admin
        )

        response = self.client.post(
            reverse(
                "accounts:prerequisite_edit",
                args=[self.relationship.pk],
            ),
            {
                "prerequisite": self.subject_a.pk,
                "successor": self.subject_c.pk,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.relationship.refresh_from_db()

        self.assertEqual(
            self.relationship.successor_id,
            self.subject_b.pk,
        )

    def test_mapping_delete_view_preserves_dependency(self):

        self.create_impact()

        self.client.force_login(
            self.admin
        )

        response = self.client.post(
            reverse(
                "accounts:mapping_delete",
                args=[self.mapping.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("accounts:mappings"),
        )

        self.assertTrue(
            SubjectCompetency.objects.filter(
                pk=self.mapping.pk
            ).exists()
        )

    def test_mapping_edit_view_preserves_dependency(self):

        self.create_impact()

        self.client.force_login(
            self.admin
        )

        response = self.client.post(
            reverse(
                "accounts:mapping_edit",
                args=[self.mapping.pk],
            ),
            {
                "subject": self.subject_b.pk,
                "competency": self.competency.pk,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:mapping_edit",
                args=[self.mapping.pk],
            ),
        )

        self.mapping.refresh_from_db()

        self.assertEqual(
            self.mapping.subject_id,
            self.subject_a.pk,
        )

    def test_mapping_directory_marks_impact_as_protected(self):

        self.create_impact()

        self.client.force_login(
            self.admin
        )

        response = self.client.get(
            reverse("accounts:mappings"),
            {
                "program": str(self.program.pk),
                "status": "protected",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        records = list(
            response.context["page"].object_list
        )

        self.assertEqual(
            len(records),
            1,
        )

        self.assertEqual(
            records[0].pk,
            self.mapping.pk,
        )

        self.assertTrue(
            records[0].is_protected
        )

    def test_student_cannot_delete_impact(self):

        impact = self.create_impact()

        self.client.force_login(
            self.student
        )

        response = self.client.post(
            reverse(
                "accounts:impact_delete",
                args=[impact.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertTrue(
            CompetencyImpact.objects.filter(
                pk=impact.pk
            ).exists()
        )

    def test_student_cannot_edit_impact(self):

        impact = self.create_impact()

        self.client.force_login(
            self.student
        )

        data = self.valid_data()

        data["relevance"] = 1

        response = self.client.post(
            reverse(
                "accounts:impact_edit",
                args=[impact.pk],
            ),
            data,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        impact.refresh_from_db()

        self.assertEqual(
            impact.relevance,
            3,
        )

    def test_missing_impact_returns_404(self):

        self.client.force_login(
            self.admin
        )

        response = self.client.get(
            reverse(
                "accounts:impact_edit",
                args=[999999999],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )