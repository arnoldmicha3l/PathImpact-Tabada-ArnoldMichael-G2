from django import forms

from assessments.models import (
    CompetencyImpact,
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

    def clean(self):

        cleaned_data = super().clean()

        if self.instance.pk and self.has_changed():

            if CompetencyImpact.objects.filter(
                prerequisite_id=self.instance.pk
            ).exists():

                raise forms.ValidationError(
                    "This prerequisite relationship is "
                    "referenced by competency impacts "
                    "and cannot be modified."
                )

        return cleaned_data