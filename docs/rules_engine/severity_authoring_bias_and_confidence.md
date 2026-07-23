# Authoring bias check and per-family confidence

Addresses two review items on the family-clustering findings: whether
observed family richness is actually author/reviewer richness in
disguise, and which family-level claims have enough sample size to
support a structural statement versus a preliminary one.

Script: `scripts/authoring_bias_experiment.py` (reproducible).

## Is "family richness" actually "author richness"?

This cannot be tested as literally requested, and that limitation is
reported directly rather than worked around: the 117-rule migration has
exactly **one** author and **one** reviewer — "Reviewer 1 (framework
author)" — for every single rule. The author/reviewer column below has
zero variance by construction, so a correlation between author identity
and family richness is undefined, not "no correlation found." Building a
table that implied otherwise would manufacture false precision.

| Family | Author | Reviewer | n | Avg factors | Practical max range | Ceilings |
|---|---|---|---|---|---|---|
| Other/Commercial Terms | Reviewer 1 | Reviewer 1 | 16 | 1.38 | 0–12 | 0 |
| Data/Privacy | Reviewer 1 | Reviewer 1 | 13 | 2.27 | 3–12 | 2 |
| Administrative | Reviewer 1 | Reviewer 1 | 13 | 0.85 | 0–3 | 0 |
| Financial | Reviewer 1 | Reviewer 1 | 11 | 2.00 | 3–11 | 1 |
| Rights Waiver/Remedy | Reviewer 1 | Reviewer 1 | 8 | 1.71 | 3–15 | 1 |
| Indemnification/Liability Cap | Reviewer 1 | Reviewer 1 | 7 | 1.50 | 3–9 | 3 |
| Unilateral Discretion/Termination | Reviewer 1 | Reviewer 1 | 7 | 2.33 | 9–15 | 4 |
| Lease | Reviewer 1 | Reviewer 1 | 6 | 2.00 | 9–9 | 3 |
| Employment | Reviewer 1 | Reviewer 1 | 5 | 2.75 | 5–21 | 1 |
| Restrictive Covenant | Reviewer 1 | Reviewer 1 | 5 | 2.00 | 3–11 | 0 |
| Loan | Reviewer 1 | Reviewer 1 | 5 | 2.33 | 9–15 | 2 |
| IP/Ownership | Reviewer 1 | Reviewer 1 | 4 | 2.33 | 6–9 | 1 |
| M&A/Partnership | Reviewer 1 | Reviewer 1 | 4 | 2.00 | 5–9 | 2 |
| Regulatory Compliance | Reviewer 1 | Reviewer 1 | 3 | 2.33 | 9–17 | 0 |
| Construction | Reviewer 1 | Reviewer 1 | 3 | 3.00 | 11–21 | 1 |
| Insurance | Reviewer 1 | Reviewer 1 | 2 | 2.00 | 9–9 | 0 |
| Franchise | Reviewer 1 | Reviewer 1 | 2 | 1.00 | 3–3 | 1 |
| Settlement | Reviewer 1 | Reviewer 1 | 2 | 1.50 | 3–9 | 0 |
| Personal Liability | Reviewer 1 | Reviewer 1 | 1 | — | n/a | 1 |

**On author-identity correlation specifically**: undefined, not zero.
Neither the original success criterion ("no correlation → confidently
rule out authoring practices") nor its converse can be claimed here,
because there is no second author or reviewer in this dataset to vary
against. This is exactly what the still-pending §10 blind re-score gate
exists to supply, and it remains the only way to fully close this
question — see Priority 7.

### The closest testable proxy: session-order drift

With one author, the nearest honest test is whether scoring generosity
drifted across the single authoring session in a way confounded with
family (rules were scored in batches that roughly track family
membership — see the batch comments in
`scripts/severity_migration_full.py`).

| Session quartile | n | Avg factors touched | Avg band-scored WAS | UD used | AT used | PE used |
|---|---|---|---|---|---|---|
| 1 (rules 1–29) | 29 | 2.14 | 4.14 | 5 | 2 | 1 |
| 2 (rules 30–58) | 29 | 1.76 | 3.07 | 1 | 0 | 1 |
| 3 (rules 59–87) | 29 | 1.69 | 2.54 | 4 | 1 | 0 |
| 4 (rules 88–117) | 30 | 2.20 | 4.45 | 7 | 2 | 2 |

**Result: weak, mixed, inconclusive — not a clean confound, but not
fully ruled out either.** The pattern is U-shaped (quartiles 1 and 4 both
higher than 2 and 3), which rules out the simplest story (monotonic
fatigue or monotonic warm-up over the session). UD/AT/PE — the factors
most associated with the richest families (Lease, Employment,
Construction, M&A) — are used across all four quartiles rather than
concentrated in the late-session batch, though quartile 4 (which
contains most of the v6.0 law-firm batch) does show the single highest
count of each. This is suggestive of a mild, partial order/family
confound at most, not the dominant explanation the earlier stress test
already substantially ruled out via two independent falsification tests
(gap-rule exclusion, orthogonal era-based reclustering). It cannot be
resolved further by this reviewer alone.

## Confidence table by sample size

Per Priority 3: family-level structural claims should be weighted by how
much data actually backs them.

| Family | Rules | Confidence |
|---|---|---|
| Other/Commercial Terms | 16 | High |
| Administrative | 13 | High |
| Data/Privacy | 13 | High |
| Financial | 11 | High |
| Rights Waiver/Remedy | 8 | Medium |
| Indemnification/Liability Cap | 7 | Medium |
| Unilateral Discretion/Termination | 7 | Medium |
| Lease | 6 | Medium |
| Employment | 5 | Medium |
| Restrictive Covenant | 5 | Medium |
| Loan | 5 | Medium |
| IP/Ownership | 4 | Low |
| M&A/Partnership | 4 | Low |
| Regulatory Compliance | 3 | Low |
| Construction | 3 | Low |
| Insurance | 2 | Low |
| Franchise | 2 | Low |
| Settlement | 2 | Low |
| Personal Liability | 1 | Low |

Thresholds used: High ≥ 10 rules, Medium 5–9, Low < 5. This is a coarse,
round-number cut, not a statistically derived confidence interval —
stated as a threshold choice, not a computed guarantee.

**Results for Insurance, Franchise, Settlement, Personal Liability,
M&A/Partnership, IP/Ownership, Regulatory Compliance, and Construction
(8 of 19 families, all n ≤ 4) are preliminary.** The cross-family
pattern documented in the family-clustering and stress-test experiments
is corroborated by both High- and Medium-confidence families (Other/
Commercial Terms, Administrative, Data/Privacy, Financial, Employment,
Loan all show the same lockout behavior independently), so the overall
conclusion does not rest on the Low-confidence families alone — but any
claim about a *specific* Low-confidence family's exact practical-max
range (e.g. "Insurance's ceiling is exactly 9") should be read as a
2-rule observation, not a settled property of insurance-clause risk in
general. Priority 6 (expanding these families to 10+ rules each) is the
correct way to upgrade these from preliminary to confirmed.
