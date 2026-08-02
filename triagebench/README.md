# TriageBench

TriageBench is TriageCounsel's continuous quality-benchmark framework. It is
not a test suite and not a script — it is the infrastructure that answers,
automatically and after every change to the engine, the one question that
matters: **did this make TriageCounsel better or worse, and exactly where?**

It runs the complete deterministic TriageCounsel workflow — Upload →
Analysis → Rule Engine → Evidence → Review → Verify → Negotiation Package →
DOCX Export → Replay → Audit — against every contract in `Benchmark - TC/`
(4,190 real SEC-filed exhibits across Employment, Purchases, Lease, and
Services), validates every stage, and produces reports, dashboards, and a
regression diff against the previous run. If one contract fails, the
benchmark logs it and continues; nothing requires manual intervention.

## Quick start

```bash
pip install -r requirements.txt              # TriageCounsel's own deps
pip install -r triagebench/requirements.txt   # + pandas/pyarrow for the corpus

# Fast sanity run (12 contracts, seconds) — good for local iteration / PR checks
python -m triagebench run --per-category 3 --workers 4

# Nightly / pre-release run — the full corpus
python -m triagebench run --workers 8 --label nightly --fail-on-regression

# Regenerate reports/dashboards for a run without re-running the corpus
python -m triagebench finalize <run_id>

# List past runs
python -m triagebench list
```

Open `triagebench_runs/<run_id>/dashboards/overview.html` directly in a
browser — no server required.

## Architecture

```
triagebench/
  config.py        Paths, run-id scheme, BenchmarkConfig
  corpus.py         Discovers contracts from Benchmark - TC/*/archive/metadata.parquet,
                    resolves them to files on disk, deterministic sampling
  html_extract.py   Two independent HTML→text extractors (SEC EDGAR exhibit format)
  engine_bridge.py  The ONLY module that imports TriageCounsel's application code
  pipeline.py       The ten-stage per-contract pipeline
  runner.py         Orchestrates the corpus pass: parallel, resumable, fault-tolerant
  storage.py        Run layout on disk, append-only results, resumability
  aggregate.py      Rollups shared by both CSV reports and HTML dashboards
  reports.py        The 11 CSV reports
  dashboards.py     The 7 self-contained HTML dashboards
  regression.py     Diffs a run against its baseline
  finalize.py       Ties aggregate/reports/dashboards/regression together
  cli.py            `python -m triagebench {run,finalize,list}`
  tests/            Framework self-tests (not corpus/engine-quality tests)
```

### Why `engine_bridge.py` never imports `main.py`

`main.py` constructs a FastAPI app, a Stripe client, and a DB/Redis-backed
session layer at import time. None of that is part of what this benchmark
measures, and importing it would make a CI benchmark depend on a live
Postgres/Redis — exactly the kind of external, non-deterministic dependency
this framework exists to not have. TriageBench imports the underlying pure
modules directly (`rules_engine`, `docx_export`, `review_workflow`,
`redline_templates`, `confidence_index`, `metadata_extractor`) — text/dict
in, dict/bytes out, no DB, no HTTP, no network. The LLM explanation layer
(`evaluator.py` / OpenAI) is excluded for the same reason plus one more: it
is non-deterministic by construction, so a benchmark meant to catch
regressions would itself become a source of noise if it depended on a model
call. TriageBench measures the deterministic control plane — the part of
TriageCounsel that is supposed to produce identical output on every run.

### The ten stages, and what "Analysis" vs. "Rule Engine" means here

TriageCounsel's own code (`main.py`'s `run_analysis`) computes analysis and
rule matching in a single `RuleEngine.analyze()` call — there is no separate
analysis pass ahead of rule matching in production. `pipeline.py` honors
that reality instead of inventing a fake seam: the **Analysis** stage times
`analyze()` itself (chunking, rule matching, clause-quality/structure
analysis, metadata extraction); the **Rule Engine** stage is the bookkeeping
pass over `analyze()`'s findings (severity counts, rules-triggered vs.
rules-executed) that a benchmark specifically needs and production doesn't
compute as a distinct step. If TriageCounsel ever splits these into
genuinely separate calls, update `pipeline.py`'s module docstring — don't
leave a stale comment.

- **Review** is automated by a fixed, documented policy since there is no
  human reviewer in CI: accept every finding that has an authored redline
  template, flag everything else for manual drafting
  (`pipeline._auto_decide`). This is the most production-representative
  automatic choice available — it exercises the real accept path end to
  end — without pretending a human reviewed the contract.
- **Verify** re-runs the full engine (the "replay run") and checks *every*
  finding reproduces by `rule_id` + `start_index` + `exact_snippet` —
  stronger than production's `/review/verify` endpoint (which checks one
  finding interactively) but built on the identical match logic.
- **Replay** reuses that same second run to diff the *entire* result set
  (finding sequence, `rule_counts`, `overall_risk`) against the first run.
  Verify asks "does this one finding reproduce?"; Replay asks "is the whole
  document's output deterministic end to end?" — a mismatch here means the
  engine itself is non-deterministic, independent of any single finding.
- **DOCX Export** validates the redlined `.docx` independently of
  `python-docx`: raw zip structure, well-formed XML on every OOXML part
  `docx_export.py` hand-builds (`word/document.xml`, `word/comments.xml`,
  `word/settings.xml`), and that the count of `w:ins`/`w:del`/comment
  elements in the XML matches what the decisions map says should be there.
