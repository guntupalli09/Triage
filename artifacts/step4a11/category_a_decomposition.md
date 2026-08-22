# Step 4A.11 Phase 3 — Category A Read-Only Root-Cause Decomposition

**Read-only. No production code touched to produce this document.**

## Provenance — real evidence, not fabricated

Unlike the original Section 4 inventory (which had to rely on the Step
4A.10 Phase 17 heuristic taxonomy alone, with no preserved corpus text),
this decomposition uses **actual case text**, recovered by re-running
`scripts/step4a10_generate_corpus.py` — a deterministic generator (no
`random`/seed usage) that reproduces the exact same 394-case corpus
(220 positives / 144 hard negatives / 30 injection cases) Step 4A.10
originally built and scored. Cross-checked: all 88
`Q_verifier_lacks_structural_pattern` case IDs from
`artifacts/step4a10/analysis_full.json`'s `phase17_bottleneck_taxonomy`
are present in the regenerated corpus, with byte-identical text (same
generator, same order, no randomness).

For all 88 cases: the CURRENT (post-Phase-1/Phase-2) `indemnification_
policy_engine.extract_indemnification_facts` was run read-only. Result:
**0/88 produce any obligation today** — `_OBLIGATION_RE` and all 10
`_SYNONYM_OBLIGATION_RES` fail to match on every single case, confirming
this bucket is genuinely about the OBLIGATION-RECOGNITION stage itself
(not accidentally already fixed by Phase 1/2, which addressed
cross-reference and conditional-applicability, not obligation
structuring).

Full case-family census (regex-classified against the 88 actual case
texts, 0 unmatched — every case accounted for):

| Family | Count | % of 88 | Example verb shape |
|---|---:|---:|---|
| `hold_role_harmless_midinsert` | 10 | 11.4% | "shall indemnify and **hold Client harmless** from..." |
| `keep_unharmed` | 6 | 6.8% | "agrees to **keep Controller** [financially] **unharmed**..." |
| `takes_responsibility_making_whole` | 6 | 6.8% | "takes responsibility for **making Sponsor** [financially] **whole**..." |
| `liable_to_compensate` | 6 | 6.8% | "will **be liable to compensate** Manufacturer for any loss..." |
| `carry_burden_of_claim` | 6 | 6.8% | "shall **carry the burden of** any claim brought against..." |
| `discharge_obligation_owed` | 6 | 6.8% | "shall **discharge any obligation** Bank would otherwise owe..." |
| `commits_covering_exposure` | 6 | 6.8% | "**commits to covering** Shipper's **exposure** resulting from..." |
| `relieve_of_financial_burden` | 6 | 6.8% | "shall **relieve** Investor **of** any **financial burden**..." |
| `undertakes_suffer_no_detriment` | 6 | 6.8% | "**undertakes that** Landlord **will suffer no monetary detriment**..." |
| `pay_on_behalf` | 6 | 6.8% | "shall **pay, on** Investor's **behalf**, any sum..." |
| `settle_at_own_expense` | 6 | 6.8% | "shall **settle, at** Distributor's **own expense**, any claim..." |
| `cover_expense_defending_definedterm` | 6 | 6.8% | "shall **cover any expense** Prime Contractor **incurs defending** a claim..." |
| `where_incurs_loss_reimburse` | 6 | 6.8% | "**Where** Purchaser **incurs a loss**..., Supplier shall **reimburse** Purchaser..." |
| `appositive_interrupt_shall_indemnify` | 3 | 3.4% | "Reseller, **on behalf of itself and its subcontractors**, shall indemnify Manufacturer..." |
| `leading_where_nominalized_obligation` | 3 | 3.4% | "Where a claim... arises..., Operator's **indemnification obligation**... **shall not apply**." |

**Total: 88/88 classified, 0 unmatched.**

## Mapping onto the requested A1–A16 taxonomy

