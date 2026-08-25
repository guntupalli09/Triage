# ROOT_CAUSE_MAP — Candidate 2 remediation

Six observed failures against frozen Candidate 1
(`f94c4c319f828c4e0072af9305d409a03964d237`). Determined to be **four
distinct root causes**, two of which are genuinely shared across
adapters (confirmed by direct code inspection, not assumed).

---

## 1. CONFIDENTIALITY — false safe (asymmetric obligations)

**OBSERVED FAILURE**: two directional confidentiality obligations
("Vendor shall protect... for five years", "Customer shall protect...
indefinitely") stated as separate sentences reached ACCEPT despite
`require_mutual_confidentiality=True`.

**ROOT CAUSE (two, compounding)**:
1. `_resolve_obligations_for_side()` resolves `exposure` and
   `protection` as two INDEPENDENT `ConfidentialityObligation` objects
   when the document uses two separate directional sentences (rather
   than one "each party..." mutual opener), and `evaluate_
   confidentiality_policy()` never compared their terms — only checked
   whether `protection` existed at all, not whether its terms matched
   `exposure`'s.
2. Masking defect found while fixing #1: the per-obligation
   classification window (`text[m.start():m.start()+1200]`) was wide
   enough to swallow a SECOND obligation's own duration/care language,
   making both obligations misclassify as identical (both "perpetual"),
   which would have hidden the very asymmetry #1's fix exists to catch.

**SHARED PRIMITIVE INVOLVED**: `policy_engine_core.detect_role_
attributed_asymmetry` — but this primitive was never actually the
problem; it was simply never CALLED for the two-separate-obligations
case, only for the single-mutual-opener case
(`_detect_confidentiality_asymmetry`, itself adapter-owned).

**ADAPTER-SPECIFIC CODE INVOLVED**:
`confidentiality_policy_engine._resolve_obligations_for_side`,
`evaluate_confidentiality_policy`, the per-obligation window
construction in `extract_confidentiality_facts`.

**CORRECT ARCHITECTURAL FIX**: compare `exposure` and `protection`
directly (using their own already-parsed fields, not a re-derived text
snapshot) whenever both resolve and `require_mutual_confidentiality` is
set, reusing the existing `_compare_confidentiality_attribution`
function. Separately, bound every obligation's classification window at
the next obligation's own anchor position, not just a fixed character
cap.

**RISK OF REGRESSION**: low — both changes are additive gates (a new
`elif` branch; a tighter, not wider, window). Verified against all 12
existing confidentiality tests plus 2 new ones.

**OTHER ADAPTERS EXPOSED TO SAME ROOT CAUSE**: `termination`,
`ip_ownership`, `insurance`, `assignment` all use the identical
"directed obligation, possibly reciprocal, resolved into two named
sides" shape (confirmed by code reading — each independently
implements the same exposure/protection or restriction-pair pattern).
**Not verified whether they have the identical asymmetry-comparison
gap** — this was investigated only for confidentiality given time
budget. Named as a follow-up in `CANDIDATE2_REPORT.md`, not silently
assumed safe.

---

## 2. DATA SECURITY — false safe (time normalization)

**OBSERVED FAILURE**: a 30-day breach-notification commitment was
invisible to a 72-hour policy maximum (extractor only recognized
hour-denominated phrasing), reaching ACCEPT with no comparable fact
established at all.

**ROOT CAUSE**: `_BREACH_HOURS_RE` had no day-denominated counterpart,
and no spelled-out-number support either.

**SHARED PRIMITIVE INVOLVED**: `policy_engine_core.word_number_
alternation`/`parse_multiplier_token` (already used elsewhere in this
codebase for duration/multiplier parsing) — was available but never
imported/used by this specific regex.

**ADAPTER-SPECIFIC CODE INVOLVED**:
`data_security_policy_engine._classify_breach_notification`,
`_BREACH_HOURS_RE`.

