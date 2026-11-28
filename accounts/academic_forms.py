
from django import forms

from assessments.models import (
    AcademicProgram,
    Subject,
    SubjectPrerequisite,
)


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
                    "placeholder": (
                        "Bachelor of Science in "
                        "Information Technology"
                    )
                }
            ),
        }

    def clean_code(self):

        code = self.cleaned_data["code"].strip().upper()

        if self.instance.pk:

            original_code = (
                AcademicProgram.objects
                .filter(pk=self.instance.pk)
                .values_list("code", flat=True)
                .first()
            )

            if original_code == "BSIT" and code != "BSIT":

                raise forms.ValidationError(
                    "The BSIT program code is required "
                    "by the current self-assessment "
                    "configuration and cannot be changed.",
                    code="protected_program_code",
                )

        records = AcademicProgram.objects.exclude(
            pk=self.instance.pk
        )

        if records.filter(code__iexact=code).exists():

            raise forms.ValidationError(
                "This program code already exists.",
                code="duplicate_program_code",
            )

        return code

    def clean_name(self):

        name = self.cleaned_data["name"].strip()

        records = AcademicProgram.objects.exclude(
            pk=self.instance.pk
        )

        if records.filter(name__iexact=name).exists():

            raise forms.ValidationError(
                "This program name already exists.",
                code="duplicate_program_name",
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
                attrs={
                    "placeholder": (
                        "e.g. Information Management 1"
                    )
                }
            ),
            "units": forms.NumberInput(
                attrs={
                    "min": 0,
                    "placeholder": "e.g. 3",
                }
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

        original = None

        if self.instance.pk:

            original = (
                Subject.objects.select_related("program")
                .filter(pk=self.instance.pk)
                .first()
            )

        if original is not None:

            is_protected_subject = (
                original.program.code == "BSIT"
                and original.code == "DB-FND"
            )

            if is_protected_subject:

                if code and code != "DB-FND":

                    self.add_error(
                        "code",
                        forms.ValidationError(
                            "This subject code is required "
                            "by the current self-assessment "
                            "configuration and cannot be changed.",
                            code="protected_subject_code",
                        ),
                    )

                if (
                    program
                    and program.pk != original.program_id
                ):

                    self.add_error(
                        "program",
                        forms.ValidationError(
                            "The current self-assessment "
                            "subject cannot be moved "
                            "to another academic program.",
                            code="protected_subject_program",
                        ),
                    )

            if (
                program
                and program.pk != original.program_id
            ):

                has_prerequisites = (
                    SubjectPrerequisite.objects.filter(
                        prerequisite_id=original.pk
                    ).exists()
                    or SubjectPrerequisite.objects.filter(
                        successor_id=original.pk
                    ).exists()
                )

                if has_prerequisites:

                    self.add_error(
                        "program",
                        "Remove prerequisite relationships "
                        "before changing the program.",
                    )

        if program and code:

            duplicate = Subject.objects.filter(
                program=program,
                code__iexact=code,
            ).exclude(pk=self.instance.pk)

            if duplicate.exists():

                self.add_error(
                    "code",
                    forms.ValidationError(
                        "This subject code already exists "
                        "in the program.",
                        code="duplicate_subject_code",
                    ),
                )

        return cleaned
