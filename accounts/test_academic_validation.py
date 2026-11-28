
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from assessments.models import (
    AcademicProgram,
    Subject,
)

from .academic_forms import ProgramForm, SubjectForm


User = get_user_model()


class AcademicValidationTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.admin = User.objects.create_user(
            username="academic_validation_admin",
            email="academic-validation@example.test",
            role="administrator",
        )

        cls.bsit, _ = AcademicProgram.objects.get_or_create(
            code="BSIT",
            defaults={
                "name": (
                    "Bachelor of Science in "
                    "Information Technology"
                ),
            },
        )

        cls.other_program = AcademicProgram.objects.create(
            code="VAL-PROG",
            name="Validation Academic Program",
        )

        cls.prototype, _ = Subject.objects.get_or_create(
            program=cls.bsit,
            code="DB-FND",
            defaults={
                "name": "Database Foundations",
            },
        )

        cls.other_subject = Subject.objects.create(
            program=cls.bsit,
            code="VAL-SUB",
            name="Validation Subject",
        )

    def subject_data(self, subject, **overrides):

        data = {
            "program": subject.program_id,
            "code": subject.code,
            "name": subject.name,
            "year_level": subject.year_level or "",
            "semester": subject.semester or "",
            "units": (
                subject.units
                if subject.units is not None
                else ""
            ),
        }

        data.update(overrides)

        return data

    def test_protected_program_code_cannot_change(self):

        form = ProgramForm(
            data={
                "code": "BSIT-NEW",
                "name": self.bsit.name,
            },
            instance=self.bsit,
        )

        self.assertFalse(form.is_valid())

        self.assertEqual(
            form.errors.as_data()["code"][0].code,
            "protected_program_code",
        )

    def test_protected_program_name_can_change(self):

        form = ProgramForm(
            data={
                "code": "BSIT",
                "name": "Updated IT Program Name",
            },
            instance=self.bsit,
        )

        self.assertTrue(form.is_valid(), form.errors)

        form.save()

        self.bsit.refresh_from_db()

        self.assertEqual(
            self.bsit.name,
            "Updated IT Program Name",
        )

    def test_protected_subject_code_cannot_change(self):

        form = SubjectForm(
            data=self.subject_data(
                self.prototype,
                code="DB-NEW",
            ),
            instance=self.prototype,
        )

        self.assertFalse(form.is_valid())

        self.assertEqual(
            form.errors.as_data()["code"][0].code,
            "protected_subject_code",
        )

    def test_protected_subject_cannot_change_program(self):

        form = SubjectForm(
            data=self.subject_data(
                self.prototype,
                program=self.other_program.pk,
            ),
            instance=self.prototype,
        )

        self.assertFalse(form.is_valid())

        codes = [
            error.code
            for error in form.errors.as_data()["program"]
        ]

        self.assertIn(
            "protected_subject_program",
            codes,
        )

    def test_protected_subject_name_can_change(self):

        form = SubjectForm(
            data=self.subject_data(
                self.prototype,
                name="Updated Database Foundations",
            ),
            instance=self.prototype,
        )

        self.assertTrue(form.is_valid(), form.errors)

        form.save()

        self.prototype.refresh_from_db()

        self.assertEqual(
            self.prototype.name,
            "Updated Database Foundations",
        )

    def test_unrelated_program_code_can_change(self):

        form = ProgramForm(
            data={
                "code": "VAL-NEW",
                "name": self.other_program.name,
            },
            instance=self.other_program,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_unrelated_subject_code_can_change(self):

        form = SubjectForm(
            data=self.subject_data(
                self.other_subject,
                code="VAL-SUB-NEW",
            ),
            instance=self.other_subject,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_program_code_rejected(self):

        form = ProgramForm(
            data={
                "code": "bsit",
                "name": "Duplicate Program",
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)

    def test_duplicate_subject_code_rejected(self):

        form = SubjectForm(
            data=self.subject_data(
                self.other_subject,
                code="db-fnd",
            ),
            instance=self.other_subject,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)

    def test_negative_subject_units_rejected(self):

        form = SubjectForm(
            data=self.subject_data(
                self.other_subject,
                units=-1,
            ),
            instance=self.other_subject,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("units", form.errors)

    def test_invalid_year_level_rejected(self):

        form = SubjectForm(
            data=self.subject_data(
                self.other_subject,
                year_level=99,
            ),
            instance=self.other_subject,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("year_level", form.errors)

    def test_invalid_semester_rejected(self):

        form = SubjectForm(
            data=self.subject_data(
                self.other_subject,
                semester=99,
            ),
            instance=self.other_subject,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("semester", form.errors)

    def test_invalid_program_update_preserves_database(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "accounts:program_edit",
                args=[self.bsit.pk],
            ),
            {
                "code": "BSIT-CHANGED",
                "name": self.bsit.name,
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "code",
            response.context["form"].errors,
        )

        self.bsit.refresh_from_db()

        self.assertEqual(self.bsit.code, "BSIT")

    def test_invalid_subject_update_preserves_database(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "accounts:subject_edit",
                args=[self.prototype.pk],
            ),
            self.subject_data(
                self.prototype,
                code="DB-CHANGED",
            ),
        )

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "code",
            response.context["form"].errors,
        )

        self.prototype.refresh_from_db()

        self.assertEqual(
            self.prototype.code,
            "DB-FND",
        )
