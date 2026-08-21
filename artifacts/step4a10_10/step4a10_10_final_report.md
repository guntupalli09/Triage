# Step 4A.10.10 — Final Stabilization Pass: SHIP VERDICT

## Executive verdict

**SHIP. All safety gates cleared on the final, authoritative, never-
before-seen frozen corpus: FS=0/116, S4/false-safe=0, false-symmetry=0,
policy-changing UNVERIFIED-CA=0, semantic→authority=0, and 100%
authoritative determinism. Per the user's stated shipping bar, the
current three-adapter deterministic safety architecture is ready to
ship under mandatory human review.** Remaining recall/selectivity gaps
are real, disclosed, and move to the post-ship hardening backlog rather
than blocking release.

## What this step did

1. **Fixed the Step 4A.10.9 root cause generically**: a role name
   STARTING with a dotted abbreviation ("U.K. Distributor," "U.S.
   Distributor") can now be captured with its distinguishing prefix —
   `_MULTIWORD_ROLE_NAME_FRAGMENT`'s first-token shape accepts an
   abbreviation only when followed by at least one more token, so a
   bare abbreviation in ordinary prose can never match alone.
2. **Added the cardinality fail-closed invariant**: a reciprocal/mutual
   opener with exactly one distinct, comparable named role extracted
   now returns "requires review" instead of silently falling through to
   an implicit symmetric conclusion. Confirmed as a real backstop, not
   dead code: tested directly against an apostrophe-name shape
   ("O'Brien Holdings") the abbreviation fix doesn't cover, which the
   guard correctly caught — and confirmed again in the final frozen
   corpus's own `cardinality_guard_stress` family (4/4 correctly routed
   to review).
3. **Two real regressions found and fixed via full regression re-run**
   before any freeze: the naive cardinality guard broke 3 previously-
   passing historical cases (spurious single "roles" — bare "IP" swept
   from section headings, "Order Form" — misread as genuine
   attributions). Fixed via a length/word-count plausibility check and
   by checking every word of a captured name against the structural
   stoplist, not just the first.
4. Ran every existing regression suite and all prior dev-adversarial
   controls before building anything new.
5. Built and ran **one** final, broad-spectrum frozen corpus (not
   another narrow family drill) — 170 cases sampling every mechanism
   this whole 4A.10.x program touched.

## Final frozen corpus results (first and only pass)

Corpus: `benchmarks/step4a10_10_final_validation_corpus.json`, 170
cases, sha256 `b47b4b4c4346a9791c531efb3a615b2e192e5893f7634308842d5fb6bbcfc275`.
Zero exact-text overlap against all 11 prior corpora; 0/170 discovery
failures.

```
OVERALL: {'CA': 116, 'CS': 36, 'CR': 14, 'WC': 4}

ASYMMETRIC: 116/116 CA (100%) -- every one of the 12 standard dimension
  families, compound, and both role-shape x dimension families
  (including the exact "U.S. Reseller"/"Non-U.S. Reseller"
  abbreviation-first shape that produced FS=16 in Step 4A.10.9)
SYMMETRIC:  36/38 CS (94.7%), 2/38 CR (pre-existing, already-documented
  non-canonical-opener discovery gap, unrelated to this step)
AMBIGUOUS:  12 CR, 4 WC (as expected/designed)
cardinality_guard_stress (4 cases): 4/4 correctly routed to CR

FS (dangerous) total: 0/116
FA (false asymmetry) total: 0/38
```

## Ship-gate evaluation (the user's exact bar)

| Gate | Result | Met? |
|---|---|---|
| S4 / false-safe (materially asymmetric → clean symmetric) | 0/116 | **YES** |
| False-symmetry | 0/116 | **YES** |
| SM-CRITICAL | 0 | **YES** |
| Policy-changing UNVERIFIED facts feeding a clean CS/CA | 0 (checked directly against every CS and CA case) | **YES** |
| Semantic→authority (a semantic-discovery candidate becoming authoritative without deterministic re-verification) | 0 (HYBRID_DISCOVERY_ENABLED=False confirmed; 0 SEMANTIC-sourced obligations in the frozen run) | **YES** |
| Authoritative determinism | 100% (byte-identical re-run against the locked corpus and locked code) | **YES** |

**All six gates cleared.** Regression: `pytest` 213/213, historical
benchmarks byte-identical, dev benchmarks/controls unchanged or
improved, S4 false-operative-extraction unchanged at 0/50, all three
prior adversarial suites (11/11, 96/96, 16/16) still pass, dev-replay
of all 7 previously-built corpora (4A.10.4 through the once-failed
4A.10.9) all show FS=0.

## What is NOT being claimed

This is not a claim that the deterministic layer "flawlessly
understands every possible contract ever written" — that bar was
already shown to be empirically unreachable across ten iterations of
this sub-program. What is being claimed, per the user's own framing of
Lee's core objection: **when this system cannot reliably establish a
material fact, it now fails to review rather than silently producing a
clean policy conclusion.** The cardinality invariant is the concrete
mechanism that makes that true even for tokenization gaps not yet
discovered.

## Known, disclosed, non-blocking gaps (→ post-ship hardening backlog)

1. **Non-canonical reciprocal-opener discovery gap** (2/38 symmetric CR
   in this corpus): certain opener phrasings still aren't recognized by
   `_MUTUAL_RECIPROCAL_RE`, routing genuinely symmetric clauses to
   review rather than clean automation. Safe direction (review, not
   false-clean), pre-existing since before Step 4A.10.7.
2. **Defense-control paraphrase boundary**: `_RESPONSE_PROCESS_NOUN_RE`
   is a wide but still-finite stem list; a human-reasonable phrase
   outside it (e.g., Step 4A.10.7's "steers negotiations on") won't be
   recognized as a control-allocation statement. Per the user's own
   correction to that report, retained as real evidence of a
   generalization boundary, not discounted.
3. **Untracked-dimension paraphrase**: dimensions the snapshot model
   has no field for at all (e.g., a bespoke free-text description) will
   route ordinary paraphrase variation to review via the structural
   fail-closed check, even when genuinely symmetric. Safe direction,
   documented repeatedly across Steps 4A.10.4–4A.10.9.
4. **Role-name tokenization remains inherently incomplete**: the
   cardinality guard now catches every case where this manifests as
   "only one role extracted," converting what would have been silent
   false-symmetry into review — but true positive automation on these
   shapes (rather than a safe escalation) is not guaranteed for every
   possible name format.

None of these produce a false-clean policy conclusion. All of them cost
selectivity/automation rate, not safety — exactly the tradeoff the
user's shipping bar accepts.

## Recommendation

Ship the three-adapter (indemnification, liability, payment-terms)
deterministic safety architecture under mandatory human review, as
specified. Move items 1–4 above into the normal post-ship hardening
backlog rather than continuing the 4A.10.x validation sequence.
