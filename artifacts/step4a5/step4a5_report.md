# Step 4A.5 — False-Escalation Reduction & Safety Hardening

**Status: INTERIM REPORT — safety-critical priorities (1–2) complete and verified; priorities 3–5 partially complete.** This document reports only what was actually implemented and measured. Per the task's explicit instruction, no claim of full completion (dedicated benchmarks K/L, fresh 60-case adversarial battery, full manual 172-case reclassification, complete FE root-cause inventory) is made where the work was not done — those items are listed under "Not completed" with an honest reason, not silently omitted.

## A. Baseline reproduction (confirmed, unchanged from prior session state)

- Step 4A.4 corpus (172 cases): reproduced exactly — CA=81, CR=26, FE=39, WC=12 (+2 separately-documented GTD), SM=12 (1 SM-CRITICAL), S4=0.
- Step 4A.2 corpus (108 semantic cases): reproduced exactly — CA=57, CR=29, FE=22, WC=0, SM=0.
- Production file hashes recorded before any change (`scratchpad/step4a5_pre_hashes.txt`).
- Frozen corpus files verified byte-identical to the frozen Step 4A.4 commit (`fd3ebc0`) via `git diff fd3ebc0 -- benchmarks/step4a2_heldout_corpus.py benchmarks/step4a2_formatting_mutations.py benchmarks/step4a4_corpus.py benchmarks/step4a4_formatting_mutations.py` → zero lines of diff, both before and after this session's implementation work.

## B/C. Root-cause work performed (Priorities 1–2 only — see "Not completed" for 3–5)

### Priority 1 — SM-CRITICAL (set-off/deduction concept)

`A4-K-07` returned `NOT_APPLICABLE` on a genuine mutual-debt-netting clause phrased without the literal words "set-off"/"offset" ("withhold ... an amount equal to any sums ... owes"), silently clearing a `prohibit_set_off` policy violation from review.

**Fix**: a new general concept detector in `payment_terms_policy_engine.py` — `_find_mutual_debt_netting_span` / `_has_mutual_debt_netting` — recognizes the underlying legal concept (one party deducting/netting/reducing/retaining/crediting/recouping an amount using amounts the OTHER party independently owes it), scoped by a local-window mutual-negation check (`_MUTUAL_DEBT_NEGATION_RE`) rather than literal-phrase matching. Also fixed a related regex gap: `_SETOFF_PERMIT_RE`/`_SETOFF_PROHIBIT_RE` previously mishandled `"shall not have any right of set-off"` (enumerated-list, non-adjacent negation), which had begun to slip through while extending permit-side matching to `"right of"`.

**Benchmark built BEFORE implementation and locked** (`benchmarks/setoff_concept_benchmark.py`, checksum `c4272d4c...b08b`, 72 cases: 42 positive across many domains, 30 negative controls — tax withholding ×2, service credits, refunds, billing corrections, rebates, promotional credits, tax deductions, disputed-amount withholding, damages, accounting net presentation, insurance deductibles, credit notes, marketing allowances, and more):

| Metric | PRE | POST |
|---|---|---|
| Recall | 7.1% (3/42) | 92.9% (39/42) |
| Precision | 100% | 100% |
| False-positive rate | 0% | 0% |

3 residual recall misses (SO-17, SO-28, SO-33 — gerund/"retain"/explicit-net-balance framings) are documented, not silently dropped.

### Priority 2 — WC hardening (all 12 known WC eliminated)

Root-caused into 5 shared general mechanisms rather than 12 case-specific patches:

