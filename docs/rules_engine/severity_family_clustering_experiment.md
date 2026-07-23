# Experiment: rule-family clustering — does one global WAS threshold work?

Follow-up to the practical-maximum-WAS experiment. That experiment
established that 91/94 band-scored rules can't reach WAS 18 even at their
own factor set's ceiling. This experiment asks the natural next question:
is that a uniform property of the ruleset, or does it vary systematically
by rule family — and if it varies, can any single global threshold still
work?

Method and full data: `scripts/rule_family_clustering_experiment.py`
(reproducible). Families are a re-grouping of the already-scored 117
rules by rule_id prefix / clause_category into practice-area and
doctrinal buckets a human reviewer would recognize (Lease, Employment,
Rights Waiver, etc.) — no rule was re-scored to produce this table.

## Family table (practical max = each rule's own already-identified
factors maxed to their own ceiling, per the prior experiment's method)

| Family | n | Ceiling | Band | Actual WAS | Practical Max |
|---|---|---|---|---|---|
| Other/Commercial Terms | 16 | 0 | 16 | 0–7 | 0–12 |
| Data/Privacy | 13 | 2 | 11 | 2–8 | 3–12 |
| Administrative | 13 | 0 | 13 | 0–1 | 0–3 |
| Financial | 11 | 1 | 10 | 1–5 | 3–11 |
| Rights Waiver/Remedy | 8 | 1 | 7 | 1–9 | 3–15 |
| Indemnification/Liability Cap | 7 | 3 | 4 | 1–6 | 3–9 |
| Unilateral Discretion/Termination | 7 | 4 | 3 | 5–9 | 9–15 |
| Lease | 6 | 3 | 3 | 3–5 | 9–9 |
| Employment | 5 | 1 | 4 | 2–12 | 5–21 |
| Restrictive Covenant | 5 | 0 | 5 | 1–4 | 3–11 |
| Loan | 5 | 2 | 3 | 3–9 | 9–15 |
| IP/Ownership | 4 | 1 | 3 | 3–8 | 6–9 |
| M&A/Partnership | 4 | 2 | 2 | 3–5 | 5–9 |
| Regulatory Compliance | 3 | 0 | 3 | 5–9 | 9–17 |
| Construction | 3 | 1 | 2 | 7–10 | 11–21 |
| Insurance | 2 | 0 | 2 | 3–3 | 9–9 |
| Franchise | 2 | 1 | 1 | 1–1 | 3–3 |
| Settlement | 2 | 0 | 2 | 3–3 | 3–9 |

## Threshold sweep against every family's practical max

| T | Families where some rule could reach T | Families structurally locked out |
|---|---|---|
| 6 | 16 of 18 | 2 (Administrative, Franchise) |
| 9 | 16 of 18 | 2 (Administrative, Franchise) |
| 12 | 8 of 18 | 10 |
| 15 | 6 of 18 | 12 |
| **18 (current)** | **2 of 18** (Employment, Construction) | **16 of 18** |
| 21 | 2 of 18 | 16 of 18 |
| 24, 36 | 0 of 18 | 18 of 18 |

## Verdict: no, a single global threshold does not work

There is no value of T that produces sensible, non-degenerate behavior
across families simultaneously:

- **Low T (6–9)**: nearly every family's ceiling already clears the bar
  — this isn't discrimination, it's saturation. The threshold stops
  meaningfully separating anything within most families.
- **Mid T (12)**: roughly half the families get locked out, but for
  reasons unrelated to actual severity — Lease and Insurance are excluded
  here specifically because their entire band-scored population sits at
  exactly practical-max 9, an artifact of how many factors those clause
  types structurally touch, not because lease/insurance risk is
  inherently mild.
- **High T (18+, i.e. the current threshold)**: only 2 of 18 families
  (Employment, Construction) have any rule that could ever cross it, at
  any draft severity. The other 16 are permanently excluded from
  MEDIUM/HIGH via aggregation, independent of how the specific clause in
  that family is worded.

No threshold between these extremes produces a stable middle where most
families get real, meaningful use of the MEDIUM band — the families'
achievable ranges don't share a common scale to cut at any single point.

## What this actually means

WAS is not a comparable quantity across rule families. The same WAS
number means something different in "Administrative" (whose entire
practical ceiling tops out at 3, because document-consistency clauses
structurally cannot touch more than one weight-1 factor) than it does in
"Employment" or "Construction" (which can stack a weight-4 factor with
two others and reach into the 20s). The variation isn't primarily in how
severely a given clause is drafted — it's in how many of the 11 factors
that clause TYPE can structurally ever touch, which is a property of the
family, not of any individual rule's severity.

Two families (Lease, Insurance) additionally show **zero internal
range** — every band-scored rule in each sits at exactly the same
practical max (9). Even a perfectly-tuned, family-specific threshold
could not differentiate mild from less-mild within those families using
WAS at all; ceiling-or-not is currently the only mechanism that produces
any distinction there.

This reframes the calibration question. It is not "is 18 the right
number" — no single number, high or low, behaves consistently across all
18 families. The real question is whether severity should be assessed
against one global WAS scale at all, versus against each family's own
achievable range (e.g. a percentile/normalized measure within family), or
whether more clause types need dedicated ceiling rules the way
Personal Liability and Rights Waiver already have, since ceilings are
presently the only mechanism producing real differentiation for most of
these 18 families.

No thresholds, weights, or factor vectors were changed to produce this
analysis, per instruction to run the experiment before changing anything.
