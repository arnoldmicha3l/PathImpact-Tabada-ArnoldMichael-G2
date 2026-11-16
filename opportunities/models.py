from django.conf import settings
from django.db import models
from django.utils import timezone


class Opportunity(models.Model):
    class Category(models.TextChoices):
        EDUCATION = "education", "Education"
        ENVIRONMENT = "environment", "Environment"
        HEALTH = "health", "Health & Wellness"
        COMMUNITY = "community", "Community Service"
        TECH = "tech", "Tech for Good"
        DISASTER = "disaster", "Disaster Relief"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices)
    location = models.CharField(max_length=150)
    event_date = models.DateField()
    deadline = models.DateField(help_text="Last day students can apply.")
    slots = models.PositiveIntegerField(help_text="Number of volunteers needed.")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="opportunities",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["event_date", "title"]
        verbose_name_plural = "opportunities"

    def __str__(self):
        return self.title

    ICONS = {"education": "📚", "environment": "🌿", "health": "💚",
             "community": "🤝", "tech": "💻", "disaster": "🆘"}

    @property
    def icon(self):
        return self.ICONS.get(self.category, "✨")

    @property
    def approved_count(self):
        return self.applications.filter(status=Application.Status.APPROVED).count()

    @property
    def slots_left(self):
        return max(self.slots - self.approved_count, 0)

    @property
    def fill_percent(self):
        if not self.slots:
            return 0
        return min(int(self.approved_count * 100 / self.slots), 100)

    @property
    def is_accepting(self):
        """Business rule: open, before the deadline and with free slots."""
        return (
            self.status == self.Status.OPEN
            and self.deadline >= timezone.localdate()
            and self.slots_left > 0
        )

    @property
    def closed_reason(self):
        if self.status == self.Status.CLOSED:
            return "This opportunity is closed."
        if self.deadline < timezone.localdate():
            return "The application deadline has passed."
        if self.slots_left == 0:
            return "All volunteer slots are filled."
        return ""


class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="applications"
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    contact_number = models.CharField(max_length=20)
    motivation = models.TextField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    admin_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["opportunity", "applicant"],
                name="unique_application_per_student",
            )
        ]

    def __str__(self):
        return f"{self.applicant} -> {self.opportunity}"
