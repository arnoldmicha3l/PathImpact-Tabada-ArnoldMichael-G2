from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from assessments import analysis_rules as rules

from assessments.models import (
    AssessmentSession,
    AssessmentResponse,
    ReadinessResult,
    ReviewRecommendation,
    CompetencyImpact,
)

from .analysis_rule_views import AnalysisSimulatorForm


class AnalysisRulesWorkspaceTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        users = get_user_model().objects

        cls.administrator = users.create_user(
            username="rules_administrator",
            email="rules_admin@example.test",
            role="administrator",
        )

        cls.student = users.create_user(
            username="rules_student",
            email="rules_student@example.test",
            role="student",
        )

    def setUp(self):

        self.url = reverse(
            "accounts:analysis_rules"
        )

        self.payload = {
            "rating_1": "2",
            "relevance_1": "3",
            "rating_2": "3",
            "relevance_2": "2",
            "rating_3": "4",
            "relevance_3": "1",
        }

    def login_admin(self):

        self.client.force_login(
            self.administrator
        )

    # =====================================================
    # ACCESS CONTROL
    # =====================================================

    def test_guest_redirected_to_login(self):

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            reverse("accounts:login"),
            response.url,
        )

    def test_student_cannot_view_workspace(self):

        self.client.force_login(self.student)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_student_cannot_submit_simulation(self):

        self.client.force_login(self.student)

        response = self.client.post(
            self.url,
            self.payload,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_administrator_can_view_workspace(self):

        self.login_admin()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "accounts/analysis_rules.html",
        )

        self.assertContains(
            response,
            "Analysis Rules",
        )

    def test_unsupported_method_rejected(self):

        self.login_admin()

        response = self.client.put(self.url)

        self.assertEqual(
            response.status_code,
            405,
        )

    # =====================================================
    # RULE DISPLAY
    # =====================================================

    def test_actual_rule_version_displayed(self):

        self.login_admin()

        response = self.client.get(self.url)

        self.assertEqual(
            response.context["rule_version"],
            rules.RULE_VERSION,
        )

        self.assertContains(
            response,
            rules.RULE_VERSION,
        )

    def test_actual_rating_scale_displayed(self):

        self.login_admin()

        response = self.client.get(self.url)

        rows = response.context["rating_rows"]

        self.assertEqual(
            len(rows),
            5,
        )

        self.assertEqual(
            [item["rating"] for item in rows],
            [1, 2, 3, 4, 5],
        )

    def test_actual_gap_threshold_displayed(self):

        self.login_admin()

        response = self.client.get(self.url)

        self.assertEqual(
            response.context["gap_threshold"],
            rules.GAP_THRESHOLD,
        )

        gaps = [
            item["rating"]
            for item in response.context["rating_rows"]
            if item["is_gap"]
        ]

        self.assertEqual(
            gaps,
            [1, 2, 3],
        )

    def test_actual_relevance_weights_displayed(self):

        self.login_admin()

        response = self.client.get(self.url)

        rows = response.context["relevance_rows"]

        self.assertEqual(
            rows,
            [
                {"label": "Low", "weight": 1},
                {"label": "Medium", "weight": 2},
                {"label": "High", "weight": 3},
            ],
        )

    def test_readiness_levels_displayed(self):

        self.login_admin()

        response = self.client.get(self.url)

        for level in (
            rules.READINESS_NEEDS_STRENGTHENING,
            rules.READINESS_DEVELOPING,
            rules.READINESS_HIGHER,
        ):

            self.assertContains(
                response,
                level,
            )

    def test_disclaimer_displayed(self):

        self.login_admin()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            rules.DISCLAIMER,
        )

    def test_sidebar_navigation_present(self):

        self.login_admin()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            f'href="{self.url}"',
        )

    # =====================================================
    # SIMULATOR BEHAVIOR
    # =====================================================

    def test_initial_get_has_no_simulation(self):

        self.login_admin()

        response = self.client.get(self.url)

        self.assertIsNone(
            response.context["simulation"]
        )

    def test_valid_simulation(self):

        self.login_admin()

        response = self.client.post(
            self.url,
            self.payload,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        result = response.context["simulation"]

        self.assertEqual(
            result["score"],
            Decimal("2.67"),
        )

        self.assertEqual(
            result["level"],
            "Needs strengthening",
        )

        self.assertEqual(
            result["gap_count"],
            2,
        )

    def test_simulation_priority_order(self):

        self.login_admin()

        response = self.client.post(
            self.url,
            self.payload,
        )

        priorities = response.context[
            "simulation"
        ]["priorities"]

        self.assertEqual(
            [
                item["priority_score"]
                for item in priorities
            ],
            [9, 4],
        )

        self.assertEqual(
            [
                item["priority_rank"]
                for item in priorities
            ],
            [1, 2],
        )

    def test_simulation_all_high_ratings(self):

        self.login_admin()

        payload = self.payload.copy()

        for index in range(1, 4):

            payload[f"rating_{index}"] = "5"

        response = self.client.post(
            self.url,
            payload,
        )

        result = response.context["simulation"]

        self.assertEqual(
            result["score"],
            Decimal("5.00"),
        )

        self.assertEqual(
            result["gap_count"],
            0,
        )

        self.assertEqual(
            result["priorities"],
            [],
        )

    def test_simulation_all_low_ratings(self):

        self.login_admin()

        payload = self.payload.copy()

        for index in range(1, 4):

            payload[f"rating_{index}"] = "1"

        response = self.client.post(
            self.url,
            payload,
        )

        result = response.context["simulation"]

        self.assertEqual(
            result["score"],
            Decimal("1.00"),
        )

        self.assertEqual(
            result["gap_count"],
            3,
        )

    # =====================================================
    # INPUT VALIDATION
    # =====================================================

    def test_invalid_rating_rejected(self):

        self.login_admin()

        for invalid in ("0", "6", "-1", "abc"):

            with self.subTest(invalid=invalid):

                payload = self.payload.copy()

                payload["rating_1"] = invalid

                response = self.client.post(
                    self.url,
                    payload,
                )

                self.assertEqual(
                    response.status_code,
                    400,
                )

                self.assertIn(
                    "rating_1",
                    response.context["form"].errors,
                )

                self.assertIsNone(
                    response.context["simulation"]
                )

    def test_invalid_relevance_rejected(self):

        self.login_admin()

        for invalid in ("0", "4", "-1", "abc"):

            with self.subTest(invalid=invalid):

                payload = self.payload.copy()

                payload["relevance_1"] = invalid

                response = self.client.post(
                    self.url,
                    payload,
                )

                self.assertEqual(
                    response.status_code,
                    400,
                )

                self.assertIn(
                    "relevance_1",
                    response.context["form"].errors,
                )

    def test_missing_input_rejected(self):

        self.login_admin()

        payload = self.payload.copy()

        del payload["rating_2"]

        response = self.client.post(
            self.url,
            payload,
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "rating_2",
            response.context["form"].errors,
        )

    # =====================================================
    # DATA SAFETY
    # =====================================================

    def test_simulation_does_not_modify_database(self):

        self.login_admin()

        models = [
            AssessmentSession,
            AssessmentResponse,
            ReadinessResult,
            ReviewRecommendation,
            CompetencyImpact,
        ]

        before = [
            list(model.objects.order_by("pk").values())
            for model in models
        ]

        response = self.client.post(
            self.url,
            self.payload,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        after = [
            list(model.objects.order_by("pk").values())
            for model in models
        ]

        self.assertEqual(
            before,
            after,
        )

    def test_simulator_uses_central_calculation_rules(self):

        form = AnalysisSimulatorForm(
            self.payload
        )

        self.assertTrue(
            form.is_valid()
        )

        result = form.calculate()

        expected = rules.weighted_readiness([
            (2, 3),
            (3, 2),
            (4, 1),
        ])

        self.assertEqual(
            result["score"],
            rules.display_score(expected),
        )

        self.assertEqual(
            result["level"],
            rules.classify_readiness(expected),
        )

    def test_workspace_is_not_cached(self):

        self.login_admin()

        response = self.client.get(self.url)

        self.assertIn(
            "no-store",
            response.headers["Cache-Control"],
        )