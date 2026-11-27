
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView


urlpatterns = [
    path(
        "",
        TemplateView.as_view(
            template_name="accounts/landing.html"
        ),
        name="home",
    ),

    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "accounts/",
        include("accounts.urls"),
    ),

    path(
        "assessments/",
        include("assessments.urls"),
    ),
]


# Custom HTTP error handlers

handler400 = "accounts.error_views.bad_request"
handler403 = "accounts.error_views.permission_denied"
handler404 = "accounts.error_views.page_not_found"
handler500 = "accounts.error_views.server_error"
