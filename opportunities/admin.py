from django.contrib import admin

from .models import Application, Opportunity


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "event_date", "deadline", "slots", "status")
    list_filter = ("category", "status")
    search_fields = ("title", "location")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "opportunity", "status", "created_at")
    list_filter = ("status",)
