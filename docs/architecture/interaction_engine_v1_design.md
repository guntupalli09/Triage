# Interaction Engine V1 — Architecture & Product Design

Status: design pass only. No code in this document has been implemented. Written after freezing all twelve deterministic policy adapters (Limitation of Liability, Indemnification, Termination, Confidentiality, Assignment, Governing Law, Data Security, IP Ownership, Insurance, Payment Terms, Warranties, SLA).

## 0. Product principle, restated

The Interaction Engine does not determine what a contract means. It detects when two or more **independently established, structured facts or policy decisions** — each already produced by a frozen, deterministic adapter — stand in a relationship that the lawyer's own Playbook has configured as worth flagging.

The existing safety boundary extends, it does not bend:

```
Extract facts -> evaluate individual policies -> evaluate configured interactions -> surface evidence -> abstain when unresolved
```

Never: "LLM reads the whole contract and guesses a legal interaction." No LLM participates in interaction *evaluation*. (Where AI-assisted extraction already exists per-adapter — Phase 3 — it stays exactly where it is: proposing individual clause facts for a lawyer to verify, never proposing or judging an interaction.)

---

## 1. Inventory of structured outputs

All twelve adapters share one machine-checkable contract, defined once in `policy_engine_core.py` and never duplicated:

```
extract_*_facts(text) -> *Facts (dataclass, clause_found: bool, ...)
evaluate_*_policy(facts, policy, source=None) -> PolicyDecision
```

`PolicyDecision` (`policy_engine_core.py:363`) is the single output shape every adapter returns, and it is already exposed outside the adapter in exactly one place per production review — see §1.3.

### 1.1 The shared `PolicyDecision` shape

```
rule_id: str                          # e.g. "POLICY_LOL_CAP", "POLICY_SLA"
clause_type: str                      # e.g. "limitation_of_liability"
state: str                            # ACCEPT | ACCEPT_WITH_NOTE | NEGOTIATE |
                                       # MUST_REDLINE | PROHIBITED | ESCALATE |
                                       # REQUIRES_REVIEW | NOT_APPLICABLE
contract_language: str                # verbatim excerpt
extracted_summary: str                # human-readable fact summary (free text)
policy_limit_summary: str             # human-readable policy summary (free text)
required_action: str
explanation: str
negotiation_ladder: List[LadderStep]
category_treatments: List[Dict]       # {category, treatment, cap_summary, raw_excerpt, established}
unresolved_facts: List[str]
start_index / end_index: Optional[int]
escalate_to: Optional[str]
fallback_text: Optional[str]
source: Optional[str]
controlling_provision: Optional[Dict] # {label, excerpt, start_index, end_index}
our_position / counterparty_position: Optional[Dict]  # {role, summary}
reconciliation: Optional[str]
summary_label / our_position_label / counterparty_position_label: str
```

Every adapter's `.as_dict()` output is byte-identical in shape. This uniformity is the single most important fact for this design: **the Interaction Engine does not need twelve different adapters to expose twelve different things — it needs one thing, twelve times.**

### 1.2 `category_treatments`: the accidental cross-adapter contract

Several adapters already emit `category_treatments` keyed by a **shared vocabulary of risk categories** — not by design intent (no adapter imports another), but because both the Limitation of Liability and Indemnification adapters modeled the same real-world carve-out categories independently and landed on the same strings:

| Category key | Liability (`category_treatments[].treatment`) | Indemnification (`category_treatments[].treatment`) |
|---|---|---|
| `ip_infringement` | `uncapped \| super_cap \| within_general_cap \| not_addressed \| unresolved` | `covered \| excluded \| not_addressed \| unresolved` |
| `data_breach` | same as above | same as above |
| `confidentiality` | same as above | same as above |
| `gross_negligence` | same as above | same as above |
| `willful_misconduct` | same as above | same as above |

This is confirmed at the regex level (`liability_policy_engine.py:84-91`, `indemnification_policy_engine.py:61-70` both anchor `ip_infringement`/`data_breach` on the same category keys). It means a rule like "IP infringement excluded from liability cap AND IP infringement indemnity exists" can be evaluated by **string-matching two already-serialized `category_treatments` lists** — no new extraction, no reparse, no new fact model. This is the single strongest piece of evidence that a V1 is buildable now rather than after further foundational work.

Warranties uses an *adjacent but differently-named* category (`non_infringement`, one of ten fixed `WARRANTY_CATEGORIES`) for the same real-world concept. This is a naming gap, not a missing fact — see §3.9.

### 1.3 Where `PolicyDecision` is actually visible outside its own adapter today

There is exactly **one production call site** that runs all twelve adapters against one contract review and holds all twelve `PolicyDecision` objects in memory at the same time: `policy_enforcement.evaluate_active_policies()` (`policy_enforcement.py:222-273`).

```python
for clause_type in pa.CLAUSE_TYPES:            # fixed, deterministic order, all 12
    position = active_positions.get(clause_type)
    if position is None:
        continue
    rule = pa.build_policy_rule_for_enforcement(position)
    extract_fn, evaluate_fn = pa._ENGINE_FUNCS[clause_type]
    facts = extract_fn(contract_text)
    decision = evaluate_fn(facts, rule, source=...)
    outcomes.append(ClauseEvaluationOutcome(clause_type, decision, revision_metadata))
```

This generalizes correctly across all twelve adapters (not just liability — that is a separate, older, legacy-only code path, `apply_liability_policy`, kept for the pre-migration rollback switch). `evaluate_active_policies` already:

- evaluates every clause type with an ACTIVE policy against the same contract text, in the same request;
- returns a list (`ClauseEvaluationOutcome`) carrying `clause_type`, `decision` (or `None` on a caught, isolated exception), and `revision_metadata` (the pinned `policy_position_id` + `config_hash` + `activated_at` — see §1.4);
- isolates one adapter's exception from every other adapter (never fabricates a decision for a broken clause type);
- is called exactly once per review, from exactly one place (`apply_active_policies`, called by `apply_policies_for_review`, called by `main.py`).

**This is the correct integration point for V1.** The Interaction Engine does not need a new pass over the contract, a new call into any extractor, or any new database read beyond what this function already assembles. It needs to run *after* this loop finishes, over its output.

### 1.4 What is NOT currently exposed (facts trapped inside adapters)

`PolicyDecision` intentionally does not carry raw numeric values — `extracted_summary`/`policy_limit_summary`/`cap_summary` are pre-formatted human strings ("2× fees paid in the preceding 12 months", "$2,000,000 per occurrence"). The underlying `*Facts` objects (`CapExpression`/`CapValue` in liability, `CoverageRequirement.per_occurrence_limit` in insurance, `SeverityTarget.response_hours` in SLA, etc.) hold the real floats, but those objects are constructed and discarded inside `evaluate_active_policies`'s loop body — never returned, never serialized, never stored on `Contract`.

This matters for exactly the interactions in §3 that require a *magnitude* comparison ("exposure materially exceeds insurance coverage") rather than a *category* comparison ("this category is uncapped"). Those are marked `NEEDS_SMALL_OUTPUT_EXTENSION` below — the fix is not new parsing, it is exposing a handful of already-computed floats that currently get thrown away.

### 1.5 Full per-adapter catalog

<details>
<summary>Liability, Indemnification, Termination</summary>

