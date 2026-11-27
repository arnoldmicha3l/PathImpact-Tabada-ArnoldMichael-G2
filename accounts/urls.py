
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from . import administrator_views
from . import academic_views


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
        "administrator/programs/",
        academic_views.programs,
        name="programs",
    ),

    path(
        "administrator/programs/new/",
        academic_views.program_edit,
        name="program_create",
    ),

    path(
        "administrator/programs/<int:pk>/edit/",
        academic_views.program_edit,
        name="program_edit",
    ),

    path(
        "administrator/programs/<int:pk>/delete/",
        academic_views.program_delete,
        name="program_delete",
    ),

    path(
        "administrator/subjects/",
        academic_views.subjects,
        name="subjects",
    ),

    path(
        "administrator/subjects/new/",
        academic_views.subject_edit,
        name="subject_create",
    ),

    path(
        "administrator/subjects/<int:pk>/edit/",
        academic_views.subject_edit,
        name="subject_edit",
    ),

    path(
        "administrator/subjects/<int:pk>/delete/",
        academic_views.subject_delete,
        name="subject_delete",
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
