# First-Party Acquisition & Product Analytics

**Document Version**: 1.0
**Last Updated**: 2026-07-19
**Status**: Implemented

## Executive Summary

TriageCounsel has a first-party analytics system that answers acquisition
and product questions without depending on Google Analytics or any
third-party tracker: how a user found the product, which channel/campaign
drove a signup, which landing pages convert, which uploaded contracts trace
back to which acquisition source, and which campaigns produce paying
customers.

The design is deliberately normalized — four purpose-built tables instead
of dozens of columns bolted onto `users` — so it stays queryable and
indexable as event volume grows into the hundreds of millions of rows.

---

## Schema

### `users` (unchanged)

Stays focused on identity and billing. No acquisition/analytics columns
were added to it.

### `user_acquisition` — one row per user, written once

The immutable signup snapshot: how this specific user arrived, and what
their device/browser/geo looked like at signup time. One-to-one with
`users` (`user_id` is unique + FK, cascade-deleted with the user).

Never updated after creation — `persist_user_acquisition()` is a no-op if
a row already exists for that user.

### `user_sessions` — one row per browsing session

Anonymous or authenticated. `is_authenticated` flips to `true` the moment
a visit's session logs in (see `analytics.mark_session_authenticated`).
`session_id` is unique and is the join key used across
`user_acquisition`, `user_events`, and `contract_events`.

### `user_events` — append-only product-analytics stream

The high-volume table. Every meaningful action (page view, login, upload,
download, subscription change, ...) becomes one row. `event_metadata`
(stored as the `metadata` column — see note below) is a flexible JSONB
payload for event-specific detail that doesn't need its own column.

### `contract_events` — one row per contract upload

Upload-specific technical facts (SHA-256, file size, processing time,
browser/device) that don't belong on the general event stream because
they describe *a document*, not *an action*. `contract_id` is nullable so
a failed upload (bad file, extraction error) can still be recorded with
`status="failed"` even though no `Contract` row was ever created.

See `analytics_models.py` for the full column list and inline rationale
for each type/index choice.

---

## Data flow

```
Request
  │
  ▼
RequestIDMiddleware        (assigns request_id — already existed)
  │
  ▼
AnalyticsMiddleware         (analytics_middleware.py)
  │  1. analytics.get_context(request)  — parse once, cache on request.state
  │  2. call_next(request)              — run the actual route
  │  3. refresh session cookie (tc_sid, 30 min sliding window)
  │  4. set first-touch cookie (tc_first_touch) — once, ever, per visitor
  │  5. if new session → INSERT user_sessions
  │  6. if GET + text/html + 200        → record_event("page_view")
  ▼
Route handler
  │  reuses analytics.get_context(request) — never re-parses
  │  records business-specific events: login, signup_completed,
  │  upload_started/completed, download_pdf, subscription_started, ...
  ▼
Response
```

### Why a cookie, not a server-side session, for first-touch attribution

Google OAuth is a full off-site redirect (`accounts.google.com`). Any
server-side "pending signup" state keyed by an anonymous session risks
being lost across that hop, and there is no reliable way to keep it in
Google's redirect params. A same-site, long-lived (400 day), httponly
cookie set on the visitor's *first* tracked request survives the OAuth
round-trip automatically — it's just an ordinary cookie the browser
re-sends on the way back to `/auth/google/callback`. This is also what
makes attribution correct when someone browses for days before signing
up: the referrer/UTM captured at signup time is the OAuth callback's own
request (which would just say "referred by accounts.google.com"), not the
original marketing touch. The cookie is what supplies the *real* referrer.

`persist_user_acquisition()` therefore blends two sources deliberately:
- **Marketing attribution** (referrer, UTM, landing page, click IDs,
  first session_id/request_id) → from the first-touch cookie.
- **Device/geo/IP** → from the actual signup-completing request, since
  that's the physically real "signup moment."

### Why geolocation never blocks a request

`geo_service.geolocate()` tries, in order: Cloudflare headers → generic
reverse-proxy headers → local MaxMind GeoLite2 (if configured) → ip-api.com
over HTTP. The first three are free/instant/local. The network fallback
only ever runs when explicitly requested with `allow_network_fallback=True`,
which `analytics.py` only sets when persisting the acquisition record
(a rare, high-value write) and only if the cheap sources found nothing.
Ordinary page views never make a network call for geolocation. Every
function in `geo_service.py` and `ua_service.py` catches its own
exceptions and degrades to `None`/`"unknown"` fields — geolocation and UA
parsing can never turn a request into a 500 or block a signup.

### Why event writes use their own DB session

`record_event()`, `record_session_start()`, and `end_session()` open a
short-lived `SessionLocal()` rather than reusing the caller's DB session.
An analytics write failure (or its `rollback()`) can therefore never
unwind a business transaction it happens to run alongside (e.g. a Contract
row commit). The one deliberate exception is `contract_events`: it's
built with `analytics.build_contract_event()` and added to the *same*
session/commit as the `Contract` row in the `/upload` handler, because
that row is really part of the same logical write (contract created +
its upload facts recorded together, one round trip).

---

## Acquisition channel classification

`channel_classifier.py` is a pure function:
`classify_channel(referring_domain, utm, click_ids) -> str`. Priority:

1. `utm_medium == "email"` → `Email`
2. A paid-ads click ID present (`gclid`, `msclkid`, `li_fat_id`, `ttclid`, `fbclid`) → the matching paid channel
3. `utm_source` matches a known source, split organic/paid by `utm_medium`
4. Referring domain matches a known domain (search engines, social platforms, developer communities)
5. No referrer and no UTM → `Direct`
6. Referrer present but unrecognized → `Referral`
7. Anything that throws → `Unknown` (never propagates an exception)

