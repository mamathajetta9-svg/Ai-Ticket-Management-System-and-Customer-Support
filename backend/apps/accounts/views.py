from rest_framework import generics
from rest_framework.permissions import AllowAny

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .serializers import (
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
)

from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView

from .serializers import ProfileSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    pass


class MyProfileView(RetrieveAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user