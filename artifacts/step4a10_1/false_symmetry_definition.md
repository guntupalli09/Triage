# Step 4A.10.1 Phase 5 — False-Symmetry Definition

**Unsafe false symmetry**: two obligations/provisions appear reciprocal or
equivalent at a superficial structural level (a shared "each party
shall..."/"mutually"/two textually-parallel named-party sentences opener),
but differ in a policy-material dimension, and the engine's evaluation
treats them as materially equivalent — most dangerously, by letting a
`clean automatic` decision (ACCEPT/ACCEPT_WITH_NOTE, or `PRESENT_AND_
VERIFIED` feeding one) proceed without surfacing the asymmetry, or by
silently dropping the more severe of the two positions.

## Required comparison dimensions (all must be checked before symmetry may
be assumed)

1. Obligated party
2. Protected party
3. Claim category (which trigger types are covered)
4. Causation standard (negligence / gross negligence / willful misconduct
   / strict, and whether it differs per party)
5. Defense obligation (who must defend)
6. Defense control (who controls the defense)
7. Monetary cap (amount/multiplier)
8. Monetary basis (what the cap is measured against)
9. Exclusion/carve-out (what's excluded, and for which party)
10. Trigger condition (what event activates the obligation)
11. Conditional applicability (a proviso/exception gating one party only)
12. Procedural prerequisite (notice, cooperation, timing conditions)
13. Temporal scope (when the obligation runs)
14. Survival (does the obligation survive termination, for which party)
15. Third-party vs. first-party claims (scope of "claim")
16. Negligence/fault threshold (ordinary vs. gross, per party)
17. IP-specific treatment (does one party get IP-only coverage)
18. Data/privacy-specific treatment
19. Exceptions/provisos generally
20. Cross-referenced limitation (a value/term defined elsewhere that
    differs per party)

## Existing detection infrastructure (as of `8acd4ff`, before this
Phase's own changes)

`_detect_reciprocal_asymmetry` (indemnification_policy_engine.py) already
checks, in order: (1) "not yet reached agreement" self-flagged
non-establishment; (2) role-attributed asymmetry via the shared
`detect_role_attributed_asymmetry` core primitive (dimensions 3-11 roughly,
via a snapshot/compare mechanism); (3) one-named-party-vs-general-terms
exceptions; (4) differentiated procedural terms (dimension 12-14, survival/
notice/defense-control/temporal); (5) except/provided-that provisos naming
one role; (6) compound (two-mechanism) differentiation. This is
substantial pre-existing machinery from Steps 4A.5-4A.9 — Phase 6/7's job
is to test it against a genuinely independent benchmark spanning the full
dimension list above, not assume it is complete.

## Ground-truth labels

- **CS (Correct Symmetric)**: genuinely symmetric provision, correctly not
  flagged.
- **CA (Correct Asymmetric)**: genuinely asymmetric provision, correctly
  flagged (`asymmetry_reasons` non-empty, or independently routed to
  review).
- **CR (Correct Review)**: genuinely ambiguous — correctly routed to
  REQUIRES_REVIEW rather than either clean symmetric or clean asymmetric.
- **FS (False Symmetry)**: genuinely asymmetric, but the engine's output
  does NOT surface the asymmetry (empty `asymmetry_reasons` AND a clean
  decision proceeds) — the dangerous case.
- **FA (False Asymmetry)**: genuinely symmetric, but flagged as
  asymmetric/routed to review anyway — safe but a selectivity cost.
- **FE**: unnecessary review on an otherwise-clear case.