`acquisition_channel` is a plain `VARCHAR(40)`, not a Postgres `ENUM` —
adding a new channel is a one-line change to `channel_classifier.py`, not
a migration.

---

## Privacy & GDPR

**Never stored, by design:**
- Passwords (unaffected by this change — `users.password_hash` only)
- OAuth access/refresh tokens (Google's ID token is decoded once for
  claims and discarded; nothing from it is persisted except email/name/sub,
  which already existed on `users` before this system)
- Full precise device fingerprints beyond standard UA-derived facts

**Stored, and why:**
- IP address, coarse geo (country/region/city), browser/OS/device facts,
  UTM/referrer/click-IDs, and a stream of product events — all standard,
  low-sensitivity, first-party analytics data, used only to answer "how do
  people find and use the product."
- IP addresses use Postgres `INET` (not free text) so range/CIDR queries
  are possible without parsing, but they are still directly identifying
  and should be treated as personal data under GDPR.

**Right to erasure:** every analytics table has `ondelete="CASCADE"` on
its `user_id`/`contract_id` foreign key, and the SQLAlchemy relationships
on `User`/`Contract` use `cascade="all, delete-orphan"`. Deleting a `User`
row (the existing `/settings/delete-account` flow) deletes their
acquisition record, sessions, and events automatically — no separate
analytics cleanup step is needed.

**Cookies set by this system:**
| Cookie | Lifetime | Purpose |
|---|---|---|
| `tc_sid` | 30 min sliding | Correlates requests into one browsing session |
| `tc_first_touch` | 400 days | First-touch marketing attribution (referrer/UTM/landing page) |

Both are `httponly`, `samesite=lax`, and `secure` when `SECURE_COOKIES=true`.
Neither is readable by client-side JavaScript or third parties.

---

## Extensibility & scale

- **New event types**: just call `analytics.record_event(request, "my_new_event", ...)`
  from any route. No schema change — `event_type` is a free-text column.
- **New acquisition channels**: add a rule to `channel_classifier.py`.
- **New geo backends**: add a function to `geo_service.py`'s priority
  chain (e.g. a paid geo API) — `analytics.py` and callers are unaffected.
- **Partitioning `user_events` / `contract_events` at very high volume**:
  both tables are already structured to make this a drop-in change later —
  `event_timestamp` is indexed and would be the natural partition key
  (e.g. monthly range partitions on Postgres). No application code
  references these tables by physical layout, only through the ORM.
- **Moving event ingestion off the request path entirely**: `record_event()`
  is already isolated behind one function. At higher scale, its body can
  be swapped to push onto a queue (Kafka/Redis Stream/SQS) consumed by a
  separate batch writer, with zero changes to any call site.
- **BigInteger PKs** on `user_sessions`, `user_events`, and
  `contract_events` (vs. `Integer` on the low-cardinality parent tables)
  leave headroom well past 100M+ rows before any PK type migration is
  needed. (On SQLite specifically, these compile down to plain `INTEGER`
  so local dev keeps working — SQLite's ROWID-alias autoincrement only
  applies to that exact declared type. Postgres gets the real `BIGINT`.)

---

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `GEOIP_CITY_DB_PATH` | unset | Path to a MaxMind GeoLite2-City `.mmdb` file to enable local geo lookups |
| `GEOIP_ASN_DB_PATH` | unset | Path to a MaxMind GeoLite2-ASN `.mmdb` file to enable ASN enrichment |
| `IP_API_FALLBACK_ENABLED` | `true` | Set `false` to disable the ip-api.com network fallback entirely |
| `IP_API_TIMEOUT_SECONDS` | `1.0` | Timeout for the ip-api.com fallback call |
| `SECURE_COOKIES` | `false` | Already existed — also governs the two new analytics cookies |

MaxMind support requires `pip install geoip2` (not installed by default —
see the commented-out line in `requirements-docker.txt`) plus a licensed
`.mmdb` file; without it, the system still works correctly via
Cloudflare/proxy headers and the ip-api.com fallback.

---

## Files

| File | Responsibility |
|---|---|
| `analytics_models.py` | SQLAlchemy models for the four tables |
| `ua_service.py` | User-agent string → browser/OS/device facts |
| `geo_service.py` | IP → country/region/city/timezone/ISP/ASN |
| `channel_classifier.py` | (referrer, UTM, click IDs) → acquisition channel |
| `analytics.py` | Public service API: context building, event/session recording, acquisition persistence |
| `analytics_middleware.py` | Per-request wiring: cookies, session bookkeeping, automatic `page_view` |
| `main.py` | Route-level calls into `analytics.record_event(...)` at business-meaningful points; admin analytics routes |
| `templates/admin_analytics.html` | Funnel, top-N breakdowns, filterable acquisition table, CSV export |
| `templates/admin_analytics_user.html` | Per-user acquisition detail + session + event timeline |

## Admin analytics UI

`/admin/analytics` (same `require_admin` gate as `/admin`):
- Acquisition funnel: Visitors → Signup Started → Signup Completed → First
  Upload → Second Upload → Subscription
- Top channels, referrers, landing pages, campaigns, countries, browsers,
  devices, UTM sources
- Filterable/searchable signups table (channel dropdown + free-text search
  across email/UTM/referrer/country), linking to a per-user detail page
- `GET /admin/analytics/export.csv` — full acquisition export
- `GET /admin/analytics/user/{id}` — one user's acquisition record, session
  history, and full event timeline
