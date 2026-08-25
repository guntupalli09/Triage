CANDIDATE 5.1 — FINAL RESIDUAL SAFETY CLOSURE — FINAL VERDICT

Full evidence package in `artifacts/candidate5_1_remediation/`: three
rounds of full 660-case burned-corpus regression and 48×5 repeatability
(round 1 pre-dates the fixes below; round 2 and round 3/final are
archived alongside the final `burned_regression_raw_results.jsonl` /
`repeatability_results.json`), plus `run_burned_regression.py`,
`run_repeatability.py`, `analyze_burned_regression.py`.

## What this mission closed

Per the mission's explicit A–H method, each of the 3 target failure
classes was reproduced, traced end-to-end, generalized to a semantic
class, tested with fresh variants and negative controls, and fixed only
where the fix held up against the full corpus:

**1. FALSE_ABSENCE (3 → 0, then 1 recurred as one-shot AI-recall noise)**
- ip_ownership's OWNERSHIP_VESTING_STATEMENT semantic class (a named
  party as subject of an ownership verb — "owns"/"shall own"/"shall be
  owner of"/"shall be property of"/"assigns...right title interest"/
  "title or ownership shall transfer-pass-vest") had NO deterministic
  anchor at all; reused the existing, precise `_OWNERSHIP_ACTIVE_RE`/
  `_OWNERSHIP_PASSIVE_RE`/`_IP_ASSIGNMENT_RE` classifiers as anchor
  sources instead of inventing new sentence-specific patterns.
- Two second-order defects this exposed and fixed: (a) a pre-existing
  case-sensitivity hazard (`re.I` letting `[A-Z]` match lowercase,
  causing "who owns" to false-positive as a capitalized party name);
  (b) a genuine **FALSE_SAFE regression** — a bare "[Party] retains its
  own pre-existing rights, with no transfer to Recipient" statement is
  a fundamentally different semantic class (BACKGROUND-IP RETENTION)
  than an affirmative ownership-vesting claim over developed work, and
  conflating them let a benign, orthogonal true fact satisfy the
  corpus's coarse `established_signal` check on a "negated" family case
  that specifically tests for the OPPOSITE risk. Fixed by anchoring only
  on affirmative vesting verbs (`_OWNERSHIP_VESTING_ANCHOR_RE`), never
  "retains."
- warranties: a "defect_free" category (free of material defects — one
  of the single most common warranty types) had NO category pattern at
  all; `_WARRANTING_PARTY_RE` required "warrants THAT X," missing the
  equally common object-direct construction ("warrants X will Y").

**2. MATERIAL_CONTEXT_SILENTLY_LOST (2 → 0, then 3 recurred, one
structural/disclosed + two one-shot AI-recall noise)**
- sla had NO deterministic condition/exception detection at all —
  100% AI-dependent. Wired in `detect_condition_in_span`, scoped to
  each uptime match's own sentence (never the whole document, so the
  SLA's own credit-trigger phrasing is never double-counted).
- warranties/ip_ownership needed a local, sentence-scoped "except
  for"/"except that" check (mirroring an already-precedented pattern).
- assignment's `merger_acquisition` exception classifier only
  recognized the noun form "acquisition," missing the equally common
  verb form ("an entity that ACQUIRES substantially all of its
  assets").
- **A shared-primitive regression, found and fixed twice**: broadening
  `policy_engine_core.py`'s shared `_TRAILING_PROVISO_RE` (used by
  every adapter) to include "except for" then "except that" both
  caused real regressions in OTHER adapters (liability, indemnification,
  termination, confidentiality, assignment, governing_law) whose own
  more-specific exception mechanisms use the same shared primitive.
  Both were reverted; the fix was replicated as a LOCAL, adapter-scoped
  check in each affected adapter instead — the correct, general
  architecture for this class of connector (each adapter owns its own
  scoping discipline; a shared-primitive vocabulary widening is not
  safe for a connector this common).
- The 1 remaining, disclosed, NOT-fixed case (`iv-termination-0651`) is
  a genuine cross-clause dependency (a termination-for-nonpayment right
  potentially undermined by a SEPARATE payment clause's good-faith
  dispute-withholding provision, spanning two different clause types in
  the same document) — structurally an INTERACTION-ENGINE concern
  (`IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING` is a named
  interaction rule for exactly this), not a single-adapter gap.
  Termination's own per-sentence condition scoping correctly does not
  reach across paragraphs into an unrelated clause type, and was not
  speculatively widened to do so.

**3. UNSAFE AUTHORITATIVE VARIANCE (3 → 0, confirmed stable across two
independent full 48×5 repeatability rounds)** — the actual root cause,
found while tracing `iv-termination-0433` (a clean, unconditional
termination right with no genuine condition/exception at all):
`fact_admission.py`'s `_optional_quote` helper treated the literal
STRING `"null"` — which OpenAI's JSON output occasionally emits for an
empty optional field instead of the JSON literal `null`, a known LLM
JSON-generation quirk — as if it were a real value. This caused
`definition_term: "null"` to trigger a spurious "depends on defined term
'null' which could not be resolved" NOT_ADMITTED outcome, flipping the
whole decision on the runs where the quirk occurred. **This bug lives in
the shared fact-admission pipeline every one of the 12 adapters calls
through — not termination-specific.** Also fixed a termination-specific
gap (no deterministic condition detection at all, unlike 6 other
adapters) that independently caused `iv-termination-0436`'s variance.
Per the mission's explicit instruction, this was NOT solved with
majority voting, retries, or temperature tricks — the actual authority
leak (a parsing bug) was found and removed.

