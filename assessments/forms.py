from django import forms

from .models import AssessmentResponse


class AssessmentForm(forms.Form):
    def __init__(self, *args, competencies, ratings=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.competencies = tuple(competencies)
        for item in self.competencies:
            self.fields[f"rating_{item.pk}"] = forms.TypedChoiceField(
                label=f"{item.competency.name}",
                help_text=item.competency.description,
                choices=[("", "Choose your rating"), *AssessmentResponse.Rating.choices],
                coerce=int,
                initial=(ratings or {}).get(item.pk),
            )

    def clean(self):
        values = super().clean()
        if not self.competencies:
            raise forms.ValidationError("No competencies are available to assess yet.")
        return values

    def responses(self, assessment):
        return [
            AssessmentResponse(assessment=assessment, subject_competency=item,
                               self_rating=self.cleaned_data[f"rating_{item.pk}"])
            for item in self.competencies
        ]
