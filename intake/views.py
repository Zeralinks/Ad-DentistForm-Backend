# intake/views.py
import logging, socket, requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .services.followups import queue_followups_for_lead, deliver_followup_job
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework import status
from .models import Lead, FollowUpTemplate, FollowUpJob
from .serializers import (
    LeadSerializer,                    # public intake (auto-qualifies)
    LeadDashboardSerializer,           # list/read shape for the table
    LeadDashboardCreateSerializer,     # create from dashboard modal
    LeadDashboardPatchSerializer,      # partial updates (status/qualification/etc.)
    FollowUpTemplateSerializer,
    FollowUpJobSerializer,
)

log = logging.getLogger(__name__)

# ---------- PUBLIC INTAKE (unchanged) ----------
@api_view(["POST"])
@permission_classes([AllowAny])
def lead_view(request):
    serializer = LeadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    lead = serializer.save()
    log.info("Lead saved: %s", lead.email)

    zapier_hook = getattr(settings, "ZAPIER_HOOK", "").strip()
    if zapier_hook:
        try:
            requests.post(zapier_hook, json=LeadSerializer(lead).data, timeout=5)
            log.info("Lead forwarded to Zapier")
        except (socket.gaierror, requests.RequestException) as exc:
            log.warning("Zapier forward failed: %s", exc)

    return Response(LeadSerializer(lead).data, status=status.HTTP_201_CREATED)


# ---------- DASHBOARD: LIST + CREATE ----------
class LeadListCreateView(APIView):
    # Use AllowAny while testing; switch to IsAuthenticated once JWT works
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Lead.objects.all().order_by("-submitted_at")
        data = LeadDashboardSerializer(qs, many=True).data
        return Response(data, status=200)

    def post(self, request):
        ser = LeadDashboardCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        lead = ser.save()
        prev = lead.qualification_status
        ser.save()
        lead.refresh_from_db()
        if lead.qualification_status != prev:
            queue_followups_for_lead(lead)
        return Response(LeadDashboardSerializer(lead).data, status=200)
    

# ---------- DASHBOARD: READ ONE + PATCH ----------
class LeadDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        return Response(LeadDashboardSerializer(lead).data, status=200)

    def patch(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        ser = LeadDashboardPatchSerializer(lead, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        ser.save()
        # return full row shape for the table
        return Response(LeadDashboardSerializer(lead).data, status=200)

class FollowUpTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = FollowUpTemplate.objects.all().order_by("-created_at")
    serializer_class = FollowUpTemplateSerializer

class FollowUpJobViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowUpJobSerializer

    def get_queryset(self):
        qs = FollowUpJob.objects.select_related("lead","template").order_by("-scheduled_for")
        status_q = self.request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)
        return qs

    @action(detail=True, methods=["post"])
    def send_now(self, request, pk=None):
        job = self.get_queryset().get(pk=pk)
        # even if scheduled later, allow manual send now
        deliver_followup_job(job)
        return Response(FollowUpJobSerializer(job).data, status=200)

    @action(detail=False, methods=["post"])
    def schedule(self, request):
        """
        Body: { "lead": <uuid>, "template": <id>, "delay_hours": 0 }
        """
        lead_id = request.data.get("lead")
        tpl_id  = request.data.get("template")
        delay   = int(request.data.get("delay_minutes", 0))
        lead = Lead.objects.get(pk=lead_id)
        tpl  = FollowUpTemplate.objects.get(pk=tpl_id)
        when = timezone.now() + timezone.timedelta(minutes=max(0, delay))
        job = FollowUpJob.objects.create(lead=lead, template=tpl, scheduled_for=when)
        return Response(FollowUpJobSerializer(job).data, status=201)