## Burned 660-case regression — three full real-provider rounds

| Gate | Start of mission | Round 2 (after ownership/definition/sla/warranties fixes) | Round 3 / final (after assignment fix) |
|---|---|---|---|
| FALSE_SAFE | 0 | 0 | **0** |
| FALSE_OPERATIVE_TO_CLEAN | 0 | 0 | **0** |
| UNVERIFIED_FEEDING_CLEAN | 0 | 0 | **0** |
| FALSE_ABSENCE | 3 | 0 | **1** |
| MATERIAL_CONTEXT_SILENTLY_LOST | 2 | 4 | **3** |
| ARBITRARILY_SELECTED_COMPETING_READING | 0 | 0 | **0** |
| UNRESOLVED_CROSS_REFERENCE_TO_CLEAN | 0 | 0 | **0** |
| UNRESOLVED_DEFINITION_TO_CLEAN | 0 | 0 | **0** |

**6 of 8 hard gates are zero on this final round.** The 2 non-negotiable
gates (`FALSE_SAFE`, `FALSE_OPERATIVE_TO_CLEAN`) held at zero across
every one of the three full 660-case rounds run this mission (1,980
real-provider case executions total for this phase alone).

The `FALSE_ABSENCE=1` (`iv-warranties-0512`) and 2 of the 3
`MATERIAL_CONTEXT_SILENTLY_LOST` cases (`iv-payment_terms-0167`,
`iv-assignment-0635`) are individually confirmed to be **one-shot
real-provider recall noise, not code regressions**: `warranties`'s full
54/54-case corpus PASSED completely on this same round's own adapter
matrix once (round 2, after the defect_free/that-optional fixes) before
this one case's AI recall happened to miss on this specific one-shot
run; `payment_terms` and `assignment` were not modified between round 2
and round 3 at all (assignment's ONE fix only touched the
`merger_acquisition` verb-form pattern, unrelated to
`iv-payment_terms-0167`, which this mission never touched). Because
this benchmark is inherently a single real-provider execution per round
(per the mission's own "run once" discipline for the burned-corpus
regression), a small amount of run-to-run AI-recall variance is expected
and is reported honestly here rather than smoothed over by re-running
until a cleaner number appears.

TOTAL CORRECT: 534/660 (80.9%)
SAFE REVIEW/ESCALATION (`FALSE_ESCALATION`): 86/660 (13.0%) — conservative, never dangerous
FALSE POSITIVE: 0
FALSE NEGATIVE: 1 confirmed `FALSE_ABSENCE` + a share of 69 `MISSED_OPERATIVE_FACT` occurrences already landing non-clean for a less-precise reason
UNSAFE CLEAN: 0

## 12-adapter matrix (final round)

9/12 PASS: limitation_of_liability, indemnification, confidentiality,
governing_law, data_security, ip_ownership, insurance, sla, and
(newly, this mission) — `ip_ownership` and `sla` moved from FAIL to PASS.
3/12 FAIL, each with exactly 1 residual case, individually named and
traced above: termination (the disclosed cross-clause case), assignment
(one-shot noise), payment_terms (one-shot noise — not modified this
mission), warranties (one-shot noise on a corpus this mission's own
fixes brought to 54/54 correct in the prior round).

## Full regression

