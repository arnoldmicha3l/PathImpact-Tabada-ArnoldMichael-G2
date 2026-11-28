
from django.test import TestCase
from django.urls import reverse

from assessments.models import (
    AcademicProgram,
    Competency,
    Subject,
    SubjectCompetency,
)

from .competency_forms import CompetencyForm
from .models import CustomUser


class CompetencyTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.admin = CustomUser.objects.create_user(
            username="competency_admin",
            email="competency_admin@example.com",
            role=CustomUser.Role.ADMINISTRATOR,
        )

        cls.student = CustomUser.objects.create_user(
            username="competency_student",
            email="competency_student@example.com",
            role=CustomUser.Role.STUDENT,
        )

        cls.program = AcademicProgram.objects.create(
            code="TEST-CM",
            name="Competency Test Program",
        )

        cls.subject = Subject.objects.create(
            program=cls.program,
            code="TEST-SUB",
            name="Test Subject",
        )

        cls.competency = Competency.objects.create(
            code="TEST-CM-01",
            name="Test competency",
            description="Demonstrate a test skill.",
        )

        cls.mapped_competency = Competency.objects.create(
            code="TEST-CM-02",
            name="Mapped test competency",
            description="Demonstrate a mapped skill.",
        )

        SubjectCompetency.objects.create(
            subject=cls.subject,
            competency=cls.mapped_competency,
        )

    def valid_data(self):

        return {
            "code": "TEST-CM-03",
            "name": "New competency",
            "description": "Demonstrate a new skill.",
        }

    def login_admin(self):

        self.client.force_login(
            self.admin
        )

    def test_valid_form(self):

        form = CompetencyForm(
            data=self.valid_data()
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_duplicate_code(self):

        data = self.valid_data()

        data["code"] = self.competency.code.lower()

        form = CompetencyForm(
            data=data
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "code",
            form.errors,
        )

    def test_empty_name(self):

        data = self.valid_data()
        data["name"] = "   "

        form = CompetencyForm(
            data=data
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "name",
            form.errors,
        )

    def test_empty_description(self):

        data = self.valid_data()
        data["description"] = "   "

        form = CompetencyForm(
            data=data
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "description",
            form.errors,
        )

    def test_guest_access(self):

        response = self.client.get(
            reverse("accounts:competencies")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_student_access(self):

        self.client.force_login(
            self.student
        )

        response = self.client.get(
            reverse("accounts:competencies")
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_student_cannot_create(self):

        self.client.force_login(
            self.student
        )

        response = self.client.post(
            reverse("accounts:competency_create"),
            self.valid_data(),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            Competency.objects.filter(
                code="TEST-CM-03"
            ).exists()
        )

    def test_admin_directory(self):

        self.login_admin()

        response = self.client.get(
            reverse("accounts:competencies")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            self.competency.code,
        )

        self.assertEqual(
            response.context["total_count"],
            Competency.objects.count(),
        )

    def test_admin_create(self):

        self.login_admin()

        response = self.client.post(
            reverse("accounts:competency_create"),
            self.valid_data(),
        )

        self.assertRedirects(
            response,
            reverse("accounts:competencies"),
        )

        self.assertTrue(
            Competency.objects.filter(
                code="TEST-CM-03"
            ).exists()
        )

    def test_admin_edit(self):

        self.login_admin()

        response = self.client.post(
            reverse(
                "accounts:competency_edit",
                args=[self.competency.pk],
            ),
            {
                "code": self.competency.code,
                "name": "Updated competency",
                "description": "Updated definition.",
            },
        )

        self.assertRedirects(
            response,
            reverse("accounts:competencies"),
        )

        self.competency.refresh_from_db()

        self.assertEqual(
            self.competency.name,
            "Updated competency",
        )

    def test_admin_delete(self):

        self.login_admin()

        url = reverse(
            "accounts:competency_delete",
            args=[self.competency.pk],
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            Competency.objects.filter(
                pk=self.competency.pk
            ).exists()
        )

        response = self.client.post(url)

        self.assertRedirects(
            response,
            reverse("accounts:competencies"),
        )

        self.assertFalse(
            Competency.objects.filter(
                pk=self.competency.pk
            ).exists()
        )

    def test_mapped_competency_cannot_be_deleted(self):

        self.login_admin()

        response = self.client.post(
            reverse(
                "accounts:competency_delete",
                args=[self.mapped_competency.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("accounts:competencies"),
        )

        self.assertTrue(
            Competency.objects.filter(
                pk=self.mapped_competency.pk
            ).exists()
        )

    def test_mapped_competency_cannot_be_edited(self):

        self.login_admin()

        original_name = self.mapped_competency.name

        response = self.client.post(
            reverse(
                "accounts:competency_edit",
                args=[self.mapped_competency.pk],
            ),
            {
                "code": self.mapped_competency.code,
                "name": "Unauthorized definition change",
                "description": "Changed description.",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.context["form"].is_valid()
        )

        self.mapped_competency.refresh_from_db()

        self.assertEqual(
            self.mapped_competency.name,
            original_name,
        )

    def test_search(self):

        self.login_admin()

        response = self.client.get(
            reverse("accounts:competencies"),
            {
                "q": self.competency.code,
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
            self.competency.pk,
        )

    def test_mapping_filter(self):

        self.login_admin()

        response = self.client.get(
            reverse("accounts:competencies"),
            {
                "status": "mapped",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        records = list(
            response.context["page"].object_list
        )

        self.assertIn(
            self.mapped_competency,
            records,
        )

        self.assertNotIn(
            self.competency,
            records,
        )
