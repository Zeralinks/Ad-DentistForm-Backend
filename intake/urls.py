from django.urls import path
from .views import lead_view

urlpatterns = [
    path("lead/", lead_view, name="lead"),
]
# intake/urls.py
# This file defines the URL patterns for the intake app, mapping the lead endpoint to the lead_view function.
# It allows the lead_view to handle POST requests for creating new leads.   