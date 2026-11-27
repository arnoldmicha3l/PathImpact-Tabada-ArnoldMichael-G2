from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# ========================================
# 01 | ACADEMIC PROGRAM
# ========================================

class AcademicProgram(models.Model):

    code = models.CharField(
        max_length=20,
        unique=True,
    )

    name = models.CharField(
        max_length=120,
        unique=True,
    )

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


# ========================================
# 02 | ACADEMIC SUBJECT
# ========================================

class Subject(models.Model):

    class YearLevel(models.IntegerChoices):

        FIRST = 1, "First year"
        SECOND = 2, "Second year"
        THIRD = 3, "Third year"
        FOURTH = 4, "Fourth year"

    class Semester(models.IntegerChoices):

        FIRST = 1, "First semester"
        SECOND = 2, "Second semester"
        SUMMER = 3, "Summer"

    program = models.ForeignKey(
        AcademicProgram,
        on_delete=models.PROTECT,
    )

    code = models.CharField(
        max_length=20,
    )

    name = models.CharField(
        max_length=120,
    )

    year_level = models.PositiveSmallIntegerField(
        choices=YearLevel.choices,
        null=True,
        blank=True,
    )

    semester = models.PositiveSmallIntegerField(
        choices=Semester.choices,
        null=True,
        blank=True,
    )

    units = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    class Meta:

        ordering = [
            "program__code",
            "year_level",
            "semester",
            "code",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=["program", "code"],
                name="unique_program_subject",
            ),

            models.CheckConstraint(
                condition=(
                    models.Q(year_level__isnull=True)
                    | models.Q(year_level__range=(1, 4))
                ),
                name="valid_subject_year_level",
            ),

            models.CheckConstraint(
                condition=(
                    models.Q(semester__isnull=True)
                    | models.Q(semester__range=(1, 3))
                ),
                name="valid_subject_semester",
            ),

        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


# ========================================
# 03 | COMPETENCY
# ========================================

class Competency(models.Model):

    code = models.CharField(
        max_length=24,
        unique=True,
    )

    name = models.CharField(
        max_length=120,
    )

    description = models.TextField()

    def __str__(self):
        return f"{self.code} - {self.name}"


# ========================================
# 04 | SUBJECT COMPETENCY MAPPING
# ========================================

class SubjectCompetency(models.Model):

    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
    )

    competency = models.ForeignKey(
        Competency,
        on_delete=models.PROTECT,
    )

    class Meta:

        ordering = [
            "subject__code",
            "competency__code",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=["subject", "competency"],
                name="unique_subject_competency",
            ),

        ]

    def __str__(self):

        return (
            f"{self.subject.code} - "
            f"{self.competency.code}"
        )


# ========================================
# 05 | ASSESSMENT SESSION
# ========================================

class AssessmentSession(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    started_at = models.DateTimeField(
        default=timezone.now,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:

        ordering = [
            "-started_at",
            "-pk",
        ]


# ========================================
# 06 | ASSESSMENT RESPONSE
# ========================================

class AssessmentResponse(models.Model):

    class Rating(models.IntegerChoices):

        BEGINNING = 1, "1 \u2014 I need a walkthrough"

        DEVELOPING = 2, "2 \u2014 I can do this with help"

        PRACTICING = 3, "3 \u2014 I can usually do this on my own"

        CONFIDENT = 4, "4 \u2014 I can do this independently"

        EXPLAINING = 5, "5 \u2014 I can do this and explain it"

    assessment = models.ForeignKey(
        AssessmentSession,
        related_name="responses",
        on_delete=models.CASCADE,
    )

    subject_competency = models.ForeignKey(
        SubjectCompetency,
        on_delete=models.PROTECT,
    )

    self_rating = models.PositiveSmallIntegerField(
        choices=Rating.choices,
    )

    class Meta:

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "assessment",
                    "subject_competency",
                ],
                name="unique_session_competency",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    self_rating__range=(1, 5)
                ),
                name="self_rating_between_1_and_5",
            ),

        ]


# ========================================
# 07 | SUBJECT PREREQUISITE
# ========================================

