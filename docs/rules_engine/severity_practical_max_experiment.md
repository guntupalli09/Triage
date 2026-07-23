# Experiment: Practical (not theoretical) maximum WAS per rule

Requested follow-up to the 117-rule migration's headline finding (94 rules
never exceeded WAS 12 against an 18-point MEDIUM threshold). This ignores
the thresholds entirely and asks a narrower question: for each rule, using
only the factors that rule's own scoring already identified as relevant
(not a fresh re-guess, and not all 11 factors), what is the maximum WAS
achievable if every one of those factors were drafted as badly as
possible? Then: what percentage of that rule's own ceiling does its actual
score represent?

Method, script, and full data: `scripts/practical_max_experiment.py`
(reproducible — run it directly for the full 117-row table).

## Headline result

**Only 3 of the 94 band-scored rules (3.2%) could ever reach WAS≥18 —
even at the absolute maximum of their own already-identified relevant
factors.** 91 of 94 (96.8%) are structurally incapable of reaching MEDIUM
under any scoring of those factors, because the factor *set* itself
(1–2 factors for most rules) caps the achievable total well below 18
regardless of the *level* chosen within it.

The 3 exceptions, and the only band-scored rules whose own practical
ceiling clears 18 at all:

| Rule | Factors touched | Actual WAS | Practical max |
|---|---|---|---|
| `H_CLASSIFICATION_01` | PE, RS, REV | 9 | 21 |
| `M_EMPLOY_SEVERANCE_RELEASE_01` | RW, RS, REV | 12 | 21 |
| `M_CONSTR_LIEN_WAIVER_01` | RW, FB, REV | 10 | 21 |

## Aggregate statistics (113 rules with a non-zero practical max; 4 rules
have zero touched factors and are excluded — see below)

- Mean: 53.7% of own practical max; median: 50.0%
- Ceiling-fired rules (23): mean much higher, mostly 73–100% — these
  rules were scored close to their own structural ceiling
- Band-scored rules (90 of the 113 with nonzero pmax): mean 45.6%,
  **median 36.4%**
- Distribution: 0 rules below 25%; 56 rules at 25–50% (nearly all
  clustered exactly at 33.3%); 31 at 50–75%; 19 at 75–99%; 7 at exactly
  100%

Rules with **zero** touched factors (practical max = 0, meaning no
factor was implicated at all under the current 11-factor model, not just
scored at a low level): `M_RENEW_01`, `M_MFN_01`, `L_GOVLAW_01`,
`L_COUNTERPARTS_ESIGN_01`. These are excluded from the percentage stats
since 0/0 is undefined — their own detection patterns describe facts
this framework treats as intrinsically non-risky regardless of drafting.

## Interpreting the 33.3% cluster

56 of 113 rules land at exactly 33.3%. This is not scattered noise from
inconsistent reviewer judgment — it is the mechanical result of scoring a
single factor (almost always REV, sometimes paired with FB or RS) at
level 1 against that factor's own ceiling of 3. 25 rules are literally
"REV=1 and nothing else."

The natural first read is "reviewer was conservative." The more careful
read, checked against the actual rubric text, is narrower: for the
clause types in this cluster (missing SLA commitments, missing invoice
triggers, escrow terms, audit-notice language, etc.), REV's level-3
definition — *structural* irreversibility, the same tier as an entered
judgment or a public data disclosure — does not describe any realistic
draft of that clause. A worse-drafted "no SLA commitment" clause does not
become "an entered judgment"; it becomes a different clause. So maxing
REV to 3 for these rules would not be more honest scoring, it would be
assigning a fact pattern the clause doesn't exhibit at any severity.

By contrast, rules that score 75–100% of their own practical max are
overwhelmingly ones where the touched factor's full 1–3 range genuinely
tracks the *same clause type* getting worse — `H_PERSONAL_01` (PE:
capped guaranty → unconditional), `H_TERM_CONVENIENCE_01` (UD: noticed
termination → immediate/sole-discretion). Those were scored using the
graduated range because the range is real for that clause type.

## What this changes about last turn's three hypotheses

This experiment substantially closes a confound left open last turn —
whether reviewer within-factor conservatism, not just factor-set
narrowness, explained the low WAS ceiling. It does not: even a
maximally aggressive re-scoring of the *already-identified* relevant
factors for each rule still leaves 91/94 band-scored rules unable to
reach 18. The bottleneck is the **count** of factors a narrowly-drafted,
single-clause-type detection rule touches at all (median 1–2), not the
**level** chosen within them.

This sharpens, rather than overturns, last turn's conclusion: the
threshold table's implicit assumption of richer multi-factor co-
occurrence than single-clause-type rules actually produce is the
dominant, now better-evidenced explanation. Hypothesis 2 (weights too
low) remains unsupported. Hypothesis 3 (over-reliance on ceilings) is
confirmed as an effect, not an independent cause: raising within-factor
scores cannot fix the LOW clustering for the 91 structurally-capped
rules — only a broader factor set per rule or a change to the threshold
table could, and this document does not recommend either, per
instruction to analyze before changing anything.
