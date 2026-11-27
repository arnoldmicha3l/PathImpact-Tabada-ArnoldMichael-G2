
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .analysis_rules import DISCLAIMER
from .analysis_services import analyze_assessment

from .models import (
    AcademicProgram,
    AssessmentSession,
    ReadinessResult,
    ReviewRecommendation,
)


def require_student(user):

    if (
        not user.is_authenticated
        or not user.is_active
        or user.role != "student"
    ):

        raise PermissionDenied(
            "You cannot access individual assessment results."
        )


@transaction.atomic
def generate_assessment_results(*, user, assessment_id):

    require_student(user)

    # Follow the existing academic catalog locking order.

    list(
        AcademicProgram.objects.select_for_update()
        .order_by("pk")
        .values_list("pk", flat=True)
    )

    assessment = get_object_or_404(
        AssessmentSession.objects.select_for_update(),
        pk=assessment_id,
        user=user,
    )

    # Calculate before replacing existing results.
    # Any calculation failure leaves previous records intact.

    analysis = analyze_assessment(
        user=user,
        assessment_id=assessment.pk,
    )

    generated_at = timezone.now()

    ReadinessResult.objects.filter(
        assessment=assessment
    ).delete()

    ReviewRecommendation.objects.filter(
        response__assessment=assessment
    ).delete()

    readiness_records = []

    recommendation_records = []

    for subject in analysis["subjects"]:

        readiness_records.append(

            ReadinessResult(
                assessment=assessment,

                succeeding_subject_id=(
                    subject["subject_id"]
                ),

                readiness_level=(
                    subject["readiness_level"]
                ),

                readiness_score=(
                    subject["readiness_score"]
                ),

                is_affected=(
                    subject["is_affected"]
                ),

                required_competency_count=(
                    subject["required_competency_count"]
                ),

                missing_count=(
                    subject["missing_count"]
                ),

                gap_count=(
                    subject["gap_count"]
                ),

                rule_version=(
                    analysis["rule_version"]
                ),

                subject_code_snapshot=(
                    subject["subject_code"]
                ),

                subject_name_snapshot=(
                    subject["subject_name"]
                ),

                generated_at=generated_at,
            )

        )

    for item in analysis["recommendations"]:

        recommendation_records.append(

            ReviewRecommendation(
                response_id=item["response_id"],

                succeeding_subject_id=(
                    item["subject_id"]
                ),

                priority_rank=(
                    item["priority_rank"]
                ),

                priority_score=(
                    item["priority_score"]
                ),

                relevance=item["relevance"],

                self_rating_snapshot=(
                    item["rating"]
                ),

                competency_code_snapshot=(
                    item["competency_code"]
                ),

                competency_name_snapshot=(
                    item["competency_name"]
                ),

                subject_code_snapshot=(
                    item["subject_code"]
                ),

                subject_name_snapshot=(
                    item["subject_name"]
                ),

                recommendation_text=(
                    item["recommendation_text"]
                ),

                rule_version=(
                    analysis["rule_version"]
                ),

                generated_at=generated_at,
            )

        )

    ReadinessResult.objects.bulk_create(
        readiness_records
    )

    ReviewRecommendation.objects.bulk_create(
        recommendation_records
    )

    return analysis


def get_saved_assessment_results(*, user, assessment_id):

    require_student(user)

    assessment = get_object_or_404(
        AssessmentSession,
        pk=assessment_id,
        user=user,
    )

    readiness_results = list(

        assessment.readiness_results.all()

    )

    recommendations = list(

        ReviewRecommendation.objects.filter(
            response__assessment=assessment
        ).order_by(
            "priority_rank",
            "pk",
        )

    )

    if assessment.completed_at is None:

        status = "incomplete_assessment"

    elif not readiness_results:

        status = "no_saved_results"

    elif any(
        item.missing_count > 0
        for item in readiness_results
    ):

        status = "partial_information"

    else:

        status = "analyzed"

    return {

        "assessment": assessment,

        "status": status,

        "readiness_results": readiness_results,

        "recommendations": recommendations,

        "affected_subject_count": sum(
            item.is_affected
            for item in readiness_results
        ),

        "recommendation_count": len(
            recommendations
        ),

        "generated_at": max(
            (
                item.generated_at
                for item in readiness_results
            ),
            default=None,
        ),

        "disclaimer": DISCLAIMER,

    }
