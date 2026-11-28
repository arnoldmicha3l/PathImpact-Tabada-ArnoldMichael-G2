
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from assessments.models import (
    AcademicProgram,
    Subject,
    SubjectPrerequisite,
)


User = get_user_model()


class AccountDatabaseIntegrityTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.existing = User.objects.create_user(
            username="integrity_existing",
            email="integrity@example.test",
            role="student",
        )

    def test_case_insensitive_username_constraint(self):

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                User.objects.create_user(
                    username="INTEGRITY_EXISTING",
                    email="different@example.test",
                    role="student",
                )

    def test_case_insensitive_email_constraint(self):

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                User.objects.create_user(
                    username="integrity_new",
                    email="INTEGRITY@example.test",
                    role="student",
                )

    def test_email_whitespace_constraint(self):

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                User.objects.create_user(
                    username="integrity_whitespace",
                    email=" integrity@example.test ",
                    role="student",
                )

    def test_invalid_role_constraint(self):

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                User.objects.create(
                    username="integrity_invalid_role",
                    email="invalid-role@example.test",
                    role="unknown",
                )

    def test_invalid_role_update_preserves_account(self):

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                User.objects.filter(
                    pk=self.existing.pk
                ).update(
                    role="unknown"
                )

        self.existing.refresh_from_db()

        self.assertEqual(
            self.existing.role,
            "student",
        )

    def test_duplicate_email_update_preserves_account(self):

        other = User.objects.create_user(
            username="integrity_other",
            email="other-integrity@example.test",
            role="student",
        )

        with self.assertRaises(IntegrityError):

            with transaction.atomic():

                User.objects.filter(
                    pk=other.pk
                ).update(
                    email="INTEGRITY@example.test"
                )

        other.refresh_from_db()

        self.assertEqual(
            other.email,
            "other-integrity@example.test",
        )

    def test_distinct_accounts_allowed(self):

        user = User.objects.create_user(
            username="integrity_distinct",
            email="distinct@example.test",
            role="student",
        )

        self.assertTrue(
            User.objects.filter(
                pk=user.pk
            ).exists()
        )

    def test_multiple_blank_emails_allowed(self):

        first = User.objects.create_user(
            username="integrity_blank_one",
            email="",
        )

        second = User.objects.create_user(
            username="integrity_blank_two",
            email="",
        )

        self.assertNotEqual(
            first.pk,
            second.pk,
        )

    def test_existing_email_can_be_updated_in_case(self):

        User.objects.filter(
            pk=self.existing.pk
        ).update(
            email="INTEGRITY@example.test"
        )

        self.existing.refresh_from_db()

        self.assertEqual(
            self.existing.email,
            "INTEGRITY@example.test",
        )


class AcademicDatabaseIntegrityTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.admin = User.objects.create_user(
            username="integrity_admin",
            email="integrity-admin@example.test",
            role="administrator",
        )

        cls.student = User.objects.create_user(
            username="integrity_student",
            email="integrity-student@example.test",
            role="student",
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

        cls.prototype, _ = Subject.objects.get_or_create(
            program=cls.bsit,
            code="DB-FND",
            defaults={
                "name": "Database Foundations",
            },
        )

        cls.other_program = AcademicProgram.objects.create(
            code="INT-PROG",
            name="Integrity Test Program",
        )

        cls.other_subject = Subject.objects.create(
            program=cls.other_program,
            code="INT-SUB",
            name="Integrity Test Subject",
        )

    def test_protected_program_cannot_be_deleted(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "accounts:program_delete",
                args=[self.bsit.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("accounts:programs"),
        )

        self.assertTrue(
            AcademicProgram.objects.filter(
                pk=self.bsit.pk
            ).exists()
        )

    def test_protected_subject_cannot_be_deleted(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "accounts:subject_delete",
                args=[self.prototype.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("accounts:subjects"),
        )

        self.assertTrue(
            Subject.objects.filter(
                pk=self.prototype.pk
            ).exists()
        )

    def test_unreferenced_subject_can_be_deleted(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "accounts:subject_delete",
                args=[self.other_subject.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("accounts:subjects"),
        )

        self.assertFalse(
            Subject.objects.filter(
                pk=self.other_subject.pk
            ).exists()
        )

    def test_unreferenced_program_can_be_deleted(self):

        self.client.force_login(self.admin)

        program = AcademicProgram.objects.create(
            code="INT-EMPTY",
            name="Empty Integrity Program",
        )

        response = self.client.post(
            reverse(
                "accounts:program_delete",
                args=[program.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("accounts:programs"),
        )

        self.assertFalse(
            AcademicProgram.objects.filter(
                pk=program.pk
            ).exists()
        )

    def test_referenced_program_cannot_be_deleted(self):

        self.client.force_login(self.admin)

        self.client.post(
            reverse(
                "accounts:program_delete",
                args=[self.other_program.pk],
            )
        )

        self.assertTrue(
            AcademicProgram.objects.filter(
                pk=self.other_program.pk
            ).exists()
        )

    def test_prerequisite_subject_cannot_be_deleted(self):

        self.client.force_login(self.admin)

        successor = Subject.objects.create(
            program=self.other_program,
            code="INT-NEXT",
            name="Integrity Successor Subject",
        )

        relationship = SubjectPrerequisite.objects.create(
            prerequisite=self.other_subject,
            successor=successor,
        )

        self.client.post(
            reverse(
                "accounts:subject_delete",
                args=[self.other_subject.pk],
            )
        )

        self.assertTrue(
            Subject.objects.filter(
                pk=self.other_subject.pk
            ).exists()
        )

        self.assertTrue(
            SubjectPrerequisite.objects.filter(
                pk=relationship.pk
            ).exists()
        )

    def test_delete_confirmation_preserves_subject(self):

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse(
                "accounts:subject_delete",
                args=[self.other_subject.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            Subject.objects.filter(
                pk=self.other_subject.pk
            ).exists()
        )

    def test_student_cannot_delete_subject(self):

        self.client.force_login(self.student)

        response = self.client.post(
            reverse(
                "accounts:subject_delete",
                args=[self.other_subject.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertTrue(
            Subject.objects.filter(
                pk=self.other_subject.pk
            ).exists()
        )

    def test_guest_cannot_delete_program(self):

        response = self.client.post(
            reverse(
                "accounts:program_delete",
                args=[self.other_program.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            AcademicProgram.objects.filter(
                pk=self.other_program.pk
            ).exists()
        )

    def test_missing_subject_returns_404(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "accounts:subject_delete",
                args=[999999999],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_valid_program_update(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "accounts:program_edit",
                args=[self.other_program.pk],
            ),
            {
                "code": "INT-UPDATED",
                "name": "Updated Integrity Program",
            },
        )

        self.assertRedirects(
            response,
            reverse("accounts:programs"),
        )

        self.other_program.refresh_from_db()

        self.assertEqual(
            self.other_program.code,
            "INT-UPDATED",
        )

    def test_invalid_program_update_preserves_record(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "accounts:program_edit",
                args=[self.other_program.pk],
            ),
            {
                "code": "BSIT",
                "name": "Invalid Integrity Program",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "code",
            response.context["form"].errors,
        )

        self.other_program.refresh_from_db()

        self.assertEqual(
            self.other_program.code,
            "INT-PROG",
        )

        self.assertEqual(
            self.other_program.name,
            "Integrity Test Program",
        )
