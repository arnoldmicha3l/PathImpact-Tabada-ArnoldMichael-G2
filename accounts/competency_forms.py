
from django import forms

from assessments.models import Competency, SubjectCompetency


class CompetencyForm(forms.ModelForm):

    class Meta:
        model = Competency

        fields = [
            "code",
            "name",
            "description",
        ]

        labels = {
            "code": "Competency code",
            "name": "Competency name",
            "description": "Description",
        }

        widgets = {
            "code": forms.TextInput(
                attrs={
                    "placeholder": "e.g. DB-SQL-01",
                    "autocomplete": "off",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Enter competency name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": (
                        "Describe the knowledge or skill "
                        "the student should demonstrate."
                    ),
                }
            ),
        }

        help_texts = {
            "code": "Use a unique and identifiable competency code.",
            "description": (
                "Provide a clear and measurable competency definition."
            ),
        }

    def clean_code(self):

        code = self.cleaned_data["code"].strip().upper()

        records = Competency.objects.filter(
            code__iexact=code
        )

        if self.instance.pk:
            records = records.exclude(
                pk=self.instance.pk
            )

        if records.exists():
            raise forms.ValidationError(
                "A competency with this code already exists."
            )

        return code

    def clean_name(self):

        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "Enter a competency name."
            )

        return name

    def clean_description(self):

        description = self.cleaned_data[
            "description"
        ].strip()

        if not description:
            raise forms.ValidationError(
                "Enter a competency description."
            )

        return description

    def clean(self):

        cleaned_data = super().clean()

        if self.instance.pk and self.has_changed():

            if SubjectCompetency.objects.filter(
                competency=self.instance
            ).exists():

                raise forms.ValidationError(
                    "This competency is mapped to a subject. "
                    "Its definition cannot be modified while "
                    "the mapping exists."
                )

        return cleaned_data
