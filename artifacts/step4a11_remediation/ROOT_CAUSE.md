# Step 4A.11 Remediation — Phase 1 Root Cause

## Mechanism located

`_MULTIWORD_ROLE_NAME_FRAGMENT` / `_ROLE_NAME_CONTINUATION_TOKEN`
(indemnification_policy_engine.py:164-207), the SOLE role-name-capture
building block shared by every structural pattern in the file (30+ regex
sites: `_OBLIGATION_RE`, `_MUTUAL_RECIPROCAL_RE`, all 11
`_STRUCTURAL_RISK_TRANSFER_PATTERNS`, the defense-control/monetary-cap/
condition-attachment role captures). A fix to this one fragment propagates
to every consumer.

## Two independent defects in the same fragment

**Defect 1 — dash-as-punctuation conflated with dash-as-word-joiner.**
The continuation separator `[\s&-]+` treats ANY run of whitespace/&/hyphen
characters identically. It cannot distinguish:
- ordinary space between words of one name (correct to continue)
- a single no-space hyphen joining two words of ONE compound name, e.g.
  "Best-Fenwick" (correct to continue — this is legitimate multi-word-name
  behavior, already relied on by real drafting)
- a spaced double-hyphen or em-dash used as PUNCTUATION marking a heading/
  clause boundary, e.g. "... OF X -- X SHALL ..." or "14. HEADING -- Actual
  Sentence." (must NOT continue — this is not part of any name)

Verified: `"Everline Packaging Systems -- Everline Packaging Systems"` is
captured as a single 6-word role name (hitting the `{0,5}` continuation
cap) because `" -- "` matches `[\s&-]+` exactly like an ordinary space.
Same mechanism produces `"RISK ALLOCATION -- Millbrook Staffing Partners"`
as a single actor name — the heading label bleeds into the real name across
the same dash-as-space collapse.

**Defect 2 — ALL-CAPS text removes the only signal that stops the match.**
The continuation-token alternation `[A-Z][A-Za-z]{1,25}` matches ANY
capitalized word, ordinary proper noun or not. In mixed-case text, an
ordinary connector/preposition ("from", "for", "arising") is lowercase and
naturally breaks the continuation loop — this is the ENTIRE mechanism that
keeps role captures bounded today. In an ALL-CAPS operative clause, every
word is capitalized, so this natural stopping signal is completely absent,
and the match runs to its hard structural limit (`{0,5}` = 6 words total)
regardless of what those words are.

Verified: `"Farrowmoor Publishing House FROM ANY THIRD"` is exactly 6 words
(1 initial + 5 continuations) — the capture did not stop at any semantic
boundary; it stopped only because the regex's own length budget was
exhausted. This means the defect is NOT specific to "FROM" or to any
particular connector word (confirmed by design, not just by this one
example) — ANY 5 additional ALL-CAPS words following a real role name will
be absorbed the same way, which is why Phase 2's benchmark tests the full
connector list (N) as attack EXAMPLES, not as a stop-word list to encode.

## Scope confirmed

- **Indemnification**: affected, systemically (shared fragment, 30+ sites).
- **Liability**: NOT affected. `_ROLE_POSITION_RE` captures a single bare
  word (`[A-Z][A-Za-z]{2,20}`) directly before `'s liability...` — no
  continuation loop exists, so there is nothing to over-consume.
- **Payment terms**: NOT affected. No structured party-name capture exists
  in this adapter at all (it extracts numeric dimensions like `net_days`
  from windows around anchor phrases, never a named-party identity).
- **Shared role-resolution infrastructure** (`policy_engine_core.py`): NOT
  affected. `_MULTIWORD_ROLE_NAME_FRAGMENT` is private to
  indemnification_policy_engine.py; policy_engine_core.py has no equivalent
  multi-word role-name regex of its own.

## Conclusion

One fragment, two independent boundary defects, systemic within
indemnification (every structural pattern shares the fragment) but
confined to indemnification (liability/payment_terms/shared core use
different, unaffected mechanisms). The fix belongs in
`_MULTIWORD_ROLE_NAME_FRAGMENT` itself, not in any individual pattern, and
not as a stop-word list (Defect 2 is general to ALL-CAPS runs, not specific
to any connector word).
