# RESIDUAL_RISK_REGISTER

Honest accounting of what this implementation pass did and did not close.
The full 24-step mission (12 adapters, targeted+regression+fresh-frozen-
corpus testing, live triagecounsel.com screenshot validation) is a
multi-week program; this pass completed Steps 0-1 and Steps 10/12 in full,
plus one reference adapter integration, and stops short of Steps 13-22.
**No claim of overall mission PASS is made.** See the final chat summary
for the itemized status against the mission's own FINAL VERDICT checklist.

## Closed in this pass

- Steps 0-1: investigation, shared fact-admission framework, 39 unit
  tests covering the full provider-failure matrix (Step 16-style), one
  fully integrated reference adapter (liability) with 7 adapter-specific
  tests including the descriptive-language regression (Step 15).
- Step 10: document-aggregation "Needs Attention" badge now consistent
  across dashboard, history, and the single-contract review page (a real,
  smaller gap than originally believed — see PRE_IMPLEMENTATION_MAP.md §8
  for the correction).
- Step 12: near-empty PDF extraction now rejected with a distinct message,
  closing the "contract has no clause" vs. "we failed to read the
  contract" ambiguity for scanned/low-density PDFs.

## Not attempted in this pass — explicitly, not by oversight

- **11 of 12 adapters remain unintegrated with the new framework**
  (indemnification already has its own equivalent, separately frozen;
  liability is the only new integration). See ADAPTER_MATRIX.md for the
  per-adapter roadmap. This is the largest remaining item.
- **Steps 13-19 (fresh targeted+adversarial test suites, full regression,
  metrics reporting, determinism replay)** — done at the scope of the one
  integrated adapter (liability) and the shared module itself, not at the
  12-adapter scope the mission specifies.
- **Step 20 (fresh 600-case frozen corpus)** — not created. Creating and
  freezing a corpus of that size, with provenance recording (corpus hash,
  commit SHA, verifier prompt version), and executing it exactly once, is
  a distinct, substantial exercise this pass did not attempt.
- **Step 21 (live triagecounsel.com validation with genuine browser
  screenshots)** — not attempted. This requires an authenticated session
  against the actual deployed product, which is outside what this pass
  had reason or occasion to do without separate, explicit authorization
  to interact with the live production service and its user accounts.
- **Step 22 (Lee Czocher question matrix)** — not answered with frozen-
  corpus/live-product evidence, since neither exists yet. Answering it
  honestly requires that evidence; answering it without would violate the
  mission's own instruction not to force verdicts to PROVEN.

## Known limitations of what WAS built

- The liability integration's semantic layer can currently only *find* a
  candidate provision it wasn't already finding — it cannot yet correct a
  regex-found provision's mis-parsed cap/basis/category, because it only
  ever seeds `_extract_provision()`'s window, never structures a fact
  itself. This mirrors indemnification's own measured ceiling
  (PRE_IMPLEMENTATION_MAP.md §15a.2 — discovery moves recall into review,
  not into clean-accept) and should not be read as an oversight to fix
  quickly; it is the architecturally correct scope for what AI is allowed
  to do here.
- `fact_admission.py`'s adversarial verifier is new code with mocked-only
  test coverage in this pass — no live-provider adversarial run (the
  equivalent of Step 4A.9.2's 200-real-call benchmark for indemnification)
  has been performed against it yet. Its prompt/schema design is
  reasoned from the mission's own Step 2/3 requirements and this
  codebase's proven prior pattern, but is unvalidated against real model
  output at scale.
- `LIABILITY_SEMANTIC_DISCOVERY_ENABLED` defaults to `False` — the new
  capability is not live for any user until a deployer explicitly flips
  it, and no decision about when/whether to do that has been made in this
  pass.
