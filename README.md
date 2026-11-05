# AI Ticket Management System and Customer Support

Backend API for an AI-powered ticket management and customer support platform.

## Technology

- Python 3.13
- Django 6.0
- Django REST Framework
- MySQL
- JWT authentication using SimpleJWT
- Google ID-token verification using google-auth

## Authentication and authorization

The accounts module provides customer registration, username/email password login, Google sign-in, JWT refresh/logout, profile retrieval, password change, and admin-only agent creation.

### Role model

| Role | Access |
|---|---|
| ADMIN | Account-management operations such as creating agents |
| AGENT | Agent role for ticket-handling APIs; each ticket endpoint must enforce its role and object-level rules |
| CUSTOMER | Customer-facing APIs; each ticket endpoint must enforce ownership rules |

Role checks use the authenticated database user rather than trusting a role claim supplied by the client. Public registration and Google-created accounts always receive CUSTOMER. Public serializers do not accept role, is_staff, or is_superuser fields.

An application ADMIN is not automatically a Django staff account. Only users with Django staff/superuser privileges can access /admin/. Create the initial Django superuser with the createsuperuser management command. The application ADMIN role and Django admin-site privileges are separate.

## Local setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

~~~powershell
cd backend
pip install -r requirements.txt
~~~

3. Copy the root .env.example file to a root .env file. Generate a fresh Django secret key locally and fill in your MySQL settings. Do not commit .env.
4. Create the MySQL database named in DB_NAME (the example uses tms1).
5. Apply migrations and run the development server:

~~~powershell
python manage.py migrate
python manage.py check
python manage.py runserver
~~~

6. Run automated account-module tests:

~~~powershell
python manage.py test apps.accounts
~~~

## Google sign-in setup

1. Create an OAuth 2.0 Client ID of type Web application in Google Cloud Console.
2. Configure the authorized JavaScript origin for the frontend.
3. Put the Client ID in the local root .env as GOOGLE_CLIENT_ID.
4. The frontend obtains a Google ID token and sends it to the backend. The backend verifies the token signature, issuer, expiry, and audience.
5. Automatic linking is allowed only for an existing CUSTOMER account with the same verified email. Existing ADMIN, AGENT, staff, or superuser accounts are not automatically linked. An administrator-controlled linking process is required for those accounts.
6. Never send the OAuth client secret, Django secret key, database password, or real .env file to GitHub or chat.

The backend expects an ID token, not an authorization code or access token.

## Authentication API

Base URL: /api/accounts/

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | register/ | Public | Register a customer |
| POST | login/ | Public | Login with username/email and password |
| POST | google/ | Public | Verify Google ID token and sign in |
| POST | token/refresh/ | Valid refresh token and active account | Rotate refresh token and issue access token |
| POST | logout/ | Authenticated; token must belong to caller | Blacklist a refresh token |
| POST | password/change/ | Authenticated | Change password and revoke all refresh tokens |
| GET | profile/ | Authenticated | Get the authenticated user profile |
| POST | agents/ | ADMIN role | Create an agent |

Protected endpoints require the Authorization: Bearer ACCESS_TOKEN header.

### Example request bodies

Registration:

~~~json
{
  "username": "sample_customer",
  "email": "customer@example.com",
  "password": "Use-A-Strong-Password"
}
~~~

Login:

~~~json
{
  "username": "sample_customer",
  "password": "Use-A-Strong-Password"
}
~~~

Google sign-in:

~~~json
{
  "id_token": "GOOGLE_ID_TOKEN_FROM_FRONTEND"
}
~~~

Logout:

~~~json
{
  "refresh": "REFRESH_TOKEN"
}
~~~

Password change:

~~~json
{
  "old_password": "Current-Password",
  "new_password": "New-Strong-Password"
}
~~~

## Security behavior

- Access tokens expire after 30 minutes; refresh tokens expire after one day and rotate on use.
- Rotated and logged-out refresh tokens are blacklisted.
- Refresh requests are rejected for inactive or deleted accounts.
- Password changes revoke all outstanding refresh tokens. Existing access tokens expire naturally within their configured lifetime.
- Logout rejects a refresh token belonging to a different authenticated user.
- Passwords use Django password validators and are stored as password hashes.
- Google sign-in accepts only a verified email claim from a correctly signed token issued for the configured client ID.
- Role permissions are checked against the current database user, so role changes take effect immediately for API authorization.
- Before production deployment, set DEBUG=False, a strong private SECRET_KEY, restrictive ALLOWED_HOSTS, secure database credentials, HTTPS, and appropriate reverse-proxy/security settings.
- Never commit .env, OAuth client secrets, database passwords, or production secrets.

## Scope

The current repository contains the backend accounts/authentication module. Ticket CRUD, ticket ownership rules, customer/agent ticket visibility, and ticket-specific authorization require ticket application models and endpoints, which are not currently present in this repository.