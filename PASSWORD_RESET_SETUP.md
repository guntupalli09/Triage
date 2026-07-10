# Password Reset Setup

Self-serve password reset is built in: **Log in → "Forgot password?" →
enter email → emailed link → choose a new password.** Receiving the email
is the ownership verification — no separate verification step needed.

The reset link expires in **1 hour**, works **once**, and only a SHA-256
hash of the token is stored in the database. Responses never reveal
whether an email has an account (no enumeration).

## Email Provider (required — pick ONE)

The app sends the reset email through whichever provider is configured.
Add to Vercel → Settings → Environment Variables, then redeploy.

### Option A — Resend (recommended for Vercel)

1. Create a free account at [resend.com](https://resend.com) (3,000 emails/month free).
2. Verify your sending domain (Resend → Domains) or use their test sender to start.
3. Add:

| Variable | Value |
|---|---|
| `RESEND_API_KEY` | `re_...` from Resend → API Keys |
| `EMAIL_FROM` | `Triage Counsel <no-reply@yourdomain.com>` |

### Option B — Any SMTP server

| Variable | Value |
|---|---|
| `SMTP_HOST` | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | `587` (STARTTLS) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP / app password |
| `EMAIL_FROM` | `Triage Counsel <no-reply@yourdomain.com>` |

### If neither is configured

Users are **not** silently stranded: the forgot-password page shows
"temporarily unavailable" with a link to the contact page. Also note that
anyone whose email is a Google account can always get back in via
**Continue with Google** regardless of email configuration.

## Lockout Matrix

| Situation | Recovery path |
|---|---|
| Password user forgot password | Forgot password → email link → new password |
| Password user with Gmail/Workspace email | Also: Continue with Google (auto-links) |
| Google-only user wants a password | Forgot password → email link → sets one (Google login keeps working) |
| Email provider down | Contact page (manual support) |
