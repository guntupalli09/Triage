# Step 4A.6 Corpus Diversity Report

Run before locking, per instructions.

## Duplicate/near-duplicate text check

212 semantic cases, 206 unique text bodies. All 6 "duplicates" are
INTENTIONAL: compound-case companion pairs where the SAME document is
scored twice, once per adapter, to test independent-adapter extraction
on a shared multi-clause document (A6-C-01/02, A6-C-16/17, A6-C-19/20,
A6-C-22/23, A6-C-24/25, A6-C-27/28). This is the documented methodology
for the compound family, not accidental repetition.

## Template/repeated-structure check

The corpus is NOT built from a small number of templates with renamed
entities. Sentence structures vary substantially across families:
plain single-obligation sentences (Tier 1), heavily-qualified run-on
sentences with boilerplate (Tier 2), passive-voice/subordinate-clause
constructions (grammatical-subject family), tabular/field:value
structures (structural family), multi-sentence definitions with
cross-references (role-definition family), and two-sentence (rather
than single run-on) reciprocal structures (A6-I-36). No single sentence
skeleton is reused more than a handful of times, and where a shape IS
intentionally repeated (e.g., "X shall indemnify... and Y shall
indemnify... in each case...") it is because that shape is the actual
object under test (reciprocal-pair recognition) — varying it away would
defeat the purpose of that specific family.

## Role-name reuse

Some names recur across multiple cases WITHIN a thematic family by
design — e.g., "Ceding Reinsurer"/"Underwriting Manager"/"Fronting
Insurer" appear across ~10-12 cases each because several
direction-invariance and reciprocal-scope-exclusion cases deliberately
hold the SAME named pair constant while varying only the construction
being tested (a genuine ambiguity, a genuine symmetric control, a
different differentiation dimension), which isolates the mechanism
under test rather than conflating it with entity-name novelty. This is
a legitimate design tradeoff, not a name-reuse artifact of low effort —
but it is disclosed here rather than hidden: roughly 35-40 distinct
role-name pairs are used across the 212 cases, with the top 3-4 pairs
(reinsurance and wine-distribution domains) each appearing in 10-14
cases. No role-name pair from Step 4A.2, Step 4A.4, or any Step 4A.5
benchmark/corpus is reused.

## Numeric-structure diversity

Multiplier values span 1x-5x; fixed-dollar values span $8,000-$4,000,000;
Net-day values span 5-45 (including business-day and calendar-day
variants); late-fee/tax/currency/dispute-window figures are similarly
varied across cases. No single numeric pattern dominates.

## Domain diversity

37 distinct business domains are used across the corpus (renewable
energy trading, veterinary services, ski-resort operations, marina/boat
storage, craft-brewery/wine distribution, solar installation,
coworking, drone services, 3D-printing manufacturing, meal-kit
delivery, HVAC servicing, self-storage, data-center colocation,
cybersecurity consulting, medical-billing/dental-practice/optometry/
physical-therapy healthcare-adjacent services, biotech licensing,
art-gallery consignment, aquarium exhibits, adventure tourism,
industrial-park management, cooperative grain milling, loan
servicing/origination, reinsurance/underwriting, maritime charter,
import/customs brokerage, franchise operations across several
verticals — dry-cleaning, fitness, vision-care, spa/wellness — and
more), none overlapping the domain lists used in step4a4_corpus.py or
step4a5_adversarial_battery.py's docstrings.

## Conclusion

The corpus is not a paraphrased regression of any prior corpus. It is
not 20 templates with renamed entities. Deliberate, disclosed
within-family name/pair repetition exists for a small number of
thematically-linked test families where holding names constant isolates
the mechanism under test; this is flagged, not hidden. No changes made
to the corpus as a result of this check — it was judged acceptable
before locking.
