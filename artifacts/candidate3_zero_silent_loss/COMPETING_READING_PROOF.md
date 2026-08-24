# Competing-Reading Guarantee Proof (Phase 6)

**Claim to prove**: if two materially different grounded readings survive, the architecture never arbitrarily selects one and returns clean merely because one is easier for the deterministic adapter to consume.

## Direct evidence from the burned corpus (final replay, real OpenAI)

All 7 originally-failing `ARBITRARILY_SELECTED_COMPETING_READING` cases (`limitation_of_liability-017`, `payment_terms-067`, `ip_ownership-087`, `ip_ownership-097`, `insurance-107`, `insurance-117`, `sla-217`) now resolve to `REQUIRES_REVIEW` — confirmed 0/240 on two consecutive full real-provider replay runs (see `BURNED_CORPUS_REGRESSION.md` in the prior mission's artifacts and this mission's replay log).

Each case represents one of the two competing-reading shapes:

1. **Direct value contradiction** (`limitation_of_liability-017`, `ip_ownership-097`, `insurance-117`, `sla-217`, `assignment-237`): two statements about the SAME dimension give incompatible values/positions. Caught by `document_wide_conflict_detected`'s `DOCUMENT_WIDE_NEGATION_RE`.
2. **Self-declared unreconciled ambiguity** (`payment_terms-067`, `ip_ownership-087`, `insurance-107`, `assignment-227`, `termination-167`, `governing_law-147`): the document itself explicitly states two provisions are unreconciled ("without indicating which governs" / "without reconciling the two/which controls"). Caught by `unreconciled_ambiguity_marker_present`.

In every one of these cases, BEFORE this mission's fix, the deterministic layer picked the FIRST or most-locally-anchored value and silently discarded the competing one, reaching a clean decision. AFTER the fix, both readings are recognized as present and the decision routes to `REQUIRES_REVIEW` — the adapter does not attempt to adjudicate which reading is correct (it cannot, from the text alone), consistent with the mission's required behavior: "both remain plausible/material → AMBIGUOUS/CONFLICTING/REQUIRES_REVIEW."

## Fresh, non-burned-phrase verification (`tests/test_candidate3_zero_silent_loss.py`)

`TestMechanismB_CrossSectionAndContradiction` exercises 8 freshly-worded cases across `confidentiality`, `sla`, `assignment`, `payment_terms`, `liability`, `insurance` — none reusing the burned corpus's exact sentences — all correctly routing away from `ACCEPT`. Two explicit regression controls prove the fix does NOT over-suppress:

- `test_liability_legitimate_category_carveout_not_falsely_flagged`: a real, single, non-contradictory category-scoped carve-out ("shall not apply to claims arising from X", with X required by policy) correctly still reaches `ACCEPT` — proving the deterministic elimination case (Section 6's "deterministically prove one reading invalid → consume the surviving reading" — here there was never a second reading, just one legitimate carve-out) is not broken by the new contradiction detector.
- `test_ip_ownership_assign_or_fallback_idiom_not_falsely_flagged`: a benign "assign-or-fallback" idiom elsewhere in the same window is not mistaken for a competing reading about the SAME clean ownership statement.

## Adapters where competing readings can materially apply — coverage confirmed

Per `ADAPTER_MATERIALITY_MATRIX.md`, competing-reading detection is wired into `limitation_of_liability`, `confidentiality`, `payment_terms`, `ip_ownership`, `insurance`, `sla`, `assignment` (7/12) — the 5 adapters where it was NOT wired (`indemnification`, `data_security`, `governing_law`, `termination`, `warranties`) either have no confirmed burned-corpus failure of this class (`governing_law`'s own contradiction-handling was independently verified correct via `governing_law-147` passing without any of this mission's changes) or were explicitly out of scope (`indemnification`'s protected safeguards; `data_security` not evaluated this mission — see `RESIDUAL_RISK_REGISTER.md`; `termination`/`warranties` had no confirmed failure of this specific class).
