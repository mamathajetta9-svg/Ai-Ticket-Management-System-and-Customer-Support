from unittest.mock import patch

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .models import User


class AccountAuthenticationTests(APITestCase):
    def setUp(self):
        self.password = "StrongPass123!"
        self.customer = User.objects.create_user(
            username="customer_one",
            email="customer@example.com",
            password=self.password,
        )

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)

    def test_registration_always_creates_customer_and_hashes_password(self):
        response = self.client.post(
            "/api/accounts/register/",
            {
                "username": "new_customer",
                "email": "  NEW@example.com ",
                "password": "SafeNewPassword456!",
                "role": "ADMIN",
                "is_staff": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="new_customer")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertFalse(user.is_staff)
        self.assertNotEqual(user.password, "SafeNewPassword456!")

    def test_login_with_username(self):
        response = self.client.post(
            "/api/accounts/login/",
            {"username": "customer_one", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(AccessToken(response.data["access"])["role"], "CUSTOMER")

    def test_login_with_case_insensitive_email(self):
        response = self.client.post(
            "/api/accounts/login/",
            {"username": "CUSTOMER@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_password_is_rejected(self):
        response = self.client.post(
            "/api/accounts/login/",
            {"username": "customer_one", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_user_cannot_login(self):
        self.customer.is_active = False
        self.customer.save()
        response = self.client.post(
            "/api/accounts/login/",
            {"username": "customer_one", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/accounts/profile/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_cannot_create_agent(self):
        self.authenticate_as(self.customer)
        response = self.client.post(
            "/api/accounts/agents/",
            {
                "username": "new_agent",
                "email": "agent@example.com",
                "password": "AnotherStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_role_can_create_agent(self):
        admin = User.objects.create_user(
            username="system_admin",
            email="admin@example.com",
            password=self.password,
            role=User.Role.ADMIN,
        )
        self.authenticate_as(admin)
        response = self.client.post(
            "/api/accounts/agents/",
            {
                "username": "new_agent",
                "email": "agent@example.com",
                "password": "AnotherStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        agent = User.objects.get(username="new_agent")
        self.assertEqual(agent.role, User.Role.AGENT)
        self.assertFalse(agent.is_staff)

    def test_partial_role_update_removes_superuser_privilege(self):
        root = User.objects.create_superuser(
            username="root_admin",
            email="root-admin@example.com",
            password=self.password,
        )
        root.role = User.Role.CUSTOMER
        root.save(update_fields=["role"])
        root.refresh_from_db()
        self.assertEqual(root.role, User.Role.CUSTOMER)
        self.assertFalse(root.is_superuser)

    def test_agent_cannot_create_another_agent(self):
        agent = User.objects.create_user(
            username="agent_one",
            email="agent@example.com",
            password=self.password,
            role=User.Role.AGENT,
        )
        self.authenticate_as(agent)
        response = self.client.post(
            "/api/accounts/agents/",
            {
                "username": "agent_two",
                "email": "agent2@example.com",
                "password": "AnotherStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_password_change_revokes_refresh_tokens(self):
        refresh = RefreshToken.for_user(self.customer)
        self.authenticate_as(self.customer)
        response = self.client.post(
            "/api/accounts/password/change/",
            {
                "old_password": self.password,
                "new_password": "NewStrongPass456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password("NewStrongPass456!"))
        refresh_response = self.client.post(
            "/api/accounts/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejects_inactive_user(self):
        refresh = RefreshToken.for_user(self.customer)
        self.customer.is_active = False
        self.customer.save(update_fields=["is_active"])
        response = self.client.post(
            "/api/accounts/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejects_deleted_user(self):
        refresh = RefreshToken.for_user(self.customer)
        self.customer.delete()
        response = self.client.post(
            "/api/accounts/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rotation_preserves_role_claim(self):
        refresh = RefreshToken.for_user(self.customer)
        refresh["role"] = self.customer.role
        response = self.client.post(
            "/api/accounts/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AccessToken(response.data["access"])["role"], "CUSTOMER")
        self.assertIn("refresh", response.data)

    def test_password_change_rejects_wrong_current_password(self):
        self.authenticate_as(self.customer)
        response = self.client.post(
            "/api/accounts/password/change/",
            {"old_password": "wrong", "new_password": "NewStrongPass456!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_blacklists_only_own_refresh_token(self):
        other = User.objects.create_user(
            username="other_customer",
            email="other@example.com",
            password=self.password,
        )
        other_refresh = RefreshToken.for_user(other)
        self.authenticate_as(self.customer)
        response = self.client.post(
            "/api/accounts/logout/",
            {"refresh": str(other_refresh)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_own_refresh_token(self):
        refresh = RefreshToken.for_user(self.customer)
        self.authenticate_as(self.customer)
        response = self.client.post(
            "/api/accounts/logout/",
            {"refresh": str(refresh)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        refresh_response = self.client.post(
            "/api/accounts/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(GOOGLE_CLIENT_ID="test-google-client-id")
    @patch("apps.accounts.serializers.verify_google_id_token")
    def test_google_login_creates_customer_and_returns_jwt(self, verify_token):
        verify_token.return_value = {
            "sub": "google-sub-123",
            "email": "newcustomer@example.com",
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }
        response = self.client.post(
            "/api/accounts/google/",
            {"id_token": "fake-id-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["role"], User.Role.CUSTOMER)
        user = User.objects.get(email="newcustomer@example.com")
        self.assertEqual(user.google_id, "google-sub-123")
        self.assertEqual(AccessToken(response.data["access"])["role"], "CUSTOMER")

    @override_settings(GOOGLE_CLIENT_ID="test-google-client-id")
    @patch("apps.accounts.serializers.verify_google_id_token")
    def test_google_login_links_existing_verified_email(self, verify_token):
        verify_token.return_value = {
            "sub": "google-sub-existing",
            "email": self.customer.email,
            "email_verified": True,
            "iss": "accounts.google.com",
        }
        response = self.client.post(
            "/api/accounts/google/",
            {"id_token": "fake-id-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.google_id, "google-sub-existing")

    @override_settings(GOOGLE_CLIENT_ID="test-google-client-id")
    @patch("apps.accounts.serializers.verify_google_id_token")
    def test_google_login_does_not_auto_link_privileged_account(self, verify_token):
        admin = User.objects.create_user(
            username="unlinked_admin",
            email="unlinked-admin@example.com",
            password=self.password,
            role=User.Role.ADMIN,
        )
        verify_token.return_value = {
            "sub": "google-admin-sub",
            "email": admin.email,
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }
        response = self.client.post(
            "/api/accounts/google/",
            {"id_token": "fake-id-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        admin.refresh_from_db()
        self.assertIsNone(admin.google_id)

    @override_settings(GOOGLE_CLIENT_ID="test-google-client-id")
    @patch("apps.accounts.serializers.verify_google_id_token")
    def test_google_login_rejects_unverified_email(self, verify_token):
        verify_token.return_value = {
            "sub": "google-sub-123",
            "email": "unverified@example.com",
            "email_verified": False,
            "iss": "https://accounts.google.com",
        }
        response = self.client.post(
            "/api/accounts/google/",
            {"id_token": "fake-id-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(GOOGLE_CLIENT_ID="test-google-client-id")
    @patch("apps.accounts.serializers.verify_google_id_token")
    def test_google_login_rejects_invalid_issuer(self, verify_token):
        verify_token.return_value = {
            "sub": "google-sub-123",
            "email": "person@example.com",
            "email_verified": True,
            "iss": "https://attacker.example",
        }
        response = self.client.post(
            "/api/accounts/google/",
            {"id_token": "fake-id-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_google_registration_does_not_grant_privileged_role(self):
        with patch("apps.accounts.serializers.verify_google_id_token") as verify:
            verify.return_value = {
                "sub": "google-customer",
                "email": "google@example.com",
                "email_verified": True,
                "iss": "https://accounts.google.com",
            }
            with override_settings(GOOGLE_CLIENT_ID="client-id"):
                response = self.client.post(
                    "/api/accounts/google/",
                    {"id_token": "valid-token"},
                    format="json",
                )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        created = User.objects.get(email="google@example.com")
        self.assertEqual(created.role, User.Role.CUSTOMER)
