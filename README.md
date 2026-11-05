# AI Ticket Management System and Customer Support

Backend API for an AI-powered ticket management and customer support platform.

## Technology

- Python 3.13
- Django 6.0
- Django REST Framework
- MySQL
- JWT authentication (SimpleJWT)
- Google ID-token verification (google-auth)

## Current backend scope

### Authentication and authorization

- Customer registration (customers cannot choose their own role).
- Login using username or email and password.
- Google sign-in using a verified Google ID token.
- Access and refresh JWT tokens.
- Refresh-token rotation and blacklisting.
- Authenticated user profile.
- Logout by blacklisting a refresh token.
- Password change with current-password validation and refresh-token revocation.
- Admin-only agent creation.
- ADMIN, AGENT, and CUSTOMER role permission classes.

## Local setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```powershell
   cd backend
   pip install -r requirements.txt
   ```

3. Copy the root `.env.example` file to a root `.env` file. Generate a fresh Django secret key locally and fill in your MySQL settings. Do not commit `.env`.
4. Create the MySQL database named in `DB_NAME` (the example uses `tms1`).
5. Apply migrations and run the development server:

   ```powershell
   python manage.py migrate
   python manage.py check
   python manage.py runserver
   ```

6. Run automated tests:

   ```powershell
   python manage.py test apps.accounts
   ```

## Google sign-in setup

1. Create an OAuth 2.0 Client ID of type **Web application** in Google Cloud Console.
2. Configure the authorized JavaScript origin for the frontend you use.
3. Put the Client ID in the local root `.env` as `GOOGLE_CLIENT_ID`.
4. The frontend obtains a Google ID token and sends it to the backend endpoint below. The backend verifies the token signature, issuer, expiry, and audience before creating or linking a customer account.
5. Never send the client secret, Django secret key, database password, or real `.env` file to GitHub or chat.

The backend expects an ID token, not an authorization code or access token.

## Authentication API

Base URL: `/api/accounts/`

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `register/` | Register a customer |
| POST | `login/` | Login with username/email and password |
| POST | `google/` | Verify Google ID token and sign in |
| POST | `token/refresh/` | Refresh JWT access token |
| POST | `logout/` | Blacklist a refresh token |
| POST | `password/change/` | Change the authenticated user's password |
| GET | `profile/` | Get the authenticated user's profile |
| POST | `agents/` | Create an agent (ADMIN only) |

### Example request bodies

Register:

```json
{
  "username": "sample_customer",
  "email": "customer@example.com",
  "password": "Use-A-Strong-Password"
}
```

Login:

```json
{
  "username": "sample_customer",
  "password": "Use-A-Strong-Password"
}
```

Google sign-in:

```json
{
  "id_token": "GOOGLE_ID_TOKEN_FROM_FRONTEND"
}
```

Logout:

```json
{
  "refresh": "REFRESH_TOKEN"
}
```

Password change:

```json
{
  "old_password": "Current-Password",
  "new_password": "New-Strong-Password"
}
```

Protected endpoints require:

```
Authorization: Bearer ACCESS_TOKEN
```

## Important

- New public registrations and Google-created accounts always receive the CUSTOMER role.
- The client cannot assign itself ADMIN or AGENT.
- Only an authenticated ADMIN can create AGENT accounts.
- The Google Client ID is configuration, not a private client secret; keep it in local environment configuration and never commit private OAuth credentials.
- Configure production values for `DEBUG`, `ALLOWED_HOSTS`, HTTPS, database credentials, and secret keys before deployment.
