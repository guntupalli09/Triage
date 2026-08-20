# Step 4A.9.1 Phase 1 — Authority Flow Audit (Indemnification)

## Purpose

Trace exactly how text becomes a policy-authoritative fact in
`indemnification_policy_engine.py`, so Phase 3's semantic discovery channel
can be wired in at the one place it is safe to enter, and nowhere else.

## The current (regex-only) pipeline

```
extract_indemnification_facts(text)
  1. ANCHOR/SYNONYM/RISK-TRANSFER-SIGNAL gate (line ~1284)
     - _ANCHOR_RE, _SYNONYM_OBLIGATION_RES: STRUCTURING patterns — a match
       here also captures group(1)/group(2) (the two role names) and is
       used directly downstream.
     - _risk_transfer_signal_present(text): NON-authoritative. Boolean
       only. Its only effect is to prevent the early `return None`. It
       supplies zero fields to any Fact/Obligation object.
  2. Structuring loops (_OBLIGATION_RE, then _SYNONYM_OBLIGATION_RES):
     each match's group(1)/group(2) become indemnifying_role/
     indemnified_role -> resolve_role_side() -> indemnifying_side/
     indemnified_side (our_side/counterparty_side equivalents).
     The window around the match feeds:
       _classify_triggers()      -> trigger_treatments   (authoritative)
       _classify_scope()         -> scope                (authoritative)
       _classify_defense_control()-> defense_control      (authoritative)
       _classify_monetary()      -> monetary (cap/multiplier) (authoritative)
       _classify_causation_standard() -> causation standard (authoritative)
       _detect_reciprocal_asymmetry() -> asymmetry_reasons (authoritative)
       _SELF_FLAGGED_INDEMNIFICATION_UNRESOLVED_RE -> self_flagged_unresolved
  3. IndemnityObligation objects assembled from #2, collected into
     IndemnificationFacts.
  4. evaluate_indemnification_policy(facts, policy) consumes
     IndemnificationFacts ONLY (never raw text again) and emits
     ACCEPT / MUST_REDLINE / PROHIBITED / REQUIRES_REVIEW / NOT_APPLICABLE.
     If `obligations` is empty -> REQUIRES_REVIEW (never NOT_APPLICABLE),
     see line ~1689. NOT_APPLICABLE is reached ONLY via the earlier
     `extract_indemnification_facts` returning `None` (step 1's gate).
```

## The one authorized entry point for a semantic layer

`_risk_transfer_signal_present()` at line 254 is architecturally exactly
what a semantic discovery channel must look like: a **boolean discovery
signal with zero authoritative payload**, whose only downstream effect is
"don't early-return None / don't call this CONFIRMED_ABSENT" — it can never
set a role, a side, a cap, a multiplier, or a policy state.

**Rule for Phase 8 implementation:** a semantic `DiscoveryCandidate` may
extend step 1's gate (same non-authoritative boolean role
`_risk_transfer_signal_present` plays today) and may propose an
`evidence_span` to be **re-run through the existing structuring regexes**
(`_OBLIGATION_RE`, `_SYNONYM_OBLIGATION_RES`, `_classify_monetary`, etc.) —
i.e. the span is handed to the SAME deterministic structuring code that
already exists, not trusted to supply role/side/cap directly. If the
deterministic structuring regexes still can't structure that span, the
candidate must fall through to the existing REQUIRES_REVIEW path (step 4),
never invent a fact.

**Where a semantic layer must NEVER be wired in:** directly setting
`indemnifying_role`, `indemnified_role`, `*_side`, `MonetaryTreatment.kind/
multiplier/fixed_amount`, `scope`, `defense_control`, causation standard,
`asymmetry_reasons`, or any field read by `evaluate_indemnification_policy`.
Those fields are populated exclusively by regex-match groups today and must
stay that way — a semantic value could at most gate *whether deterministic
structuring is attempted on a span*, never supply the structured value
itself.

## Absence-state boundary

Today there is only a binary: `extract_indemnification_facts` returns
`None` (-> NOT_APPLICABLE) or a `IndemnificationFacts` with >=0 obligations
(-> REQUIRES_REVIEW if empty, else evaluated normally). Phase 11 requires
widening this to four states; the natural implementation point is the same
gate at line 1284 — `CONFIRMED_ABSENT` is only reachable when NEITHER regex
discovery NOR semantic discovery propose anything.
