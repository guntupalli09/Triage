# Step 4A.10.9 — Role-Name Boundary & Tokenization Generalization: Final Report

## Executive verdict

**FAILED. FS = 16/170 on the authoritative frozen corpus — a real,
dangerous, and severe safety regression, all 16 cases sharing one exact
root cause. The 4A.10.x sequence does NOT stop and Step 4A.11 is NOT
authorized.** This is a different and more serious failure mode than
either Step 4A.10.7 (false symmetry via a wrong comparison) or Step
4A.10.8/earlier FA findings (false asymmetry via an over-strict
comparison): here the comparison mechanism never runs at all, and its
silent abstention defaults to "clean," which is exactly the failure
mode the whole Step 4A.10.x program exists to close.

## Root cause: dotted abbreviations cannot start a role name

`_ROLE_NAME_FIRST_TOKEN` (the required shape of the FIRST token in a
role-name match) was kept as `[A-Z][A-Za-z]{1,25}` — an ordinary
capitalized word, unchanged from before this step, deliberately as the
precision guard against starting a match on a stray letter in prose.
Dotted abbreviations (`(?:[A-Z]\.){1,4}`, e.g. "U.K.", "U.S.") were
added ONLY as a valid CONTINUATION token, never considered as a
possible FIRST token.

**Consequence**: a role name that itself BEGINS with a dotted
abbreviation ("U.K. Distributor," "U.S. Distributor") can never be
captured with its distinguishing prefix at all — the regex cannot
start matching at "U," since "U" alone (followed immediately by a
period, not a letter) fails the first-token requirement. The match
engine simply skips forward to the next word that DOES satisfy the
first-token shape: "Distributor." Both "U.K. Distributor" and "U.S.
Distributor" are captured as the SAME bare word, "Distributor" —
deduplicated by the existing case-insensitive dedup logic into a
single "role." With fewer than 2 distinct roles found, the entire
comparison block (`len(distinct_roles) >= 2 and ...`) never engages —
`_detect_reciprocal_asymmetry` returns an empty reasons list not
because it verified the two obligations match, but because it never
even recognized there were two obligations to compare.

Confirmed directly:
```python
>>> [trim_role_name(m.group(1)) for m in _NAMED_ROLE_MENTION_RE.finditer(text)]
['Each', 'Agreement', 'Distributor', 'Distributor']
```
Both the genuinely-asymmetric ("capped at $220,000" vs. "no cap at
all") AND the genuinely-symmetric version of this construction produce
the identical empty-reasons result — the symmetric case happens to land
on the correct label (CS) but for the wrong reason (silent abstention,
not verification), which is itself concerning: it means a clean
"symmetric" result can currently be produced with zero comparison ever
having occurred, for this one construction shape.

## Why this matters more than a narrow miss

Every one of Step 4A.10.9's OWN dev-adversarial tests for dotted
abbreviations used "Non-U.S. Distributor" — where the abbreviation is
NOT the first token (it follows "Non-"), so the first-token requirement
was satisfied by "Non" and the bug never manifested in development.
The authoritative corpus independently chose "U.K. Distributor" /
"U.S. Distributor" — where the abbreviation IS the first token — and
found the gap the dev suite's specific phrasing choice had missed. This
is exactly why the corpus must be built without seeing the fix's own
test cases: it found a real edge the adversarial suite didn't cover,
not a corpus-authoring artifact.

## Not patched here

Per the standing rule for this whole 4A.10.x sequence — freeze, lock,
run exactly once, accept whatever results, no code changes in response
to a specific corpus's own results — this defect is NOT fixed in this
report. The frozen result stands as reported: **FAILED**.

## Everything else, for completeness

- Every OTHER role-construction class the user named (hyphenated
  multi-word, hyphenated single-word pair, hyphen+digit designator,
  space+letter designator, ampersand-joined) scored cleanly — the FS
  failures are 100% isolated to the "abbreviation-as-first-token"
  shape, not a broader regression of this step's work.
- Over-capture guards (Schedule/Section/Exhibit/Annex references) all
  passed — 0 false roles from document-structure language.
- Production hashes unchanged pre/post execution; determinism
  confirmed byte-identical; zero UNVERIFIED-fact violations by the
  narrow self-flagged/role-conflict check; full regression (pytest,
  historical benchmarks) clean throughout — this is a narrowly isolated
  defect, not a broad regression.

## Hard gates — honest evaluation

| Gate | Target | Result | Met? |
|---|---|---|---|
| FS | 0 | **16/170** | **NO — FAILED** |
| FA | ≤5% | 0/65 = 0% | YES |
| Symmetric recall | ≥95% | 65/65 = 100% | YES |
| Asymmetric recall | ≥95% | 154/170 = 90.6% (also depressed by the same root cause) | NO |
| Zero policy-changing UNVERIFIED facts | required | 0 by the narrow check, but see the note below — this finding IS a policy-changing unverified-fact problem in substance, just not one the narrow self-flagged/conflict check was built to detect | See note |
| Authoritative determinism | 100% | byte-identical re-run | YES |

**Note on the UNVERIFIED-facts gate**: the narrow mechanical check (no
`self_flagged_unresolved`, no `role_side_conflict_reasons` on any CS
case) reports 0 violations, but this finding shows a case landing on
"clean symmetric" with NO comparison ever executed at all — a role
merge caused by the tokenizer, not a self-flagged fact. This is the
same underlying concern the gate is meant to catch, surfacing through a
different mechanism than the one the check currently looks for. Flagged
honestly rather than reported as a clean pass.

## Required next step (not undertaken here)

A narrowly-scoped follow-up should widen `_ROLE_NAME_FIRST_TOKEN` to
also accept a dotted abbreviation as a valid FIRST token (mirroring
what continuation tokens already accept), with care to keep the
existing precision guard against starting a match on a stray
non-role initialism in ordinary prose (e.g., requiring the abbreviation
be followed by a genuine word, not by lowercase prose continuing a
sentence). This should be validated against a SIXTH, still-different
frozen corpus specifically re-testing "abbreviation-as-first-token"
constructions ("U.K. Distributor," "N.A. Servicer," "U.S. Buyer," etc.)
before any gate-clearing claim is made again.

## Step 4A.11 / 4B authorization

Per the user's explicit bar, the 4A.10.x sequence does **NOT** stop
here. Step 4A.11 is **NOT authorized**. Step 4B remains **NOT
authorized**.
