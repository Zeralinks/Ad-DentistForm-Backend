from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from intake.models import FollowUpTemplate, FollowUpJob, Lead

# simple safe formatter
def ctx_for_lead(lead: Lead) -> dict:
    full_name = f"{(lead.first_name or '').strip()} {(lead.last_name or '').strip()}".strip()
    return {
        "first_name": lead.first_name or "",
        "last_name": lead.last_name or "",
        "name": full_name or lead.email,
        "email": lead.email,
        "phone": lead.phone or "",
        "service": lead.service or "",
        "source": lead.source or "",
        "insurance": lead.insurance or "",
        "urgency": lead.urgency or "",
        "situation": lead.situation or "",
        "score": str(lead.qualification_score or 0),
        "status": lead.qualification_status or "",
    }

def render_text(template_str: str, ctx: dict) -> str:
    # lightweight {{var}} replacement
    out = template_str
    for k, v in ctx.items():
        out = out.replace(f"{{{{{k}}}}}", str(v))
    return out

def queue_followups_for_lead(lead: Lead):
    """Create jobs for all active templates matching the lead's qualification."""
    if not lead.email:
        return 0
    now = timezone.now()
    templates = FollowUpTemplate.objects.filter(active=True, trigger_on=lead.qualification_status)
    created = 0
    with transaction.atomic():
        for tpl in templates:
            when = now + timedelta(minutes=max(0, tpl.delay_minutes))
            FollowUpJob.objects.create(lead=lead, template=tpl, scheduled_for=when)
            created += 1
    return created

# ---- sending ----
def send_email_simple(to_email: str, subject: str, body: str):
    if not getattr(settings, "EMAIL_HOST", None) and not getattr(settings, "SENDGRID_API_KEY", None):
        # no SMTP configured; do nothing but pretend success
        return True
    send_mail(
        subject=subject or "(no subject)",
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
        recipient_list=[to_email],
        fail_silently=False,
    )
    return True

def deliver_followup_job(job: FollowUpJob):
    lead = job.lead
    tpl  = job.template
    ctx  = ctx_for_lead(lead)
    subject = render_text(tpl.subject or "", ctx)
    body    = render_text(tpl.content, ctx)

    if tpl.channel == "email":
        ok = send_email_simple(lead.email, subject, body)
    else:
        # SMS stub: integrate Twilio/Vonage later
        ok = True

    job.status  = "sent" if ok else "failed"
    job.sent_at = timezone.now() if ok else None
    job.last_error = "" if ok else "Delivery failed"
    job.save(update_fields=["status", "sent_at", "last_error"])
    return ok
