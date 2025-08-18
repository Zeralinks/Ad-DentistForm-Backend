# intake/views.py
import logging, socket, requests
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .serializers import LeadSerializer

log = logging.getLogger(__name__)

@api_view(["POST"])
@permission_classes([AllowAny])
def lead_view(request):
    serializer = LeadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    lead = serializer.save()
    log.info("Lead saved: %s", lead.email)

    # Optional: forward to Zapier if you still want that behavior later
    zapier_hook = getattr(settings, "ZAPIER_HOOK", "").strip()
    if zapier_hook:
        try:
            requests.post(zapier_hook, json=LeadSerializer(lead).data, timeout=5)
            log.info("Lead forwarded to Zapier")
        except (socket.gaierror, requests.RequestException) as exc:
            log.warning("Zapier forward failed: %s", exc)

    # Return data the frontend can use right away
    return Response(LeadSerializer(lead).data, status=status.HTTP_201_CREATED)
