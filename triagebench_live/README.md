# TriageBench Live

TriageBench (the sibling `triagebench/` package) proves the deterministic
*engine* is correct: parser, rule matching, evidence, replay, DOCX
generation — all in-process, no HTTP, no database, no browser.

**TriageBench Live proves the deployed *product* actually works for a real
customer.** It never imports an engine or app module (`rules_engine.py`,
`docx_export.py`, `main.py`, ...) — see `__init__.py` and
`tests/test_no_engine_imports.py`, which enforces this as an automated
constraint, not a convention. Every action happens the way a real customer's
browser or HTTP client would: real signup, real session cookies, real file
upload through the real `/upload` form, real page loads, real downloads,
real clicks in a real Chromium instance.

## Quick start

```bash
pip install -r requirements.txt              # the application's own deps
pip install -r triagebench_live/requirements.txt

# Start the application under test (any environment — see "Target" below)
DEV_MODE=true APP_HMAC_SECRET=... SESSION_SECRET=... python -m uvicorn main:app

# Run against it
python -m triagebench_live run --base-url http://127.0.0.1:8000 \
    --per-category 5 --workers 3 --label "pre-release"
```

Open `triagebench_live_runs/<run_id>/production_summary.html` — the
Production Readiness Report, with a Go/No-Go verdict at the top.

## Target: staging, not literally hammering production by default

`--per-category` defaults to 5 contracts per category (~20 total), not the
full 4,190-contract corpus. Each contract's journey creates a brand-new real
account (see "Fresh account per contract" below) and drives ~20-90 real HTTP
requests depending on how many findings the contract has — running the full
corpus by default would mean tens of thousands of signups against whatever
`--base-url` points at. A Principal SRE does not point an unbounded
adversarial load generator at a real production system without a deliberate
decision to do so: use `--limit`/`--per-category` to control exactly how
much load this suite generates, and point `--base-url` at staging unless a
production synthetic-monitoring run has been explicitly sized and approved.
`--workers` controls concurrency for the same reason — see "A real bug this
suite found" below for why conservative defaults matter here specifically.

## Fresh account per contract

Each contract workflow signs up a brand-new disposable account
(`corpus_source.unique_test_email`) rather than reusing one shared account.
Two reasons: it exercises the real signup flow on every single contract
(not just once), and it sidesteps the free plan's 3-contracts/month usage
limit without touching the database or granting the test account any
special treatment a real customer doesn't get.

## What each module does

```
triagebench_live/
  config.py          Paths, run-id scheme, LiveConfig
  http_client.py       LiveSession — the only way this package talks HTTP
  corpus_source.py      Prepares real upload payloads from Benchmark - TC
                        (via triagebench.html_extract — test-data prep only)
  workflow.py            The 11-step real customer journey, per contract
  docx_validate.py        Independent DOCX/ZIP validation: raw XML, python-docx,
                          mammoth — three parsers that must all agree
  security.py              Adversarial probes: IDOR, auth bypass, forged
                            decisions, session/CSRF checks
  failure_tests.py          Corrupt/huge/empty uploads, repeated verify/
                            finalize/package, interrupted downloads, races
  concurrency.py             Two real sessions on one account, racing
                            real requests against the same contract
  browser.py                Real Chromium (+ Firefox/WebKit/Edge where
                            available) driving the actual DOM
  aggregate.py               Rollups shared by reports + the dashboard
  reports.py                  The 8 CSV/HTML deliverables
  regression.py                Diffs this run against the previous one
  readiness.py                  Go/No-Go scoring — see "Scoring", below
  dashboard.py                  production_summary.html renderer
  runner.py                     Orchestrator: threaded, resumable, fault-tolerant
  finalize.py                    Ties reports/regression/dashboard together
  cli.py                          `python -m triagebench_live {run,finalize,list}`
```

## The 11-step workflow (`workflow.py`)

Signup → Login (fresh session, proving the just-created credentials really
work) → Upload (the response IS the completed analysis — `/upload` runs
`run_analysis()` synchronously, so there is no polling loop; see main.py)
→ verify the report page renders an overall-risk badge → open Review →
read the findings the page actually embeds (`const FINDINGS = {{
findings|tojson }}` in `templates/review.html` — parsed via regex over the
real HTML response, exactly like a browser-side script would) → decide on
every finding (accept/reject/edit/flag, each exercised — see `_auto_decide`)
→ comment on roughly a third of them → **reload and verify persistence**
(a fresh `GET` of the review page, decisions must survive byte-for-byte) →
Verify every finding (not just one, unlike the interactive UI) → Finalize
→ generate + download the Negotiation Package → validate the ZIP and the
DOCX inside it independently → Logout, then confirm the session is actually
dead (not just client-side).

