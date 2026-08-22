# Step 4A.11 Bounded Remediation — Final Report

## Verdict

**PASS WITH CONDITIONS — STEP 4A COMPLETE; STEP 4B AUTHORIZED.**

## Summary

The single blocker identified in the Step 4A.11 final report
(`wrong_ownership=6`, a heading/clause-boundary role-name-capture defect)
has been root-caused, fixed, and independently validated. All hard gates
pass. The fix is bounded to the diagnosed mechanism — the only production
file touched is `indemnification_policy_engine.py`; `policy_engine_core.py`,
`liability_policy_engine.py`, `payment_terms_policy_engine.py`, and
`semantic_discovery.py` are byte-identical to the original freeze
(`d769491`).

## Evidence chain

1. **Root cause** (`ROOT_CAUSE.md`): two independent defects in the single
   shared `_MULTIWORD_ROLE_NAME_FRAGMENT` building block (30+ structural
   patterns in indemnification_policy_engine.py) — a dash-as-punctuation/
   dash-as-word-joiner conflation, and an ALL-CAPS-removes-the-only-
   stopping-signal overflow. Confirmed confined to indemnification;
   liability and payment_terms use different, unaffected mechanisms.
2. **80-case DEV benchmark** (categories A–U): PRE wrong_clean=31/80, POST
   wrong_clean=0/80 (61 correct, 3 correctly fail-closed on genuinely
   ambiguous cases, 16 safe FE).
3. **Structural fix**: a dash-boundary separator requiring letter/digit-
   flanking, a "trusted continuation budget" (real names top out at 5
   words; a 6-word capture is flagged as budget-exhausted), and a
   subordinate-clause-connector boundary reusing the SAME closed
   preposition class already used elsewhere in this codebase's condition
   infrastructure — not a growing stop-phrase list. All 5 actor/
   beneficiary construction sites route through a new `_verify_role_capture`
   wrapper and skip (leave unresolved) on an unreliable span, implementing
   the material-fact-ownership invariant.
4. **Full regression suite**: zero unexplained change (pytest 1210/1210
   identical, every historical/DEV/battery benchmark unchanged or
   improved, semantic-authority/security controls unchanged, Step 4A.10
   Clean-Verified Recall unchanged at 63.18%).
5. **Locked 393-case corpus replay** (regression evidence only, ground
   truth untouched): WC 6→0, SM unchanged at 7 (the two already-disclosed,
   out-of-scope findings reproduce identically), Clean-Verified Recall
   57.5%→58.4% (slight improvement).
6. **Remediation freeze** at `2f8d4762cec595ec6b5f7a16edd5b885e9bde67d`
   (only `indemnification_policy_engine.py` hash changed from the
   original freeze).
7. **Fresh 167-case remediation-validation corpus** (independent,
   completely new vocabulary, overlap-checked against all 1199 prior
   cases including the DEV benchmark and Phase 6 corpus, executed exactly
   once): **CA=108 CR=12 FE=47 WC=0**. Automation Recall 69.7%. All hard
   gates PASS: wrong_ownership=0, semantic_authority_diffs=0,
   determinism=100% (confirmed twice, including a separate reproduction
   run after the corpus's own internal 5x check).

## Hard gate table

| Gate | Required | Actual | Status |
|---|---|---|---|
| wrong-role-clean / wrong-ownership-clean | 0 | 0 | PASS |
| S4 (pre-existing named benchmark) | 0 | 0 (unchanged) | PASS |
| SM-CRITICAL | 0 | 0 (unchanged) | PASS |
| False-symmetry | 0 | 0 (unchanged) | PASS |
| Policy-changing UNVERIFIED-CA | 0 | 0 (unchanged) | PASS |
| Semantic→authority | 0 | 0 | PASS |
| Fabricated-evidence→authority | 0 | 0 (unchanged) | PASS |
| Authoritative determinism | 100% | 100% (reproduced twice) | PASS |
| Clean-Verified Recall (frozen target) | ≥44.5% | 58.4% (locked-corpus replay) | PASS, not materially destroyed vs. 57.5% pre-remediation |

No repeated new WRONG-CLEAN mechanism was found in the fresh corpus.

## Findings surfaced by the fresh corpus, disclosed and NOT patched (per the "no tuning after execution" rule)

All are safe (FE-only — lost automation, never a wrong value) and are
recorded here as post-ship backlog items, not blockers:

1. **Dotted abbreviation directly followed by a no-space hyphen**
   ("U.S.-Pacific Trading Corp") regressed by this remediation's own
   dash-boundary fix — the hyphen's lookbehind requires a letter/digit,
   and a dotted abbreviation ends in a period. Confirmed via direct
   A/B testing against the pre-remediation code that this specific shape
   worked before and does not now. Narrow (requires BOTH a dotted
   abbreviation AND a directly-adjacent, no-space hyphen), safe (produces
   FE, not a wrong value), and discovered only after the fresh corpus had
   already been executed — per protocol, not patched now. Recommended fix
   for the next development increment: extend the separator's lookbehind
   to also accept a trailing period.
2. **Brand-style names starting with a lowercase letter** ("eCommerce
   Solutions Group") were never supported by the role-name capture's
   first-token shape (`[A-Z]...`) — confirmed as a pre-existing limitation
   unrelated to and unchanged by this remediation.
3. **`_MUTUAL_RECIPROCAL_RE`'s trailing-clause coverage is narrower than
   `_OBLIGATION_RE`'s** — a reciprocal opener with an unusual trailing
   clause ("...AGAINST ANY LOSS TRACEABLE TO ITS RESPECTIVE ACTS OF
   MISCONDUCT" instead of the more common "...FROM ANY CLAIM ARISING OUT
   OF...") falls through to the generic named-role path, capturing "EACH
   PARTY"/"THE OTHER PARTY" as literal (if syntactically clean, not
   corrupted) role text instead of being flagged as the dedicated
   reciprocal pattern. Confirmed as a pre-existing, unrelated mechanism —
   not the diagnosed defect, not touched by this remediation's fix.
4. Apostrophe-bearing names in a specific combination ("St. Cuthbert's
   Health Trust") were confirmed via direct A/B testing to already fail
   identically before this remediation — not a regression.

None of these are WRONG-CLEAN findings and none are systemic to the fixed
mechanism; per the automation gate ("safe additional review... is
acceptable within reason... safety takes priority over marginal
automation"), they belong on the post-ship backlog.

## Stop-rule application

All four stop-rule conditions are met: the dedicated development benchmark
passes (wrong_clean=0/80), the locked 393-case regression replay
eliminates the known defect without material regression (WC 6→0, recall
improved), the fresh 167-case remediation corpus clears every hard gate
(WC=0, semantic→authority=0, fabricated-evidence→authority=0, determinism
=100%), and no new WRONG-CLEAN systemic mechanism was found. Per the
explicit stop rule: **STOP. Do not create Step 4A.11.3. Do not run another
corpus. Do not continue optimizing safe review cases.**

The four newly-surfaced FE-only findings above move to the post-ship
backlog alongside the two already-disclosed findings from the original
final report (ALL-CAPS `is_operative_context` heading limitation;
liability's missing broad discovery signal).

## STEP 4B: AUTHORIZED.
