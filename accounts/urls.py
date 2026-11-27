from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from . import administrator_views
from . import academic_views
from . import prerequisite_views
from . import competency_views
from . import mapping_views
from . import impact_views
from . import user_management_views
from . import report_views


app_name = "accounts"


from . import analysis_rule_views


urlpatterns = [

    path(
        "administrator/analysis-rules/",
        analysis_rule_views.analysis_rules,
        name="analysis_rules",
    ),


    # ========================================
    # AUTHENTICATION
    # ========================================

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

    # ========================================
    # DASHBOARDS
    # ========================================

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

    # ========================================
    # ACADEMIC PROGRAMS
    # ========================================

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

    # ========================================
    # ACADEMIC SUBJECTS
    # ========================================

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

    # ========================================
    # PREREQUISITES
    # ========================================

    path(
        "administrator/prerequisites/",
        prerequisite_views.prerequisites,
        name="prerequisites",
    ),

    path(
        "administrator/prerequisites/new/",
        prerequisite_views.prerequisite_edit,
        name="prerequisite_create",
    ),

    path(
        "administrator/prerequisites/<int:pk>/edit/",
        prerequisite_views.prerequisite_edit,
        name="prerequisite_edit",
    ),

    path(
        "administrator/prerequisites/<int:pk>/delete/",
        prerequisite_views.prerequisite_delete,
        name="prerequisite_delete",
    ),

    # ========================================
    # COMPETENCIES
    # ========================================

    path(
        "administrator/competencies/",
        competency_views.competencies,
        name="competencies",
    ),

    path(
        "administrator/competencies/new/",
        competency_views.competency_edit,
        name="competency_create",
    ),

    path(
        "administrator/competencies/<int:pk>/edit/",
        competency_views.competency_edit,
        name="competency_edit",
    ),

    path(
        "administrator/competencies/<int:pk>/delete/",
        competency_views.competency_delete,
        name="competency_delete",
    ),

    # ========================================
    # COMPETENCY MAPPINGS
    # ========================================

    path(
        "administrator/mappings/",
        mapping_views.mappings,
        name="mappings",
    ),

    path(
        "administrator/mappings/new/",
        mapping_views.mapping_edit,
        name="mapping_create",
    ),

    path(
        "administrator/mappings/<int:pk>/edit/",
        mapping_views.mapping_edit,
        name="mapping_edit",
    ),

    path(
        "administrator/mappings/<int:pk>/delete/",
        mapping_views.mapping_delete,
        name="mapping_delete",
    ),

    # ========================================
    # COMPETENCY IMPACTS
    # Phase 07H.1
    # ========================================

    path(
        "administrator/impacts/",
        impact_views.impacts,
        name="impacts",
    ),

    path(
        "administrator/impacts/new/",
        impact_views.impact_edit,
        name="impact_create",
    ),

    path(
        "administrator/impacts/<int:pk>/edit/",
        impact_views.impact_edit,
        name="impact_edit",
    ),

    path(
        "administrator/impacts/<int:pk>/delete/",
        impact_views.impact_delete,
        name="impact_delete",
    ),

    # ========================================
    # USER MANAGEMENT
    # ========================================

    path(
        "administrator/users/",
        user_management_views.users,
        name="users",
    ),

    path(
        "administrator/users/<int:pk>/",
        user_management_views.user_detail,
        name="user_detail",
    ),

    path(
        "administrator/users/<int:pk>/status/<str:action>/",
        user_management_views.user_status,
        name="user_status",
    ),

    # ========================================
    # ASSESSMENT REPORTS
    # ========================================

    path(
        "administrator/reports/",
        report_views.assessment_reports,
        name="assessment_reports",
    ),

    path(
        "administrator/reports/export/",
        report_views.assessment_reports_export,
        name="assessment_reports_export",
    ),

    # ========================================
    # ACCOUNT MANAGEMENT
    # ========================================

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