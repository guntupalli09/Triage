# Step 4B — Dashboard/Listing Aggregation Integration

## Scope

Wires `document_aggregation.aggregate_document_state` (built and dev-
benchmarked in the prior checkpoint, `bb9f936`) into the two surfaces the
task named as minimum required, plus their row-level listing
representation (§5 of `consumer_map_and_mode_contract.md`):

- `/dashboard` — new "Needs Attention" stat (`stats.attention_count`),
  per-row `data-document-state` marker + attention badge on the
  recent-contracts table.
- `/history` — new `risk=attention` filter value, per-row
  `data-document-state` marker + attention badge.

Full read-only consumer trace and the required enforcement-mode truth
table are in `artifacts/step4b/consumer_map_and_mode_contract.md`. Out of
scope for this increment (unchanged): single-document badges
(`results.html`, `review.html`, `shared_report.html`, `pdf_report.html`),
`batch_results.html`, `admin_dashboard.html` — see that document's §5 for
the explicit scope decision and rationale.

## Persistence decision

No schema migration. `document_state` is computed at read time, in
Python, per fetched row, from already-persisted
`overall_risk`/`policy_decisions_json`/`interaction_decisions_json` —
required by the encryption architecture (`EncryptedJSON` columns cannot be
filtered in SQL) and documented in the consumer map §1/§4.

## Mode-inference approximation (disclosed)

No per-contract enforcement-mode column exists. `_document_state_for_contract`
(`main.py`) infers the effective mode for `aggregate_document_state`'s
`mode` parameter from `interaction_decisions_json is not None` (a reliable
positive signal that cutover ran for that contract) — a legacy/shadow-
shaped contract (`interaction_decisions_json is None`) always passes
`mode="shadow"`, which is conservative: it can never falsely produce
`CONFIGURATION_UNRESOLVED` for an ordinary no-playbook contract, at the
cost of not being able to distinguish a genuine cutover-no-playbook case
from an ordinary legacy/shadow one (both look identical: both fields
`None`). Documented in `main.py`'s own docstring for this function and in
the consumer map.

## Production files changed

- `main.py` — new import (`document_aggregation`), new module-level
  helpers (`_document_state_for_contract`, `_needs_attention`), dashboard
  handler (attention count + per-row states), history handler
  (`risk=attention` filter branch + per-row states).
- `templates/dashboard.html` — new stat card, per-row marker + badge, grid
  adjusted from 4 to 5 columns.
- `templates/history.html` — new filter pill, per-row marker + badge.

No change to `Contract.overall_risk`'s computation, no change to any
adapter, interaction rule, or Step 4A verification code, no change to
`POLICY_ENFORCEMENT_MODE`'s default.

## PRE integration tests (through the real, running app)

`tests/test_step4b_dashboard_listing_integration.py` — `fastapi.testclient.TestClient`
against the real `main.app`, real (test) database, real `/register`,
`/upload`, `/dashboard`, `/history` routes. 19 cases covering the 15
required scenarios (some scenarios needed both a policy-only and an
interaction-bearing variant to be constructed correctly — see the disclosed
test-authoring correction below) plus the attention-filter
inclusion/exclusion and dashboard-count checks.

**Environment note**: this sandbox initially could not even collect
TestClient-based tests (`RuntimeError: starlette.testclient requires
httpx2`, then a cascade of missing packages: `dotenv`, `stripe`, `fpdf`,
`openai`, and the previously-characterized pyo3/cffi `_cffi_backend` native-
extension failure blocking `cryptography`). All of these were **environment
dependency-installation gaps**, not application defects — resolved by
installing the exact versions `requirements.txt` already pins
(`starlette==0.27.0`, `httpx==0.25.2` compatible with it, `jinja2==3.1.2`,
`cryptography`/`cffi` reinstalled to pick up the compiled `_cffi_backend`
extension the pre-installed system package was missing). A stray
unconstrained `pip install openai`/`httpx2` earlier in this same
troubleshooting sequence had transitively upgraded `starlette` to `1.6.0`,
whose `TemplateResponse(request, name, context)` signature is incompatible
with this codebase's `TemplateResponse(name, context)` call convention
used throughout `main.py` — repinning to the exact versions in
`requirements.txt` fixed this immediately. **This resolution also
unblocked `tests/test_interaction_enforcement.py`**, previously
uncollectible and flagged as an accepted, unrelated environment limitation
in the Phase 3 report — it now collects and passes cleanly, and the fuller
regression run below no longer needs to carry that caveat.

