
from django import forms

from .models import AssessmentResponse


class AssessmentForm(forms.Form):

    def __init__(
        self,
        *args,
        competencies,
        ratings=None,
        **kwargs,
    ):

        super().__init__(*args, **kwargs)

        self.competencies = tuple(competencies)

        for item in self.competencies:

            self.fields[f"rating_{item.pk}"] = (
                forms.TypedChoiceField(
                    label=item.competency.name,
                    help_text=item.competency.description,
                    choices=AssessmentResponse.Rating.choices,
                    coerce=int,
                    required=True,
                    initial=(ratings or {}).get(item.pk),
                    widget=forms.RadioSelect,
                    error_messages={
                        "required": (
                            "Select a rating for this competency."
                        ),
                        "invalid_choice": (
                            "Select a valid rating from 1 to 5."
                        ),
                    },
                )
            )

    def clean(self):

        values = super().clean()

        if not self.competencies:

            raise forms.ValidationError(
                "No competencies are available to assess yet.",
                code="empty_catalog",
            )

        expected_fields = {
            self.add_prefix(f"rating_{item.pk}")
            for item in self.competencies
        }

        rating_prefix = self.add_prefix("rating_")

        submitted_fields = {
            key
            for key in self.data
            if key.startswith(rating_prefix)
        }

        unexpected_fields = (
            submitted_fields - expected_fields
        )

        if unexpected_fields:

            self.add_error(
                None,
                forms.ValidationError(
                    "The assessment contains invalid or "
                    "outdated competency selections. "
                    "Reload the assessment and try again.",
                    code="unexpected_competency",
                ),
            )

        if hasattr(self.data, "getlist"):

            for field_name in self.fields:

                submitted_values = self.data.getlist(
                    self.add_prefix(field_name)
                )

                if len(submitted_values) > 1:

                    self.add_error(
                        field_name,
                        forms.ValidationError(
                            "Submit only one rating "
                            "for this competency.",
                            code="duplicate_rating",
                        ),
                    )

        return values

    def responses(self, assessment):

        if not self.is_bound or not self.is_valid():

            raise ValueError(
                "Assessment responses cannot be generated "
                "from an invalid or unsubmitted form."
            )

        return [
            AssessmentResponse(
                assessment=assessment,
                subject_competency=item,
                self_rating=self.cleaned_data[
                    f"rating_{item.pk}"
                ],
            )
            for item in self.competencies
        ]
