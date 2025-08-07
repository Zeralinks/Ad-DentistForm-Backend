from django.contrib import admin
from .models import Lead

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "submitted_at", "tags")
    search_fields = ("first_name", "last_name", "email", "phone")
    list_filter   = ("urgency", "insurance")
    ordering = ("-submitted_at",)