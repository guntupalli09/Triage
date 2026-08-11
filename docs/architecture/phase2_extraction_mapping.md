# Phase 2 — Deterministic Extraction Mapping

Per-field mapping from each engine's existing `extract_*_facts()` output to
`PolicyPositionField` proposals, classified `DIRECTLY_ESTABLISHABLE` /
`REQUIRES_LAWYER_INTERPRETATION` / `NOT_DERIVABLE_FROM_TEMPLATE`, written
before/alongside `playbook_extraction.py` per the Phase 2 task instructions.
No policy engine is modified by this document or by Phase 2 — every fact
referenced below already exists in the six engines' `Facts` dataclasses;
this document only decides which of those facts are safe to present to a
lawyer as "your template established this."

## The governing rule

Two failure directions matter, and they are not symmetric:

1. **Manufacturing a range from a point.** A template stating "cap = 2×
   fees" tells you the preferred position. It tells you nothing about
   what would be *acceptable*, *negotiable*, or *grounds for escalation*
   — those are three additional, independent business decisions a single
   document cannot contain evidence for. **Ladder tiers beyond "preferred"
   are never established, for any adapter, no exceptions.**
2. **Manufacturing a requirement from silence.** A template's carve-out
   list not mentioning `fraud` does not mean the organization refuses to
   require a fraud carve-out — it may just not have come up in this deal.
   Confusing "not mentioned" with "affirmatively decided against" is the
   Phase 2 false-establishment failure mode named in the task.

This yields one operating rule, applied identically across all six
adapters below:

> **A boolean or list field may only be established in the direction the
> template's own actual clause content self-evidently demonstrates.**
> If the template's own clause *contains* the disfavored/prohibited thing
> itself (e.g. its own cap is literally unlimited), that is affirmative,
> self-evident proof the template does not categorically prohibit it —
> establish the negative (`prohibit_* = False`, `require_* = False`).
> A single clause containing a *favorable* term (e.g. a numeric cap, a
> present carve-out) is **never** sufficient to establish the opposite
> categorical requirement (`prohibit_* = True`, `require_* = True`) —
> that direction requires the clause to affirmatively rule out the
> alternative, not merely to omit it. Plain silence (the dimension isn't
> addressed at all) is always `NOT_ESTABLISHED`, in both directions.

Every "why NOT_ESTABLISHED even though the template has X" note below is
an application of this same rule, not a one-off judgment call.

## 1. Limitation of Liability (`limitation_of_liability`)

Source: `LiabilityFacts` → `controlling_provision` (`Provision`) after the
engine's own existing reconciliation (`facts.reconciliation`). Multiple
provisions with different effective caps and `reconciliation ==
"unreconciled"` → the general-cap field is `CONFLICTING`, evidence = both
provisions' excerpts.

| Field | Classification | Source signal | Why |
|---|---|---|---|
| `preferred_multiplier` | DIRECTLY_ESTABLISHABLE | `controlling_provision.general_cap_expression.effective_cap()`, kind=`fee_multiplier`, basis=`FEES` | The template's own stated cap, reduced by the engine's own already-tested `effective_cap()` (greater-of/lesser-of/per-claim already resolved or reported unresolved) |
| `acceptable_max_multiplier` | NOT_DERIVABLE_FROM_TEMPLATE | — | Ladder-range rule |
| `negotiate_max_multiplier` | NOT_DERIVABLE_FROM_TEMPLATE | — | Ladder-range rule |
| `prohibit_unlimited` | DIRECTLY_ESTABLISHABLE (False only) | effective cap kind=`unlimited` | Template's own cap being unlimited is self-evident proof unlimited liability isn't categorically prohibited. Never established `True` — a numeric cap in one deal doesn't prove unlimited would be refused. |
| `required_exceptions_json` | DIRECTLY_ESTABLISHABLE (whitelist only) | `category_treatments[cat]` with `established=True` and `treatment in (uncapped, super_cap)` | The template's own clause carves this category out — direct textual evidence. Categories with `not_addressed`/`unresolved` are simply omitted (never asserted absent). |
| `require_consequential_damages_exclusion` | DIRECTLY_ESTABLISHABLE (True only) | `consequential_damages_excluded is True and consequential_damages_established` | Extractor only ever returns `True` or `None` for `excluded` (see `_classify_consequential_damages`) — there is no "affirmatively not excluded" signal to establish `False` from, so that direction is structurally unreachable, not just policy-restricted. |
| `required_consequential_carveouts_json` | DIRECTLY_ESTABLISHABLE | `consequential_damages_carveouts` when `excluded is True` | Same clause, same evidence span. |

## 2. Indemnification (`indemnification`)

