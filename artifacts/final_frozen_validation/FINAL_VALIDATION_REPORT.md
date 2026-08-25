FROZEN COMMIT: f94c4c319f828c4e0072af9305d409a03964d237
CORPUS HASH: dcf7c43c698c1857c202a692a4d3f86595399a3ff07d61584a08e6a957488d8c
TOTAL CASES: 74 (7-8/adapter for liability/indemnification/confidentiality, 5-6/adapter for the other 9 — see "Scope reduction" below; the mission asked for ≥600)

FALSE SAFE: **3 confirmed** (confidentiality-06, data_security-02, data_security-05)
UNVERIFIED→CLEAN: 0 observed in this deterministic-only run (AI layer not exercised — see blocker below)
FALSE OPERATIVE→CLEAN: **2 confirmed** (insurance-04, sla-04)
FALSE ABSENCE: 0 confirmed
MATERIAL CONTEXT SILENTLY LOST: **1 confirmed** (indemnification-07 — masked by an unrelated MUST_REDLINE, so it did not independently reach CLEAN, but the qualifier itself never surfaced anywhere in the decision)
ARBITRARY COMPETING READING: 0 confirmed
PROVIDER FAILURE→CLEAN: not applicable this run (provider not invoked — see blocker below)
GROUNDING FAILURE→CLEAN: not applicable this run (same reason)
WRONG PARTY→CLEAN: 0 confirmed (1 candidate, indemnification-06, investigated and reclassified as a corpus/ground-truth defect, not a system defect — see below)
DETERMINISM: **100%** (74/74 cases — repeat deterministic evaluation of the same admitted facts produced byte-identical decisions every time)

LIABILITY: 7 cases, 0 confirmed gate violations, 4 mismatches attributed to corpus/ground-truth calibration (see per-adapter section) — **PASS** (no violation) but recall gaps noted
INDEMNIFICATION: 7 cases, 0 confirmed gate violations, 1 confirmed silent-context-loss instance (masked, non-clean outcome), 2 other mismatches reclassified as corpus defects — **PASS** (no CLEAN-reaching violation) with a residual-risk finding
CONFIDENTIALITY: 7 cases, **1 confirmed FALSE_SAFE** (asymmetric-obligations case reached CLEAN) — **FAIL**
PAYMENT TERMS: 6 cases, 0 confirmed gate violations, 4 mismatches all traced to one recall gap (day-count phrasing not parsed) — **PASS** (fails safe, not clean) with a recall-gap finding
IP OWNERSHIP: 6 cases, **2 confirmed FALSE_OPERATIVE→CLEAN-shaped defects** (descriptive and explicitly-negated text both reached CLEAN with zero structured ownership fact) — **FAIL**
INSURANCE: 6 cases, **1 confirmed FALSE_OPERATIVE→CLEAN** (descriptive "remains to be negotiated" text extracted as `established=True`) — **FAIL**
DATA SECURITY: 6 cases, **2 confirmed FALSE_SAFE** (30-day notice and explicit negation both reached CLEAN) — **FAIL**
GOVERNING LAW: 5 cases, 0 confirmed gate violations, 2 mismatches (both fail safe to REQUIRES_REVIEW/NOT_APPLICABLE rather than CLEAN) — **PASS**
TERMINATION: 6 cases, 0 confirmed gate violations, 3 mismatches all fail safe (NOT_CLEAN/REQUIRES_REVIEW) — **PASS** with a recall-gap finding
WARRANTIES: 6 cases, 0 confirmed gate violations, 4 mismatches all fail safe or are corpus defects — **PASS**
SLA: 6 cases, **1 confirmed FALSE_OPERATIVE→CLEAN** (descriptive "have not yet negotiated" text extracted as an established 99.9% uptime commitment) — **FAIL**
ASSIGNMENT: 6 cases, 0 confirmed gate violations after investigation, 3 mismatches reclassified as corpus defects — **PASS**

