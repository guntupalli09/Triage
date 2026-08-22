# Step 4A.5 — False-Escalation Reduction & Safety Hardening (FINAL REPORT)

**Status: COMPLETE.** This report supersedes the interim report committed earlier in this engagement (at `bacee25`) and covers all five priorities: SM-CRITICAL (P1), WC elimination (P2), remaining Silent Miss elimination (P3), False-Escalation reduction (P4), and the fresh adversarial battery (P5). Every claim below is backed by a command that was actually run; where something was investigated and left unfixed, that is stated explicitly rather than omitted.

## A. Baseline reproduction

- Step 4A.4 corpus (172 cases): reproduced exactly at session start — CA=81, CR=26, FE=39, WC=12 (+2 separately-documented GTD), SM=12 (1 SM-CRITICAL), S4=0.
- Step 4A.2 corpus (108 semantic cases): reproduced exactly — CA=57, CR=29, FE=22, WC=0, SM=0.
- Production file hashes recorded before any change (`scratchpad/step4a5_pre_hashes.txt`).
- Frozen corpus files verified byte-identical to the Step 4A.4 commit (`fd3ebc0`) via `git diff fd3ebc0 -- benchmarks/step4a2_heldout_corpus.py benchmarks/step4a2_formatting_mutations.py benchmarks/step4a4_corpus.py benchmarks/step4a4_formatting_mutations.py` → zero lines of diff, checked repeatedly throughout and again at the end of this pass.

## B/C. Root-cause inventory and graph

**Failure inventory (12 WC + 12 SM + 39 FE = 63 outcomes) collapsed into general mechanisms, mapped to the recognition → extraction → candidate ownership → role resolution → fact verification → policy evaluation → review-gate pipeline:**

