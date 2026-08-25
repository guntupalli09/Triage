CANDIDATE 4 — PHASE 12: BURNED 660-CASE CORPUS REGRESSION

Corpus: the SAME frozen 660-case independent-validation corpus from
Mission B, now burned. Verified unmodified via its own canonical-JSON
hash check inside `run_independent_corpus.py` (reused, not
reimplemented) before this run. Not edited, regenerated, tuned, or
relabeled. Executed once against the current (Candidate 4) code with the
real OpenAI provider and the same `FACT_ADMISSION_MODE=enforced`,
`INDEMNIFICATION_SEMANTIC_DISCOVERY_ENABLED=true`,
`INDEMNIFICATION_RECONCILIATION_ENABLED=true` configuration Candidate 3's
run used.

## An operational incident, disclosed in full

The first execution attempt (`run_burned_regression.py`) silently lost
236 of 660 records: while it was mid-run, a `git stash`/`git stash pop`
cycle (used to compare a single case's pre-fix behavior — see
`PHASE11_REPEATABILITY.md`) checked out and rewrote the SAME tracked file
the running process held open for append, truncating it. The process's
own progress log reported reaching 660/660, but the file on disk had only
424 complete, valid, newline-terminated JSON records afterward — a clean,
contiguous range of case_ids (starting at `iv-governing_law-0425`) never
made it to disk, not corrupted or malformed data. `resume_burned_
regression.py` was written to re-run ONLY the missing 236 case_ids
(computed by diffing recorded `case_id`s against the corpus) and append
them, leaving the 424 already-present records untouched. Final
integrity, verified: 660 total lines, 660 unique `case_id`s, exact set
match against the corpus, zero malformed lines. No result was discarded,
edited, or relabeled — the incident cost re-execution of 236 cases, not
data integrity. This is reported per this engagement's standing
disclosure discipline rather than omitted.

## Hard safety gate results

| Gate | Candidate 3 (prior run) | Candidate 4 (this run) | Required |
|---|---|---|---|
| FALSE_SAFE | 0 | **0** | 0 |
| FALSE_OPERATIVE_TO_CLEAN | 0 | **0** | 0 |
| UNVERIFIED_FEEDING_CLEAN | 33 | **6** | 0 |
| FALSE_ABSENCE | 9 | **11** | 0 |
| MATERIAL_CONTEXT_SILENTLY_LOST | 3 | **4** | 0 |
| ARBITRARILY_SELECTED_COMPETING_READING | 6 | **0** | 0 |
| UNRESOLVED_CROSS_REFERENCE_TO_CLEAN | 9 | **0** | 0 |
| UNRESOLVED_DEFINITION_TO_CLEAN | 17 | **17** | 0 |

**4 of 8 hard gates are non-zero. This burned-corpus regression does NOT
meet the mission's "ALL EIGHT MUST BE ZERO" requirement.**

The two non-negotiation gates (Phase 9) held at zero, as required:
`FALSE_SAFE=0`, `FALSE_OPERATIVE_TO_CLEAN=0`.

## What genuinely improved, and why

- `ARBITRARILY_SELECTED_COMPETING_READING`: 6 → 0, and
  `UNRESOLVED_CROSS_REFERENCE_TO_CLEAN`: 9 → 0. Both gates require a
  candidate to have been ADMITTED (or a note surfaced) before a
  competing-reading or cross-reference note can be lost or arbitrarily
  resolved. The Cluster 1 fix's effect on `insurance`/`data_security`/
  `ip_ownership` materially increased the rate at which these adapters
  correctly surface `PRESENT_BUT_UNRESOLVED` rather than silently
  discarding the underlying candidate — as a direct side effect, the
  competing-reading and cross-reference notes riding along with those
  candidates are now also surfaced rather than discarded with them. This
  is a genuine, traceable causal link, not coincidence.
- `UNVERIFIED_FEEDING_CLEAN`: 33 → 6 (82% reduction). The 6 remaining
  occurrences are all `insurance` cases from the SAME adversarial
  families (`iv-insurance-0277/0286/0295/0304/0313/0322`) already
  disclosed in Candidate 3's report as affected by the templating
  inconsistency (generic "liability coverage" phrasing the deterministic
  `cgl` classifier does not recognize) COMBINED with a genuine AI recall
  miss on the same text in this specific run. This mission's fix reduces
  but does not fully eliminate this gate because these SPECIFIC 6 cases
  hit a compound failure (deterministic AND semantic channels both miss
  the same text), which Cluster 1's fix — designed for "found_anything is
  True via an operative anchor" — cannot help when the anchor itself
  requires the SAME phrasing the deterministic classifier already
  requires (i.e., `found_anything`'s own operative-context check still
  needs an anchor MATCH to exist in the first place; a phrasing so
  generic it fails to match `_ANCHOR_RE`'s coverage-type sub-patterns at
  all is a different, deeper defect than the one this mission targeted).

