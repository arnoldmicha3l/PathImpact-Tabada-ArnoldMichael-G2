from django.urls import path

from . import views

app_name = "opportunities"

urlpatterns = [
    path("", views.opportunity_list, name="list"),
    path("new/", views.opportunity_create, name="create"),
    path("<int:pk>/", views.opportunity_detail, name="detail"),
    path("<int:pk>/edit/", views.opportunity_edit, name="edit"),
    path("<int:pk>/delete/", views.opportunity_delete, name="delete"),
    path("<int:pk>/apply/", views.apply, name="apply"),
    path("applications/", views.my_applications, name="my_applications"),
    path("applications/<int:pk>/edit/", views.application_edit, name="application_edit"),
    path("applications/<int:pk>/withdraw/", views.application_withdraw, name="application_withdraw"),
    path("review/", views.review_list, name="review_list"),
    path("review/<int:pk>/", views.review_application, name="review"),
]
