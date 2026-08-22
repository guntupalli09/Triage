# Step 4A.10.9 — Role-Name Boundary & Tokenization Generalization: Design

## Scope

`_MULTIWORD_ROLE_NAME_FRAGMENT` (the single shared role-name capture
fragment reused across ~15 regexes in `indemnification_policy_engine.py`)
and its two filtering call sites. The symmetry comparator and
equal-treatment-cue masking logic from Step 4A.10.8 are untouched —
that mechanism's own frozen evidence (FS=0/136, asymmetric recall
100%) was excellent, and no new evidence surfaced that it is defective.

## What changed

The prior fragment required plain WHITESPACE between every constituent
word. Generalized to a TOKEN + CONNECTOR model:

- **First token**: unchanged — must be an ordinary capitalized word
  (`[A-Z][A-Za-z]{1,25}`). This is what keeps a match from starting on
  an isolated stray letter or digit in ordinary prose.
- **Continuation tokens**: an ordinary capitalized word, OR a bare
  designator (single capital letter not followed by another letter —
  "B" in "Class B" — or a 1-3 digit run — "1" in "Tier-1"), OR a dotted
  abbreviation (`(?:[A-Z]\.){1,4}` — "U.S.", tried before the
  single-letter alternative so it isn't preempted by matching just the
  first letter).
- **Connector between tokens**: whitespace, a hyphen, or an ampersand
  (`[\s&-]+`) — not whitespace alone.

## Over-capture guard

Allowing bare letters/digits as continuation tokens creates a new risk:
"Schedule A," "Section 2," "Exhibit B" now match the fragment as ONE
string ("schedule a" was never in the exact-match stoplist, only
"schedule" was). Fixed via `_role_name_first_word()`: reject a captured
fragment if its FIRST WORD ALONE (not the whole string) is a
document-structure/generic-role stoplist word, applied at the highest-
risk consumer (the bare `_NAMED_ROLE_MENTION_RE` scan in
`_detect_reciprocal_asymmetry`'s general discovery block).

## A real, distinct bug found and fixed during this step's own iteration

Once a role name can itself contain an internal period (a dotted
abbreviation like "Non-U.S. Distributor"), the pre-existing sentence-
boundary heuristic (`re.search(r"\.\s|\.$", window[start:hi])`,
searching from the role's own START offset) could match that internal
period and mistake it for the clause's end — truncating the role's
local span down to just "Non-U.S. " and losing all real content after
it (a genuine FA risk, caught immediately by this step's own dev
adversarial suite). Fixed by starting the boundary search AFTER the
role name's own captured length (`start + len(role)`), not at `start`.

## Development iteration (exhaustive, per the user's mandate)

New `scripts/step4a10_9_dev_adversarial_controls.py`: every construction
the user named — Cross-Border Agent, Sub-Processor, Tier-1 Supplier,
Class B Purchaser, Non-U.S. Distributor, ordinary multi-word roles with
no punctuation — tested in both genuinely-asymmetric and genuinely-
symmetric form, plus over-capture guards (Schedule A/B, Section 2/3,
Exhibit A/B, Annex 1/2, and an ampersand-joined corporate name "Smith &
Co." that surfaced a second real gap, fixed by adding "&" as a valid
connector). 16/16 pass after both fixes.

Step 4A.10.6's 11-case suite (defense-control) and Step 4A.10.8's
96-case suite (opener x dimension matrix) both still pass 11/11 and
96/96, confirming neither prior mechanism was disturbed.

Dev-replay of all 6 previously-built, non-authoritative frozen corpora
(4A.10.4 through 4A.10.8): **FS=0 across all six**, including 4A.10.8's
own corpus — its FA dropped from 4/58 to 0/58 (the exact "Cross-Border
Agent" bug this step targets), confirming symmetric recall there is now
58/58 (100%).