- **A1 (proposition not recognized at all)**: `hold_role_harmless_
  midinsert`, `keep_unharmed`, `takes_responsibility_making_whole` —
  22/88 (25.0%). The underlying LEGAL CONCEPT is already authoritative
  ("indemnify," "hold harmless," "make whole" all already exist in
  `_OBLIGATION_RE`/`_SYNONYM_OBLIGATION_MAKE_WHOLE_RE`) but the SYNTACTIC
  POSITION of the object differs: "hold **Client** harmless" (object
  BETWEEN verb and predicate-adjective) vs. the only currently-supported
  order, "hold harmless **Client**" (object AFTER). This is the single
  most common English word order for this construction and is a pure
  WORD-ORDER generalization of an already-trusted verb concept, not a
  new one.

- **A1 (genuinely new, single-clause verb idiom, not previously covered
  at all)**: `liable_to_compensate`, `carry_burden_of_claim`,
  `discharge_obligation_owed`, `commits_covering_exposure`,
  `relieve_of_financial_burden`, `undertakes_suffer_no_detriment`,
  `pay_on_behalf`, `settle_at_own_expense`,
  `cover_expense_defending_definedterm`, `where_incurs_loss_reimburse` —
  60/88 (68.2%). None of these use "indemnif*," "hold harmless," or any
  phrase in the existing 10 compound synonym patterns. Each IS its own
  distinct verb concept — this is genuinely a vocabulary gap, not a
  parsing bug in an existing pattern. **Critical architectural finding**:
  every one of the 10 EXISTING synonym patterns
  (`_SYNONYM_OBLIGATION_HOLD_HARMLESS_RE` through `_SYNONYM_OBLIGATION_
  ANSWER_FOR_RE`) is a single, rigidly-ordered, COMPOUND multi-clause
  full-phrase template ("hold X harmless from and defend X against,"
  "protect, defend, and reimburse," "shall bear full responsibility for
  defending and satisfying such claims on X's behalf") — none of the 88
  cases use compound phrasing at all; they use much SIMPLER single-clause
  idioms. The existing architecture is a genuinely closed, exact-phrase
  vocabulary list (already flagged as such in its own code comments —
  "This widened list is still finite and still lexical — it is NOT the
  architectural fix"), and the 60 new idioms found here would, if solved
  the same way, simply be 10 MORE full-phrase entries in that same
  closed list — precisely the anti-pattern this phase's mandate warns
  against (Section 6).

- **A2 (subject established but an intervening structure breaks the
  match)**: `appositive_interrupt_shall_indemnify` — 3/88 (3.4%). Uses
  the fully canonical "shall indemnify" verb; the only obstacle is a
  comma-delimited appositive clause ("on behalf of itself and its
  subcontractors") between the subject role and the modal verb, which
  `_OBLIGATION_RE`'s optional-parenthetical allowance doesn't cover
  (parenthetical `(...)`, not comma-delimited appositive).

- **A14 (nominalized obligation structure, genuinely ambiguous)**:
  `leading_where_nominalized_obligation` — 3/88 (3.4%). These reference
  a PRE-EXISTING obligation via a noun phrase ("Operator's
  indemnification obligation under this Section") and state a scope
  restriction on it ("...shall not apply" under a stated condition), but
  no sentence anywhere in the case text ever states the underlying
  promise directly. There is no complete proposition to establish from
  this text alone — the case is *about* an obligation's conditional
  non-applicability, not a declaration that creates one.

## Per-family evaluation (case count / % / adapters / solvability / safety)

| Family | Count | % | Adapters | Sufficient info in text? | Failure stage | Structurally solvable? | Semantic discovery relevant? | Automation gain | Safety risk |
|---|---:|---:|---|---|---|---|---|---|---|
| `hold_role_harmless_midinsert` + `keep_unharmed` + `takes_responsibility_making_whole` (object-insertion, A1) | 22 | 25.0% | indemnification only | Yes — full directional promise stated | A1 — recognition | **Yes**, via a bounded word-order relaxation of an already-authoritative verb concept | Not needed (deterministic regex already sufficient once relaxed) | High, safe | Low — same verb concept, only object POSITION changes; existing role/claim-noun guards still apply |
| 10 single-clause verb idioms (A1, new vocabulary) | 60 | 68.2% | indemnification only | Yes — full directional promise stated in every case | A1 — recognition | **Yes, but requires new verb-cluster recognition** — genuinely a vocabulary-breadth problem, not a parsing bug. Solvable SAFELY only by separating (1) broadened, single-clause verb-cluster DISCOVERY from (2) a SHARED, reusable positional role-extraction routine (not 10 separate full-phrase regexes) | `_RISK_TRANSFER_SIGNAL_RE` already recognizes several of these verb families as non-authoritative DISCOVERY signals; extending it and reusing its claim/loss-noun proximity gate is the correct base to build on | High, but requires the most new mechanism | Moderate — must not turn into an ever-growing verb list; requires disciplined shared extraction + hard-negative testing, same rigor as `_OBLIGATION_RE` |
| `appositive_interrupt_shall_indemnify` (A2) | 3 | 3.4% | indemnification only | Yes | A2 — subject/actor structural interruption | Yes — small, safe, general regex relaxation | N/A | Low volume but very general (helps ANY future case with this shape) | Very low |
| `leading_where_nominalized_obligation` (A14) | 3 | 3.4% | indemnification only | **No** — no complete promise stated anywhere in the case text | A14 — nominalized reference to an obligation not itself declared | **No** — genuinely insufficient evidence in-document | N/A | None safely achievable | Attempting to manufacture a fact here would be exactly the "invent omitted actors / infer unstated obligations" failure mode Section 4 prohibits |

## Priority decision for this increment

Per Section 5's selection criteria (recoverable automation volume,
structural solvability, cross-adapter generality, safety):

1. **Selected for this increment: a unified "Structural Risk-Transfer
   Proposition Establishment" mechanism**, covering the object-insertion
   family (22 cases) AND the 10 single-clause verb idioms (60 cases) —
   82/88 (93.2%) of Category A — via ONE general design:
   - Broaden verb-cluster DISCOVERY (extending `_RISK_TRANSFER_SIGNAL_
     RE`'s existing, already-non-authoritative pattern family) to also
     recognize the new single-clause idioms and the object-insertion
     word order, still requiring the SAME claim/loss-noun proximity gate
     that signal already enforces.
   - Add ONE shared, reusable STRUCTURAL role-extraction routine that,
     given a verb-cluster match span, tries a small, bounded set of
     POSITIONAL STRATEGIES (subject immediately before the cluster;
     object immediately after; object introduced by "against"; object
     inside a possessive "X's exposure/behalf" slot; object inside a
     subordinate "X incurs"/"X would owe" clause) — this is the "operate
     on structural evidence inside an already-discovered span" approach
     Section 6 requires, not one full-phrase regex per idiom.
   - This is cross-adapter-generic in DESIGN (the positional-extraction
     routine belongs in `policy_engine_core.py`) even though every
     concrete verb cluster here is indemnification-specific (liability/
     payment_terms have no equivalent Category-A backlog from this
     corpus, since the Step 4A.10 corpus tests indemnification only).

2. **Deferred, documented, not attempted this increment**: the appositive-
   interruption fix (3 cases) is small enough to fold in cheaply once the
   main mechanism is built, if time permits, but is not the priority
   driver.

3. **Left as SHOULD_REVIEW, not solved**: `leading_where_nominalized_
   obligation` (3 cases, 3.4%) — the text genuinely does not contain a
   complete, establishable promise. Per Section 21, this is documented
   for the post-ship backlog rather than forced.

## What this decomposition does NOT claim

This is not a claim that 60 genuinely new, previously-unseen verb idioms
in the wild will map cleanly onto these same 13 families — the Step
4A.10 corpus is templated (each family here is ~6 near-duplicate
generation instances of one template), so the REAL held-out diversity of
"how do people phrase risk-transfer without saying indemnify" is
understated by this specific count, and overstated in how CLEANLY
delineated the families are. What this decomposition DOES establish,
with real evidence: (1) the specific verb constructions that this
corpus's true positives use and the current engine cannot recognize; (2)
that none of them require inventing facts — every A1/A2 case states a
complete, unconditional directional promise in the text; (3) that the
existing synonym-pattern architecture is a full-phrase closed list, and
extending it in the same style for 10 more idioms would repeat a known
anti-pattern rather than fix it.