## DOCX validation: three independent parsers (`docx_validate.py`)

1. Raw zip + stdlib `xml.etree` — structural well-formedness, exact
   `w:ins`/`w:del`/comment counts against what the decisions actually sent.
2. `python-docx` — the same library the app uses to build the file; opening
   what you wrote with the library that wrote it is a necessary check, not
   a sufficient one.
3. `mammoth` — a fully independent, third-party OOXML→HTML converter, used
   for its warning/error surface. A malformed relationship or unrecognized
   style that the other two miss shows up here.

`all_validators_agree` is only true when all three succeed with zero
warnings and the redline counts reconcile exactly with what was sent.

## Scoring (`readiness.py`)

The Production Readiness Report's verdict is computed from an explicit,
auditable rule set — not a black box:

- **Issues** are collected from every suite (contract workflow failures,
  security findings, failure-injection findings, concurrency findings,
  browser failures, regression deltas) and classified critical/high/medium
  by the same file, with the reasoning inline as code comments.
- **Readiness score** = weighted composite of workflow pass rate (55%),
  security pass rate (25%), browser pass rate (20%), minus a flat penalty
  per critical (-20) / high (-8) / medium (-2) issue — so one severe bug
  can't be diluted away by a large passing sample.
- **Commercial readiness score** additionally weighs whether the
  Negotiation Package — the actual deliverable a paying customer sends to
  a counterparty — was generated successfully, since that is the product's
  core commercial promise, not just "the app didn't return a 500."
- **Verdict**: NO-GO if any critical issue exists; CONDITIONAL GO if more
  than 3 high-severity issues or score < 70; GO otherwise.

## A real bug this suite found

During development of this suite — running it against an unmodified local
instance of this exact codebase — `main.py`'s database session handling
(`db = next(get_db())`, used on nearly every route instead of
`Depends(get_db)` or a context manager) leaked connections badly enough
that the SQLAlchemy connection pool (5 + 10 overflow, the default main.py
never overrides) exhausted after roughly two full contract workflows'
worth of sequential HTTP traffic — one Python process, no load testing
tool, no concurrency. Every request after that hung for the full 30-second
pool timeout before failing. `readiness.py`'s `_detect_infra_issues`
recognizes this failure signature automatically and reports it as a
critical blocker whenever it reproduces in a run. This is exactly the
class of bug an in-process engine benchmark structurally cannot find — it
only exists once real HTTP connections, a real connection pool, and real
sequential request volume are involved — which is the entire reason this
suite exists.

## Browser matrix (`browser.py`)

Chromium is pre-installed in this environment and is genuinely launched and
driven. Firefox, WebKit, and a real Edge channel are not installed here;
the suite attempts to launch each one and records `available: false` with
the real launch error when it can't — never a fabricated pass or a silent
omission. In a CI image with `playwright install` run for all browsers,
the same code exercises all four for real.

## Resumability, fault tolerance, concurrency model

Same append-only-JSONL pattern as `triagebench/storage.py`:
`contract_results.jsonl` is written incrementally, `--resume <run_id>`
picks up only what's left. Contract workflows run in a `ThreadPoolExecutor`
(I/O-bound HTTP waits, not CPU work — threads are correct here, unlike
`triagebench`'s process pool for CPU-bound regex matching). Every suite
(security, failure-injection, concurrency, browser) is wrapped
independently in `runner.py`'s `_run_suite` — if the target degrades badly
enough mid-run that a suite can't complete (exactly what happened during
this suite's own development), that suite is recorded as failed and the
run still finalizes with everything collected so far, rather than losing
the whole run.

## What this suite deliberately does not measure

- **Server CPU/memory.** A black-box HTTP client cannot observe a remote
  process's resource usage; that requires server-side APM/instrumentation
  (Sentry, Datadog, `/metrics`) which is out of scope for an external
  validation suite and environment-specific to wire up. `production_summary.html`
  says this explicitly rather than fabricating numbers.
- **Rule/finding correctness.** That's `triagebench/`'s job (regression
  against the deterministic engine's own prior output) and, ultimately,
  attorney review — this suite only proves the *product* faithfully
  delivers whatever the engine decided, end to end.
- **True production traffic patterns.** This is synthetic, scripted
  traffic from a known set of test accounts — real production load has
  different concurrency, payload, and usage-pattern characteristics.
