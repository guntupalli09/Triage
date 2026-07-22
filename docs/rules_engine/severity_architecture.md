# Severity Classification Architecture

Status: **proposed** — this document defines the target architecture. The
current 117 rules still carry legacy analogy-assigned severities pending the
migration in §9. Until Phase 5 of that migration completes, `Severity` on
`Rule` remains the source of truth and this document is not yet enforced.

This is intended as the permanent, versioned standard referenced by every
future rule contribution. It replaces "classify by analogy to a similar
rule" with a deterministic, auditable, factor-based scoring system.

---

## 1. Is a single CRITICAL/HIGH/MEDIUM/LOW axis sufficient?

**No.** A single ordinal label forces an *implicit, unrecorded* weighting of
several legally distinct dimensions every time someone assigns it:

- magnitude of exposure if the clause operates as written
- *what kind* of harm it is (money vs. a waived legal right vs. transferred
  ownership vs. regulatory/criminal exposure)
- whether the harm is reversible
- who bears it (the contracting entity vs. a natural person) and how many
  parties it can reach

Collapsing all of that into one label at authoring time is exactly the
"this feels HIGH" problem — the weighting still happens, it just happens
silently in a reviewer's head instead of on paper. It also can't be audited
after the fact: a reviewer two years later can't reconstruct *why* a rule
landed where it did, because the reasoning was never written down anywhere
but a sentence of prose.

**Proposed architecture: a two-layer model**, closely analogous to CVSS
(Common Vulnerability Scoring System) in security — the closest existing
industry precedent for "many independent reviewers must converge on the same
severity for a large, growing item count, using a documented deterministic
formula instead of judgment."

