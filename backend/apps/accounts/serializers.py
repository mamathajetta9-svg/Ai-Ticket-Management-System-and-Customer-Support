from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


# Customer Registration
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


# JWT Login: the existing "username" field accepts either username or email.
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
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


# User Profile
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
