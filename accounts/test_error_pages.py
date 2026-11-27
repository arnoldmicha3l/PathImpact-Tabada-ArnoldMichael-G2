
from django.core.exceptions import (
    PermissionDenied,
    SuspiciousOperation,
)

from django.http import Http404

from django.test import (
    SimpleTestCase,
    Client,
    override_settings,
)

from django.urls import (
    path,
    get_resolver,
)

from . import error_views


# Test-only views.
# These are not registered in production URLs.

def trigger_bad_request(request):

    raise SuspiciousOperation(
        "PRIVATE_BAD_REQUEST_DETAIL"
    )


def trigger_permission_denied(request):

    raise PermissionDenied(
        "PRIVATE_PERMISSION_DETAIL"
    )


def trigger_not_found(request):

    raise Http404(
        "PRIVATE_NOT_FOUND_DETAIL"
    )


def trigger_server_error(request):

    raise RuntimeError(
        "PRIVATE_SERVER_ERROR_DETAIL"
    )


# Isolated test URL configuration.

urlpatterns = [

    path(
        "test-errors/400/",
        trigger_bad_request,
    ),

    path(
        "test-errors/403/",
        trigger_permission_denied,
    ),

    path(
        "test-errors/404/",
        trigger_not_found,
    ),

    path(
        "test-errors/500/",
        trigger_server_error,
    ),
]


handler400 = error_views.bad_request

handler403 = error_views.permission_denied

handler404 = error_views.page_not_found

handler500 = error_views.server_error


@override_settings(
    DEBUG=False,
    ROOT_URLCONF=__name__,
)
class CustomErrorPageTests(SimpleTestCase):

    def setUp(self):

        self.client = Client(
            raise_request_exception=False
        )

    def test_bad_request_page(self):

        response = self.client.get(
            "/test-errors/400/"
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertTemplateUsed(
            response,
            "errors/400.html",
        )

        self.assertContains(
            response,
            "Invalid request",
            status_code=400,
        )

    def test_permission_denied_page(self):

        response = self.client.get(
            "/test-errors/403/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertTemplateUsed(
            response,
            "errors/403.html",
        )

        self.assertContains(
            response,
            "Access denied",
            status_code=403,
        )

    def test_not_found_page(self):

        response = self.client.get(
            "/test-errors/404/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTemplateUsed(
            response,
            "errors/404.html",
        )

    def test_unknown_url_returns_custom_404(self):

        response = self.client.get(
            "/this-page-does-not-exist/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTemplateUsed(
            response,
            "errors/404.html",
        )

    def test_server_error_page(self):

        response = self.client.get(
            "/test-errors/500/"
        )

        self.assertEqual(
            response.status_code,
            500,
        )

        self.assertTemplateUsed(
            response,
            "errors/500.html",
        )

        self.assertContains(
            response,
            "Something went wrong",
            status_code=500,
        )

    def test_private_error_details_not_exposed(self):

        cases = [

            (
                400,
                "PRIVATE_BAD_REQUEST_DETAIL",
            ),

            (
                403,
                "PRIVATE_PERMISSION_DETAIL",
            ),

            (
                404,
                "PRIVATE_NOT_FOUND_DETAIL",
            ),

            (
                500,
                "PRIVATE_SERVER_ERROR_DETAIL",
            ),
        ]

        for status, private_detail in cases:

            with self.subTest(status=status):

                response = self.client.get(
                    f"/test-errors/{status}/"
                )

                self.assertNotContains(
                    response,
                    private_detail,
                    status_code=status,
                )

                self.assertNotContains(
                    response,
                    "Traceback",
                    status_code=status,
                )

    def test_error_pages_have_homepage_link(self):

        for status in (400, 403, 404, 500):

            with self.subTest(status=status):

                response = self.client.get(
                    f"/test-errors/{status}/"
                )

                self.assertContains(
                    response,
                    'href="/"',
                    status_code=status,
                )

                self.assertContains(
                    response,
                    "Return to homepage",
                    status_code=status,
                )

    def test_error_pages_use_pathimpact_branding(self):

        for status in (400, 403, 404, 500):

            with self.subTest(status=status):

                response = self.client.get(
                    f"/test-errors/{status}/"
                )

                self.assertContains(
                    response,
                    "PathImpact",
                    status_code=status,
                )

    def test_error_pages_are_not_cached(self):

        for status in (400, 403, 404, 500):

            with self.subTest(status=status):

                response = self.client.get(
                    f"/test-errors/{status}/"
                )

                self.assertIn(
                    "no-store",
                    response.headers["Cache-Control"],
                )


@override_settings(
    DEBUG=False,
    ROOT_URLCONF="config.urls",
)
class ProductionErrorConfigurationTests(SimpleTestCase):

    def test_production_error_handlers_registered(self):

        resolver = get_resolver("config.urls")

        expected = {

            400: error_views.bad_request,

            403: error_views.permission_denied,

            404: error_views.page_not_found,

            500: error_views.server_error,
        }

        for status, handler in expected.items():

            with self.subTest(status=status):

                self.assertEqual(
                    resolver.resolve_error_handler(status),
                    handler,
                )

    def test_production_unknown_url_returns_custom_404(self):

        response = self.client.get(
            "/pathimpact-nonexistent-page-123456/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTemplateUsed(
            response,
            "errors/404.html",
        )
