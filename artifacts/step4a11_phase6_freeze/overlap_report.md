# Step 4A.11 Phase 6 — Final Corpus Overlap Report

## Methodology

Two mechanical checks, both literal-text (no embeddings/LLM judgment):

1. **6-word n-gram overlap** (`scripts/step4a11_phase6_overlap_check.py`) — same
   methodology as Phase 4's own overlap check, extended to also compare against
   the Phase 4 battery itself. Flags any final-corpus case sharing at least one
   6-consecutive-word run with any case in: Step 4A.10 corpus (394 cases),
   Phase 1 cross-reference DEV benchmark, Phase 2 conditional-applicability DEV
   benchmark, Phase 3 structural DEV benchmark, Phase 4 fresh adversarial
   battery (174 cases) — 726 prior cases total.
2. **Longest-common-consecutive-word-run** binary search, used to separate
   "ordinary short legal idiom recurring by chance" from "a longer run
   indicating actual near-copying," since 6-word idiom overlap ("third party
   claim arising out of," "shall not exceed the total fees") is expected and
   not itself evidence of copying.

**Disclosed limitation** (unchanged from Phase 4's own methodology note): this
cannot detect purely conceptual reuse — the same legal scenario described in
entirely different words. That is a design intent verified by self-review of
the case list against the templates used in Phase 1-4, not by this script.

## Findings and disposition

- 193/391 final-corpus cases share >=1 six-word run with a prior corpus case —
  expected given the domain: standard section headings ("12. Limitation of
  Liability."/"9. Payment Terms.") and canonical verb phrases ("shall
  indemnify, defend, and hold harmless," "shall not exceed") are the ordinary
  vocabulary of commercial contract drafting and recur across any two
  indemnification/liability/payment corpora regardless of independent
  authorship.
- The longest-common-run check found an initial maximum of 15 consecutive
  shared words on 6 cases, and 12 total cases sharing a run of >=13 words —
  each traced back to a Phase 4 battery template this same session authored
  (not a prior-session/prior-phase corpus), specifically: the liability
  cross-reference decoy structure (`fab-lia-af4-multiple-candidate-targets-01`),
  a payment late-fee sentence, a payment "provided that... does not apply to
  disputed invoices" proviso, and a reciprocal-indemnification-with-defense-
  control sentence. **All 4 were rewritten** with different lead-in phrasing,
  different connective structure, and (for the liability case) different
  labels/values, before the corpus was locked — see the corresponding case
  templates in `benchmarks/step4a11_final_corpus.py` for the revised text.
- After revision, the maximum remaining shared run is 12 consecutive words,
  confined to the literal section-heading-plus-lead-in convention ("9. Payment
  Terms. [Party] shall pay [Party] within Net N days of receipt of invoice,
  provided that the invoice") — this is standard Net-N-with-proviso drafting
  phrasing, not reproduction of a specific prior case's unique content (the
  role names, specific day counts, and the substance of each proviso all
  differ). Disclosed and accepted rather than further rewritten, consistent
  with the methodology's own explicit exclusion of ordinary short-phrase
  recurrence from "copying."
- No case was found to reproduce a prior case's FULL sentence, its specific
  numeric values AND role names AND structural shape together — the
  combination that would indicate an actual paraphrase rather than shared
  domain idiom.

## Conclusion

The final corpus is judged independent under this methodology: the worst
offenders (near-verbatim reuse of this session's own Phase 4 battery
sentences) were found and rewritten before lock; the residual overlap is
ordinary, unavoidable legal-drafting boilerplate below the threshold this
methodology treats as copying.
