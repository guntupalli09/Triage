PRE-FREEZE INSPECTION — INSPECTION ONLY, NO CODE CHANGED

# Twelve-Adapter Tree — discovery through final decision, per adapter

Each adapter is one of two architectures: **Architecture M** ("mirror" — 11 adapters,
built on the shared `fact_admission.py` pipeline via `_run_semantic_discovery`), or
**Architecture I** (indemnification, structurally distinct).

## 01. limitation_of_liability (`liability_policy_engine.py`) — Architecture M, fully verified template

```
deterministic discovery ──── _ANCHOR_RE + _SECONDARY_ANCHOR_RE, deduped (_discover_anchors, 1600-1620)
AI contextual discovery ──── _run_semantic_discovery called UNCONDITIONALLY at line 1734,
                              before the `if not accepted_anchors:` gate — PASS, fix confirmed present
semantic verification ────── fact_admission.verify_and_ground (shared) — PASS (inherited)
evidence grounding ────────── fact_admission (shared) — PASS (inherited)
primary-fact reconciliation ─ single / amendment_resolved / consistent_duplicate / unreconciled
                              (1861-1908); unreconciled → REQUIRES_REVIEW (2048-2060) — PASS
condition handling ────────── deterministic ConditionEvidence + AI augmentation only when
                              deterministic == UNCONDITIONAL (1812-1813); any non-UNCONDITIONAL
                              condition forces unresolved_facts (2152-2164) — PASS
exception/carve-out handling  category_treatments per-category classifier; unresolved-for-
                              required-category forces review (2141-2144); established-but-
                              not-required surfaces via ACCEPT_WITH_NOTE, never disappears
                              (2209-2212, 2258-2259) — PASS
definition handling ───────── generic role-word resolution via resolve_role_side — PASS
cross-reference handling ──── AI-sourced path only (fact_admission composition, 1817-1828);
                              no direct deterministic locate_target_provision call found in
                              liability's own structuring — UNKNOWN (deterministic path)
competing-reading handling ── inherited from evaluate_admission's ≥2-grounded-readings gate — PASS
unresolved dependency ──────── PARTIAL PASS: primary "no anchor at all" path forces
propagation                   REQUIRES_REVIEW via DEPENDENCY_UNRESOLVED (1753-1765, 2017-2035);
                              anchor-exists path gated on _any_provision_established
                              (1853-1859) — correctly suppresses limitation_of_liability-006-
                              shaped redundant flakiness (live-reproduced in this audit), but
                              by the adapter's OWN comment (1768-1777) a SEPARATE admitted
                              candidate at a non-matching offset is silently dropped —
                              documented residual risk, not fixed this mission
deterministic evaluation ──── states observed: ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, ESCALATE,
                              MUST_REDLINE, PROHIBITED, REQUIRES_REVIEW, NOT_APPLICABLE (all 7
                              mission states + ACCEPT_WITH_NOTE)
```

## 02. indemnification (`indemnification_policy_engine.py`) — Architecture I, structurally distinct

```
deterministic discovery ──── FOUR independent negative signals required to all miss before
                              considering absence (_ANCHOR_RE, _SYNONYM_OBLIGATION_RES,
                              _risk_transfer_signal_present, _STRUCTURAL_RISK_TRANSFER_PATTERNS,
                              2805-2827) — a materially broader net than the other 11 adapters
AI contextual discovery ──── 🚨 HYBRID_DISCOVERY_ENABLED=True, UNCONDITIONAL, NO ENV OVERRIDE
                              (line 80); dispatches to SEMANTIC_PROVIDER="SIMULATED" (line 89,
                              hardcoded, zero os.environ reads anywhere in file) →
                              semantic_discovery.py's regex-based DiscoveryCandidate proposer —
                              NOT a language model in any deployment absent a source edit.
                              FACT_ADMISSION_MODE=enforced has NO EFFECT on this path — FAIL
                              against the mission's stated premise that AI discovery is
                              env-configurable and provider-backed
semantic verification ────── the SIMULATED channel has no verification step of its own (it
                              IS deterministic Python); the SEPARATE, real fact_admission-backed
                              channel below does use real verify_and_ground when enabled
evidence grounding ────────── same split as above
primary-fact reconciliation ─ NOT a "single controlling value" model like the other 11 —
                              BOTH directions of a reciprocal indemnity are independently real
                              facts, never merged (2781-2889, role-pair-aware dedup 2849-2855) —
                              PASS for this adapter's own (correct) design intent
condition handling ────────── per-obligation deterministic condition; `_reconcile_obligation_
                              with_contextual_analysis` (115-170, off by default via
                              INDEMNIFICATION_RECONCILIATION_ENABLED, the ONE env-gated
                              real-AI channel this adapter has) composes an AI qualifier only
                              when `already_captured` (obligation.condition already
                              ESTABLISHED) is False — PARTIAL, narrower gate than liability's
exception/carve-out handling  same reconciliation channel, same partial gate
definition handling ────────── same reconciliation channel
cross-reference handling ──── same reconciliation channel
competing-reading handling ── inherited from evaluate_admission (only within the reconciliation
                              channel, since the primary discovery channel is not fact_admission-
                              backed at all)
unresolved dependency ──────── 🚨 FAIL: the reconciliation channel's `else` branch (167-170,
propagation                   reached on NOT_ADMITTED) calls first_unresolved_dependency_note
                              UNCONDITIONALLY — no equivalent to liability's
                              _any_provision_established gate. Consumed unconditionally at
                              3461-3465/3516-3520. For an obligation whose condition is the
                              ONLY unresolved dimension (monetary/scope independently clean),
                              this can flip clean↔REQUIRES_REVIEW across identical runs —
                              exactly the limitation_of_liability-006 shape, never closed here,
                              never in the repeatability corpus
deterministic evaluation ──── states observed: ACCEPT, NEGOTIATE, PROHIBITED, ESCALATE,
                              MUST_REDLINE, REQUIRES_REVIEW, NOT_APPLICABLE (7 states observed;
                              ACCEPT_WITH_NOTE not confirmed present or absent — not fully
                              read to file end, UNKNOWN)
```

