from rest_framework import serializers
from .models import Lead
import ast

class LeadSerializer(serializers.ModelSerializer):
    # incoming camelCase aliases ------------------------------
    firstName  = serializers.CharField(source="first_name")
    lastName   = serializers.CharField(source="last_name")
    zip        = serializers.CharField(source="zip_code", allow_blank=True)
    # lists arrive as CSV  ("Pain,Discomfort")
    symptoms   = serializers.CharField(write_only=True, required=False, allow_blank=True)
    solutions  = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tags       = serializers.CharField(write_only=True, required=False, allow_blank=True)
    hipaa      = serializers.CharField(write_only=True)  # "true"/"false" string

    class Meta:
        model  = Lead
        # expose DB fields when serializing out
        fields = [
            "firstName","lastName","email","phone",
            "zip","insurance","situation","urgency",
            "symptoms","solutions","financing","notes",
            "hipaa","tags"
        ]

    def create(self, validated):
        """Convert CSV strings → lists & bool before saving."""
        csv_to_list = lambda s: [x.strip() for x in s.split(",") if x.strip()]
        validated["symptoms"]  = csv_to_list(validated.pop("symptoms", ""))
        validated["solutions"] = csv_to_list(validated.pop("solutions", ""))
        validated["tags"]      = csv_to_list(validated.pop("tags", ""))
        validated["hipaa"]     = validated["hipaa"].lower() == "true"
        return super().create(validated)
        # This method converts the incoming data to the appropriate types
        # before saving it to the database, ensuring that lists and booleans