- **Independent Parsing** cross-checks TriageBench's own primary HTML
  extractor (event-driven, stdlib `html.parser`) against a second,
  differently-built one (regex tag-stripper) — a large word-count
  divergence between them signals a markup quirk one of them is
  mishandling, which is exactly the failure mode this validation exists to
  catch. It runs regardless of downstream stage outcomes, as long as upload
  itself succeeded.

Every stage is wrapped so a single contract's failure — at any stage, of
any kind — cannot stop the run or corrupt other contracts' results. If a
prerequisite stage fails, downstream stages are recorded as `skipped` with
a reason, not silently omitted.

## Determinism and reproducibility

- **Corpus discovery** sorts contracts by a content-derived `contract_id`
  (`sha1(category/archive_name)`), never by filesystem or parquet row
  order — both of those are allowed to vary between machines/OS/pandas
  versions, and if `contract_id` depended on them, regression detection
  (which joins two runs by `contract_id`) would misreport every contract as
  simultaneously new and missing.
- **Sampling** (`--limit`, `--per-category`) is seeded (`--seed`, default
  fixed) — the same corpus snapshot always produces the same sample.
- **The pipeline itself** re-runs `analyze()` twice per contract and
  requires byte-for-byte identical output (the Replay stage) — determinism
  is not assumed, it is checked on every single contract, every run.

## Resumability and fault tolerance

Results are appended to `results.jsonl` as each contract finishes, not
batched in memory. Killing the process (or the machine) at any point loses
at most the handful of contracts mid-flight. `--resume <run_id>` re-reads
that file and only schedules what's left. A worker-process crash
(`BrokenProcessPool` — e.g. a segfault in a C extension) is caught one level
up; the runner restarts a fresh pool for the remaining contracts rather than
losing the run. A single contract's exception is caught at the pipeline
level (per-stage) *and* again at the worker level (`runner._worker`) as an
absolute last line of defense — a contract can fail, the benchmark cannot.

## Parallelism

`runner.py` uses a `ProcessPoolExecutor` (CPU-bound regex work benefits from
real parallelism, not threads under the GIL). Each worker builds its own
`RuleEngine` instance once (`engine_bridge.get_engine()`, memoized per
process) and reuses it across every contract that process handles — a
benchmark run should measure `analyze()` time, not ruleset construction
repeated per contract.

## CI usage

```bash
python -m triagebench run --per-category 25 --workers 8 --fail-on-regression
```

Exit codes: `0` = success, no critical regressions. `1` = the benchmark ran
to completion but found critical regressions (or, with `--fail-on-error`,
any contract errored). `2` = the run itself could not complete (treat as an
infrastructure problem, not a quality signal).

A regression is "critical" if it includes any of: a finding-producing rule
that stopped firing on a contract it fired on before, a rule that
disappeared corpus-wide, `verify` newly failing, `replay` newly
non-deterministic, a coverage drop ≥5 points on a contract, or a DOCX export
status/consistency change. See `regression.py` for exact thresholds — they
are named constants at the top of the file, not buried magic numbers.

## Where run history lives

`triagebench_runs/` is gitignored — every run is fully reproducible from the
corpus + the engine at a given commit, so committing thousands of run
directories to the repository over years would bloat it for no benefit. In
CI, publish `triagebench_runs/<run_id>/` as a build artifact (and/or ship it
to durable object storage) so `--baseline` has something to diff against
across CI machines. `triagebench_runs/LATEST_RUN.json` is the pointer a run
without an explicit `--baseline` diffs against; it only updates when a run
*finishes* (never points at a crashed/partial run).

## Known precision tradeoff: finding-level vs. rule-level regression detail

`results.jsonl` keeps which `rule_id`s fired on a contract, not the
exact-position finding list (`start_index`/`end_index`/`exact_snippet`) —
that detail lives only in memory during a run to keep `results.jsonl` a
bounded size across thousands of contracts, run after run, for years.
Regression detection therefore operates at `(contract_id, rule_id)`
granularity ("rule X started/stopped firing on contract Y"), not individual
finding-occurrence granularity. This is still exactly the signal that
matters for triage and is a deliberate, documented storage/precision
tradeoff — see `regression.py`'s module docstring.

## What this benchmark deliberately does not measure

- **Rule correctness against ground truth.** The corpus has no
  human-labeled "this contract should trigger these rules" answer key —
  TriageBench measures *consistency and stability* (does the engine still
  produce the same output on the same input; did coverage/findings move
  between commits), not whether any given finding is legally correct. That
  is `evaluator.py` LLM-judged red-teaming or attorney review's job, not
  this framework's.
- **LLM explanation quality.** Out of scope by design — see "Why
  `engine_bridge.py` never imports `main.py`" above.
- **Real Microsoft Word rendering.** `docx_export.py`'s own module
  docstring is explicit about this: hand-built OOXML has been validated for
  well-formedness and round-tripped through `python-docx` and (separately)
  `mammoth`, but never opened in actual Word in this environment.
  TriageBench's DOCX Export stage inherits that same limit — it is strong
  automated evidence, not a substitute for opening the file in Word.
