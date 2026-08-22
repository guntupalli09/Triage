# Step 4B — Document-Level Aggregation Specification

## 1. Problem restated (Phase 1 finding)

`Contract.overall_risk` (`main.py:316`, `rule_engine.analyze()`) is computed
BEFORE `apply_policies_for_review` runs (`main.py:1358` vs `:1392`) and is
never recomputed or merged with policy/interaction results afterward. It is
the sole signal used by:

- `main.py:1202-1204` — dashboard "high risk contracts" count.
- `main.py:1231` — `/history` listing `risk` filter.
- `main.py:1590-1592` — UI risk badge.
- `main.py:3608-3610` — dashboard risk-distribution stats.

None of these read `Contract.policy_decisions_json` or
`Contract.interaction_decisions_json`. A contract whose legacy
pattern-match risk is "low" but whose deterministic policy layer (cutover
mode) finds a `PROHIBITED`/`MUST_REDLINE`/`ESCALATE` decision, or whose
Interaction Engine finds an `ESCALATE`/`REQUIRES_REVIEW` interaction, is
today invisible to every one of those four surfaces.

## 2. Mode investigation — what shadow/cutover actually do today

Traced directly in `policy_enforcement.apply_policies_for_review`
(lines 734-792):

- **legacy** and **shadow** both take the SAME branch (line 779): the
  user-visible `policy_decisions` come exclusively from
  `apply_liability_policy` (the single legacy liability-only engine, not
  the 12-adapter layer). `interaction_decisions` is unconditionally `None`
  in both modes — the Interaction Engine V1 is **never invoked at all**,
  not merely hidden, when the deployment is not in cutover.
- **shadow** additionally runs `run_shadow_comparison` (liability-only
  divergence logging to `AuditLog`) — explicitly diagnostic-only, wrapped
  in a bare `except: pass` so it can never affect the user-visible result,
  and never surfaced to any UI. It does not run the 12-adapter layer or
  the interaction engine either.
- **cutover** is the only mode that calls `apply_active_policies` (all 12
  adapters) and `interaction_enforcement.apply_interaction_rules`.
- `DEFAULT_MODE = "shadow"` (`policy_enforcement.py`), confirmed the
  active default absent an explicit `POLICY_ENFORCEMENT_MODE=cutover` env
  var.
- The codebase already contains a deliberate, pre-existing UX safeguard
  for exactly this class of problem: `is_policy_authoritative()` and
  `enforcement_disclosure()` (lines 156-204), built for a documented prior
  finding ("UX walkthrough P0-2") — every policy-facing UI surface is
  required to gate on `is_policy_authoritative()`, never on
  `PolicyPosition.status`, so a Playbook does not visually claim to
  "govern" a review it is not actually deciding. This shows the shadow/
  cutover distinction and its UX risk were already a recognized, actively
  guarded-against concern before Step 4B — but that guard is scoped to
  "does an active Playbook look like it's deciding this review," not to
  "does `overall_risk` correctly reflect deterministic findings that DO
  exist." The two are complementary, not overlapping: this Step 4B
  aggregation work does not need to touch `is_policy_authoritative()` or
  `enforcement_disclosure()`, and must not weaken or bypass them.

**Conclusion**: in the shipped default (shadow), there is categorically
nothing to aggregate from the interaction layer — `interaction_decisions`
is always `None` — and `policy_decisions` is always the single-clause
legacy liability decision, which (per Phase 0/1) already IS folded into
legacy findings the way it always was. **The false-clean gap is real and
material only in cutover mode.** This does not make it low priority: any
deployment that has already turned on cutover (the entire point of Step 4B
existing) is exposed today. But it does mean the aggregation function must
be **mode-aware by construction**, not merely mode-blind logic that
happens to no-op in shadow — a mode-blind implementation that reads
`policy_decisions_json`/`interaction_decisions_json` and finds them empty
in shadow would silently no-op, which is the correct behavior, but only
if it is verified to be correct behavior and not an accident of currently-
empty data. This is tested explicitly below (§5, shadow-mode cases).

