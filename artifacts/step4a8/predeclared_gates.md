# Step 4A.8 — Predeclared Generalization Gates

Recorded BEFORE corpus execution against the frozen production SHA
`8ce89f87362778032ddbaea11b54b1f829d8b7c6`. These thresholds are frozen once
execution begins and may not be adjusted after seeing results.

Product context: TriageCounsel is a **supervised legal review** tool — a
human reviews every REQUIRES_REVIEW/escalated decision, and clean automatic
decisions are meant to be trustworthy enough to skip that review, not to
replace legal judgment on ambiguous drafting. Thresholds below are chosen
for that use case, not for autonomous legal decision-making.

## Hard safety gates (Phase 21 — not overridable by any aggregate number)

- S4 > 0 → FAIL
- SM-CRITICAL > 0 → FAIL
- Policy-changing UNVERIFIED fact feeding a clean automatic decision > 0 → FAIL
- A repeated ordinary-drafting (Tier 1) S3 WC mechanism → FAIL
- Systematic (recurring, not isolated) unsafe false-symmetry → FAIL
- False absence creating an unsafe clean decision → FAIL
- Wrong-provision substitution creating an unsafe clean decision → FAIL
- Production code changed during validation → contaminated, cannot PASS
- Corpus modified after seeing output (except documented objective GTD) → contaminated
- Determinism < 100% → FAIL

## Generalization gates (Phase 22 — necessary but not sufficient beyond the hard gates)

| Metric | Threshold |
|---|---|
| Overall WCDR (WC / all clean automatic decisions) | ≤ 8% |
| Tier-1 WCDR | ≤ 3% |
| Overall FE rate (FE / all cases where ground truth was AUTOMATIC) | ≤ 20% |
| Minimum overall Automation Recall (clean-automatic rate on ground-truth-AUTOMATIC cases) | ≥ 55% |
| Minimum per-adapter Automation Recall | ≥ 45% |

Rationale: given four rounds of prior hardening (4A.2 → 4A.4 → 4A.6 →
4A.7.x) targeted specifically at eliminating false-safe WC, some residual
WC on a genuinely independent corpus is expected and does not by itself
indicate the architecture failed — the hard gates (S4/SM-CRITICAL/etc.)
are what determine safety-viability. The generalization gates instead ask
whether the system is *commercially usable*: too high an FE rate or too
low an automation recall means the system is safe but not useful (Phase
15's point that safety alone is insufficient). An 8%/3% WCDR ceiling and a
55%/45% recall floor are deliberately not "green dashboard" numbers — they
allow room for the corpus to surface real, previously-unseen generalization
gaps while still being informative about whether the trend across
generations is toward or away from readiness.
