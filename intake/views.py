# intake/views.py
import logging, socket, requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Lead
from .serializers import (
    LeadSerializer,                    # public intake (auto-qualifies)
    LeadDashboardSerializer,           # list/read shape for the table
    LeadDashboardCreateSerializer,     # create from dashboard modal
    LeadDashboardPatchSerializer,      # partial updates (status/qualification/etc.)
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
        return Response(LeadDashboardSerializer(lead).data, status=201)


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
