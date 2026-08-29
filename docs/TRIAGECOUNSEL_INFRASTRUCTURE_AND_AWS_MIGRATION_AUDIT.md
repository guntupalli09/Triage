# TriageCounsel Infrastructure & AWS Migration Audit

Read-only repository audit. No code, configuration, infrastructure, or production
systems were modified to produce this document. Every claim is backed by a
file/path citation from the `guntupalli09/triage` repository (branch
`claude/triagecounsel-aws-audit-vazxtp`, audited 2026-08-29). Where the
repository does not contain the answer, this document says so explicitly —
**UNKNOWN — requires server inspection** — rather than guessing.

---

## 1. Executive Summary

TriageCounsel is a **single-service, monolithic Python web application**
(FastAPI + server-rendered Jinja2 templates — there is no separate frontend
codebase or SPA). It is packaged as one Docker image (`Dockerfile`) run
alongside Postgres and Redis via `docker-compose.yml`, explicitly tuned for a
**Hetzner CX23 VPS (2 vCPU / 4 GB RAM)** per a comment in `gunicorn.conf.py`.
The operator-confirmed actual bill for this VPS is **€/$6.49/month**
(Hetzner Cloud console, instance "Triagecx23", 91.98.128.252 — 2 vCPU, 4 GB
RAM, 40 GB local disk, 0/20 TB traffic used), plus **under $5/month** in
OpenAI API usage — **total current infrastructure spend is roughly
$11–12/month**, not the ~$100/month originally assumed in scoping this
audit. This is a materially different starting point for the AWS
cost comparison in Part 11 and the final recommendation in Part 16: any
AWS architecture with a Load Balancer, RDS, and EC2 will cost several times
more than the current setup in absolute dollars, even though it remains
inexpensive by SaaS-infrastructure standards. That trade-off — real
reliability gains (backups, managed TLS, monitoring) in exchange for a
~6–10x increase in a very small absolute number — is spelled out plainly
below rather than glossed over.

The application already has a real security baseline: AES-256-GCM
application-layer encryption of contract text (`encryption.py`), CSRF
protection (`csrf.py`), Redis-backed rate limiting (`rate_limit.py`), security
headers incl. HSTS (`security_headers.py`), TOTP MFA (`mfa.py`), RBAC
(`rbac.py`), audit logging (`audit_log.py`), and a hard architectural
boundary preventing full contract text from reaching the LLM (`evaluator.py`).
What it does **not** have — and what dominates the risk picture — is
infrastructure-level resilience: no backups, no CI/CD, no monitoring/alerting,
no staging environment, and a single VPS that is a complete single point of
failure for compute, database, and file storage all at once.

The recommended AWS path is **not** ECS/Fargate or EKS. Given the workload
(one process, no horizontal scale need yet, cost-sensitive, small team), the
simplest architecture that meaningfully improves on the current VPS is:
**one EC2 instance running the existing Docker Compose stack, behind an
Application Load Balancer for TLS, with the database moved to RDS Postgres
and automated snapshots, S3 for backups, and Secrets Manager for
credentials.** This preserves the current deployment model almost exactly
(same Dockerfile, same Compose file minus Postgres) while fixing the two
CRITICAL gaps repository evidence confirms: no backups and no managed
encryption-at-rest guarantee. Estimated AWS cost at current scale: **$60–140/month all-in (AWS infra +
OpenAI)**. Set against the operator-confirmed actual current spend of
**~$11–12/month** ($6.49 Hetzner + under $5 OpenAI), this is a real
**~6–10x increase in absolute dollars** — still cheap for a SaaS product
with paying legal customers, but not "comparable," and not something to
undertake unless the reliability gains (automated backups, managed TLS,
monitoring/alerting — none of which are confirmed to exist today) are
worth that jump. Section 16 discusses a lower-cost alternative for a team
that isn't ready to spend that increase yet: fixing the CRITICAL backup
gap directly on the existing Hetzner box first, and treating AWS as a
later step once customer count or compliance requirements justify it.

---

## 2. Current Tech Stack

### Languages

| Language | Where used | Evidence |
|---|---|---|
| Python 3.12 | Entire backend: FastAPI app, rules engine, LLM integration, DB models, background scripts | `Dockerfile:1` (`FROM python:3.12-slim`), `main.py`, 190+ root-level `.py` modules |
| HTML + Jinja2 templates | Server-rendered UI (no SPA) | `templates/*.html` (base_app.html, dashboard.html, playbooks.html, etc.) |
| CSS (Tailwind, pre-built) | Styling | `static/tailwind.css` — no `tailwind.config.js`/`package.json` found in repo root, so the CSS is either hand-maintained or built outside this repo |
| SQL | Raw migration/DDL statements referenced in code comments; primarily driven through SQLAlchemy | `database.py`, `models.py` |
| Shell | Not found as first-class deploy scripts; only inline snippets in docs (`docs/security/data_retention_infra.md` shows crontab/systemd examples, not committed scripts) | — |
| LaTeX | Unrelated: an IEEE research paper submission, not part of the product | `IEEE paper/`, `Submission/` |

There is **no JavaScript/TypeScript frontend framework** (no React/Vue/Next.js,
no `package.json` at the repo root). The UI is classic server-rendered HTML
with Jinja2 and Tailwind CSS, plus presumably some vanilla JS in the templates
themselves (not separately inspected line-by-line here).

### Frontend

- **Framework**: None (no SPA). Server-rendered Jinja2 templates (`templates/`) served directly by the FastAPI app.
- **Language**: HTML/Jinja2 + Tailwind CSS.
- **Build system**: No build step found in the repo (no `package.json`, no `tailwind.config.js`, no `npm`/`yarn`/`pnpm` lockfile). `static/tailwind.css` is a static file already checked in.
- **Package manager**: N/A — no JS dependency manager present in the repo.
- **Serving**: Frontend and backend are **the same process** — FastAPI mounts `static/` via `StaticFiles` and renders templates via `Jinja2Templates` (`main.py:42-43`). They are **not** separate services.

### Backend

- **Language**: Python 3.12.
- **Framework**: FastAPI (`requirements.txt:2` — `fastapi==0.104.1`), ASGI via `uvicorn[standard]`.
- **API architecture**: Traditional server-rendered MVC-style routes (HTML responses) plus some JSON/internal endpoints — not a dedicated REST/GraphQL API product; one process serves both UI and logic.
- **Web/application server**: Gunicorn with `UvicornWorker` in production (`Dockerfile` CMD: `gunicorn main:app -c gunicorn.conf.py`; `gunicorn.conf.py` sets `worker_class = "uvicorn.workers.UvicornWorker"`, 2 workers by default). Locally, `uvicorn main:app --reload` per `README.md`.
- **Background processing**: No dedicated task queue (no Celery/RQ/Dramatiq found). Long-running work (OpenAI calls) happens synchronously inside the request via `async`/`await` in FastAPI; `gunicorn.conf.py` sets a 120s worker timeout specifically to accommodate this.
- **Queues/workers**: None found. Redis is used for **sessions** and **rate-limit counters**, not as a job queue (`auth.py:3`, `rate_limit.py:4`).
- **Scheduled jobs**: None run automatically in the Docker deployment. `retention.py` and `run_retention_cleanup.py` implement data-retention cleanup, but the code and docs are explicit that **nothing invokes them automatically** — an operator must wire up cron/systemd timer/K8s CronJob themselves (`retention.py:9-19`, `docs/security/data_retention_infra.md`). `WORKER_ENABLED=true` exists in `.env.example` but names a background-processing toggle, not a scheduler.

### Database

