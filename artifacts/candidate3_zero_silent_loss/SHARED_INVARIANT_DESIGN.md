# Shared Zero-Silent-Loss Invariant Design (Phases 2-3)

## Studying the liability reference implementation (Phase 2)

The immediately-prior mission's fix to `limitation_of_liability` (3 `MATERIAL_CONTEXT_SILENTLY_LOST` cases) worked by: whenever `provision.category_treatments` contains an established `"uncapped"` category NOT named in `policy.required_exceptions_json`, elevate a would-be bare `ACCEPT` to `ACCEPT_WITH_NOTE` and describe the carve-out in the explanation.

What this preserves: the carve-out's existence and description.
How it detects unresolved material context: by checking `category_treatments` (already deterministically populated, unrelated to this fix) against the configured policy's specific list of REQUIRED categories — anything established but not required was previously invisible.
Where it blocks (or rather, downgrades) clean authority: entirely inside `evaluate_liability_policy`, at the point the final `state` is computed — never in extraction, never in `fact_admission.py`.
Where the mechanism lives: `liability_policy_engine.py` only. It never needed `fact_admission.py` or `policy_engine_core.py` changes, because the underlying fact (`category_treatments['X'] = 'uncapped'`) was ALREADY correctly, deterministically established — the gap was purely in how the decision-layer consumed it.

**This IS a shared invariant, but not a shared mechanism**: the invariant — "an established material modifier not covered by any positive check must remain visible in the decision, never a bare ACCEPT" — generalizes. The concrete detection logic (`category_treatments` keyed by named risk categories) is liability-specific vocabulary and does NOT transplant directly to other adapters (confidentiality has no risk categories; insurance has coverage types; ip_ownership has ownership categories).

## Separating the shared invariant from adapter-specific materiality semantics

**Shared invariant** (implemented as reusable primitives in `policy_engine_core.py`, Phase 3):

1. `document_wide_conflict_detected(text)` — a separate, later statement broadly negating/superseding an established value elsewhere in the document. General regex vocabulary (`DOCUMENT_WIDE_NEGATION_RE`): "no specific X (is/are) required", "does not guarantee any specific X", "Section N shall not apply" (scoped to whole-section nullification, not a category carve-out), "retains all ownership rights...grants...a license", "may freely `<verb>`...without consent". Adapter-agnostic: takes only the document text.
2. `unreconciled_ambiguity_marker_present(text)` — the document's OWN explicit self-declaration of unreconciled ambiguity ("without indicating which governs", "without reconciling the two/which controls"). A real, standard contract-drafting-review convention, not vocabulary invented for one test corpus. Adapter-agnostic.
3. `cross_section_carveout_referencing(text, section_label)` — a carve-out, exclusion, or additional requirement elsewhere in the document that explicitly cross-references the primary clause's OWN section number (by number, not by adapter-specific keyword). Parameterized by `section_label` (already tracked by every adapter's own facts object) so it works identically for insurance's "Section 10", sla's "Section 14", confidentiality's "Section 8", or assignment's "Section 20" without any adapter-specific vocabulary in the shared function itself.
4. `detect_condition_in_span` / `detect_condition_in_text` (pre-existing, already shared and used by liability before this mission) — a deterministic condition/proviso attached to a specific span or window. Reused, not reinvented, for insurance/warranties/ip_ownership.

**Adapter-specific materiality semantics** (decided per adapter, Phase 4):

- WHICH established facts are inherently notable regardless of policy configuration (liability's uncapped risk categories, insurance's coverage conditions/exceptions, ip_ownership's ownership conditions/exceptions) vs. WHICH are routinely benign and would create noise if always flagged (confidentiality's four standard exclusions — public-domain, independently-developed, third-party-rightful, required-by-law — are present in nearly every well-drafted clause and are normatively GOOD, not risk-bearing).
- WHAT the resulting state should be when a conflict/ambiguity/cross-reference is found — always `REQUIRES_REVIEW` for confidentiality/sla/assignment/payment_terms/ip_ownership/insurance (since these represent genuine, adapter-specific value-conflicts, condition-satisfaction-unknowns, or self-declared ambiguities that this evaluation cannot resolve), vs. `ACCEPT_WITH_NOTE` for liability's uncapped-but-not-required carve-outs specifically (since an uncapped carve-out for a standard risk category is not itself a policy violation, merely a fact worth surfacing).

This separation is why the same shared primitive (`cross_section_carveout_referencing`) is wired into 6 different adapters but each adapter decides for itself what to DO once it fires (liability: N/A — not applicable to liability's fix, which used a different primitive; insurance/sla/confidentiality/assignment: append to `unresolved_facts`, forcing `REQUIRES_REVIEW`).

## Why "no clean result permitted" rather than a new state enum

The mission's suggested `COMPLETE`/`UNRESOLVED_MATERIAL_CONTEXT`/`CONFLICTING`/`AMBIGUOUS` reconciliation-result vocabulary was evaluated against the EXISTING states every adapter already has (`ACCEPT`/`ACCEPT_WITH_NOTE`/`NEGOTIATE`/`MUST_REDLINE`/`PROHIBITED`/`ESCALATE`/`REQUIRES_REVIEW`/`NOT_APPLICABLE`). `REQUIRES_REVIEW` already IS the "material context could not be reliably established/reconciled" state every adapter uses for exactly this purpose (unresolved dependencies, ambiguous qualifiers, provider errors). Introducing a parallel `UNRESOLVED_MATERIAL_CONTEXT`/`CONFLICTING`/`AMBIGUOUS` state family would create a REDUNDANT state system the mission's own Phase 3 instruction explicitly warns against ("Do not create redundant state systems unnecessarily"). All fixes in this mission route to the adapter's EXISTING `REQUIRES_REVIEW` (or, for liability's specific case, the existing `ACCEPT_WITH_NOTE`) rather than inventing new vocabulary.