| Root cause | Mechanism | Cases fixed | Files |
|---|---|---|---|
| Multi-word role-name truncation | Single-token role regex (`[A-Z][A-Za-z]{2,25}`) truncated names like "Charter Operator" → replaced with `_MULTIWORD_ROLE_NAME_FRAGMENT` (1–3 capitalized words) + `trim_role_name()` stopword trimming (needed once ALL-CAPS formatting mutations over-captured trailing connector words) | A4-J-02, A4-J-12, A4-J-15, A4-COMP-06, contributes to A4-A-03/A4-A-07/A4-A-09/A4-A-11 | `policy_engine_core.py`, `indemnification_policy_engine.py` |
| Role-definition body missing later-sentence evidence | Cross-sentence extension: when the found definition body carries no directional evidence, extend to the next sentence re-mentioning the role's own name | A4-A-03, A4-A-05 | `policy_engine_core.py` |
| One side known / other unmapped-but-clean | Elimination-by-other-side logic in `_resolve_obligations_for_side`: if one role's side is confidently resolved and the OTHER role has no conflicting definition, its identity follows by elimination in a strictly two-party obligation | A4-A-07, A4-A-09, A4-A-11 | `indemnification_policy_engine.py` |
| Reciprocal-but-NAMED obligation pairs | Two directional obligations naming the same pair in opposite directions with matching monetary/scope/defense terms are policy-outcome-invariant to which is "us" (mirrors existing "each party" handling); required an ordered-tuple (not frozenset) dedup fix so both directions survive extraction | A4-E-06, A4-E-11, A4-E-13, A4-E-15, A4-J-10 | `indemnification_policy_engine.py` |
| Multi-definition / self-referential role identity | `resolve_role_side` now (a) finds ALL definitional anchors for a role (not just the first) and flags disagreement between differently-scoped definitions, (b) recognizes a "the party other than X" self-referential construction as inherently unresolvable, (c) fixed a `\bsell\b` word-boundary gap that missed "resells" | A4-G-01, A4-G-03, A4-G-07 | `policy_engine_core.py` |
| Liability basis/structure ambiguity | New general detectors: `_BASIS_VALUE_AMBIGUITY_RE` (multiplier's own basis value stated as "may refer to X or, if greater, Y"), `_SELF_FLAGGED_AMBIGUITY_RE` (document explicitly says "unclear whether...") | A4-H-06, A4-H-08 | `liability_policy_engine.py` |
| Differentiated procedural terms under a reciprocal opener | New general detector (`_find_procedural_differentiation_roles`): survival period, notice precondition, defense-control grant, or temporal carve-out attached separately to two distinct named parties (not the reciprocal "each party" placeholders) — generalizes beyond the existing monetary/trigger/scope comparison; survival-period matches only count when the two extracted period VALUES actually differ (avoiding a new FE source from purely stylistic per-party restatement of an identical term) | A4-J-05, A4-J-06, A4-J-11, A4-J-14 | `indemnification_policy_engine.py` |
| Protection-side cross-reference monetary blind spot | The existing "cross-reference monetary → unresolved" check only guarded the exposure side; a symmetric protection-side check was added, and `_classify_monetary` now preserves cross-reference information instead of collapsing a disqualified-as-belonging-to-another-clause figure to `not_stated` | A4-COMP-02 (discovered as a NEW WC introduced transiently by the elimination-by-other-side fix above — investigated and fixed within the same implementation loop, not shipped) | `indemnification_policy_engine.py` |

Each fix's invariant and negative-control reasoning is documented inline in the source as a comment at its definition site.

## D. Verification performed after every change

- Full adapter test suites (`tests/test_indemnification_policy_engine.py`, `tests/test_liability_policy_engine.py`, `tests/test_payment_terms_policy_engine.py`, `tests/test_payment_terms_benchmark_gate.py`): 112 passed, 0 failed, throughout.
- `benchmarks/run_liability_benchmark.py`, `run_indemnification_benchmark.py`, `run_indemnification_asymmetry_benchmark.py` (19/19, 0 false-safe), `run_payment_terms_benchmark.py` (0 false-safe, 0 false-escalation, 100% determinism): same pre-existing documented failures before and after (`xref-03`, `xref-04`, `cap-excluded-01`, `super-cap-01/02` on indemnification; `unheaded-08`, `partial-01`, `amendment-02` on liability) — confirmed via `git stash` diff that these are unchanged baseline gaps, not new regressions. One pre-existing failure (`xref-04`) transiently disappeared then reappeared during the session; confirmed via direct regex testing that it is unaffected by the final code state and matches the original baseline exactly.
- `benchmarks/run_setoff_concept_benchmark.py`: see table above.

## E. SM-CRITICAL PRE → POST

- PRE: `A4-K-07` → state `NOT_APPLICABLE`, `facts.setoff_permitted=None` — a genuine `prohibit_set_off` violation silently cleared from review.
- POST: state `MUST_REDLINE` (or equivalent violation-detected state) — the mutual-debt-netting concept is now recognized and the prohibition check engages.
- SM-CRITICAL count: 1 → **0**.

## F. WC elimination table

| Adapter | PRE (known WC) | POST (known WC) |
|---|---|---|
| Liability | 6 (incl. A4-G-01, A4-G-03, A4-H-06, A4-H-08 + 2 more) | **0** |
| Indemnification | 6 (incl. A4-G-07, A4-J-05/06/10/11/14, A4-COMP-06, A4-E-family) | **0** |
| **Total known WC** | **12** | **0** |

Remaining `WC_CANDIDATE` bucket count is 2 (`A4-H-04`, `A4-H-05`) — both are the pre-existing GTD (Ground Truth Defect) cases already independently documented and reclassified in the original Step 4A.4 report (label judged too aggressive on reflection against defensible output), not new or unresolved WC. No new WC was introduced by any fix in this pass (one transient regression, A4-COMP-02, was caught and fixed within the same implementation loop per the mandatory "check for new WC before continuing" step).

## G. Silent-miss status

SM count: 12 → 11 (the SM-CRITICAL case is fixed; see E). The remaining 11 are **all Recognition misses** (Family K): the clause-anchor regex never fires at all on a non-canonical predicate phrasing (e.g., "undertakes to make...whole for" instead of "indemnify, defend, and hold harmless"; "disbursed by" instead of "paid by"/"due within"; "any recovery against...is limited to a sum not to exceed" instead of "liability shall not exceed"; a purely tabular field:value presentation with no prose sentence at all). None involve a policy violation being silently cleared (none are SM-CRITICAL) — the system correctly returns `NOT_APPLICABLE` rather than a false ACCEPT, but per the task's "never silently disappear" principle this is still a defect: a real, supported clause is not surfaced to REQUIRES_REVIEW either. **These 11 were not fixed in this pass** — see "Not completed."

## H. False escalation

| Adapter | PRE FE | POST FE |
|---|---|---|
| Liability | ~22 | 18 |
| Indemnification | ~18 | 8 |
| Payment Terms | ~5 (est.) | 5 |
| **Total** | **39** | **31** |

FE reduction here is a side effect of the WC-hardening fixes (several of the same mechanisms — multi-word role names, definition-body extension, elimination-by-other-side, reciprocal-pair invariance — simultaneously converted FE cases to CA, since the same broken role/definition resolution was driving both). No FE was reduced by removing an escalation gate; every fix added positive evidence (a correctly-bounded role name, a found cross-sentence definition, a confirmed elimination-by-other-side identity, a confirmed matching reciprocal pair) that justified resolving automatically. **A dedicated, purpose-built FE-reduction pass targeting Families 1–3 as originally specified (multi-word role BOUNDARY benchmark, bystander-entity discrimination, direction-invariance benchmark) was not separately executed — the FE reduction above is an emergent consequence of the WC fixes, not a targeted Priority-4 pass.** See "Not completed."

## I. Step 4A.4 PRE → POST metric table

| Metric | PRE | POST |
|---|---|---|
| CA | 81 | **90** |
| CR | 26 | 38 |
| FE | 39 | **31** |
| WC (known) | 12 | **0** |
| SM | 12 | 11 |
| SM-CRITICAL | 1 | **0** |
| S4 | 0 | 0 |
| Automation Recall (overall) | 61.4% | **68.2%** |
| FE-among-AUTOMATABLE | 29.5% | **23.5%** |

All four selectivity gates required for a full PASS are met: CA POST(90) > 81 ✓; Automation Recall POST(68.2%) > 61.4% ✓; FE POST(31) < 39 ✓; FE-among-AUTOMATABLE POST(23.5%) < 29.5% ✓. Safety gates S4=0 ✓, SM-CRITICAL=0 ✓, known WC 12→0 ✓ are all met. **The known-SM 12→0 gate is not met (12→11)** — this is the one hard gate left open.

## J. Per-adapter selectivity (POST)

| Adapter | AUTOMATABLE | CA | CR | FE | WC | SM | Automation Recall | FE-among-AUTOMATABLE |
|---|---|---|---|---|---|---|---|---|
| Liability | 57 | 35 | 12 | 18 | 0 | 4 | 61.4% | 31.6% |
| **Indemnification** | 35 | 23 | 16 | 8 | 0 | 4 | **65.7%** (was 37.1%) | **22.9%** (was 51.4%) |
| Payment Terms | 40 | 32 | 10 | 5 | 0 | 3 | 80.0% | 12.5% |

Indemnification — flagged as "particularly weak" in Step 4A.4 (Automation Recall 37.1%) — improved to 65.7%, the largest gain of any adapter, directly from the role-resolution and reciprocal-pair fixes (Priority 2's largest cluster was indemnification-specific).

## K. Dedicated mechanism benchmarks

| Benchmark | Required min | Built? | Result |
|---|---|---|---|
| Set-off/mutual-debt-netting concept | ≥40 pos / ≥30 neg | **Yes** (42/30) | Recall 92.9%, Precision 100%, FP 0% |
| Multi-word role boundaries | ≥30 pos / ≥20 neg | **No** — verified only via existing adapter tests/benchmarks and direct case testing, not a dedicated locked benchmark | Not measured as a standalone metric |
| Bystander entity discrimination | ≥25 neg / ≥20 pos | **No** | Not attempted this pass |
| Direction invariance | ≥40 cases | **No** — mechanism implemented and verified against the specific frozen cases it fixes plus the existing asymmetry benchmark (19/19, 0 false-safe), but no dedicated locked benchmark built | Not measured as a standalone metric |
| Existing controls (role-safety, Payment recognition, Liability ownership, Indemnification asymmetry, liability-concept) | — | Re-run, unweakened | All pass at pre-existing rates; asymmetry benchmark 19/19 (100%), 0 false-safe |

## L. Step 4A.2 historical control

- Manual/verified reproduction of the exact PRE state (CA57/CR29/FE22/WC0/SM0) was done at session start.
- A full POST manual reclassification matching that same methodology **was not repeated** this pass (time constraint). The available automated evidence: (a) zero new failures in `pytest`/benchmark suites that exercise this corpus's underlying mechanisms; (b) the heuristic `classify_step4a2_heldout.py` script (which itself needs manual verification per its own docstring) shows its WC-candidate count improving from 8→7 with no new case IDs appearing, only `INDEM-I2-02` dropping out — consistent with improvement, not regression, but **not a substitute for the required manual re-verification**.

## M. Existing policy benchmarks

Liability-125, Indemnification-100 (actual corpus sizes differ slightly from those names; see benchmark files), Payment-84 all re-run: false-safe = 0, false-escalation = 0 (payment), determinism = 100% throughout. No unexplained regression in any.

## N/O. Fresh adversarial battery / regression suite

**Not completed this pass.** The fresh ≥60-case adversarial battery (15 safety / 15 silent-miss / 15 false-escalation / 15 mixed, with mandatory anti-false-safe attacks against every newly-introduced FE-reduction mechanism) was not built. The full `pytest` regression suite was run only for the directly-relevant adapter test files (112 passed, 0 failed); the broader suite's pre-existing 43 collection errors (environment/dependency issues unrelated to this work, matching the Step 4A.4 baseline exactly) were not re-verified line-by-line against the full 1157/10/43 baseline in this pass.

## P. Remaining limitations

**Safe limitations (correctly routed to review, not silently missed):**
- All 12 original WC cases now correctly escalate rather than silently resolving.
- The 2 GTD cases (A4-H-04, A4-H-05) remain WC-shaped in the raw classifier output but are independently documented as mislabeled ground truth, not system defects.

**Selectivity limitations (unnecessarily reviewed):**
- 31 remaining FE cases, concentrated per Section H; no dedicated root-cause pass beyond the WC-driven fixes was performed this session.
- The single-role-only branch of the new procedural-differentiation detector (`_find_procedural_differentiation_roles`) escalates conservatively whenever it finds exactly one named-party procedural grant/exclusion with no matching counterpart in its local window — this could produce avoidable review in documents where the counterpart is genuinely mirrored using phrasing this detector doesn't recognize.

**Potential residual safety surfaces (not adequately tested):**
- 11 remaining SM (recognition misses) mean specific non-canonical drafting patterns are invisible to the system entirely (return NOT_APPLICABLE) rather than escalating — while none currently observed clear an actual violation, this class of gap is exactly where a future SM-CRITICAL could hide, and was not exhaustively probed for that risk.
- No dedicated bystander-entity-discrimination or direction-invariance benchmark was built, so FE Families 2 and 3 as originally scoped remain unverified against their own adversarial negative controls.
- The fresh 60-case adversarial battery, including the mandatory anti-false-safe attacks against this session's own new mechanisms (procedural-differentiation detector, multi-definition conflict detector, elimination-by-other-side logic), was not built — these mechanisms have only been verified against the frozen corpora's specific cases, not against adversarially-constructed attacks designed to slip past them.

## Not completed (honest accounting)

- Priority 3 (remaining-SM classification into Recognition/Extraction/Ownership/Policy-routing/Scope/Other and fixing or escalating each): classification done (all 11 are Recognition misses), fixes not attempted.
- Priority 4 (systematic FE root-causing beyond the WC-driven byproduct; FE Families 1–3 dedicated benchmarks and targeted fixes): not done as a separate, purpose-built pass.
- Priority 5 (Automation Recall/usefulness push beyond the WC-driven gains): not separately pursued.
- Fresh 60-case adversarial battery with anti-false-safe attacks: not built.
- Full manual reclassification of all 172 Step 4A.4 cases against actual extracted facts (not just the auto-classifier heuristic): not done — the auto-classifier's CA/CR/FE bucketing (unambiguous by construction against the locked label) is trusted for the headline metrics in Section I/J, and every WC/SM case was individually inspected (Sections F/G), but a full independent audit of all 90 CA_CANDIDATE and 38 CR was not performed.
- Full regression-suite comparison against the exact 1157/10/43 baseline: not re-verified line-by-line.

## Verdict

**MORE HARDENING REQUIRED** — not because of any newly-discovered safety defect (S4=0, SM-CRITICAL=0, and all 12 known WC are eliminated and verified with zero regressions across every adapter test and benchmark), but because:
1. The hard "known SM 12→0" gate is not met (12→11) — 11 recognition-vocabulary misses remain, and per the task's explicit criteria a remaining SM (even non-critical) blocks a clean PASS.
2. Priorities 3–5 as specified (SM fixes, dedicated FE-family benchmarks and targeted fixes, the fresh adversarial battery, full manual reclassification) were not completed in this pass.

This is **not** a "FAIL — REDESIGN REQUIRED" outcome: no FE-reduction attempt reintroduced an unsafe automatic decision, every fix in this pass was justified by newly-identified positive evidence (never by relaxing an escalation gate), and every measured selectivity gate improved materially without any safety regression. The honest state is that safety-critical work (Priorities 1–2) is complete and verified, while breadth-of-coverage work (Priorities 3–5, adversarial hardening, full corpus audit) remains open.

## Step 4A.6 recommendation

**NO** — do not yet freeze this state for a third independent held-out validation. Recommend completing, in order: (a) the 11 remaining SM (Recognition-miss vocabulary gaps — likely tractable with the same anchor-regex-generalization approach already used successfully for role/definition recognition), (b) the fresh 60-case adversarial battery with mandatory anti-false-safe attacks against this session's own new mechanisms (these mechanisms are exactly the kind of newly-loosened logic Step 4A.6 would need independent evidence about), and (c) the full manual 172-case reclassification audit, before subjecting the result to frozen validation. Step 4B remains **not started**, as instructed.
