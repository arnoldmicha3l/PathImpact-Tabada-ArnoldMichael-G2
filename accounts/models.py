
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower, Trim


class CustomUser(AbstractUser):

    class Role(models.TextChoices):

        STUDENT = "student", "Student"
        ADMINISTRATOR = "administrator", "Administrator"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    class Meta(AbstractUser.Meta):

        constraints = [

            models.UniqueConstraint(
                Lower("username"),
                name="accounts_username_ci_unique",
            ),

            models.UniqueConstraint(
                Lower(Trim("email")),
                condition=~models.Q(email__regex=r"^\s*$"),
                name="accounts_email_ci_unique",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    role__in=[
                        "student",
                        "administrator",
                    ]
                ),
                name="accounts_valid_role",
            ),

        ]
