"""Auth & user serializers (master prompt §10, Phase 2)."""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "email", "full_name", "role",
            "native_language", "learning_goal", "app_language",
            "is_active", "created_at",
        )
        read_only_fields = ("id", "role", "is_active", "created_at")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            "id", "email", "password", "full_name",
            "native_language", "learning_goal", "app_language",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        password = validated_data.pop("password")
        # Public registration always creates a student (master prompt §4).
        return User.objects.create_user(
            password=password, role=User.Role.STUDENT, **validated_data
        )


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login that also returns the serialized user."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class SocialAuthSerializer(serializers.Serializer):
    """Stub social login payload (Phase 2 — completed later).

    For the MVP stub we accept a verified identity directly. Real token
    verification against Google/Apple is wired in here later without changing
    the endpoint contract.
    """

    provider_uid = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField(required=False, allow_blank=True)