### PRE result (before wiring)

18/19 failed — every scenario expecting a material `document_state` marker
found none (`got None`), because `data-document-state` and
`stat-attention-count` did not exist in the rendered HTML at all. This is
the dashboard/listing gap reproduced through the actual application path,
not inferred from the pure function alone. Full output preserved in this
session's transcript.

### Test-authoring correction (disclosed, GTD-style)

Two defects in the test file's own predeclared expectations were found and
corrected before trusting the result, verified against the spec (not
against production's behavior):

1. `legacy_low_interaction_violation` was declared with
   `interaction_decisions=None` while expecting a material result — self-
   contradictory (no interaction data means no interaction can fire).
   Removed as a duplicate of the correctly-constructed
   `legacy_low_interaction_violation_ix` scenario (which does set an
   `ESCALATE` interaction).
2. `legacy_high_policy_clean` / `legacy_high_policy_not_applicable` were
   declared `expected_material=True`. Per `document_aggregation_spec.md`
   §3, a high-legacy-risk document with an otherwise-clean policy layer
   resolves to `CLEAN_LEGACY_ATTENTION`, deliberately excluded from the
   material-state set the new "Needs Attention" marker drives — the
   existing "High Risk" badge already flags these; a duplicate marker
   would be redundant, not a fix. Corrected to `expected_material=False`.

### POST result (after wiring)

**18/18 passed** (1957/1957 in the full `tests/` suite, 14 skipped,
0 failed — see Regression below).

## Filtering-safety verification

`test_attention_filter_includes_low_risk_material_contract` and
`test_attention_filter_excludes_genuinely_clean_contract`: a contract with
`overall_risk=low` and a confirmed `PROHIBITED` policy decision **is**
returned by `/history?risk=attention`; a genuinely clean contract (all
`ACCEPT`, all interactions `NOT_TRIGGERED`) is **not**. Policy-important
contract omitted from attention filter = **0** (measured, not assumed).

## Regression (full suite, this session)

- `python3 -m pytest tests/` (excluding the new integration file, run
  separately above): **1957 passed, 14 skipped, 0 failed** — includes
  `test_interaction_enforcement.py`, previously blocked.
- `tests/test_step4b_dashboard_listing_integration.py`: 18/18 passed.
- `benchmarks/run_interaction_benchmark.py` (existing 54-case corpus):
  unchanged, 100%, all 4 historical gates PASS.
- `scripts/step4b_run_phase4_dev_benchmark.py` (213-case Phase 4 corpus):
  unchanged, 213/213 (100%).
- `scripts/step4b_run_document_aggregation_benchmark.py` (104-case
  aggregation corpus): unchanged, 104/104, PRE false-clean still 71/104
  (that PRE number is a fixed historical measurement of the OLD behavior,
  correctly unaffected by this session's wiring), POST false-clean = 0.
- `scripts/step4a11_run_final_corpus.py` (Step 4A.11 locked 393-case
  corpus): WC=0, semantic→authority=0, determinism=100%, Clean-Verified
  Recall 58.4% (≥44.5% target) — unchanged from the post-remediation
  baseline, since no adapter/extraction file was touched.
- `scripts/step4a11_run_remediation_validation_corpus.py` (167-case
  remediation validation corpus): WC=0, wrong-ownership=0,
  semantic→authority=0, determinism=100% — unchanged.

**No new Step 4A safety regression.**

## Conclusion

The dashboard/listing safety gate named in the task is now satisfied for
the two in-scope surfaces, verified through the real running application
(not the pure function alone): a material policy violation, critical
interaction, unresolved review state, or unresolved cutover configuration
is visible on `/dashboard` (count + row badge) and retrievable via
`/history?risk=attention`, even when legacy `overall_risk` is `low`. A
genuinely clean contract is not swept into the same bucket. Full pytest
suite green at 1957/1957. No Step 4A regression across both held regression
corpora.

Remaining, explicitly out of scope for this increment (see consumer map
§5): single-document badge surfaces, batch/admin analytics surfaces.
