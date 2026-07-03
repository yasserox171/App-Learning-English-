"""Progress / placement / certificate serializers (Phase 5)."""
from rest_framework import serializers

from .models import Certificate, Progress


class ProgressUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Progress.Status.choices)
    score = serializers.IntegerField(required=False, min_value=0)
    time_spent = serializers.IntegerField(required=False, min_value=0)


class PlacementSubmitSerializer(serializers.Serializer):
    # answers maps question id -> selected option index
    answers = serializers.DictField(child=serializers.IntegerField())


class CertificateSerializer(serializers.ModelSerializer):
    level_code = serializers.CharField(source="level.code", read_only=True)
    level_name = serializers.CharField(source="level.name", read_only=True)

    class Meta:
        model = Certificate
        fields = (
            "id", "certificate_number", "level_code", "level_name",
            "pdf_url", "issued_at",
        )


class PhaseSerializer(serializers.Serializer):
    phase = serializers.IntegerField(min_value=1, max_value=5)
    score = serializers.FloatField(required=False, default=0)


class AssessmentSubmitSerializer(serializers.Serializer):
    # answers maps exercise id -> that template's answer object
    answers = serializers.DictField(child=serializers.DictField())


class RatingSerializer(serializers.Serializer):
    rating = serializers.ChoiceField(choices=["up", "down"])


class VocabResultSerializer(serializers.Serializer):
    item_id = serializers.UUIDField()
    correct = serializers.BooleanField()


class VocabTrackSerializer(serializers.Serializer):
    results = VocabResultSerializer(many=True)
