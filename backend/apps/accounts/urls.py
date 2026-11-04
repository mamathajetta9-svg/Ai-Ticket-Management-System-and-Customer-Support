from django.urls import path
from .views import (
    RegisterView,
    CustomLoginView,
    CustomTokenRefreshView,
    MyProfileView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', MyProfileView.as_view(), name='my_profile'),
]