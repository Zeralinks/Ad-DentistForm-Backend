# intake/serializers.py
from rest_framework import serializers
from .models import Lead
from .service.qualification import qualify

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
