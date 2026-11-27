from django import forms

from assessments.models import (
    CompetencyImpact,
    SubjectCompetency,
    SubjectPrerequisite,
)


class PrerequisiteChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):

        return (
            f"{obj.prerequisite.program.code} | "
            f"{obj.prerequisite.code} → "
            f"{obj.successor.code}"
        )


class MappingChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):

        return (
            f"{obj.subject.program.code} | "
            f"{obj.subject.code} | "
            f"{obj.competency.code} - "
            f"{obj.competency.name}"
        )


class ImpactForm(forms.ModelForm):

    prerequisite = PrerequisiteChoiceField(
        queryset=(
            SubjectPrerequisite.objects
            .select_related(
                "prerequisite__program",
                "successor",
            )
        ),
        label="Prerequisite relationship",
        empty_label="Select a prerequisite relationship",
        help_text=(
            "Select the prerequisite subject and "
            "its succeeding subject."
        ),
    )

    subject_competency = MappingChoiceField(
        queryset=(
            SubjectCompetency.objects
            .select_related(
                "subject__program",
                "competency",
            )
        ),
        label="Prerequisite competency",
        empty_label="Select a competency mapping",
        help_text=(
            "The competency must belong to "
            "the selected prerequisite subject."
        ),
    )

    class Meta:

        model = CompetencyImpact

        fields = [
            "prerequisite",
            "subject_competency",
            "relevance",
        ]

        labels = {
            "relevance": "Competency relevance",
        }

        help_texts = {
            "relevance": (
                "Low = 1, Medium = 2, High = 3. "
                "Relevance represents the importance "
                "of this competency to the succeeding subject."
            ),
        }