**CORRECT ARCHITECTURAL FIX**: add a calendar-day pattern, canonicalize
to hours (× 24) into the SAME comparable value set the hour pattern
populates; add a SEPARATE business-day pattern that is deliberately
NEVER canonicalized (a business day's wall-clock length is
recipient-calendar-dependent — converting it would manufacture false
precision) and instead forces `REQUIRES_REVIEW`; use the shared
word-number vocabulary for both, not just digits.

**RISK OF REGRESSION**: low — purely additive regex alternatives and
value-set population; the existing hour-only behavior for hour-phrased
text is unchanged.

**OTHER ADAPTERS EXPOSED TO SAME ROOT CAUSE**: any adapter comparing a
policy threshold against a document-stated time period is potentially
exposed to the same day/hour (or day/business-day) confusion.
`termination` (notice/cure periods, stated in days already — no hours
comparison exists there, so N/A), `sla` (response/restoration hours per
severity tier — uses hours already, but was not checked for a
day-phrased variant), `insurance` (cancellation notice days). **Not
audited for the identical gap** given time budget — named as a
follow-up.

---

## 3. DATA SECURITY — false safe (negated obligation)

**OBSERVED FAILURE**: "Vendor shall have no obligation to notify
Customer of any personal data breach..." reached ACCEPT — identical
treatment to the obligation simply never being mentioned.

**ROOT CAUSE (two, compounding)**:
1. No negation-detection regex existed for this dimension at all
   (unlike `warranties_policy_engine._CATEGORY_NEGATION_RE`, which
   exists specifically for this class of defect in that adapter).
