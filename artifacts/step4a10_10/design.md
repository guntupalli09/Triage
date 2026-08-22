# Step 4A.10.10 — Final Stabilization Pass: Design

## Scope

Final pre-ship pass per the user's explicit directive: (1) fix the
Step 4A.10.9 dotted-abbreviation-as-first-token bug generically, (2)
add a fail-closed cardinality invariant so a single-role extraction
failure can never again silently default to symmetric, (3) run every
regression suite, (4) build and run one final, comprehensive frozen
corpus, (5) ship if the safety gates (not the selectivity gates) are
met.

## Fix 1 — leading dotted abbreviations

`_MULTIWORD_ROLE_NAME_FRAGMENT`'s FIRST-token shape now accepts either
an ordinary capitalized word (unchanged) OR a dotted abbreviation
(`(?:[A-Z]\.){1,4}`) — but ONLY when followed by at least one more
token (`{1,5}`, not `{0,5}`), so a bare abbreviation in ordinary prose
("under U.S. law") can never match alone. "U.K. Distributor" and "U.S.
Distributor" are now captured as two full, distinct role names.

## Fix 2 — the cardinality fail-closed invariant

New rule in `_detect_reciprocal_asymmetry`: if a reciprocal/mutual
opener is present AND exactly one distinct, comparable named role was
extracted, the clause returns an unresolved ("requires review") reason
instead of silently falling through to an empty (implicitly-symmetric)
result. This is deliberately narrower than "zero roles found" (ordinary
"each party shall indemnify the other" boilerplate with no named-role
attribution attempt at all is not itself suspicious) — it fires only
when the clause plainly tried to attribute something to ONE specific
named party inside a reciprocal structure, and a second, comparable
attribution could not be confirmed. This is the general safety net Step
4A.10.9's bug should have been caught by regardless of which specific
tokenization gap caused it — a defense-in-depth invariant, not a patch
for one bug.

Confirmed as a real safety net (not merely code that happens to never
fire): tested directly against an apostrophe-led name shape the
tokenizer still doesn't handle ("O'Brien Holdings" appearing twice),
which the guard correctly caught and routed to review rather than
letting fall through as clean.

## Two regressions found and fixed via full regression re-run

The blunt version of the cardinality guard (fire on ANY single-role
case) broke 3 previously-passing historical regression cases —
`multi-reciprocal-01`, `asym-03`, `asym-25` — all because a SPURIOUS
single "role" (a bare 2-letter abbreviation like "IP" swept up from "IP
infringement"/"IP Indemnification" section headings, or "Order Form," a
document reference) was being treated as a genuine single-role
attribution. Fixed two ways:
- `_looks_like_plausible_role_name`: the cardinality guard only fires
  when the lone captured "role" is multi-word OR a single token longer
  than 3 characters — excludes bare short abbreviations without
  excluding genuine short names.
- `_role_name_any_word_is_structural` (generalizing the prior
  first-word-only check): rejects a captured fragment if ANY of its
  words, not just the first, is a document-structure/generic-role
  stoplist word — catches "IP Indemnification" (second word
  "Indemnification" already stoplisted) and "Order Form" (both words
  newly added to the stoplist).

After both fixes, all 3 previously-broken historical regression cases
pass again, and both the dotted-abbreviation fix's target case and the
apostrophe-name adversarial test still work correctly.

## Full regression (all suites)

- `pytest` (relevant policy-engine test files): 213/213 pass.
- `step4a7_reciprocal_semantic_benchmark` /
  `indemnification_asymmetry_benchmark`: byte-identical vs. the
  pre-4A.10.1 baseline.
- Step 4A.10.1 symmetry benchmark: CS=19, CA=72 unchanged; FS=0; CR rose
  29→33 (net improvement — cases the cardinality guard now correctly
  routes to review that previously fell through as
  `FE_missed_ambiguity`, which dropped 12→8).
- Step 4A.10.2 dev controls: CA=8, CS=10 unchanged; no FA; WC improved
  6→5.
- Step 4A.10.1 S4 benchmark: false-operative-extraction unchanged at
  0/50.
- Steps 4A.10.6/4A.10.8/4A.10.9's adversarial dev suites: 11/11, 96/96,
  16/16 — all still pass.
- Dev-replay of all 7 previously-built, non-authoritative frozen
  corpora (4A.10.4 through the failed 4A.10.9): **FS=0 across all
  seven**, including 4A.10.9's own corpus (FS 16→0, CA 154→170 =
  100%). One new FA appears on 4A.10.9's corpus replay (a
  causation-dimension case, same "untracked paraphrase + trailing-
  connector" pattern already documented repeatedly in this program) —
  a conservative false-escalation, not a safety issue, left for the
  post-ship hardening backlog per the user's shipping bar.

## The final, authoritative frozen corpus

Per the user's instruction not to build another endless family-
specific benchmark, the final corpus (`step4a10_10_final_validation_
corpus.json`) is broader-spectrum: it samples across every dimension
family and mechanism this whole 4A.10.x program touched (role
attribution, defense control, equal-treatment cue masking, reciprocal-
opener discovery, role-name tokenization including the exact
abbreviation-first-token shape that failed) rather than drilling one
narrow construction. See the frozen results section below.
