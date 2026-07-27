"""Auth views (master prompt §10 + v2 §2.1/§6)."""
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from . import services
from .models import SocialAuth
from .serializers import (
    EmailTokenObtainPairSerializer,
    RegisterSerializer,
    SocialAuthSerializer,
    UserSerializer,
)

User = get_user_model()


def _token_response(user, status_code=status.HTTP_200_OK):
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        status=status_code,
    )


class GuestView(APIView):
    """POST /auth/guest — automatic guest account on first app open (v2 §2.1).

    No user input required. Issues the exact same JWT as registered users.
    Idempotence is the client's job (it stores the token); calling again
    simply creates another guest.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        country = services.detect_country(
            request, explicit=str(request.data.get("country", ""))
        )
        user = services.create_guest(country=country)
        return _token_response(user, status.HTTP_201_CREATED)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        requester = request.user if request.user.is_authenticated else None
        if requester is not None and requester.is_guest:
            # Guest → registered: convert the SAME row (v2 §2.1). Coins,
            # interests and progress survive because the pk never changes.
            data = serializer.validated_data
            user = services.convert_guest(
                requester,
                email=data["email"],
                password=data["password"],
                full_name=data.get("full_name", ""),
            )
            for field in ("native_language", "learning_goal", "app_language"):
                if data.get(field):
                    setattr(user, field, data[field])
            user.save()
        else:
            user = serializer.save()
        return _token_response(user, status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class GoogleLoginView(APIView):
    """POST /auth/social/google {"id_token": "..."} (v2 §6.1).

    The ID token is verified server-side against Google (signature, expiry,
    audience). Guests calling this endpoint get their row converted in place.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = str(request.data.get("id_token", ""))
        if not token:
            return Response(
                {"detail": "id_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            info = services.verify_google_id_token(token)
            requester = request.user if request.user.is_authenticated else None
            user = services.google_sign_in(token_info=info, requester=requester)
        except services.GoogleVerificationError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED
            )
        return _token_response(user)


class AppleLoginView(APIView):
    """Apple login stub (unchanged in v2 — Google is the active provider)."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        social = (
            SocialAuth.objects.filter(
                provider=SocialAuth.Provider.APPLE,
                provider_uid=data["provider_uid"],
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
                provider=SocialAuth.Provider.APPLE,
                provider_uid=data["provider_uid"],
            )
        return _token_response(user)
