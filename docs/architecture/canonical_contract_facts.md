# Canonical Contract Facts (Phases 1–4 + golden SSOT)

Status: **Phase 1 schema package `contract_facts/` is implemented.
Phase 2 wires Limitation of Liability extraction → canonical facts →
LoL v2. Phase 3 assembles the Indemnification clause family
(directional obligations, shared procedure, contextual roles, §6.3
cross-clause linkage separate from monetary). Phase 4 feeds structured
`ContractDocumentFacts` into the Interaction Engine and implements the
vendor-indemnity-inside-general-cap interaction. Commercial extract +
ACV provenance + downstream consumer cutover + production-path golden
E2E close the Liability + Indemnification single-source-of-truth path.**

This document defines the authoritative **contract-side** representations
that TriageCounsel will use after the post-E2E forensic audit. It is the
companion to `policy_grammar/` (policy-side) and deliberately does **not**
migrate generic rules in Phase 1–3.

---

## 1. Why this exists

The forensic audit proved TriageCounsel currently has **multiple independent
parsers** over the same contract language (liability extractor, LoL v2 bridge,
indemnification extractor, clause_quality inspectors, rules_engine rules,
payment-term heuristics, redline templates). Symptoms such as:

- six-month fee-period cap → “could not be normalized for v2 comparison”
- §6.3 “limitations apply to indemnification” → indemnity `REQUIRES_REVIEW`
- “EITHER PARTY” consequential waiver → one-sided redline
- inspector IP present / adapter IP missing

share one architectural cause: **no shared contract-side fact layer**.

Phase 1 defines that layer. Later phases populate it and make consumers
read it.

---

## 2. Authority boundary

| Concern | Source of truth | Package |
|---|---|---|
| What the **contract** says (caps, triggers, roles, payment due, cross-clause links) | `ContractDocumentFacts` | `contract_facts/` |
| What the **approved playbook** requires | `PolicyPosition` / `LiabilityPolicyV2` / adapter policy rules | `policy_grammar/`, `playbook_authoring`, engines |
| Generic pattern findings outside these families | `RuleEngine` findings (until a later migration) | `rules_engine.py` |
| Human explanations | LLM explanation layer (must not change deterministic state) | `evaluator.py` |

**Invariant:** once a fact family is represented in `contract_facts`, no
downstream consumer may re-derive that fact from raw text for decisioning.
Re-parsing for *discovery candidates* is allowed only if admission writes
into these types.

---

## 3. Core primitives

### `Presence`

`PRESENT` | `ABSENT` | `UNKNOWN`

- `UNKNOWN` is first-class.
- Inspectors/rules must not coerce “not detected” → `False`.
- Evaluation maps `UNKNOWN` on a decision-critical fact → `REQUIRES_REVIEW`.

### `EvidenceSpan`

Absolute `start_index` / `end_index` + `excerpt` + optional `section_label`.
Provenance travels with the fact; it is not reconstructed later from strings.

### `EstablishedFact[T]`

`presence` + optional `value` + optional `evidence` + `unresolved_reason`
when `UNKNOWN`. Enforced invariants:

- `PRESENT` ⇒ value required
- `ABSENT` / `UNKNOWN` ⇒ value must be `None`
- `UNKNOWN` ⇒ reason required

---

## 4. Domain schemas

### Liability — `ContractLiabilityFacts`

- General cap is `EstablishedFact[policy_grammar.CapExpression]`.
- **Fee-period caps are first-class** via `FeeRelativeCap` (same operand
  policy v2 already understands). No more contract-side `CapValue` that
  only knows `fee_multiplier` / `fixed_amount` / `unlimited`.
- Category treatments use `CategoryTreatmentKind` including
  `within_general_cap` (the §6.3 case).
- Mutuality and consequential-damages exclusion are `EstablishedFact`s
  with `UNKNOWN` possible.
- `category_treatments_for_interactions()` exposes the list shape
  `interaction_rules` already consumes.

### Indemnification — `ContractIndemnificationFacts`

- Directional `IndemnityObligationFacts` (indemnifying → indemnified).
- Per-obligation triggers, claim scope, monetary treatment.
- **`SharedProcedure`** referenced by `procedure_id` so §5.3 attaches to
  both §5.1 and §5.2 without independent re-parse.
- `MonetaryKind.CROSS_REFERENCE` means monetary delegation only.

### Roles / procedure — `DocumentRoleModel`, `RoleBinding`, `SharedProcedure`

- Contextual roles (`indemnifying_party`, etc.) bind to named parties.
- `DefenseControl.binds_to_indemnifying_party()` returns `Presence`, not bool.

### Commercial — `ContractCommercialFacts`

- Annual fees / currency / billing / payment due / invoice trigger.
- `PaymentDueTerms` carries days **and** basis (`invoice_receipt`, `net`, …)
  so “payable within thirty (30) days after receipt” is representable.
- Distinct from reviewer `deal_value` on `EvaluationContext`.

### Cross-clause — `CrossClauseGraph`

- `CrossClauseKind.LIABILITY_APPLIES_TO_INDEMNIFICATION` is the correct home
  for §6.3-style language.
- Storing that relationship as indemnity monetary `cross_reference` is
  **forbidden** by this design (documented in `MonetaryKind` docstring).

---

## 5. Aggregate

`ContractDocumentFacts` holds roles, commercial, liability,
indemnification, and cross_clause under `schema_version = 1`.

---

## 6. Explicit non-goals (Phase 1–4)

1. Do **not** migrate the 189 generic rules onto these types.
2. Do **not** delete legacy `CapValue` / `IndemnityObligation` dataclasses yet —
   dual-running continues; bridges map legacy → canonical.