2. Masking defect found while fixing #1: even after adding the
   negation regex, the anchor-forward classification window (which
   starts AT the anchor match, e.g. "personal data breach...") discards
   any negation verb phrase that PRECEDES the anchor in natural
   sentence order ("Vendor shall have no obligation to notify Customer
   of any personal data breach") — invisible to the classifier for a
   structural reason, not just a missing pattern.

**SHARED PRIMITIVE INVOLVED**: none directly reused (warranties' own
`_CATEGORY_NEGATION_RE` is adapter-local, tied to its own per-category
noun-phrase dict — not a generic primitive that could be imported
as-is). The POLARITY CONCEPT is shared (see "Other adapters" below),
but no shared code existed to fix in one place.

**ADAPTER-SPECIFIC CODE INVOLVED**:
`data_security_policy_engine._classify_breach_notification`, the
windows-loop in `extract_data_security_facts`,
`evaluate_data_security_policy`.

**CORRECT ARCHITECTURAL FIX**: a generalized negation-verb-phrase
regex (multiple phrasings, not the one failed sentence), checked
against a backward-widened scan window; a new
`breach_notification_explicitly_disclaimed` fact, distinct from "not
addressed"; a MUST_REDLINE-severity check in the evaluator whenever
policy expects a notification commitment to exist.

**RISK OF REGRESSION**: low — new field, new branch, existing
hours/conflict logic untouched.

**OTHER ADAPTERS EXPOSED TO SAME ROOT CAUSE — genuinely investigated**:
This is the most important shared-cause question in this remediation.
Checked every adapter for an existing negation mechanism:
- `warranties_policy_engine._CATEGORY_NEGATION_RE`: **has** one.
- `data_security_policy_engine`: **now has** one (this fix), scoped to
  breach notification only — its OTHER binary dimensions (audit rights,
  cooperation obligation, confidentiality-of-personal-data,
  deletion-or-return) have **no** equivalent negation check and are
  **not fixed this pass** — named as a concrete follow-up.
- `liability_policy_engine`, `indemnification_policy_engine`,
  `payment_terms_policy_engine`: each has its own `_core_detect_
  condition_in_span`-family deterministic condition/negation-shaped
  detection (different code, same underlying concern), already
  proven in prior sessions' adversarial tests.
- `confidentiality`, `termination`, `governing_law`, `ip_ownership`,
  `insurance`, `sla`, `assignment`: **not individually audited for a
  general negated-obligation blind spot** this pass, beyond the
  specific dimensions already covered by their own existing
  `ai_identified_condition`/`ai_identified_exception` composition
  (which only helps when semantic discovery is enabled and a provider
  is reachable — the DETERMINISTIC path for an explicit negation in
  these adapters has not been swept). Named as the single highest-value
  follow-up item for a future session, not silently assumed fine.

---

## 4/5. INSURANCE and SLA — false operative → clean (descriptive/background language)

**OBSERVED FAILURE**: "It is common practice for a services vendor to
carry Commercial General Liability insurance, though the specific
coverage requirements ... remain to be negotiated" (insurance) and "SaaS
agreements typically commit to 99.9% uptime ... although the parties
have not yet negotiated specific service levels" (sla) were both
extracted as established, operative commitments.

**ROOT CAUSE (confirmed shared, not two coincidentally-identical
adapter-local bugs)**: `policy_engine_core.is_operative_context()` is
an EXISTING shared primitive built specifically to reject descriptive/
hypothetical/quoted/meta-instructional text before a structuring regex
match is trusted. A repo-wide check
(`grep -c is_operative_context *.py`) found it is called by only 3 of
12 adapters: `liability_policy_engine` (5 call sites), `indemnification_
policy_engine` (8 call sites), `payment_terms_policy_engine` (4 call
sites). The other 9 — `confidentiality`, `ip_ownership`, `insurance`,
`data_security`, `governing_law`, `termination`, `warranties`, `sla`,
`assignment` — **never call it at all**, and are therefore ALL
structurally exposed to some version of this exact failure mode,
whether or not this session's 74-case corpus happened to trigger it in
each of them.

A SECOND, deeper layer: even after wiring insurance/sla onto the shared
primitive, both failing sentences STILL passed through, because none
of `is_operative_context`'s existing structural cue families
(`_DESCRIPTIVE_ABOUT_CLAUSE_RE`, `_RECITAL_INTENT_RE`,
`_NEGATED_OR_REJECTED_MATERIAL_RE`, `_META_INSTRUCTIONAL_RE`) covers
"industry-norm descriptive framing" ("it is common practice...",
"typically commit to...") combined with an explicit "not yet
agreed"/"remains to be negotiated" disclaimer. This is a genuine gap IN
THE SHARED PRIMITIVE ITSELF, not just a wiring gap.

**SHARED PRIMITIVE INVOLVED**: `policy_engine_core.is_operative_
context()` — both the wiring gap (9 adapters never call it) and the
content gap (missing structural cue family) live here.

**ADAPTER-SPECIFIC CODE INVOLVED**:
`insurance_policy_engine`'s coverage-type mention loop (`extract_
insurance_facts`), `sla_policy_engine`'s uptime and service-credit
detection loops (`extract_sla_facts`).

**CORRECT ARCHITECTURAL FIX**: (a) add `_INDUSTRY_NORM_DESCRIPTIVE_RE`
+ `_NOT_YET_AGREED_RE` to `policy_engine_core.py`, checked together
(BOTH signals required) inside `is_operative_context()`, so every
current and future caller benefits from one fix; (b) wire `insurance`
and `sla`'s establishing-fact loops onto `is_operative_context`, exactly
mirroring how liability/indemnification/payment_terms already gate
their own structuring matches.

Requiring BOTH signals (not either alone) is a deliberate precision/
recall tradeoff: an industry-context lead-in sentence that precedes a
genuinely operative clause ("It is common practice to require CGL
insurance. Vendor shall maintain CGL with a $2M limit.") must NOT be
suppressed just because it mentions common practice — only the
combination with an explicit "not yet agreed" disclaimer is a reliable
non-operative signal.

**RISK OF REGRESSION**: medium-low. `is_operative_context` is used by 3
existing adapters with real regression suites (liability,
indemnification, payment_terms) — the new check requires BOTH new
signals to fire, so it cannot suppress any match that doesn't also
contain explicit "not yet agreed" language, which no known passing test
case in those 3 adapters' suites contains. Verified: full regression
after this change shows zero new failures across all 12 adapters plus
the shared framework.

**OTHER ADAPTERS EXPOSED TO SAME ROOT CAUSE**: `confidentiality`,
`ip_ownership`, `data_security`, `governing_law`, `termination`,
`warranties`, `assignment` — the 7 remaining adapters that still never
call `is_operative_context`. **NOT wired this pass** given time budget;
each remains exposed to the same class of false-operative defect this
report just confirmed twice. This is the single most important
follow-up item from this entire remediation — see
`CANDIDATE2_REPORT.md`.

---

## 6. INDEMNIFICATION — material context silent loss (cross-section backward reference)

**OBSERVED FAILURE**: a time-bar qualifier stated in a separate,
later section ("Notwithstanding Section 12, Vendor's indemnification
obligation applies only to claims filed within ninety days...") never
surfaced anywhere in the decision.

**ROOT CAUSE**: `policy_engine_core.detect_conflicting_backward_
conditions()` — the ONLY existing mechanism for cross-section
backward-reference detection in this codebase — is deliberately scoped
to CONFLICTS between 2+ such references (`if len(matches) < 2: return
None`). It was never designed to surface a single, unopposed
qualifier at all; that was simply out of scope for what it was built
to do. Separately, its regex vocabulary required the section reference
to PRECEDE the qualifying language ("the indemnification obligation
under Section 12 ... shall apply only..."), and did not cover the
extremely common inverted "Notwithstanding Section 12, ..." construct.

**SHARED PRIMITIVE INVOLVED**: `policy_engine_core.detect_conflicting_
backward_conditions` and its regex, `_BACKWARD_CONDITION_ON_SECTION_RE`.

**ADAPTER-SPECIFIC CODE INVOLVED**:
`indemnification_policy_engine.extract_indemnification_facts`'s
per-obligation backward-reference check.

**CORRECT ARCHITECTURAL FIX**: added `detect_backward_referenced_
qualifier()` ALONGSIDE (not replacing) the existing function —
`liability_policy_engine` and `payment_terms_policy_engine` both call
the ORIGINAL function and depend on its exact "only fires on conflict"
contract, so it was not safe to change its behavior in place. The new
function fires on the FIRST qualifying reference found (ESTABLISHED,
forcing review) or on 2+ conflicting ones (CONFLICTING, identical logic
to the original), and recognizes both the original "Section N ...
shall apply only" surface form and the new "Notwithstanding Section
N, ..." form.

**RISK OF REGRESSION**: low — a new function, wired only into
indemnification; the original function and its two other callers are
byte-unchanged.

**OTHER ADAPTERS EXPOSED TO SAME ROOT CAUSE**: `liability_policy_
engine` and `payment_terms_policy_engine` both call the ORIGINAL
conflict-only function for their own cap/payment-term backward
references, and are therefore exposed to the identical "single
unopposed qualifier silently discarded" gap. **NOT migrated to the new
generalized function this pass** — doing so safely requires
re-verifying each adapter's own adversarial suite against the wider
match set (a single qualifying reference now becomes ESTABLISHED
instead of invisible, which could change existing test expectations in
ways that need per-adapter review, not a blanket swap). Named as a
concrete, scoped follow-up in `CANDIDATE2_REPORT.md`.

---

## Summary: 6 observed failures, 4 root causes, 2 confirmed shared

| # | Failure | Root cause bucket | Shared? |
|---|---|---|---|
| 1 | Confidentiality asymmetry | (A) two-separate-obligations comparison never wired + window bleed | Adapter-local (siblings exposed, unverified) |
| 2 | Data security time units | (B) missing day/business-day support | Adapter-local (siblings unaudited) |
| 3 | Data security negation | (C) missing negation detector + window direction | Adapter-local (siblings unaudited) |
| 4 | Insurance false-operative | (D) `is_operative_context` not wired + primitive gap | **Confirmed shared** (9/12 adapters never call the primitive) |
| 5 | SLA false-operative | (D) same as #4 | **Confirmed shared** — same root cause as #4, not independent |
| 6 | Indemnification silent loss | (E) backward-reference detector conflict-only scope | Adapter-local fix; siblings (liability, payment_terms) confirmed exposed, not migrated |

Defects 4 and 5 are **the same root cause**, not two — this report
does not double-count them. The single highest-leverage remaining risk
identified by this analysis is root cause (D): 7 of 12 adapters remain
unwired to `is_operative_context` after this pass.
