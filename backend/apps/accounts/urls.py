from django.urls import path

from .views import (
    AgentCreateView,
    CustomLoginView,
    CustomTokenRefreshView,
    GoogleLoginView,
    LogoutView,
    MyProfileView,
    PasswordChangeView,
    RegisterView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('google/', GoogleLoginView.as_view(), name='google_login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('agents/', AgentCreateView.as_view(), name='agent_create'),
    path('profile/', MyProfileView.as_view(), name='my_profile'),
]