LEE QUESTIONS:
Q1: PARTIAL — see Phase 7 below
Q2: PARTIAL
Q3: PARTIAL
Q4: PROVEN (for the dimensions this corpus could exercise)
Q5: DISPROVEN (AI cannot acquire authority — architecturally enforced) but NOT PROVABLE end-to-end this session (provider unreachable)
Q6: NOT PROVABLE this session (interaction engine untested — see Phase 1/6)
Q7: PARTIAL (confidentiality asymmetry gap found)
Q8: DISPROVEN for the AI-sourced path (proven in prior sessions' unit tests); PARTIAL for the deterministic-only path (this session found real gaps)
Q9: DISPROVEN — yes, in `shadow`/`legacy` mode by design (see Phase 0 in EXECUTABLE_ARCHITECTURE.md)
Q10: NOT PROVABLE this session (not exercised)
Q11: PROVEN — six concrete, reproducible mechanisms identified below

FINAL VALIDATION VERDICT: **FAIL**
SHIP: **NOT AUTHORIZED**

---

## 0. How to read this report

This report distinguishes IMPLEMENTED / WIRED / UNIT-TESTED /
CORPUS-PROVEN / LIVE-PROVEN throughout, per this mission's explicit
instruction. See `EXECUTABLE_ARCHITECTURE.md` for the full trace. The
short version: **the fact-admission architecture validated across prior
sessions is not what decided any of the results below.** With
`ANTHROPIC_API_KEY` unavailable (confirmed in `FREEZE_MANIFEST.md`), the
semantic/AI-contextual-discovery layer never ran for any case in this
corpus — by design, since it requires the provider and defaults to off
regardless. **Every result below comes from the deterministic backbone
alone** — the same regex/structural extraction and the same
`evaluate_*_policy` functions that would run whether or not the AI layer
is ever reached. This is a legitimate and important thing to validate
(it is what's authoritative in `shadow`/`legacy` mode today, and it is
the gate every AI-sourced candidate must still pass even in `cutover`
mode), but it is **not** a validation of the definition/cross-reference/
competing-reading/reconciliation work from prior sessions, which
requires the provider.

## 1. VALIDATION BLOCKER (declared, not worked around)

**No `ANTHROPIC_API_KEY` is available in this environment.** Per this
mission's explicit instruction ("Do not fabricate provider calls if
credentials/budget are unavailable... Do NOT substitute mocks and call
the final corpus passed"), the AI-contextual-discovery/verification
dimension of the architecture is **VALIDATION BLOCKED** in this session.
This corpus and this report do not claim otherwise anywhere. The
following remain **UNIT-TESTED but NOT CORPUS-PROVEN and NOT
LIVE-PROVEN** as of this report:
- Definition/cross-reference/competing-reading resolution
- Indemnification's reconciliation channel
- Provider-timeout/malformed-output/unverifiable-evidence behavior
- Any case in the mission's adversarial category list that requires the
  AI layer at all (Q, R, S, T, U, W, X in the strict "AI notices what
  regex misses" sense, AE-AL)

## 2. Scope reduction (declared, not hidden)

The mission asked for ≥600 fresh cases (≥50/adapter). This session
produced and ran **74** fresh, hand-authored cases (5-8/adapter),
written with ground truth BEFORE execution, hashed and frozen before
running (`CORPUS_MANIFEST.json`, corpus SHA-256 above), and run exactly
once with no changes to expected answers after seeing results. This is
a real, smaller-than-requested corpus, not a placeholder — every case
was actually executed and every result below is real. Given this
mission's own Absolute Rule #1 (freeze before results, no fixing
production code afterward) and Rule #2 (freeze the corpus before
running), a full 600-case corpus authored to the same standard of
adversarial care as these 74 was not achievable in this session's time
budget without either rushing case quality (risking exactly the kind of
sloppy ground truth this mission warns against) or exceeding the
session. **The five confirmed defects below were found with only 74
cases** — a strong signal that a genuinely larger, independent corpus
would find more, not fewer.

## 3. Confirmed safety-gate violations (verified by direct code
inspection of the extracted facts object, not just the final decision)

### 3.1 CONFIDENTIALITY — FALSE SAFE (`confidentiality-06`)

