"""Auth views (master prompt §10, Phase 2)."""
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import SocialAuth
from .serializers import (
    EmailTokenObtainPairSerializer,
    RegisterSerializer,
    SocialAuthSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class _SocialLoginBase(APIView):
    """Shared logic for social login stubs."""

    permission_classes = [permissions.AllowAny]
    provider = ""

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        social = (
            SocialAuth.objects.filter(
                provider=self.provider, provider_uid=data["provider_uid"]
            )
            .select_related("user")
            .first()
        )
        if social:
            user = social.user
        else:
            user, _ = User.objects.get_or_create(
                email=data["email"],
                defaults={
                    "full_name": data.get("full_name", ""),
                    "role": User.Role.STUDENT,
                },
            )
            SocialAuth.objects.create(
                user=user,
                provider=self.provider,
                provider_uid=data["provider_uid"],
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )


class GoogleLoginView(_SocialLoginBase):
    provider = SocialAuth.Provider.GOOGLE


class AppleLoginView(_SocialLoginBase):
    provider = SocialAuth.Provider.APPLE
