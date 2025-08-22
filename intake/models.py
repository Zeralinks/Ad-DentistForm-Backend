# intake/models.py
from django.db import models

STATUS_CHOICES = [
    ("new", "New"),
    ("contacted", "Contacted"),
    ("follow-up", "Follow-up"),
    ("booked", "Booked"),
]

class Lead(models.Model):
    first_name  = models.CharField(max_length=80)
    last_name   = models.CharField(max_length=80)
    email       = models.EmailField()
    phone       = models.CharField(max_length=30)
    zip_code    = models.CharField(max_length=10, blank=True)
    insurance   = models.CharField(max_length=80, blank=True)
    situation   = models.CharField(max_length=120, blank=True)
    urgency     = models.CharField(max_length=20, blank=True)

    # Store lists as JSON so you’re not fighting CSV strings
    symptoms    = models.JSONField(default=list, blank=True)
    solutions   = models.JSONField(default=list, blank=True)
    tags        = models.JSONField(default=list, blank=True)

    financing   = models.CharField(max_length=20, blank=True)
    notes       = models.TextField(blank=True)
    hipaa       = models.BooleanField(default=False)

    source      = models.CharField(max_length=50, blank=True, default="")
    service     = models.CharField(max_length=80, blank=True, default="")
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    last_contact = models.DateTimeField(null=True, blank=True)

    # Auto-qualification results
    qualification_status  = models.CharField(
        max_length=20,
        choices=[("qualified","Qualified"),("nurture","Nurture"),("disqualified","Disqualified")],
        default="nurture"
    )
    qualification_score   = models.IntegerField(default=0)
    qualification_reasons = models.JSONField(default=list, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"

# add to the bottom of models.py

class FollowUpTemplate(models.Model):
    CHANNELS = [("email", "Email"), ("sms", "SMS")]
    TRIGGERS = [("qualified","Qualified"), ("nurture","Nurture"), ("disqualified","Disqualified")]

    name        = models.CharField(max_length=120)
    channel     = models.CharField(max_length=10, choices=CHANNELS, default="email")
    subject     = models.CharField(max_length=200, blank=True)  # email only
    content     = models.TextField()
    delay_minutes = models.IntegerField(default=0)  # 0 = immediate
    trigger_on  = models.CharField(max_length=20, choices=TRIGGERS)
    active      = models.BooleanField(default=True)

    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} [{self.trigger_on}/{self.channel}]"

class FollowUpJob(models.Model):
    STATUSES = [("pending","Pending"), ("sent","Sent"), ("failed","Failed"), ("cancelled","Cancelled")]

    lead          = models.ForeignKey("Lead", on_delete=models.CASCADE, related_name="followups")
    template      = models.ForeignKey("FollowUpTemplate", on_delete=models.CASCADE)
    scheduled_for = models.DateTimeField()
    status        = models.CharField(max_length=12, choices=STATUSES, default="pending")
    last_error    = models.TextField(blank=True)
    sent_at       = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["status", "scheduled_for"])]
