from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from django.conf import settings
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, APIException
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


def verify_google_id_token(token, client_id):
    """Verify the signature, issuer, expiry, and audience of a Google ID token."""
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token

    return id_token.verify_oauth2_token(
        token,
        Request(),
        audience=client_id,
    )


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_email(self, value):
        return value.strip().lower()

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.Role.CUSTOMER,
        )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accept username or email in the existing username login field."""

    def validate(self, attrs):
        login_value = attrs.get(self.username_field, '').strip()
        password = attrs.get('password')

        user = User.objects.filter(
            Q(username__iexact=login_value) | Q(email__iexact=login_value)
        ).first()

        authenticated_user = None
        if user is not None:
            authenticated_user = authenticate(
                request=self.context.get('request'),
                username=user.username,
                password=password,
            )

        if authenticated_user is None:
            raise AuthenticationFailed(
                'No active account found with the provided credentials.'
            )

        refresh = self.get_token(authenticated_user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        return token


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'role',
            'is_active',
            'date_joined',
        ]
        read_only_fields = fields


class AgentCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_email(self, value):
        return value.strip().lower()

    def create(self, validated_data):
        return User.objects.create_user(
            **validated_data,
            role=User.Role.AGENT,
        )


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate_new_password(self, value):
        user = self.context['request'].user
        validate_password(value, user=user)
        return value


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True, trim_whitespace=True)

    def validate_id_token(self, value):
        if not settings.GOOGLE_CLIENT_ID:
            raise APIException(
                'Google sign-in is not configured. Set GOOGLE_CLIENT_ID in .env.'
            )

        try:
            payload = verify_google_id_token(value, settings.GOOGLE_CLIENT_ID)
        except ImportError as exc:
            raise APIException(
                'Google sign-in dependency is missing. Install backend requirements.'
            ) from exc
        except Exception as exc:
            raise serializers.ValidationError(
                'Google ID token is invalid or expired.'
            ) from exc

        if not payload.get('email') or payload.get('email_verified') is not True:
            raise serializers.ValidationError(
                'Google must provide a verified email address.'
            )
        if not payload.get('sub'):
            raise serializers.ValidationError('Google account ID is missing.')

        self.context['google_payload'] = payload
        return value
