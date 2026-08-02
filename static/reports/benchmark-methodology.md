# TriageBench Methodology

**Ruleset validated:** 7.2.0 (189 rules) &middot; **Corpus:** 4,190 real SEC-filed contracts &middot; **Reference run:** `20260802T164957Z`

## What TriageBench is

TriageBench runs TriageCounsel's complete deterministic pipeline, in-process, against every
contract in a fixed corpus — independent of the FastAPI/database/Stripe application surface,
and with no dependency on the non-deterministic LLM explanation layer. It never imports
`main.py`; only the pure, deterministic modules (`rules_engine`, `docx_export`,
`review_workflow`, `clause_quality`, etc.) are exercised directly.

## The ten-stage pipeline

Every contract in the corpus passes through the same ten stages, each independently timed
and fault-isolated — a single contract's failure at any stage never stops the run; downstream
stages are recorded as skipped with a documented reason.

1. **Upload** — raw document bytes are read and the primary HTML-to-text extractor runs.
2. **Analysis** — `RuleEngine.analyze()` is invoked: chunking, rule matching, clause-quality
   and structure analysis, and metadata extraction, exactly as production computes it.
3. **Rule Engine** — the bookkeeping pass over `analyze()`'s findings: severity counts,
   rules-triggered vs. rules-executed, per-rule occurrence aggregation.
4. **Evidence** — clause-level evidence spans are validated against the source text.
5. **Review** — a fixed, documented synthetic policy (`pipeline._auto_decide`, in
   `triagebench/pipeline.py`) stands in for a human reviewer, since a CI benchmark has none.
   The policy accepts every authored redline and flags everything else — the most
   defensible default, chosen so DOCX and negotiation-package generation are exercised
   against real production code paths on every run, not skipped.
6. **Verify** — the full engine is re-run (a "replay run") and every finding from the first
   run is checked to reproduce exactly, matched by rule ID, start index, and exact snippet.
7. **Negotiation Package** — the cover memo, audit trail, and package assembly are generated
   from the review decisions above.
8. **DOCX Export** — the redlined Word document (native Track Changes + comments) is built
   and validated as well-formed OOXML.
9. **Replay** — the second run from step 6 is compared to the first at the whole-document
   level: finding sequence, rule counts, and overall risk must be byte-for-byte identical.
   Verify asks "does this one finding reproduce?"; Replay asks "is the entire document's
   output deterministic end to end?" — a mismatch here indicates non-determinism in the
   engine itself, independent of any single finding.
10. **Audit** — an independent, secondary HTML-text extractor cross-checks the primary
    extraction (this is `independent_parsing` in the reports below) as a corpus-parsing
    sanity check, separate from the rule engine and export pipeline.

## Corpus

4,190 real SEC EDGAR contract exhibits across four categories — Employment (2,455),
Purchases (1,007), Services (664), Lease (64). No synthetic contracts, no AI-generated
examples. Corpus preflight for the reference run found 0 empty files, 0 unreadable files,
and 14 duplicate-content groups (28 contracts) — every discovered contract was still
scheduled and processed independently.

## Pass/fail and severity classification

A contract's terminal status is `pass` unless any stage raises. Parser, export, and replay
failures are additionally classified by severity (P0–P3 for parser issues, E0–E3 for export
issues) so a benchmark-blocking defect (P0/P1, or any `ci_blocking=True` row) is distinguished
from a lower-severity, documented, non-blocking condition.

## Go/No-Go

The Go/No-Go verdict for a run is computed from, in order: whether every discovered contract
reached a terminal state, whether any critical blocker was recorded, parser/verify/replay/export
success rates, and the reliability scores below. A single engineering-owned document
(`executive_benchmark_report.md`, generated fresh for every run) states the verdict plainly —
GO or NO-GO — with the exact numbers behind it, not a qualitative summary.

## Scores

| Dimension | What it measures |
|---|---|
| Engine reliability | Overall contract-level pass rate across all ten stages |
| Parser reliability | Share of contracts with no P0/P1 parser defect |
| Determinism | Replay match rate (second run byte-identical to the first) |
| Evidence anchoring | Clause-level evidence spans validate against source text |
| DOCX/export reliability | DOCX export + Negotiation Package success rate |
| Commercial readiness | Composite of the above plus critical-blocker count |

---

*This document describes the reference methodology as implemented in `triagebench/pipeline.py`
and `triagebench/extended_reports.py`. It is generated from the same codebase that produced
the reference run — not written independently of the code that runs it.*
