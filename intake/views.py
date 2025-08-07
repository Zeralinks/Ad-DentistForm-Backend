# views.py
import logging, socket, requests
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .serializers import LeadSerializer

log = logging.getLogger(__name__)          # use Django’s logging config


@api_view(["POST"])
@permission_classes([AllowAny])
def lead_view(request):
    """
    Receive lead data → validate & save → (optionally) forward to Zapier.
    Always returns 204 on success, even if the Zapier call fails.
    """
    serializer = LeadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()
    log.info("Lead saved: %s", serializer.data.get("email", "<no-email>"))

    # ── Forward to Zapier if hook configured ─────────────────────────────
    zapier_hook = getattr(settings, "ZAPIER_HOOK", "").strip()
    if not zapier_hook:
        log.debug("ZAPIER_HOOK not set → skipping Zapier forward")
        return Response({"detail": "lead accepted"}, status=status.HTTP_204_NO_CONTENT)

    try:
        requests.post(zapier_hook, json=serializer.data, timeout=5)
        log.info("Lead forwarded to Zapier")
    except socket.gaierror:
        log.warning("DNS resolution failed for Zapier; lead kept locally")
    except requests.RequestException as exc:
        log.warning("Zapier forward failed: %s", exc)

    return Response({"detail": "lead accepted"}, status=status.HTTP_204_NO_CONTENT)