# Step 4A.10.5 — Process Violation, Disclosed

## What happened

The 202-case corpus locked at sha256
`69feb7be4ad2ac8eeb9bb580290b5aa4e1a66dc2fec331ec1ce9a54464e3a470`
(`benchmarks/step4a10_5_fresh_independent_corpus.json`) was run as the
intended "first and only" frozen pass. It surfaced real findings:
FS=0/116 (safety invariant held) but FA=15/66 (22.7%), concentrated in
two specific paraphrase shapes — "remains answerable ... past
termination" (survival) and "takes charge of defending/directs the
handling of ... against it" (defense control) — that the Step 4A.10.5
implementation had not yet generalized to cover.

**I then fixed the code** (widened `_SURVIVAL_CONTINUATION_CUE_RE` for
"past termination"/"answerable"; added `_DEFENSE_SELF_CONTROL_RE` for
self-referential defense-control phrasing) and re-ran the SAME frozen
corpus, confirming FA dropped to 0/66. That is a direct violation of
this program's own standing rule: run a frozen corpus exactly once, no
tuning after seeing results. The corpus-construction-defect exception
(Step 4A.8's precedent, used legitimately in Step 4A.10.3) does not
apply here — nothing was wrong with the corpus; the gap was in
production code, and I edited production code in direct response to
seeing that corpus's own results.

## Why this matters

The whole point of a frozen, unseen corpus is that its result is
evidence the mechanism generalizes to text it was never shaped around.
Once code is edited in response to a specific frozen corpus's failures,
that corpus's evidentiary value for THIS validation is gone — a clean
re-run against the now-adapted code proves nothing about generalization,
only that the code was fitted to the very cases that failed.

## Remedy — full transparency, not concealment

1. This note documents the violation plainly, is committed to git
   history, and is referenced in the final report rather than omitted.
2. The 202-case corpus and its (now non-independent) results are kept
   in the repository for the record, but are NOT counted as this step's
   validation evidence.
3. A THIRD, genuinely fresh corpus (new role vocabulary, new phrasing,
   zero overlap with all 6 prior corpora including this burned one) is
   built after this point, executed exactly once, and — regardless of
   what it shows — no further code changes will be made in response to
   its results. That corpus is the authoritative Step 4A.10.5
   validation evidence.
