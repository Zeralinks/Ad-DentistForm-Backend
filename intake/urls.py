from django.urls import path, include
from .views import lead_view, LeadListCreateView, LeadDetailView
from intake.views import FollowUpTemplateViewSet, FollowUpJobViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'followups/templates', FollowUpTemplateViewSet, basename='fu-templates')
router.register(r'followups/jobs', FollowUpJobViewSet, basename='fu-jobs')

urlpatterns = [
    path("lead/", lead_view, name="lead-intake"),
    path("leads/", LeadListCreateView.as_as_view(), name="leads"),
    path("leads/<int:pk>/", LeadDetailView.as_as_view(), name="lead-detail"),
    path("", include(router.urls)),
]