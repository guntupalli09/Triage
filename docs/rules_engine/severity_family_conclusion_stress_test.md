# Stress-testing "WAS is not comparable across families"

An adversarial attempt to disprove the family-clustering experiment's
conclusion, per instruction: assume it's wrong, identify alternative
explanations for the observed family-level practical-max variation, and
test each empirically against the existing 117-rule dataset before
trusting the original conclusion further.

Script: `scripts/family_conclusion_stress_test.py` (reproducible).

## Alternative explanations tested

### A. Incomplete factor coverage

**Hypothesis**: low-ceiling families are low only because the 11-factor
model is missing dimensions that would properly capture their risk — not
because families are inherently incomparable. If true, excluding the
rules already flagged (in `scripts/severity_migration_full.py`'s
FINDINGS) as not mapping cleanly onto any factor should raise or unlock
some families.

**Test**: removed all 11 gap-flagged rule_ids (`H_INDEM_ONEWAY_01`,
`H_PUBLICITY_01`, `H_CONTENT_LICENSE_01`, `H_EMPLOY_ATWILL_WAIVER_01`,
`M_NONDISPARAGE_01`, `M_INJUNCT_01`, `H_SETTLEMENT_RELEASE_OVERBROAD_01`,
`M_REFUND_01`, `M_WARRANTY_DISCLAIM_01`, `H_CONSEQUENTIAL_01`,
`H_LOL_NO_CARVEOUT_01`) from every family and recomputed lockout status
at T=18.

**Result: falsified.** Every family's lockout status is identical with or
without these rules — none of them was ever the rule defining its
family's ceiling. Coverage gaps exist (documented separately) but they
are not what's producing the family-level pattern.

### E. Systematic ontology/batch bias

**Hypothesis**: low-ceiling families (especially "Administrative") are
low because they're dominated by the v4.0 "contract-to-cash" rule batch,
which the changelog describes as document-completeness checks, explicitly
not designed to carry severity weight. If so, the low ceiling reflects
correct-by-design triviality, not a flaw in WAS comparability.

**Test 1**: excluded all 9 rules in the `DocumentConsistency`/
`ExecutionDefect` clause categories (structurally identified as
placeholder/completeness checks) from the Administrative family and
recomputed. Lockout count across all 18 families: 16/18 before, 16/18
after — unchanged.

**Test 2 (stronger)**: reclustered all 117 rules along a completely
different, independently-motivated axis — by originating version/era
(v1-v3 initial+broad-ICP+consumer, v4.0 contract-to-cash, v5.0 hardening,
v6.0 law-firm-expansion) instead of practice area — and reran the full
threshold sweep.

| Era | n | Practical max range | Locked at T=18? |
|---|---|---|---|
| v1-v3 | 63 | 0-21 | No |
| v4.0 contract-to-cash | 16 | 0-11 | Yes |
| v5.0 hardening | 12 | 3-12 | Yes |
| v6.0 law-firm | 26 | 3-21 | No |

**Result: falsified.** The same qualitative pattern — some groups locked
out, some not, no single T working for all — reappears under a clustering
axis that shares no logic with the original practice-area families. This
is also the strongest evidence against alternative C below.

### C. Family definition errors

**Hypothesis**: the 18 practice-area families from the prior experiment
were my own on-the-spot grouping and could be mis-drawn — too coarse, too
fine, or not corresponding to a real distinction — making the "no
threshold works" finding an artifact of bad clustering rather than a real
property.

**Test**: the era-based reclustering above (Test E.2) is a second,
independent test of this same question, since it groups the identical 117
rules along an entirely different axis.

**Result: falsified.** The lockout pattern is robust across two
unrelated ways of drawing family boundaries. If it were a clustering
artifact, a different, independently-motivated grouping should have
produced different qualitative behavior. It didn't.

### B. Uneven rule granularity

**Hypothesis**: some families just have more, thinner, more atomized
rules (each capturing one narrow slice of what a richer rule would
combine), which mechanically caps their ceiling — a rule-design artifact,
not evidence that WAS itself is incomparable.

**Test**: computed correlation between family rule count and average
factors touched per band-scored rule.

**Result: partially confirmed, not sufficient alone.**
Correlation = -0.31 (moderate). Administrative is the clean supporting
case: 13 rules, 0.85 average factors touched, pmax=3. But Data/Privacy
has the identical rule count (13) with 2.27 average factors and pmax=12,
and Construction has only 3 rules yet pmax=21. Family size predicts
richness only weakly — domain-intrinsic factor-richness differences
persist even holding rule count roughly constant. Granularity is a real,
partial contributor (most visible in Administrative specifically) but
does not account for the cross-family pattern generally.

### D. Reviewer scoring artifacts

**Hypothesis**: a single reviewer scoring all 117 rules in one pass
plausibly under-scores some rules inconsistently relative to structurally
similar ones, inflating the appearance of family variance that a second,
independent reviewer wouldn't reproduce.

**Test**: spot-checked the 8 "amount/timing is undeterminable"-type
rules clustered in Administrative/Financial for internal consistency.

**Result: real but too small to matter.** Found a genuine inconsistency:
`M_USAGE_MEASUREMENT_01` ("billing amount effectively undeterminable")
was scored `FB=1, REV=1`, while `M_CURRENCY_AMBIGUOUS_01` ("payment
reconciliation errors") and `M_PRICE_EXHIBIT_MISSING_01` ("pricing...
unusable for invoicing") — describing the same underlying kind of fact —
were scored `REV=1` only, with no FB. This is real within-reviewer noise,
not a phantom. But even correcting it moves Administrative's ceiling from
3 to roughly 9 — nowhere near the 18 threshold that would need to be
cleared to change the family's locked-out status. The inconsistency is
real; its magnitude cannot explain a gap that runs from pmax=3 to pmax=21
across families. The only test that fully resolves this alternative is
the still-pending §10 blind re-score gate (a second, independent
reviewer) — not something a single reviewer re-scoring their own work can
simulate honestly.

## Verdict

Of five alternative explanations, tested against the existing dataset
rather than argued from priors:

- **A (incomplete factor coverage)** and **E (ontology/batch bias)** are
  actively falsified — removing the rules each hypothesis predicts should
  matter changes nothing.
- **C (family definition error)** is falsified by an independent
  reclustering along an unrelated axis, which reproduces the same
  pattern.
- **B (granularity)** and **D (reviewer artifacts)** both have real,
  demonstrable partial support, but both are too small in magnitude to
  account for a gap spanning pmax=3 to pmax=21 across families.

The original conclusion survives this adversarial pass: WAS's achievable
range genuinely differs by family in a way none of the five alternatives
explains away, though B and D suggest the specific numbers for a few
individual rules (not the qualitative cross-family pattern) are somewhat
noisy and would likely shift slightly under a second reviewer's pass.
