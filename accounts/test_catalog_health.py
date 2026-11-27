
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from assessments.models import (
    AcademicProgram,
    Subject,
    Competency,
    SubjectCompetency,
    SubjectPrerequisite,
    CompetencyImpact,
)

from .catalog_services import build_catalog_health


class CatalogHealthTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        users = get_user_model().objects

        cls.admin = users.create_user(
            username="catalog_admin",
            email="catalog_admin@example.test",
            role="administrator",
        )

        cls.student = users.create_user(
            username="catalog_student",
            email="catalog_student@example.test",
            role="student",
        )

        cls.program = AcademicProgram.objects.create(
            code="HEALTH-TEST",
            name="Catalog Health Test",
        )

        cls.foundation = Subject.objects.create(
            program=cls.program,
            code="CH-FND",
            name="Foundation",
        )

        cls.successor = Subject.objects.create(
            program=cls.program,
            code="CH-ADV",
            name="Advanced Subject",
        )

        cls.competency = Competency.objects.create(
            code="CH-SQL",
            name="SQL Queries",
            description="SQL preparation.",
        )

        cls.mapping = SubjectCompetency.objects.create(
            subject=cls.foundation,
            competency=cls.competency,
        )

        cls.relationship = SubjectPrerequisite.objects.create(
            prerequisite=cls.foundation,
            successor=cls.successor,
        )

    # =====================================================
    # CATALOG STATISTICS
    # =====================================================

    def test_actual_subject_count(self):

        health = build_catalog_health()

        self.assertEqual(
            health["subject_count"],
            Subject.objects.count(),
        )

    def test_actual_program_count(self):

        health = build_catalog_health()

        self.assertEqual(
            health["program_count"],
            AcademicProgram.objects.count(),
        )

    def test_unmapped_subject_detected(self):

        health = build_catalog_health()

        self.assertGreaterEqual(
            health["unmapped_subject_count"],
            1,
        )

    def test_mapping_reduces_configuration_gap(self):

        before = build_catalog_health()

        SubjectCompetency.objects.create(
            subject=self.successor,
            competency=self.competency,
        )

        after = build_catalog_health()

        self.assertEqual(
            after["unmapped_subject_count"],
            before["unmapped_subject_count"] - 1,
        )

    def test_mapping_coverage_calculation(self):

        health = build_catalog_health()

        expected = round(
            health["mapped_subject_count"]
            / health["subject_count"] * 100,
            1,
        )

        self.assertEqual(
            health["mapping_coverage"],
            expected,
        )

    def test_unused_competency_detected(self):

        before = build_catalog_health()

        Competency.objects.create(
            code="CH-UNUSED",
            name="Unused Competency",
            description="Test competency.",
        )

        after = build_catalog_health()

        self.assertEqual(
            after["unused_competency_count"],
            before["unused_competency_count"] + 1,
        )

    # =====================================================
    # PREREQUISITES AND COMPETENCY IMPACTS
    # =====================================================

    def test_uncovered_prerequisite_detected(self):

        health = build_catalog_health()

        self.assertGreaterEqual(
            health["uncovered_prerequisite_count"],
            1,
        )

    def test_impact_reduces_uncovered_count(self):

        before = build_catalog_health()

        CompetencyImpact.objects.create(
            prerequisite=self.relationship,
            subject_competency=self.mapping,
            relevance=3,
        )

        after = build_catalog_health()

        self.assertEqual(
            after["uncovered_prerequisite_count"],
            before["uncovered_prerequisite_count"] - 1,
        )

        self.assertEqual(
            after["impact_count"],
            before["impact_count"] + 1,
        )

    # =====================================================
    # ACADEMIC DATA INTEGRITY
    # =====================================================

    def test_invalid_cross_program_relationship(self):

        before = build_catalog_health()

        other_program = AcademicProgram.objects.create(
            code="HEALTH-OTHER",
            name="Other Test Program",
        )

        other_subject = Subject.objects.create(
            program=other_program,
            code="CH-OTHER",
            name="Other Subject",
        )

        SubjectPrerequisite.objects.create(
            prerequisite=self.foundation,
            successor=other_subject,
        )

        after = build_catalog_health()

        self.assertEqual(
            after["invalid_prerequisite_count"],
            before["invalid_prerequisite_count"] + 1,
        )

    def test_invalid_impact_detected(self):

        before = build_catalog_health()

        incorrect_mapping = SubjectCompetency.objects.create(
            subject=self.successor,
            competency=self.competency,
        )

        CompetencyImpact.objects.create(
            prerequisite=self.relationship,
            subject_competency=incorrect_mapping,
            relevance=2,
        )

        after = build_catalog_health()

        self.assertEqual(
            after["invalid_impact_count"],
            before["invalid_impact_count"] + 1,
        )

    # =====================================================
    # DATA SAFETY
    # =====================================================

    def test_catalog_service_is_read_only(self):

        models = [
            AcademicProgram,
            Subject,
            Competency,
            SubjectCompetency,
            SubjectPrerequisite,
            CompetencyImpact,
        ]

        before = [
            list(model.objects.order_by("pk").values())
            for model in models
        ]

        build_catalog_health()

        after = [
            list(model.objects.order_by("pk").values())
            for model in models
        ]

        self.assertEqual(before, after)

    # =====================================================
    # ADMINISTRATOR DASHBOARD INTEGRATION
    # =====================================================

    def test_administrator_dashboard_integration(self):

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("accounts:administrator_dashboard")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "catalog_health",
            response.context,
        )

        self.assertContains(
            response,
            "Academic Catalog Health",
        )

    # =====================================================
    # ACCESS CONTROL
    # =====================================================

    def test_student_cannot_access_admin_dashboard(self):

        self.client.force_login(self.student)

        response = self.client.get(
            reverse("accounts:administrator_dashboard")
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_guest_cannot_access_admin_dashboard(self):

        response = self.client.get(
            reverse("accounts:administrator_dashboard")
        )

        self.assertEqual(
            response.status_code,
            302,
        )
