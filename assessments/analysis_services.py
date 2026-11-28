
from collections import defaultdict

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import (
    AssessmentSession,
    CompetencyImpact,
)

from .analysis_rules import (
    RULE_VERSION,
    DISCLAIMER,
    READINESS_INSUFFICIENT,
    READINESS_UNAVAILABLE,
    classify_readiness,
    display_score,
    gap_description,
    is_competency_gap,
    priority_score,
    recommendation_text,
    weighted_readiness,
)


def empty_result(assessment_id, status):

    return {
        "assessment_id": assessment_id,
        "rule_version": RULE_VERSION,
        "status": status,
        "response_count": 0,
        "gap_count": 0,
        "affected_subject_count": 0,
        "gaps": [],
        "subjects": [],
        "recommendations": [],
        "disclaimer": DISCLAIMER,
    }


def analyze_assessment(*, user, assessment_id):

    # Restrict individual analysis to active student owners.

    if (
        not user.is_authenticated
        or not user.is_active
        or user.role != "student"
    ):
        raise PermissionDenied(
            "You cannot access this assessment analysis."
        )

    assessment = get_object_or_404(
        AssessmentSession,
        pk=assessment_id,
        user=user,
    )

    if assessment.completed_at is None:

        return empty_result(
            assessment.pk,
            "incomplete_assessment",
        )

    responses = list(
        assessment.responses.select_related(
            "subject_competency__subject__program",
            "subject_competency__competency",
        ).order_by(
            "subject_competency__subject__code",
            "subject_competency__competency__code",
            "pk",
        )
    )

    if not responses:

        return empty_result(
            assessment.pk,
            "no_responses",
        )

    response_lookup = {
        response.subject_competency_id: response
        for response in responses
    }

    gaps = []

    # Identify gaps from actual student responses.

    for response in responses:

        mapping = response.subject_competency

        if is_competency_gap(response.self_rating):

            gaps.append({
                "response_id": response.pk,
                "mapping_id": mapping.pk,
                "subject_id": mapping.subject_id,
                "subject_code": mapping.subject.code,
                "subject_name": mapping.subject.name,
                "competency_id": mapping.competency_id,
                "competency_code": mapping.competency.code,
                "competency_name": mapping.competency.name,
                "rating": response.self_rating,
                "description": gap_description(
                    response.self_rating
                ),
            })

    # Find explicitly defined competency impacts.

    relevant_impacts = CompetencyImpact.objects.filter(
        subject_competency_id__in=response_lookup.keys()
    )

    successor_ids = list(
        relevant_impacts.order_by().values_list(
            "prerequisite__successor_id",
            flat=True,
        ).distinct()
    )

    # Include all defined impacts for candidate subjects.
    # This prevents missing ratings from being ignored.

    impacts = list(
        CompetencyImpact.objects.filter(
            prerequisite__successor_id__in=successor_ids
        ).select_related(
            "prerequisite__prerequisite",
            "prerequisite__successor__program",
            "subject_competency__subject",
            "subject_competency__competency",
        ).order_by(
            "prerequisite__successor__code",
            "subject_competency__competency__code",
            "pk",
        )
    )

    grouped_impacts = defaultdict(list)

    for impact in impacts:

        # Reject inconsistent reference relationships.

        if (
            impact.subject_competency.subject_id
            != impact.prerequisite.prerequisite_id
        ):
            raise ValueError(
                "An inconsistent competency impact exists."
            )

        if (
            impact.prerequisite.prerequisite.program_id
            != impact.prerequisite.successor.program_id
        ):
            raise ValueError(
                "A cross-program competency impact exists."
            )

        grouped_impacts[
            impact.prerequisite.successor_id
        ].append(impact)

    subjects = []

    recommendations = []

    for subject_id, subject_impacts in grouped_impacts.items():

        successor = (
            subject_impacts[0]
            .prerequisite.successor
        )

        readiness_inputs = []

        subject_gaps = []

        missing_count = 0

        for impact in subject_impacts:

            mapping = impact.subject_competency

            response = response_lookup.get(mapping.pk)

            if response is None:

                readiness_inputs.append(
                    (None, impact.relevance)
                )

                missing_count += 1

                continue

            rating = response.self_rating

            readiness_inputs.append(
                (rating, impact.relevance)
            )

            if not is_competency_gap(rating):

                continue

            item = {
                "response_id": response.pk,
                "impact_id": impact.pk,
                "subject_id": successor.pk,
                "subject_code": successor.code,
                "subject_name": successor.name,
                "prerequisite_code": mapping.subject.code,
                "competency_code": mapping.competency.code,
                "competency_name": mapping.competency.name,
                "rating": rating,
                "relevance": impact.relevance,
                "relevance_label": (
                    impact.get_relevance_display()
                ),
                "priority_score": priority_score(
                    rating,
                    impact.relevance,
                ),
                "recommendation_text": recommendation_text(
                    mapping.competency.name,
                    successor.name,
                ),
            }

            subject_gaps.append(item)

            recommendations.append(item)

        raw_score = weighted_readiness(
            readiness_inputs
        )

        readiness_level = classify_readiness(
            raw_score,
            has_impacts=bool(subject_impacts),
        )

        subjects.append({
            "subject_id": subject_id,
            "subject_code": successor.code,
            "subject_name": successor.name,
            "program_code": successor.program.code,
            "readiness_score": display_score(raw_score),
            "readiness_level": readiness_level,
            "required_competency_count": len(
                subject_impacts
            ),
            "missing_count": missing_count,
            "gap_count": len(subject_gaps),
            "is_affected": bool(subject_gaps),
            "gaps": subject_gaps,
        })

    # Highest review priority appears first.
    # Additional sorting ensures deterministic ties.

    recommendations.sort(
        key=lambda item: (
            -item["priority_score"],
            -item["relevance"],
            item["rating"],
            item["competency_code"],
            item["subject_code"],
            item["response_id"],
            item["subject_id"],
        )
    )

    for rank, recommendation in enumerate(
        recommendations,
        start=1,
    ):

        recommendation["priority_rank"] = rank

    subjects.sort(
        key=lambda item: (
            not item["is_affected"],
            item["readiness_score"] is None,
            (
                item["readiness_score"]
                if item["readiness_score"] is not None
                else 0
            ),
            item["subject_code"],
            item["subject_id"],
        )
    )

    if not subjects:

        status = "no_defined_impacts"

    elif any(
        subject["readiness_level"] == READINESS_INSUFFICIENT
        for subject in subjects
    ):

        status = "partial_information"

    else:

        status = "analyzed"

    return {
        "assessment_id": assessment.pk,
        "rule_version": RULE_VERSION,
        "status": status,
        "response_count": len(responses),
        "gap_count": len(gaps),
        "affected_subject_count": sum(
            subject["is_affected"]
            for subject in subjects
        ),
        "gaps": gaps,
        "subjects": subjects,
        "recommendations": recommendations,
        "disclaimer": DISCLAIMER,
    }
