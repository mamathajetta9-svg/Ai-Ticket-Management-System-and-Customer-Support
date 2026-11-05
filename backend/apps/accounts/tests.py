from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class AccountAuthenticationTests(APITestCase):
    def setUp(self):
        self.password = 'StrongPass123!'
        self.customer = User.objects.create_user(
            username='customer_one',
            email='customer@example.com',
            password=self.password,
            role=User.Role.CUSTOMER,
        )

    def test_login_with_username(self):
        response = self.client.post(
            '/api/accounts/login/',
            {'username': 'customer_one', 'password': self.password},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_email(self):
        response = self.client.post(
            '/api/accounts/login/',
            {'username': 'CUSTOMER@example.com', 'password': self.password},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_customer_cannot_create_agent(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            '/api/accounts/agents/',
            {
                'username': 'new_agent',
                'email': 'agent@example.com',
                'password': 'AnotherStrongPass123!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_agent(self):
        admin = User.objects.create_user(
            username='system_admin',
            email='admin@example.com',
            password=self.password,
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=admin)
        response = self.client.post(
            '/api/accounts/agents/',
            {
                'username': 'new_agent',
                'email': 'agent@example.com',
                'password': 'AnotherStrongPass123!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            User.objects.get(username='new_agent').role,
            User.Role.AGENT,
        )

    def test_password_change_revokes_refresh_tokens(self):
        refresh = RefreshToken.for_user(self.customer)
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            '/api/accounts/password/change/',
            {
                'old_password': self.password,
                'new_password': 'NewStrongPass456!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password('NewStrongPass456!'))
        refresh_response = self.client.post(
            '/api/accounts/token/refresh/',
            {'refresh': str(refresh)},
            format='json',
        )
        self.assertEqual(
            refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_blacklists_refresh_token(self):
        refresh = RefreshToken.for_user(self.customer)
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            '/api/accounts/logout/',
            {'refresh': str(refresh)},
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_205_RESET_CONTENT,
        )
        refresh_response = self.client.post(
            '/api/accounts/token/refresh/',
            {'refresh': str(refresh)},
            format='json',
        )
        self.assertEqual(
            refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    @patch('apps.accounts.serializers.GoogleLoginSerializer.validate_id_token')
    def test_google_login_creates_customer_and_returns_jwt(self, mock_verify):
        mock_verify.return_value = 'mock-google-token'
        serializer_payload = {
            'sub': 'google-sub-123',
            'email': 'newcustomer@example.com',
            'email_verified': True,
        }

        with patch(
            'apps.accounts.serializers.GoogleLoginSerializer.validate_id_token',
            autospec=True,
        ) as mocked:
            def validate(serializer, value):
                serializer.context['google_payload'] = serializer_payload
                return value
            mocked.side_effect = validate

            response = self.client.post(
                '/api/accounts/google/',
                {'id_token': 'mock-google-token'},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['role'], User.Role.CUSTOMER)
        self.assertTrue(
            User.objects.filter(
                email='newcustomer@example.com',
                google_id='google-sub-123',
            ).exists()
        )
        self.assertIn('access', response.data)

    @patch('apps.accounts.serializers.GoogleLoginSerializer.validate_id_token')
    def test_google_login_links_existing_verified_email(self, mock_verify):
        mock_verify.return_value = 'mock-google-token'
        with patch(
            'apps.accounts.serializers.GoogleLoginSerializer.validate_id_token',
            autospec=True,
        ) as mocked:
            def validate(serializer, value):
                serializer.context['google_payload'] = {
                    'sub': 'google-sub-existing',
                    'email': self.customer.email,
                    'email_verified': True,
                }
                return value
            mocked.side_effect = validate

            response = self.client.post(
                '/api/accounts/google/',
                {'id_token': 'mock-google-token'},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.google_id, 'google-sub-existing')