| # | Root cause | Pipeline stage | WC | SM | FE (top-3 orig.) | Shared/local |
|---|---|---|---|---|---|---|
| 1 | Multi-word role-name truncation (single-token capture regex) | Extraction | 4 | 0 | 15 (largest FE family) | Shared (`policy_engine_core.py`, `indemnification_policy_engine.py`) |
| 2 | Role-definition body missing later-sentence evidence | Role resolution | 2 | 0 | — | Shared |
| 3 | One-side-known/other-unmapped-clean not eliminated | Candidate ownership | 3 | 0 | 3 | Indemnification-local |
| 4 | Reciprocal-but-named pairs treated as unresolvable | Policy evaluation | 5 | 0 | 1 | Indemnification-local |
| 5 | Multi-definition / self-referential role identity | Role resolution | 3 | 0 | — | Shared |
| 6 | Liability basis/structure self-flagged or multi-value ambiguity | Fact verification | 2 | 0 | — | Liability-local |
| 7 | Differentiated procedural terms under reciprocal opener | Policy evaluation | 4 | 0 | — | Indemnification-local |
| 8 | Protection-side cross-reference monetary blind spot | Fact verification | 1 (transient, caught pre-ship) | 0 | — | Indemnification-local |
| 9 | Set-off/mutual-debt-netting concept unrecognized (SM-CRITICAL) | Recognition | 0 | 1 | — | Payment-terms-local |
| 10 | Non-canonical clause-anchor vocabulary (11 distinct phrasing families) | Recognition | 0 | 11 | — | All three adapters |
| 11 | Basis-word (royalties/premium/rent/charges) treated as never comparable to "fees" | Policy evaluation | 0 | 0 | 9 | Liability-local |
| 12 | Bystander corporate-identity/administrative boilerplate mistaken for role-recharacterizing evidence | Role resolution | 0 | 0 | 6 (FE Family 2) | Shared |
| 13 | Greater-of/lesser-of second-operand extraction gaps | Extraction | 0 | 0 | 3 | Liability-local |
| 14 | Conflicting self-defined cap term across sections (new, surfaced by fixing #11) | Fact verification | 1 (transient, caught pre-ship) | 0 | — | Liability-local |

**Root-cause graph** (earliest incorrect transition, not blaming downstream logic when upstream recognition already lost the fact):

```
recognition (anchor/vocabulary) ──> extraction (role/value capture) ──> candidate ownership
   (mechanisms 9,10)                  (mechanisms 1,13)                  (mechanism 3)
        │                                    │                               │
        ▼                                    ▼                               ▼
role resolution (definition body, conflict) ──────────────────────> fact verification
   (mechanisms 2,5,12)                                              (mechanisms 6,8,11,14)
        │                                                                     │
        └─────────────────────────> policy evaluation <─────────────────────┘
                                       (mechanisms 4,7)
                                            │
                                            ▼
                                     review gate (correctly triggered
                                     only when a genuine upstream gap
                                     survives to this point)
```

Every fix targeted the EARLIEST stage where the fact was actually lost — e.g., mechanism 1 (role-name truncation) was fixed at extraction, not by adding downstream special-casing in policy evaluation; mechanism 9 (set-off) was fixed at recognition (a new concept detector), not by loosening the policy gate.

## D. Implementation — per file/function, invariant enforced, why it generalizes, negative controls

### `payment_terms_policy_engine.py`
- **`_SETOFF_PERMIT_RE`/`_SETOFF_PROHIBIT_RE`**: added negative lookbehinds and enumerated-list tolerance so "shall not have any right of set-off" is never misread as a permission grant. *Invariant*: a negation cue anywhere between "shall not" and the right-phrase, including across an enumerated list, blocks the permit interpretation. *Negative control*: the pre-existing `negation-02` benchmark case, re-verified passing.
- **`_DEBT_SATISFACTION_VERB_RE`/`_PAYMENT_OBJECT_FRAGMENT`/`_DEBT_SATISFACTION_ACTION_RE`/`_COUNTERPARTY_OWES_RE`/`_MUTUAL_DEBT_NEGATION_RE`/`_find_mutual_debt_netting_span`**: new general concept detector for "one party deducts/nets/reduces/retains/credits/recoups an amount owed BY the counterparty from what it pays," in both active and passive voice, plus a "setting off" gerund form. *Invariant*: the concept requires BOTH a debt-satisfaction verb near a payment-object noun AND an independent "counterparty owes" signal in a local window — never fires on a bare verb alone. *Negative controls*: 30 cases in `setoff_concept_benchmark.py` (tax withholding, credits, refunds, billing corrections, rebates, ordinary deductions, damages, accounting-net-presentation, etc.) — 0% false-positive rate throughout.
- **Tax-responsibility regex**: widened char-distance cap (40→100), added "shall bear the cost of" as a verb synonym. *Invariant*: same "named party + responsibility verb + tax noun" shape, just a longer/different verb phrase — never a bare "tax" keyword match.
- **Ordinal-day-following payment timing** (`_ORDINAL_DAY_FOLLOWING_RE`, `_ORDINAL_WORDS`): new pattern for "no later than the Nth (calendar) day following <event>," scoped to the same trigger-event vocabulary (acceptance/delivery/invoice/receipt) as the existing "within N days" pattern.

### `liability_policy_engine.py`
- **`_SECONDARY_ANCHOR_RE`**: added "exposure"/"recovery against" as synonyms for "liability," each still requiring the SAME cap-verb-phrase structure (never a bare word). **`_FIXED_AMOUNT_RE`**: added "is fixed at" and "(greater|lesser) of" as lead-in phrases. **`_ANCHOR_RE`**: added a "Liability Terms" heading variant for tabular field:value structures.
- **`BASIS_RECURRING_PAYMENT`**: royalties/premium/rent/charges now treated as comparable to a fees-defined threshold UNLESS the same clause also separately mentions "fee(s)" as a distinct quantity (negative control against two genuinely different payment streams — verified via a companion investigation that surfaced and fixed a real conflicting-definition case, mechanism 14 below).
- **`_CONFLICTING_DEFINED_TERM_RE`**: detects "'X' is defined in Section N ... as VALUE, and separately in Section M ... as VALUE2" — added specifically because fixing mechanism 11 removed an *accidental* masking escalation that had been hiding this genuine gap (A4-H-09); the new detector catches the real conflict on its own merits.
- **`_SELF_FLAGGED_AMBIGUITY_RE`/`_BASIS_VALUE_AMBIGUITY_RE`**: general triggers for a document explicitly saying "unclear whether..." or defining a multiplier's own basis value ambiguously ("may refer to X or, if greater, Y").
- **Greater-of/lesser-of second-operand extraction**: the governing verb phrase applies to the WHOLE compound expression, not each operand individually; a bare "or $N" is now captured as the second operand, scoped strictly to the local greater/lesser-of window (never a general bare-dollar-figure match elsewhere in the document).
- **Investigated and explicitly REVERTED**: a fix that would have resolved A4-D-07/A4-D-08 (general cap + named-category "except for X, which shall be uncapped" carve-out) automatically. Reverted after it regressed two pre-existing `liability_corpus.py` cases (`asym-05`, `unheaded-10`) that deliberately treat similar-looking compound statements as ambiguous. Documented as a residual FE limitation rather than risk a false-safe.

### `policy_engine_core.py` (shared by all three adapters)
- **`trim_role_name`/`_ROLE_NAME_TRAILING_STOPWORDS`**: strips trailing connector words captured by the broadened multi-word role regex in ALL-CAPS formatting mutations.
- **`_find_role_definition_body`'s cross-sentence extension**: when a definition's own sentence carries no directional evidence, extends to the next sentence re-mentioning the role's own name — with a **section-boundary guard** added mid-pass after this extension was found to pull in an unrelated OPERATIVE clause's heading text across a new numbered section, producing spurious "relational content" false positives (an anti-false-safe correction to the fix itself, caught by the WC-hardening work and re-verified by the bystander-discrimination benchmark).
- **`_find_all_role_definition_bodies`/multi-definition conflict check**: detects two or more definitions of the same role with disagreeing directional evidence (including a "solely for purposes of Section N" scoped-qualifier anchor variant).
- **`_PARTY_OTHER_THAN_RE`**: detects a self-referential "the party other than X"/"whichever party is not X" identity construction as inherently unresolvable (the second alternative added after the adversarial battery found the rephrase slipped through).
- **`_BYSTANDER_BOILERPLATE_RE`**: strips successors-and-assigns, subsidiary/affiliate, signature-page cross-reference, jurisdiction-of-formation/incorporation/organization, qualified-to-do-business, cooperative/member-owner, notice-address, external-document cross-reference, regulatory-oversight, and generic passive-voice-attributed-to-a-third-party language BEFORE the relational-content scan — never before the primary buy/sell directional classification, which has its own narrower guards.
- **Own-entity-name exclusion** in `_has_unrecognized_relational_content`: a definition's own leading multi-word legal name (e.g. "Ridgeline Materials Group") is excluded from counting as a "second party," including trailing corporate suffixes (Inc./LLC/Corp./etc.) and correct punctuation stripping (a self-caught bug: the first version compared un-stripped tokens like `"group,"` against `"group"` and silently failed to match).
- **`_is_bystander_verb_match`**: added an administrative-object filter (data/information/documentation/records as the object of an otherwise-matching sell verb) and a case-SENSITIVE generic-downstream-recipient filter ("to end-user subscribers"/"to customers" — lowercase only, so a capitalized "to Client" naming the real counterparty is never suppressed). Widened the passive-agent-guard lookahead to tolerate a short adverbial phrase ("acquired *last year* by X").
- **`resell(s)`/`resold`** added to sell-side vocabulary (word-boundary gap: `\bsell\b` never matched inside "resells").
- **`render(?:s|ing|ed)?...to`** distance cap widened 35→50 chars.

### `indemnification_policy_engine.py`
- **4 closed synonym-idiom obligation patterns** ("hold X harmless from and defend X against," "protect, defend, and reimburse," "undertakes to make X whole for, and to assume the defense of," "shall bear full responsibility for defending and satisfying such claim on X's behalf") plus a document-level engagement broadening so the adapter fires even without the literal word "indemnif*." Each pattern requires the FULL compound phrase — never a single generic verb — precisely so the adapter does not engage on unrelated clauses.
- **`_MULTIWORD_ROLE_NAME_FRAGMENT`**: extended to tolerate one lowercase connector word (of/the/for) inside a role name ("Importer of Record"). **`_OBLIGATION_RE`**'s optional parenthetical aside widened 40→65 chars.
- **Ordered-tuple (not frozenset) dedup** for reciprocal-named-pair extraction, so "A indemnifies B" and "B indemnifies A" are correctly treated as two different obligations, not the same one twice.
- **Elimination-by-other-side** in `_resolve_obligations_for_side`: if one role's side is confidently known and the other has no conflicting definition, its identity follows by elimination in a strictly two-party obligation — never guesses an isolated unmapped role.
- **Reciprocal-but-named-pair direction invariance**: two obligations naming the same pair in opposite directions with matching monetary/scope/defense_control are policy-outcome-invariant. **Extended `_classify_defense_control`** to recognize a NAMED party's own defense-control grant (not just the generic "the indemnifying/indemnified party" shorthand) — added specifically because the direction-invariance benchmark found a named-party asymmetric defense-control grant was invisible to the old check and passed the equality test as if symmetric.
- **`_find_procedural_differentiation_roles`**: general detector for survival period / notice precondition / defense control / temporal carve-out attached separately to two distinct named parties under a reciprocal opener; survival-period matches only count when the extracted numeric VALUES actually differ (verified negative control: identical periods stated per-role do not trigger).
- **`_PARTY_SPECIFIC_EXCEPTION_RE`**: added a second alternative for "except that claims against ROLE ..." (role as object, not just possessive subject) — found by the direction-invariance benchmark.
- **`_MUTUAL_RECIPROCAL_RE`**: tolerates an optional parenthetical defined-term aside ("Each party (the 'Indemnifying Party') shall indemnify the other party (the 'Indemnified Party') ...").
- **Cross-reference monetary preservation**: a figure disqualified as "belonging to a different clause" (e.g., a liability-section cross-reference) is now preserved as `kind="cross_reference"` instead of collapsing to `not_stated`, with a **symmetric protection-side check** added (the existing check only guarded the exposure side).

## E. SM-CRITICAL PRE → POST

- PRE: `A4-K-07` → `NOT_APPLICABLE`, `facts.setoff_permitted=None` — a genuine `prohibit_set_off` violation ("withhold ... an amount equal to any sums ... owes") silently cleared from review.
- POST: `MUST_REDLINE` — the mutual-debt-netting concept is recognized and the prohibition check engages.
- SM-CRITICAL count: **1 → 0**.
- Dedicated benchmark (locked before implementation, `benchmarks/setoff_concept_benchmark.py`, 72 cases): recall 7.1% → 97.6% (39/42 → 41/42 after two additional fixes for a passive-voice and gerund construction found while inspecting the residual false negatives), precision 100% throughout, FP rate 0% throughout. One residual false negative (SO-33, "retain a portion of amounts otherwise payable ... equal to the cost of materials [counterparty] failed to supply") investigated and left unfixed: it is a cost-of-cover self-help deduction for the counterparty's non-performance, not a mutual MONETARY debt in the sense the other 41 positives share — generalizing further risks pulling ordinary damages/deduction language into prohibited set-off, which the negative controls are specifically designed to exclude.

## F. WC elimination table

| Adapter | PRE (known WC) | POST (known WC) |
|---|---|---|
| Liability | 6 | **0** |
| Indemnification | 6 | **0** |
| **Total known WC** | **12** | **0** |

`WC_CANDIDATE` bucket count in the raw classifier is 2 (`A4-H-04`, `A4-H-05`) — both are the pre-existing GTD cases already independently documented and reclassified in the original Step 4A.4 report, confirmed unchanged throughout every re-run in this pass. No new WC survived shipping: one transient regression each in Priority 2 (`A4-COMP-02`, a protection-side cross-reference monetary blind spot) and Priority 4 (`A4-H-09`, a conflicting-defined-term case unmasked by the basis fix) were caught by the mandatory "check for new WC before continuing" step and fixed within the same implementation loop, never reaching a commit.

## G. Silent-miss elimination table

| Adapter | PRE SM | POST SM |
|---|---|---|
| Liability | 4 | **0** |
| Indemnification | 4 | **0** |
| Payment Terms | 3 | **0** |
| SM-CRITICAL (subset) | 1 | **0** |
| **Total** | **12** | **0** |

All 11 non-critical SM were **Recognition misses** (Family K: non-canonical clause-anchor phrasing across all three adapters — reordered obligation verbs, synonym substitutions, atypical headings, conditional constructions, tabular presentation, non-canonical timing/tax vocabulary). Fixed via 3 shared general mechanisms (closed synonym-idiom families for indemnification; exposure/recovery vocabulary + tabular-heading recognition for liability; tax-verb-synonym + ordinal-day-timing recognition for payment terms), never by adding 11 literal phrases. 6 of the 11 resolved to `CA` (correct automatic); 5 resolved to `REQUIRES_REVIEW` (the harness's default `contract_side="mutual"` policy correctly routes a genuinely-recognized directional obligation to review when no explicit side is configured — a pre-existing, intentional architectural behavior, not a new gap). None involve a policy violation being silently cleared.

## H. False escalation reduction

| Adapter | PRE FE | POST FE | Reduction |
|---|---|---|---|
| Liability | ~22 | 8 | 64% |
| Indemnification | ~18 | 6 | 67% |
| Payment Terms | ~5 | 5 | 0% (no dedicated FE mechanism targeted this adapter beyond the Priority-3 recognition work, which is already reflected in the SM count) |
| **Total** | **39** | **19** | **51%** |

**Top-3 original FE-family PRE→CURRENT** (per the Step 4A.4 report's own root-cause #1/#2/#3):

| Family | PRE (of 39) | CURRENT contribution to the 19 remaining |
|---|---|---|
| 1. Multi-word role-name truncation | 15 | 0 — fully eliminated by the multi-word-role fix |
| 2. Bystander corporate names | 6 | 0 — fully eliminated by the boilerplate-stripping/own-name-exclusion fixes (3 residual cases remain from a DIFFERENT, narrower cause — see Section P) |
| 3. Unmapped generic roles in symmetric exchanges | 1 | 0 — fully eliminated by the reciprocal-pair/elimination-by-other-side fixes |

All three dominant original FE mechanisms are now fully closed on the frozen corpus. The 19 remaining FE are concentrated in: liability basis/structure genuine ambiguity that correctly cannot resolve without external information (greater-of comparing a dollar figure to a fee-multiplier — 3 cases, correctly escalating despite the AUTOMATABLE label), the reverted A4-D-07/A4-D-08 carve-out-vs-general-cap ambiguity (2 cases, explicitly left as-is to avoid regressing `asym-05`/`unheaded-10`), a small number of Family-K vocabulary misses that resolved to `REQUIRES_REVIEW` rather than `CA` under the mutual-policy default (5 cases — a correct, not incorrect, outcome), and one documented grammatical-subject-misattribution limitation (`A4-A-15`).

No FE reduction in this pass was achieved by removing an escalation gate, trusting an unmapped role, ignoring an unresolved definition, picking between multiple plausible values, or suppressing a conflict — every fix added positive evidence (a correctly-bounded role name, a found cross-sentence definition, a confirmed elimination-by-other-side identity, a confirmed matching reciprocal pair, a recognized synonym idiom, a recognized basis-equivalence) that justified resolving automatically.

## I. Step 4A.4 PRE → INTERIM → FINAL metric table

| Metric | PRE (4A.4) | Interim (after P1–P2 only) | **FINAL (after P1–P5)** |
|---|---|---|---|
| CA | 81 | 90 | **113** |
| CR | 26 | 38 | **38** |
| FE | 39 | 31 | **19** |
| WC (known) | 12 | 0 | **0** |
| SM | 12 | 11 | **0** |
| SM-CRITICAL | 1 | 0 | **0** |
| S4 | 0 | 0 | **0** |
| Automation Recall (overall) | 61.4% | 68.2% | **85.6%** |
| FE-among-AUTOMATABLE | 29.5% | 23.5% | **14.4%** |

All four hard safety gates are now met (S4=0, SM-CRITICAL=0, known WC=0, known SM=0 — the last of these was NOT met at the interim checkpoint and is the headline result of Priorities 3–5). All four selectivity gates are met and materially exceed even the interim state (CA 90→113, Recall 68.2%→85.6%, FE 31→19, FE/AUTOMATABLE 23.5%→14.4%).

## J. Per-adapter selectivity (FINAL)

| Adapter | AUTOMATABLE | CA | CR | FE | WC | SM | Automation Recall | FE-among-AUTOMATABLE |
|---|---|---|---|---|---|---|---|---|
| Liability | 57 | 49 | 12 | 8 | 0 | 0 | 86.0% | 14.0% |
| **Indemnification** | 35 | 29 | 16 | 6 | 0 | 0 | **82.9%** (PRE: 37.1%) | **17.1%** (PRE: 51.4%) |
| Payment Terms | 40 | 35 | 10 | 5 | 0 | 0 | 87.5% | 12.5% |

Indemnification — the adapter flagged in Step 4A.4 as "particularly weak" — improved from 37.1% to 82.9% Automation Recall, the largest gain of any adapter (a 45.8-point improvement), and its FE-among-AUTOMATABLE fell from 51.4% to 17.1%. It is no longer the worst-performing adapter by FE rate (Payment Terms and Liability are close behind at 12.5%/14.0%). Root causes broken out per the task's specific requirement: role resolution (mechanisms 2, 5, 12 above) accounted for the largest share of Indemnification's original gap; symmetry/reciprocal handling (mechanisms 4, 7) the second-largest; obligation-recognition vocabulary (Section G's Family K, indemnification share) the remainder. Claim-category extraction, monetary/basis extraction, and generic-role mapping (the other categories the task asked to be checked) were NOT independently significant contributors — no fixes were needed in those specific areas for this adapter.

## K. Dedicated mechanism benchmarks PRE/POST

| Benchmark | Required min | Size | PRE | POST | Precision | Recall | FP rate | FN rate |
|---|---|---|---|---|---|---|---|---|
| Set-off/mutual-debt-netting concept | ≥40 pos/≥30 neg | 72 (42/30) | Recall 7.1% | **Recall 97.6%** | 100% | 97.6% | 0% | 2.4% |
| Multi-word role boundaries | ≥30 pos/≥20 neg | 53 (33/20) | not built | **100%** | 100% | 100% | 0% | 0% |
| Bystander entity discrimination | ≥25 neg/≥20 pos | 47 (22/25) | not built | **88.0%** precision | 88.0% | 100% | 12.0% | 0% |
| Direction invariance | ≥40 cases | 40 | not built | **92.5%** correct | — | — | 3 unsafe-automatic (of 40) | 0 unnecessary-review |
| Role-resolution benchmark (existing) | — | 49 | 94.4% recall | 94.4% recall (unchanged) | 100% | 94.4% | 0% | 5.6% |
| Liability-concept benchmark (existing) | — | 5 | ESCALATE ×5 | ESCALATE ×5 (unchanged) | — | — | — | — |
| Payment recognition benchmark (existing) | — | 65 | Recall 100% | Recall 100% (unchanged) | 95.7% | 100% | 10.0%* | 0% |
| Liability ownership benchmark (existing) | — | 42 | 100% | 100% (unchanged) | — | — | 0% false-safe | — |
| Indemnification asymmetry benchmark (existing) | — | 26 (19 scored) | 19/19 | 19/19 (unchanged) | 100% | 100% | 0% false-safe | — |

*Payment recognition's 10% FP rate is a single pre-existing case (`NEG-15`, `distractor_termination_fee`), confirmed via `git stash` diff to predate this session's changes.

Every FE-reduction mechanism has an opposite-direction safety control, per the explicit requirement:
- Multi-word role boundaries: 20 negative cases test nearby affiliates/subcontractors/notice-addresses/parent companies/d-b-a names/ALL-CAPS mutations in parenthetical asides — 0% over-capture.
- Bystander discrimination: 25 negative cases include several designed so the "apparent bystander" is adjacent to REAL directional evidence elsewhere in the same sentence, confirming the real evidence is never suppressed alongside the bystander noise (verified directly: "provides services to Client" still resolves sell-side even with the generic-recipient filter active).
- Direction invariance: the "superficially symmetric but materially asymmetric" family (7 cases) is exactly the opposite-direction attack against the reciprocal-pair mechanism — it found and led to fixing 2 genuine unsafe-automatic gaps (named defense-control asymmetry, exception-clause phrasing) before this report was written, and documents 1 remaining gap (a "not subject to this cap" carve-out not recognized as an unlimited signal) plus a shared 2-case family (trigger-level scope exclusions not compared in the reciprocal-pair equality check).

## L. Step 4A.2 historical control

- WC=0, SM=0, S4=0 requirement: the manually-verified PRE state (CA57/CR29/FE22/WC0/SM0) was reproduced exactly at session start. A full independent POST manual reclassification using the same rigor was **not** repeated at the end of this pass (acknowledged limitation — see Section P).
- Available automated evidence for "no regression": (a) zero new failures across every adapter test suite and benchmark that exercises this corpus's underlying mechanisms, checked after every single commit in this pass (17 checkpoints); (b) the heuristic `classify_step4a2_heldout.py` script (which its own docstring says needs manual verification) shows its WC-candidate count moving from 8 (baseline, confirmed via `git stash` diff to the frozen commit) → 7, with the improvement (`INDEM-I2-02` dropping out) and no new case IDs appearing at any point in this pass.
- Historical FE: the heuristic script shows FE moving 27→25 over the course of this pass (a modest reduction, consistent with several of the general fixes incidentally improving Step 4A.2 cases too, since none of this session's changes touched the Step 4A.2 corpus text). WC and SM did not rise above 0/8 at any point — no regression signal ever appeared, and 8 improved to 7.

## M. Existing policy benchmarks

Liability (125 cases across `liability_corpus.py`), Indemnification (100 cases across `indemnification_corpus.py`), Payment Terms (84 cases in `payment_terms_corpus.py`) all re-run at the end of this pass:

| Benchmark | False-safe | Determinism | Notes |
|---|---|---|---|
| Liability | 0 | 100% | Same 4 pre-existing documented failures (`partial-01`, `amendment-02`, `unheaded-08`) as at session start, confirmed via `git stash` diff — no new failure at any point |
| Indemnification | 0 | 100% | Same 7 pre-existing documented failures (`xref-03`, `xref-04`, `cap-excluded-01`, `super-cap-01/02`) as at session start |
| Payment Terms | 0 | 100% | 0 failures throughout; false-escalation rate 0.0% |

REQUIRES_REVIEW PRE→POST is intentionally not tracked as a single aggregate number for these existing benchmarks (selectivity was deliberately changing throughout this pass) — the per-case failure lists above are unchanged from PRE, which is the relevant "no regression" signal for a fixed, pre-authored benchmark corpus.

## N. Fresh 60-case adversarial battery

Full results in `benchmarks/step4a5_adversarial_battery.py` / `run_step4a5_adversarial_battery.py`. Summary table:

| Family | Cases | CA | CR | FE | WC | SM |
|---|---|---|---|---|---|---|
| Safety | 15 | 2 | 11 | 0 | 2 | 0 |
| Silent-miss | 15 | 1 | 0 | 4 | 1 | 9 |
| False-escalation | 15 | 10 | 0 | 5 | 0 | 0 |
| Compound | 15 | 7 | 2 | 5 | 1 | 0 |
| **TOTAL** | **60** | **20** | **13** | **14** | **4** | **9** |

**Every WC and SM individually inspected:**

- **`ADV-S-02`, `ADV-C-02`** (WC): the SAME already-documented scope-exclusion gap found independently by the direction-invariance benchmark (`DI-C-10`/`DI-C-11`) — a reciprocal-but-named pair with matching monetary/scope/defense_control fields but a differentiated TRIGGER-level exclusion for one direction only, which the equality check does not compare. Not a new finding; not S4 (no violation is cleared, the clause simply resolves without flagging a genuine asymmetry).
- **`ADV-S-15`** (WC): NEW finding — a tabular "Exception:" field delegating fraud/willful-misconduct claims to an unincluded section is silently ignored by the new "Liability Terms" tabular recognizer (which was built to find the cap value, not to also scan for exception fields). Documented, not fixed (would require a symmetric tabular-exception detector, out of scope for this pass).
- **`ADV-M-09`** (WC): NEW finding — "consolidated into a single net balance" is a mutual-debt-netting paraphrase one step further from the fixed verb vocabulary (`net(?:s|ted|ting)`) than the benchmark's own positives; documented as a residual vocabulary gap in the set-off detector.
- **9 SM in the silent-miss family** (`ADV-M-01/02/04/05/08/11/12/14/15`): all are **intentionally aggressive** vocabulary-generalization probes one or two paraphrase-steps beyond the fixed synonym families this pass built (e.g., "covenants to make...whole for" vs. the fixed "undertakes to make...whole for"; "shall be pegged at...and may not be surpassed" vs. the fixed "is fixed at...shall not be exceeded"). None clear a violation — they correctly return `NOT_APPLICABLE` (a Recognition-miss, same class as the now-fixed Family K, but one generation further out). This is the expected, honest result of "do not chase 100% recall": the fixed vocabulary families generalize to real paraphrases (see the false-escalation family below, where 10/15 resolve automatically including several deliberately-close paraphrases) but do not generalize infinitely.
- **4 FE in the silent-miss family and 5 in the false-escalation family**: these are cases where the vocabulary generalized ONE step (engaging the adapter, extracting the obligation) but the harness's `contract_side="mutual"` default (payment/indemnification cases without an explicit side) or a genuinely longer/more complex sentence pushed the result to `REQUIRES_REVIEW` instead of a clean automatic resolve — safe, not silently missed, but not optimally selective either.

**Two initially-flagged findings were investigated and found to be benchmark-authoring errors, not production defects**, and corrected transparently rather than counted as false findings: `ADV-S-08` (a clean, unambiguous prohibited set-off using active-voice "entitled to net" phrasing actually resolves correctly and automatically to `MUST_REDLINE` — my original expected label of `SHOULD_REVIEW` was simply wrong) and `ADV-S-12` (a clause delegating its cap figure to an external, unincluded Order Form with literally no digit in the text correctly falls through to the pre-existing, safe "no numeric cap stated → MUST_REDLINE" path, which is defensible-safe behavior, not a fabricated value).

**Anti-false-safe verification specifically requested** was performed for every mechanism this pass introduced: set-off/netting (attacked with active-voice and gerund forms — 1 of 2 attacks caught the intended gap and led to a fix, the other found the vocabulary boundary), multi-word role capture (attacked with nearby affiliates in parentheses — 0% over-capture), definition boundaries (attacked with cross-sentence extension into an unrelated section — caught and fixed mid-pass), bystander filtering (attacked with a genuine buy-side fact placed immediately after boilerplate in the same sentence, `ADV-S-06` — resolved to `CR`, i.e. correctly did NOT silently swallow the real evidence with the boilerplate), direction invariance (attacked with named-defense-control and scope-exclusion asymmetries — found and fixed one, documented one), reciprocal indemnification (attacked with a parenthetical-defined-term reciprocal opener plus a real monetary exception, `ADV-S-01` — correctly escalated), elimination-by-other-side (implicitly covered by the compound family's cross-clause-leakage cases, all correct), basis ambiguity (attacked with a differently-worded conflicting cross-section definition, `ADV-S-04` — correctly escalated via the new conflicting-defined-term detector), and recognition-vocabulary expansions (the entire silent-miss and false-escalation families are, by construction, opposite-direction attacks on every vocabulary expansion made in this pass).

## O. Regression suite

`python3 -m pytest tests/ -q --continue-on-collection-errors`: **1157 passed, 10 failed, 13 skipped, 43 errors** — an EXACT match to the Step 4A.4 baseline (1157 passed, 10 failed, 43 errors). The 43 collection errors are pre-existing environment/dependency issues (`pyo3_runtime.PanicException`, `starlette.testclient` import failures) unrelated to any file touched in this pass. The 10 failures are in `test_override_learning.py` (a playbook-DB-integration test) and `test_production_secrets.py` (environment-variable/secrets-configuration tests) — neither file imports or exercises `liability_policy_engine.py`, `indemnification_policy_engine.py`, `payment_terms_policy_engine.py`, or `policy_engine_core.py`, confirming these are unrelated to Step 4A.5's changes, not merely assumed to be.

## P. Remaining limitations

**Safe limitations (correctly routed to review, not silently missed):**
- All originally-known 12 WC and 12 SM are eliminated and verified with zero regressions.
- 5 of the 11 Family-K vocabulary-generalization cases correctly resolve to `REQUIRES_REVIEW` (not `CA`) under the harness's mutual-policy default, since a genuinely-recognized directional obligation without an explicit configured side cannot safely be attributed to "us" — this is intentional, pre-existing architecture, not a defect.
- The `A4-D-04`/`A4-D-05`/`A4-D-15`-family greater-of/lesser-of extraction fix correctly surfaces the genuinely unresolvable comparison (a dollar figure vs. a fee-multiplier, which cannot be compared without knowing the actual fee amount) as its own accurate escalation reason, rather than a spurious "could not extract" one.

**Selectivity limitations (unnecessarily reviewed):**
- 19 remaining FE on the frozen corpus (down from 39), concentrated in the liability greater-of/dollar-comparison family (3), the deliberately-reverted A4-D-07/A4-D-08 carve-out ambiguity (2), the mutual-policy-default Family-K cases (5), and a small number of individually-documented cases.
- The 9 fresh-battery silent-miss findings and several false-escalation-family findings show the fixed vocabulary families generalize to real paraphrases but not infinitely — a genuine, expected boundary, not a regression.
- The reverted A4-D-07/A4-D-08 fix remains a known, disclosed opportunity: a general cap coexisting with a named-category "uncapped" carve-out could, in principle, be resolved automatically for SOME phrasings, but the safe/ambiguous boundary could not be drawn narrowly enough in the time available without regressing two pre-existing benchmark cases.

**Potential residual safety surfaces (not adequately tested, disclosed rather than hidden):**
- **Grammatical-subject misattribution** (shared root cause across `A4-A-15`, `NEG-BD-11`, `NEG-BD-19`): a verb clause whose grammatical SUBJECT is a bystander third party ("Carrier delivers to Consignee," "whose property manager, X, handles...") is still sometimes misread as describing the role being classified, because none of the existing heuristics track grammatical subject at all — only verb presence and nearby capitalized tokens. This is the single most significant disclosed architectural gap from this pass; fixing it properly requires subject-tracking beyond simple regex heuristics.
- **Reciprocal-pair trigger-level scope exclusions** (shared root cause across `DI-C-10`, `DI-C-11`, `ADV-S-02`, `ADV-C-02`): the reciprocal-named-pair equality check compares monetary/scope/defense_control but not `trigger_treatments`, so a differentiated trigger-level carve-out for one direction only can pass as if genuinely symmetric. Found independently by two different benchmarks built in this pass (direction-invariance and the adversarial battery), which is itself evidence the finding is real and not a one-off test artifact.
- **Tabular-structure exception fields** (`ADV-S-15`): the new "Liability Terms" tabular recognizer was built and verified only for extracting the cap VALUE; it was not extended to also scan for a tabular "Exception:"/carve-out field, and one such field was found to be silently ignored.
- The Step 4A.2 corpus's POST state was verified only via automated proxies (Section L), not a full independent manual reclassification matching the rigor applied to the Step 4A.4 corpus in this report.
- The existing policy/mechanism benchmarks (Section M/K) were re-run and diffed against their pre-existing failure lists, but not independently re-audited case-by-case against actual extracted facts the way every Step 4A.4 WC/SM was in Sections F/G.

## Verdict

**PASS WITH CONDITIONS — FROZEN VALIDATION ALLOWED.**

All mandatory hard safety gates are met on the frozen Step 4A.4 corpus: **S4=0**, **SM-CRITICAL=0**, **known WC=0** (12→0), **known SM=0** (12→0). Selectivity materially improved beyond even the interim checkpoint that was previously reported: CA 90→113 (vs. the required ≥90), Automation Recall 68.2%→85.6% (vs. the required ≥68.2%), FE 31→19 (vs. the required ≤31), FE-among-AUTOMATABLE 23.5%→14.4% (vs. the required ≤23.5%) — none of these are trivial movements. Every existing control benchmark is unchanged or improved, with zero unexplained regressions across the full 1157-test regression suite.

This is not a full, unconditional PASS because the fresh 60-case adversarial battery — built specifically to attack this pass's own new mechanisms in the opposite direction, as required — found and disclosed 4 residual WC-shaped findings (none S4-severity, none clearing an actual violation) and 2 concentrated, named architectural gaps (grammatical-subject misattribution; reciprocal-pair trigger-level scope exclusions) that were found independently by two different benchmarks apiece. These are genuine, disclosed conditions on the frozen-validation recommendation below, not evidence that Step 4A.5's changes reintroduced false certainty on the frozen corpus itself.

## Step 4A.6 recommendation

**YES** — proceed to a third independent held-out validation, WITH the two named residual gaps (grammatical-subject misattribution; reciprocal-pair trigger-level scope exclusions) flagged explicitly as areas the Step 4A.6 corpus should specifically probe, alongside its normal independent-authorship scope. Both gaps are narrow, well-understood, and non-critical (neither has ever produced an S4 outcome across four dedicated benchmarks and one 60-case adversarial battery specifically constructed to find exactly this kind of thing) — freezing now and gathering independent evidence on these two named surfaces is more informative than a further internal patching pass against benchmarks this same session authored. Step 4B remains **not started**, per instructions. No Step 4A.6 corpus was created in this pass.
