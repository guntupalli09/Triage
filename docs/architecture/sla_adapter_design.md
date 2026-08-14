# SLA / Service Levels — Adapter #12 Design Pass

**Scope**: a design-only review for the SLA/Service Levels adapter, performed
before implementation, per the recommendation of
`docs/architecture/ten_adapter_scalability_review.md` (§9.2), which already
flagged SLA as "the one adapter of the twelve where the honest answer isn't
a clean yes or no" on whether it introduces a new reasoning shape — because
of exactly the tiered-severity-table question this document resolves.

No code was written or changed to produce this document. Every claim about
current architecture below was checked against the actual source
(`playbook_authoring.py`, `policy_engine_core.py`, `insurance_policy_engine.py`,
`payment_terms_policy_engine.py`) rather than assumed from memory.

---

## 1. Reasoning shape

SLA is not one shape — it is three shapes wired together, and conflating
them is the single biggest risk in this design. Modeled as three
independent groups of facts, mirroring the discipline the Payment Terms
task established ("keep distinct... do not collapse X and Y into one
field") and the Warranties task extended ("keep warranty obligation
separate from remedy"):

**Group A — Availability commitment** (a single-value, catalog-of-facts
shape, closest in kind to Payment Terms' individual dimensions):
- uptime/availability percentage commitment
- measurement period (monthly / quarterly / annually — the window the
  percentage is calculated over)
- exclusions that modify the *effective* threshold: scheduled maintenance,
  emergency maintenance, customer-caused outages, force majeure — each
  independently present/absent, because a contract can state any subset
  and the presence of one does not imply the others
- reporting/measurement methodology (how uptime is calculated — e.g.
  "measured at the network edge," "excludes DNS propagation") — presence-
  only fact, not a structured formula (see §5 on why parsing an actual
  formula deterministically is out of scope)

**Group B — Severity-tiered response/restoration commitments** (a keyed
catalog, structurally identical in kind to Insurance's per-coverage-type
`CoverageRequirement` dict — see §2 for the full argument): for each
severity level, independently: response-time target, restoration/
resolution-time target, whether the clock runs on business hours or
24x7, and support-hours/support-channel commitments that may be global
(one set for the whole SLA) or per-severity (e.g. P1 gets 24x7 phone
support, P3 gets business-hours email only).

**Group C — Remedy mechanics** (directed-obligation-adjacent, closest in
kind to Warranties' remedy facts, deliberately kept separate from Group
A/B per-fact establishment): service-credit schedule (what % of fees is
credited at what breach severity/frequency), credit thresholds, credit
caps (a ceiling on cumulative credits in a period), chronic-failure/
repeated-breach definition (e.g. "three consecutive months of Sev1
breach"), termination rights triggered by chronic failure, claim/credit
submission deadlines, and whether service credits are the customer's
**exclusive remedy** for an SLA breach — this last fact is the SLA
analogue of Warranties' `exclusive_remedy_present`/`prohibit_exclusive_
remedy` pair and should reuse that exact naming/reasoning pattern rather
than reinvent it.

**Do not assume a single threshold model** — confirmed as the correct
instruction. A `sla_compliant: bool` or single `overall_state` classifier
would collapse three independently-configurable, independently-violable
commercial facts (a contract can meet its uptime commitment while missing
every P1 response target, or vice versa) into one number, exactly the
mistake every prior adapter in this codebase was built to avoid (Payment
Terms' and Insurance's module docstrings both open by rejecting this
same shape for their own domains).

---

## 2. Tiered severity table — the key design question

### 2.1 What the current schema can and cannot express

Checked directly against `playbook_authoring.py`'s `_validate_field`
(the function `validate_config` uses to type-check every `config_json`
value against its adapter's Protocol): the generic validator supports
exactly two shapes — a bare scalar (`bool`/`float`/`int`/`str`, optionally
`None`) or `List[scalar]` (one element type, validated per-element, plus
an optional bounded-vocabulary check). There is **no support for
`List[Dict]`, a nested dataclass, or any keyed/structured object** in a
Protocol field's type hint — `_non_none_arm`'s own docstring states every
config field's Optional union "wraps exactly one other type... never a
real multi-type Union," and the list-handling branch destructures exactly
one element type via `(elem_type,) = typing.get_args(inner) or (str,)`.

This means a literal "typed row objects" design — a `severity_tiers:
List[SeverityTarget]` Protocol field, where `SeverityTarget` is itself a
dataclass with `severity_level`/`response_hours`/`restoration_hours`/
`business_hours_only` — **cannot be validated by `validate_config` as it
exists today.** Adding that support would be a genuine change to shared,
generic code (`_validate_field`, and by extension every place that
introspects `CLAUSE_TYPE_CONFIG_FIELDS`/`ACTIVATION_REQUIRED_FIELDS` via
`typing.get_type_hints()`), affecting all eleven existing adapters' schema
derivation, not just SLA's.

### 2.2 The three options, evaluated against that constraint

**Typed row objects (nested dataclass list) at the *policy config*
layer.** Rejected for the reason above — it requires extending the
generic schema validator, which the task explicitly does not authorize
for a design-only pass, and which the ten-adapter review already flagged
as exactly the kind of promotion that should be deliberately re-scoped
before being built, not defaulted into by one adapter's convenience.

**Keyed severity catalog, flattened to fixed per-severity scalar Protocol
fields.** This is the same pattern already proven, twice, in this exact
codebase: `insurance_policy_engine.py`'s `CoverageRequirement` is a
per-coverage-type dict at the **facts** layer, but its **policy**-layer
counterpart in `InsurancePolicyRuleLike` is not a list or dict at all —
it is eight flat, independently-named scalar fields
(`cgl_minimum_per_occurrence`, `cgl_minimum_aggregate`,
`professional_liability_minimum_limit`, `cyber_liability_minimum_limit`,
`employers_liability_minimum_limit`, `auto_liability_minimum_limit`, each
paired with a `require_*` boolean), one flat pair per coverage type in a
**fixed, enumerated catalog** (`COVERAGE_TYPES`). `warranties_policy_
engine.py` uses the identical technique for its ten warranty categories,
just without per-category numeric fields (categories are membership in a
`List[str]`, not per-category numbers). SLA's severity tiers are the same
shape as Insurance's coverage types — a small, fixed, well-known
enumerated catalog (SLA practice overwhelmingly converges on 3-4 severity
levels, conventionally named P1-P4 or Sev1-Sev4), each needing its own
independent numeric thresholds.

Concretely: a `SEVERITY_LEVELS = ("p1", "p2", "p3", "p4")` module
constant (adapter-local, like Insurance's `COVERAGE_TYPES`), and eight
flat Protocol fields — `p1_max_response_hours`, `p1_max_restoration_
hours`, `p2_max_response_hours`, `p2_max_restoration_hours`,
`p3_max_response_hours`, `p3_max_restoration_hours`,
`p4_max_response_hours`, `p4_max_restoration_hours` (all `Optional[float]`)
— fits the existing generic machinery with **zero schema changes**: every
field is a plain scalar, the existing `number_input` template macro
covers each one (repeated four times, exactly how `insurance.html` repeats
`tristate`/`number_input` per coverage type today), and the existing
`_fmt_hours` summarizer helper (already used by `data_security`'s breach-
notification-hours field) covers formatting with no new helper needed.

**Classification: keyed severity catalog, flattened to fixed scalar
fields at the policy layer — matching a real, already-shipped pattern in
this codebase, not inventing a new one.**

At the **extraction/facts** layer (`SLAFacts`, internal to
`sla_policy_engine.py`, never exposed through `validate_config`), typed
row objects are exactly right and carry no schema risk at all — every
existing adapter's facts layer already uses nested dataclasses freely
(`CapExpression`/`CapValue`, `IndemnityObligation`, `CoverageRequirement`).
A `SeverityTarget` dataclass (`severity_level: str`, `response_hours:
Optional[float]`, `restoration_hours: Optional[float]`, `business_hours_
only: Optional[bool]`, `raw_excerpt`, `start_index`, `end_index`) is the
correct facts-layer structure; it is only the authoring/policy layer that
must flatten to the fixed catalog.

### 2.3 The real cost, stated plainly

A fixed `p1`-`p4` catalog does not gracefully support a contract that
genuinely uses five+ tiers or a non-numbered taxonomy ("Critical/High/
Medium/Low"). The correct, safe handling for that case is **normalization
at extraction time with a documented fallback**: a `_SEVERITY_LABEL_
NORMALIZE` dict (mirroring `payment_terms_policy_engine._CURRENCY_
NORMALIZE`'s exact technique) maps common synonyms ("Sev 1," "Severity
1," "Critical," "P1") onto the canonical `p1`-`p4` set; any severity
token that doesn't normalize cleanly, or a fifth distinct tier beyond
`p4`, should route to `REQUIRES_REVIEW` rather than being silently
dropped or force-mapped — the same "abstain rather than guess" discipline
already used by every other adapter's unmappable-token handling (e.g.
`_resolve_owner`/`_resolve_obligated_party`/`_resolve_warranting_side`
all return `unresolved` instead of guessing). This is a real, named
limitation of the recommended design, not something to discover in
production.

**DECIDED**: confirmed as the design. Four canonical internal severity
levels — `P1_CRITICAL`, `P2_HIGH`, `P3_MEDIUM`, `P4_LOW` — with the
source contract's original label preserved as evidence on the extracted
row (e.g. `SeverityTarget.raw_label = "Sev 1"`, `canonical_level =
"P1_CRITICAL"`) rather than discarded once normalized. Deterministic
synonym mappings ("Sev 1," "Severity 1," "Critical," "Priority 1" →
`P1_CRITICAL`, and the equivalent three-way mappings for P2-P4) are
applied via the `_SEVERITY_LABEL_NORMALIZE` dict described above.
Genuinely ambiguous mappings — a label with no confident match to any of
the four canonical levels, or a fifth distinct tier the contract itself
does not equate to one of the four — route to `REQUIRES_REVIEW`, never a
best-guess assignment. The module docstring should state this
explicitly: the four-level catalog is a deliberate, documented
simplification of real-world severity taxonomies, not a claim that every
company's taxonomy is actually four-tiered.

---

## 3. Activation readiness

### 3.1 What the existing mechanical rule already covers correctly

Checked directly: `ACTIVATION_REQUIRED_FIELDS` is derived mechanically —
a config field qualifies iff its Protocol type hint is exactly `bool`
(not `Optional[bool]`) **and** its name starts with `require_`. For SLA's
true booleans (`require_uptime_commitment`, `require_service_credits`,
`require_termination_right_for_chronic_failure`, etc. — see §4), this
rule applies completely unchanged, with zero new code, exactly as it did
for all eleven prior adapters.

For the eight flat per-severity numeric fields from §2.2
(`p1_max_response_hours` etc.), the mechanical rule correctly does **not**
add them to `ACTIVATION_REQUIRED_FIELDS` (they are `Optional[float]`, not
`bool`) — and that is the right outcome, not a gap: every existing
numeric-ceiling field in every adapter (Payment Terms' `maximum_late_
interest_rate_percent`, Insurance's `cgl_minimum_per_occurrence`) is
allowed to activate while `NOT_ESTABLISHED`, meaning "no policy stance on
this dimension," and SLA's per-severity numeric fields are not
architecturally different from those. A lawyer who only cares about P1
targets and genuinely has no P3/P4 policy stance should be able to
activate that position, the same way a lawyer configuring Insurance who
only cares about CGL coverage can activate without configuring
Professional Liability or Cyber Liability. **This is not a new problem
requiring new machinery — the task's framing ("no P1 target configured"
vs. "missing restoration target" vs. "missing uptime threshold" are
different from explicit permissive policy") is already correctly handled
by the existing per-field `NOT_ESTABLISHED`/`ESTABLISHED` status on
`PolicyPositionField`, independent of `config_json`'s actual value** —
that distinction is exactly what `PolicyPositionField.status` exists to
carry, and it already works identically for every numeric field in every
adapter today.

### 3.2 What is genuinely new: cross-field internal consistency

The mechanical rule checks exactly one field's type and name — it cannot
express a relationship *between* fields. SLA introduces a real instance
of a relationship the existing rule structurally cannot catch: a lawyer
who sets `require_uptime_commitment = True` (satisfying the mechanical
rule by itself reaching `ESTABLISHED`) while leaving `minimum_acceptable_
uptime_percent` at `NOT_ESTABLISHED` has satisfied the *boolean gate* but
configured a position that is vacuously enforceable — the engine would
require *some* uptime commitment to exist in the contract text, but never
check it against any lawyer-specified floor, silently accepting any
uptime percentage (or none) as sufficient. The same shape recurs for
`require_service_credits` with no credit-percentage/threshold fields set,
and for a severity-tier "require some tiered commitment" gate (see below)
with all eight `pN_max_*_hours` fields left `NOT_ESTABLISHED`.

This is a genuinely new activation-readiness question this codebase has
not needed before, because no prior adapter paired a `require_*` boolean
whose entire semantic weight depends on a *companion set* of numeric
fields also being configured — Insurance's `require_cgl` is paired with
exactly two companion numeric fields checked independently by the
evaluator regardless of activation status, and a lawyer leaving both
`NOT_ESTABLISHED` produces a real, visible NEGOTIATE/gap in every
contract review (not a silently-vacuous pass), because Insurance's
evaluator flags "coverage present but limit not confirmed" as its own
finding. SLA's severity commitments are structurally the same **if the
evaluator is built the same way** (flag "P1 exists in the contract but no
policy floor was configured" as a REQUIRES_REVIEW-adjacent finding, not
silence) — which suggests the *first* fix should be in the evaluator's
own reasoning (matching Insurance's precedent), and activation-time
validation is a second, complementary safety net, not a replacement for
correct evaluator design.

### 3.3 Recommendation: an adapter-owned activation-validator hook

Per the task's explicit preference ("prefer an adapter-owned activation
validator if that is cleaner than expanding generic heuristics") —
**yes, this is cleaner**, and it can be added with a minimal, purely
additive change to `validate_position_for_activation` that does not touch
the mechanical mostly-generic path used by the other eleven adapters:

```python
# Sketch only -- not implemented as part of this design pass.
_ADAPTER_ACTIVATION_VALIDATORS: Dict[str, Callable[[PolicyPosition, Dict[str, str]], List[str]]] = {}

def validate_position_for_activation(position: PolicyPosition) -> None:
    required = ACTIVATION_REQUIRED_FIELDS.get(position.clause_type, [])
    statuses = _current_field_statuses(position)
    missing = [name for name in required if statuses.get(name) != "ESTABLISHED"]
    extra_validator = _ADAPTER_ACTIVATION_VALIDATORS.get(position.clause_type)
    if extra_validator:
        missing.extend(extra_validator(position, statuses))
    if missing:
        raise PolicyActivationError(position.clause_type, missing)
```

`_ADAPTER_ACTIVATION_VALIDATORS` defaults to empty for every adapter that
doesn't register one (all eleven existing adapters, unchanged behavior,
zero risk); SLA registers a function that checks, e.g., "if
`require_uptime_commitment` is `ESTABLISHED` as `True`, at least one of
`minimum_acceptable_uptime_percent`/`preferred_uptime_percent` must also
be `ESTABLISHED`" and the equivalent for service-credit and severity-tier
gates. This is a generic *extension point* (one new dict, one new
optional call), not new generic *logic* — the mechanical rule keeps
governing the ten adapters that need nothing more, and SLA opts into
exactly the additional check its own field relationships require. This
also directly answers §8's question about whether SLA needs adapter-
specific activation validation: **yes**, and this is the shape it should
take.

---

## 4. Policy authoring — proposed lawyer-facing fields

Following the naming and NOT_ESTABLISHED-preserving conventions of the
eleven existing adapters exactly (a `require_*` boolean gates whether a
whole dimension is checked at all; a `prohibit_*` boolean chooses severity
between two already-non-accepting states; numeric fields are bare
`Optional[float]` ceilings/floors; bounded-string fields go through
`_BOUNDED_VOCABULARIES`).

**DECIDED (comparison direction)**: per the explicit instruction not to
infer comparison semantics from field names, every numeric field's
direction is stated in prose here and must be implemented as a literal,
named comparison in the evaluator (`actual < policy_value` or
`actual > policy_value`), never inferred from whether the field is
spelled `minimum_*`/`maximum_*`. Response/restoration targets are
maximums a contract must not exceed (smaller stated value is a stronger
commitment). Availability/uptime and credit-cap generosity are minimums
a contract must meet or exceed (larger stated value is stronger). Two
fields below were renamed from the original draft specifically because
their original names implied the wrong direction by convention alone —
exactly the failure mode decision #3 warns against.

| Field | Type | Direction | Purpose |
|---|---|---|---|
| `require_uptime_commitment` | `bool` | — | Gates whether an uptime/availability commitment must be established at all |
| `preferred_uptime_percent` | `Optional[float]` | — | Not itself activation-gating (mirrors `payment_terms.preferred_net_days`) |
| `minimum_acceptable_uptime_percent` | `Optional[float]` | Floor — violation if `actual < policy_value` | Larger stated uptime is stronger |
| `p1_max_response_hours` … `p4_max_response_hours` | `Optional[float]` × 4 | Ceiling — violation if `actual > policy_value` | Per-severity response ceiling (§2.2); smaller stated hours is stronger |
| `p1_max_restoration_hours` … `p4_max_restoration_hours` | `Optional[float]` × 4 | Ceiling — violation if `actual > policy_value` | Per-severity restoration/resolution ceiling; smaller stated hours is stronger |
| `require_severity_tiers` | `bool` | — | Gates whether *some* per-severity commitment must exist (paired with the §3.3 hook) |
| `required_support_hours` | `Optional[str]` | — | Bounded vocab: `"24x7"` / `"business_hours"` / `"not_stated"` — mirrors `governing_law.required_dispute_resolution`'s bounded-string pattern exactly |
| `permitted_maintenance_exclusions_json` | `Optional[List[str]]` | — | Bounded vocab over `("scheduled_maintenance", "emergency_maintenance", "customer_caused", "force_majeure")` — mirrors `assignment.required_exceptions_json`'s list-of-bounded-tokens pattern |
| `require_service_credits` | `bool` | — | Gates whether a service-credit remedy must exist at all (this adapter's own remedy fact — see §7 on why this is deliberately not merged with `payment_terms.service_credit_present`) |
| `minimum_credit_percent_of_fees` | `Optional[float]` | Floor — violation if `actual < policy_value` | Larger stated credit percentage per qualifying breach is stronger |
| `minimum_credit_cap_percent_of_fees` | `Optional[float]` | Floor — violation if `actual < policy_value` | Renamed from `maximum_credit_cap_...` in the original draft: a credit *cap* is a ceiling on the vendor's exposure, so a **higher** cap is more favorable to the party receiving credits — the policy field is therefore a floor (minimum acceptable cap), the opposite direction a "maximum"-style ceiling field would suggest by name alone |
| `require_chronic_failure_remedy` | `bool` | — | Gates whether a chronic/repeated-breach provision must exist |
| `require_termination_right_for_chronic_failure` | `bool` | — | Gates whether chronic failure must carry a termination right, not just credits |
| `prohibit_service_credits_as_exclusive_remedy` | `bool` | — | Mirrors `warranties.prohibit_exclusive_remedy` exactly — same fact, same adapter-local naming convention, applied to SLA's remedy instead of Warranties' |
| `minimum_claim_submission_days` | `Optional[float]` | Floor — violation if `actual < policy_value` | Not renamed — on review this field was already directionally correct in the original draft (a *shorter* contract-stated deadline than the policy's minimum is the violation, the same `actual < floor` direction as every other minimum-style field in this codebase); flagged here explicitly only so the comparison direction is stated, not inferred, per decision #3 |
| `escalation_approval_authority` | shared | — | Standard |
| `fallback_text` | shared | — | Standard |

Every field defaults to `NOT_ESTABLISHED`/`None` per the standard
convention; nothing here infers a negotiation tier the lawyer hasn't
explicitly set, matching every prior adapter's discipline.

---

## 5. Extraction hazards

Cross-checked against the actual bug classes already found and fixed in
this codebase (`docs/architecture/ten_adapter_scalability_review.md` §2,
plus this session's Stage A hardening pass) — SLA is the adapter most
likely to reproduce several of them simultaneously, because it has more
independently-meaningful numbers sharing similar surface phrasing than
any prior adapter:

- **Percentages from unrelated provisions.** SLA's uptime percentage
  ("99.9%"), credit percentage ("5% of monthly fees"), and — if a
  contract also has Payment Terms language nearby (common in a combined
  "Fees and Service Levels" section) — price-increase or late-fee
  percentages, are all bare `N%` patterns. This is the exact collision
  class Payment Terms' own corpus already documents fixing (late-fee vs.
  price-increase percentages) via dimension-specific anchor-scoped local
  windows (`_INTEREST_ANCHOR_RE`/`_PRICE_INCREASE_ANCHOR_RE`) — SLA needs
  the same technique from the first draft (`_UPTIME_ANCHOR_RE`/`_CREDIT_
  ANCHOR_RE`), not discovered via a benchmark failure.
- **P1/P2/P3 labels colliding with section numbering.** A contract
  section labeled "9.1," "9.2," "9.3" sits visually and pattern-wise
  close to "P1," "P2," "P3" severity labels, especially in poorly-OCR'd
  or inconsistently-formatted text ("Section 9.1 (P1)"). A naive `P\d`
  regex risks matching "P" immediately preceding a section-numbering
  digit in unrelated prose. Needs a word-boundary- and context-anchored
  pattern (e.g. requiring "Severity"/"Priority" nearby) rather than a bare
  `P[1-4]` token match.
- **Response time confused with restoration time.** These are two
  independently meaningful numbers in the *same sentence*
  ("P1: 1 hour response, 4 hour restoration") — the highest-risk
  extraction pattern in the whole adapter, structurally identical to
  Payment Terms' worst historical bug (late-fee vs. price-increase
  percentage cross-contamination) but *harder*, because here both numbers
  belong to the *same* severity tier and are legitimately close together,
  so anchor-scoping alone (which worked for Payment Terms because the two
  percentages were in different sentences) will not fully separate them
  — the regex needs to capture response and restoration as two named
  groups from one match, not two independent scoped searches, or it will
  silently mismatch which number means which.
- **Hours vs. business hours vs. business days.** "4 hours" vs. "4
  business hours" vs. "1 business day" are three different actual
  durations. **DECIDED**: unlike Warranties' month/year-to-days
  normalization (a safe conversion because a month and a year are
  calendar-time units with no external dependency), calendar hours and
  business hours are **never** converted into one another. A business
  calendar depends on facts not present in the contract text (holiday
  schedules, support-window start/end times, which days count as
  business days for this specific counterparty) — computing "4 business
  hours = X calendar hours" would be fabricated precision, the same
  category of risk the §1 "effective uptime percentage" discussion
  already rejects for the same reason. `SeverityTarget` therefore carries
  a `basis: "calendar" | "business" | "not_stated"` field alongside its
  numeric value, and the evaluator compares a contract's stated target
  against a policy ceiling **only when both share the same basis**; a
  policy ceiling stated in calendar hours compared against a contract
  commitment stated in business hours (or vice versa) routes to
  `REQUIRES_REVIEW` rather than silently mixing units — unless the
  contract itself explicitly defines the conversion (e.g. "business
  hours are 9am-6pm Monday-Friday, excluding federal holidays," which
  some SLAs do state), in which case that contract-stated conversion,
  and only that one, may be applied. This is a stricter rule than any
  existing adapter's numeric-normalization pattern and should be called
  out as such in the module docstring, not silently modeled as "just
  another unit conversion."
- **Minutes/hours/days conversions generally.** Some SLAs state response
  times in minutes ("15-minute response for P1"). A single canonical
  unit (hours, as a float) with a documented minutes→hours conversion is
  the same normalization discipline as Warranties' duration handling.
- **Different tables for support vs. SLA.** A contract's "Support"
  section (support hours, support channels, ticket-submission process)
  and its "Service Level" section (uptime, credits) are often physically
  separate, sometimes in different schedules entirely, and a naive
  document-wide anchor could conflate a support-hours commitment with an
  SLA severity-tier commitment. Needs the anchor/window design to treat
  "support hours" as its own fact (already in the Group A/B/C model
  above) extractable independently of whether it's textually adjacent to
  the severity table.
- **Cross-referenced schedules.** "SLA terms are as set forth in Exhibit
  B" — the same detect-but-don't-resolve pattern already used by
  `payment_terms._SCHEDULE_CROSSREF_RE` and `warranties._SCHEDULE_
  CROSSREF_RE` applies directly; SLA is highly likely to have this
  pattern given how commonly service levels live in a separate exhibit.
- **Multiple SLA versions / amendments.** Per the ten-adapter review's
  finding (§1.4/§2.4): no adapter except `liability_policy_engine.py` has
  genuine amendment-aware "last mention wins" resolution; every other
  adapter (correctly) relies on the generic accumulate-then-conflict
  machinery to route a genuine amendment to `REQUIRES_REVIEW` rather than
  guess. SLA should follow the same precedent — no bespoke amendment
  logic, safe abstention via conflict detection on the per-severity
  values and the uptime percentage.
- **Availability exclusions modifying the effective threshold.** This is
  SLA-specific and has no direct precedent in this codebase: "99.9%
  uptime, excluding scheduled maintenance" states a *nominal* threshold
  whose *effective* meaning depends on which exclusions apply and how
  broadly they're drafted (a broad "and any other planned downtime"
  exclusion materially weakens a 99.9% commitment). The adapter should
  extract the nominal percentage and the exclusion list as **independent
  facts** (per §1's Group A model) and explicitly **not** attempt to
  compute an "effective" percentage — that computation requires knowing
  how much downtime the exclusions actually cover, which is not
  extractable from contract text alone. Any policy check should compare
  against the nominal percentage while separately flagging the presence
  of broad/open-ended exclusion language, rather than fabricate a
  weighted number.
- **Credits expressed as percentage of monthly fees.** Needs to be kept
  as a percentage fact tied to a stated base ("% of monthly fees," "% of
  the fees paid in the affected month") — not normalized to a dollar
  amount, since the base is contract-specific and often not itself a
  fixed number in the visible text (mirrors Payment Terms' deliberate
  choice to keep percentage-based facts as percentages rather than
  attempting dollar conversion).
- **Cumulative credit schedules.** "5% credit for the first breach, 10%
  for a second breach in the same quarter, capped at 25% of monthly fees"
  is a genuinely tiered, stateful structure (credit amount depends on
  breach *count*, not just breach *severity*) — this is likely to be the
  single hardest extraction target in the whole adapter and the strongest
  candidate for "detect that a cumulative/escalating schedule exists,
  extract the cap, do not attempt to parse the full escalation formula
  deterministically" — the same "detect, don't over-parse" discipline
  Liability's cross-reference resolver and Payment Terms' schedule
  cross-reference both already apply to structures that are real but not
  safely reducible to one deterministic value.

---

## 6. Corpus plan (80–100 cases, proposed structure — not yet written)

Following the corpus discipline already established and explicitly
required by every adapter since Insurance (`DEFAULT_POLICY` requires
nothing; each case turns on only the dimension(s) it tests;
`case()`/`CASES` helper structure identical to `benchmarks/warranties_
corpus.py`), proposed distribution across roughly 85 cases:

| Category | ~Count | Notes |
|---|---|---|
| Fully-compliant baseline | 1 | Combines uptime + full severity table + credits + support hours, mirroring every prior adapter's `clean-01` |
| Simple uptime commitments | 5 | 99.9%/99.5%/99.99%, missing, conflicting |
| Measurement period variants | 3 | Monthly/quarterly/annual |
| Tiered uptime/credit tables | 4 | Multiple uptime bands each with a different credit % |
| Severity-response matrices | 8 | Full P1-P4 table; partial (P1 only); response-only no restoration; restoration-only no response |
| Response vs. restoration disambiguation | 4 | Adversarial cases specifically targeting the §5 response/restoration confusion risk |
| Business hours vs. 24x7 vs. business days | 6 | Each unit type, plus a mixed case (P1 24x7, P3 business-hours) |
| Minutes/hours/days conversion | 4 | 15-minute response; 1-business-day restoration; mixed units in one table |
| Conflicting severity tables | 4 | Two different P1 response values stated in different sections |
| Scheduled maintenance exclusions | 3 | Narrow, broad/open-ended, absent |
| Emergency maintenance / customer-caused / force-majeure exclusions | 3 | One per exclusion type |
| Support hours (24x7 vs. business-hours) | 3 | Including one where support hours differ from the P1 response commitment |
| Support channels | 2 | Phone/email/portal presence |
| Service-credit formulas | 6 | Flat %, tiered by severity, tiered by breach count, capped, uncapped, expressed against undefined base |
| Chronic failure / repeated breach | 4 | Defined trigger, undefined trigger, present but no remedy attached |
| Termination triggers tied to SLA failure | 3 | Present, absent, present but ambiguous threshold |
| Exclusive remedy | 3 | Present/prohibited/allowed — mirrors Warranties' `as-is-prohibited-01`/`as-is-allowed-01` pattern exactly |
| Claim/credit submission deadlines | 2 | Present, missing |
| No SLA clause | 2 | Including one with a stray "service level" mention with no structure (mirrors Warranties' `no-clause-stray-mention-01`) |
| Malformed tables/text | 4 | Garbled table, placeholder text, run-on repetition, OCR-mangled table cell |
| Explicit negation | 2 | "No service level commitments are made," "P4 issues carry no restoration target" |
| Cross-referenced schedules (Exhibit/SOW) | 3 | Nothing-else-established, supplementing existing text |
| Amendments | 2 | Consistent restatement, changed uptime value |
| Multiple SLA versions in one document | 2 | Superseded draft language left in, genuinely conflicting |
| Negative controls | 8 | "guarantee" used non-legally (already precedented in Warranties' corpus); a percentage from an unrelated Payment Terms clause; "P1" as a product SKU; "response time" in a marketing/non-contractual context; "24/7" in an unrelated operational clause; a severity label inside a bug-tracking cross-reference, not the SLA itself |
| Ambiguous pronouns / unresolvable severity labels | 3 | A fifth, non-standard severity tier; a severity label with no numeric target attached; "as applicable" with no table |

Total: ~85, comfortably inside the 80-100 range, matching the size of the
Warranties (83) and Insurance (79) corpora it is modeled on.

---

## 7. Interaction readiness (facts to expose, not to wire up)

Following the same evidence-based classification method used in the
ten-adapter review's Interaction Engine section (§8 there) — assessed
against what `SLAFacts`/`PolicyDecision` would plausibly carry once built,
not against a hypothetical:

- **SLA ↔ Termination.** **READY FROM STRUCTURED FACTS**, by direct
  analogy to the already-verified Payment↔Termination relationship (the
  ten-adapter review's cleanest example): `termination_policy_engine.py`
  already has a `_TRIGGER_NONPAYMENT_RE` trigger category; a chronic-
  SLA-failure termination right is the same shape (a named trigger
  category an interaction layer can join on by category name and
  `start_index`/`end_index` span), and SLA's own `require_termination_
  right_for_chronic_failure` fact plus Termination's independently-
  extracted trigger give an interaction layer both sides without
  re-parsing.
- **SLA ↔ Payment Terms.** **NEEDS SMALL OUTPUT EXTENSION — DECIDED, no
  merge.** Resolved explicitly: SLA owns the full service-level remedy
  (trigger, percentage, calculation basis, cap, exclusivity, claim
  deadline) as its own facts; Payment Terms keeps its existing
  `service_credit_present: Optional[bool]` exactly as-is, continuing to
  recognize only that a service credit exists in the commercial/payment
  context, with no new dependency on `sla_policy_engine.py` and no shared
  resolver function between the two modules. The two adapters' facts stay
  genuinely independent today, each extracted by its own module with no
  cross-import. The only forward-looking hook is the same low-cost
  primitive already used elsewhere in this codebase for cross-adapter
  correlation without coupling: both facts already carry (or will carry)
  `start_index`/`end_index` spans, which a **future** Interaction Engine
  — not either extractor — can use to notice "these two facts describe
  the same contract sentence" without either adapter importing or
  knowing about the other. This is a deliberate rejection of cross-adapter
  coupling inside either extractor, not a deferred merge.
- **SLA ↔ Warranties.** **READY FROM STRUCTURED FACTS**, structurally,
  once built — both adapters already carry an `exclusive_remedy_present`/
  `prohibit_exclusive_remedy`-shaped fact (Warranties has it today; SLA's
  §4 field list proposes the identical fact under a parallel name). An
  interaction layer asking "does the SLA's service-credit exclusivity
  conflict with or duplicate the Warranties section's remedy
  exclusivity" is a direct structured comparison with no re-extraction,
  the same shape as the prior review's Payment↔Termination example.
- **SLA ↔ Liability.** **NEEDS SMALL OUTPUT EXTENSION.** `liability_
  policy_engine.py`'s `_CATEGORY_KEYWORD_RE` carve-out categories do not
  currently include an SLA/service-credit category (its current set is
  `data_breach`/`ip_infringement`/`confidentiality`/`indemnification`/
  `fraud`/`gross_negligence`/`willful_misconduct`). "Is the customer's
  service-credit remedy explicitly carved out of (or subject to) the
  general liability cap" is a real, commercially significant question
  (service credits are sometimes drafted as entirely outside the
  liability cap, sometimes counted against it) that neither adapter can
  answer today without Liability adding an `sla_credits`-shaped
  carve-out category alongside its existing ones — a small, additive
  extension to an existing enumerated set, not a new mechanism, and the
  same shape of extension the ten-adapter review already recommended for
  the Liability↔Data/Security and IP↔Liability relationships (both of
  which also just need a shared identifier or an additional named
  category, not new extraction machinery).

None of the four relationships would require re-extraction; two need a
small, already-precedented output extension.

---

## 8. Final verdict

**Can SLA fit the current adapter architecture cleanly?**
Yes, at the facts/extraction/evaluation layer without exception, and at
the policy-authoring layer with one specific, well-precedented technique
(the flattened keyed-catalog pattern from §2.2) rather than a literal
nested-object schema. Every other piece — evidence/provenance via
`PolicyDecision`, REQUIRES_REVIEW construction, the accumulate-then-
resolve conflict discipline, negation guards, case-sensitive party-name
capture, `detect_role_attributed_asymmetry` (not needed here — SLA has no
reciprocal/mutual concept, the same negative-control data point
`governing_law` already represents) — reuses existing, proven primitives
with zero new code required in `policy_engine_core.py`.

**Does it need a new shared primitive?**
No new *generic-layer* (`policy_engine_core.py`/`playbook_authoring.py`
schema-validation) primitive is required, provided the flattened keyed-
catalog design from §2.2 is used instead of a literal typed-object config
field. Two *adapter-local* patterns should be reused, not reinvented, from
existing adapters: the `_local_window`/`_SENTENCE_END_RE` regex-based
sentence-boundary helper (copy verbatim from `payment_terms_policy_
engine.py`, as `insurance_policy_engine.py` and `warranties_policy_
engine.py` both already did this session — see the Stage A hardening
pass and the Warranties build) and the `_SCHEDULE_CROSSREF_RE` detect-
don't-resolve pattern.

**Does it need adapter-specific activation validation?**
Yes — confirmed as a genuine, new-in-kind need (§3.2/§3.3), because SLA
is the first adapter where a `require_*` boolean's entire enforcement
value depends on a companion *set* of numeric fields also being
configured, a relationship the mechanical `ACTIVATION_REQUIRED_FIELDS`
rule cannot express by design (it inspects one field's type and name,
never relationships between fields). The recommended fix (§3.3) is a
minimal, purely additive optional-hook extension point on
`validate_position_for_activation`, registered per-clause-type, that
changes nothing about the mechanical path the other eleven adapters use.

**What must be decided before implementation? — RESOLVED.**
All four decisions originally raised here have been made explicitly and
are recorded in the sections they affect:

1. **Severity catalog (§2.3)**: four canonical levels, `P1_CRITICAL`
   through `P4_LOW`, with the source contract's original label preserved
   as evidence on every extracted row. Deterministic synonyms ("Sev 1,"
   "Critical," "Priority 1") normalize to the canonical set; genuinely
   ambiguous mappings, or a taxonomy that doesn't reduce to four tiers,
   route to `REQUIRES_REVIEW` rather than being force-mapped.
2. **Business-hours conversion (§5)**: never converted to calendar hours.
   `SeverityTarget` carries an explicit `basis: "calendar" | "business" |
   "not_stated"` field; the evaluator compares a contract value against a
   policy ceiling only when both share the same basis, routing to
   `REQUIRES_REVIEW` on a basis mismatch unless the contract itself
   states the conversion.
3. **Ceiling/floor direction (§4)**: encoded explicitly per field, never
   inferred from a field's name. Response/restoration targets are
   maximums (smaller is stronger); availability and credit-cap
   generosity are minimums (larger is stronger). Two fields from the
   original draft were renamed during this resolution specifically
   because their names implied the wrong direction by convention alone
   (`maximum_credit_cap_percent_of_fees` → `minimum_credit_cap_percent_
   of_fees`) — direct confirmation that "don't build clever inference
   from field names" is the right rule, since the inference actually
   produced a wrong field name on the first pass.
4. **SLA vs. Payment Terms credits (§7)**: not merged. SLA owns the full
   service-level remedy as its own facts; Payment Terms keeps
   `service_credit_present` unchanged, with no cross-import between the
   two extractor modules. Reconciliation, if ever needed, is a future
   Interaction Engine concern operating on both adapters' independently-
   extracted `start_index`/`end_index` spans, not a coupling built into
   either adapter now.

None of these four was an architecture blocker, and none required a
schema or generic-layer change to resolve — each was a scoped, adapter-
local design decision, now closed.

---

## Recommendation

**PROCEED TO IMPLEMENTATION.** The four decisions §8 originally flagged
as prerequisites are now resolved and recorded in §2.3/§4/§5/§7. Build the
adapter with:
- the flattened keyed-severity-catalog policy schema from §2.2 (not a
  nested-object config field),
- the adapter-owned activation-validator hook from §3.3,
- dimension-specific anchor-scoped extraction for every percentage/
  numeric fact from the first draft (§5), rather than as a
  benchmark-driven retrofit, and
- the response/restoration same-sentence disambiguation named as the
  single highest-risk extraction pattern in §5, designed for explicitly
  rather than discovered as a bug.

Nothing found in this design pass indicates a need to change
`policy_engine_core.py`, `models.py`, or the generic parts of
`playbook_authoring.py` — the one addition (§3.3's optional activation-
validator hook) is purely additive and does not alter behavior for any
of the eleven existing adapters.
