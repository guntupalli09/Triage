"""Step 4A.6 — master aggregator for the independent frozen held-out
validation corpus. Combines all category files into ALL_CASES.

LOCKED after benchmarks/step4a6_checksums.txt is written. See
artifacts/step4a6/step4a6_final_report.md for full methodology."""

from benchmarks.step4a6_corpus_liability import LIABILITY
from benchmarks.step4a6_corpus_liability_ownership import LIABILITY_OWNERSHIP
from benchmarks.step4a6_corpus_liability_absence import LIABILITY_ABSENCE
from benchmarks.step4a6_corpus_liability_subject import LIABILITY_SUBJECT
from benchmarks.step4a6_corpus_liability_role import LIABILITY_ROLE
from benchmarks.step4a6_corpus_indemnification import INDEMNIFICATION
from benchmarks.step4a6_corpus_indemnification_reciprocal import INDEMNIFICATION_RECIPROCAL
from benchmarks.step4a6_corpus_indemnification_subject import INDEMNIFICATION_SUBJECT
from benchmarks.step4a6_corpus_indemnification_direction import INDEMNIFICATION_DIRECTION
from benchmarks.step4a6_corpus_indemnification_absence import INDEMNIFICATION_ABSENCE
from benchmarks.step4a6_corpus_payment import PAYMENT
from benchmarks.step4a6_corpus_payment_more import PAYMENT_MORE
from benchmarks.step4a6_corpus_payment_final import PAYMENT_FINAL
from benchmarks.step4a6_corpus_compound import COMPOUND
from benchmarks.step4a6_corpus_compound_more import COMPOUND_MORE
from benchmarks.step4a6_corpus_ratio_balance import RATIO_BALANCE

ALL_CASES = (
    LIABILITY + LIABILITY_OWNERSHIP + LIABILITY_ABSENCE + LIABILITY_SUBJECT + LIABILITY_ROLE
    + INDEMNIFICATION + INDEMNIFICATION_RECIPROCAL + INDEMNIFICATION_SUBJECT
    + INDEMNIFICATION_DIRECTION + INDEMNIFICATION_ABSENCE
    + PAYMENT + PAYMENT_MORE + PAYMENT_FINAL
    + COMPOUND + COMPOUND_MORE
    + RATIO_BALANCE
)

# Sanity: no duplicate IDs.
_ids = [c["id"] for c in ALL_CASES]
assert len(_ids) == len(set(_ids)), "duplicate case ID found in Step 4A.6 corpus"
