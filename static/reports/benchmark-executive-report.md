# TriageBench Full-Corpus Baseline — Executive Report

**Run ID:** `20260802T164957Z`
**Label:** full-corpus-baseline-v2-post-docx-fix
**Git commit:** `d47ccae11fea4e28437b266fef9c6cc68d69b0c9` (branch `claude/triagebench-framework-h8rqmk`)
**Ruleset version:** `7.2.0` (189 rules)
**Corpus manifest hash:** `cb10c8febce1cf13c33c59cde8434eaaa8cbe3662d1d2401993d4ea5e9da306f`
**Started / finished:** 2026-08-02T16:49:57Z → 2026-08-02T17:36:39Z (2801.6s wall-clock)
**Machine:** vm — Linux-6.18.5-x86_64-with-glibc2.39 — Python 3.11.15

## Were all 4,190 contracts accounted for?

**YES** — 4190 of 4190 expected contracts have a terminal state.
Corpus preflight: 0 empty files, 0 unreadable files,
14 duplicate-content groups (28 contracts) — all processed independently regardless.

## Headline numbers

| Metric | Value |
|---|---|
| Completed successfully (pass) | 4131 (98.59%) |
| Failed (fail/error) | 59 |
| Skipped | 0 (every discovered contract was scheduled and processed — see manifest `corpus_selected`) |
| Parser success rate (no P0/P1) | 100.0% |
| P0 rate | 0.0% |
| Verify/replay success rate | 100.0% |
| DOCX export success rate | 100.0% |
| Negotiation Package success rate | 100.0% |
| Redline coverage (overall mean) | 7.08% |

### Redline coverage by category

- **Employment**: 6.94% (n=2455)
- **Lease**: 11.49% (n=64)
- **Purchases**: 6.77% (n=1007)
- **Services**: 7.65% (n=664)

## Rules

- Rules never triggered: 34 — see `rules_never_triggered.csv`
- Top-firing rules: see `rule_coverage.csv` / `rule_coverage.html`
- Rules with verify/replay involvement: see `rules_with_replay_failures.csv`

## Worst-performing categories (P0+P1 parser issues)

- None — no category had a P0/P1 parser issue.

## Runtime performance

- P50: 1107.679 ms
- P95: 11252.332 ms
- P99: 18611.12 ms
- Max: 234049.465 ms

## Critical blockers

- None.

## Regression vs. prior full-corpus baseline

This is the **first full-corpus baseline** — no prior full-corpus run exists to compare against. This run establishes the reference point for all future full-corpus runs.

## Scores (0-100)

| Dimension | Score |
|---|---|
| Engine reliability | 99 |
| Parser reliability | 100 |
| Determinism | 100 |
| Evidence anchoring | 100 |
| DOCX/export reliability | 100 |
| Performance | 69 |
| **Benchmark confidence** | **100** |
| **Commercial readiness** | **97** |

## Is the current build suitable for controlled pilots?

**YES** — no critical blockers were found; the deterministic engine, parser, evidence anchoring, and export pipeline all held up across the full corpus.

## Is the current build suitable for unrestricted commercial production?

Engine-level results support it; TriageBench Live (separately, against a deployed instance) additionally validated the live product surface — see that suite for auth/session/security/UI evidence not in scope for this engine-level run.

## What should engineering fix first?

1. **[general]** Full failure inventory — 59 total stage failures across the corpus — see benchmark_failures.csv. (owner: engineering leads)

## Go / No-Go verdict

# GO

---

**Disclaimer:** This report measures deterministic engine behavior, parser fidelity, evidence anchoring,
export integrity, and performance. It does not constitute legal advice, attorney validation, or a
user-acceptance study. All review decisions (accept/reject/edit/flag) in this run were produced by a
fixed, documented synthetic CI policy (`pipeline._auto_decide`), not by an attorney — see
`triagebench/pipeline.py`'s module docstring.
