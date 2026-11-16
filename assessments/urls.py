from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="assessment_index"),
    path("new/", views.edit, name="assessment_create"),
    path("<int:pk>/", views.detail, name="assessment_detail"),
    path("<int:pk>/edit/", views.edit, name="assessment_edit"),
    path("<int:pk>/delete/", views.delete, name="assessment_delete"),
]