- **Layer 1 — Intrinsic Factor Vector.** Every rule is scored on ~10
  independently-defined, jurisdiction-neutral factors (§2), each on a
  documented ordinal scale with an explicit definition per level (not "use
  your judgment").
- **Layer 2 — Deterministic Aggregation.** A pure function maps the factor
  vector to one of the four tiers (§4). The four-tier label is *retained* as
  the public-facing projection (UI badges, `signature_readiness` gating,
  existing `ONE_WAY_RULE_IDS`/severity-keyed logic all keep working
  unmodified) — but it becomes a **computed, derived field**, never a
  directly-authored one. The factor vector, not the tier, is the actual
  source of truth and the audit trail.

This is a deliberate compromise, not a missed opportunity for something
"more pure": collapsing the whole system to a continuous score everywhere
would be more theoretically elegant but would break every existing
downstream consumer that keys off the four-tier enum for no additional
rigor — the rigor comes from *how* the tier is computed, not from exposing
a raw number in the UI.

---

## 2. Intrinsic factors

A factor is legitimate here iff it can be determined **from the clause's
text and general legal doctrine alone** — without reference to the specific
parties, the specific governing law, market/negotiation dynamics, or
probabilistic/actuarial estimation (this test is what separates §2 from §3).

Factors are grouped into three **harm tiers** used for weighting in §4.

### Tier A — Fundamental rights & personal harm (weight ×4)

| Factor | Scale | Definition |
|---|---|---|
| **PE** — Personal Exposure | 0–3 | Does liability/obligation extend to a natural person rather than staying with the contracting entity? 0 = entity only. 1 = personal exposure exists but is capped/conditional. 2 = personal exposure is substantial and largely unconditional. 3 = unconditional, uncapped personal liability (e.g. unlimited personal guaranty). |
| **RW** — Rights/Procedural Waiver | 0–3 | Does the clause waive a procedural or substantive legal right rather than merely allocate business risk? 0 = no waiver. 1 = waives a negotiable contractual protection (e.g. notice period). 2 = waives a significant statutory protection (e.g. a specific consumer-protection right). 3 = waives a fundamental due-process/procedural right (e.g. confession of judgment, waiver of right to a hearing). |
| **CR** — Criminal/Quasi-Criminal Exposure | 0–2 | Could the clause's operation, or the underlying non-compliance it governs, expose a party to criminal liability or license revocation? 0 = none. 1 = indirect/regulatory-adjacent (e.g. licensing-board exposure). 2 = direct criminal exposure. Acts as a ceiling factor (§4) — rare, but must exist. |

### Tier B — Structural financial & legal exposure (weight ×2)

| Factor | Scale | Definition |
|---|---|---|
| **FB** — Financial Boundedness | 0–3 | Is the financial exposure created by the clause bounded by its own terms? 0 = capped at a defined, modest amount. 1 = capped but at a large/uncertain multiple. 2 = cap exists but has broad carve-outs that functionally void it. 3 = facially unlimited (no cap stated). |
| **RS** — Regulatory/Statutory Exposure | 0–3 | Does the clause's operation, or a gap in it, expose a party to regulatory enforcement, fines, or loss of a required authorization (HIPAA, GDPR, securities, franchise-relationship statutes, etc.)? 0 = none. 3 = direct exposure to a specific, named regulatory regime. |
| **AT** — Asset/Ownership Transfer | 0–3 | Does the clause transfer *ownership* of an asset (IP, equity, real property, data) rather than merely license, limit, or condition its use? 0 = no transfer. 3 = unconditional, broad ownership transfer. |

### Tier C — Operational & temporal exposure (weight ×1)

| Factor | Scale | Definition |
|---|---|---|
| **REV** — Reversibility | 0–3 | If the harm occurs, can it be remedied (damages, specific performance, cure) or is it structural/irreversible (disclosed trade secret, executed release of unknown claims, entered judgment)? 0 = fully remediable. 3 = structurally irreversible. |
| **SC** — Scope of Affected Parties | 0–3 | Does the clause's failure mode affect only the signing counterparty, or reach third parties (consumers, employees, the public)? 0 = counterparty only. 3 = broad third-party/public exposure. |
| **OC** — Operational Continuity Impact | 0–2 | Does the clause remove access to a mission-critical asset/service/premises without a notice or cure window? 0 = notice/cure provided. 2 = no notice or cure required. |
| **DUR** — Duration/Persistence | 0–2 | Is the obligation/exposure time-bound, or perpetual/unbounded? 0 = defined, bounded term. 2 = perpetual or indefinite. |
| **MC** — Trigger Conditionality | 0–2 | Does the adverse effect operate automatically/unconditionally upon signature, or only upon a specific, discrete contingent event (default, breach)? 0 = requires a defined contingent event. 2 = automatic/unconditional on signature. This is a structural fact about the text ("is there a gate or not"), not a probability estimate — that distinction is what keeps it out of §3. |

10 factors total. This intentionally does *not* enumerate "IP ownership,"
"confidentiality," "data privacy," "litigation exposure," or "termination
risk" as separate top-level factors from the prompt's example list — each of
those is a **clause_category** (§5), not an intrinsic-severity factor; their
actual severity is produced by scoring *that instance* against PE/RW/FB/RS/
AT/REV/SC/OC/DUR/MC like any other clause. Keeping the factor count near 10
is deliberate: every additional factor is additional surface for reviewer
disagreement, and the goal is a rubric two people can apply identically, not
an exhaustive taxonomy.

---

## 3. Factors deliberately excluded

Each of these fails the litmus test in §2 — they depend on facts external to
the clause's text and doctrine:

| Excluded factor | Why |
|---|---|
| Likelihood of litigation / dispute frequency | Depends on the parties' actual future behavior and market conditions — not a property of the text. Two identical clauses in different deals have identical intrinsic severity but wildly different dispute likelihood. |
| Bargaining power | Extrinsic to the clause. The same clause is exactly as severe whether a large or small party signed it. |
| Ease of negotiation | A market/tactical fact, and circular — clauses are "hard to negotiate away" partly *because* the market already treats them as high-severity; using it as an input double-counts the conclusion as a cause. |
| Estimated dollar damages | Requires case-specific facts (contract value, actual counterparty facts) unknowable at rule-authoring time. **FB** (structural boundedness) is the correct intrinsic proxy — it asks "is there a cap," not "what will the cap cost." |
| Probability of enforcement | Depends on governing law and court behavior — this is exactly what the Applicability Layer (§6) exists to model separately. Folding it into intrinsic severity would re-couple the two things this architecture is designed to decouple. |
| Frequency of occurrence in real contracts | A prevalence/telemetry metric — useful for a *different* reporting surface ("how often does this show up"), but not a legal-risk fact about the clause itself. |
| Contract value / deal size | Extrinsic, per-document, not a property of the rule. |
| Counterparty sophistication/creditworthiness | Extrinsic. |
| Governing-law enforceability, statute of limitations | Explicitly modeled in the Jurisdiction layer (§6), never in intrinsic severity. |

---

## 4. Scoring model

### 4.1 Ceiling rules (evaluated first, in order — first match wins)

A pure weighted sum can "average away" a single catastrophic factor (a 3/3
on personal exposure diluted by four low scores elsewhere). Real risk
frameworks (and the existing engine's own `CRITICAL` tier definition)
already treat certain facts as automatically dispositive regardless of
anything else — this is made explicit and deterministic rather than left as
unwritten intuition:

```
1. CR >= 1                          -> CRITICAL
2. PE == 3                          -> CRITICAL
3. RW == 3                          -> CRITICAL
4. FB == 3 and PE >= 2              -> CRITICAL   (unbounded exposure reaching a person)
5. AT == 3 and REV == 3             -> HIGH        (irreversible unconditional ownership transfer)
```

If no ceiling rule fires, proceed to 4.2.

### 4.2 Weighted Aggregate Score (WAS)

```
WAS = Σ over all factors of (level_i × tier_weight)
  tier_weight = 4 for Tier A factors, 2 for Tier B, 1 for Tier C
```

Maximum possible WAS with the factor set in §2:
- Tier A: (3 + 3 + 2) × 4 = 32
- Tier B: (3 + 3 + 3) × 2 = 18
- Tier C: (3 + 3 + 2 + 2 + 2) × 1 = 12
- **Max WAS = 62**

### 4.3 Threshold table (initial hypothesis — see §9 for calibration)

| WAS range | % of max | Tier |
|---|---|---|
| Ceiling rule fired | — | CRITICAL (or HIGH per rule 5) |
| 43–62 | ≥70% | HIGH |
| 22–42 | 35–69% | MEDIUM |
| 0–21 | <35% | LOW |

These cut points are a **starting hypothesis, not a final answer** — §9
Phase 3 calibrates them empirically against the existing 117 rules re-scored
by an attorney reviewer, then freezes them as a versioned constant. Once
frozen, changing a threshold is a governed, reviewed change (§8.6 golden-set
regression), not an ad hoc edit.

### 4.4 Final severity

```
severity_tier = ceiling_result if a ceiling rule fired else band(WAS)
```

Fully deterministic: the same factor vector always produces the same tier,
by construction. `severity_derivation` (§5) records *which* rule produced
it, so the answer to "why is this CRITICAL" is always a one-line lookup, not
a re-litigation.

---

## 5. Rule metadata schema

```python
@dataclass(frozen=True)
class RuleMetadata:
    rule_id: str
    rule_version: str                 # semver of this rule's definition

    # --- Classification (controlled vocabularies, not free text) ---
    legal_domain: LegalDomain          # Lease | Loan | Employment | MSA | Franchise | ...
    clause_category: ClauseCategory    # Indemnification | LiabilityCap | IPAssignment |
                                        # Termination | RightsWaiver | ... — CROSS-CUTS
                                        # legal_domain (e.g. "Indemnification" appears in
                                        # MSAs, leases, and M&A alike). Severity correlates
                                        # with clause_category far more than with
                                        # legal_domain, which is why §8.2's consistency
                                        # check groups by this field, not by domain.
    affected_party_role: PartyRole     # Tenant | Guarantor | Employee | Buyer | Vendor |
                                        # Any | ContextDependent
    affected_asset: AssetType          # Money | IP | Data | RealProperty |
                                        # PersonalRights | Equity | OperationalContinuity

    # --- Intrinsic scoring (the actual source of truth) ---
    factor_vector: Dict[str, FactorScore]   # {"PE": FactorScore(level=3, justification="...")}
    severity_score: int                      # computed WAS
    severity_tier: Severity                  # computed, never hand-set
    severity_derivation: SeverityDerivation  # {method: "ceiling"|"band", rule_fired / band}

    # --- Detection (unchanged from today) ---
    detection: DetectionSpec           # pattern | anchors/nearby | topic/protective — as today

    # --- Applicability & jurisdiction (§6) ---
    prerequisite_facts: List[str]      # deterministic gates, e.g. "guarantor is a natural
                                        # person" — distinct from jurisdiction; these decide
                                        # whether the rule is IN SCOPE at all, not how
                                        # severe it is once in scope
    jurisdiction_profile: List[JurisdictionModifier]   # empty by default, §6

    # --- Explainability & governance ---
    rationale: str                     # human-readable explanation (exists today)
    references: List[str]              # statute sections, restatement cites, model-act
                                        # provisions — required for legal defensibility
    authored_by: str
    reviewed_by: str                   # licensed-attorney or domain reviewer sign-off, §7
    review_date: date

    # --- Compatibility ---
    legacy_severity: Optional[Severity]  # pre-migration severity, kept permanently (§9)
    schema_version: str                  # so old rule records can be forward-migrated
    aliases: List[str]                   # exists today
```

Design notes:

- `factor_vector` stores `{level, justification}` pairs, never bare
  integers — a level with no textual justification is a schema violation.
  This is what makes "two independent reviewers reach the same severity"
  checkable (§7, §8): the justification is what a second reviewer
  re-derives from, not the number.
- `clause_category` is deliberately separate from `legal_domain` so the
  consistency check in §8.2 can compare, e.g., every indemnification clause
  across every practice area on equal footing, rather than only within one
  domain's rules.
- `legacy_severity` is never deleted, even after migration — it's the
  permanent record of "what this rule used to be called, before the
  rearchitecture, and why it changed."
- `confidence` (evidentiary confidence that a *regex match* is real) already
  exists in the engine (`_score_confidence`) and is correctly **not** part
  of this schema — that's about match quality, this is about the underlying
  clause's severity. They must stay separate: a CRITICAL rule with a
  medium-confidence match is still CRITICAL if it fires; conflating the two
  would silently downgrade real risks because of an unrelated evidentiary
  question.

---

## 6. Jurisdiction architecture

Severity must stay jurisdiction-neutral (§2's litmus test already enforces
this at the factor level). Jurisdiction is modeled as a **separate,
optional overlay**, never as a second severity engine:

```
Rule
  │  (pattern/detection + factor_vector + rationale + clause_category)
  ▼
Intrinsic Severity                              <- §4, always computed,
  │  same for every document, any governing law     always shown
  ▼
Applicability Layer  (per-document, deterministic)
  - resolve the document's governing_law (extracted from a governing-law
    clause, or explicitly declared by the caller)
  - look up JurisdictionModifier for (clause_category, governing_law)
  - absence of an entry is a valid, common state: "no jurisdiction-specific
    data known" — NOT an error, and NOT treated as "not risky"
  ▼
Jurisdiction Modifier Table (separately maintained, versioned, keyed by
  (clause_category, jurisdiction) — never by rule_id, so one modifier entry
  covers every rule in that clause_category automatically)
  Each entry expresses ONLY one of a small closed set of effects — it can
  never re-derive severity from scratch, which is what keeps this table
  from becoming a second, ungoverned severity system:
    - enforceability: valid | void | voidable | restricted | unsettled
    - severity_adjustment: none | -1_tier | +1_tier   (bounded to ±1 band —
      a jurisdiction fact can nudge severity, never invert CRITICAL to LOW)
    - statutory_citation: str
    - note: str
  ▼
Final Finding
  - intrinsic_severity        (always present)
  - jurisdiction_adjusted_severity   (present only when governing_law is
    known; = intrinsic_severity + severity_adjustment, clamped to ±1 band)
  - enforceability_status     (surfaced distinctly — see example below)
  - jurisdiction_confidence: known | assumed | unknown
```

**Worked example — confession of judgment (`H_LOAN_CONFESSION_JUDGMENT_01`,
RW=3 → intrinsic CRITICAL via ceiling rule):**

- Governing law = Pennsylvania → modifier entry: `enforceability: valid`
  (PA permits cognovit notes for commercial debt) → Final Finding: CRITICAL,
  enforceable, "this is a live, currently-effective risk."
- Governing law = California → modifier entry: `enforceability: void` →
  Final Finding: CRITICAL (intrinsic severity is unchanged — the drafting is
  still bad), enforceability_status = void, with a note explaining the
  clause is unenforceable *as currently drafted* but that the underlying
  language should still be removed, particularly since the agreement could
  be reformed, assigned, or re-drafted under a different governing law.
- Governing law = unknown/not extracted → Final Finding: CRITICAL,
  jurisdiction_confidence = unknown, no enforceability claim made.

This is why the split matters: "is this bad drafting" and "does this
particular fact pattern currently bite" are different questions, and
conflating them (as a single jurisdiction-aware severity would) hides the
first question whenever the second one happens to be "no."

---

## 7. Mandatory rule-authoring workflow

This is the standard every future rule — #118 through #1000+ — must follow.
"Classify by analogy" is retired as an instruction entirely.

1. **Clause identification.** Assign `clause_category` from the controlled
   taxonomy. If none fits, that's a separate taxonomy-governance PR first —
   categories are never invented ad hoc inside a rule PR.
2. **Factor scoring.** For each of the 10 factors in §2, select a level and
   write a 1–2 sentence justification tied to the clause language. The
   schema rejects a bare integer with no justification.
3. **Automated score computation.** The contributor runs the scoring
   function (§4) — a pure, unit-tested function of the factor vector. The
   contributor **never hand-picks** the tier; it is derived, full stop.
4. **Derivation record auto-generated** (`severity_derivation`) for the
   audit trail.
5. **Detection pattern authoring.** Unchanged from current practice:
   pattern/anchors/topic/protective regex, tolerant of messy
   whitespace/line-wraps (the existing `\s+`/bounded-DOTALL discipline),
   with a positive match test, a negative/near-miss test, and a
   deliberately-mangled-formatting test.
6. **Prerequisite facts & jurisdiction stub.** Declare `prerequisite_facts`.
   Leave `jurisdiction_profile` empty unless the contributor has a sourced
   citation — no speculative jurisdiction claims.
7. **Blind re-score gate.** A second contributor, given only the rule's
   `rationale` and clause text (not the first contributor's factor vector),
   independently scores the same 10 factors. If their computed tier
   diverges from the original, the PR is blocked until the *factor
   definitions* are reconciled — never until someone just picks a tier by
   fiat. This is the literal operationalization of "two independent
   reviewers reach the same severity."
8. **Subject-matter/legal sign-off.** `reviewed_by` must be a reviewer with
   familiarity in that `clause_category`/`legal_domain`; recorded on the
   rule permanently.
9. **Automated validation suite passes** (§8).
10. **Documentation generated, not hand-written.** The rule reference doc
    and changelog entries are generated from the metadata store at build
    time. (The current hand-maintained `all_rules.md`, already stale at 117
    rules, is exactly the failure mode this eliminates — it does not scale
    to 1,000 rules as prose.)

---

## 8. Validation rules (CI-enforced, every rule change)

1. **Recomputation check.** Stored `severity_tier` must exactly equal
   `compute_severity(factor_vector)`; build fails otherwise. (Structurally,
   `severity_tier` should be a generated/read-only field, not a settable
   one — this check is the backstop if that's ever bypassed.)
2. **Cross-rule monotonicity check within `clause_category`.** For any two
   rules A, B sharing a `clause_category`: if every factor level in A is
   ≥ the corresponding level in B (with at least one strictly greater),
   then `severity(A)` must be ≥ `severity(B)`. This is the automatic,
   whole-rulebase version of "why is this HIGH when a strictly worse clause
   is MEDIUM" — it catches the inconsistency at PR time instead of relying
   on someone reading all 1,000 rules.
3. **Duplicate/near-duplicate detection.** Token- or embedding-similarity
   clustering over `rationale` + detection pattern flags candidate
   duplicates for human triage before merge, preventing silent
   proliferation of near-identical rules with divergent severities.
4. **Ceiling-coverage keyword check.** A maintained keyword list (e.g.
   "personal," "confession of judgment," "criminal," "unlimited") scanned
   against `rationale`; if present but the corresponding ceiling factor
   (§4.1) wasn't triggered, flag for manual review. A lightweight
   under-scoring catch, not a substitute for §7.7.
5. **Schema validation.** Required fields present; factor levels within
   documented bounds; every factor has a non-empty justification;
   `clause_category` in the controlled taxonomy; any `jurisdiction_profile`
   entries carry a real citation.
6. **Golden-set regression.** A frozen set of attorney-confirmed
   `(factor_vector → tier)` examples (seeded from the §9 calibration pass)
   must still score correctly after any change to the scoring function or
   thresholds. Any tier flip in the golden set requires explicit sign-off —
   this is what prevents silent rubric drift over years of maintenance.
7. **Detection-pattern test-coverage lint.** Every `rule_id` must map to at
   least one positive, one negative, and one messy-formatting test
   function (extending the discipline already used for the v6.0 rules
   added this session).

---

## 9. Migration strategy for the existing 117 rules

**Phase 0 — Freeze & snapshot.** Tag the current ruleset
`v6.0.0-legacy-severity`. Copy each rule's current `severity` into a new
`legacy_severity` field, kept permanently.

**Phase 1 — Additive schema introduction.** Add the §5 metadata fields to
`Rule` as optional/nullable. `analyze()` output is unchanged; `severity`
remains authoritative. Zero behavioral risk — pure additive migration.

**Phase 2 — Retroactive factor scoring.** For each of the 117 rules, run
the §7 workflow (contributor + attorney reviewer) to populate
`factor_vector` and compute `computed_severity`, stored alongside — but not
replacing — the legacy `severity`.

**Phase 3 — Calibration.** Diff `computed_severity` against legacy
`severity` for all 117 rules. Every mismatch gets root-caused: either the
legacy analogy-based severity was simply wrong (the expected, common case —
this is the whole point of the rearchitecture), or the §4.3 thresholds need
adjusting. Iterate the threshold table until remaining mismatches are all
individually justified, then **freeze** the thresholds as a versioned
constant and seed the §8.6 golden set from this pass.

**Phase 4 — Shadow mode.** Ship `computed_severity` as a secondary,
clearly-labeled field for one release cycle. Re-run all existing behavior
that keys off `severity` today — `overall_risk` aggregation,
`signature_readiness` gating, `ONE_WAY_RULE_IDS` handling — against
`computed_severity` in test-only mode to confirm no unexpected downstream
break before anything user-facing changes.

**Phase 5 — Cutover.** `severity` becomes a generated property
(`severity = tier_of(computed_severity)`); direct hand-setting is removed.
`legacy_severity` stays on every rule permanently as the historical record.

**Phase 6 — Enforcement.** Turn on the §8 validation suite as a hard CI
gate for all new rules; publish this document as the CONTRIBUTING standard;
remove "classify by analogy" from any remaining docs/prompts.

**Rollback:** every phase through Phase 4 is purely additive/reversible.
Phase 5's cutover is a one-line revert (repoint `severity` back to
`legacy_severity`) if regression testing surfaces a problem, since nothing
is deleted. Full existing regression suite (261+ tests today) plus the new
golden-set tests must pass at every phase boundary.

---

## 10. Comparison: analogy-based vs. factor-vector architecture

| Dimension | Analogy-based (current) | Factor-vector + ceiling/band (proposed) |
|---|---|---|
| Consistency | Degrades as rule count grows; no structural guarantee | Enforced structurally (§8.2 monotonicity check); scales flat with rule count |
| Determinism | Depends on which "similar" rule a reviewer recalls | Pure function of a documented, versioned factor vector |
| Auditability | "Looked like Rule X" is not a legal justification | Every tier traces to specific factor levels + justification text + derivation record |
| Reproducibility | Two reviewers may diverge | Two reviewers converge by construction (§7.7 blind re-score gate) |
| Maintainability | Hand-written changelog/doc tables already stale at 117 rules | Metadata-generated docs/changelog; one scoring function to maintain instead of N ad hoc judgments |
| Extensibility | Every new practice area re-derives intuition from scratch | New `clause_category` scored once against the same 10 factors; jurisdiction handled orthogonally |
| Legal defensibility | Not defensible in a client-facing or dispute context | Resembles an actual legal risk memo: magnitude, rights waived, reversibility, regulatory exposure |
| Implementation complexity | Low upfront, rising hidden cost per rule | Higher upfront (rubric design + retroactive scoring of 117 rules); flat marginal cost thereafter |
| Contributor onboarding | Fast start, inconsistent output without tribal knowledge | Slower first rule; then mechanical and machine-checkable |
| Long-term scalability (500–1,000+) | Breaks down — no one holds 1,000 rules' relative severity in their head | Designed for exactly this — the entire point is replacing that mental model with a checkable function |

---

## Open question worth surfacing, not resolving here

The four-tier label currently serves two different downstream consumers at
once: human risk communication (a simple badge) and automated decisioning
(`signature_readiness` gating keys off `severity` directly today). Those two
consumers may eventually want different scales — a human badge benefits from
staying at four tiers forever, while automated gating could use the raw WAS
score for finer-grained decisions. This document deliberately does **not**
resolve that now: preserving the four-tier projection as the stable public
contract while making the factor vector the real source of truth gets all
the rigor benefits without a breaking change to existing consumers. If
`signature_readiness` logic outgrows four tiers later, that's a scoped
follow-up against `severity_score` directly — not a reason to delay this
migration.