**Liability** (`liability_policy_engine.py`) — `LiabilityFacts`: `clause_found`, `provisions: List[Provision]`, `controlling_provision`, `reconciliation` (`single|amendment_resolved|consistent_duplicate|unreconciled`). Each `Provision`: `general_cap_expression: CapExpression` (`structure`, `components: List[CapValue]` each with `kind: fee_multiplier|fixed_amount|unlimited`, `basis: FEES|PURCHASE_PRICE|CONTRACT_VALUE|FIXED_AMOUNT|OTHER|UNRESOLVED`, `multiplier`, `fixed_amount`), `category_treatments: Dict[str, CategoryTreatment]` (categories: `data_breach, ip_infringement, confidentiality, indemnification, fraud, gross_negligence, willful_misconduct`; treatment: `uncapped|super_cap|within_general_cap|not_addressed|unresolved`), `party_positions: Dict[str, PartyPosition]` (side-resolved), `cross_reference: Optional[Dict]`. `PolicyRuleLike`: multiplier thresholds, `prohibit_unlimited`, `required_exceptions_json`, consequential-damages fields.

**Indemnification** (`indemnification_policy_engine.py`) — `IndemnificationFacts`: `clause_found`, `obligations: List[IndemnityObligation]` (no single-cap reconciliation — several directional obligations coexist by design). Each obligation: `indemnifying_role/side`, `indemnified_role/side`, `trigger_treatments: Dict[str, TriggerTreatment]` (triggers: `ip_infringement, data_breach, confidentiality, negligence, gross_negligence, willful_misconduct`; treatment: `covered|excluded|not_addressed|unresolved`), `scope` (`third_party_only|includes_first_party|...`), `defense_control`, `monetary: MonetaryTreatment` (`kind: multiplier|fixed|unlimited|cross_reference|not_stated`), `is_mutual_reciprocal`, `asymmetry_reasons`. `PolicyRuleLike`: `required_protection_triggers_json`, `prohibited_exposure_triggers_json`, `require_exposure_third_party_only`, `require_defense_control_for_exposure`, `prohibit_uncapped_exposure`, exposure multiplier thresholds.

**Termination** (`termination_policy_engine.py`) — `TerminationFacts`: `clause_found`, `rights: List[TerminationRight]`, `survival_topics: Dict[str, SurvivalTreatment]` (topics include `limitation_of_liability` and `indemnification` — a direct textual cross-reference to two other clause types), `fee: TerminationFee`. Each right: `holder_role/side`, `trigger_type` (`convenience|material_breach|insolvency|non_payment|automatic`), `notice_period_days`, `cure_period_days`, `immediate: bool`, `is_mutual`, `asymmetry_reasons`. `PolicyRuleLike`: `require_mutual_convenience_termination`, `min_notice_days_against_us`, `min_cure_days_against_us`, `prohibit_immediate_termination_for_cause`, `required_survival_topics_json`, fee thresholds.

</details>

<details>
<summary>Confidentiality, Assignment, Governing Law</summary>

**Confidentiality** — `ConfidentialityFacts.obligations: List[ConfidentialityObligation]`: `protecting_role/side`, `protected_role/side`, `exclusions_present: Dict[str,bool]` (4 fixed topics: `public_knowledge, independently_developed, third_party_rightful, required_by_law` — no personal-data-specific field), `standard_of_care`, `duration_years`/`duration_perpetual`, `is_mutual`, `asymmetry_reasons`. `PolicyRuleLike`: `required_exclusions_json`, `min_protection_duration_years`, `max_exposure_duration_years`, `require_mutual_confidentiality`.

**Assignment** — `AssignmentFacts.restrictions: List[AssignmentRestriction]`: `restricted_role/side`, `consent_required`, `consent_standard` (`sole_discretion|reasonable|not_stated`), `exceptions_present: Dict[str,bool]` (`affiliate, change_of_control, merger_acquisition`), `is_mutual`, `asymmetry_reasons`. `PolicyRuleLike`: `required_exceptions_json`, `prohibit_sole_discretion_consent`, `require_consent_for_counterparty_assignment`.

**Governing Law** — `GoverningLawFacts` (single object, non-directional): `jurisdiction`, `venue`, `dispute_resolution` (`litigation|arbitration|mediation_then_arbitration|not_stated`), `jury_trial_waived`. `PolicyRuleLike`: `preferred/acceptable/prohibited_jurisdictions_json`, `required_dispute_resolution`, `require_jury_trial_waiver`.

</details>

<details>
<summary>Data Security, IP Ownership, Insurance</summary>

**Data Security** — `DataSecurityFacts`: `role_attributions: Dict[str,set]` (controller/processor), `role_conflict`, `subprocessor_treatment` (`unrestricted|notice|consent|prohibited`), `breach_notification_hours`, `breach_without_undue_delay`, `transfer_mechanism` (`scc|adequacy|prohibited|unaddressed_transfer`), `data_residency_region`, `deletion_or_return_required`, `retention_days`, `audit_rights`, `security_standard`, `confidentiality_of_personal_data: Optional[bool]`, `dpa_cross_reference`, `liability_cross_reference` (this adapter *notices* a reference to Limitation of Liability but deliberately never re-evaluates it — an explicit precedent for "note the reference, don't reparse the other clause"). `PolicyRuleLike`: `require_processor_role`, subprocessor/breach-notification/transfer/residency/retention/audit/certification/cooperation/confidentiality requirements.

**IP Ownership** — `IPFacts`: `ownership_attributions: Dict[category, Dict[party,bool]]` (categories: `background_ip, work_product, customer_materials, vendor_technology`), `ownership_conflict_categories`, `joint_ownership_categories`, `work_product_includes_background_ip` (sweep-in conflict detector), `exclusivity`, `royalty`, `duration`, `revocability`, `sublicensable`, `transferable`, `territory`, `derivative_works_permitted`, `infringement_remedy_referenced`, `post_termination_survival`, `sow_cross_reference`. `PolicyRuleLike`: 14 `require_*`/`prohibit_*` booleans covering ownership direction, license terms, and remedy reference.

