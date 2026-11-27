
from django import forms

from assessments.models import AcademicProgram, Subject


class ProgramForm(forms.ModelForm):

    class Meta:

        model = AcademicProgram

        fields = [
            "code",
            "name",
        ]

        labels = {
            "code": "Program code",
            "name": "Program name",
        }

        widgets = {
            "code": forms.TextInput(
                attrs={"placeholder": "e.g. BSIT"}
            ),
            "name": forms.TextInput(
                attrs={
                    "placeholder":
                    "Bachelor of Science in Information Technology"
                }
            ),
        }

    def clean_code(self):

        code = self.cleaned_data["code"].strip().upper()

        records = AcademicProgram.objects.exclude(
            pk=self.instance.pk
        )

        if records.filter(code__iexact=code).exists():
            raise forms.ValidationError(
                "This program code already exists."
            )

        return code

    def clean_name(self):

        name = self.cleaned_data["name"].strip()

        records = AcademicProgram.objects.exclude(
            pk=self.instance.pk
        )

        if records.filter(name__iexact=name).exists():
            raise forms.ValidationError(
                "This program name already exists."
            )

        return name


class SubjectForm(forms.ModelForm):

    class Meta:

        model = Subject

        fields = [
            "program",
            "code",
            "name",
            "year_level",
            "semester",
            "units",
        ]

        labels = {
            "program": "Academic program",
            "code": "Subject code",
            "name": "Subject name",
            "year_level": "Year level",
            "semester": "Semester",
            "units": "Academic units",
        }

        widgets = {
            "code": forms.TextInput(
                attrs={"placeholder": "e.g. CSIT226"}
            ),
            "name": forms.TextInput(
                attrs={"placeholder": "e.g. Information Management 1"}
            ),
            "units": forms.NumberInput(
                attrs={"min": 0, "placeholder": "e.g. 3"}
            ),
        }

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean(self):

        cleaned = super().clean()

        program = cleaned.get("program")
        code = cleaned.get("code")

        if program and code:

            duplicate = Subject.objects.filter(
                program=program,
                code__iexact=code,
            ).exclude(pk=self.instance.pk)

            if duplicate.exists():
                self.add_error(
                    "code",
                    "This subject code already exists in the program."
                )

        return cleaned