## What did NOT improve, and the honest reason why

- `FALSE_ABSENCE`: 9 → 11 (worse by 2). `UNRESOLVED_DEFINITION_TO_CLEAN`:
  17 → 17 (unchanged). Both are now dominated by `ip_ownership`'s
  "conditional" family (`iv-ip_ownership-0220/0221/0229/.../0268` — 8 of
  11 `FALSE_ABSENCE` occurrences, 6 of 17 `UNRESOLVED_DEFINITION_TO_CLEAN`
  occurrences). This mission's `ip_ownership` fix specifically targets
  the case where a DETERMINISTIC ANCHOR IS present and operative but
  nothing structures from it. The "conditional" family's exact phrasing
  ("Title... shall transfer to Recipient upon...") does NOT match
  `ip_ownership_policy_engine.py`'s `_ANCHOR_RE` at all (confirmed by
  direct inspection: the pattern requires "intellectual property" /
  "proprietary rights" / "work product" / "work made for hire" / "license
  grant" / "IP ownership" — none of which appear in this phrasing). With
  zero deterministic anchor, the ENTIRE decision for these cases depends
  on whether the real OpenAI provider admits a semantic candidate for
  this specific text — and Phase 11's repeatability check directly
  confirmed (via 5x re-execution of `iv-ip_ownership-0220`, both before
  and after this mission's fix) that this admission is non-deterministic:
  it succeeds roughly 1 run in 5. This single one-shot execution happened
  to land more of these coin-flips on the "missed" side than Candidate
  3's one-shot execution did — a real, inherent consequence of a
  single-shot real-provider run against a case family whose outcome is
  already known (Phase 11) to vary run-to-run, not a code regression this
  mission introduced (confirmed: `ip_ownership_policy_engine.py`'s
  ANCHOR pattern and this failure path are unmodified by this mission's
  diff). Closing this class of failure would require broadening
  `_ANCHOR_RE`'s deterministic vocabulary to catch generic ownership-
  transfer language, which was deliberately NOT done in this mission
  because it risks widening the anchor's false-positive surface on
  unrelated "title"/"transfer" language elsewhere in a contract — a
  change of that shape needs its own adversarial test design and
  regression pass, out of THIS mission's scope of fixing the specific
  root causes already diagnosed, not inventing a new one under time
  pressure.

## Twelve-adapter matrix (this run)

| Adapter | Result |
|---|---|
| Limitation of Liability | PASS |
| Indemnification | PASS |
| Termination | FAIL (1 MATERIAL_CONTEXT_SILENTLY_LOST occurrence, `iv-termination-0651` — pre-existing, adapter untouched this mission) |
| Confidentiality | PASS |
| Assignment | FAIL (2 MATERIAL_CONTEXT_SILENTLY_LOST occurrences — pre-existing, adapter untouched this mission) |
| Governing Law | PASS |
| Data Protection & Security | PASS (this mission's fix here fully resolved this adapter's contribution to every hard gate) |
| IP Ownership & Licensing | FAIL (8 FALSE_ABSENCE, 6 UNRESOLVED_DEFINITION_TO_CLEAN — see above) |
| Insurance | FAIL (6 UNVERIFIED_FEEDING_CLEAN, 6 UNRESOLVED_DEFINITION_TO_CLEAN — the compound-miss cases above) |
| Payment Terms | PASS |
| Warranties | FAIL (3 FALSE_ABSENCE, 5 UNRESOLVED_DEFINITION_TO_CLEAN — pre-existing AI recall-miss class, adapter untouched this mission) |
| SLA / Service Levels | FAIL (1 MATERIAL_CONTEXT_SILENTLY_LOST — pre-existing, adapter untouched this mission) |

6/12 PASS (up from 5/12 in Candidate 3's independent-validation run;
`data_security` moved from FAIL to PASS as a direct result of this
mission's fix).

## Conclusion

Real, verifiable progress was made on the exact root causes diagnosed in
Phase 0 (2 gates fully closed, 1 gate reduced 82%), and the two
non-negotiable gates remained at zero throughout. But the mission's
explicit Phase 12 requirement — ALL EIGHT gates at zero — is not met.
Per Phase 9's own instruction ("do not reinterpret a nonzero safety gate
as acceptable"), this is reported as a genuine, unresolved gap, not
downplayed by the aggregate pass-rate improvement (75.9%, up from 74.2%).