**Text**: "Vendor shall protect Customer's Confidential Information for
five years using reasonable care. Customer shall protect Vendor's
Confidential Information indefinitely using the highest degree of care
available in the industry." (`require_mutual_confidentiality=True`)

**Result**: `ACCEPT` ("No policy gaps found").

**Mechanism**: `confidentiality_policy_engine._detect_confidentiality_asymmetry()`
is scoped to ONE drafting pattern — a single "each party..." MUTUAL
opener with differing per-party carve-outs inside it. This case states
the same legal risk (materially different duration/care-standard terms
per direction) as **two separately-phrased directional obligations**
instead. Because the text never uses a mutual opener, the asymmetry
detector never runs at all; the two directional obligations are
resolved independently and neither individually looks non-compliant, so
`evaluate_confidentiality_policy` reaches a clean ACCEPT despite the
same underlying asymmetric-terms risk `require_mutual_confidentiality`
exists to catch.

**Residual risk**: any two-sided confidentiality clause phrased as
separate sentences per party (extremely common drafting, arguably more
common than the single-mutual-opener form) bypasses asymmetry detection
entirely.

### 3.2 DATA SECURITY — FALSE SAFE ×2 (`data_security-02`, `data_security-05`)

**data_security-02 text**: "Vendor shall notify Customer of any data
breach affecting personal data within thirty days of becoming aware of
it." (`max_breach_notification_hours=72`)

**Result**: `ACCEPT` ("No policy gaps found").

**Mechanism**: confirmed by direct extraction — `extract_data_security_facts()`
returns `breach_notification_hours=None`. The deterministic notification-
period extractor only recognizes HOUR-denominated phrasing; a
DAY-denominated commitment ("thirty days") — which is a full 17x slower
than the 72-hour policy maximum and should be a clear violation — is
never parsed into a comparable figure at all, so the "no timeframe found"
path is taken and nothing flags it.

**data_security-05 text**: "Vendor shall have no obligation to notify
Customer of any personal data breach under this Agreement." (same
policy)

**Result**: `ACCEPT`.

**Mechanism**: confirmed by direct extraction — `clause_found=True`,
`breach_notification_hours=None`. An EXPLICIT, confidently-stated
negation of a policy-required obligation is treated identically to
"nothing found to evaluate," reaching the same clean ACCEPT as a
document that never mentions breach notification at all — this is the
opposite of `warranties_policy_engine`'s own documented
`_CATEGORY_NEGATION_RE` handling (which this session's own prior work
confirmed exists specifically to catch "Vendor makes no warranty..." as
a confidently-observed non-compliant gap, NOT an absence) — data_security
has no equivalent mechanism for its own negated-obligation case.

### 3.3 IP OWNERSHIP — FALSE-OPERATIVE-SHAPED DEFECT ×2 (`ip_ownership-04`, `ip_ownership-06`)

**ip_ownership-04 text**: "Background. In consulting arrangements, it
is typical for the customer to own work product created specifically
for it, although the parties have not addressed IP ownership in this
Agreement yet." (all policy requirements off)

**ip_ownership-06 text**: "This Agreement does not address ownership of
any intellectual property created during the engagement." (same policy)

**Result (both)**: `ACCEPT` ("No policy gaps found").

**Mechanism**: confirmed by direct extraction — BOTH cases produce
`clause_found=True` (the anchor regex fires on "work product"/"IP
ownership" appearing anywhere, including inside descriptive or
explicitly-negating prose) with **`ownership_attributions={}`** — a
completely empty ownership structure, zero facts established. Unlike
confidentiality/termination/assignment (which each have an explicit "if
not obligations: REQUIRES_REVIEW" branch for exactly this "anchor fired,
nothing structured" case) or warranties/sla (which have the
`found_anything` negative-control gate that returns `None`/
`NOT_APPLICABLE`), `ip_ownership_policy_engine.evaluate_ip_policy()` has
**no equivalent gate**: with every policy requirement left at its
default `False`, "no ownership fact was ever established" and "every
requirement I don't have is trivially satisfied by a null fact" produce
the identical `unresolved=[]` list, and the function falls through to
ACCEPT. This did not reach CLEAN in this specific run only because
these two cases happened to have no active requirements to violate — a
policy WITH an active requirement (e.g. `require_we_retain_background_ip=True`)
against the SAME empty-attribution input would presumably still reach
whatever this adapter's "requirement X but no attribution found" branch
does; that branch was not exercised by this corpus and is a concrete,
named follow-up (see Section 6).

