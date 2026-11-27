
from django import forms

from assessments.models import (
    Subject,
    Competency,
    SubjectCompetency,
    AssessmentResponse,
)


class SubjectChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return (
            f"{obj.program.code} | "
            f"{obj.code} - {obj.name}"
        )


class CompetencyChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return f"{obj.code} - {obj.name}"


class MappingForm(forms.ModelForm):

    subject = SubjectChoiceField(
        queryset=Subject.objects.select_related(
            "program"
        ).order_by(
            "program__code",
            "code",
        ),
        empty_label="Select an academic subject",
        help_text="Choose the subject that uses this competency.",
    )

    competency = CompetencyChoiceField(
        queryset=Competency.objects.order_by("code"),
        empty_label="Select a competency",
        help_text="Choose an existing competency definition.",
    )

    class Meta:
        model = SubjectCompetency

        fields = [
            "subject",
            "competency",
        ]

    def clean(self):

        cleaned_data = super().clean()

        subject = cleaned_data.get("subject")
        competency = cleaned_data.get("competency")

        if self.instance.pk and self.has_changed():

            if AssessmentResponse.objects.filter(
                subject_competency_id=self.instance.pk
            ).exists():

                raise forms.ValidationError(
                    "This mapping is referenced by student "
                    "assessment responses and cannot be modified."
                )

        if subject and competency:

            records = SubjectCompetency.objects.filter(
                subject=subject,
                competency=competency,
            )

            if self.instance.pk:

                records = records.exclude(
                    pk=self.instance.pk
                )

            if records.exists():

                raise forms.ValidationError(
                    "This competency is already assigned "
                    "to the selected subject."
                )

        return cleaned_data