No change to `DEFAULT_MODE` is made or recommended here — that remains a
deployment decision, unaffected by this aggregation work.

## 3. Document-level state model

A new, explicit state — **not a replacement for `overall_risk`**, which
stays as the legacy presentation signal it always was, but an additional,
authoritative document-level result computed from all three fact sources.
Explicit states, ordered most-to-least severe (mirrors `review_queue.py`'s
own `TIER_RANK` precedence so the two stay consistent):

| State | Meaning | Trigger |
|---|---|---|
| `HAS_CRITICAL_INTERACTION` | A cross-policy interaction reached `ESCALATE` | any `InteractionDecision.state == "ESCALATE"` |
| `HAS_POLICY_VIOLATION` | A single policy decision reached an actionable violation state | any `PolicyDecision.state in {PROHIBITED, MUST_REDLINE, ESCALATE, NEGOTIATE}` |
| `REQUIRES_REVIEW` | Something material is unresolved, not itself a violation | any `PolicyDecision.state == REQUIRES_REVIEW`, or any `InteractionDecision.state in {REQUIRES_REVIEW, INSUFFICIENT_FACTS}` where the interaction's own ceiling is REQUIRES_REVIEW-or-above, or `InteractionDecision.state == EVALUATION_ERROR` |
| `CONFIGURATION_UNRESOLVED` | Policy enforcement is authoritative (cutover) but no playbook/position could be resolved for this contract (`policy_decisions is None`) | `mode == cutover and policy_decisions is None` |
| `CLEAN` | No policy violation, no critical/unresolved interaction, no configuration gap | none of the above, AND legacy `overall_risk` itself is not `"high"` |
| `CLEAN_LEGACY_ATTENTION` | Every deterministic signal available is clean, but the legacy pattern-match risk is `"high"` | none of the above, but `overall_risk == "high"` |

Precedence is evaluated top-to-bottom (first match wins) — this is a
DETERMINISTIC ceiling composition, structurally identical in spirit to
`interaction_engine_core.evaluate()`'s own ceiling enforcement: the
document-level state is never MORE certain/clean than the least-certain
material input feeding it (the FALSE-CLEAN INVARIANT from the task spec).
`CLEAN_LEGACY_ATTENTION` is kept distinct from `CLEAN` rather than folded
into it, because legacy `overall_risk == "high"` is itself a signal a user
has always seen — this aggregation must not make a document look SAFER
than it already appeared under the pre-Step-4B system, only ever equal or
more cautious.

In **shadow/legacy** mode, `policy_decisions` reflects only the single
legacy liability decision (never `None` when a playbook exists) and
`interaction_decisions` is always `None` — so only `HAS_POLICY_VIOLATION`
(liability-only) and `CLEAN`/`CLEAN_LEGACY_ATTENTION` are reachable;
`HAS_CRITICAL_INTERACTION`, the interaction-derived `REQUIRES_REVIEW`
paths, and `CONFIGURATION_UNRESOLVED` are structurally unreachable, by the
mode-behavior traced in §2 — not defended against for that reason, but a
provable consequence of it, verified in the benchmark below.

## 4. Non-goals for this bounded increment

- **Not changing `Contract.overall_risk`'s own computation** — it remains
  `rule_engine.analyze()`'s legacy output, unchanged, for full backward
  compatibility (existing filters/badges/PDF exports that read it keep
  working exactly as before).
- **Not adding a new persisted DB column or migration in this increment.**
  The aggregation function below is a pure function over already-persisted
  JSON fields (`policy_decisions_json`, `interaction_decisions_json`,
  `overall_risk`), computable on read without a schema change. Wiring it
  into the dashboard/listing/API surfaces (so `Contract.overall_risk == "high"`
  DB filters stop being the only gate) is the next actionable step and is
  explicitly NOT done in this increment — see the checkpoint note at the
  end of this session's report. Building the pure function and proving it
  correct against a real benchmark first, before touching any live
  dashboard filter, is the deliberately bounded scope here.
- **Not changing `POLICY_ENFORCEMENT_MODE`'s default.**