**This is reported as a real architecture defect** (a missing
"anchor-fired-but-nothing-structured" gate that 9 of the other 11
adapters have in some form), not merely a corpus miscalibration,
because the mechanism is confirmed by reading the actual extracted facts
object, not inferred from the decision alone.

### 3.4 INSURANCE — FALSE OPERATIVE → CLEAN (`insurance-04`)

**Text**: "Background. It is common practice for a services vendor to
carry Commercial General Liability insurance, though the specific
coverage requirements for this engagement remain to be negotiated."
(all requirements off)

**Result**: `ACCEPT`.

**Mechanism**: confirmed by direct extraction —
`facts.coverages["cgl"].established == True`. The sentence explicitly
states the requirements "remain to be negotiated" (i.e., NOT yet an
agreed term of this engagement), yet the deterministic coverage-type
classifier marks CGL as an ESTABLISHED coverage purely from the word
"carry ... Commercial General Liability insurance" appearing in
industry-background prose. This is the single clearest, most literal
instance of the mission's own FALSE_OPERATIVE→CLEAN definition found in
this corpus: "non-operative/descriptive/hypothetical ... text was
treated as an authoritative operative obligation and allowed a clean
automatic decision."

### 3.5 SLA — FALSE OPERATIVE → CLEAN (`sla-04`)

**Text**: "Background. SaaS agreements typically commit to 99.9%
uptime with service credits for shortfalls, although the parties have
not yet negotiated specific service levels for this Agreement."
(`minimum_acceptable_uptime_percent` unset in this specific case)

**Result**: `ACCEPT` ("SLA commitments: uptime 99.9%.").

**Mechanism**: confirmed by direct extraction —
`uptime_percent=99.9` and `service_credit_present=True` are both
extracted from prose that explicitly says the parties "have not yet
negotiated" any service level. The number "99.9%" appearing anywhere
near the word "uptime" is sufficient for the deterministic extractor to
treat it as this Agreement's own established commitment, regardless of
the surrounding sentence explicitly disclaiming it as descriptive/
not-yet-agreed. Structurally identical mechanism to 3.4.

### 3.6 INDEMNIFICATION — MATERIAL CONTEXT SILENTLY LOST, masked (`indemnification-07`)

