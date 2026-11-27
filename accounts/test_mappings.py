
from django.test import TestCase
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

from .mapping_forms import MappingForm
from .models import CustomUser


class MappingTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.admin = CustomUser.objects.create_user(
            username="mapping_admin",
            email="mapping_admin@example.com",
            role=CustomUser.Role.ADMINISTRATOR,
        )

        cls.student = CustomUser.objects.create_user(
            username="mapping_student",
            email="mapping_student@example.com",
            role=CustomUser.Role.STUDENT,
        )

        cls.program = AcademicProgram.objects.create(
            code="MAP-TEST",
            name="Mapping Test Program",
        )

        cls.other_program = AcademicProgram.objects.create(
            code="MAP-OTHER",
            name="Other Mapping Program",
        )

        cls.subject_a = Subject.objects.create(
            program=cls.program,
            code="MAP-A",
            name="Mapping Subject A",
        )

        cls.subject_b = Subject.objects.create(
            program=cls.program,
            code="MAP-B",
            name="Mapping Subject B",
        )

        cls.subject_c = Subject.objects.create(
            program=cls.other_program,
            code="MAP-C",
            name="Mapping Subject C",
        )

        cls.competency_a = Competency.objects.create(
            code="MAP-COMP-A",
            name="Mapping Competency A",
            description="Demonstrate competency A.",
        )

        cls.competency_b = Competency.objects.create(
            code="MAP-COMP-B",
            name="Mapping Competency B",
            description="Demonstrate competency B.",
        )

        cls.competency_c = Competency.objects.create(
            code="MAP-COMP-C",
            name="Mapping Competency C",
            description="Demonstrate competency C.",
        )

        cls.mapping = SubjectCompetency.objects.create(
            subject=cls.subject_a,
            competency=cls.competency_a,
        )

        cls.protected = SubjectCompetency.objects.create(
            subject=cls.subject_b,
            competency=cls.competency_b,
        )

        cls.assessment = AssessmentSession.objects.create(
            user=cls.student,
            completed_at=timezone.now(),
        )

        cls.response = AssessmentResponse.objects.create(
            assessment=cls.assessment,
            subject_competency=cls.protected,
            self_rating=3,
        )

    def login_admin(self):

        self.client.force_login(self.admin)

    def valid_data(self):

        return {
            "subject": self.subject_a.pk,
            "competency": self.competency_c.pk,
        }

    def test_valid_mapping(self):

        form = MappingForm(
            data=self.valid_data()
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_duplicate_mapping(self):

        form = MappingForm(
            data={
                "subject": self.subject_a.pk,
                "competency": self.competency_a.pk,
            }
        )

        self.assertFalse(
            form.is_valid()
        )

    def test_missing_subject(self):

        data = self.valid_data()
        data["subject"] = ""

        form = MappingForm(data=data)

        self.assertFalse(form.is_valid())

        self.assertIn(
            "subject",
            form.errors,
        )

    def test_missing_competency(self):

        data = self.valid_data()
        data["competency"] = ""

        form = MappingForm(data=data)

        self.assertFalse(form.is_valid())

        self.assertIn(
            "competency",
            form.errors,
        )

    def test_invalid_subject(self):

        data = self.valid_data()
        data["subject"] = 999999999

        form = MappingForm(data=data)

        self.assertFalse(form.is_valid())

    def test_guest_access(self):

        response = self.client.get(
            reverse("accounts:mappings")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_student_access(self):

        self.client.force_login(self.student)

        response = self.client.get(
            reverse("accounts:mappings")
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_student_cannot_create(self):

        self.client.force_login(self.student)

        response = self.client.post(
            reverse("accounts:mapping_create"),
            self.valid_data(),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            SubjectCompetency.objects.filter(
                subject=self.subject_a,
                competency=self.competency_c,
            ).exists()
        )

    def test_admin_directory(self):

        self.login_admin()

        response = self.client.get(
            reverse("accounts:mappings")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["total_count"],
            SubjectCompetency.objects.count(),
        )

        self.assertContains(
            response,
            self.subject_a.code,
        )

    def test_admin_create(self):

        self.login_admin()

        response = self.client.post(
            reverse("accounts:mapping_create"),
            self.valid_data(),
        )

        self.assertRedirects(
            response,
            reverse("accounts:mappings"),
        )

        self.assertTrue(
            SubjectCompetency.objects.filter(
                subject=self.subject_a,
                competency=self.competency_c,
            ).exists()
        )

    def test_admin_edit(self):

        self.login_admin()

        response = self.client.post(
            reverse(
                "accounts:mapping_edit",
                args=[self.mapping.pk],
            ),
            self.valid_data(),
        )

        self.assertRedirects(
            response,
            reverse("accounts:mappings"),
        )

        self.mapping.refresh_from_db()

        self.assertEqual(
            self.mapping.competency_id,
            self.competency_c.pk,
        )

    def test_admin_delete(self):

        self.login_admin()

        url = reverse(
            "accounts:mapping_delete",
            args=[self.mapping.pk],
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            SubjectCompetency.objects.filter(
                pk=self.mapping.pk
            ).exists()
        )

        response = self.client.post(url)

        self.assertRedirects(
            response,
            reverse("accounts:mappings"),
        )

        self.assertFalse(
            SubjectCompetency.objects.filter(
                pk=self.mapping.pk
            ).exists()
        )

        self.assertTrue(
            Subject.objects.filter(
                pk=self.subject_a.pk
            ).exists()
        )

        self.assertTrue(
            Competency.objects.filter(
                pk=self.competency_a.pk
            ).exists()
        )

    def test_protected_mapping_edit(self):

        self.login_admin()

        url = reverse(
            "accounts:mapping_edit",
            args=[self.protected.pk],
        )

        response = self.client.post(
            url,
            self.valid_data(),
        )

        self.assertRedirects(
            response,
            url,
        )

        self.protected.refresh_from_db()

        self.assertEqual(
            self.protected.subject_id,
            self.subject_b.pk,
        )

        self.assertEqual(
            self.protected.competency_id,
            self.competency_b.pk,
        )

    def test_protected_mapping_delete(self):

        self.login_admin()

        response = self.client.post(
            reverse(
                "accounts:mapping_delete",
                args=[self.protected.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("accounts:mappings"),
        )

        self.assertTrue(
            SubjectCompetency.objects.filter(
                pk=self.protected.pk
            ).exists()
        )

        self.assertTrue(
            AssessmentResponse.objects.filter(
                pk=self.response.pk,
                subject_competency=self.protected,
            ).exists()
        )

    def test_search(self):

        self.login_admin()

        response = self.client.get(
            reverse("accounts:mappings"),
            {
                "q": self.competency_a.code,
            },
        )

        records = list(
            response.context["page"].object_list
        )

        self.assertEqual(
            records,
            [self.mapping],
        )

    def test_program_filter(self):

        self.login_admin()

        response = self.client.get(
            reverse("accounts:mappings"),
            {
                "program": self.program.pk,
            },
        )

        records = list(
            response.context["page"].object_list
        )

        self.assertIn(self.mapping, records)
        self.assertIn(self.protected, records)

        for item in records:

            self.assertEqual(
                item.subject.program_id,
                self.program.pk,
            )

    def test_subject_filter(self):

        self.login_admin()

        response = self.client.get(
            reverse("accounts:mappings"),
            {
                "subject": self.subject_a.pk,
            },
        )

        records = list(
            response.context["page"].object_list
        )

        self.assertEqual(
            records,
            [self.mapping],
        )

    def test_unmapped_subjects(self):

        self.login_admin()

        response = self.client.get(
            reverse("accounts:mappings"),
            {
                "program": self.other_program.pk,
            },
        )

        records = list(
            response.context["unmapped_subjects"]
        )

        self.assertIn(
            self.subject_c,
            records,
        )

        self.assertNotIn(
            self.subject_a,
            records,
        )
