# Step 4A.10 — Independent Corpus Manifest (locked before execution)

- `benchmarks/step4a10_benchmark.json` — 394 cases. SHA-256:
  `322a490c52befa9265c48c08e3d5b491c42a602b82589042ca55ee8313fa3ce1`
- `benchmarks/step4a10_mutations.json` — 40 formatting mutations. SHA-256:
  `6d83656e39c9a436b214be829a3261df623b9fc7c0c9968f31a945755785f0e0`
- Total planned executions: 434 (exceeds the >=400 target).

## Composition

- Positives: 220 (target 220) — Tier 1: 100, Tier 2: 70, Tier 3: 50.
- Hard negatives (non-injection): 144 (target >=140), across 23 categories
  (limitation of liability, insurance, warranty, ordinary damages,
  unrelated reimbursement, refunds, credits, SLA credits, taxes, payment
  reimbursement, defense cooperation, litigation cooperation, releases,
  waivers, security deposit, ordinary responsibility, set-off, price
  adjustment, assignment, IP ownership, data security, employment,
  regulatory cooperation, claims-notice procedure).
- Prompt-injection battery: 30 (target 30), 10 attack families x 3 role
  pairs each.
- Noncanonical positives: 150 (target >=120) — do not depend on
  "indemnify"/"indemnification"/"hold harmless."
- Compound-tagged positives: 39 (target >=30) — genuine risk-transfer
  language co-occurring with liability caps, schedules/exhibits, or other
  adjacent provisions in the same case, to test whether discovery finds
  the CORRECT evidence rather than just "risk-like vocabulary present
  somewhere."
- Formatting mutations: 40, drawn from 40 distinct locked positive cases,
  7 mutation types (whitespace doubling, forced line breaks, numbering
  prefix, heading insertion, bullet restructuring, punctuation spacing,
  tab insertion) — presentation only, no wording change.

## Independence from prior corpora

Built from the underlying concept (a party contractually bearing,
assuming, reimbursing, protecting against, or otherwise taking
responsibility for another party's claims/losses/liabilities/expenses),
using a vocabulary of ~35 new templates authored for this step (see
`scripts/step4a10_generate_corpus.py`) — distinct from the Step 4A.9.1
benchmark's vocabulary ("make good to," "recompense," "shoulder the cost,"
"absorb," "on the hook," "stand behind," "undertake to make whole,"
"backstop," "pick up the tab," and the `novel_unseen` family's "left
holding the bag," "square things up," "foot the bill," "out of pocket").

Programmatic overlap check (6-word shingle intersection against
`step4a8_corpus_semantic.json`, `step4a9_recognition_benchmark.json`,
`step4a9_fresh_battery.json`, `step4a9_1_benchmark.json`): 79/394 cases
share a 6-word fragment with a prior corpus, but every one of those
fragments is generic legal boilerplate ("arising out of or relating to,"
"in a professional and workmanlike manner," "party may assign this
agreement without," "aggregate liability... under this agreement
exceed") that any independently-authored contract-language corpus would
be expected to reuse — not case-specific test phrasing. A stricter
full-case-text exact-duplicate check against all four prior corpora found
**0 matches**.

The semantic prompt (`frozen_semantic_prompt.txt`) was consulted only to
confirm it contains no example sentences that this corpus could
accidentally mirror — it does not (the prompt gives no example clause
text at all, only instructions) — and was NOT used as a source of
vocabulary or sentence structure for this corpus.

## Ground truth

Assigned in the generator BEFORE any execution (Phase 9), per-case:
`concept_present`, `expected_discovery`, `expected_absence_state`,
`expected_reviewability` (`AUTOMATABLE_IN_PRINCIPLE` vs `REVIEW_REQUIRED`
vs `NOT_APPLICABLE`), `expected_clean_automation`, `obligated_party`,
`protected_party`, `directionality`, `causation_standard`,
`monetary_treatment`, `attack_family`. Discovery ground truth
(`expected_discovery`/`expected_absence_state`) is explicitly kept
separate from structuring ground truth (`expected_reviewability`) per the
task's requirement — a case can have `expected_discovery=PRESENT` and
`expected_reviewability=REVIEW_REQUIRED` simultaneously (Tier 2/3
provision genuinely exists but is objectively too conditional for
automatic policy evaluation — not the same as absent).

## Lock sequence

1. Corpus + mutations generated (this session), zero prior exposure to
   the semantic provider — no case in this file was ever sent to
   `discover_candidate_spans_real` before this manifest and its hashes
   were written.
2. SHA-256 checksums computed and recorded above BEFORE the first
   execution against them (see `corpus_hashes_PRELOCK.txt`).
3. Production hashes re-verified unchanged since Phase 0 (byte-identical
   to `production_hashes_pre.txt`).
4. Semantic prompt hash unchanged (`a8988ce2...`, unchanged — no edits
   made to `semantic_discovery_real.py` this step).
5. Provider config unchanged (`provider_config.md`, unedited).
6. Corpus commit follows immediately after this manifest, before Phase 11
   execution begins.