3. Do **not** convert fee-period months into money or `months/12` multipliers
   when symbolic comparison is possible.
4. Phase 4 does **not** re-parse raw text inside interaction predicates —
   assembly happens upstream from outcome-carried extracts.

---

## 7. Phase 2 delivered (liability)

1. **`CapValue.kind == "fee_period"`** — `_find_cap_values` recognizes duration
   and trailing fee-period language in the full provision window; evidence
   spans the component, not a heading truncate.
2. **`contract_facts.liability_bridge`** — legacy `LiabilityFacts` →
   `ContractLiabilityFacts` → LoL v2 `ContractCapFacts` without excerpt re-parse
   when components are present.
3. **ACV provenance** — `AcvSource` + `resolve_annual_contract_value`:
   reviewer `deal_value` ≻ contract `annual_fees`; trailing-period fees never
   become ACV.
4. **LoL v2 consumer** — `policy_enforcement._evaluate_lol_v2_position` prefers
   canonical caps and forwards category treatments from the bridge.

## 7b. Phase 3 delivered (indemnification clause-family)

1. **Bounded attribute windows** — directional obligations clip at the next
   numbered subsection so §5.1 triggers do not bleed into §5.2.
2. **Shared procedure** — §5.3 discovered once (`SharedProcedureRecord`) and
   attached via `procedure_id` to both Provider→Customer and Customer→Provider
   obligations; `will` control-defense / cooperate recognized.
3. **IP enumeration** — patent/copyright/trademark infringement maps to
   `ip_infringement`.
4. **§6.3 separated from monetary** — "limitations apply to Section 5" becomes
   `liability_applies_links` / `CrossClauseKind.LIABILITY_APPLIES_TO_INDEMNIFICATION`;
   "subject to this Section 5" procedure scope is not `monetary.cross_reference`.
5. **`contract_facts.indemnification_bridge`** — legacy →
   `ContractIndemnificationFacts` + `DocumentRoleModel` + `CrossClauseGraph`.

## 7c. Phase 4 delivered (cross-policy interactions)

1. **`document_assembly`** — `assemble_document_facts_from_legacy` builds
   `ContractDocumentFacts` from liability + indemnification adapter extracts
   already computed during `evaluate_active_policies` (`ClauseEvaluationOutcome.legacy_facts`).
2. **`interaction_hydration`** — before gating, empty/lossy
   `PolicyDecision.category_treatments` are merged from canonical facts,
   including synthesizing liability `indemnification` → `within_general_cap`
   from controlling carve-outs or §6.3 `LIABILITY_APPLIES_TO_INDEMNIFICATION`.
3. **Rule 3 `IX_INDEMNITY_WITHIN_GENERAL_CAP`** — family-level path: graph /
   liability `indemnification` treatment plus any covered indemnity exposure
   (explicit per-category uncapped/super_cap still owned by Rules 1–2).
4. **Wiring** — `interaction_enforcement.apply_interaction_rules` passes
   `document_facts` into `interaction_engine_core.evaluate`; cutover path
   unchanged except for outcome-carried extracts.

### Remaining phases (reference only)

Phases 1–4 delivered the Liability + Indemnification fact layer and
interaction wiring. The golden E2E path now also:

1. **Commercial SSOT** — `contract_facts/commercial_extract.py` establishes
   `annual_fees` and `payment_due` with provenance; ACV is resolved only via
   `resolve_annual_contract_value` (`reviewer_deal_value` ≻
   `contract_annual_fees`), never by silently equating fees to ACV.
2. **Downstream consumers** — payment UI, consequential redline suppression,
   and the LoL inspector read canonical / commercial facts rather than
   independently rediscovering them from raw text.
3. **Production-path golden** — `tests/test_golden_mock_saas_e2e.py` asserts
   the full oracle through `apply_policies_for_review` (cutover).

Further work (outside this golden path): migrate remaining generic rules
deliberately; extend commercial into payment-terms policy enforcement.

---

## 8. Golden example (schema-level)

For the controlled SaaS test contract, Phase 2–3 population produces
(conceptually):

```text
# ACV (EvaluationContext) — provenance explicit
annual_contract_value         = $600,000  source=reviewer_deal_value | contract_annual_fees
# Liability (ContractLiabilityFacts)
liability.general_cap         = PRESENT FeeRelativeCap(months=6, PAID_OR_PAYABLE, AGREEMENT)
# Indemnification (ContractIndemnificationFacts)
indemnification.obligations   = [Provider→Customer IP..., Customer→Provider ...]
indemnification.procedures    = [§5.3 defense=indemnifying_party, notice=true, coop=true]
cross_clause                  = LIABILITY_APPLIES_TO_INDEMNIFICATION (§6.3 → §5)
```

Full document golden (later phases):

```text
commercial.annual_fees        = PRESENT $600,000 USD
commercial.payment_due        = PRESENT 30 days / invoice_receipt
liability.general_cap         = PRESENT FeeRelativeCap(months=6, PAID_OR_PAYABLE, AGREEMENT)
liability.mutuality           = PRESENT mutual
liability.consequential       = PRESENT excluded=true
liability.categories.indemnification = within_general_cap
indemnification.obligations   = [Provider→Customer IP..., Customer→Provider ...]
indemnification.procedures    = [§5.3 defense=indemnifying_party, notice=true, coop=true]
cross_clause                  = LIABILITY_APPLIES_TO_INDEMNIFICATION (§6.3 → §5)
```

Evaluation against the Active playbook then becomes a pure function of
these facts + policy — not a second parse.
