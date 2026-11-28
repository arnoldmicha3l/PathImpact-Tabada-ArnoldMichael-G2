
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from assessments.models import (
    AcademicProgram,
    Subject,
    SubjectPrerequisite,
)

from .prerequisite_forms import PrerequisiteForm


class PrerequisiteTests(TestCase):

    def setUp(self):

        p = AcademicProgram.objects.create(
            code="TEST",
            name="Test program",
        )

        q = AcademicProgram.objects.create(
            code="OTHER",
            name="Other program",
        )

        self.a, self.b, self.c = [
            Subject.objects.create(
                program=p,
                code=x,
                name=x,
            )
            for x in "ABC"
        ]

        self.d = Subject.objects.create(
            program=q,
            code="D",
            name="D",
        )

        User = get_user_model()

        self.admin = User.objects.create_user(
            username="test_admin",
            role="administrator",
        )

        self.student = User.objects.create_user(
            username="test_student",
            role="student",
        )

    def form(self, a, b):

        return PrerequisiteForm(
            {
                "prerequisite": a.pk,
                "successor": b.pk,
            }
        )

    def test_valid(self):

        self.assertTrue(
            self.form(self.a, self.b).is_valid()
        )

    def test_self(self):

        self.assertFalse(
            self.form(self.a, self.a).is_valid()
        )

    def test_duplicate(self):

        SubjectPrerequisite.objects.create(
            prerequisite=self.a,
            successor=self.b,
        )

        self.assertFalse(
            self.form(self.a, self.b).is_valid()
        )

    def test_cycle(self):

        SubjectPrerequisite.objects.create(
            prerequisite=self.a,
            successor=self.b,
        )

        SubjectPrerequisite.objects.create(
            prerequisite=self.b,
            successor=self.c,
        )

        self.assertFalse(
            self.form(self.c, self.a).is_valid()
        )

    def test_cross_program(self):

        self.assertFalse(
            self.form(self.a, self.d).is_valid()
        )

    def test_guest(self):

        response = self.client.get(
            reverse("accounts:prerequisites")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_student(self):

        self.client.force_login(self.student)

        response = self.client.post(
            reverse("accounts:prerequisite_create"),
            {
                "prerequisite": self.a.pk,
                "successor": self.b.pk,
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_admin_create_delete(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("accounts:prerequisite_create"),
            {
                "prerequisite": self.a.pk,
                "successor": self.b.pk,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        record = SubjectPrerequisite.objects.get(
            prerequisite=self.a,
            successor=self.b,
        )

        url = reverse(
            "accounts:prerequisite_delete",
            args=[record.pk],
        )

        self.assertEqual(
            self.client.get(url).status_code,
            200,
        )

        self.assertTrue(
            SubjectPrerequisite.objects.filter(
                pk=record.pk
            ).exists()
        )

        self.assertEqual(
            self.client.post(url).status_code,
            302,
        )

        self.assertFalse(
            SubjectPrerequisite.objects.filter(
                pk=record.pk
            ).exists()
        )
