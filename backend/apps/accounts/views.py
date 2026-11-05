from uuid import uuid4

from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError, transaction
from django.utils.text import slugify
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenBlacklistSerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .permissions import IsAdmin
from .serializers import (
    AgentCreateSerializer,
    CustomTokenObtainPairSerializer,
    GoogleLoginSerializer,
    PasswordChangeSerializer,
    ProfileSerializer,
    RegisterSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)


class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = (AllowAny,)


class GoogleLoginView(APIView):
    permission_classes = (AllowAny,)

    @transaction.atomic
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.context["google_payload"]

        email = payload["email"].strip().lower()
        google_id = payload["sub"]

        try:
            user = User.objects.select_for_update().filter(google_id=google_id).first()
            if user is None:
                user = User.objects.select_for_update().filter(email__iexact=email).first()

            if user is not None:
                if user.google_id and user.google_id != google_id:
                    raise AuthenticationFailed(
                        "This email is already linked to another Google account."
                    )
                if not user.is_active:
                    raise AuthenticationFailed("This account is inactive.")
                if not user.google_id:
                    user.google_id = google_id
                    user.save(update_fields=("google_id",))
            else:
                # A random suffix avoids collisions when multiple sign-ups share an email prefix.
                base = slugify(email.split("@", 1)[0])[:110] or "google_user"
                username = f"{base}_{uuid4().hex[:8]}"
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=None,
                    google_id=google_id,
                    role=User.Role.CUSTOMER,
                )
        except IntegrityError as exc:
            raise ValidationError(
                "An account conflict occurred. Please try signing in again."
            ) from exc

        refresh = RefreshToken.for_user(user)
        refresh["username"] = user.username
        refresh["email"] = user.email
        refresh["role"] = user.role

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.pk,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                },
            },
            status=status.HTTP_200_OK,
        )


class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = (AllowAny,)


class MyProfileView(generics.RetrieveAPIView):
    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        # A logged-in user may only revoke their own refresh token.
        serializer = TokenBlacklistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["refresh"]
        token_user_id = token.payload.get("user_id")
        if str(token_user_id) != str(request.user.pk):
            raise AuthenticationFailed("You can only revoke your own refresh token.")
        serializer.save()
        return Response(
            {"detail": "Logout successful. Refresh token has been revoked."},
            status=status.HTTP_205_RESET_CONTENT,
        )


class PasswordChangeView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=("password",))
        update_session_auth_hash(request, request.user)

        # Revoke every outstanding refresh token after a credential change.
        for token in OutstandingToken.objects.filter(user=request.user):
            BlacklistedToken.objects.get_or_create(token=token)

        return Response(
            {"detail": "Password changed. Please log in again."},
            status=status.HTTP_200_OK,
        )


class AgentCreateView(generics.CreateAPIView):
    serializer_class = AgentCreateSerializer
    permission_classes = (IsAuthenticated, IsAdmin)
