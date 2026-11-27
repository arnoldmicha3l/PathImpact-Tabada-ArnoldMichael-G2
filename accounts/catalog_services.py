from django.db.models import Exists, OuterRef, F

from assessments.models import (
    AcademicProgram,
    Subject,
    Competency,
    SubjectCompetency,
    SubjectPrerequisite,
    CompetencyImpact,
)


def build_catalog_health():

    programs = AcademicProgram.objects.all()

    subjects = Subject.objects.all()

    competencies = Competency.objects.all()

    prerequisites = SubjectPrerequisite.objects.all()

    impacts = CompetencyImpact.objects.all()

    unmapped_subjects = subjects.annotate(
        has_mapping=Exists(
            SubjectCompetency.objects.filter(
                subject_id=OuterRef("pk")
            )
        )
    ).filter(
        has_mapping=False
    )

    unused_competencies = competencies.annotate(
        has_mapping=Exists(
            SubjectCompetency.objects.filter(
                competency_id=OuterRef("pk")
            )
        )
    ).filter(
        has_mapping=False
    )

    uncovered_prerequisites = prerequisites.annotate(
        has_impact=Exists(
            CompetencyImpact.objects.filter(
                prerequisite_id=OuterRef("pk")
            )
        )
    ).filter(
        has_impact=False
    )

    invalid_prerequisites = prerequisites.exclude(
        prerequisite__program_id=F(
            "successor__program_id"
        )
    )

    invalid_impacts = impacts.exclude(
        subject_competency__subject_id=F(
            "prerequisite__prerequisite_id"
        )
    )

    total_subjects = subjects.count()

    unmapped_count = unmapped_subjects.count()

    mapped_count = total_subjects - unmapped_count

    coverage = (
        round(
            mapped_count / total_subjects * 100,
            1,
        )
        if total_subjects
        else 0
    )

    uncovered_count = (
        uncovered_prerequisites.count()
    )

    unused_count = unused_competencies.count()

    invalid_prerequisite_count = (
        invalid_prerequisites.count()
    )

    invalid_impact_count = invalid_impacts.count()

    integrity_issue_count = (
        invalid_prerequisite_count
        + invalid_impact_count
    )

    configuration_gap_count = (
        unmapped_count
        + uncovered_count
        + unused_count
    )

    if integrity_issue_count:

        status = "Integrity issues detected"

    elif not total_subjects:

        status = "Catalog not configured"

    elif configuration_gap_count:

        status = "Configuration review recommended"

    else:

        status = "Coverage checks passed"

    return {
        "program_count": programs.count(),
        "subject_count": total_subjects,
        "competency_count": competencies.count(),
        "mapping_count": (
            SubjectCompetency.objects.count()
        ),
        "prerequisite_count": prerequisites.count(),
        "impact_count": impacts.count(),

        "mapped_subject_count": mapped_count,
        "unmapped_subject_count": unmapped_count,
        "mapping_coverage": coverage,

        "unused_competency_count": unused_count,

        "uncovered_prerequisite_count": (
            uncovered_count
        ),

        "invalid_prerequisite_count": (
            invalid_prerequisite_count
        ),

        "invalid_impact_count": (
            invalid_impact_count
        ),

        "integrity_issue_count": (
            integrity_issue_count
        ),

        "configuration_gap_count": (
            configuration_gap_count
        ),

        "status": status,

        "unmapped_subjects": list(
            unmapped_subjects.select_related(
                "program"
            ).order_by(
                "program__code",
                "code",
                "pk",
            )[:10]
        ),

        "unused_competencies": list(
            unused_competencies.order_by(
                "code",
                "pk",
            )[:10]
        ),

        "uncovered_prerequisites": list(
            uncovered_prerequisites.select_related(
                "prerequisite",
                "successor",
            ).order_by(
                "prerequisite__code",
                "successor__code",
                "pk",
            )[:10]
        ),
    }