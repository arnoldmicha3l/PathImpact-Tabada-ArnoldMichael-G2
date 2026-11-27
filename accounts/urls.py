
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from . import administrator_views


app_name = "accounts"


urlpatterns = [

    path(
        "register/",
        views.register,
        name="register",
    ),

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            next_page=reverse_lazy("accounts:dashboard"),
            redirect_authenticated_user=True,
        ),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(
            next_page=reverse_lazy("accounts:login"),
        ),
        name="logout",
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),

    path(
        "dashboard/student/",
        views.student_dashboard,
        name="student_dashboard",
    ),

    path(
        "dashboard/administrator/",
        administrator_views.dashboard,
        name="administrator_dashboard",
    ),

    path(
        "profile/",
        views.profile,
        name="profile",
    ),

    path(
        "profile/edit/",
        views.edit_profile,
        name="edit_profile",
    ),

]