**Insurance** — `InsuranceFacts.coverages: Dict[str, CoverageRequirement]` (types: `cgl, professional_liability, cyber_liability, workers_comp, employers_liability, auto_liability`). Each `CoverageRequirement`: `established`, `per_occurrence_limit: Optional[float]`, `aggregate_limit: Optional[float]`, `limit_conflict`, `basis_ambiguous`, `obligated_party_attributions`, `obligated_party_conflict`. Plus `additional_insured_required`, `waiver_of_subrogation_required`, `notice_of_cancellation_days`, `claims_made_or_occurrence`, `schedule_cross_reference`. No cross-reference field to Liability exists on this adapter (unlike Data Security's `liability_cross_reference`) — any Liability↔Insurance comparison is necessarily external to both adapters.

</details>

<details>
<summary>Payment Terms, Warranties, SLA</summary>

**Payment Terms** — `PaymentFacts`: `payment_direction_attributions`, `net_days`, `payment_trigger` (`invoice|receipt|acceptance|milestone`), `dispute_right_present`, `dispute_notice_days`, `undisputed_amounts_still_payable`, `disputed_amounts_withholdable`, `late_fee_rate_percent`, `setoff_permitted`, `price_increase_*` fields, `tax_responsibility_attributions`, `currency`, `refund_entitlement_present`, `service_credit_present` (deliberately shallow, presence-only — see §3.8). No termination-trigger or exclusive-remedy fields exist on this adapter at all.

**Warranties** — `WarrantiesFacts.categories: Dict[str, WarrantyCategoryFacts]` (10 fixed categories: `authority, compliance_with_law, professional_workmanlike, conformity_to_documentation, non_infringement, malware_free, security, performance, title, third_party_rights` — note `non_infringement`, not `ip_infringement`), each with `established/negated/conflict`, `warranting_party_attributions`, `established_mutually`. Plus `exclusive_remedy_present`, `repair_replace_reperform_present`, `refund_credit_remedy_present`, `as_is_disclaimer_present`, `warranty_survival_present`, `schedule_cross_reference`. No termination-trigger fields (only `warranty_survival_present`, i.e. survival past termination, not a trigger of it).

**SLA** — `SLAFacts`: availability (`uptime_percent`, `measurement_period`, 4 maintenance-exclusion booleans), severity (`severity_targets: Dict[level, SeverityTarget]` with independent `response_hours/basis` and `restoration_hours/basis`, `severity_ambiguous_labels`), remedy (`service_credit_present`, `credit_trigger_present`, `credit_percent`, `credit_basis`, `credit_cap_percent`, `cumulative_credit_schedule_present`, `claim_deadline_days`, `chronic_failure_present`, `termination_right_present`, `exclusive_remedy_present`). This is the richest remedy-mechanics fact set of the twelve adapters, and by explicit prior design decision (`docs/architecture/sla_adapter_design.md` §7/§8) it is never cross-imported with Payment Terms — the two adapters' `service_credit_present` booleans are independent observations of possibly-the-same real-world mechanism, deliberately left for the Interaction Engine to reconcile.

</details>

### 1.6 Summary: what today's architecture already gives V1 for free

1. One deterministic function (`evaluate_active_policies`) that already produces all twelve `PolicyDecision`s for one contract review, in one place, in a fixed order, with per-adapter failure isolation.
2. A category-treatment vocabulary that already overlaps meaningfully across Liability, Indemnification, and (with a naming translation) Warranties.
3. A revision-pinning mechanism (`config_hash_for_position`, `policy_revision_metadata_json`) already proven for exactly the "did the input change since this decision was made" question — see §7.
4. A `Verify` replay mechanism (`verify_policy_finding`) already proven for "does re-running the deterministic engine against the pinned inputs reproduce the same result" — the direct template for an interaction-level `verify_interaction_finding`.
5. A review-queue model (`review_queue.py`) that already cleanly separates PASSED / EXCEPTION / NOT_APPLICABLE / EVALUATION_ERROR by construction, not by inference — ready to grow a fourth bucket.
6. An adapter-owned extension-point precedent (`playbook_authoring._ADAPTER_ACTIVATION_VALIDATORS`, added for SLA) proving the codebase already tolerates one clause type registering additional validation logic without touching the other eleven — the same additive-registration pattern this design proposes for interaction rules.

None of this needed to be built for the Interaction Engine. It was built, independently, for other reasons, and happens to be exactly the substrate the Interaction Engine needs. This is the strongest argument in this document for **not** treating V1 as a foundational rewrite.

---

## 2. The interaction model

### 2.1 Proposed shape (validated against the codebase, not assumed)

```python
@dataclass
class InteractionRule:
    interaction_id: str                      # "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"
    label: str                                # lawyer-facing name
    participating_clause_types: Tuple[str, ...]   # 2+, order-independent
    kind: str                                 # "CONFLICT" | "DEPENDENCY" | "IMPACT_WATCH" — see S4
    required_decision_fields: Dict[str, Tuple[str, ...]]  # clause_type -> field paths this rule reads
    predicate: Callable[[Dict[str, PolicyDecision]], InteractionOutcome]  # pure, deterministic
    explanation_template: str
    required_action_template: str
    default_state: str                        # ESCALATE | NEGOTIATE | REQUIRES_REVIEW | ACCEPT (rule's own ceiling)
    escalation_approval_authority_field: Optional[str]  # which participating clause's escalation authority governs, if any
```

This validates cleanly against the codebase with three adjustments from the sketch in the prompt:

- **`required_facts` becomes `required_decision_fields`, scoped to `PolicyDecision`, not raw `*Facts`.** Per §1.3/§1.4, the only thing consistently available across all twelve adapters at the interaction layer is the serialized `PolicyDecision`. A rule that needs a raw `*Facts` field (e.g., `CoverageRequirement.per_occurrence_limit`) needs that field promoted onto `PolicyDecision` first (§1.4, §3) — the rule itself never reaches back into an adapter's internals. This is the same "no second evaluation implementation" discipline `policy_enforcement.py`'s own docstring insists on for its own callers.
- **`resulting state` is a ceiling, not a fixed value**, matching how every existing adapter already treats `escalation_approval_authority`/`fallback_text`: the rule declares the worst state it can produce (e.g. `ESCALATE`), and the actual state is the worse of that ceiling and whatever the two participating decisions individually indicate is unresolved (mirrors the existing `_worse()` combiner pattern already independently implemented in `indemnification_policy_engine.py`, `termination_policy_engine.py`, etc. — promote it once into `policy_engine_core.py` rather than reinventing it a thirteenth time).
- **`evidence references` are not a new field** — they are the participating `PolicyDecision.controlling_provision` dicts (already carrying `label`, `excerpt`, `start_index`, `end_index`), collected by clause type. No new evidence storage format is needed; see §6.

### 2.2 Two-clause vs. N-clause

`participating_clause_types` is a tuple, not a pair, from the start. The predicate function signature (`Dict[str, PolicyDecision] -> InteractionOutcome`) is already N-ary — a 3-clause rule (Liability × Data Security × Insurance) is not a special case, it is the general case with `len(participating_clause_types) == 2` as the common instance. This costs nothing to design in from the start and avoids a second schema later.

### 2.3 What an `InteractionRule` is NOT

It is not a second `PolicyRule`/`PolicyPosition`. It does not have its own `*Facts` dataclass, because it extracts nothing from contract text — its only inputs are other adapters' already-computed `PolicyDecision` objects. It is not evaluated by an LLM. It is not stored per-playbook as free-configuration the way a `*PolicyRuleLike` Protocol is (see §8 for the authoring model, which is deliberately narrower).

---

## 3. Interaction catalog — classified against real structured facts

Each candidate below is checked against the actual field inventory in §1.5, not against what would be convenient.

### 3.1 Liability × Indemnification

| Candidate | Classification | Basis |
|---|---|---|
| Indemnification exposure covers a category Liability marks `uncapped`/`super_cap` (matches the flagship IP example) | **READY_FROM_STRUCTURED_FACTS** | `liability.category_treatments[cat].treatment` and `indemnification.category_treatments[cat].treatment` share category keys (`ip_infringement`, `data_breach`, `confidentiality`, `gross_negligence`, `willful_misconduct` — confirmed identical regex-anchored vocabulary, §1.2). No numeric comparison needed — only a category/treatment match. |
| Indemnification exposure is subject to Liability's *general* cap (i.e. Liability treats the category `within_general_cap` or `not_addressed` while Indemnification exposure is `covered`) | **READY_FROM_STRUCTURED_FACTS** | Same fields, opposite branch — the interaction fires as a `DEPENDENCY` (see §4) rather than a `CONFLICT`: it does not mean something is wrong, it means the lawyer should know indemnification liability rides inside the general cap, which changes how "uncapped indemnity" claims should be read elsewhere in negotiation. |
| Indemnification treatment ambiguous relative to cap | **READY_FROM_STRUCTURED_FACTS** | Either decision's own `unresolved_facts`/`treatment == "unresolved"` is itself the signal — the Interaction Engine does not need to invent ambiguity detection, it inherits it from the two adapters' own abstention states (§4.2). |

### 3.2 Liability × Insurance

| Candidate | Classification | Basis |
|---|---|---|
| A category Liability treats `uncapped`/`super_cap` has **no** corresponding Insurance coverage established at all | **READY_FROM_STRUCTURED_FACTS** | `liability.category_treatments[cat].treatment in (uncapped, super_cap)` plus a category→coverage-type mapping (`data_breach`→`cyber_liability`, `ip_infringement`→ no direct insurance product, so this pair is scoped to categories with a real mapping) against `insurance.category_treatments[coverage_type].established`. Presence-only; no magnitude needed. |
| Contractual exposure **materially exceeds** the configured insurance limit | **NEEDS_SMALL_OUTPUT_EXTENSION** | Requires a raw numeric liability cap value (normalized to a dollar amount, which today only exists inside `CapValue.fixed_amount`/`multiplier` × the contract's annual-fee figure, never surfaced on `PolicyDecision`) compared against `CoverageRequirement.per_occurrence_limit`/`aggregate_limit` (also never surfaced). The fix is additive: a small numeric fields block on `PolicyDecision` (e.g. `numeric_facts: Dict[str, float]`, populated only by adapters that have a genuine number to offer), not new parsing. |

### 3.3 Liability × Data Security × Insurance

| Candidate | Classification | Basis |
|---|---|---|
| Data breach receives special liability treatment while cyber insurance sits at a different (lower) coverage position | **NEEDS_SMALL_OUTPUT_EXTENSION** | Same numeric gap as §3.2 (liability magnitude vs. insurance limit) plus Data Security's `clause_found`/`role_conflict` as a presence gate for whether the data-security obligations exist at all (that half is already `READY`). The three-clause shape is not itself the obstacle — the missing numeric extension is the only blocker, and it is the *same* extension as §3.2, not a separate one. |

### 3.4 IP × Indemnification × Liability

| Candidate | Classification | Basis |
|---|---|---|
| IP infringement indemnity exists AND IP claims receive uncapped/special liability treatment | **READY_FROM_STRUCTURED_FACTS** | This is the exact worked example from the prompt (§6 below) and from §3.1 — `ip_infringement` is a shared category key across both adapters. This is the single strongest, most defensible V1 launch rule: two adapters, one shared vocabulary term, zero numeric extension, zero new extraction. |

### 3.5 Confidentiality × Data Security

| Candidate | Classification | Basis |
|---|---|---|
| Personal-data confidentiality obligations "differ materially" from general confidentiality treatment | **NOT_SAFE_FOR_V1** | Confidentiality has **no personal-data-specific field at all** (its `exclusions_present` covers `public_knowledge, independently_developed, third_party_rightful, required_by_law` — none are personal-data-specific). Data Security's `confidentiality_of_personal_data` is a bare presence boolean with no comparable "duration"/"standard of care" shape to diff against Confidentiality's `duration_years`/`standard_of_care`. "Differ materially" is not a deterministic predicate over these two fact sets as they exist today — it would require the Interaction Engine to invent a legal judgment about materiality that neither adapter's structured output supports. **Recommended V1 substitute** (a `DEPENDENCY`, not the stated `CONFLICT`): if Data Security's `confidentiality_of_personal_data` is `True` and no Confidentiality clause is active at all (`clause_found == False` or no ACTIVE position), flag for review. That is a presence check the facts genuinely support; the "differ materially" comparison is not, and should not be built as if it were. |

### 3.6 Payment Terms × Termination

| Candidate | Classification | Basis |
|---|---|---|
| Non-payment termination rights conflict with dispute/withholding mechanics | **READY_FROM_STRUCTURED_FACTS** | `TerminationRight.trigger_type == "non_payment"` gates applicability directly; its `notice_period_days`/`cure_period_days`/`immediate` are directly comparable to `payment_terms.dispute_notice_days`/`disputed_amounts_withholdable`/`undisputed_amounts_still_payable`. A conflict fires when Termination permits immediate/short-notice termination for non-payment while Payment Terms independently establishes a right to withhold *disputed* amounts without cure — the counterparty could terminate for non-payment of an amount the contract itself says was properly disputed and withheld. Both fact sets already carry everything needed; no numeric extension. |

### 3.7 SLA × Termination

| Candidate | Classification | Basis |
|---|---|---|
| Repeated SLA failure establishes (or conflicts with) a termination entitlement | **NEEDS_SMALL_OUTPUT_EXTENSION** | `SLAFacts.chronic_failure_present`/`termination_right_present` are presence-only booleans local to the SLA clause. `TerminationFacts.rights[].trigger_type` enum (`convenience|material_breach|insolvency|non_payment|automatic`) has **no value representing "SLA/service-level failure"** — so there is no way today to confirm the master Termination article's rights list actually reflects what the SLA clause independently claims. The safe extension is small (one new `trigger_type` value, `sla_failure`, recognized by `termination_policy_engine.py`'s own existing extraction — not a new adapter, one more regex branch in an existing one) rather than a reparse. Until that lands, this pair should ship, if at all, as an unconditional `DEPENDENCY` flag ("SLA establishes a chronic-failure concept — confirm the termination article is consistent with it") rather than a resolved `CONFLICT`, because the facts cannot currently support telling the two apart. |

### 3.8 SLA × Payment Terms

| Candidate | Classification | Basis |
|---|---|---|
| SLA service-credit mechanics interact with separately established payment-credit treatment | **READY_FROM_STRUCTURED_FACTS**, but only at presence-consistency depth | `sla.service_credit_present` and `payment_terms.service_credit_present` are both real, already-extracted booleans. This is *exactly* the case anticipated by the SLA adapter's own design doc decision #4 ("SLA credits vs Payment Terms credits: don't merge them... Later the Interaction Engine can reconcile them"). The correct V1 behavior is a `DEPENDENCY` — "both clauses reference service credits; confirm they describe one consistent mechanism" — never a numeric `CONFLICT`, because Payment Terms deliberately never extracts the percentage/basis/cap (that is SLA's job by design, not a gap to fill). Building this as a `CONFLICT` would mean re-litigating a decision already made deliberately in the SLA design pass; it stays a `DEPENDENCY` by design, not by current limitation. |

### 3.9 Warranties × Liability / Indemnification

| Candidate | Classification | Basis |
|---|---|---|
| Warranty remedy/exposure participates in the same IP-risk reasoning as §3.1/§3.4 | **NEEDS_SMALL_OUTPUT_EXTENSION** | Warranties' category taxonomy uses `non_infringement` where Liability/Indemnification use `ip_infringement` — the same real-world concept, different string. The fix is a one-line, explicitly-declared category-name mapping table owned by the interaction rule (`{"non_infringement": "ip_infringement"}`), not new extraction and not a change to any adapter's own vocabulary (each adapter's category name is *correct* in its own context — `non_infringement` is how warranty law actually frames it). Once mapped, `warranties.categories["non_infringement"].established` and `warranties.exclusive_remedy_present` are directly comparable to Liability/Indemnification's `ip_infringement` treatment. |
| Any other Warranties × Liability/Indemnification pairing (e.g. general warranty breach vs. liability cap) | **NOT_SAFE_FOR_V1** | Warranties carries no cap/monetary concept for its own remedies (repair/replace/refund is typed, not capped in dollars) — there is no numeric or categorical bridge to Liability's cap concept outside the IP-specific mapping above. Do not generalize past the one category that actually maps. |

### 3.10 Catalog summary

| # | Interaction | Kind | Classification |
|---|---|---|---|
| 1 | IP infringement: Indemnification covers it AND Liability treats it as uncapped/super-capped | CONFLICT | READY |
| 2 | A shared category (data_breach, confidentiality, gross_negligence, willful_misconduct) shows the same Liability/Indemnification pattern as #1 | CONFLICT | READY |
| 3 | Indemnification exposure rides inside Liability's general cap | DEPENDENCY | READY |
| 4 | Either Liability or Indemnification abstains (unresolved) on a shared category | DEPENDENCY | READY |
| 5 | Liability treats a category uncapped/super-capped with no matching Insurance coverage established | CONFLICT | READY |
| 6 | Non-payment termination right vs. payment dispute/withholding mechanics | CONFLICT | READY |
| 7 | SLA and Payment Terms both reference service credits | DEPENDENCY | READY (by design, presence-depth only) |
| 8 | Warranties non-infringement ↔ Liability/Indemnification ip_infringement | CONFLICT/DEPENDENCY | NEEDS_SMALL_OUTPUT_EXTENSION (category name mapping) |
| 9 | Contractual exposure materially exceeds insurance limit (Liability×Insurance, Liability×Data Security×Insurance) | CONFLICT | NEEDS_SMALL_OUTPUT_EXTENSION (numeric facts on PolicyDecision) |
| 10 | SLA chronic failure vs. Termination trigger consistency | DEPENDENCY | NEEDS_SMALL_OUTPUT_EXTENSION (new `sla_failure` trigger_type) |
| 11 | Personal-data confidentiality "differs materially" from general confidentiality | — | NOT_SAFE_FOR_V1 as stated; presence-only substitute is READY |
| 12 | General warranty breach vs. liability cap (non-IP) | — | NOT_SAFE_FOR_V1 |

**V1 launch catalog: rules 1-7 (7 rules, all READY_FROM_STRUCTURED_FACTS, zero new extraction).** Rules 8-10 are the correctly-scoped V1.1 backlog, each needing one small, explicit, reviewable addition — not a redesign. Rules 11-12 are explicitly excluded, with the reasoning left in this document rather than silently dropped, per the standing project discipline of never relabeling a hard case to make a gate pass.

---

## 4. Three concepts, kept distinct

### 4.1 CONFLICT

Two established provisions are incompatible **under an explicitly configured interaction rule** — not under general legal principles. A `CONFLICT` always has a `default_state` ceiling of `ESCALATE` or `NEGOTIATE` (never silently `ACCEPT`) and always names which rule fired. Example: rule #1 above (IP indemnity + uncapped IP liability).

Precondition: every participating `PolicyDecision.state` is one of the "resolved" states (i.e. not `REQUIRES_REVIEW`, not an evaluation error). If any participant is itself unresolved, the interaction cannot be a `CONFLICT` — it degrades to §4.2.

### 4.2 DEPENDENCY

A decision about one provision **requires considering** another provision, without necessarily being incompatible with it. Two triggers:

- **Structural dependency**: the rule is inherently informational, not adversarial (rule #3, #7 above — "this rides inside the general cap," "both clauses reference credits, confirm one mechanism").
- **Abstention dependency**: one or more participating decisions is itself `REQUIRES_REVIEW` or an evaluation error. The Interaction Engine never resolves an interaction it cannot see both sides of — it surfaces "this interaction could not be evaluated because Indemnification's own facts were ambiguous," which is itself useful information, distinct from "no interaction was found."

`DEPENDENCY` outcomes route to `REQUIRES_REVIEW` by default (matching every existing adapter's own abstention convention) unless the rule's own `default_state` ceiling is lower (e.g. a purely informational dependency can cap at `ACCEPT_WITH_NOTE`).

### 4.3 IMPACT

A *proposed* redline/change may invalidate a previously computed interaction. This is not a third decision state alongside CONFLICT/DEPENDENCY — it is a **temporal** property of an already-computed `InteractionDecision`: has anything it depended on changed since it was computed. See §5 and §7 for the full mechanism. An `InteractionDecision` is never itself "IMPACT" — it is either current or stale; IMPACT is the *event* (an edit) that makes a decision go from current to stale, and the resulting UI state is `STALE`, not a fourth outcome kind.

---

## 5. Invalidation — what actually needs to change to invalidate

This is the section the design doc is explicitly warned to get right, and it requires distinguishing two genuinely different scenarios that the codebase already treats differently:

### 5.1 Scenario A — the Playbook's policy changes (a new PolicyPosition revision is activated)

Nothing needs "invalidating" here, by the existing revision-pinning invariant (`docs/architecture/phase4_cutover.md`, `models.py`'s `PolicyPosition` docstring): an ACTIVE row is **never mutated in place**; editing creates a new row, and `activate_position` archives the old one. Every past `Contract.policy_decisions_json` entry is permanently pinned to the exact revision that produced it (`policy_revision_metadata_json`, `config_hash_for_position`). A completed review's stored decisions — and therefore any interaction decisions computed from them — are already immutable historical record; they are not supposed to "update" when the playbook changes later, any more than a signed contract updates when the playbook does.

What *does* need to happen: `Verify` (§7.1) must be able to tell a lawyer, on demand, "this interaction decision was computed against a policy revision that is no longer the active one — replay to see if today's policy would produce the same result." This is a read-only, on-demand check, exactly mirroring `verify_policy_finding`'s existing semantics, extended to interactions.

### 5.2 Scenario B — within one contract review, a lawyer edits/accepts/rejects a redline on a finding

This is the scenario the design prompt's phrase "lawyer edits/redlines provision" actually describes, and it is **not currently a re-extraction event** anywhere in the codebase: `review_workflow`'s `review_decisions_json` records `{action, reason, edited_text, decided_at}` per finding as an override annotation. `edited_text` is free-form lawyer-authored text; nothing re-parses it, and nothing should — re-extracting arbitrary free-text redlines deterministically is exactly the kind of "fake determinism" the whole project has refused to do anywhere else (see the SLA business-hours decision, the liability reconciliation logic, etc.).

Given that constraint, the only safe invalidation behavior is: **mark, don't recompute.**

```
Original review
  -> individual policies evaluated (evaluate_active_policies, once)
  -> interactions evaluated (interaction_engine.evaluate, once, over the same decisions)
  -> lawyer takes an action (accept/edit/reject) on a policy_decision finding for clause type X
  -> every stored InteractionDecision whose participating_clause_types includes X
     is flagged NEEDS_RECONFIRMATION in review_decisions_json (additive field,
     not a new table)
  -> the review UI visually marks those interaction rows STALE and offers
     "Recompute" (re-runs interaction_engine.evaluate over the UNCHANGED
     original decisions -- this does NOT re-extract X, it re-asks "given
     everything else unchanged, does this interaction still apply," which
     is deterministic and safe) alongside "Dismiss" (lawyer has reviewed
     and the flag was a false alarm for this specific edit)
  -> nothing is silently recomputed and re-shown as if untouched; the lawyer
     always sees that something downstream needs a second look
```

This is deliberately conservative: an edit to clause X never automatically "fixes" or "breaks" an interaction — it flags every interaction touching X for human reconfirmation, because the system cannot know what the free-text edit actually changed. This is the same abstention philosophy as `REQUIRES_REVIEW` applied one layer up.

### 5.3 What "only dependent interactions invalidated" means concretely

`participating_clause_types` on `InteractionDecision` (stored, not recomputed) is the entire mechanism: invalidation is a filter (`[d for d in interactions if X in d.participating_clause_types]`), not a graph traversal, not a rerun of the full twelve-adapter pass. A contract with an edit to Governing Law never touches the Liability×Indemnification interaction's stale flag, because Governing Law never appears in that rule's `participating_clause_types`. This is exactly the "do not simply rerun everything" requirement, and it costs nothing beyond storing a tuple of strings per interaction decision — which the rule already declares statically (§2.1).

---

## 6. Evidence model

No new evidence *storage* format — the existing `controlling_provision` dict (`{label, excerpt, start_index, end_index}`) already carried by every participating `PolicyDecision` is reused directly, one per participating clause type, plus a fixed "why this matters" string generated from the rule's `explanation_template`:

```python
@dataclass
class InteractionDecision:
    interaction_id: str
    kind: str                          # CONFLICT | DEPENDENCY
    state: str                         # the resolved state after combining rule ceiling + participant states
    participating_clause_types: Tuple[str, ...]
    participating_provisions: Dict[str, Dict]   # clause_type -> controlling_provision dict (verbatim, reused)
    explanation: str                            # rendered from explanation_template
    required_action: str
    escalate_to: Optional[str]
    participating_decision_snapshot: Dict[str, Dict[str, str]]  # clause_type -> {policy_position_id, config_hash} (S7)
    stale: bool = False
    stale_reason: Optional[str] = None
```

Rendered exactly per the prompt's worked example — `render_evidence_report()` generalizes trivially:

```
Interaction requires attention

Limitation of Liability S12.2
IP infringement is excluded from the general cap.

Indemnification S9.1
Supplier indemnifies Customer for third-party IP infringement claims.

Why this matters
These independently established positions interact under your Playbook's IP-risk rule.

Required action
Legal review required.
```

Every line above is drawn from data already produced by the two adapters (`controlling_provision.label`, `.excerpt`) plus the rule's own static template text — never a generated legal conclusion, never free text an LLM wrote.

---

## 7. Determinism, verification, and audit

### 7.1 Determinism

`interaction_engine.evaluate(decisions: Dict[str, PolicyDecision], rules: List[InteractionRule]) -> List[InteractionDecision]` is a pure function — no I/O, no randomness, no LLM call, identical in spirit to `evaluate_active_policies` itself. Given the same `decisions` dict and the same `rules` list, it produces byte-identical output, checkable with the exact same `decision_hash`/`check_deterministic` pattern already in `policy_engine_core.py` (§10 benchmark design reuses this directly).

Because `decisions` is itself already required to be deterministic (each adapter's own 100%-determinism gate), and interaction rules are pure predicates over that dict, determinism composes for free — there is no new source of nondeterminism to introduce as long as no rule predicate is allowed to call anything nondeterministic (enforced by code review / a lint rule forbidding imports of `random`, `datetime.now`, or any LLM client inside `interaction_engine.py`, mirroring the existing discipline that no adapter imports an LLM client either).

### 7.2 Verify (extends `verify_policy_finding`)

```python
def verify_interaction_finding(db, contract, interaction_finding) -> Dict[str, Any]:
```

Mirrors `verify_policy_finding` exactly: for each `clause_type` in the interaction's `participating_clause_types`, look up the pinned `policy_position_id` from `Contract.policy_revision_metadata_json[clause_type]`, re-run `extract_fn`/`evaluate_fn` against `contract.contract_text` under that exact pinned revision (never today's current ACTIVE position, which may have changed — same non-negotiable rule `verify_policy_finding`'s docstring already states), collect the replayed decisions into a dict, and re-run `interaction_engine.evaluate` over just that one rule. `verified = replayed_state == original_state`. No new replay mechanism — this is the same mechanism, applied one layer up, over N decisions instead of one.

### 7.3 Audit

`AuditLog` needs no schema change. Interaction evaluation is deterministic and derived entirely from already-audited inputs (each participating `PolicyPosition`'s `policy_position_id`/`config_hash` is already in `policy_revision_metadata_json`); an `InteractionDecision` is fully reproducible from data already audited, so it does not itself need a separate append-only audit row — it needs to be **findable from** the audit trail, which `participating_decision_snapshot` (§6) already provides. The one new audit-worthy *event* is a lawyer dismissing a `NEEDS_RECONFIRMATION` flag (§5.2) — that is a human judgment call, not a deterministic computation, and follows the exact existing pattern (`review_decisions_json` entry + mirrored `AuditLog` row, same as every other review action).

---

## 8. Authoring

### 8.1 Configurable, not hardcoded

The prompt's own example — "If IP indemnity exists AND IP liability is uncapped → ESCALATE to Senior Legal Counsel" versus a universal hardcoded legal assumption — is the right question, and the codebase already answers it structurally: every one of the twelve adapters treats *whether a category is required, prohibited, or merely noted* as lawyer-configured (`required_exceptions_json`, `prohibited_warranty_categories_json`, etc.), never hardcoded. The Interaction Engine should follow the identical pattern: **the rule's existence and its predicate logic are code** (the same way "what counts as `uncapped`" is code inside `liability_policy_engine.py`, not something a lawyer types into a form), **but whether the rule is active, and what it escalates to, is playbook-level configuration** — the same separation every adapter already makes between "the deterministic logic of what a fact means" (code) and "what the firm wants done about it" (`PolicyPosition.config_json`).

### 8.2 Minimum viable authoring UX

Reuse the `_ADAPTER_ACTIVATION_VALIDATORS` precedent (§1.6 point 6) rather than inventing a parallel authoring surface:

- A new, small config surface per playbook: `InteractionRuleConfig` (one row per `interaction_id` per playbook — same shape family as `PolicyPosition`, minus the per-field extraction/evidence machinery, since an interaction rule has no text of its own to extract from): `enabled: bool`, `escalation_approval_authority_override: Optional[str]`, `severity_override: Optional[str]` (allowing a firm to downgrade a `DEPENDENCY` rule's default `REQUIRES_REVIEW` to `ACCEPT_WITH_NOTE` if they've decided it's not worth flagging, but never allowing a firm to upgrade past a `CONFLICT` rule's coded ceiling — the *existence* of the incompatibility is not configurable, only how loudly it's raised).
- **No new authoring page shape.** The existing Workbench clause-card pattern (`playbook_workbench.py`, `templates/playbook_position_edit_base.html`) generalizes directly: an "Interactions" card per playbook, listing every registered `InteractionRule`, each toggleable on/off with an optional escalation-authority override — not a twelve-field form, because an interaction rule has one real configuration surface (on/off, who to escalate to), not a whole `*PolicyRuleLike` Protocol's worth of thresholds. This is a materially smaller authoring surface than any clause adapter, by design — the rule logic itself is not something a lawyer edits, only whether it's active for this playbook.
- V1 ships with all seven catalog rules (§3.10) **enabled by default**, since none of them encode a firm-specific threshold — they encode "these two independently-established facts are worth a human look," which is true regardless of house style. A firm that genuinely never wants a specific rule can disable it explicitly and that choice is itself audited.

---

## 9. Review UX — no second application

### 9.1 Reuse `review_queue.py`'s existing three-way split, add a fourth bucket

`ReviewQueueSummary` already separates `top_tier` / `negotiate` / `requires_review` / `evaluation_error` / `passed` / `not_applicable` from clean, typed inputs (`findings` + `policy_decisions`), never from inference. The natural, minimal extension:

```python
@dataclass
class ReviewQueueSummary:
    ...  # unchanged existing fields
    interactions_needing_attention: int   # NEW
```

An `InteractionDecision` in a `CONFLICT`/`DEPENDENCY`-with-actionable-state becomes a synthetic finding with `finding_type="interaction_decision"` (parallel to the existing `finding_type="policy_decision"`, never overloading it — `build_review_queue`'s bucketing already switches on `finding_type`, so this is a third branch in an existing `if`, not new architecture). It carries the same shape as a `policy_decision` finding (`severity`, `rationale`, `escalate_to`, `evidence_report`) plus `participating_clause_types` for the row-styling hook below.

### 9.2 Matches the prompt's exact target copy, using data already computed

```
10 policy checks passed
2 clause exceptions
2 cross-policy interactions require attention
```

is `summary.passed`, `summary.needs_attention` (existing), and the new `summary.interactions_needing_attention` — three numbers, already computed, rendered in the same summary block `templates/review.html`'s `renderPanelList()` already builds (`templates/review.html:591-602`).

### 9.3 Visual distinction

Interaction rows get their own CSS class (`queue-row.is-interaction`, parallel to the existing `queue-state-badge` styling) and a distinct icon/badge (e.g. a link/chain glyph vs. the existing severity dot) — never the same row shape as an ordinary clause exception, so a lawyer scanning the queue immediately knows "this row is about a *relationship*, not a single clause." Interaction rows sort into their own section head ("Cross-Policy Interactions"), positioned between "Playbook Exceptions" and "Other Contract Findings" in `renderPanelList()` — same list, same page, no second review surface.

### 9.4 Drill-down

Clicking an interaction row opens the same finding-detail popover (`openFinding(idx)`) already used for every other finding type, rendering the evidence report from §6 verbatim (each participating provision's excerpt + section label, the "why this matters" line, the required action) — reusing the existing popover chrome entirely, adding one new content-rendering branch keyed on `finding_type === "interaction_decision"`.

### 9.5 Stale interactions (§5.2)

A `STALE` interaction row gets a third, distinct visual state (not `resolved`, not the normal actionable look) — a muted badge reading "Needs reconfirmation — {edited clause} was changed" with the two actions from §5.2 (`Recompute` / `Dismiss`) inline, never silently disappearing from the queue and never silently re-showing as if nothing happened.

---

## 10. Adversarial benchmark design

### 10.1 Corpus structure

Mirrors every existing adapter benchmark's shape (`benchmarks/run_*_benchmark.py` + a `*_corpus.py` module of hand-labeled cases) but at the **decision level, not the text level** — an interaction benchmark case is a set of pre-built `PolicyDecision` fixtures (or, for a smaller top layer, full two/three-clause contract text run through the real adapters), not raw contract prose alone. This matters: interaction correctness must be provably independent of any single adapter's own extraction quirks, so most cases should construct `PolicyDecision` objects directly (bypassing extraction) to isolate "does the interaction predicate itself behave correctly," with a smaller end-to-end subset (full contract text -> real adapters -> interaction engine) to prove the wiring, not the logic, is correct.

Required coverage (from the prompt, each mapped to a concrete construction):

| Category | Construction |
|---|---|
| True interactions | Two decisions that should trigger a `CONFLICT`/`DEPENDENCY` per §3.10's catalog |
| Apparent interactions that should NOT fire | Decisions sharing surface vocabulary but not the rule's actual predicate (e.g. `ip_infringement` present in both but Liability's treatment is `within_general_cap`, not `uncapped`) |
| Missing participating facts | One participating clause type has no ACTIVE position at all (`evaluate_active_policies` never produced a decision for it) — the rule must not fire, must not error, must report "not evaluated," never silently pass |
| Ambiguous facts | A participating decision is `REQUIRES_REVIEW` — interaction must degrade to `DEPENDENCY`/abstain, never guess a resolution (§4.2) |
| REQUIRES_REVIEW upstream decisions | Same as above, exercised explicitly per rule |
| Contradictory provisions | A single adapter's own `reconciliation == "unreconciled"` (Liability) feeding into an interaction — the interaction must inherit, not paper over, the adapter's own unresolved state |
| Three-clause interactions | Rule #9's shape (once its extension lands) exercised with all 8 combinations of which 1/2/3 participants are present |
| Amendments | A participating decision's `controlling_provision` reflects an amendment-resolved value (Liability's `reconciliation == "amendment_resolved"`) — interaction evaluates against the resolved value, never the superseded one |
| Cross-references | A participating decision's underlying facts flagged a cross-reference to an unresolved Schedule/Exhibit — same "unresolved" propagation as ambiguous facts |
| Redline invalidation | Full review lifecycle: evaluate → interactions computed → simulate an "edited" review decision on one participant → assert the interaction is flagged `NEEDS_RECONFIRMATION` and no other interaction is touched (§5.3) |
| Stale interaction prevention | A completed, stored `InteractionDecision` whose participating revision no longer matches current `config_hash` — `verify_interaction_finding` must report `verified=False` with a specific reason, never a silent pass |

### 10.2 Release gates (from the prompt, plus two additions)

- **False interaction = 0** — no case where the corpus says "should not fire" produces a fired interaction.
- **Missed configured high-risk interaction = 0** — every `CONFLICT`-kind case the corpus says should fire, fires, when the rule is enabled.
- **False-safe = 0** — reused definition from `policy_engine_core.is_false_safe`, applied at the interaction layer: a case whose correct outcome needed attention but the engine returned nothing / a `DEPENDENCY` where a `CONFLICT` was correct.
- **Determinism = 100%** — `check_deterministic`, reused verbatim, over `InteractionDecision` instead of `PolicyDecision`.
- **Stale interaction after dependent change = 0** — every redline-invalidation case correctly flags `NEEDS_RECONFIRMATION`; zero cases where a stored interaction silently continues showing pre-edit evidence as current.
- **Addition — participation-scoping precision = 100%**: an edit to clause type X never flags an interaction that does not list X in `participating_clause_types` (this is the "only dependent interactions invalidated" requirement made independently measurable, distinct from the stale-detection recall metric above).
- **Addition — abstention-propagation recall = 100%**: every case with an upstream `REQUIRES_REVIEW`/evaluation-error participant correctly degrades to `DEPENDENCY`/abstain rather than either silently skipping the interaction (false-safe-adjacent) or guessing a resolution (fabrication).

### 10.3 Corpus size

Proportional to catalog size, not a fixed target: given 7 launch rules × (true-fire, near-miss, missing-participant, ambiguous-participant, degraded-upstream) ≈ 35 minimum cases, plus the cross-cutting categories in §10.1 (invalidation, staleness, amendments, cross-references) applied to a representative subset ≈ 55-70 cases total — smaller than any single clause adapter's own corpus, appropriately, since interaction rules are narrower predicates over already-validated inputs rather than free-text extraction.

---

## 11. Architecture boundary — explicit answers, validated against code

**Should the Interaction Engine consume raw contract text?** **No.** Nothing in `evaluate_active_policies` requires it, and no candidate rule in §3 needs anything contract text can provide that `PolicyDecision` (plus the small numeric extension in §1.4) does not already carry. Consuming raw text would mean re-deriving facts a frozen adapter already derived — the exact "second evaluation implementation" `policy_enforcement.py`'s own docstring already refuses to allow for enforcement, and the same discipline applies one layer up.

**Should it call individual extractors?** **No.** `evaluate_active_policies` already calls every extractor exactly once, in one place, per review. The Interaction Engine runs *after* that loop, over its output (`List[ClauseEvaluationOutcome]`), never duplicating a call `apply_active_policies` already made.

**Should it consume normalized structured facts/decisions produced by adapters?** **Yes — this is the validated architecture.** Specifically `PolicyDecision.as_dict()` (already normalized, already uniform across all twelve adapters per §1.1), plus the small numeric-facts extension in §1.4 for the handful of rules that genuinely need a magnitude, not a category.

**Should interactions modify individual `PolicyDecision`s?** **No.** `InteractionDecision` is a fully independent, separately-typed object (§6) that *references* participating decisions (by clause type + revision snapshot) and never mutates or re-wraps them. This preserves every existing invariant `PolicyDecision`/`policy_decisions_json` already has (revision pinning, `Verify` replay, the review queue's PASSED/EXCEPTION split) without touching a single line of any of the twelve frozen adapters or the `policy_enforcement.py` orchestrator's existing behavior for single-clause decisions. `Contract` gains one new column, `interaction_decisions_json`, parallel to and independent of `policy_decisions_json` — never nested inside it.

**Integration point, stated precisely:** a new function, `interaction_enforcement.apply_interaction_rules(db, playbook, outcomes: List[ClauseEvaluationOutcome], findings_dict)`, called from `apply_policies_for_review` immediately after `apply_active_policies` returns, in `cutover` mode only (shadow/legacy modes have no multi-clause decision set to interact over, by construction — same scoping `run_shadow_comparison` already applies to liability alone). This is one new call site in one existing function, not a new orchestration layer.

---

## 12. The Kate test

> "Contracts are living, breathing documents. Changing one clause can affect several others, not merely because they cross-reference one another."

**What V1 genuinely addresses:** the specific, common, high-cost failure mode where two independently-drafted provisions create a real commercial/legal inconsistency that neither clause's own reviewer would catch in isolation — the flagship example (IP indemnity + uncapped IP liability) is a real, recurring negotiation trap, not a demo trick, and V1 catches it deterministically, with full evidence, with zero LLM guessing, the same day the twelfth adapter that makes it possible was frozen. The catalog in §3.10 is narrow by design, but every rule in it is a *documented, real* commercial risk pattern a contracts lawyer would recognize on sight, not a synthetic example invented to have something to demo.

**What V1 explicitly does NOT solve, stated plainly (not hedged):**

- **General legal judgment.** V1 never determines what a contract *means* — only whether two specific, pre-defined structured facts stand in a pre-defined relationship. A lawyer must still read the contract; V1 narrows where they need to look first.
- **Negotiation leverage.** V1 does not advise on what to ask for, what to concede, or how a specific interaction should be resolved in negotiation — only that it exists and needs attention. `required_action` says "legal review required," never "counter-propose X."
- **Stylistic consistency.** Two clauses using different but legally equivalent phrasing (e.g. "Confidential Information" vs. "Proprietary Information" meaning the same thing) is not something V1 detects or cares about — it operates on already-normalized structured facts, not on prose style.
- **Arbitrary semantic relationships.** V1 only evaluates the finite, explicitly coded catalog of rules (§3.10) a lawyer has enabled. It will never notice a genuinely novel interaction pattern no rule was written for — that is a permanent, structural limitation of a deterministic system, not a V1-specific gap to be "improved away" later without adding a new coded rule.
- **Undefined legal consequences.** V1 never states what happens *if* the interaction goes unresolved (breach exposure, unenforceability, etc.) — only that the two facts co-exist under a configured rule. That legal-consequence judgment is left entirely to the lawyer, on every single finding, without exception.

**Verdict on the Kate test:** V1 addresses a real, meaningful, and previously entirely-unaddressed slice of "contracts are living documents" — specifically, the slice where "living" means *the interaction between two clauses this tool already independently understands*, not the slice where "living" means arbitrary, novel, or stylistic cross-clause meaning. That is a legitimate, honestly-scoped product, not a demo trick — provided the UI and documentation are equally honest about the boundary (§12's own five bullet points should appear, verbatim or close to it, in whatever user-facing documentation ships with V1, not just in this design doc).

---

## Final output

1. **Proposed architecture** — §11. `InteractionRule` predicates run once per review, immediately after `evaluate_active_policies`, consuming `PolicyDecision` objects only. No raw text, no duplicate extraction, no mutation of existing decisions.
2. **Data model** — §2, §6. `InteractionRule` (code + a thin per-playbook enable/escalation-override config row), `InteractionDecision` (new, independent, `Contract.interaction_decisions_json`).
3. **Evaluation lifecycle** — §5.3, §11's integration point: `evaluate_active_policies` → `apply_interaction_rules` → findings injected exactly like existing `policy_decision` findings, one new `finding_type`.
4. **Initial interaction catalog** — §3.10: 7 launch rules, all `READY_FROM_STRUCTURED_FACTS`; 3 explicitly scoped V1.1 candidates each needing one small, named extension; 2 explicitly excluded with reasoning preserved.
5. **Authoring UX** — §8: one new small Workbench card, on/off + escalation-authority override per rule, no new per-field extraction machinery, all 7 launch rules enabled by default.
6. **Review UX** — §9: one new bucket in the existing `ReviewQueueSummary`, one new `finding_type`, reused popover, distinct row styling — no second application.
7. **Invalidation/re-evaluation model** — §5, §7: policy-revision changes never retroactively alter completed reviews (existing pinning invariant, extended to interactions via `verify_interaction_finding`); within-review redline edits mark dependent interactions `NEEDS_RECONFIRMATION`, never silently recompute or silently persist stale evidence.
8. **Benchmark design** — §10: decision-level fixtures + a smaller end-to-end subset, 6 required gates (4 from the prompt + 2 added: participation-scoping precision, abstention-propagation recall), ~55-70 cases for the 7-rule launch catalog.
9. **Security/audit implications** — §7.3: no new audit-log shape; `InteractionDecision` is fully reproducible from already-audited inputs; the one new audited event is a human dismissing a staleness flag.
10. **Implementation phases** (proposed, not committed — for the next planning pass, not this one):
    - **Phase A**: `InteractionRule`/`InteractionDecision` data model + the 7 launch-catalog predicates (all `READY_FROM_STRUCTURED_FACTS`) + promotion of the existing independently-duplicated `_worse()` combiner into `policy_engine_core.py`.
    - **Phase B**: `apply_interaction_rules` wiring into `apply_policies_for_review`, `interaction_decisions_json` column, review-queue/UI integration (§9).
    - **Phase C**: `verify_interaction_finding`, redline-invalidation marking (§5.2), stale-row UX.
    - **Phase D**: adversarial benchmark + release gates (§10), full regression against all twelve adapter benchmarks proving zero drift (identical discipline to every adapter's own §5 rerun step).
    - **Phase E (deferred, explicitly out of this design's scope)**: the three `NEEDS_SMALL_OUTPUT_EXTENSION` rules (#8-10), each requiring one small, separately-reviewed adapter change before its interaction rule can ship.
11. **Risks**:
    - A rule whose predicate is subtly wrong is now cross-cutting — it can raise or hide attention across two adapters' worth of contracts at once, so interaction rules deserve the same benchmark rigor as a full adapter, not less, despite being narrower.
    - Category-vocabulary drift: if a future adapter (or an edit to an existing one) renames a category key, an interaction rule silently stops matching with no error — needs an explicit registration-completeness-style test (mirroring the existing `test_clause_type_registration_completeness.py` precedent) asserting every interaction rule's referenced category keys still exist in its participating adapters' actual vocabularies.
    - Authoring surface creep: the temptation to let lawyers write their *own* interaction predicates (not just enable/disable coded ones) would reintroduce exactly the "guessing legal interactions" risk this design explicitly avoids — §8 authoring stays narrow on purpose, and should stay narrow past V1.
    - Redline-invalidation UX fatigue: if every minor edit flags every touching interaction, lawyers may start reflexively dismissing `NEEDS_RECONFIRMATION` flags without reading them — worth watching post-launch, not a reason to weaken the flag itself.
12. **Explicit recommendation:**

# PROCEED TO INTERACTION ENGINE V1

Scoped exactly to the 7-rule launch catalog in §3.10, using the architecture in §11, with the 3 `NEEDS_SMALL_OUTPUT_EXTENSION` rules and the excluded `NOT_SAFE_FOR_V1` candidates left explicitly deferred rather than force-fit. The evidence for this recommendation is structural, not aspirational: the review, revision-pinning, Verify-replay, and review-queue infrastructure this design leans on was not built for this task and did not need to be — it already existed, already proven, for reasons independent of the Interaction Engine, and the launch catalog's category-vocabulary overlap (§1.2) was discovered by inventory, not designed in advance. A foundational change is not required first; the foundation, largely by accident of careful prior design, is already sufficient for a genuinely narrow, genuinely honest V1.
