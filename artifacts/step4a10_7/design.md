# Step 4A.10.7 — Reciprocal-Opener Discovery Generalization: Design

## Scope (narrow, per the user's explicit constraint)

Only `_MUTUAL_RECIPROCAL_RE` (the discovery-layer gate for the
dedicated reciprocal-obligation extraction path) was touched. The
symmetry comparator itself (`_detect_reciprocal_asymmetry`,
`role_texts_structurally_equivalent`, `established_equal_fn`,
`_classify_self_response_control`, `_equal_treatment_cue_present`, and
every per-dimension classifier) is byte-identical to the Step 4A.10.6
frozen state — its own frozen evidence was excellent and the user's
rule was explicit: do not touch it absent new evidence it's defective.
None surfaced.

## Root causes (from Step 4A.10.6's own CR results)

Two closed-vocabulary discovery gaps, both in `_MUTUAL_RECIPROCAL_RE`:

1. **Subject quantifier and verb modal hardcoded**: only "each party ...
   shall indemnify ... the other" was recognized. "Either party shall
   indemnify and hold harmless the other..." — a routine synonym —
   fell through entirely, because `_OBLIGATION_RE`'s own named-role
   path already accepts shall/will/agrees-to but the mutual-opener path
   never did, and "each" was the only quantifier recognized at all.
   Generalized the subject to the small, genuinely closed, finite class
   of English reciprocal quantifiers (each/either/both/every) — the
   same reasoning already used to extend `WORD_NUMBERS` in Step
   4A.10.5 (a closed function-word set, not an open domain-phrase
   list) — and the verb modal to match `_OBLIGATION_RE`'s own
   shall/will/agrees-to set.
2. **A second, distinct opener SHAPE never recognized at all**: a
   nominalized statement of the duty ("Each party's indemnification
   duty ... binds/applies to/governs X and Y identically") rather than
   a verb-phrase sentence. Still squarely reciprocal-opener discovery —
   both shapes assert the same underlying fact, a reciprocal
   indemnification obligation exists — just expressed as a noun phrase
   instead of a verb. Added as a second alternative in the same regex.
3. Also added "one another" as a synonym object for "each other" in the
   pre-existing "the parties shall [mutually] indemnify each other"
   alternative.

## A real bug found and fixed during this step's own dev iteration

The first draft of the "one another" addition moved the optional
"mutually" token to the wrong position (after "indemnify" instead of
before), which silently broke the ALREADY-WORKING "the parties shall
**mutually** indemnify each other" pattern — caught immediately by the
existing regression suite (`test_indemnification_benchmark_gate.py`'s
`reciprocal-02` case, plus 3 false-safe cases in
`run_indemnification_asymmetry_benchmark.py`, plus the Step 4A.10.1 dev
symmetry benchmark's CS dropping from 19 to 13). Fixed by restoring
"mutually" to its correct position before "indemnify"; full regression
returned to byte-identical immediately after.

## Development iteration (non-authoritative)

Dev-replay of all four previously-built, now-non-authoritative frozen
corpora (4A.10.4, the burned 4A.10.5, 4A.10.5b, 4A.10.6):

| Corpus | Symmetric recall before | Symmetric recall after | FA | FS |
|---|---|---|---|---|
| 4A.10.4 (187 cases) | 42/66 | 51/66 | 0 | 0 |
| 4A.10.5 (202 cases) | 62/66 | 66/66 | 0 | 0 |
| 4A.10.5b (207 cases) | 62/71 | **71/71 (100%)** | 0 | 0 |
| 4A.10.6 (214 cases) | 60/70 | **70/70 (100%)** | 0 | 0 |

The 11/11 adversarial controls from Step 4A.10.6
(`step4a10_6_dev_adversarial_controls.py`) still pass unchanged —
confirming this step did not disturb the defense-control mechanism.

Per the user's methodology (already established in prior steps of this
program), no authoritative frozen corpus was built until this dev/
adversarial iteration was complete and the code was stable.
