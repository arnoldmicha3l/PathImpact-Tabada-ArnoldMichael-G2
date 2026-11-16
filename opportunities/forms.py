import re

from django import forms
from django.utils import timezone

from .models import Application, Opportunity


class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = [
            "title", "category", "location", "event_date",
            "deadline", "slots", "status", "description",
        ]
        widgets = {
            "event_date": forms.DateInput(attrs={"type": "date"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 6}),
            "slots": forms.NumberInput(attrs={"min": 1}),
        }

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters.")
        return title

    def clean_slots(self):
        slots = self.cleaned_data["slots"]
        if slots < 1:
            raise forms.ValidationError("At least 1 volunteer slot is required.")
        if self.instance.pk and slots < self.instance.approved_count:
            raise forms.ValidationError(
                f"{self.instance.approved_count} volunteers are already approved; "
                "slots cannot go below that number."
            )
        return slots

    def clean_description(self):
        text = self.cleaned_data["description"].strip()
        if len(text) < 20:
            raise forms.ValidationError("Please describe the opportunity (20+ characters).")
        return text

    def clean(self):
        cleaned = super().clean()
        event_date, deadline = cleaned.get("event_date"), cleaned.get("deadline")
        today = timezone.localdate()
        if event_date and not self.instance.pk and event_date < today:
            self.add_error("event_date", "The event date cannot be in the past.")
        if event_date and deadline and deadline > event_date:
            self.add_error("deadline", "The deadline must be on or before the event date.")
        if deadline and not self.instance.pk and deadline < today:
            self.add_error("deadline", "The deadline cannot be in the past.")
        return cleaned


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["contact_number", "motivation"]
        widgets = {
            "contact_number": forms.TextInput(attrs={"placeholder": "e.g. 09171234567"}),
            "motivation": forms.Textarea(
                attrs={"rows": 6, "placeholder": "Why do you want to join this opportunity?"}
            ),
        }

    def clean_contact_number(self):
        number = self.cleaned_data["contact_number"].strip()
        if not re.fullmatch(r"\+?[0-9][0-9 \-]{6,18}[0-9]", number):
            raise forms.ValidationError("Enter a valid contact number (7-15 digits).")
        return number

    def clean_motivation(self):
        text = self.cleaned_data["motivation"].strip()
        if len(text) < 30:
            raise forms.ValidationError("Please write at least 30 characters.")
        return text


class ReviewForm(forms.ModelForm):
    decision = forms.ChoiceField(
        choices=[
            (Application.Status.APPROVED, "Approve"),
            (Application.Status.REJECTED, "Reject"),
            (Application.Status.PENDING, "Keep pending"),
        ],
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Application
        fields = ["admin_remarks"]
        widgets = {"admin_remarks": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["decision"].initial = self.instance.status

    def clean(self):
        cleaned = super().clean()
        decision = cleaned.get("decision")
        remarks = (cleaned.get("admin_remarks") or "").strip()
        opp = self.instance.opportunity
        if (
            decision == Application.Status.APPROVED
            and self.instance.status != Application.Status.APPROVED
            and opp.slots_left < 1
        ):
            raise forms.ValidationError("No slots left: cannot approve more volunteers.")
        if decision == Application.Status.REJECTED and not remarks:
            self.add_error("admin_remarks", "Please give a reason when rejecting.")
        return cleaned

    def save(self, commit=True):
        self.instance.status = self.cleaned_data["decision"]
        return super().save(commit=commit)
