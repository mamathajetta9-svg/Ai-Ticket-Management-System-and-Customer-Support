from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenBlacklistSerializer,
)

from .models import User


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
