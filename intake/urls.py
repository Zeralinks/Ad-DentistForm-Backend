# intake/urls.py
from django.urls import path
from .views import lead_view, LeadListCreateView, LeadDetailView

urlpatterns = [
    path("lead/", lead_view, name="lead-intake"),                 # POST (public form)
    path("leads/", LeadListCreateView.as_view(), name="leads"),   # GET list, POST create
    path("leads/<int:pk>/", LeadDetailView.as_view(), name="lead-detail"),  # GET, PATCH
]
