from django.db import models

class Lead(models.Model):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    zip_code = models.CharField(max_length=10, blank=True)
    insurance = models.CharField(max_length=80, blank=True)
    situation = models.CharField(max_length=120, blank=True)
    urgency = models.CharField(max_length=20, blank=True)
    symptoms = models.TextField(blank=True, default="")
    solutions = models.TextField(blank=True, default="")
    tags = models.TextField(blank=True, default="")
    financing = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    hipaa = models.BooleanField(default=False)
    tags = models.TextField(max_length=40, default=list, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"
