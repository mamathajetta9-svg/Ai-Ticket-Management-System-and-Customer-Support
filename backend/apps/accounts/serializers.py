from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class GoogleSignInUnavailable(APIException):
    status_code = 503
    default_detail = "Google sign-in is not configured on this server."
    default_code = "google_sign_in_unavailable"


def verify_google_id_token(token, client_id):
    """Verify the signature, issuer, expiry, and audience of a Google ID token."""
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token

    return id_token.verify_oauth2_token(token, Request(), audience=client_id)


class UniqueAccountFieldsMixin:
    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class RegisterSerializer(UniqueAccountFieldsMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        # Role is deliberately not accepted from the request.
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            role=User.Role.CUSTOMER,
        )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accept either username or email in the standard username field."""

    def validate(self, attrs):
        login_value = (attrs.get(self.username_field) or "").strip()
        password = attrs.get("password")

        user = User.objects.filter(
            Q(username__iexact=login_value) | Q(email__iexact=login_value)
        ).first()

        authenticated_user = None
        if user is not None:
            authenticated_user = authenticate(
                request=self.context.get("request"),
                username=user.username,
                password=password,
            )

        if authenticated_user is None or not authenticated_user.is_active:
            raise AuthenticationFailed(
                "No active account found with the provided credentials."
            )

        refresh = self.get_token(authenticated_user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        token["role"] = user.role
        return token


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "is_active", "date_joined")
        read_only_fields = fields


class AgentCreateSerializer(UniqueAccountFieldsMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data, role=User.Role.AGENT)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, user=self.context["request"].user)
        return value


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True, trim_whitespace=True)

    def validate_id_token(self, value):
        if not settings.GOOGLE_CLIENT_ID:
            raise GoogleSignInUnavailable()

        try:
            payload = verify_google_id_token(value, settings.GOOGLE_CLIENT_ID)
        except ImportError as exc:
            raise GoogleSignInUnavailable(
                "Google sign-in dependency is missing. Install backend requirements."
            ) from exc
        except Exception as exc:
            raise serializers.ValidationError(
                "Google ID token is invalid or expired."
            ) from exc

        if payload.get("email_verified") is not True or not payload.get("email"):
            raise serializers.ValidationError(
                "Google must provide a verified email address."
            )
        if not payload.get("sub"):
            raise serializers.ValidationError("Google account ID is missing.")

        self.context["google_payload"] = payload
        return value
