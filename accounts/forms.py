
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser


class RegistrationForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        max_length=254,
        error_messages={
            "required": "Enter your email address.",
            "invalid": "Enter a valid email address.",
            "max_length": "Email must not exceed 254 characters.",
        },
    )

    class Meta(UserCreationForm.Meta):

        model = CustomUser

        fields = (
            "username",
            "email",
        )

    def clean_username(self):

        username = self.cleaned_data["username"]

        if CustomUser.objects.filter(
            username__iexact=username
        ).exists():

            raise forms.ValidationError(
                "This username is already taken.",
                code="duplicate_username",
            )

        return username

    def clean_email(self):

        email = self.cleaned_data["email"].strip().lower()

        if CustomUser.objects.filter(
            email__iexact=email
        ).exists():

            raise forms.ValidationError(
                "This email is already registered.",
                code="duplicate_email",
            )

        return email

    def save(self, commit=True):

        user = super().save(commit=False)

        user.role = CustomUser.Role.STUDENT
        user.is_staff = False
        user.is_superuser = False

        if commit:

            user.save()
            self.save_m2m()

        return user


class ProfileForm(forms.ModelForm):

    email = forms.EmailField(
        required=True,
        max_length=254,
        error_messages={
            "required": "Enter your email address.",
            "invalid": "Enter a valid email address.",
            "max_length": "Email must not exceed 254 characters.",
        },
    )

    class Meta:

        model = CustomUser

        fields = (
            "first_name",
            "last_name",
            "email",
        )

    def clean_first_name(self):

        return self.cleaned_data["first_name"].strip()

    def clean_last_name(self):

        return self.cleaned_data["last_name"].strip()

    def clean_email(self):

        email = self.cleaned_data["email"].strip().lower()

        other_users = CustomUser.objects.exclude(
            pk=self.instance.pk
        )

        if other_users.filter(
            email__iexact=email
        ).exists():

            raise forms.ValidationError(
                "This email is already registered.",
                code="duplicate_email",
            )

        return email
