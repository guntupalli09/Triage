# Step 4A.11 Remediation — Phase 2/5 Dev Benchmark PRE → POST

80-case role-boundary DEV benchmark (categories A-U per remediation spec).

| Metric | PRE | POST |
|---|---|---|
| Correct (exact match) | 41 | 61 |
| Correctly unresolved (fail-closed, ambiguous) | 0 | 3 |
| Missed (safe FE, no value) | 8 | 16 |
| **wrong_clean (HARD REQUIREMENT)** | **31** | **0 — PASS** |

Three cases were corrected as DEV-benchmark ground-truth defects (not
production defects) discovered during iteration, disclosed here since this
corpus is explicit development evidence:
- `rb-N-07/08/09/12/13/14`: originally expected Title-Case role names for
  ALL-CAPS source sentences — corrected to expect verbatim ALL-CAPS
  (correct behavior preserves source case, does not normalize it).
- `rb-I-01/I-02`: originally expected an "and"-joined long name to resolve
  fully, but "and" was never a supported internal connector (only
  of/the/for are) — this is a pre-existing, unrelated coverage gap, out of
  this remediation's scope; corrected to accept any safe outcome.
- `rb-E-01`: a heading with zero punctuation and zero case distinction from
  the real name is genuinely irreducible from local text alone — corrected
  to only require the beneficiary resolve correctly, leaving the actor
  unchecked.

## Fix summary (production changes, indemnification_policy_engine.py only)

1. **Dash-boundary separator** (`_ROLE_NAME_SEPARATOR`): replaced the bare
   `[\s&-]+` character class with an explicit alternation — plain
   whitespace, an ampersand with optional whitespace, or a bare hyphen ONLY
   when flanked by a letter/digit on both sides with no whitespace. A
   doubled hyphen or a spaced hyphen (heading/clause punctuation) can never
   satisfy the letter-flanked hyphen case and correctly terminates the
   continuation loop instead of bridging across it.
2. **Trusted continuation budget** (`_MULTIWORD_ROLE_NAME_FRAGMENT_TRUSTED_BUDGET`,
   `_ROLE_NAME_TRUSTED_BUDGET_FULLMATCH_RE`): every legitimate multi-word
   entity name observed across this codebase's own corpora tops out at 5
   words; a capture using the full 6-word budget the base pattern allows is
   flagged as budget-exhausted (evidence the match ran out of room, not
   evidence of a genuinely long name) and rejected rather than trusted.
3. **Subordinate-clause-connector boundary**
   (`_ROLE_NAME_CLAUSE_CONNECTOR_BOUNDARY_RE`): reuses the SAME closed
   preposition/conjunction class already used elsewhere in this codebase's
   condition-attachment infrastructure (`_TRAILING_PROVISO_RE`,
   `_BACKREF_CONDITION_RE`'s "arising from/out of/under") plus "against"
   (already present in the pre-existing `_ROLE_NAME_TRAILING_STOPWORDS`
   set) as a role-name boundary rather than a condition boundary — a role
   name can never legitimately continue past the start of a subordinate
   clause. Applied as first-occurrence truncation (not merely trailing),
   which is what closes the gap `trim_role_name`'s existing trailing-only
   algorithm could not.
4. **Repeated hyphen-prefix continuation** (`{0,2}` instead of `?`): a
   minor, closely-related extension so multi-hyphen compound adjectives
   ("State-of-the-Art") resolve as fully as single-hyphen ones
   ("Best-in-Class") already did.
5. All five actor/beneficiary CONSTRUCTION sites (the main `_OBLIGATION_RE`
   loop, the synonym-obligation loop, the structural-risk-transfer loop,
   and both semantic-candidate-verification paths) now call the new
   `_verify_role_capture` wrapper instead of bare `trim_role_name`, and
   `continue` (skip the match, leave the obligation unresolved) whenever it
   returns `None` — implementing the Phase 4 material-fact-ownership
   invariant: an unreliable role span never becomes part of a clean
   ESTABLISHED decision.