class SubjectPrerequisite(models.Model):

    prerequisite = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="successor_links",
    )

    successor = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="prerequisite_links",
    )

    class Meta:

        ordering = [
            "successor__code",
            "prerequisite__code",
            "pk",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "prerequisite",
                    "successor",
                ],
                name="unique_subject_prerequisite",
            ),

            models.CheckConstraint(
                condition=~models.Q(
                    prerequisite=models.F("successor")
                ),
                name="no_self_prerequisite",
            ),

        ]

    def clean(self):

        super().clean()

        if not self.prerequisite_id or not self.successor_id:

            return

        # Prevent self-referencing prerequisites.

        if self.prerequisite_id == self.successor_id:

            raise ValidationError(
                "A subject cannot require itself."
            )

        # Verify that both subjects exist.

        subjects = dict(
            Subject.objects.filter(
                pk__in=[
                    self.prerequisite_id,
                    self.successor_id,
                ]
            ).values_list(
                "pk",
                "program_id",
            )
        )

        if (
            self.prerequisite_id not in subjects
            or self.successor_id not in subjects
        ):

            raise ValidationError(
                "Select valid prerequisite and successor subjects."
            )

        # Prevent cross-program relationships.

        if (
            subjects[self.prerequisite_id]
            != subjects[self.successor_id]
        ):

            raise ValidationError(
                "Both subjects must belong to the same program."
            )

        # Prevent duplicate relationships.

        edges = SubjectPrerequisite.objects.exclude(
            pk=self.pk
        )

        if edges.filter(
            prerequisite_id=self.prerequisite_id,
            successor_id=self.successor_id,
        ).exists():

            raise ValidationError(
                "This prerequisite relationship already exists."
            )

        # Build the prerequisite dependency graph.

        graph = {}

        for source, target in edges.values_list(
            "prerequisite_id",
            "successor_id",
        ):

            graph.setdefault(
                source,
                [],
            ).append(target)

        # Prevent circular prerequisite chains.

        pending = [self.successor_id]

        visited = set()

        while pending:

            node = pending.pop()

            if node == self.prerequisite_id:

                raise ValidationError(
                    "This relationship would create a "
                    "circular prerequisite chain."
                )

            if node not in visited:

                visited.add(node)

                pending.extend(
                    graph.get(node, [])
                )

    def __str__(self):

        return (
            f"{self.prerequisite.code} \u2192 "
            f"{self.successor.code}"
        )


# ========================================
# 08 | COMPETENCY IMPACT
# PHASE 07H.1
# ========================================

class CompetencyImpact(models.Model):

    class Relevance(models.IntegerChoices):

        LOW = 1, "Low"
        MEDIUM = 2, "Medium"
        HIGH = 3, "High"

    prerequisite = models.ForeignKey(
        SubjectPrerequisite,
        on_delete=models.PROTECT,
        related_name="competency_impacts",
    )

    subject_competency = models.ForeignKey(
        SubjectCompetency,
        on_delete=models.PROTECT,
        related_name="competency_impacts",
    )

    relevance = models.PositiveSmallIntegerField(
        choices=Relevance.choices,
        default=Relevance.MEDIUM,
    )

    class Meta:

        ordering = [
            "prerequisite__prerequisite__code",
            "prerequisite__successor__code",
            "subject_competency__competency__code",
            "pk",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "prerequisite",
                    "subject_competency",
                ],
                name="unique_competency_impact",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    relevance__range=(1, 3)
                ),
                name="valid_impact_relevance",
            ),

        ]

    def clean(self):

        super().clean()

        if not self.prerequisite_id:

            return

        if not self.subject_competency_id:

            return

        # Verify the prerequisite relationship.

        prerequisite = (
            SubjectPrerequisite.objects
            .filter(
                pk=self.prerequisite_id
            )
            .first()
        )

        # Verify the competency mapping.

        mapping = (
            SubjectCompetency.objects
            .filter(
                pk=self.subject_competency_id
            )
            .first()
        )

        if prerequisite is None or mapping is None:

            raise ValidationError(
                "Select valid academic relationships."
            )

        # Ensure that the competency belongs to
        # the selected prerequisite subject.

        if mapping.subject_id != prerequisite.prerequisite_id:

            raise ValidationError({

                "subject_competency": (
                    "The competency must belong to "
                    "the selected prerequisite subject."
                )

            })

        # Prevent duplicate competency impacts.

        duplicate = CompetencyImpact.objects.filter(
            prerequisite_id=self.prerequisite_id,
            subject_competency_id=self.subject_competency_id,
        ).exclude(
            pk=self.pk
        )

        if duplicate.exists():

            raise ValidationError(
                "This competency impact already exists."
            )

    def __str__(self):

        return (
            f"{self.subject_competency} -> "
            f"{self.prerequisite.successor.code}"
        )