- **Technology**: PostgreSQL 16 in production (`docker-compose.yml`: `image: postgres:16-alpine`), SQLite for local development (`database.py:3` — "Supports PostgreSQL (production) and SQLite (development)").
- **ORM**: SQLAlchemy (`requirements-docker.txt` — `sqlalchemy>=2.0.0`; `models.py`, `database.py`).
- **Migrations**: No Alembic or migration framework found. `database.py` creates schema directly (`init_db()` called from `gunicorn.conf.py`'s `on_starting` hook); `migrate_policy_positions.py` and `backfill_encryption.py` exist as one-off manual scripts, not a migrations directory.
- **Connection configuration**: `DATABASE_URL` env var; connection pool tuned for Postgres (`pool_size=5, max_overflow=5, pool_recycle=1800, pool_pre_ping=True` — `database.py:33-40`).
- **Persistence architecture**: Single primary database, no read replicas, no sharding evidence.
- **Where it runs**: Inside Docker, as the `postgres` service in `docker-compose.yml`, with a named Docker volume `pgdata:/var/lib/postgresql/data`. It is **not** shown running on the bare host or as an external managed service anywhere in the repo.

### AI

This is the most safety-critical subsystem for a legal product, so it gets
extra scrutiny.

- **Provider**: OpenAI only (`openai_provider.py`, `evaluator.py:26` — `from openai import OpenAI`). No Anthropic/other provider found.
- **Model**: Default `gpt-4o-mini`, configurable via `OPENAI_MODEL` env var (`.env.example`: "Model used for LLM evaluation. gpt-4o-mini is cost-effective for triage").
- **Where AI calls occur**: Exclusively in `evaluator.py`'s `LLMEvaluator` class, invoked from `main.py` during contract analysis.
- **Credentials**: `OPENAI_API_KEY` env var, read centrally through `openai_provider.py` ("the single shared config module for every OpenAI call in the application" — `evaluator.py:59-61`), not hardcoded.
- **Can contract content reach OpenAI?** By explicit architectural design, **no — not the full contract**. `evaluator.py`'s module docstring states the LLM "Receives ONLY deterministic findings (never full contract text)" and "NEVER sees full contract text (hard architectural boundary)." The prompt builder (`_build_prompt`) sends only: rule name, title, severity, rationale, and up to 2 short **excerpts per matched rule** (not the whole document) — see `evaluator.py:78-100`.
- **What data is transmitted**: Short excerpts of contract text tied to specific findings (wrapped with delimiter markers and sanitized via `prompt_security.py` to reduce prompt-injection risk — `evaluator.py:114-118`), plus rule metadata. Full contract text is never sent — this is enforced by "code-level assertions" per the module docstring, not just by convention.
- **Synchronous or async**: Synchronous within the request/response cycle (FastAPI `async` call, but the user's HTTP request waits for the OpenAI response). This is why Gunicorn's worker timeout is set to 120s (`gunicorn.conf.py`).
- **Failure behavior**: "Safe Failure Modes: System works even if LLM is unavailable" (`README.md`) — the deterministic rule engine (`rules_engine.py`) is the source of truth for risk detection; the LLM only adds explanatory text. If `OPENAI_API_KEY` is unset, `LLMEvaluator.__init__` logs and continues without a client (`evaluator.py:65-70`) rather than crashing.
- **Prompt-injection guardrails**: Present — `prompt_security.py`, excerpt sanitization/wrapping, and an explicit "UNTRUSTED DATA WARNING" block embedded in every prompt instructing the model to treat contract text as data, not instructions (`evaluator.py:105-110`).

### Document processing

- **PDF**: `PyPDF2` for text extraction (`main.py:49`); page-count and text-density limits enforced in `upload_security.py` (`validate_pdf_page_count`, `assess_pdf_text_density`).
- **DOCX**: `python-docx` (`main.py:50`); zip-bomb/zip-safety validation in `upload_security.py:114` (`validate_docx_zip_safety`).
- **TXT**: Read directly, subject to the same size/extension checks.
- **OCR**: **Not implemented.** `upload_security.py:163` explicitly states: "This is a length/density heuristic, not OCR -- no OCR dependency exists," and the same file's user-facing error message tells users to "run OCR first and re-upload" if the PDF is a scan (`upload_security.py:188`). Scanned/image-only PDFs are rejected, not processed.
- **PDF report generation** (output, not input): `fpdf2` in the Docker deployment (`requirements-docker.txt`), `xhtml2pdf` in the (legacy) Vercel path (`requirements-prod.txt`) — two different PDF-generation libraries depending on deployment target.
- **Malware scanning**: Pluggable interface exists (`upload_security.py`), but the default is `NoopMalwareScanner` — **no scanning happens unless an operator stands up a ClamAV daemon and sets `MALWARE_SCANNER=clamd`** (`docs/security/upload_hardening_infra.md`). Filename sanitization, magic-byte/content-type validation, and size caps (10 MB) run regardless.

### Infrastructure

- **Docker**: Single `Dockerfile`, Python 3.12-slim base, non-root user (`triage`), built-in `HEALTHCHECK` hitting `/health` (`Dockerfile`).
- **Docker Compose**: `docker-compose.yml` defines 3 services — `web`, `postgres` (16-alpine), `redis` (7-alpine) — on one bridge network (`internal`), with health checks and log rotation (`max-size: 10m/5m`, `max-file: 5/3`) on each.
- **Reverse proxy**: **Not present in the repository.** No Nginx/Traefik/Caddy config file exists. `web` in `docker-compose.yml` maps directly to host port `8000:8000`. Anything terminating TLS or fronting the app on port 80/443 must live outside this repo. **UNKNOWN — requires server inspection.**
- **TLS/HTTPS**: The application sets HSTS and other security headers (`security_headers.py`) and supports `SECURE_COOKIES=true`, but **TLS termination itself is not configured anywhere in this repository** (no cert files, no Let's Encrypt/Certbot config, no proxy TLS block). **UNKNOWN — requires server inspection** for how HTTPS is actually terminated in production.
- **Ports**: Container exposes `8000` (`Dockerfile EXPOSE 8000`); Compose publishes `8000:8000` on the host.
- **Volumes**: `pgdata` (Postgres data), `redisdata` (Redis AOF persistence — `--appendonly yes`). No named volume for uploaded files, because uploads are **not written to disk**: contract text is parsed in-memory and stored as an encrypted column in Postgres (`models.py:80` — `contract_text = Column(EncryptedText, ...)`), not as files on a filesystem or object store.
- **Networks**: One internal bridge network per Compose; no external network segmentation defined at the Compose level.
- **Environment variables / secrets**: `.env` file consumed via `env_file:` in Compose and `python-dotenv` in `main.py`. `.env.example` documents every required variable, including production-refusal behavior for insecure defaults (e.g., `APP_HMAC_SECRET`/`SESSION_SECRET` must be changed from dev defaults — `.env.example` "Security" section). No secrets manager (Vault, AWS Secrets Manager, etc.) is referenced anywhere in the repo — secrets live in a plain `.env` file on the host.
- **Persistent storage**: Postgres and Redis Docker volumes only; both are local to whatever host runs Compose.
- **Logging**: JSON-file Docker logging driver with rotation caps (`docker-compose.yml`); Gunicorn access/error logs to stdout (`gunicorn.conf.py`). No log shipping/aggregation (no Fluentd/Loki/CloudWatch agent/ELK config found).
- **Backups**: **No backup mechanism found in the repository** — no scheduled `pg_dump`, no volume snapshot automation, no S3/off-host backup target, no restore scripts. This is corroborated by the repo's own `docs/security/soc2_readiness_assessment.md` (finding C-01).
- **Monitoring**: `/health` endpoint exists and is used by Docker/Compose health checks (`main.py`, `Dockerfile`, `docker-compose.yml`), but no external uptime monitoring, metrics exporter, or alerting configuration was found in the repo.

### Testing

- **Unit/integration tests**: `pytest` (`requirements-dev.txt` implied; `tests/` directory), **138 test files**, README claims "194/194 tests passing (100% pass rate)" as of the last recorded run.
- **Regression/benchmark tests**: An unusually large, purpose-built regression suite under `benchmarks/` and `scripts/` — dozens of adversarial/held-out corpora used to validate the deterministic rules engine and LLM boundary behavior (e.g., `run_liability_benchmark.py`, `run_confidentiality_benchmark.py`, prompt-injection benchmarks under `step4b_phaseJ_prompt_injection_benchmark.py`). This is a genuinely strong regression-testing culture specific to the correctness of legal risk detection, distinct from typical web-app CI.
- **End-to-end tests**: Not clearly separated from the integration suite in `tests/` (e.g., `test_guest_upload_flow.py`, `test_upload_security_integration.py` exercise multi-step flows); no browser-driven E2E framework (Playwright/Selenium) found.
- **Security scanning**: No SAST/dependency-scanning tool config found (no Bandit, Semgrep, pip-audit, Safety, Dependabot/Renovate config).
- **CI/CD**: **No `.github/workflows` directory exists.** There is no CI pipeline of any kind checked into the repository. Tests, benchmarks, and any deployment steps currently run manually.

### Final Stack Table

| Component | Current Technology | Purpose | Evidence/File |
|---|---|---|---|
| Backend language/framework | Python 3.12, FastAPI 0.104.1 | Web app + API | `Dockerfile`, `requirements.txt` |
| App server | Gunicorn + UvicornWorker | Production process manager | `gunicorn.conf.py` |
| Frontend | Jinja2 templates + Tailwind CSS (server-rendered, same process) | UI | `templates/`, `static/tailwind.css`, `main.py:42-43` |
| Database | PostgreSQL 16 (prod), SQLite (dev) | Primary data store | `docker-compose.yml`, `database.py` |
| ORM | SQLAlchemy ≥2.0 | DB access | `models.py`, `database.py` |
| Cache/session/rate-limit store | Redis 7 | Sessions, rate limiting | `docker-compose.yml`, `auth.py`, `rate_limit.py` |
| AI provider | OpenAI (gpt-4o-mini default) | Finding explanation only, never raw text | `evaluator.py`, `openai_provider.py` |
| Document parsing | PyPDF2, python-docx | PDF/DOCX/TXT ingestion | `main.py`, `upload_security.py` |
| PDF report output | fpdf2 (Docker) / xhtml2pdf (Vercel) | Generated risk reports | `requirements-docker.txt`, `requirements-prod.txt` |
| Encryption at rest | AES-256-GCM, app-layer | Contract text & sensitive JSON columns | `encryption.py`, `models.py:76-80` |
| Auth | Password + PBKDF2-HMAC-SHA256, Google OAuth, TOTP MFA | User auth | `auth.py`, `google_oauth.py`, `mfa.py` |
| Authorization | RBAC | Roles/permissions | `rbac.py` |
| CSRF protection | Custom middleware | State-changing route protection | `csrf.py` |
| Rate limiting | Redis-backed | Brute-force/abuse protection | `rate_limit.py` |
| Security headers | Custom middleware (HSTS, CSP, etc.) | Browser-side hardening | `security_headers.py` |
| Audit logging | App-level event log | Compliance trail | `audit_log.py` |
| Payments | Stripe | Subscription billing | `main.py`, `.env.example` |
| Email | Resend API or SMTP | Password reset, notifications | `emailer.py`, `.env.example` |
| Containerization | Docker, Docker Compose (web/postgres/redis) | Packaging & orchestration | `Dockerfile`, `docker-compose.yml` |
| Current hosting target | Hetzner CX23 VPS (2 vCPU/4GB), explicitly named in config | Compute | `gunicorn.conf.py:2` |
| Reverse proxy / TLS termination | Not in repo | HTTPS | UNKNOWN — requires server inspection |
| Legacy/secondary deploy path | Vercel serverless (`@vercel/python`) | Appears superseded by Docker/Hetzner path | `vercel.json`, `VERCEL_DEPLOYMENT.md`, `requirements-prod.txt` |
| CI/CD | None found | — | No `.github/workflows` |
| Backups | None found | — | Confirmed gap, also flagged in `docs/security/soc2_readiness_assessment.md` (C-01) |

**Note on the Vercel path**: The repository contains a `vercel.json`,
`VERCEL_DEPLOYMENT.md`, and a `requirements-prod.txt` clearly built for
serverless (SQLite falls back to `/tmp` when `VERCEL` env var is set —
`database.py:18`). This looks like an earlier or parallel deployment target.
The Hetzner-specific tuning in `gunicorn.conf.py`, the full Postgres/Redis
Compose stack, and `docker-compose.yml`'s production-grade health checks are
stronger, more recent evidence of the **actual current production
deployment being Docker Compose on a VPS**, not Vercel. This should be
confirmed with the team/server inspection (Part 17) before treating Vercel
as dead, since a live Vercel deployment would materially change the AWS
migration plan.

---

## 3. Programming Languages

Summarized above in Part 2. In one line: **the entire product is Python**
(FastAPI backend, server-rendered Jinja2/HTML frontend, SQL via SQLAlchemy).
There is no separate frontend language/runtime (no Node.js, no JS framework)
and no other backend language.

---

## 4. Current Server Architecture

### What can be determined from the repository

```
User (browser)
   │  HTTPS (assumed — HSTS header sent by app; TLS termination point unknown)
   ▼
DNS  (BASE_URL env var holds the public domain; DNS provider UNKNOWN)
   │
   ▼
Internet
   │
   ▼
??? TLS termination — UNKNOWN, requires server inspection
   │  (no nginx/Caddy/Traefik config in repo; app itself does not terminate TLS)
   ▼
Host: single VPS, sized per gunicorn.conf.py comment as
      "Hetzner CX23 (2 vCPU, 4 GB RAM)"
   │
   ▼
Docker Compose (docker-compose.yml), one bridge network "internal":
   ┌─────────────────────────────────────────────────────────┐
   │  container: web           container: postgres            │
   │  - Dockerfile image       - postgres:16-alpine            │
   │  - gunicorn + 2 uvicorn   - volume: pgdata                │
   │    workers, port 8000     - healthcheck: pg_isready       │
   │  - published 8000:8000                                    │
   │                            container: redis                │
   │                            - redis:7-alpine, AOF persist   │
   │                            - volume: redisdata             │
   └─────────────────────────────────────────────────────────┘
   │
   ▼
Application data / storage:
   - Postgres: users, contracts (contract_text ENCRYPTED at app layer,
     AES-256-GCM), playbooks, findings, audit events — all in one DB
   - Redis: sessions + rate-limit counters (ephemeral, AOF-persisted)
   - Uploaded files are NOT written to disk or object storage — parsed
     in-memory, extracted text stored (encrypted) directly in Postgres
   - Generated PDF reports: templates/pdf_report.html + fpdf2 — whether
     these are written to disk (static/reports/ exists in the repo tree)
     or streamed directly to the client is UNKNOWN without deeper code
     tracing beyond this audit's scope; if written under static/reports/,
     they live on the same ephemeral container/host filesystem
   │
   ▼
External services: OpenAI API (finding explanations only), Stripe (billing),
Google OAuth (login), Resend/SMTP (email)
```

### Answering the specific questions

- **What receives HTTP/HTTPS traffic?** UNKNOWN — requires server inspection. The repo shows the app listening on port 8000 inside Docker; nothing in the repo shows what's in front of it on 80/443.
- **Where is TLS terminated?** UNKNOWN — requires server inspection. No TLS certs, Nginx/Caddy/Traefik config, or ACME client config exist in the repo.
- **Which ports are exposed?** Confirmed: `8000` (Compose `ports: "8000:8000"`). Any 80/443 exposure is outside this repo. **UNKNOWN** whether Postgres (5432) or Redis (6379) are ever exposed to the host — the Compose file does **not** publish them to the host (no `ports:` block on those services), so by default they are reachable only inside the Compose network — this is a good practice already in place.
- **What Docker containers run?** Confirmed: `web`, `postgres`, `redis` (3 containers). No reverse-proxy or ClamAV container is defined by default (ClamAV is opt-in per `docs/security/upload_hardening_infra.md`).
- **What runs inside each container?** `web`: Gunicorn + 2 Uvicorn workers running the FastAPI app. `postgres`: stock Postgres 16 Alpine image. `redis`: stock Redis 7 Alpine image with AOF persistence and a 128 MB memory cap (`docker-compose.yml`: `--maxmemory 128mb --maxmemory-policy allkeys-lru`).
- **How do containers communicate?** Over the Docker Compose bridge network `internal`, by service name (`postgres`, `redis`) — confirmed by `DATABASE_URL`/`REDIS_URL` construction in `docker-compose.yml`'s `environment:` block for `web`.
- **Where is application data stored?** Postgres named volume `pgdata`, on whatever host filesystem the VPS uses.
- **Where are uploaded contracts stored?** Nowhere persistent as files — extracted text goes straight into the encrypted `contract_text` Postgres column (`models.py:80`); no S3/object storage or upload-directory volume exists in the repo.
- **Where is the database stored?** Docker named volume `pgdata` on the VPS's local disk.
- **What survives container recreation?** Named volumes (`pgdata`, `redisdata`) survive `docker compose up`/container restarts and even `docker compose down` (without `-v`). They do **not** survive host/disk loss, since nothing backs them up off-host.
- **What happens if the server dies?** Total outage: application, database, and Redis sessions are all on the same single VPS. There is no standby, no replication, no automated failover in the repository. **This is the single biggest infrastructure risk** (see Part 3).
- **What happens after reboot?** `restart: unless-stopped` is set on all three services (`docker-compose.yml`), so Docker will restart containers automatically on daemon start, assuming Docker itself is configured to start on boot at the OS level (UNKNOWN — that's host/systemd config, not in this repo).
- **How are backups performed?** Not evidenced in the repository at all. **UNKNOWN — requires server inspection** to confirm whether an out-of-band backup process (e.g., a cron job not committed to this repo) exists on the actual VPS.
- **How are secrets stored?** A plain `.env` file consumed via `env_file:` in Compose (`docker-compose.yml`) and `python-dotenv` (`main.py`). No secrets manager. `.env` is git-ignored (`.gitignore` presumably covers it — confirmed indirectly by `.env.example` being the checked-in template and no `.env` appearing in the file listing).
- **How are deployments currently performed?** UNKNOWN — requires server inspection. No CI/CD, no deploy script, no `Makefile` deploy target (the repo's `Makefile` only runs experiments, not deployment). Most likely a manual `git pull && docker compose up -d --build` on the VPS, but this is inferred, not confirmed.
- **Is there staging?** No evidence of a staging environment/config in the repository.
- **Is there automatic rollback?** No evidence found.
- **Is there health checking?** Yes, at the container level: `/health` endpoint + Docker/Compose `healthcheck:` blocks for all three services (`main.py`, `Dockerfile`, `docker-compose.yml`). This is liveness/readiness only, not external synthetic monitoring.
- **Is there monitoring/alerting?** No evidence of metrics collection, uptime monitoring, or alerting in the repository.
- **Is there redundancy?** None. One VPS, one web container, one DB container, one Redis container.
- **Is the architecture currently a single point of failure?** **Yes, comprehensively.** The VPS is a single point of failure for compute, database, session store, and (implicitly) file storage, since everything lives in Docker volumes on that one host's disk.

---

## 5. Current Deployment Process

Not evidenced in the repository beyond the artifacts themselves (Dockerfile,
Compose file, `.env.example`). No CI/CD pipeline, no deploy scripts, no
documented runbook for pushing new code to production was found.
**UNKNOWN — requires server inspection / team knowledge** for the actual
day-to-day deploy mechanics (SSH + `docker compose up -d --build`, or
something more automated that simply isn't checked into this repo).

---

## 6. Current Infrastructure Risks (Production-Readiness Assessment)

Classification reflects the **current state of the code as inspected**, which
in several areas (encryption, CSRF, rate limiting, MFA, security headers) is
materially better than the repository's own `docs/security/soc2_readiness_assessment.md`
(dated 2026-07-22) suggests — that document is a useful historical artifact
but is stale relative to the current codebase and should not be quoted as
today's state. This section reflects direct code inspection instead.

| # | Area | Rating | Notes |
|---|---|---|---|
| 1 | Single point of failure (whole stack) | **CRITICAL** | One VPS runs app + DB + Redis. See Part 4. |
| 2 | Server failure | **CRITICAL** | No standby/failover; total outage on VPS loss. |
| 3 | Disk failure | **CRITICAL** | `pgdata`/`redisdata` are local Docker volumes on one disk; no replication. |
| 4 | Database failure | **CRITICAL** | Single Postgres instance, no replica, no automated backup found. |
| 5 | Region/data-center failure | HIGH | Single-region by construction (one VPS); acceptable to defer full multi-region at this scale, but total loss of that datacenter = total outage. |
| 6 | Backup strategy | **CRITICAL** | No backup mechanism found anywhere in repo. Confirmed by repo's own SOC2 doc finding C-01. |
| 7 | Restore testing | CRITICAL (moot without #6) | Cannot test restores that don't exist. |
| 8 | TLS | MEDIUM | App sends HSTS/security headers and supports `SECURE_COOKIES`, but where TLS is actually terminated is unconfirmed (UNKNOWN — requires server inspection). Treat as MEDIUM risk pending confirmation, not CRITICAL, since HSTS implies HTTPS is in active use. |
| 9 | Firewall/network exposure | MEDIUM | Compose does not publish Postgres/Redis ports to host (good). Host-level firewall (ufw/iptables/cloud security group) is UNKNOWN. |
| 10 | Secrets management | MEDIUM | Plain `.env` file, no rotation, but the app enforces non-default secrets in production for the security-critical values (`.env.example` "REQUIRED — change from defaults") and encryption keys are validated at startup (`encryption.py` `validate_startup()`). Not GOOD because no rotation/KMS/audit trail on secret access; not HIGH because there is real startup enforcement against known-bad defaults. |
| 11 | Encryption at rest | **GOOD / ALREADY ADDRESSED** | AES-256-GCM app-layer envelope encryption of `contract_text` and other sensitive JSON columns, versioned key IDs, key rotation supported (`encryption.py`, `models.py`). This directly resolves what the repo's own older SOC2 doc lists as Critical C-02 — confirms that doc is stale. |
| 12 | Encryption in transit | MEDIUM | Depends on the unconfirmed TLS termination point (#8); OpenAI/Stripe/Google calls are HTTPS by library default. |
| 13 | Contract/document storage | GOOD | Not stored as files at all — encrypted DB column only, minimizing loose-file exposure surface, but this also means DB backup loss = total data loss (ties back to #6). |
| 14 | Database security | MEDIUM | Not exposed to host network; credentials via env var; no evidence of least-privilege DB roles (app likely uses one superuser-ish role) — UNKNOWN in detail. |
| 15 | Container security | GOOD | Non-root user (`triage`) in the app container, minimal base image (`python:3.12-slim`), Compose health checks. |
| 16 | Docker image vulnerabilities | MEDIUM | No image scanning (Trivy/Grype/ECR scan) evidenced anywhere. |
| 17 | Python dependency vulnerabilities | MEDIUM | Most packages pinned; several allowed as open ranges (`openai`, `fpdf2`, `python-dotenv`, `sqlalchemy`, `user-agents` — `requirements.txt`). No automated vulnerability scanning (pip-audit/Safety/Dependabot) found. |
| 18 | Dependency patching | MEDIUM | Manual only; no automation found. |
| 19 | Logging | MEDIUM | Structured-ish access/error logs to stdout with rotation caps; no central aggregation/search. |
| 20 | Monitoring | HIGH | `/health` exists but nothing external polls it; no metrics/dashboards found. |
| 21 | Alerting | HIGH | None found. |
| 22 | Incident recovery | HIGH | No runbooks, no DR plan, no on-call process evidenced. |
| 23 | Deployment safety | HIGH | No CI, no tests-gate-deploy mechanism, no staged rollout — deploys are manual and unverified by tooling. |
| 24 | Rollback | HIGH | No automated rollback mechanism found. |
| 25 | Dev vs prod isolation | MEDIUM | `DEV_MODE` flag exists and gates dangerous defaults (`.env.example`), but no separate staging environment/infra was found. |
| 26 | AI-provider privacy/data exposure | GOOD | Hard architectural boundary prevents full contract text from reaching OpenAI; only short, sanitized excerpts tied to specific findings are sent (`evaluator.py`). This is a genuinely strong control for a legal product. |
| 27 | Tenant/customer isolation | MEDIUM | Single shared DB with `user_id` foreign-key filtering (application-level multi-tenancy), not DB-level tenant isolation (e.g., row-level security, per-tenant schemas). Reasonable at current scale; would need row-level security or similar if compliance requirements tighten. |
| 28 | Rate limiting | **GOOD / ALREADY ADDRESSED** | Redis-backed rate limiting present (`rate_limit.py`), contradicting the older SOC2 doc's "Missing" rating — confirms code has moved on since that doc was written. |
| 29 | Authentication/session security | GOOD | PBKDF2-HMAC-SHA256 password hashing, HttpOnly/SameSite cookies, TOTP MFA (`mfa.py`), Redis-backed sessions surviving restarts. Google OAuth signature verification depth not re-verified in this pass — worth a follow-up spot check, but out of scope here. |
| 30 | Audit logs | MEDIUM | `audit_log.py` exists and is called from sensitive flows (deletions, retention cleanup, etc.), but no evidence of log immutability, off-host shipping, or long-term retention policy. |

### Detail on CRITICAL/HIGH items

**#1–4, #6–7 — Single VPS, no backups, no DR (CRITICAL)**
- *Current condition*: `docker-compose.yml` defines named Docker volumes for Postgres and Redis with zero off-host replication or backup automation. No backup service, cron job, or restore script exists anywhere in the repository.
- *Evidence*: `docker-compose.yml`; absence of any `backup`/`pg_dump`/S3-upload script in the repo tree; corroborated by the repo's own `docs/security/soc2_readiness_assessment.md` finding C-01 ("No backup, restore, or disaster recovery evidence").
- *Realistic failure scenario*: The VPS provider has a disk failure, the host is compromised/ransomwared, or an operator runs a destructive command against the live Postgres container. Every customer's contracts, analysis history, and accounts are permanently and irrecoverably lost — with zero way to reconstruct them. For a legal SaaS product, this is an existential risk, not just an inconvenience.
- *Remediation*: Move the database to a managed service with automated point-in-time backups (RDS with automated backups + a retention window), or, if staying self-hosted, add nightly `pg_dump` + off-host upload (S3) with tested restores. This is Phase 1 priority regardless of the AWS decision.

**#20–24 — No monitoring, alerting, incident recovery, deploy safety, rollback (HIGH)**
- *Current condition*: The only operational visibility is a `/health` endpoint nothing external polls, and container logs with no aggregation. Deploys are (presumed) manual `docker compose up -d --build` with no automated test gate and no rollback mechanism.
- *Evidence*: No `.github/workflows`, no monitoring agent config, no alerting integration (PagerDuty/Opsgenie/Slack webhook) anywhere in the repo.
- *Realistic failure scenario*: A bad deploy silently breaks contract analysis (e.g., an exception in `rules_engine.py` on a specific contract type) and nobody notices until a paying customer reports it days later — with no way to quickly identify which deploy introduced it or roll back cleanly.
- *Remediation*: Add basic CloudWatch/uptime-check alerting and a CI pipeline that runs the existing 138+ tests and benchmark suite before any deploy is allowed to proceed (the test suite already exists — it's just not gating anything automatically).

---

## 7. Recommended AWS Architecture

### 7.1 Deployment approach comparison

| | A. EC2 + Docker Compose | B. ECS/Fargate | C. App Runner | D. EKS/Kubernetes |
|---|---|---|---|---|
| Architecture | One (or two, for HA) EC2 instance(s) running the existing `docker-compose.yml` almost unchanged, behind an ALB | Containerize `web` as an ECS Fargate service; RDS/ElastiCache separate | Point App Runner at the existing Docker image; RDS/ElastiCache separate | Full K8s control plane, Deployments/Services/Ingress for one app |
| Benefits | Near-zero rework — same Dockerfile/Compose mental model the team already uses; cheapest; full control | No host patching; scales to zero-ish; AWS manages the control plane | Simplest managed option; auto-scaling and HTTPS built in with almost no config | Portable, huge ecosystem, best for many services/teams |
| Drawbacks | You patch the OS; manual instance replacement on failure unless in an ASG | More moving pieces (task defs, ECR, service discovery) than needed for one service; slightly higher fixed cost | Less control over networking/VPC specifics; still maturing for some enterprise needs (e.g., certain VPC connector nuances) | Wildly over-engineered for one Python monolith; steep learning curve, real ongoing ops burden |
| Security | Depends on you hardening the AMI/OS + security groups | AWS-managed runtime reduces host attack surface | AWS-managed runtime, least host surface of all options | Depends entirely on cluster hardening — most work, most ways to get it wrong |
| Availability | Single instance = SPOF unless placed in an Auto Scaling Group across 2 AZs (adds complexity close to option B) | Multi-AZ tasks behind ALB natively; easy | Multi-AZ natively, easiest of all | Multi-AZ via node groups; most capable but most complex |
| Scalability | Manual or ASG-based; coarse-grained | Native task-count autoscaling | Native, simplest autoscaling | Most powerful, most complex to tune |
| Operational complexity | **Low** | Medium | **Low** | High |
| Migration difficulty from today | **Very low** — reuse Dockerfile/Compose almost as-is | Medium — need task definitions, ECR push pipeline | Low-Medium — need ECR push pipeline, but no orchestration to design | High — not justified for one service |
| Approx. monthly cost (current scale) | **~$60–110** (1× t3.small/medium + EBS) | ~$90–150 (Fargate vCPU/mem pricing tends to run a bit above equivalent EC2, plus ALB) | ~$70–120 (pay-per-use compute + built-in ALB-equivalent) | ~$150–250+ (control plane fee alone is $73/mo, before any nodes) |

### 7.2 Recommendation: **A. EC2 + Docker Compose, evolving toward B (Fargate) later**

For TriageCounsel today — one process, no proven need for horizontal
scaling, a small team, and explicit cost sensitivity — **EC2 running the
existing Docker Compose stack (minus Postgres, which moves to RDS) behind
an Application Load Balancer** is the architecture that best satisfies
"simplest architecture that is secure and reliable enough for paying legal
customers." It requires almost no rewrite of what already exists (same
Dockerfile, same Compose file for `web` + `redis`), fixes the two CRITICAL
gaps (backups, verified encryption/TLS) via managed AWS services around it,
and keeps monthly cost close to today's ~$100 baseline.

**App Runner is a legitimate second choice** and is worth strongly
considering if the team wants to minimize ops work even further and is
comfortable with slightly less networking control — it removes the ALB/EC2
management entirely. It is not the top pick only because moving off the
Compose model the team already understands adds a small amount of near-term
migration friction (App Runner wants an image pushed to ECR, and Redis would
need to move to ElastiCache immediately rather than staying co-located).

**ECS/Fargate** becomes the natural *next* step once/if the app needs to run
more than one instance for real load reasons — the migration from "EC2 +
Compose" to "Fargate" is comparatively easy since both are "run this same
Docker image" models. **EKS is explicitly not recommended** — there is one
service, one team, and no multi-service/multi-team orchestration need that
would justify Kubernetes' operational overhead and $73/month control-plane
floor before a single node is even added.

### 7.3 Service-by-service mapping for the recommended architecture

| AWS Service | Classification | Maps to / Why |
|---|---|---|
| EC2 (1× t3.small or t3.medium) | **REQUIRED NOW** | Replaces the Hetzner CX23 VPS; runs `web` + `redis` containers via the existing Docker Compose file. |
| RDS for PostgreSQL (db.t4g.micro/small, single-AZ) | **REQUIRED NOW** | Replaces the `postgres` container/volume. Fixes CRITICAL #1 (backups) via automated snapshots — the single highest-priority gap found in this audit. |
| Application Load Balancer | **REQUIRED NOW** | Terminates TLS with an ACM certificate (fixes the unconfirmed TLS-termination gap), health-checks `/health`, gives a stable DNS target. |
| ACM (AWS Certificate Manager) | **REQUIRED NOW** | Free TLS certificate for the ALB listener. |
| Route 53 | **RECOMMENDED NOW** | Clean DNS management and health-check-based failover readiness; not strictly required if the domain is already hosted elsewhere and just CNAME'd to the ALB. |
| S3 | **REQUIRED NOW** | Target for encrypted database backup exports (`pg_dump` → S3, or RDS automated snapshots which are S3-backed automatically) and any generated PDF report artifacts that should outlive the instance. |
| Secrets Manager | **RECOMMENDED NOW** | Replaces the plain `.env` file for `OPENAI_API_KEY`, `STRIPE_SECRET_KEY`, `ENCRYPTION_KEYS`, `SESSION_SECRET`, DB credentials — directly addresses the "no rotation, no audit trail" gap noted in Part 6, #10. |
| KMS | **RECOMMENDED NOW** | Backs Secrets Manager encryption and RDS storage encryption; can also hold the application's own AES-256-GCM keys for `encryption.py` if you want managed rotation instead of manual `.env` rotation. |
| CloudWatch (Logs + basic Alarms) | **REQUIRED NOW** | Centralizes the container logs currently only rotated locally; alarms on EC2/RDS health, disk, CPU — directly addresses HIGH #20/#21 (no monitoring/alerting). |
| CloudTrail | **RECOMMENDED NOW** | Low/no cost for the management-event trail; gives an audit record of AWS account activity, useful for the SOC2 roadmap already documented in the repo (`SOC2_ROADMAP.md`). |
| AWS Backup | **RECOMMENDED NOW** | Centralizes and schedules RDS/EBS snapshot retention policy in one place rather than relying only on RDS's default automated backups. |
| VPC (with public + private subnets) | **REQUIRED NOW** | Standard network isolation: ALB in public subnets, EC2 + RDS in private subnets. |
| NAT Gateway | **LATER / cost-conscious NOT NEEDED YET** | Only required if the private-subnet EC2 instance needs outbound internet access (it does — for OpenAI/Stripe/Google calls) **unless** you instead place the EC2 instance in a public subnet with a tightly scoped security group, which is the cheaper, still-reasonably-secure option at this scale (see cost notes, Part 9). Recommendation: skip the NAT Gateway initially and use a public-subnet EC2 with a locked-down security group + no direct SSH from the internet (use SSM Session Manager instead); revisit NAT once there are multiple private-subnet resources needing egress. |
| Security Groups | **REQUIRED NOW** | ALB SG allows 443 from the internet; EC2 SG allows 8000 only from the ALB SG; RDS SG allows 5432 only from the EC2 SG. |
| IAM roles | **REQUIRED NOW** | EC2 instance role scoped to only what it needs (Secrets Manager read, S3 backup-bucket write, CloudWatch Logs write) — no long-lived AWS access keys on the instance. |
| GuardDuty | **LATER** | Valuable, but a recurring cost best added once there's a team/process to actually respond to its findings; not required for initial cutover. |
| AWS WAF | **LATER** | The app already has CSRF/rate-limiting/security headers at the app layer; WAF adds defense-in-depth (e.g., managed bot/IP-reputation rules) but isn't required for a legal-vertical SaaS at 1–25 customers. Revisit once traffic/abuse patterns justify it. |
| ECR | **NOT NEEDED for Option A** | Only needed if/when you move to ECS/Fargate or App Runner. |
| ECS/Fargate | **LATER** | The natural next step once real horizontal-scale or zero-downtime-deploy needs emerge. |
| SES | **LATER** | Repo already supports Resend/SMTP for email (`emailer.py`); SES is a cheaper drop-in replacement worth adopting alongside the migration, but is not a blocker. |
| SQS | **NOT NEEDED** | No queue-based architecture exists or is currently needed — the app is synchronous by design (Part 2, AI section). |
| Lambda | **NOT NEEDED** | No serverless-function-shaped workload in the current design (the legacy Vercel path used a different serverless model entirely, not Lambda). |
| ElastiCache (Redis) | **LATER** | Redis currently just holds sessions/rate-limit counters and lives happily as a container on the same EC2 instance at this scale. Move to ElastiCache once you run more than one app instance (so all instances share one session store) — i.e., exactly when you move to option B (Fargate). |
| Auto Scaling Group | **LATER** | Add once there's a second instance to manage (multi-AZ HA or real load-based scaling); not required for the initial single-instance cutover. |
| RDS Multi-AZ | **LATER** | Meaningful availability upgrade, but roughly doubles RDS cost. Start single-AZ with automated backups + snapshots (which already solves the CRITICAL backup gap); add Multi-AZ once paying-customer SLAs demand it. |

### 7.4 Current component → AWS replacement → Why

| Current component | AWS replacement | Why |
|---|---|---|
| Hetzner CX23 VPS | EC2 (t3.small/medium) | Same "one box running Docker Compose" model, now with AWS's networking/IAM/snapshot tooling around it |
| `postgres` container + `pgdata` volume | RDS for PostgreSQL | Automated backups solve the #1 CRITICAL finding; same Postgres engine, no app code changes needed beyond `DATABASE_URL` |
| `redis` container (kept on EC2 for now) | Stays as-is initially; ElastiCache later | No change needed until you need multi-instance session sharing |
| No reverse proxy / unconfirmed TLS | ALB + ACM | Managed TLS termination, health checks, single stable endpoint |
| Plain `.env` file | Secrets Manager | Rotation, access auditing, IAM-scoped read access instead of a flat file on disk |
| No backups | RDS automated backups + AWS Backup + S3 | Directly resolves the repo's own documented C-01 finding |
| No monitoring | CloudWatch Logs + Alarms | Turns the existing `/health` endpoint and container logs into something that actually pages someone |
| No CI/CD | GitHub Actions (see Part 8) | The 138+ existing tests and benchmark suite already exist — they just need to gate deploys |

### 7.5 ASCII diagram — recommended architecture

```
                                Internet
                                    │
                                    ▼
                            Route 53 (DNS)
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   Application Load Balancer     │
                    │   (public subnets, 2 AZs)       │
                    │   TLS via ACM cert, :443         │
                    └───────────────┬───────────────┘
                                    │  :8000 (SG: ALB→EC2 only)
                                    ▼
                    ┌───────────────────────────────┐
                    │        VPC — EC2 instance        │
                    │  (public subnet initially, or     │
                    │   private + SSM Session Manager)  │
                    │                                    │
                    │  Docker Compose:                   │
                    │   ┌───────────┐   ┌────────────┐   │
                    │   │   web     │   │   redis    │   │
                    │   │ Gunicorn+ │   │ sessions + │   │
                    │   │ Uvicorn   │   │ rate limit │   │
                    │   └─────┬─────┘   └────────────┘   │
                    │         │  IAM instance role:        │
                    │         │  Secrets Manager read,      │
                    │         │  S3 backup write,           │
                    │         │  CloudWatch Logs write      │
                    └─────────┼─────────────────────────┘
                              │  :5432 (SG: EC2→RDS only)
                              ▼
                    ┌───────────────────────────────┐
                    │  RDS PostgreSQL (single-AZ,       │
                    │  private subnet, automated        │
                    │  backups, encrypted storage)       │
                    └───────────────────────────────┘

        Secrets Manager ◄── EC2 reads OPENAI_API_KEY, STRIPE_SECRET_KEY,
                             ENCRYPTION_KEYS, DB creds at container start

        S3 ◄── nightly encrypted backup export / AWS Backup snapshots
        CloudWatch ◄── container + Gunicorn logs, health alarms
        CloudTrail ◄── AWS account activity audit trail

        External services (unchanged): OpenAI API, Stripe, Google OAuth,
        Resend/SMTP — all reached via outbound HTTPS from the EC2 instance
```

---

## 8. High Availability

| Failure | What happens | Protect NOW vs LATER |
|---|---|---|
| 1. Application container crashes | Docker `restart: unless-stopped` restarts it automatically on the same instance (same as today); brief downtime during restart. | **NOW** — already true today, keep it. |
| 2. EC2 instance/ECS task dies | Single EC2 instance: the app is down until manually replaced/rebooted, unless placed in an Auto Scaling Group (min/max=1, multi-AZ) which AWS will auto-replace. | **NOW-ish**: a simple ASG with desired-capacity=1 is cheap insurance and worth adding at cutover; full multi-instance HA is **LATER**. |
| 3. Database becomes unavailable | Single-AZ RDS: brief outage during underlying host issues; RDS auto-recovers on the same AZ in most cases; a true AZ-level failure requires Multi-AZ to fail over automatically. | Automated backups = **NOW**. Multi-AZ failover = **LATER**, once paying-customer uptime SLAs justify ~2x RDS cost. |
| 4. Availability zone fails | Single-AZ EC2 + single-AZ RDS = outage until manual recovery in another AZ. | **LATER** — acceptable risk at 1–25 customers; revisit with Multi-AZ RDS + a second EC2 in another AZ behind the ALB once customer count/contract value justifies it. |
| 5. AWS region fails | Total outage; no cross-region DR. | **NOT justified now** — multi-region is expensive and operationally heavy; defer indefinitely until scale/compliance requires it. |
| 6. Deployment contains a bug | Today: no gate, ships straight to production. With CI (Part 10): tests + benchmark suite run before deploy; a health-check-gated deploy can auto-rollback if `/health` fails post-deploy. | **NOW** — this is cheap (GitHub Actions + the tests that already exist) and high-value. |
| 7. Python dependency update breaks behavior | Pinned versions in `requirements-docker.txt` limit surprise; CI running the existing 138+ tests before deploy catches most regressions. | **NOW** via CI; automated dependency-update PRs (Dependabot) reviewed manually — **LATER** for full automation. |
| 8. External AI provider (OpenAI) becomes unavailable | Already handled gracefully by design: the deterministic rules engine is the source of truth, and `LLMEvaluator` degrades without crashing if the OpenAI client can't be built or a call fails (`evaluator.py`). | **Already GOOD** — no AWS-side change needed; verify request-level try/except around the live API call itself continues this pattern (not fully re-verified in this pass). |

**What we should protect against now**: instance crash auto-restart (already
true), database backups (RDS automated backups — cheap, essential), and a
CI gate on deploys (uses tests that already exist).

**What is unnecessary at current size**: multi-region DR, RDS Multi-AZ,
cross-AZ EC2 fleets, and anything resembling active-active infrastructure.
These are real future needs, not today's needs — building them now would
directly violate the "don't over-engineer" objective.

---

## 9. Security Architecture

| Control | Current state | AWS service that helps |
|---|---|---|
| Encryption at rest | Already strong at the app layer (AES-256-GCM, `encryption.py`) | RDS storage encryption (KMS-backed) adds a second, infrastructure-level layer under the existing app-layer encryption — defense in depth, not a replacement |
| Encryption in transit | HSTS set by the app; TLS termination point currently unconfirmed | ALB + ACM gives a known-good, auto-renewing TLS termination point |
| Customer-document storage | Not stored as files — encrypted DB column only | N/A — this is already a good design choice; keep it |
| Database encryption | App-layer only today | RDS encryption-at-rest (KMS) as a second layer |
| Secrets | Plain `.env` file | Secrets Manager: rotation, IAM-scoped access, audit trail via CloudTrail |
| IAM / least privilege | N/A (no cloud IAM exists yet — self-hosted VPS) | Scoped EC2 instance role (Secrets Manager read, S3 backup write, CloudWatch write only) — no standing AWS access keys anywhere |
| Network isolation | Compose network isolates Postgres/Redis from the host's public interface already | VPC private subnets for RDS + (optionally) EC2; security groups enforcing ALB→EC2→RDS only |
| Vulnerability scanning | None found | Amazon Inspector (EC2 + ECR image scanning) — add once there's an image registry (i.e., when/if you move to ECR-based deploys) |
| Dependency scanning | None found | Not AWS-specific — add Dependabot/pip-audit in CI (Part 10) |
| Docker image scanning | None found | Amazon Inspector or `docker scan`/Trivy in CI, before the image ever reaches EC2 |
| Audit logging | App-level (`audit_log.py`) exists but not shipped off-host | CloudWatch Logs (ship container logs there) + CloudTrail (AWS-level account activity) |
| Access logging | ALB access logs to S3 | Gives you request-level access logs independent of the app itself |
| Backups | None found — CRITICAL gap | RDS automated backups + AWS Backup policy + S3 |
| Restore testing | N/A (nothing to restore) | Schedule a quarterly restore-to-scratch-RDS-instance drill once backups exist |
| Incident response | No runbooks found | Not AWS-specific — write a short runbook once CloudWatch alarms exist to actually trigger one |
| Retention/deletion | `retention.py`/`run_retention_cleanup.py` exist but nothing invokes them automatically today | EventBridge Scheduler → the existing `POST /internal/retention/cleanup` endpoint (already built for exactly this — bearer-token protected via `CRON_SECRET`, per `.env.example` and `retention.py`) — this requires zero new app code |
| AI-provider data handling | Strong architectural boundary already (excerpts only, never full text) | No AWS service needed here — this is an app-design control, already good |

---

## 10. CI/CD & Regression Strategy — Safe Deployment Pipeline

### What already exists
- **Unit/integration tests**: 138+ files under `tests/`, pytest-based.
- **Regression/benchmark suite**: extensive adversarial/held-out corpora under `benchmarks/`/`scripts/` validating rules-engine correctness and LLM-boundary behavior — unusually strong for a product at this stage.
- **Container build**: `Dockerfile` already builds a clean, health-checked, non-root image.
- **Health verification hook**: `/health` endpoint already exists and is already used by Docker health checks.

### What's missing (the whole left-to-right pipeline requested)

```
Developer → Git → CI [MISSING] → Unit tests [exist, not gating] →
Integration/regression tests [exist, not gating] →
Dependency/security scan [MISSING] → Container build [exists manually] →
Container vulnerability scan [MISSING] → Staging [MISSING] →
E2E regression [partially exists as integration tests] →
Approval [MISSING] → Production [manual, unconfirmed] →
Health verification [exists, not wired to deploy] →
Rollback if necessary [MISSING]
```

### Recommendation

**GitHub Actions** is the right choice — the repository is already on
GitHub, there's no existing CI tool to migrate away from, and it integrates
natively with pull requests (no new vendor/account needed). Recommended
pipeline, built almost entirely from things the repo already has:

1. **On every PR**: `pytest` (existing 138+ tests) + the benchmark/regression suite already in `benchmarks/`/`scripts/` + a dependency scan (`pip-audit`) + a container vulnerability scan (Trivy) on the built image.
2. **On merge to `main`**: build and push the Docker image to ECR (only new infra needed for this step), then deploy to a staging EC2/environment (can be a second small EC2 instance, or — cheaper — a scheduled task that deploys to the same instance's staging port during off-hours if a second instance isn't yet justified).
3. **Manual approval gate** (a GitHub Actions "environment" with required reviewers) before promoting the same tested image to production.
4. **Deploy to production**: pull the new image, `docker compose up -d`, then poll `/health` for N seconds.
5. **Automatic rollback**: if `/health` doesn't return healthy within the timeout, redeploy the previous image tag automatically.

This is a modest addition — no new services beyond GitHub Actions + ECR (needed anyway once you're pushing versioned images) — but it converts "no deployment safety net at all" into a real gate, using tests the team has already invested heavily in building.

---

## 11. AWS Cost Estimate

All figures are monthly, us-east-1-style pricing, rounded to realistic
ranges. These are estimates for planning, not a quote.

**Baseline for comparison — confirmed current spend**: $6.49/month Hetzner
CX23 VPS + under $5/month OpenAI API = **~$11–12/month total**. Every
scenario below is measured against that, not against a hypothetical
$100/month baseline. Scenario A alone represents roughly a **5–12x**
increase over current spend for the AWS infrastructure portion alone.

### SCENARIO A — Prototype (1–5 customers, low volume)

| Item | Estimate |
|---|---|
| EC2 t3.small (2 vCPU, 2GB) or t3.medium (4GB) | $15–30 |
| RDS db.t4g.micro, single-AZ, 20GB gp3 | $15–25 |
| ALB | $18–20 (fixed) + minimal LCU |
| S3 (backups, small volume) | $1–3 |
| Data transfer | $2–5 |
| CloudWatch (basic logs/alarms) | $3–8 |
| Secrets Manager (5–8 secrets) | $2–4 |
| Route 53 (hosted zone + queries) | $1–2 |
| **AWS subtotal** | **~$60–100** |
| OpenAI API (low volume) | $10–40 |
| **Total infra + AI** | **~$70–140/month** |

### SCENARIO B — Early production (5–25 customers)

| Item | Estimate |
|---|---|
| EC2 t3.medium | $30 |
| RDS db.t4g.small, single-AZ, 50GB gp3 | $30–45 |
| ALB | $20–25 |
| S3 (backups + report artifacts) | $3–6 |
| Data transfer | $5–15 |
| CloudWatch | $8–15 |
| Secrets Manager | $3–5 |
| Route 53 | $1–2 |
| AWS Backup (managed retention policy) | $2–5 |
| **AWS subtotal** | **~$100–150** |
| OpenAI API | $50–150 |
| **Total infra + AI** | **~$150–300/month** |

### SCENARIO C — Growth (25–100 customers)

| Item | Estimate |
|---|---|
| EC2 (t3.large, or 2× t3.medium in an ASG for HA) | $60–120 |
| RDS db.t4g.medium, consider Multi-AZ now | $80–170 (single-AZ) / $160–340 (Multi-AZ) |
| ALB | $25–35 |
| ElastiCache (Redis, now shared across instances) | $25–50 |
| S3 | $5–15 |
| Data transfer | $15–40 |
| CloudWatch | $15–30 |
| Secrets Manager, GuardDuty (now worth adding) | $10–20 |
| **AWS subtotal** | **~$235–460 (single-AZ RDS) / ~$315–630 (Multi-AZ)** |
| OpenAI API | $200–600 |
| **Total infra + AI** | **~$435–1,230/month** |

### SCENARIO D — Larger deployment (100–500 customers)

| Item | Estimate |
|---|---|
| Compute — likely ECS/Fargate by now, autoscaled | $200–500 |
| RDS Multi-AZ, larger instance class | $300–700 |
| ALB | $40–70 |
| ElastiCache | $50–120 |
| S3 | $15–40 |
| Data transfer | $50–150 |
| CloudWatch/observability (worth a dedicated tool by now) | $50–150 |
| WAF + GuardDuty + Secrets Manager | $50–100 |
| **AWS subtotal** | **~$755–1,830** |
| OpenAI API | $800–2,500+ |
| **Total infra + AI** | **~$1,550–4,300+/month** |

### Fixed-cost traps to watch

- **ALB**: ~$18–25/month *just to exist*, before any traffic — worth it here for TLS + health checks, but don't add a second one per environment casually.
- **NAT Gateway**: ~$32/month **plus** per-GB data processing charges — this is why the recommendation above avoids it initially by using a public-subnet EC2 with a locked-down security group instead of a private-subnet instance requiring NAT for outbound OpenAI/Stripe calls.
- **RDS Multi-AZ**: roughly **doubles** RDS cost for a synchronous standby — defer until customer-facing SLAs require it (Scenario C+).
- **WAF**: per-web-ACL + per-rule + per-request charges add up faster than expected under bot traffic — defer to Scenario C+.
- **GuardDuty**: reasonable at low volume but scales with CloudTrail/VPC Flow Log/DNS log volume — fine to add early, just budget for it, don't let it surprise you as traffic grows.
- **Excessive CloudWatch Logs**: verbose access logs (especially Gunicorn's `%(D)s` per-request timing already configured in `gunicorn.conf.py`) can generate a surprising ingestion+storage bill — set log retention (e.g., 30–90 days) rather than "never expire."

### Where to safely save money

- Skip NAT Gateway initially (see above) — biggest single avoidable fixed cost.
- Single-AZ RDS with automated backups is enough for Scenarios A/B — Multi-AZ is the single most deferrable "nice to have."
- Skip WAF/GuardDuty until Scenario C, where GuardDuty in particular starts paying for itself against real distributed abuse patterns.
- Right-size EC2/RDS instance classes to actual measured CPU/memory (start at t3.small/t4g.micro, scale up only when CloudWatch shows sustained pressure) rather than over-provisioning "just in case."

---

## 12. Migration Plan

| Phase | Actions | Risk | Expected downtime | Rollback | Effort |
|---|---|---|---|---|---|
| 0 — Audit | This document + the read-only server inspection in Part 13, run against the actual production VPS. | None (read-only) | None | N/A | 0.5–1 day |
| 1 — AWS foundation | Create VPC (public+private subnets, 2 AZs), security groups, IAM roles, S3 backup bucket, Secrets Manager entries (populated from the current `.env`, not committed anywhere). | Low | None | Delete the new AWS resources; nothing in production touched yet. | 1–2 days |
| 2 — Database | Stand up RDS Postgres. Take a `pg_dump` of the current production DB (or use AWS DMS for a lower-downtime path), restore into RDS, verify row counts/checksums against source. | Medium — data-integrity risk if dump/restore is rushed | None yet (RDS is a parallel copy, not cutover) | Simply don't cut over; RDS instance can be deleted with no impact to the live VPS. | 1–2 days |
| 3 — Document storage | N/A for object storage (contracts are DB rows, not files) — confirm during Phase 0 inspection whether generated PDF reports under `static/reports/` need an S3 target; if so, add an S3 bucket + update the report-writing code path accordingly (this is the one step that may need a small code change, not pure infra). | Low | None | Leave reports on local disk as today. | 0.5 day (pending Phase 0 findings) |
| 4 — Application deployment | Launch EC2 instance, install Docker, pull the same repo/image, point `docker-compose.yml`'s `web`/`redis` services at it, override `DATABASE_URL` to point at the new RDS instance, pull secrets from Secrets Manager into the environment at container start. Run smoke tests against the EC2 instance directly (not yet public). | Medium | None (parallel environment) | Terminate the EC2 instance; nothing public-facing changed. | 1–2 days |
| 5 — DNS | Put the ALB in front of the new EC2 instance; verify HTTPS via ACM cert; do **not** cut DNS over yet — test against the ALB's own DNS name first. | Low | None | N/A — old DNS still points at the old VPS throughout this phase. | 0.5 day |
| 6 — Staging validation | Run the full `pytest` + benchmark suite against the new AWS environment; manually exercise upload → analysis → report flows end-to-end; verify Stripe webhook delivery to the new endpoint (Stripe supports registering a second webhook endpoint temporarily for this). | Medium | None | N/A | 1–2 days |
| 7 — Production cutover | Put the app in a brief maintenance/read-only mode on the old VPS if possible (or accept a short write-freeze window); take a final `pg_dump` delta and apply it to RDS; flip DNS (Route 53 or the domain's existing registrar) to the ALB; monitor closely. | **Medium-High** — this is the one step with real customer-facing risk | **Low, if planned**: with DNS TTL pre-lowered and a short write-freeze, realistically **5–30 minutes** of write-blocked or degraded access, not full outage, since the app itself is fully warmed up and tested by this point | Flip DNS back to the old VPS (it's untouched and still running); resync any writes that happened only against RDS during the cutover window back to the old DB if needed. | 0.5–1 day, plus the freeze window itself |
| 8 — Backup/restore verification | Confirm RDS automated backups are running; perform one real restore into a scratch RDS instance and verify data integrity; document the runbook. | Low | None | N/A | 0.5–1 day |
| 9 — Monitoring/security | Wire up CloudWatch alarms (CPU, disk, RDS connections, `/health` failures), CloudTrail, and the CI pipeline from Part 10; confirm Secrets Manager rotation plan. | Low | None | N/A | 1–2 days |
| 10 — Decommission old server | Once AWS has run cleanly in production for an agreed soak period (recommend **at least 1–2 weeks**, spanning at least one billing cycle for Stripe webhook confidence), cancel/decommission the Hetzner VPS. Keep a final off-host copy of the old DB dump indefinitely as a cold archive. | Low (by this point) | None | N/A — this step is one-way by design, which is exactly why it's last and gated on a soak period. | 0.5 day |

**Total estimated effort**: roughly **2–3 weeks of focused work** for one
engineer, most of it in Phases 1–4 (foundation + parallel environment build)
and Phase 7 (the actual cutover, which deserves the most care and the
smallest blast radius). No phase before 7 touches the live system at all,
and Phase 7 itself is designed to be reversible within minutes via DNS.

---

## 13. Server Inspection Checklist (READ-ONLY)

Run these on the current production server to fill in every **UNKNOWN**
in this document. All commands below are strictly read-only: nothing here
restarts services, stops containers, modifies files, prints secret values,
alters firewall rules, installs packages, or touches the database's data.

```bash
# --- OS / kernel ---
cat /etc/os-release
uname -a
uptime

# --- CPU / memory / disk ---
nproc
free -h
df -h
lsblk

# --- Docker ---
docker --version
docker compose version
docker ps
docker ps -a
docker images
docker network ls
docker volume ls
docker inspect $(docker ps -q) --format '{{.Name}}: {{.State.Status}} (restarts: {{.RestartCount}})'

# --- Docker Compose config as actually running (no secret values printed) ---
docker compose config --services
docker compose ps

# --- Exposed ports / listeners ---
sudo ss -tulnp
sudo netstat -tulnp 2>/dev/null

# --- Processes ---
ps aux --sort=-%mem | head -30
ps aux --sort=-%cpu | head -30

# --- Firewall ---
sudo ufw status verbose 2>/dev/null
sudo iptables -L -n -v 2>/dev/null

# --- Reverse proxy / TLS (adjust paths to whatever is found) ---
which nginx caddy traefik 2>/dev/null
sudo nginx -T 2>/dev/null | grep -iE "server_name|listen|ssl_certificate " 
sudo systemctl status nginx caddy traefik 2>/dev/null
ls -la /etc/letsencrypt/live/ 2>/dev/null
sudo certbot certificates 2>/dev/null

# --- Mounted storage / where volumes live on disk ---
docker volume inspect $(docker volume ls -q)
sudo du -sh /var/lib/docker/volumes/* 2>/dev/null

# --- Database location / size (no data contents) ---
docker exec -it $(docker ps --filter "name=postgres" -q) psql -U triage -d triage -c "\l+" 2>/dev/null
docker exec -it $(docker ps --filter "name=postgres" -q) psql -U triage -d triage -c "SELECT pg_size_pretty(pg_database_size('triage'));" 2>/dev/null

# --- Memory / CPU usage snapshot ---
docker stats --no-stream

# --- Uptime of each container ---
docker inspect $(docker ps -q) --format '{{.Name}}: started {{.State.StartedAt}}'

# --- Logs (read-only tail, last N lines only) ---
docker compose logs --no-color --tail=200 web
docker compose logs --no-color --tail=200 postgres
docker compose logs --no-color --tail=200 redis

# --- Backup configuration (read-only listing, no data) ---
crontab -l
sudo systemctl list-timers --all
ls -la /etc/systemd/system/ | grep -i triage
ls -la /root/*.sh /home/*/*.sh 2>/dev/null | grep -iE "backup|deploy"

# --- Confirm which deployment path is live (Docker vs Vercel) ---
curl -sI https://<your-domain>/health   # check response headers/server banner only
```

Do **not** run anything that echoes `.env` contents, connection strings with
embedded passwords, or `docker exec ... env` — all of those would print
secret values and are intentionally excluded.

---

## 14. Unknowns Requiring Verification

- **TLS termination point** — nothing in the repo shows what (if anything) sits in front of port 8000 on 80/443. Confirmed only that the app itself sends HSTS headers.
- **Whether the Vercel deployment path is still live** — `vercel.json`/`VERCEL_DEPLOYMENT.md`/`requirements-prod.txt` exist and look functional, but the Hetzner/Docker-Compose evidence is stronger and more recent. If Vercel is still serving production traffic in parallel, this changes both the current-architecture description and the migration plan materially.
- **How deployments are currently performed** — no CI/CD or deploy script found; presumed manual.
- **Whether an out-of-band backup process exists on the VPS but simply isn't committed to this repo** (e.g., a cron job set up directly on the host).
- **Host-level firewall configuration** (ufw/iptables/cloud security group equivalent for the VPS provider).
- **Where generated PDF reports (`templates/pdf_report.html`, `static/reports/`) are ultimately written/served from** — local disk vs. streamed response — relevant to whether Phase 3 of the migration needs any code change at all.
- **DNS provider and current TTLs** — needed to plan the low-downtime cutover in Phase 7.
- **Exact current monthly hosting bill breakdown** — the user's stated "~$100/month" is the baseline this document compares AWS estimates against, but the VPS-only cost vs. any add-ons (backups, monitoring, domain) wasn't itemized.

---

## 15. Immediate Priorities (regardless of AWS timing)

These are worth doing **even before any AWS migration**, because they fix
the CRITICAL findings from Part 6 and are largely infrastructure-agnostic:

1. **Stand up automated, tested backups today** — even a simple nightly `pg_dump` piped to an off-host destination (S3, Backblaze, another server) closes the single biggest risk in this entire audit.
2. **Confirm and document the actual TLS termination setup** on the current VPS (Part 13's checklist covers this) — either it's solid and just undocumented, or it's a real gap.
3. **Add a CI pipeline** (GitHub Actions) that runs the existing 138+ tests + regression benchmarks on every PR — this is nearly free given the test suite already exists and dramatically reduces deploy risk immediately, independent of where the app is hosted.
4. **Confirm whether the Vercel deployment path is still receiving production traffic** — resolving this ambiguity is a prerequisite for planning any migration correctly.
5. **Move secrets out of the plain `.env` file** into something with rotation/audit capability — this is valuable on the current VPS too (e.g., via a self-hosted Vault) and becomes even easier once on AWS (Secrets Manager).

---

## 16. Final Recommendation

The confirmed actual current spend — **$6.49/month Hetzner + under
$5/month OpenAI, ~$11–12/month total** — changes this recommendation from
"obviously worth doing now" to "a real trade-off the team should choose
deliberately." Two honest paths follow, in order of what to consider first:

### 16.1 Lower-cost first step: fix the CRITICAL gap on the existing box

Before spending 6–10x more on AWS, the single highest-value, lowest-cost
fix is directly addressing Part 6's #1 CRITICAL finding — **no backups** —
on the current Hetzner VPS itself. Hetzner's own managed backup product
(visible in the same console screenshot used to confirm pricing, under the
"Backups"/"Snapshots" tabs) typically costs **~20% of the instance price**
(roughly **+$1.30/month** on a $6.49 instance) and would close most of the
CRITICAL/HIGH risk from losing all customer contract data to a disk or
host failure, for a trivial cost increase — no migration required. Pairing
that with a scripted nightly `pg_dump` to an off-host destination (e.g., a
$5/month Backblaze B2 or Hetzner Storage Box) closes the gap even more
robustly. Combined with the CI pipeline in Part 10 (free — GitHub Actions
on a small repo is within the free tier) and a documented TLS/reverse-proxy
setup (Part 13's checklist), a huge fraction of this audit's CRITICAL/HIGH
findings can be resolved for **well under $20/month total**, with zero
migration risk and zero downtime.

### 16.2 When AWS becomes the right move

AWS is the right move once one or more of these becomes true, not before:
- Paying legal customers start asking for a documented DR/backup posture, SOC 2 evidence, or specific cloud-provider commitments (AWS/GCP/Azure) as part of their own vendor-risk process — common in legal and enterprise procurement.
- Customer count or contract value grows enough that the ~$50–130/month *incremental* cost (Scenario A/B in Part 11, above the current ~$12/month) is trivial relative to revenue.
- The team wants managed-service operational relief (automated failover, managed patching, IAM-based access control) rather than continuing to hand-operate a single VPS.

When that time comes, the recommendation from the original analysis still
holds: **EC2 + Docker Compose for the app/Redis, RDS Postgres for the
database, and an ALB for TLS** — not ECS/Fargate, not App Runner, and
certainly not EKS. This is the smallest possible change from what already
works (same Dockerfile, same Compose mental model) that directly closes
the CRITICAL gaps this audit found: no backups and unconfirmed/unmanaged
TLS and encryption-at-rest guarantees, while adding centralized
logging/alerting and a documented recovery path. Treat ECS/Fargate as the
natural next step if/when real multi-instance scaling is needed, and treat
everything in the "LATER" column of Part 7.3 (Multi-AZ RDS, WAF,
GuardDuty, NAT Gateway, autoscaling) as deliberately deferred, not
forgotten — revisit each one as customer count and contract value justify
its cost.

**Bottom line**: don't move to AWS today purely to fix the backup gap —
that can be fixed on the current $6.49/month box for a few dollars more.
Move to AWS when the business reasons above show up, using the
architecture in Part 7 as the ready-to-execute plan for that point.

---

*This document was produced by inspecting repository files only. No
production system, server, or database was accessed or modified. Where
evidence was insufficient to answer a question, this document says so
explicitly rather than guessing.*
