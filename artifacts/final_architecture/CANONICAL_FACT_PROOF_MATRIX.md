# CANONICAL_FACT_PROOF_MATRIX

Per the mission's explicit instruction: **"Framework exists" is NOT
PASS. "Adapter is wired" is NOT PASS. "Unit tests pass" is NOT PASS.**
A PASS requires proof of the complete chain: AI context → complete
candidate → material modifiers preserved → deterministic grounding →
admitted fact → correct adapter input → deterministic decision or safe
review. Every row below is scored against that bar, not against whether
code exists.

| Adapter | AI CONTEXT | QUALIFIER PRESERVATION | CONDITION PRESERVATION | EXCEPTION PRESERVATION | DEFINITION RESOLUTION | CROSS-REFERENCE | PARTY GROUNDING | COMPETING READING | DETERMINISTIC GROUNDING | UNVERIFIED→CLEAN | FALSE-OPERATIVE→CLEAN | FALSE ABSENCE | FINAL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| limitation_of_liability | PASS | **PASS** | **PASS** | N/A (no dedicated exception field wired; category carve-outs are a separate, pre-existing deterministic mechanism not part of this pass) | FAIL (not wired) | FAIL (not wired) | FAIL (party grounding remains deterministic-only; AI-sourced party claims are not separately grounded) | FAIL (not implemented) | PASS | 0 | 0 | 0 | **PASS** (narrow — see scope note) |
| indemnification | FAIL (own separate mechanism; no qualifier vocabulary in its AI layer at all, by original pre-existing design) | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL (deterministic only) | FAIL | PASS (its own pre-existing grounding) | 0 | 0 | 0 | **FAIL** |
| confidentiality | FAIL (flag exists, no qualifier wiring) | FAIL | N/A | FAIL | FAIL | FAIL | FAIL | FAIL | PASS (evidence-quote only) | 0 | 0 | 0 | **FAIL** |
| payment_terms | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS (evidence-quote only) | 0 | 0 | 0 | **FAIL** |
| ip_ownership | FAIL | FAIL | N/A | FAIL | FAIL | FAIL | FAIL | FAIL | PASS (evidence-quote only) | 0 | 0 | 0 | **FAIL** |
| insurance | FAIL | FAIL | N/A | FAIL | FAIL | FAIL | FAIL | FAIL | PASS (evidence-quote only) | 0 | 0 | 0 | **FAIL** |
| data_security | FAIL | FAIL | N/A | FAIL | FAIL | FAIL | FAIL | FAIL | PASS (evidence-quote only) | 0 | 0 | 0 | **FAIL** |
| governing_law | FAIL | FAIL | N/A | N/A | N/A | N/A | N/A | FAIL | PASS (evidence-quote only) | 0 | 0 | 0 | **FAIL** |
| termination | FAIL | FAIL | FAIL | N/A | FAIL | FAIL | FAIL | FAIL | PASS (evidence-quote only) | 0 | 0 | 0 | **FAIL** |
| warranties | FAIL | FAIL | N/A | FAIL | FAIL | FAIL | FAIL | FAIL | PASS (evidence-quote only) | 0 | 0 | 0 | **FAIL** |
| sla | FAIL | FAIL | N/A | FAIL | FAIL | FAIL | N/A | FAIL | PASS (evidence-quote only) | 0 | 0 | 0 | **FAIL** |
| assignment | FAIL | FAIL | N/A | FAIL | FAIL | FAIL | FAIL | FAIL | PASS (evidence-quote only) | 0 | 0 | 0 | **FAIL** |

## Scope note on liability's PASS

Liability's PASS is **narrow, not the full bar this matrix's header
describes**. What is actually proven, with an executable test
(`test_ai_identified_condition_survives_to_forced_review_the_mission_
critical_case`):

- The AI verifier can notice a material CONDITION phrased outside the
  deterministic detector's regex vocabulary.
- That condition, once grounded, is composed onto `Provision.condition`.
- The existing deterministic evaluator (unmodified) forces
  `REQUIRES_REVIEW` because it already treats any non-`UNCONDITIONAL`
  condition that way, regardless of source.

What is **NOT** proven for liability, honestly marked FAIL/N/A above:
exception-specific wiring (liability has no separate "exception" concept
distinct from category carve-outs, which remain deterministic-only and
untouched), definition resolution, cross-reference resolution, AI-sourced
party-role grounding, and competing-reading preservation. Liability's
PASS covers exactly one dimension (condition preservation) of the eight
this matrix scores, chosen because it is the dimension the mission's own
worked example (Vendor/Customer indemnification with a notice condition)
most directly maps onto, and because the reference-adapter discipline
established in prior phases says prove one thing completely before
generalizing.

## Verdict

**12/12 PASS is NOT achieved.** Per the mission's own rule ("Do not call
the architecture complete unless 12/12 PASS"), this phase's own gate is
not met. 1/12 adapters (liability) has ONE dimension of the required
proof; 11/12 have none. This is reported here without softening, per the
mission's instruction to be extremely conservative with PASS.
