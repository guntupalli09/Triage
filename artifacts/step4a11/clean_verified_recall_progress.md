# Step 4A.11 — Clean-Verified Recall Progress Measurement

**Development-time evidence. Not the final Step 4A.11 authoritative
measurement.** This is a PRE→POST progress check against the Step 4A.10
corpus, taken because that corpus turned out to be exactly reproducible
(see below) — not a substitute for the eventual independent, locked,
≥300-case frozen corpus the mandate requires before any final verdict.

## A disclosed limitation from earlier in this program is now resolved

The original Section 4 inventory and both Phase 1/Phase 2 checkpoints
disclosed that the Step 4A.10 corpus text was "not preserved as a
standalone artifact," so no honest PRE→POST Clean-Verified Recall could
be measured directly. That is no longer true: `benchmarks/
step4a10_benchmark.json` (the actual 394-case corpus artifact Step
4A.10 scored) is present in the repository, and
`scripts/step4a10_generate_corpus.py` (deterministic — no `random`/seed
usage) independently reproduces it byte-for-byte identical (checked:
0/394 mismatches). Both give the same answer; the saved artifact was
used for this measurement.

## Methodology (matches Step 4A.10's own, exactly)

Reused `scripts/step4a10_analyze.py`'s own `clean_verified_recall`
definition verbatim: among the corpus's 220 POSITIVE-labeled cases, the
fraction where `extract_indemnification_facts(text).absence_state ==
"PRESENT_AND_VERIFIED"`. No other criterion, no relabeling, no
selection — every one of the 220 positives run through the exact same
current production `extract_indemnification_facts`.

## Result

| | PRE (Step 4A.10 baseline, frozen) | POST (current, end of Phase 3) |
|---|---:|---:|
| Clean-Verified Recall (220 positives) | 24.5% (54/220) | **63.2% (139/220)** |
| Hard-negative false engagement (144 non-injection negatives) | not separately reported at this granularity in Step 4A.10 | **0/144** |

**63.2% clears the frozen ≥44.5% target by 18.7 absolute percentage
points**, using the exact original denominator and the exact original
methodology — the strongest, most direct evidence available that this
step's development work is real, not cosmetic.

By tier (positives only):

| Tier | PRE | POST |
|---|---:|---:|
| 1 (canonical) | 30.0% | 100.0% |
| 2 (noncanonical, moderate) | 20.0% | 41.4% |
| 3 (noncanonical, hard) | 20.0% | 20.0% |

Tier 3 is unchanged — expected: Category A's decomposition (see
`category_a_decomposition.md`) found the tier-3-weighted cases include
the genuinely unsolvable nominalized-reference family and several
categories (B/C/G/J/K/L/M from the original inventory) not yet
addressed by Phase 3's specific mechanism. Tier 1 reaching 100% and
tier 2 more than doubling directly reflects the structural risk-transfer
mechanism (Phase 3) plus the cross-reference (Phase 1) and conditional-
applicability (Phase 2) mechanisms compounding.

## A genuine regression this measurement caught, fixed before this
   number was finalized

Running the FULL 144-case hard-negative set (not just the 88-case
Category A subset or the 62-case DEV benchmark) surfaced a real false-
establishment defect the DEV benchmark's own hard negatives had not
covered: the `bare_reimburse` structural pattern (added this phase)
matched **12/144** hard negatives — ordinary expense reimbursement
("Client shall reimburse Vendor for reasonable travel expenses...") and
fee-paid-on-behalf language ("...reimburse Vendor for third-party
licensing fees Vendor pays on Client's behalf...") — because the
generic claim/loss-noun proximity gate treats "expenses" and "third
party" as sufficient evidence on their own, which is exactly the false-
positive risk this module's own long-standing comments warn about
("reimburse Client for prepaid amounts... not risk transfer"). Fixed by
requiring the claim/loss noun to be the DIRECT grammatical object of
"for" ("reimburse X for [that/any/such] claim/loss/damages/judgment"),
not merely present somewhere in a wide surrounding window. A second,
unrelated bug was found and fixed in the same pass: the fix's own first
draft used `losses?` as a regex fragment, which matches the literal
string "losse"+optional "s" — NOT "loss" alone (a pre-existing quirk
this module's shared `_CLAIM_LOSS_NOUN_RE` also carries, left
untouched, out of scope) — corrected locally to `loss(?:es)?`.

Sequence, disclosed exactly as it happened: an initial unverified read
of 63.2% (139/220) was taken before the 144-case hard-negative set was
checked at all; checking it found the 12 false positives above; the
direct-object tightening fix (first attempt) dropped Clean-Verified
Recall to 60.5% (133/220) while also losing 2 DEV-benchmark true
positives, because its `losses?` regex fragment silently failed to
match singular "loss"; correcting that fragment to `loss(?:es)?`
restored both — final: **0/144 false PRESENT_AND_VERIFIED** (down from
12) and Clean-Verified Recall back to 63.2% (139/220), with the 62-case
Phase 3 DEV benchmark at 62/62 exact match. This is disclosed in full
rather than silently reported as a clean first-pass result.

## What this number is and is not

- **Is**: honest, reproducible, apples-to-apples evidence, on the exact
  original denominator and methodology, that development work through
  Phase 3 materially increased deterministic automation without
  increasing false engagement on the same corpus's hard negatives.
- **Is not**: the final Step 4A.11 authoritative measurement. The
  mandate requires an independently-authored, locked, ≥300-case corpus
  run exactly once, after candidate freeze — this number does not
  substitute for that. Development is not complete (Category A's
  remaining ~3 nominalized-reference cases, and inventory categories B/
  C beyond what Phases 1-2 already cover, G/J/K/L/M, remain); the
  120+ fresh adversarial battery, the material-fact trust audit, the
  false-absence audit, and the security audit have not yet run.
- This corpus is now known to be reproducible and will be excluded (or
  explicitly treated as non-independent, disclosed prior exposure) from
  the eventual frozen validation corpus, since it has now been used for
  active development measurement, not held out.
