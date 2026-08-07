# Known Issues (discovered during the security hardening pass)

Non-security bugs found incidentally while testing the P1–P9 security work.
Deliberately **not fixed** as part of that work — out of scope for a
security-focused change set — but recorded here so they aren't lost.

## Admin dashboard crashes on SQLite when there is data to aggregate

**Where:** `main.py`, `admin_dashboard()` (`GET /admin`), the `daily_jobs` /
`daily_users` queries using `cast(Contract.created_at, Date)` /
`cast(User.created_at, Date)` grouped by day.

**Symptom:** `TypeError: fromisoformat: argument must be str`, raised from
SQLAlchemy's compiled `Date` result processor, once any `Contract` or `User`
row exists for the query to aggregate. Discovered while adding an audit-log
test for admin dashboard access (P7) — no test in the suite exercised `GET
/admin` against a populated database before that.

**Likely cause:** SQLite has no native `DATE` type; `CAST(col AS DATE)`
relabels type affinity but doesn't reformat the stored value, so the raw
column value SQLAlchemy gets back doesn't match what its `Date` processor
expects to parse. This is a SQLite-specific incompatibility — it may not
reproduce on PostgreSQL (the intended production database per
`docker-compose.yml`), but should be verified there rather than assumed.

**Impact:** `GET /admin` will 500 in any deployment running SQLite with
actual usage data (i.e., every non-empty SQLite deployment, including local
dev and any small self-hosted instance not using the Postgres/Redis Docker
Compose stack).

**Suggested fix:** Replace `cast(col, Date)` grouping with a
dialect-appropriate day-truncation expression, or group in Python after
fetching `created_at` values directly, rather than relying on SQL-level
`DATE` casting that behaves differently across SQLite and PostgreSQL.

**Not a security issue**, but affects enterprise readiness: an admin
dashboard that can 500 under any real dataset is not production-ready
regardless of the security posture of the rest of the app.
