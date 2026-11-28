from django import forms
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from assessments import analysis_rules as rules

from .administrator_views import administrator_only


class AnalysisSimulatorForm(forms.Form):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        rating_choices = [
            (rating, str(rating))
            for rating in range(
                rules.MIN_RATING,
                rules.MAX_RATING + 1,
            )
        ]

        relevance_choices = [
            (value, rules.RELEVANCE_LABELS[value])
            for value in sorted(
                rules.RELEVANCE_WEIGHTS
            )
        ]

        defaults = [
            (2, 3),
            (3, 2),
            (4, 1),
        ]

        for index, (rating, relevance) in enumerate(
            defaults,
            start=1,
        ):

            self.fields[f"rating_{index}"] = (
                forms.TypedChoiceField(
                    label=f"Competency {index} rating",
                    choices=rating_choices,
                    coerce=int,
                    initial=rating,
                    widget=forms.Select(
                        attrs={
                            "class": "ar-select",
                        }
                    ),
                )
            )

            self.fields[f"relevance_{index}"] = (
                forms.TypedChoiceField(
                    label=f"Competency {index} relevance",
                    choices=relevance_choices,
                    coerce=int,
                    initial=relevance,
                    widget=forms.Select(
                        attrs={
                            "class": "ar-select",
                        }
                    ),
                )
            )

    def calculate(self):

        inputs = []

        items = []

        for index in range(1, 4):

            rating = self.cleaned_data[
                f"rating_{index}"
            ]

            relevance = self.cleaned_data[
                f"relevance_{index}"
            ]

            inputs.append(
                (rating, relevance)
            )

            items.append({
                "name": f"Sample competency {index}",
                "rating": rating,
                "relevance": relevance,
                "relevance_label": (
                    rules.RELEVANCE_LABELS[relevance]
                ),
                "weight": rules.relevance_weight(
                    relevance
                ),
                "is_gap": rules.is_competency_gap(
                    rating
                ),
                "priority_score": rules.priority_score(
                    rating,
                    relevance,
                ),
                "description": rules.gap_description(
                    rating
                ),
                "index": index,
            })

        score = rules.weighted_readiness(inputs)

        priorities = [
            item
            for item in items
            if item["is_gap"]
        ]

        priorities.sort(
            key=lambda item: (
                -item["priority_score"],
                -item["relevance"],
                item["rating"],
                item["index"],
            )
        )

        for rank, item in enumerate(
            priorities,
            start=1,
        ):

            item["priority_rank"] = rank

        return {
            "score": rules.display_score(score),
            "level": rules.classify_readiness(score),
            "gap_count": len(priorities),
            "priorities": priorities,
            "items": items,
            "numerator": sum(
                rating * rules.relevance_weight(
                    relevance
                )
                for rating, relevance in inputs
            ),
            "denominator": sum(
                rules.relevance_weight(relevance)
                for _, relevance in inputs
            ),
        }


@administrator_only
@require_http_methods(["GET", "POST"])
@never_cache
def analysis_rules(request):

    form = AnalysisSimulatorForm(
        request.POST
        if request.method == "POST"
        else None
    )

    simulation = None

    if request.method == "POST":

        if form.is_valid():

            simulation = form.calculate()

    rating_rows = [
        {
            "rating": rating,
            "description": rules.gap_description(
                rating
            ),
            "is_gap": rules.is_competency_gap(
                rating
            ),
        }
        for rating in range(
            rules.MIN_RATING,
            rules.MAX_RATING + 1,
        )
    ]

    relevance_rows = [
        {
            "label": rules.RELEVANCE_LABELS[value],
            "weight": weight,
        }
        for value, weight in sorted(
            rules.RELEVANCE_WEIGHTS.items()
        )
    ]

    readiness_rows = [
        {
            "range": "1.00 to below 3.00",
            "level": rules.classify_readiness(1),
            "style": "strengthening",
        },
        {
            "range": "3.00 to below 4.00",
            "level": rules.classify_readiness(3),
            "style": "developing",
        },
        {
            "range": "4.00 to 5.00",
            "level": rules.classify_readiness(4),
            "style": "higher",
        },
    ]

    simulator_rows = [
        {
            "name": f"Sample competency {index}",
            "rating": form[f"rating_{index}"],
            "relevance": form[f"relevance_{index}"],
        }
        for index in range(1, 4)
    ]

    context = {
        "rule_version": rules.RULE_VERSION,
        "minimum_rating": rules.MIN_RATING,
        "maximum_rating": rules.MAX_RATING,
        "gap_threshold": rules.GAP_THRESHOLD,
        "rating_rows": rating_rows,
        "relevance_rows": relevance_rows,
        "readiness_rows": readiness_rows,
        "simulator_rows": simulator_rows,
        "simulation": simulation,
        "form": form,
        "disclaimer": rules.DISCLAIMER,
    }

    return render(
        request,
        "accounts/analysis_rules.html",
        context,
        status=(
            400
            if request.method == "POST"
            and form.errors
            else 200
        ),
    )