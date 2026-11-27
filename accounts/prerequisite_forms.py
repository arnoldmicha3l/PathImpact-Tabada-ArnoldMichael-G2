
from django import forms

from assessments.models import (
    Subject,
    SubjectPrerequisite,
)


class SubjectChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return (
            f"{obj.program.code} | "
            f"{obj.code} - {obj.name}"
        )


class PrerequisiteForm(forms.ModelForm):

    prerequisite = SubjectChoiceField(
        queryset=Subject.objects.select_related(
            "program"
        ),
        help_text="Subject that must be taken first.",
    )

    successor = SubjectChoiceField(
        queryset=Subject.objects.select_related(
            "program"
        ),
        help_text="Subject that depends on the prerequisite.",
    )

    class Meta:
        model = SubjectPrerequisite

        fields = [
            "prerequisite",
            "successor",
        ]
