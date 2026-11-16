from django.conf import settings
from django.db import models
from django.utils import timezone


class AcademicProgram(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120, unique=True)


class Subject(models.Model):
    program = models.ForeignKey(AcademicProgram, on_delete=models.PROTECT)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["program", "code"], name="unique_program_subject")]


class Competency(models.Model):
    code = models.CharField(max_length=24, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField()


class SubjectCompetency(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    competency = models.ForeignKey(Competency, on_delete=models.PROTECT)

    class Meta:
        ordering = ["subject__code", "competency__code"]
        constraints = [models.UniqueConstraint(fields=["subject", "competency"], name="unique_subject_competency")]


class AssessmentSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at", "-pk"]


class AssessmentResponse(models.Model):
    class Rating(models.IntegerChoices):
        BEGINNING = 1, "1 — I need a walkthrough"
        DEVELOPING = 2, "2 — I can do this with help"
        PRACTICING = 3, "3 — I can usually do this on my own"
        CONFIDENT = 4, "4 — I can do this independently"
        EXPLAINING = 5, "5 — I can do this and explain it"

    assessment = models.ForeignKey(AssessmentSession, related_name="responses", on_delete=models.CASCADE)
    subject_competency = models.ForeignKey(SubjectCompetency, on_delete=models.PROTECT)
    self_rating = models.PositiveSmallIntegerField(choices=Rating.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["assessment", "subject_competency"], name="unique_session_competency"),
            models.CheckConstraint(condition=models.Q(self_rating__range=(1, 5)), name="self_rating_between_1_and_5"),
        ]
