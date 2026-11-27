from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path(
        "",
        RedirectView.as_view(
            pattern_name="accounts:dashboard",
            permanent=False,
        ),
        name="home",
    ),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
]


# =========================================================
# CUSTOM HTTP ERROR HANDLERS
# =========================================================

handler400 = "accounts.error_views.bad_request"
handler403 = "accounts.error_views.permission_denied"
handler404 = "accounts.error_views.page_not_found"
handler500 = "accounts.error_views.server_error"
