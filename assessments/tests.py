from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import AssessmentResponse, AssessmentSession, SubjectCompetency


class AssessmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.student = users.create_user("learner", "learner@example.test")
        cls.other = users.create_user("other", "other@example.test")
        cls.staff = users.create_user("staff", "staff@example.test", role="administrator")
        cls.ratings = {f"rating_{i}": "3" for i in SubjectCompetency.objects.values_list("pk", flat=True)}

    def test_ui_create_read_edit_delete(self):
        self.client.force_login(self.student)
        self.assertContains(self.client.get(reverse("accounts:student_dashboard")), "Open self-assessments")
        r = self.client.post(reverse("assessment_create"), self.ratings, follow=True)
        attempt = AssessmentSession.objects.get(user=self.student)
        self.assertIsNotNone(attempt.completed_at)
        self.assertContains(r, "Self-assessment saved")
        self.assertContains(self.client.get(reverse("assessment_index")), f"Attempt {attempt.pk}")
        self.assertEqual(attempt.responses.count(), 3)
        edit = reverse("assessment_edit", args=[attempt.pk])
        self.assertContains(self.client.get(edit), 'value="3" selected', count=3)
        self.client.post(edit, {k: 5 for k in self.ratings}, follow=True)
        self.assertEqual(list(attempt.responses.values_list("self_rating", flat=True)), [5, 5, 5])
        target = reverse("assessment_delete", args=[attempt.pk])
        self.client.get(target)
        self.assertTrue(AssessmentSession.objects.filter(pk=attempt.pk).exists())
        self.assertContains(self.client.post(target, follow=True), "Self-assessment deleted")
        self.assertFalse(AssessmentResponse.objects.filter(assessment_id=attempt.pk).exists())

    def test_reject_missing_and_out_of_bounds_ratings(self):
        self.client.force_login(self.student)
        url = reverse("assessment_create")
        values = self.ratings.copy()
        values.pop(next(iter(values)))
        self.assertContains(self.client.post(url, values), "This field is required.")
        self.assertContains(self.client.post(url, {k: 9 for k in self.ratings}), "Select a valid choice")
        self.assertFalse(AssessmentSession.objects.exists())

    def test_guest_staff_and_other_student_access(self):
        attempt = AssessmentSession.objects.create(user=self.student)
        routes = [reverse(name, args=[attempt.pk]) for name in ("assessment_detail", "assessment_edit", "assessment_delete")]
        for url in routes:
            self.assertRedirects(self.client.get(url), reverse("accounts:login") + "?next=" + url)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("assessment_index")).status_code, 403)
        self.assertNotContains(self.client.get(reverse("accounts:administrator_dashboard")), "Self-assessments")
        self.client.force_login(self.other)
        for url in routes:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(routes[1], self.ratings).status_code, 404)
        self.assertEqual(self.client.post(routes[2]).status_code, 404)

    def test_database_rejects_duplicate_and_invalid_ratings(self):
        attempt = AssessmentSession.objects.create(user=self.student)
        competency = SubjectCompetency.objects.first()
        data = dict(assessment=attempt, subject_competency=competency)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AssessmentResponse.objects.create(**data, self_rating=6)
        AssessmentResponse.objects.create(**data, self_rating=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AssessmentResponse.objects.create(**data, self_rating=4)