## 03–12. Ten remaining Architecture-M adapters (confidentiality, payment_terms, ip_ownership,
insurance, data_security, governing_law, termination, warranties, sla, assignment)

All ten confirmed, by direct call-site line inspection, to invoke `_run_semantic_discovery`
**before** their own `if not <anchors>:` gate (i.e. the "gated behind deterministic miss"
defect is fixed in current code for all ten, matching liability):

| Adapter | discovery-before-gate line | RECOGNITION_UNCERTAIN present | dependency-propagation mechanism | verified end-to-end? |
|---|---|---|---|---|
| confidentiality | 343→344 | yes (347) | unconditional field + unconditional consumption (447, 570, 617) | **PASS, fully verified** |
| assignment | 252→253 | yes (255) | unconditional field + unconditional consumption (319, 454) | **PASS, fully verified** |
| governing_law | 182→183 | yes (185) | unconditional field + unconditional consumption (206, 313) | **PASS, fully verified** |
| termination | 458→459 | yes (461) | unconditional field + unconditional consumption (559, 720) | **PASS, fully verified** |
| insurance | 395→396 | yes (398) | `deterministic_value_found`-gated (630-634), verified end-to-end (790-794) | **PASS, fully verified** |
| payment_terms | 730→731 | yes (733) | `_any_established`-gated (1052-1071), same pattern as liability | **PASS, structurally consistent; not traced to every evaluate branch** |
| data_security | 585→586 | yes (588) | `_any_established`-gated (755-769) | **PASS, structurally consistent; not traced to every evaluate branch** |
| ip_ownership | 617→(below) | yes (620) | `_any_other_established`-gated (750-763) | **PASS, structurally consistent; not traced to every evaluate branch** |
| sla | 466→467 | yes (469) | `found_anything`-gated (758-777) | **PASS, structurally consistent; not traced to every evaluate branch** |
| warranties | 464→465 | yes (467) | `found_anything`-gated (627-646) | **PASS, structurally consistent; not traced to every evaluate branch** |

All ten inherit the **shared** `first_unresolved_dependency_note` `VERIFICATION_ERROR` gap
(FAILURE_FLOW_TREE.md) — this is a `fact_admission.py`-level defect, not an adapter-specific
one, so it applies uniformly regardless of each adapter's own gating quality.

## Per-adapter states reachable (from ladder/`_worse`/literal-`state=` grep, not exhaustively re-verified for every adapter)

| Adapter | States confirmed |
|---|---|
| liability | ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, ESCALATE, MUST_REDLINE, PROHIBITED, REQUIRES_REVIEW, NOT_APPLICABLE |
| indemnification | ACCEPT, NEGOTIATE, PROHIBITED, ESCALATE, MUST_REDLINE, REQUIRES_REVIEW, NOT_APPLICABLE |
| confidentiality | ACCEPT, NEGOTIATE, MUST_REDLINE, ESCALATE, REQUIRES_REVIEW, NOT_APPLICABLE |
| termination | ACCEPT, MUST_REDLINE, NEGOTIATE, PROHIBITED, ESCALATE, REQUIRES_REVIEW, NOT_APPLICABLE |
| assignment | ACCEPT, NEGOTIATE, REQUIRES_REVIEW, NOT_APPLICABLE (MUST_REDLINE/PROHIBITED/ESCALATE not confirmed — UNKNOWN) |
| warranties | ACCEPT, REQUIRES_REVIEW, NOT_APPLICABLE confirmed; NEGOTIATE/MUST_REDLINE/PROHIBITED/ESCALATE UNKNOWN |
| sla | ACCEPT, REQUIRES_REVIEW, NOT_APPLICABLE confirmed; remainder UNKNOWN |
| governing_law | NOT_APPLICABLE, REQUIRES_REVIEW, MUST_REDLINE, NEGOTIATE confirmed; ACCEPT/ESCALATE/PROHIBITED UNKNOWN |
| payment_terms, ip_ownership, insurance, data_security | NOT_APPLICABLE, REQUIRES_REVIEW confirmed with certainty; full reachable-state set UNKNOWN (not captured by the grep pattern used) |

This table's gaps are reported honestly rather than assumed — a full accounting would
require reading each evaluate function to its end, not done for all 12 in this pass.