class ReadinessResult(models.Model):

    class Level(models.TextChoices):

        NEEDS_STRENGTHENING = (
            "Needs strengthening",
            "Needs strengthening",
        )

        DEVELOPING = (
            "Developing readiness",
            "Developing readiness",
        )

        HIGHER = (
            "Higher readiness",
            "Higher readiness",
        )

        INSUFFICIENT = (
            "Insufficient information",
            "Insufficient information",
        )

    assessment = models.ForeignKey(
        AssessmentSession,
        on_delete=models.CASCADE,
        related_name="readiness_results",
    )

    succeeding_subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="readiness_results",
    )

    readiness_level = models.CharField(
        max_length=30,
        choices=Level.choices,
    )

    readiness_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
    )

    is_affected = models.BooleanField(
        default=False,
    )

    required_competency_count = (
        models.PositiveIntegerField(default=0)
    )

    missing_count = models.PositiveIntegerField(
        default=0,
    )

    gap_count = models.PositiveIntegerField(
        default=0,
    )

    rule_version = models.CharField(
        max_length=20,
    )

    subject_code_snapshot = models.CharField(
        max_length=20,
    )

    subject_name_snapshot = models.CharField(
        max_length=120,
    )

    generated_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:

        ordering = [
            "-is_affected",
            "subject_code_snapshot",
            "pk",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "assessment",
                    "succeeding_subject",
                ],
                name="unique_assessment_readiness",
            ),

            models.CheckConstraint(
                condition=(
                    models.Q(
                        readiness_score__isnull=True
                    )
                    | models.Q(
                        readiness_score__range=(1, 5)
                    )
                ),
                name="valid_readiness_score",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    readiness_level__in=[
                        "Needs strengthening",
                        "Developing readiness",
                        "Higher readiness",
                        "Insufficient information",
                    ]
                ),
                name="valid_readiness_level",
            ),

            models.CheckConstraint(
                condition=(
                    models.Q(
                        readiness_level="Insufficient information",
                        readiness_score__isnull=True,
                    )
                    | (
                        ~models.Q(
                            readiness_level="Insufficient information"
                        )
                        & models.Q(
                            readiness_score__isnull=False
                        )
                    )
                ),
                name="consistent_readiness_score",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    missing_count__lte=models.F(
                        "required_competency_count"
                    )
                ),
                name="valid_readiness_missing_count",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    gap_count__lte=(
                        models.F("required_competency_count")
                        - models.F("missing_count")
                    )
                ),
                name="valid_readiness_gap_count",
            ),

            models.CheckConstraint(
                condition=(
                    models.Q(
                        is_affected=True,
                        gap_count__gt=0,
                    )
                    | models.Q(
                        is_affected=False,
                        gap_count=0,
                    )
                ),
                name="consistent_affected_subject",
            ),

        ]

    def __str__(self):

        return (
            f"Assessment #{self.assessment_id} | "
            f"{self.subject_code_snapshot} | "
            f"{self.readiness_level}"
        )


class ReviewRecommendation(models.Model):

    response = models.ForeignKey(
        AssessmentResponse,
        on_delete=models.CASCADE,
        related_name="review_recommendations",
    )

    succeeding_subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="review_recommendations",
    )

    priority_rank = models.PositiveIntegerField()

    priority_score = models.PositiveSmallIntegerField()

    relevance = models.PositiveSmallIntegerField(
        choices=CompetencyImpact.Relevance.choices,
    )

    self_rating_snapshot = (
        models.PositiveSmallIntegerField()
    )

    competency_code_snapshot = models.CharField(
        max_length=24,
    )

    competency_name_snapshot = models.CharField(
        max_length=120,
    )

    subject_code_snapshot = models.CharField(
        max_length=20,
    )

    subject_name_snapshot = models.CharField(
        max_length=120,
    )

    recommendation_text = models.TextField()

    rule_version = models.CharField(
        max_length=20,
    )

    generated_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:

        ordering = [
            "priority_rank",
            "pk",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "response",
                    "succeeding_subject",
                ],
                name="unique_response_recommendation",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    priority_rank__gte=1
                ),
                name="valid_review_priority_rank",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    priority_score__range=(2, 12)
                ),
                name="valid_review_priority_score",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    relevance__range=(1, 3)
                ),
                name="valid_review_relevance",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    self_rating_snapshot__range=(1, 3)
                ),
                name="valid_review_gap_rating",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    priority_score=(
                        (5 - models.F("self_rating_snapshot"))
                        * models.F("relevance")
                    )
                ),
                name="consistent_review_priority",
            ),

        ]

    def __str__(self):

        return (
            f"Priority {self.priority_rank} | "
            f"{self.competency_code_snapshot} | "
            f"{self.subject_code_snapshot}"
        )
