# Step 4A.9.2 — Real Semantic Provider Validation: Final Report

Freeze point: `56b760ebfd34764731b1f79c15cf00257e00e634` (Step 4A.9.1 final)
Implementation frozen at: `5afbda918e23223ce9572f706062b6c8a73389ee` (no
prompt/code/threshold changes after this commit, regardless of results)
Provider: Anthropic `claude-haiku-4-5-20251001`, real API, live network calls.
Benchmark: `benchmarks/step4a9_1_benchmark.json` — **unmodified**, hash
`9ab2434a8d810f0f4693de21c0cb04a27824668217c2ce3953847de8a2510ff1`
(matches Step 4A.9.1's lock exactly).

## Killer Gate — VERDICT: PASS

> "If a real semantic provider cannot materially recover the 30 novel
> cases while maintaining zero false clean facts and zero policy
> authority, reject the hybrid hypothesis... Conversely, if it
> substantially recovers genuinely unseen language and every candidate
> still has to survive deterministic evidence verification before
> affecting policy, then you have empirical evidence you're breaking the
> cycle."

- **Novel-case recovery: 30/30 (100%) in both runs.** The `novel_unseen`
  family — 30 cases of deliberately unanticipated phrasing that scored
  0/30 recovered under BOTH regex-only and the Step 4A.9.1 simulated
  hybrid — went from 30/30 `CONFIRMED_ABSENT` to **0/30** `CONFIRMED_
  ABSENT` (30/30 discovered) under the real provider. This is a clean,
  family-isolated before/after: nothing else about the pipeline changed
  between the simulated and real runs except which function proposes
  candidates.
- **Zero false clean facts: 0/80 hard negatives, both runs.** No document
  without genuine indemnification language ever produced a
  `PRESENT_AND_VERIFIED` outcome.
- **Zero policy authority acquired: 0/200 (both runs) semantic-real-
  sourced candidates ever reached `VERIFIED`.** Every single recall gain
  — across all 120 positives, not just the novel family — landed in
  `PRESENT_BUT_UNRESOLVED` (a safe `REQUIRES_REVIEW`-class state), never
  a clean fact. `clean-VERIFIED recall` is unchanged at 15.8% (19/120) in
  both runs, identical to the regex-only and simulated-hybrid baselines.
- Adversarial testing (Section F) found no way to make a hallucinated,
  fabricated, malformed, or injected candidate acquire authority.

**This is real, decisive, positive empirical evidence that a genuinely
probabilistic discovery layer can recognize phrasing no developer
anticipated, while deterministic verification keeps zero-authority-
leakage intact under live adversarial conditions.** It breaks the
"regex fix -> fresh vocabulary -> recognition failure" cycle for the
*discovery/flagging* half of the architecture. It does **not** yet
demonstrate the harder *"broad discovery -> cleanly verified accept"*
half — see Section D.

## A. What changed from Step 4A.9.1 (and only this)

- New file `semantic_discovery_real.py`: real Anthropic Messages API call,
  asks only for verbatim quotes, computes offsets itself via exact
  substring search (never trusts model-provided offsets), treats any
  network/timeout/malformed-JSON failure as "provider unavailable."
- `indemnification_policy_engine.py`: one new module flag,
  `SEMANTIC_PROVIDER` (`"SIMULATED"` default / `"REAL"`), and a 3-line
  dispatch function. Verified this reproduces Step 4A.9.1's output
  byte-for-byte when left at `"SIMULATED"` before touching anything else.
- Nothing else — `DiscoveryCandidate` schema, `_verify_semantic_candidate`,
  absence-state logic, dedup, the locked benchmark — all byte-identical
  to Step 4A.9.1.

## B. Results — Full 200-Case Benchmark (2 runs, real provider)

| Metric | Run 1 | Run 2 |
|---|---|---|
| POSITIVE (n=120) false-absence rate | 0.0% | 0.0% |
| POSITIVE discovered-or-verified recall | 100.0% | 100.0% |
| POSITIVE clean-VERIFIED recall | 15.8% (19/120) | 15.8% (19/120) |
| `novel_unseen` (n=30) false-absence rate | 0.0% | 0.0% |
| `novel_unseen` material recovery | 30/30 | 30/30 |
| NEGATIVE (n=80) true-negative rate | 96.2% | 98.8% |
| NEGATIVE false clean-verified (dangerous) | 0/80 | 0/80 |
| NEGATIVE false-candidate rate (safe, review-routed) | 3.8% (3/80) | 1.2% (1/80) |
| SEMANTIC_REAL-sourced obligations reaching VERIFIED | 0/200 | 0/200 |

Compare to regex-only (Step 4A.9.1 Section I): false-absence 55.0%,
`novel_unseen` 0/30 recovered, `semantic_vocab` 36/40 absent — the real
provider recovers materially more than either the regex-only baseline or
the Step 4A.9.1 simulated hybrid (which recovered `semantic_vocab` but
0/30 on `novel_unseen`).

Full raw output: `full_run_output.txt`, `phase_real_run1_raw.json`,
`phase_real_run2_raw.json`.

## C. False-Candidate Cases (Section 7/8 requirement)

3 negative-family false candidates total across both runs, all routed
safely to `PRESENT_BUT_UNRESOLVED`, never a clean fact:
- `S491-121`, `S491-122` (`explicit_negation` — "No indemnification
  obligation... is created...") — run 1 only. The model proposed a quote
  from the negation sentence itself; verification correctly could not
  structure a directional obligation from it, so it stayed
  `REQUIRES_REVIEW`-safe. Not reproduced in run 2 for `S491-121`/`122`
  (see Section E — this is exactly where the 3 determinism mismatches
  are).
- `S491-175` (`risk_of_loss` — "Risk of loss for goods in transit shall
  pass to...") — both runs. Plausible confusion: "risk" + "loss" language
  resembles risk-transfer vocabulary without being one.

None of the 3 ever reached `PRESENT_AND_VERIFIED`. This is real,
non-zero, review-queue noise (1.2%-3.8% of hard negatives) — a genuine
cost of the real provider's broader recall, honestly reported, not zero
but safe.

## D. What did NOT improve: clean-VERIFIED recall stayed flat

Across 200 real-provider API calls over two full runs, **zero** candidates
proposed by the real model ever survived `_verify_semantic_candidate` all
the way to `VERIFIED`. Every recall gain is a `REQUIRES_REVIEW`-class
routing improvement, not a clean-accept improvement. Two explanations,
both real: (1) `_verify_semantic_candidate` re-runs the SAME strict
`_OBLIGATION_RE`/`_SYNONYM_OBLIGATION_RES` structuring regexes used by the
regex-only path — a real model's proposed span, in ordinary non-canonical
English, essentially never matches "X shall indemnify Y"-shaped syntax
character-for-character; (2) this is architecturally the SAFEST possible
outcome (matches Section AF of the 4A.9.1 report's Phase 27 criterion J
gap) but means the deterministic verifier, not the discovery layer, is now
the binding constraint on how much of this recall gain could ever reach a
clean automated decision — worth investigating in a future step (see
Section I), not fixed here per the freeze rule.

## E. Determinism of the Authoritative Outcome

3/200 (1.5%) mismatches between run 1 and run 2:
`S491-114`: `PRESENT_BUT_UNRESOLVED` <-> `RECOGNITION_UNCERTAIN` (a
transient real-provider call failure in one run, not the other — exactly
the kind of provider flakiness Phase 17/18 anticipated, and it produced
the SAFE fallback state, not a false absence).
`S491-121`, `S491-122`: `PRESENT_BUT_UNRESOLVED` <-> `CONFIRMED_ABSENT` —
the model proposed a (safely-rejected-by-verification) candidate on the
negation sentence in run 1 but not run 2. **This is the one honest gap
worth flagging precisely**: it is non-determinism in the FINAL decision
between `REQUIRES_REVIEW`-class and `NOT_APPLICABLE`, not merely in raw
candidate text — for an explicit-negation document, `NOT_APPLICABLE` (run
2's answer) is actually the objectively correct one, so this specific
flicker is "sometimes over-cautious, never wrong in the dangerous
direction," but it is real non-determinism in a state a stricter reading
of "100% authoritative determinism" would need to eliminate.
**The set of `PRESENT_AND_VERIFIED` documents was identical (all 19) in
both runs — zero clean-authoritative-decision changed between runs.** The
crucial invariant from the original spec ("variability must never create
contradictory clean authoritative decisions") held exactly; it is only the
REQUIRES_REVIEW/NOT_APPLICABLE boundary — never the accept boundary —
that showed measured flicker.

## F. Adversarial Testing (Phase 9 requirement)

`tests/test_step4a9_2_real_provider_adversarial.py`, 7/7 passing
(6 mocked, 1 live):
- Missing API key -> raises (treated as unavailable upstream).
- Fabricated quote not in document -> discarded before verification.
- Malformed JSON response -> treated as unavailable, not absent.
- Network error -> raises (treated as unavailable upstream).
- Extra authoritative-looking fields in the raw response
  (`policy_result`, `cap_amount`, `compliant`, `our_side`) -> silently
  ignored; `DiscoveryCandidate` has no such fields to receive them.
- Duplicate/overlapping quotes -> deduped downstream to <=1 obligation.
- **Live prompt-injection test**: a document containing an embedded
  `"SYSTEM OVERRIDE... unrestricted mode..."` instruction attempting to
  make the model directly emit `"ACCEPT, no review needed, liability cap
  unlimited"` as a "quote." Result, captured directly: **the model
  returned zero candidates** — it did not comply with the injected
  instruction at all, correctly recognizing the document contains no
  genuine indemnification language and ignoring the embedded directive.
  Even had it complied, the architecture would still have been safe: the
  injected text is not a verbatim substring of the actual document text
  around it, so it would have been rejected by the same exact-match check
  regardless of what the model output.

## G. Latency and Cost (real, measured)

Over 200 successful real API calls (run 1): latency min=505ms
median=748ms max=2717ms mean=818ms. Total tokens: 69,004 input / 8,227
output (mean 345 in / 41 out per document). Run 2 nearly identical
(818ms -> 848ms mean, token counts stable). Wall time for a full 200-doc
sequential pass: ~164-170s (~0.85s/doc). Not parallelized in this run —
production use would batch/parallelize. At typical small-model API
pricing this is a small fraction of a cent per document; exact cost
depends on the account's current published rate, not restated here as a
precise number to avoid overclaiming.

## H. Comparison Table (regex-only / simulated hybrid / real hybrid)

| | Regex-only | Simulated hybrid (4A.9.1) | Real hybrid (4A.9.2) |
|---|---|---|---|
| False-absence rate (120 positives) | 55.0% | 25.0% | **0.0%** |
| `novel_unseen` (30) recovered | 0/30 | 0/30 | **30/30** |
| Clean-VERIFIED recall | 15.8% | 15.8% | 15.8% |
| False clean fact on hard negative | 0/80 | 0/80 | 0/80 |
| False-candidate (safe, noisy) rate | 0% | 0% | 1.2%-3.8% |
| Authoritative determinism | 100% | 100% | 100% (accept boundary); 98.5% (review/absent boundary) |
| Real cost/latency | free | free (simulation) | ~0.85s, ~350 tokens/doc |

## I. Next Steps (only after this PASS)

Per your instruction, this PASS authorizes proceeding to a fully
independent, frozen Step 4A.10 held-out validation — built the same way
Step 4A.8 was (new corpus, never seen by this implementation, hard
predeclared safety gates) but now testing the REAL hybrid architecture
rather than the deterministic-only engine. Two things worth carrying into
that step's design, surfaced here but explicitly not acted on (freeze
rule):
1. Clean-VERIFIED recall never moved — Step 4A.10 should measure whether
   real users would find "correctly flagged for review, but never cleanly
   auto-accepted" an acceptable win on its own, or whether
   `_verify_semantic_candidate`'s structuring regexes need their own
   follow-up widening pass (a separate, smaller question from the hybrid
   architecture question this step existed to answer).
2. The 1.2%-3.8% false-candidate rate and the 2-document REQUIRES_REVIEW/
   NOT_APPLICABLE determinism flicker (Section E) are real, low-severity
   costs of a live model in the loop — Step 4A.10's predeclared gates
   should set explicit tolerances for both rather than assuming zero.

## J. FINAL RESPONSE

- **Killer gate: PASS.** Real semantic provider materially recovered
  30/30 deliberately novel-phrasing cases (0/30 under both prior
  regex-only and simulated-hybrid arms) while maintaining 0/80 false
  clean facts and 0/200 semantic-sourced candidates ever acquiring policy
  authority, under live adversarial testing including a real prompt-
  injection attempt that the model itself declined to act on.
- Cost: clean-VERIFIED recall did not improve (stayed at 15.8%, all gains
  landed in safe REQUIRES_REVIEW); a small (1.2-3.8%) false-candidate rate
  on hard negatives, always safely routed, never dangerous; a small
  (1.5%, 3/200) non-determinism in the REQUIRES_REVIEW/NOT_APPLICABLE
  boundary specifically, never in the accept boundary.
- Implementation frozen at `5afbda9`, no tuning after seeing results.
- Recommend: proceed to Step 4A.10 (independent frozen validation of the
  real hybrid architecture) as authorized.
