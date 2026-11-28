
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import RegistrationForm, ProfileForm


User = get_user_model()


class AccountValidationTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.existing = User.objects.create_user(
            username="validation_existing",
            email="existing@example.test",
            password="Validation-Test!9274",
        )

    def registration_data(self, **overrides):

        data = {
            "username": "validation_new",
            "email": "new@example.test",
            "password1": "Validation-Test!9274",
            "password2": "Validation-Test!9274",
        }

        data.update(overrides)

        return data

    def test_valid_registration(self):

        form = RegistrationForm(
            data=self.registration_data()
        )

        self.assertTrue(form.is_valid(), form.errors)

        user = form.save()

        self.assertEqual(user.role, "student")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.assertTrue(
            user.check_password("Validation-Test!9274")
        )

    def test_required_registration_email(self):

        form = RegistrationForm(
            data=self.registration_data(email="")
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_invalid_registration_email(self):

        form = RegistrationForm(
            data=self.registration_data(
                email="invalid-email"
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_registration_email_length(self):

        form = RegistrationForm(
            data=self.registration_data(
                email=(
                    "a" * 64
                    + "@"
                    + ".".join(["b" * 63] * 3)
                    + ".com"
                )
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_duplicate_username_case_insensitive(self):

        form = RegistrationForm(
            data=self.registration_data(
                username=self.existing.username.upper()
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_duplicate_email_case_insensitive(self):

        form = RegistrationForm(
            data=self.registration_data(
                email=self.existing.email.upper()
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_email_normalization(self):

        form = RegistrationForm(
            data=self.registration_data(
                email="  NEW@EXAMPLE.TEST  "
            )
        )

        self.assertTrue(form.is_valid(), form.errors)

        self.assertEqual(
            form.cleaned_data["email"],
            "new@example.test",
        )

    def test_password_mismatch(self):

        form = RegistrationForm(
            data=self.registration_data(
                password2="Different-Test!9274"
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_weak_password_rejected(self):

        form = RegistrationForm(
            data=self.registration_data(
                password1="123",
                password2="123",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_invalid_registration_creates_no_user(self):

        before = User.objects.count()

        response = self.client.post(
            reverse("accounts:register"),
            self.registration_data(
                email="invalid-email"
            ),
        )

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "email",
            response.context["form"].errors,
        )

        self.assertEqual(
            User.objects.count(),
            before,
        )

    def test_valid_registration_redirects(self):

        response = self.client.post(
            reverse("accounts:register"),
            self.registration_data(),
        )

        self.assertRedirects(
            response,
            reverse("accounts:login"),
        )

        self.assertTrue(
            User.objects.filter(
                username="validation_new"
            ).exists()
        )

    def test_profile_accepts_own_email(self):

        form = ProfileForm(
            data={
                "first_name": "Student",
                "last_name": "Example",
                "email": self.existing.email,
            },
            instance=self.existing,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_profile_normalizes_names(self):

        form = ProfileForm(
            data={
                "first_name": "  Student  ",
                "last_name": "  Example  ",
                "email": self.existing.email,
            },
            instance=self.existing,
        )

        self.assertTrue(form.is_valid(), form.errors)

        self.assertEqual(
            form.cleaned_data["first_name"],
            "Student",
        )

        self.assertEqual(
            form.cleaned_data["last_name"],
            "Example",
        )

    def test_profile_rejects_invalid_email(self):

        form = ProfileForm(
            data={
                "first_name": "Student",
                "last_name": "Example",
                "email": "invalid-email",
            },
            instance=self.existing,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_invalid_profile_preserves_database(self):

        self.client.force_login(self.existing)

        original_name = self.existing.first_name
        original_email = self.existing.email

        response = self.client.post(
            reverse("accounts:edit_profile"),
            {
                "first_name": "Changed",
                "last_name": "Example",
                "email": "invalid-email",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.existing.refresh_from_db()

        self.assertEqual(
            self.existing.first_name,
            original_name,
        )

        self.assertEqual(
            self.existing.email,
            original_email,
        )
