# intake/serializers.py
from rest_framework import serializers
from .models import Lead
from .services.qualification import qualify

class LeadSerializer(serializers.ModelSerializer):
    # Accept camelCase from your form
    firstName = serializers.CharField(source="first_name")
    lastName  = serializers.CharField(source="last_name")
    zip       = serializers.CharField(source="zip_code", allow_blank=True, required=False)

    # These arrive as CSV strings in your FormData; parse → lists
    symptoms  = serializers.CharField(write_only=True, required=False, allow_blank=True)
    solutions = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tags      = serializers.CharField(write_only=True, required=False, allow_blank=True)

    hipaa     = serializers.BooleanField()

    # Expose read-only qualification back to the client
    qualification_status  = serializers.CharField(read_only=True)
    qualification_score   = serializers.IntegerField(read_only=True)
    qualification_reasons = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Lead
        fields = [
            "firstName","lastName","email","phone",
            "zip","insurance","situation","urgency",
            "symptoms","solutions","financing","notes","hipaa","tags",
            "qualification_status","qualification_score","qualification_reasons"
        ]

    def create(self, validated_data):
        # pull out raw CSVs (if present) and split → lists
        def csv_to_list(val):
            if not val: return []
            if isinstance(val, list): return val
            return [x.strip() for x in str(val).split(",") if x.strip()]

        symptoms  = csv_to_list(validated_data.pop("symptoms", ""))
        solutions = csv_to_list(validated_data.pop("solutions", ""))
        tags_in   = csv_to_list(validated_data.pop("tags", ""))

        # attach parsed lists back
        validated_data["symptoms"]  = symptoms
        validated_data["solutions"] = solutions
        validated_data["tags"]      = tags_in

        # Run qualification on the server
        q = qualify(validated_data)

        # Merge qualification + server tags (don’t trust client tags alone)
        server_tags = q.pop("server_tags", [])
        final_tags  = list({*tags_in, *server_tags})
        validated_data["tags"] = final_tags

        # Persist
        lead = Lead.objects.create(**validated_data, **q)
        return lead

# intake/serializers.py
class LeadDashboardSerializer(serializers.ModelSerializer):
    # existing
    name          = serializers.SerializerMethodField()
    qualification = serializers.CharField(source="qualification_status", read_only=True)
    createdAt     = serializers.DateTimeField(source="submitted_at", read_only=True)
    lastContact   = serializers.DateTimeField(source="last_contact", required=False, allow_null=True)

    # NEW fields (these are fine)
    firstName = serializers.CharField(source="first_name", read_only=True)
    lastName  = serializers.CharField(source="last_name", read_only=True)
    insurance = serializers.CharField(read_only=True)
    urgency   = serializers.CharField(read_only=True)
    situation = serializers.CharField(read_only=True)

    qualification_status  = serializers.CharField(read_only=True)
    qualification_score   = serializers.IntegerField(read_only=True)
    qualification_reasons = serializers.ListField(child=serializers.CharField(), read_only=True)

    submitted_at = serializers.DateTimeField(read_only=True)

    tags  = serializers.ListField(child=serializers.CharField(), read_only=True)
    notes = serializers.CharField(read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id", "firstName", "lastName", "name",
            "email", "phone",
            "insurance", "urgency", "situation", "source", "service", "status", "notes", "tags",
            "qualification", "qualification_status", "qualification_score", "qualification_reasons",
            "createdAt", "submitted_at", "lastContact",
        ]

    def get_name(self, obj):
        return f"{(obj.first_name or '').strip()} {(obj.last_name or '').strip()}".strip()



# intake/serializers.py

class LeadDashboardCreateSerializer(serializers.ModelSerializer):
    # let users type a single "name" or split fields
    name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    # OPTIONAL incoming fields when creating manually
    qualification = serializers.CharField(source="qualification_status", required=False, allow_blank=True)
    qualification_score = serializers.IntegerField(required=False)
    qualification_reasons = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    tags = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Lead
        fields = [
            "name", "first_name", "last_name",
            "email", "phone",
            "source", "service", "status",
            "insurance", "urgency", "situation",
            "notes", "tags",
            "qualification", "qualification_score", "qualification_reasons",
        ]

    def create(self, data):
        # support "name" → split into first/last if those are empty
        name = (data.pop("name", "") or "").strip()
        if name and not (data.get("first_name") or data.get("last_name")):
            parts = name.split()
            data["first_name"] = parts[0]
            data["last_name"]  = " ".join(parts[1:]) if len(parts) > 1 else ""

        # defaults if not provided
        data.setdefault("qualification_status", "nurture")
        data.setdefault("qualification_score", 0)
        data.setdefault("qualification_reasons", [])
        data.setdefault("tags", [])

        return super().create(data)

class LeadDashboardPatchSerializer(serializers.ModelSerializer):
    qualification = serializers.CharField(source="qualification_status", required=False)
    lastContact = serializers.DateTimeField(source="last_contact", required=False, allow_null=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)


    class Meta:
        model = Lead
        fields = ["status", "qualification", "lastContact", "notes", "service", "source", "tags"]
        extra_kwargs = {f: {"required": False} for f in fields}


from rest_framework import serializers
from .models import FollowUpTemplate, FollowUpJob

class FollowUpTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpTemplate
        fields = "__all__"

class FollowUpJobSerializer(serializers.ModelSerializer):
    lead_name = serializers.SerializerMethodField()
    email     = serializers.CharField(source="lead.email", read_only=True)

    class Meta:
        model = FollowUpJob
        fields = ["id","status","scheduled_for","sent_at","last_error","template","lead","lead_name","email"]

    def get_lead_name(self, obj):
        f, l = (obj.lead.first_name or "").strip(), (obj.lead.last_name or "").strip()
        return (f" {l}".join([f, l])).strip() or obj.lead.email
