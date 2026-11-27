
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AcademicProgram(models.Model):

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


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

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)

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


class Competency(models.Model):

    code = models.CharField(max_length=24, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField()

    def __str__(self):
        return f"{self.code} - {self.name}"


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
        return f"{self.subject.code} - {self.competency.code}"


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
        ordering = ["-started_at", "-pk"]


class AssessmentResponse(models.Model):

    class Rating(models.IntegerChoices):

        BEGINNING = 1, "1 — I need a walkthrough"

        DEVELOPING = 2, "2 — I can do this with help"

        PRACTICING = 3, "3 — I can usually do this on my own"

        CONFIDENT = 4, "4 — I can do this independently"

        EXPLAINING = 5, "5 — I can do this and explain it"

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
                fields=["assessment", "subject_competency"],
                name="unique_session_competency",
            ),

            models.CheckConstraint(
                condition=models.Q(self_rating__range=(1, 5)),
                name="self_rating_between_1_and_5",
            ),

        ]


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
                fields=["prerequisite", "successor"],
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

        if self.prerequisite_id == self.successor_id:

            raise ValidationError(
                "A subject cannot require itself."
            )

        subjects = dict(
            Subject.objects.filter(
                pk__in=[
                    self.prerequisite_id,
                    self.successor_id,
                ]
            ).values_list("pk", "program_id")
        )

        if (
            self.prerequisite_id not in subjects
            or self.successor_id not in subjects
        ):

            raise ValidationError(
                "Select valid prerequisite and successor subjects."
            )

        if (
            subjects[self.prerequisite_id]
            != subjects[self.successor_id]
        ):

            raise ValidationError(
                "Both subjects must belong to the same program."
            )

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

        graph = {}

        for source, target in edges.values_list(
            "prerequisite_id",
            "successor_id",
        ):

            graph.setdefault(source, []).append(target)

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
            f"{self.prerequisite.code} → "
            f"{self.successor.code}"
        )