Source: `IndemnificationFacts.obligations`, split into "our exposure"
(we are `indemnifying_role`) vs. "our protection" (we are
`indemnified_role`) via the engine's own existing
`_resolve_obligations_for_side(facts.obligations, contract_side)` —
reused as-is (never reimplemented) so Phase 2's directional read can never
silently disagree with what `evaluate_indemnification_policy` itself
would resolve. `contract_side` is a lawyer-supplied input to the import
action (default `mutual`); it is not itself extractable — no adapter's
Facts model identifies which named party is "us" (out of scope, see §7).

| Field | Classification | Source signal | Why |
|---|---|---|---|
| `required_protection_triggers_json` | DIRECTLY_ESTABLISHABLE | protection obligation's `trigger_treatments[t]`, `established=True`, `treatment=="covered"` | They demonstrably cover this trigger for us in this template. |
| `prohibited_exposure_triggers_json` | DIRECTLY_ESTABLISHABLE | exposure obligation's `trigger_treatments[t]`, `established=True`, `treatment=="excluded"` | Affirmative exclusion language for our own exposure — self-evident. `not_addressed` is never treated as prohibited. |
| `require_exposure_third_party_only` | DIRECTLY_ESTABLISHABLE (both directions) | exposure obligation's `scope` | `"third_party_only"` → True; `"includes_first_party"` → False (both are affirmative statements the clause actually makes). `"not_addressed"`/`"unresolved"` → NOT_ESTABLISHED. |
| `require_defense_control_for_exposure` | DIRECTLY_ESTABLISHABLE (both directions) | exposure obligation's `defense_control` | `"indemnifying_party"` (us) → True; `"indemnified_party"` (them) → False. `"shared"` → NOT_ESTABLISHED (not a clean match either way). |
| `require_notice_and_cooperation_for_exposure` | REQUIRES_LAWYER_INTERPRETATION | exposure obligation's `notice_required`/`cooperation_required` | Extractor only distinguishes "both required" from "not established" — there is no affirmative "explicitly not required" signal, so only the True direction is reachable and even that conflates two independent conditions into one boolean. Established True only when both are `True`; never established False. |
| `prohibit_uncapped_exposure` | DIRECTLY_ESTABLISHABLE (False only) | exposure obligation's `monetary.kind == "unlimited"` | Self-evident, same pattern as liability's `prohibit_unlimited`. |
| `exposure_preferred_multiplier` | DIRECTLY_ESTABLISHABLE | exposure obligation's `monetary`, kind=`multiplier` | Template's own stated exposure cap. |
| `exposure_acceptable_max_multiplier` / `exposure_negotiate_max_multiplier` | NOT_DERIVABLE_FROM_TEMPLATE | — | Ladder-range rule. |

If `_resolve_obligations_for_side` itself reports an ambiguous/ multiple
candidate result for a direction (its own `resolution_reasons`), that
direction's fields are `NOT_ESTABLISHED` with the reason surfaced, not
guessed at.

## 3. Termination (`termination`)

Source: `TerminationFacts`. Directional split (their rights against us vs.
our rights) by `TerminationRight.holder_side`.

| Field | Classification | Source signal | Why |
|---|---|---|---|
| `require_mutual_convenience_termination` | DIRECTLY_ESTABLISHABLE (True only) | both sides hold a `trigger_type=="convenience"` right (or one `is_mutual=True` convenience right) | Template demonstrably gives both sides the same walk-away right. An asymmetric template (only one side has it) does **not** establish False — the template may simply not have needed mutuality in that deal; conservative per the negative-evidence rule. |
| `min_notice_days_against_us` | DIRECTLY_ESTABLISHABLE | counterparty's (`holder_side != contract_side`) convenience right's `notice_period_days` | A single required floor value, not a range — same shape as "preferred", not the ladder. |
| `min_cure_days_against_us` | DIRECTLY_ESTABLISHABLE | counterparty's `material_breach` right's `cure_period_days` | Same reasoning. |
| `prohibit_immediate_termination_for_cause` | DIRECTLY_ESTABLISHABLE (False only) | **our own** (`holder_side == contract_side`) `material_breach` right has `immediate=True` | Self-evident: our own template lets us (or, for a mutual right, either side) terminate immediately without cure, so the template itself doesn't categorically prohibit that. Never established True from a cure period merely being present in one deal. |
| `required_survival_topics_json` | DIRECTLY_ESTABLISHABLE (whitelist only) | `survival_topics[t].present == True` | Direct read of the template's own survival clause. |
| `prohibit_uncapped_termination_fee` | DIRECTLY_ESTABLISHABLE (False only) | `fee.kind == "unlimited"` | Self-evident, same pattern. |
| `fee_preferred_multiplier` | DIRECTLY_ESTABLISHABLE | `fee.kind == "multiplier"` | Template's own stated fee. |
| `fee_acceptable_max_multiplier` / `fee_negotiate_max_multiplier` | NOT_DERIVABLE_FROM_TEMPLATE | — | Ladder-range rule. |

## 4. Confidentiality (`confidentiality`)

Source: `ConfidentialityFacts.obligations`, directional by
`protecting_side`/`protected_side`.

