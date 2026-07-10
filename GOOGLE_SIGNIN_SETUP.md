# Google Sign-In Setup

Google sign-in ("Continue with Google") is built into the app. It activates
automatically when both environment variables are present — no code changes
needed to turn it on or off.

## Environment Variables (Vercel → Settings → Environment Variables)

| Variable | Value |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth Client ID from Google Cloud console |
| `GOOGLE_CLIENT_SECRET` | OAuth Client Secret from Google Cloud console |

Redeploy after adding them. If either is missing, the Google buttons are
hidden and email/password login works as before.

## Google Cloud Console Checklist

In [Google Cloud console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials),
your OAuth 2.0 Client ID (type: **Web application**) must have:

**Authorized redirect URIs** — exact match required:

```
https://<your-production-domain>/auth/google/callback
http://localhost:8000/auth/google/callback   (for local development)
```

If the URI is missing or differs (http vs https, trailing slash, www),
Google shows `Error 400: redirect_uri_mismatch`.

Also make sure the **OAuth consent screen** is configured and published
(in "Testing" mode only allowlisted test users can sign in).

## Database

No manual migration needed. On startup the app applies:

- `ALTER TABLE users ADD COLUMN google_sub VARCHAR(255)` + unique index
- `ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL` (PostgreSQL)

## How Accounts Are Handled

1. **Returning Google user** (`google_sub` matches) → logged in.
2. **Existing email/password user** signs in with Google using the same
   email → the Google identity is linked to that account (Google verifies
   email ownership); their password still works.
3. **New user** → account created with `password_hash = NULL`, free plan
   (3 contracts/month), same as form registration.

Unverified Google emails are rejected. The OAuth flow is CSRF-protected via
a short-lived `state` cookie, and the ID token's issuer, audience, and
expiry are validated server-side.
