# Step 4A.10.8 — Equal-Treatment Cue Structural Exclusion: Final Report

## Executive verdict

**FS = 0/136 on the authoritative frozen corpus — the core safety gate
is met, and asymmetric recall is 100% (136/136). FA = 4/58 (6.9%,
target ≤5%) and symmetric recall = 54/58 (93.1%, target ≥95%) narrowly
miss their targets — both traced to a single, precisely-identified,
PRE-EXISTING role-name tokenization gap (a hyphenated role name)
unrelated to the equal-treatment-cue architecture this step targeted.
This is NOT the Step 4A.10.7 failure repeating; it is a materially
different, much narrower, and clearly out-of-scope finding. Per the
user's stated bar, not all five gates were met, so the 4A.10.x sequence
does not stop and Step 4A.11 is not authorized — but the character of
what remains has changed again, now down to one isolated, well-
understood tokenization issue.**

## What this step did (recap)

Implemented the architectural rule specified: an equal-treatment cue
can override fail-closed comparison only when it independently asserts
equivalence of the relevant obligations or material dimension — never
because a reciprocal quantifier (each/either/both/every, "one another"/
"each other," the nominalized duty-binds shape) merely CREATED the two
obligations being compared.

`_equal_treatment_cue_present` now masks every `_MUTUAL_RECIPROCAL_RE`
match out of the text before scanning for cue words. This is
structural, not a "both" special case: it reuses whatever the opener-
discovery regex already recognizes, so it covers every quantifier and
opener shape uniformly and stays correct if that regex changes again.

A related bug (`_GENERIC_ROLE_WORDS` missing "every," introduced in
Step 4A.10.7 but never propagated to the role stoplist) was found and
fixed during development.

## Development iteration (exhaustive, per the user's mandate)

Before any freeze, `scripts/step4a10_8_dev_adversarial_controls.py`
crossed every reciprocal-opener shape (each/either/both/every/"one
another"/"mutually...each other") with a downstream difference in each
of the user's eight named dimensions (scope, survival, cap, causation,
defense control, claim category, proviso, cross-reference), both
asymmetric and symmetric versions — 96/96 passed after the two fixes
above. Step 4A.10.6's own 11-case adversarial suite still passed
11/11 (defense-control confirmed undisturbed). Dev-replay of all 5
previously-built, non-authoritative frozen corpora showed FS=0 across
all five, including Step 4A.10.7's own corpus (0/124, was 4/124
authoritative).

## Authoritative frozen results (first and only pass)

Corpus: `benchmarks/step4a10_8_fresh_independent_corpus.json`, 212
cases, sha256 `da8bd1577dc6879cc073a8ff14a6434b89a6645dd35cf22ac9c41eaab04a4719`.
New role-pair vocabulary; 48 cases directly crossing reciprocal-opener
shapes with the eight mandated dimensions (both asymmetric and
symmetric); the standard 12-family asymmetric set plus compound for
full regression confirmation; non-canonical and nominalized generic
openers; defense-control and cue regression; ambiguous cases. Zero
exact-text overlap against all 9 prior corpora; 0/212 discovery
failures.

```
OVERALL: {'CA': 136, 'FA': 4, 'CS': 54, 'CR': 6, 'WC': 12}

By label:
  ASYMMETRIC: 136/136 CA (100%)
  SYMMETRIC:  54 CS, 4 FA (0 CR — no discovery misses at all)
  AMBIGUOUS:  6 CR, 12 WC (expected/pre-existing, not scored against this step's gates)

FS (dangerous) total: 0/136
```

**Every dimension family — all 8 opener×dimension combinations AND all
12 standard asymmetric families AND compound — scored 100% CA.** The
opener-masking fix and the "every" stoplist fix both hold cleanly
across the entire matrix.

## Root cause of the 4 FA (single, isolated, pre-existing)

All four failures involve the same role name: **"Cross-Border Agent."**
The hyphen breaks `_MULTIWORD_ROLE_NAME_FRAGMENT`
(`[A-Z][A-Za-z]{1,25}(?:\s+[A-Z][A-Za-z]{1,25}){0,4}`), which requires
WHITESPACE between constituent words, not a hyphen. Confirmed directly:

```python
>>> [trim_role_name(m.group(1)) for m in _NAMED_ROLE_MENTION_RE.finditer(text)]
['Each', 'Cross', 'Border Agent', 'Local Distributor']
```

"Cross-Border Agent" splits into two spurious "roles" ("Cross" and
"Border Agent"), producing 3 distinct roles instead of 2 and corrupting
the pairwise structural comparison for every case that happened to
cycle onto this role pair (4 of the corpus's 8 role-pair slots landed
on cases using this name across the opener×dimension matrix).

This is the SAME class of limitation already found and disclosed during
Step 4A.10.6's own adversarial iteration (single-letter suffixes like
"Vendor A"/"Series A Investor" breaking the same regex for the same
structural reason — no whitespace-delimited multiword match). It is a
**pre-existing role-name tokenization gap**, not a defect in
`_equal_treatment_cue_present`'s masking logic or anything else this
step built. It surfaced here only because "Cross-Border Agent" happened
to be one of eight role names I chose for this corpus — a corpus-
vocabulary selection that exposed a known class of gap, not a new
defect introduced by this step's own change. Per the user's own
correction to the Step 4A.10.7 report, this is disclosed as real,
standing evidence of a generalization boundary (hyphenated/
non-whitespace-delimited multi-token role names), not discounted
because it hurt the FA count.

## Hard gates — honest evaluation

| Gate | Target | Result | Met? |
|---|---|---|---|
| FS | 0 | **0/136** | **YES** |
| FA | ≤5% | 4/58 = 6.9% | NO (narrowly; single isolated root cause) |
| Symmetric recall | ≥95% | 54/58 = 93.1% | NO (same single root cause) |
| Asymmetric recall | ≥95% | **136/136 = 100%** | **YES** |
| UNVERIFIED fact supporting clean symmetry | 0 | 0 (checked directly) | **YES** |
| Authoritative determinism | 100% | byte-identical re-run | **YES** |

**4 of 6 gates met.** The two misses share one precisely-isolated,
pre-existing, out-of-scope cause.

## What changed from Step 4A.10.7

Step 4A.10.7 failed on the SAFETY gate (FS=4) with a defect squarely
inside the mechanism under test (the cue itself misreading the opener's
own grammar). Step 4A.10.8 passes the safety gate cleanly (FS=0,
asymmetric recall 100%) and misses only the selectivity gates, by a
narrow margin, for a reason entirely OUTSIDE the mechanism under test
(role-name tokenization, a different subsystem `_MULTIWORD_ROLE_NAME_
FRAGMENT` that predates this whole sub-program). This is real progress,
honestly measured — not glossed over because it's "close."

## Step 4A.11 / 4B authorization

Per the user's explicit bar, not every listed gate was cleared, so the
4A.10.x sequence does **NOT** stop here and Step 4A.11 is **NOT**
authorized. Recommend a narrowly-scoped **Step 4A.10.9 — Hyphenated/
Compound Role-Name Tokenization** (widen
`_MULTIWORD_ROLE_NAME_FRAGMENT` to accept a hyphen as a valid
inter-word connector, alongside the existing capitalized-word
continuation, mirroring how apostrophes are already tolerated
elsewhere) before the next validation attempt — this is a role-name
PARSING fix, not a comparator or discovery-opener change, and should be
even narrower in scope than 4A.10.7/4A.10.8 were.

**Step 4B: NOT authorized** (unchanged).
