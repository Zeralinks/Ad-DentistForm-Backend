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

    # NEW: match your table’s fields
    firstName = serializers.CharField(source="first_name", read_only=True)
    lastName  = serializers.CharField(source="last_name", read_only=True)
    insurance = serializers.CharField(read_only=True)
    urgency   = serializers.CharField(read_only=True)
    situation = serializers.CharField(read_only=True)

    # Your table reads *_status/score/reasons directly
    qualification_status  = serializers.CharField(read_only=True)
    qualification_score   = serializers.IntegerField(read_only=True)
    qualification_reasons = serializers.ListField(child=serializers.CharField(), read_only=True)

    # The table uses submitted_at (snake) — keep both for compatibility
    submitted_at = serializers.DateTimeField(source="submitted_at", read_only=True)

    # actions use tags and notes
    tags  = serializers.ListField(child=serializers.CharField(), read_only=True)
    notes = serializers.CharField(read_only=True)

    class Meta:
        model = Lead
        fields = [
            # identity
            "id", "firstName", "lastName", "name",
            # contact
            "email", "phone",
            # lead info
            "insurance", "urgency", "situation", "source", "service", "status", "notes", "tags",
            # qualification (both alias + raw fields your UI reads)
            "qualification", "qualification_status", "qualification_score", "qualification_reasons",
            # dates (both)
            "createdAt", "submitted_at", "lastContact",
        ]

    def get_name(self, obj):
        return f"{(obj.first_name or '').strip()} {(obj.last_name or '').strip()}".strip()


class LeadDashboardCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Lead
        fields = ["name", "first_name", "last_name", "email", "phone", "source", "service", "status", "notes"]

    def create(self, data):
        name = data.pop("name", "").strip()
        if name and not (data.get("first_name") or data.get("last_name")):
            parts = name.split()
            data["first_name"] = parts[0]
            data["last_name"]  = " ".join(parts[1:]) if len(parts) > 1 else ""
        # dashboard add = no qualification run here (keep default “nurture”)
        return super().create(data)

class LeadDashboardPatchSerializer(serializers.ModelSerializer):
    qualification = serializers.CharField(source="qualification_status", required=False)
    lastContact = serializers.DateTimeField(source="last_contact", required=False, allow_null=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)


    class Meta:
        model = Lead
        fields = ["status", "qualification", "lastContact", "notes", "service", "source", "tags"]
        extra_kwargs = {f: {"required": False} for f in fields}