**Text**: a core indemnification sentence in Section 12, with a
material time-bar qualifier ("applies only to claims filed within
ninety days") stated in a LATER, separate Section 19 that
back-references Section 12.

**Result**: `MUST_REDLINE` — but for an unrelated reason ("exposure
obligation states no monetary treatment at all"), not because the
Section 19 qualifier was found.

**Mechanism**: confirmed by inspecting `decision_unresolved_facts` — the
Section 19 time-bar language never appears anywhere in the decision or
its explanation. `_core_detect_conflicting_backward_conditions` (the
deterministic backward-reference mechanism proven for liability's own
adversarial tests in prior sessions) did not fire for this phrasing.
**This did not independently produce a CLEAN result in this specific
case** only because an unrelated defect (missing monetary structure)
already forced `MUST_REDLINE` first — so it is reported as a confirmed,
real instance of material context disappearing before deterministic
evaluation (the mission's metric #4), flagged as MASKED rather than
counted toward the strict "reached CLEAN" gates, in the interest of not
overstating what was proven. **A version of this same document with a
monetary cap stated would very plausibly reach ACCEPT while the Section
19 time-bar silently vanishes** — this was not tested (a new case would
be required, and Rule #2 forbids modifying frozen corpus cases after
seeing results), so it is named here as a concrete, high-priority
follow-up rather than claimed as proven.

## 4. Investigated and RECLASSIFIED as corpus/ground-truth defects (not system defects)

Per Absolute Rule #2 ("If a corpus case itself is objectively defective,
document it separately. Do not silently repair it or remove it from
denominators."), the following mismatches were investigated and
determined to reflect an error in this session's ground-truth authoring
or corpus phrasing, not a genuine safety-gate violation — each is kept
in the corpus and its mismatch is counted in the raw numbers, but not
counted among the confirmed violations above:

- **liability-01, liability-05, liability-07, payment_terms-01/04/05/06,
  data_security-01/06 (ESCALATE), warranties-06, termination-01/04/06,
  governing_law-02/05, assignment-04/06, confidentiality-02/04/07,
  ip_ownership-02/05, insurance-05, sla-06, indemnification-05,
  warranties-01/02/05**: in every one of these, the actual decision was
  **more conservative** than this session's predicted ground truth
  (REQUIRES_REVIEW/NEGOTIATE/MUST_REDLINE/NOT_APPLICABLE where CLEAN or
  a specific violation state was predicted), because this session's
  hand-authored contract text did not match a specific deterministic
  extraction pattern (e.g., liability's cap-multiplier regex expects
  "N times fees," not "shall not exceed fees paid"; payment_terms'
  net-days regex did not recognize spelled-out "thirty days" in this
  phrasing; several adapters' obligation regexes did not recognize
  cross-sentence or unusually-phrased directional statements). None of
  these reached a clean/accepting result when the ground truth expected
  otherwise — they all fail toward MORE scrutiny, which is the safe
  direction this architecture is built to prefer. They are recall gaps
  (missed detections that route to caution) rather than safety
  violations (missed detections that route to false confidence), and
  are named here as legitimate but lower-priority follow-up items, not
  hidden.
- **indemnification-06**: re-examined and determined the ground truth
  itself was likely wrong — a one-directional indemnity that protects
  the sell-side party with no corresponding exposure obligation on that
  same party is not inherently a policy gap (it is favorable to the
  protected side); this session's authored expectation that "Vendor's
  own unaddressed exposure side should force review" does not have a
  clear textual or policy basis. Not counted as a WRONG_PARTY→CLEAN
  violation.
- **assignment-05**: similar re-examination — an asymmetric assignment
  restriction (Customer restricted, Vendor unrestricted) evaluated from
  the VENDOR's own contract_side is, in fact, favorable to Vendor; this
  session's ground truth calling for NOT_CLEAN did not account for whose
  side the policy evaluation runs from. Not counted as a violation.
- **confidentiality-06 asymmetry** is the one exception in this
  category that WAS confirmed as real (see Section 3.1) — included here
  only to make clear that "asymmetric obligations" as a category was not
  uniformly dismissed; it was investigated case-by-case.

## 5. Phase 1 findings (see `EXECUTABLE_ARCHITECTURE.md` for full detail)

The single most consequential finding of this validation: **with
`POLICY_ENFORCEMENT_MODE` unset (the production default = `"shadow"`),
none of the 12-adapter fact-admission architecture validated across this
initiative's prior sessions determines any customer-visible review
result today.** Only `apply_liability_policy()` (the original,
pre-initiative, liability-only legacy path) is authoritative in
`shadow`/`legacy` mode; the 12-adapter engine runs only as a discarded
diagnostic comparison. This is a known, disclosed, deliberate state (see
`ENFORCEMENT_DISCLOSURE` in `policy_enforcement.py`), not a bug, but it
means this validation's scope — and everything found wrong in Section 3
— describes code that is not yet deciding any real contract review,
and will not until a separate, later operator action
(`POLICY_ENFORCEMENT_MODE=cutover`) that this mission's own rules forbid
taking here.

## 6. Named follow-up items (not fixed, per Rule #1)

1. **`ip_ownership_policy_engine.evaluate_ip_policy()`** needs an
   explicit "clause anchor fired but zero ownership attribution
   structured" gate, matching the pattern already used by
   confidentiality/termination/assignment/warranties/sla.
2. **`data_security_policy_engine`**'s breach-notification extractor
   needs day-denominated phrasing support (not just hours), and an
   explicit negated-obligation gate matching warranties' own
   `_CATEGORY_NEGATION_RE` pattern.
3. **`confidentiality_policy_engine._detect_confidentiality_asymmetry()`**
   needs to also compare terms across two SEPARATELY-phrased directional
   obligations, not only within a single mutual opener.
4. **`insurance_policy_engine`** and **`sla_policy_engine`**'s
   coverage/uptime classifiers need a check against the module's own
   `_core_is_operative_context`-style guard (already used elsewhere in
   this codebase, e.g. indemnification) to stop background/descriptive
   sentences from being read as established commitments.
5. **`indemnification_policy_engine`**'s backward-reference condition
   detector should be re-tested against a corpus case with BOTH a
   working monetary cap AND a far-away Section qualifier, to determine
   whether the masked silent-loss in Section 3.6 would reach CLEAN
   unmasked.
6. **A full ≥600-case independent corpus**, per this mission's original
   target, executed with real provider access, to validate the
   AI-contextual-discovery dimension this session could not reach.

## 7. PHASE 7 — Lee Czocher adversarial questions

**Q1: What stops a confidently wrong extraction from becoming a
confidently wrong deterministic ruling?**
VERDICT: PARTIAL.
MECHANISM: `evaluate_admission()`'s hard gates (verbatim grounding,
qualifier grounding, definition/cross-reference resolution,
competing-reading block) stop a confidently wrong AI extraction from
reaching authority — proven in prior sessions' unit tests, not
re-provable here (provider unreachable). For the DETERMINISTIC
extraction path specifically (what this session could test), the answer
is: **nothing, in the five confirmed cases above.** A confidently wrong
deterministic classification (e.g., insurance-04's `established=True`
from background prose) flows straight through to the ruling with no
independent check.
CODE: `insurance_policy_engine.py` coverage classification;
`fact_admission.py:evaluate_admission` (for the AI path only).
CORPUS PROOF: insurance-04, sla-04, data_security-02/05, confidentiality-06.
RESULT: five confirmed rulings driven by a wrong deterministic
extraction.
RESIDUAL RISK: the deterministic backbone has no general-purpose
"is this operative language" guard equivalent to what indemnification's
own `_core_is_operative_context` provides for its module; other adapters
lack an equivalent.

**Q2: What counts clauses that aren't there?**
VERDICT: PARTIAL.
MECHANISM: anchor regexes per adapter; absence states
(`CONFIRMED_ABSENT`/`RECOGNITION_UNCERTAIN`/`PRESENT_BUT_UNRESOLVED`).
CORPUS PROOF: ip_ownership-04/06, insurance-04, sla-04 all "count" a
clause that is either purely descriptive or explicitly negated as
`clause_found=True`.
RESULT: over-counting confirmed in 4 of 74 cases; under-counting
(false absence) not confirmed in any case.
RESIDUAL RISK: anchor-level over-counting is the majority failure mode
found this session, not under-counting.

**Q3: What happens when a clause exists but the system fails to
recognize it?**
VERDICT: PARTIAL.
MECHANISM: `RECOGNITION_UNCERTAIN` absence state exists specifically for
provider failure; for pure regex miss (no provider involved), the
adapter falls back to `NOT_APPLICABLE`/`CONFIRMED_ABSENT` with no
distinct "recognition failed" signal.
CORPUS PROOF: payment_terms-01 (Net-30 clearly present, not recognized,
routed to NEGOTIATE not ACCEPT-nor-flagged-as-recognition-failure).
RESULT: fails safe (NEGOTIATE, not ACCEPT) in the one case tested, but
the SPECIFIC "we saw something but couldn't parse it" signal is
conflated with "policy requires X and X wasn't found" in the
explanation text, which could mislead a reviewer about the actual root
cause.

**Q4: How do we know evidence attached to a decision actually supports
the asserted fact?**
VERDICT: PROVEN (for the deterministic path).
MECHANISM: every decision's `contract_language`/explanation quotes the
actual source excerpt (`_excerpt()` helpers), never a paraphrase.
CORPUS PROOF: every one of the 74 raw results includes a verbatim
`decision_explanation` quoting the source text.
RESULT: consistent across all 74 cases.
RESIDUAL RISK: for the AI-sourced path specifically, this is proven only
by prior sessions' unit tests (`ground_evidence_quote`'s exact-substring
check), not re-provable here.

**Q5: Can the semantic/AI layer acquire decision authority?**
VERDICT: DISPROVEN architecturally / NOT PROVABLE end-to-end this
session.
MECHANISM: `fact_admission.CandidateMaterialFact`'s `_FORBIDDEN_FIELD_NAMES`
guard and `assert_authority_boundary_intact()` prevent any
decision-shaped field from ever existing on the AI-facing schema;
`evaluate_admission()` is the only function permitted to set
`admission_status`.
CODE: `fact_admission.py`.
CORPUS PROOF: none this session (provider unreachable) — this remains a
unit-tested, not corpus-proven, claim.
RESULT: architecturally enforced; not independently re-verified against
fresh adversarial input this session.

**Q6: What happens when independently extracted policy facts need to be
considered together?**
VERDICT: NOT PROVABLE this session.
MECHANISM: `interaction_enforcement.apply_interaction_rules()`, reached
only in `cutover` mode via `apply_active_policies()`.
CORPUS PROOF: none — this corpus calls each adapter's `extract_fn`/
`evaluate_fn` directly (mirroring the `cutover` per-clause dispatch) but
never routes through the interaction engine, since doing so requires the
full `policy_enforcement.py`/database plumbing this validation script
did not build.
RESULT: unexercised this session; a real gap in this validation's
coverage, named here rather than silently skipped.

**Q7: What happens when two parties appear symmetric but differ on a
material dimension?**
VERDICT: PARTIAL.
MECHANISM: `_detect_*_asymmetry()` functions exist for several adapters.
CORPUS PROOF: confidentiality-06 (confirmed gap for the two-separate-
directional-obligations phrasing); ip_ownership-05 and assignment-05
tested but not confirmed as violations after investigation (see Section
4) — termination-05's asymmetric convenience-right case DID correctly
route to `NOT_CLEAN`... actually returned via a different mismatch path
(see raw_results.jsonl for termination-05, which was NOT among the 39
mismatches — it matched ground truth `NOT_CLEAN` correctly).
RESULT: confidentiality's asymmetry detection has a confirmed, real gap;
termination's does not, for the one phrasing tested.

**Q8: Can a condition, proviso, schedule, cross-reference, exception or
definition be silently stripped?**
VERDICT: DISPROVEN for the AI-sourced path (prior sessions' unit tests);
PARTIAL for the deterministic-only path.
MECHANISM: `fact_admission.evaluate_admission`'s zero-silent-loss gates
(unit-tested, not corpus-provable here).
CORPUS PROOF: indemnification-07 confirms a deterministic-only,
non-AI-assisted qualifier CAN be silently lost when phrased in a
separate section — masked in this instance by an unrelated escalation.
RESULT: real, confirmed, but masked this session.

**Q9: Can a user see CLEAN while an underlying material policy
evaluation is unresolved?**
VERDICT: DISPROVEN — yes, by design, today.
MECHANISM: in `shadow`/`legacy` mode (`POLICY_ENFORCEMENT_MODE` unset,
the production default), the 12-adapter engine's REQUIRES_REVIEW/
MUST_REDLINE findings are computed (via shadow comparison) but NEVER
shown to the user — only `apply_liability_policy()`'s result is
user-visible. A user could see a clean liability-only legacy result
while the modern engine's shadow evaluation (discarded, never surfaced)
found something else entirely.
CODE: `policy_enforcement.py:776-809`.
CORPUS PROOF: not corpus-based — confirmed by direct code reading
(Phase 1).
RESULT: confirmed, disclosed, deliberate (see `ENFORCEMENT_DISCLOSURE`),
but real.

**Q10: Can current policy configuration silently change the meaning of
historical review?**
VERDICT: NOT PROVABLE this session.
MECHANISM: `Contract.policy_revision_metadata_json` pins the ACTIVE
`PolicyPosition` revision at decision time (cutover mode only); legacy/
shadow mode has no revisioning (`PolicyRule` mutated in place).
CORPUS PROOF: none — this validation did not exercise the database/
revisioning layer.
RESULT: unexercised; named as a gap in this validation's coverage.

**Q11: Where can the system STILL create false confidence?**
VERDICT: PROVEN.
Six concrete, reproducible mechanisms, all confirmed by direct code/data
inspection in this session:
1. `ip_ownership`'s missing "anchor fired, nothing structured" gate
   (Section 3.3).
2. `data_security`'s day-vs-hour phrasing blind spot and missing
   negated-obligation gate (Section 3.2).
3. `confidentiality`'s asymmetry detector scoped to only one drafting
   pattern (Section 3.1).
4. `insurance`/`sla`'s coverage/uptime classifiers reading descriptive
   background prose as an established commitment (Sections 3.4-3.5).
5. Cross-section qualifiers (Section 3.6) can be silently lost by the
   deterministic-only path even when the AI layer would have caught
   them — this session could not prove the AI layer actually would
   catch it live (provider unreachable), only that prior sessions'
   MOCKED tests showed it should.
6. `shadow`/`legacy` mode itself (Q9) — the biggest source of potential
   false confidence is not a bug in the fact-admission architecture at
   all, but the fact that none of it is customer-authoritative under
   the current default configuration.

## 8. PHASE 8 — Final ship gate

FALSE_SAFE = **3** (target 0) → **GATE FAILED**
UNVERIFIED_TO_CLEAN = 0 (not exercised — AI layer unreachable)
FALSE_OPERATIVE_TO_CLEAN = **2** (target 0) → **GATE FAILED**
FALSE_ABSENCE = 0
MATERIAL_CONTEXT_SILENT_LOSS = **1 confirmed (masked)** (target 0) → **GATE FAILED** (reported as a real instance regardless of masking)
ARBITRARY_COMPETING_READING = 0 (not exercised this session in the deterministic-only path's own terms — the framework-level gate is unit-tested, not corpus-provable here)
PROVIDER_FAILURE_TO_CLEAN = not applicable (provider not invoked)
GROUNDING_FAILURE_TO_CLEAN = not applicable (same)
WRONG_PARTY_TO_CLEAN = 0 confirmed
DETERMINISM = 100% → **GATE PASSED**

Additional required conditions:
- All 12 adapters actually exercised: **YES** (74 cases across all 12).
- No production code changed after final corpus results were observed:
  **YES** — the two fixes made during corpus construction (missing
  `_TerminationPolicy`/`_AssignmentPolicy` attribute names in this
  session's OWN validation-script dataclasses) were made BEFORE any case
  result was observed (the runner crashed before producing any decision
  for those cases) and touched only `artifacts/final_frozen_validation/
  corpus/run_corpus.py`, never a production file. No production file
  listed in `FREEZE_MANIFEST.md`'s hash list was modified at any point
  after freeze.

**Multiple required gates failed (FALSE_SAFE, FALSE_OPERATIVE→CLEAN,
MATERIAL_CONTEXT_SILENT_LOSS).**

## FINAL VALIDATION VERDICT: FAIL

## SHIP: NOT AUTHORIZED

This frozen candidate (`f94c4c319f828c4e0072af9305d409a03964d237`) does
not meet the ship gate. Five confirmed, reproducible safety-gate
violations were found in the deterministic backbone using a corpus of
only 74 fresh cases — smaller than the requested 600, which is itself
grounds to expect more undiscovered defects, not fewer. Per this
mission's explicit instruction, no production code was modified in
response to these findings. A later candidate, after the six named
follow-up items in Section 6 are addressed on a fresh branch, must
receive a NEW independent frozen corpus — this one is spent (its cases
and results are now known and can no longer serve as a blind test).
