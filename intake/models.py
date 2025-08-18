# intake/models.py
from django.db import models

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