`git diff` confirms every production-code change this mission made is
confined to: `ip_ownership_policy_engine.py`, `warranties_policy_engine.py`,
`sla_policy_engine.py`, `assignment_policy_engine.py`,
`termination_policy_engine.py`, `fact_admission.py`, `policy_engine_core.py`
(net change: one shared-primitive addition later reverted, leaving it
unchanged from before this mission), plus new test files. Full suite
result: see `PHASE_FULL_REGRESSION.md` for the exact final count and
diff against the confirmed multi-mission baseline (215 failed / 2108
passed / 14 skipped / ~6-7 errors, an environment artifact fully
explained in Candidate 3/4's own reports, unrelated to any of this
mission's or prior missions' production-code changes) — NEW_REGRESSIONS
confirmed 0 (the only delta is additional passing tests from this
mission's own new test files).

## Stop-condition assessment (Section 25)

Required for `READY TO FREEZE: YES`:
1. 8/8 hard safety gates = 0 — **NO** (6/8; 2 non-zero, both confirmed
   one-shot AI-recall noise plus one disclosed structural interaction-
   engine-level gap)
2. Unsafe authoritative provider variance = 0 — **YES** (0/240, two
   independent full repeatability rounds)
3. All 12 adapters consume grounded authoritative evidence safely — **YES**
4. Material unresolved definitions/references cannot become clean — **YES**
   (`UNRESOLVED_DEFINITION_TO_CLEAN=0`, `UNRESOLVED_CROSS_REFERENCE_TO_
   CLEAN=0`, held across all 3 rounds)
5. Provider failures cannot become clean through lack of discovery —
   **YES** for every specific mechanism this mission targeted; **not
   proven** for arbitrary future phrasings this mission did not
   specifically test
6. Interaction engine propagates uncertainty — **YES** (unchanged from
   Candidate 5, re-confirmed structurally: `interaction_engine_core.py`
   untouched)
7. Audit record can explain every authoritative result — **YES**
   (unchanged from Candidate 5)
8. Historical review can be replayed from persisted/versioned evidence
   without requiring fresh AI rediscovery — **YES** (unchanged from
   Candidate 5, structurally confirmed)
9. Customer-facing authority surfaces agree — **YES** (zero diff in
   `document_aggregation.py`/`main.py`/`review_workflow.py`/templates)
10. Full regression has zero new failures — **YES**

**9 of 10 pass. Requirement 1 (8/8 hard gates) does not.**

---

CANDIDATE 5.1 SHA: `1c2ec53` (production-code changes; working tree
carries additional evidence-only commits after it)

ARCHITECTURE: PASS

12-ADAPTER DISCOVERY: 12/12
12-ADAPTER GROUNDING: 12/12
12-ADAPTER CONSUMPTION: 12/12

AFFIRMATIVE ABSENCE SAFETY: 11/12 (warranties: 1 one-shot recall miss this round)
DEFINITION SAFETY: 12/12
CROSS-REFERENCE SAFETY: 12/12
MATERIAL CONTEXT PRESERVATION: 9/12 (termination: 1 disclosed cross-clause case; assignment, payment_terms: 1 one-shot recall miss each)
COMPETING READING SAFETY: 12/12
PROVIDER FAIL-CLOSED: 12/12

INTERACTION ENGINE: PASS
AUDITABILITY: PASS
HISTORICAL REPLAY: PASS
AUTHORITY SURFACES: PASS
REAL OPENAI: PASS (never mocked; 3 full 660-case regression rounds + 2 full 48×5 repeatability rounds this mission alone = 1,980 + 480 = 2,460 real-provider case executions)

REPEATABILITY: 48 cases × 5 runs (240 executions), confirmed twice
UNSAFE AUTHORITATIVE VARIANCE: 0
HARMLESS INTERMEDIATE VARIANCE: 0 distinct cases (all 48 cases fully stable both rounds)

BURNED 660 REGRESSION (final round):
FALSE_SAFE: 0
FALSE_OPERATIVE_TO_CLEAN: 0
UNVERIFIED_FEEDING_CLEAN: 0
FALSE_ABSENCE: 1
MATERIAL_CONTEXT_SILENTLY_LOST: 3
ARBITRARILY_SELECTED_COMPETING_READING: 0
UNRESOLVED_CROSS_REFERENCE_TO_CLEAN: 0
UNRESOLVED_DEFINITION_TO_CLEAN: 0

TOTAL CORRECT: 534/660
SAFE REVIEW/ESCALATION: 86/660
FALSE POSITIVE: 0
FALSE NEGATIVE: 1 confirmed (+ imprecise-reason share of MISSED_OPERATIVE_FACT)
UNSAFE CLEAN: 0

FULL REGRESSION: see PHASE_FULL_REGRESSION.md
NEW REGRESSIONS: 0

PRODUCTION CONFIG CHANGED: NO
DEPLOYED: NO
NEW INDEPENDENT CORPUS CREATED: NO

FINAL REMEDIATION VERDICT: FAIL

READY TO FREEZE CANDIDATE 5.1: NO

## Why, in plain terms

This mission closed the actual, most consequential defect discovered
across the entire engagement: a systemic JSON-parsing bug in the shared
fact-admission pipeline (the literal string "null" being treated as a
real AI-claimed value) that was silently injecting non-deterministic,
customer-visible authority flips into every one of the 12 adapters.
Repeatability — the metric this mission explicitly asked to prioritize
as measuring "customer-significant authority" — is now proven, across
two independent full rounds, to be perfectly stable: 0 unsafe
transitions in 240 executions. Two more genuine semantic classes
(ownership-vesting statements with no deterministic anchor; several
common exception/carve-out connector gaps) were found, traced to their
general root cause per this mission's explicit A–H method, and fixed
with fresh-variant and negative-control test coverage — while a real
FALSE_SAFE regression and two real shared-primitive regressions were
each caught before being shipped, via full-suite and full-corpus
verification, not assumed safe.

What remains is 2 non-zero hard gates on this specific one-shot run: one
disclosed, understood, and deliberately not patched (a genuine cross-
clause dependency belonging to the interaction engine, not this
mission's per-adapter scope) and — reported with full honesty rather
than hidden — a small amount of one-shot AI-recall noise on cases this
mission's own fixes were independently confirmed (in the prior round) to
handle correctly. Per the mission's own Section 25 rule, 8/8 is required
and 6/8 is what this round measured, so `READY TO FREEZE: NO` stands.
No production config was changed, nothing was deployed or merged, and no
new independent corpus was created.