| Field | Classification | Source signal | Why |
|---|---|---|---|
| `required_exclusions_json` | DIRECTLY_ESTABLISHABLE (whitelist only) | obligation where `protecting_side != contract_side` (they protect us), `exclusions_present[t] == True` | Direct evidence of a carve-out present in the protection we actually receive in this template. |
| `min_protection_duration_years` | DIRECTLY_ESTABLISHABLE | same obligation's `duration_years` (or a documented sentinel if `duration_perpetual`) | Single stated floor value. |
| `max_exposure_duration_years` | DIRECTLY_ESTABLISHABLE | obligation where `protecting_side == contract_side` (we protect them), `duration_years` | Single stated ceiling value — this is the one ladder-shaped field across all six adapters where the *template's own single number* is directly the policy value itself, not a range boundary being inferred; both directions are independently observable single obligations, not a guess. |
| `require_mutual_confidentiality` | DIRECTLY_ESTABLISHABLE (True only) | an `is_mutual=True` obligation, or both directional obligations present | Template demonstrably protects both directions. A single-direction template does not establish False (negative-evidence rule). |

## 5. Assignment (`assignment`)

Source: `AssignmentFacts.restrictions`, directional by `restricted_side`.

| Field | Classification | Source signal | Why |
|---|---|---|---|
| `required_exceptions_json` | DIRECTLY_ESTABLISHABLE (whitelist only) | restriction on us (`restricted_side == contract_side`), `exceptions_present[t] == True` | Direct evidence this exception is already carved out for us in this template. |
| `prohibit_sole_discretion_consent` | DIRECTLY_ESTABLISHABLE (False only) | our own restriction's `consent_standard == "sole_discretion"` | Self-evident: the template itself subjects us to sole-discretion consent, so it plainly doesn't prohibit that language categorically. `"reasonable"` never establishes True (omission ≠ prohibition). |
| `require_consent_for_counterparty_assignment` | DIRECTLY_ESTABLISHABLE (True only) | a restriction also exists where `restricted_side != contract_side` | Template demonstrably restricts both sides. A one-sided template does not establish False. |

`AssignmentFacts.unrestricted_assignment` (clause explicitly states no
restriction at all) has no corresponding policy field to populate — noted
as NOT_DERIVABLE_FROM_TEMPLATE at the whole-fact level, not mapped.

## 6. Governing Law (`governing_law`)

Source: `GoverningLawFacts` — the one adapter with no directionality
(consistent with its role as negative control throughout this project).

| Field | Classification | Source signal | Why |
|---|---|---|---|
| `preferred_jurisdictions_json` | DIRECTLY_ESTABLISHABLE | `jurisdiction` when `clause_found` | Single-element list from the template's own stated jurisdiction. |
| `acceptable_jurisdictions_json` | NOT_DERIVABLE_FROM_TEMPLATE | — | One document names one jurisdiction; it cannot establish a set of *alternatives* it would also accept. |
| `prohibited_jurisdictions_json` | NOT_DERIVABLE_FROM_TEMPLATE | — | A document naming a jurisdiction says nothing about jurisdictions it would refuse. |
| `required_dispute_resolution` | DIRECTLY_ESTABLISHABLE | `dispute_resolution` | `"arbitration"` and `"mediation_then_arbitration"` both map to `"arbitration"` (the evaluator itself already treats `mediation_then_arbitration` as satisfying an arbitration requirement — see `evaluate_governing_law_policy`'s own mismatch check); `"litigation"` maps directly; `"not_stated"` → NOT_ESTABLISHED. |
| `require_jury_trial_waiver` | DIRECTLY_ESTABLISHABLE (True only) | `jury_trial_waived == True` | `jury_trial_waived` is a bare regex-presence detector (`bool(_JURY_WAIVER_RE.search(text))`) — `False` means "the waiver phrase wasn't found," not "the template affirmatively preserves jury trial rights." Establishing `False` from this signal would be exactly the false-establishment failure mode the release gate measures, since the overwhelming majority of templates simply never mention jury trial at all. |

## What Phase 2 does not attempt

- **`contract_side` is never extracted**, for any adapter — determining
  "which named party is us" requires information (a defined-terms
  preamble binding a real organization identity to a role label) no
  extractor in this codebase parses. It is a required input to the
  import action itself, defaulting to `mutual`.
- **`escalation_approval_authority`** is an organizational fact (who
  signs off), not a contract fact — NOT_DERIVABLE_FROM_TEMPLATE for every
  adapter.
- **`fallback_text`** is drafted redline language the org would *propose*,
  not language a template necessarily already contains verbatim in a
  reusable form — NOT_DERIVABLE_FROM_TEMPLATE for every adapter. (A
  future phase could propose the template's own clause text as a
  fallback candidate; Phase 2 does not, to avoid implying the org has
  already vetted it as fallback-quality language.)
