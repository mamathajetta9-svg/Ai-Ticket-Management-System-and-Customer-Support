from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


# Customer Registration
class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_email(self, value):
        return value.lower()

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.Role.CUSTOMER
        )
        return user


# JWT Login
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

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