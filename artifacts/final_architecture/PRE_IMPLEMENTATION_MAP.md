# PRE_IMPLEMENTATION_MAP — Final Trust Architecture (Phase 0)

Branch: `claude/final-trust-architecture-cutover`, forked from
`claude/triage-fact-admission-verification-k5h57x` at commit `38f7cec`.

Per this mission's own instruction — "Do not assume prior reports are
correct... Production source and runtime behavior are authoritative" —
every claim below was re-verified directly against current code in this
pass, not copied from `artifacts/fact_admission_architecture/`. Where a
prior claim held up, it is cited, not re-derived from scratch. Where this
pass found something the prior session's artifacts did not surface
clearly, it is flagged as **NEW FINDING**.

---

## NEW FINDING (most important): the modern 12-adapter engine is dark by default

`policy_enforcement.py:52`: `DEFAULT_MODE = "shadow"`. `get_enforcement_mode()`
reads `POLICY_ENFORCEMENT_MODE` from the environment, defaulting to
`"shadow"` if unset. Traced the actual branch in
`apply_policies_for_review()` (`policy_enforcement.py:767-809`):

- **`mode == "cutover"`**: runs `apply_active_policies()` (the 12-adapter
  engine) AND, only here, `interaction_enforcement.apply_interaction_rules()`
  (`policy_enforcement.py:793`) — the single integration point for
  `interaction_engine_core.evaluate()`.
- **`mode == "legacy"` or `mode == "shadow"`** (i.e. every other setting,
  including the actual default): the user-visible result comes ONLY from
  `apply_liability_policy()` — the OLD, liability-only legacy path. In
  `"shadow"` mode, `run_shadow_comparison()` additionally runs the modern
  engine **diagnostically**, but explicitly "must never affect the
  user-visible legacy result already computed above" (comment,
  `policy_enforcement.py:800-804`).

**Consequence**: unless whatever deployment serves triagecounsel.com has
explicitly set `POLICY_ENFORCEMENT_MODE=cutover`, none of the 12-adapter
architecture — not the pre-existing confidentiality/payment_terms/etc.
adapters, not indemnification's own semantic layer, not this session's
new `fact_admission.py` integration across 11 adapters, not the
interaction engine — has ever produced a user-visible decision in
production. This repository has no CI/deployment config in scope for this
session to check the actual deployed environment variable value, so this
map does **not** assume either answer; it states the mechanism and flags
it as the single most consequential unknown for the rest of this mission
(see RESIDUAL_RISK_REGISTER.md).

## NEW FINDING: no `FACT_ADMISSION_MODE` env var exists

Confirmed by repo-wide grep: `FACT_ADMISSION_MODE` does not appear
anywhere in the codebase. Each of the 11 newly-integrated adapters' opt-in
switches (e.g. `LIABILITY_SEMANTIC_DISCOVERY_ENABLED`) are **hardcoded
Python module-level booleans, defaulting `False`**, not environment-
variable-driven — changing one today requires a code edit (or a test's
`monkeypatch`), not a deployment config change. Indemnification's own
pre-existing `HYBRID_DISCOVERY_ENABLED`/`SEMANTIC_PROVIDER` follow the
identical pattern (also hardcoded constants, not env vars). This mission's
Phase 12 explicitly asks for env-var-driven configurability and a
`FACT_ADMISSION_MODE=enforced` cutover switch — this is real, unstarted
work, addressed in Phase 12 of this pass (see ARCHITECTURE.md).

## Re-verified from the prior branch (held up under re-inspection)

- **12/12 production adapters confirmed** via `ls *_policy_engine.py` and
  cross-checked against `playbook_ai_extraction.py`'s own import list:
  liability, indemnification, confidentiality, payment_terms, ip_ownership,
  insurance, data_security, governing_law, termination, warranties, sla,
  assignment. No 13th adapter file exists; no adapter on this list is
  actually dead code (all are imported by `policy_enforcement.py`'s
  `_ENGINE_FUNCS`/`pa.CLAUSE_TYPES`, confirmed by grep).
- **12/12 adapters have `_run_semantic_discovery`**: confirmed by
  `grep -l "_run_semantic_discovery" *_policy_engine.py` returning exactly
  12 files.
- **11/12 use the shared `fact_admission.py` framework** (all except
  indemnification, which has its own separate, pre-existing,
  Step-4B-frozen mechanism — `semantic_discovery_real.py` +
  `SEMANTIC_PROVIDER`): confirmed by `grep -l "SEMANTIC_DISCOVERY_ENABLED"
  *_policy_engine.py` returning exactly 11 files, none of which is
  `indemnification_policy_engine.py`.
- **Every new flag defaults `False`**: spot-checked 3 of 11
  (`liability_policy_engine.py`, `confidentiality_policy_engine.py`,
  `assignment_policy_engine.py`) directly; consistent with the pattern
  documented (and unit-tested — `test_disabled_by_default_is_confirmed_
  absent` exists for all 11) in the prior branch.
- **`document_aggregation.py` wiring**: confirmed intact —
  `main.py:1263` (`_document_state_for_contract`), called from
  `/dashboard` (`main.py:1319`), `/history` (`main.py:1360`), and
  `review_contract` (`main.py:2397`); `templates/review.html:292` renders
  the "Needs Attention" badge condition. This matches the prior session's
  claim exactly — re-verified, not assumed.
- **Interaction engine wiring**: prior session's claim that
  `interaction_engine_core.py` is untouched and "already correct" holds —
  but this pass additionally traced *where* it's called from (see NEW
  FINDING above), which the prior map did not spell out as explicitly:
  it is called ONLY inside the `cutover` branch, never in `legacy`/
  `shadow`. This is consistent with, but sharper than, the prior map's
  characterization.
- **Historical reproducibility** (`models.py`'s
  `policy_revision_metadata_json`, `policy_enforcement.config_hash_for_
  position()`): unchanged since the prior session's verification; not
  re-derived line-by-line again in this pass, spot-checked present at
  `models.py:163` and `policy_enforcement.py` (function still defined).
- **Provider configuration**: confirmed via `grep` that
  `ANTHROPIC_API_KEY` (fact_admission.py, semantic_discovery_real.py) and
  `OPENAI_API_KEY`/`OPENAI_MODEL` (evaluator.py, playbook_ai_extraction.py)
  remain the only credential env vars referenced, read via
  `os.environ.get`/`os.getenv` only — no value was read, printed, or
  logged during this verification pass.

## What Phase 0 changes about the rest of this mission

Because the 12-adapter engine (with or without this session's fact-
admission work) is not confirmed live today, Phase 16 ("controlled
cutover" — setting `POLICY_ENFORCEMENT_MODE=cutover` in production) is not
merely "enable a feature flag on top of already-live infrastructure" — it
is potentially **the actual first activation of the entire modern policy
architecture for real users**, or it is a re-confirmation of an
already-active cutover this session cannot verify either way. Either
reading raises the bar for Phase 15's hard gates rather than lowering it.
Given this session's confirmed inability to run a live-model frozen
corpus or a live triagecounsel.com validation (see FROZEN_CORPUS_MANIFEST.md
and the live-validation section of FINAL_VALIDATION_REPORT.md), this map
recommends against treating Phase 16 as executable in this session — see
RESIDUAL_RISK_REGISTER.md and the final verdict.
