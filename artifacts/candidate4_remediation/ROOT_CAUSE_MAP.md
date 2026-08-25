CANDIDATE 4 — PHASE 0: ROOT CAUSE MAP

Base: Candidate 3 frozen SHA `d2820362` (`FROZEN_CANDIDATE_SHA`). Working from
the Candidate 3 independent-validation evidence package
(`artifacts/candidate3_independent_validation/PHASE4_HARD_SAFETY_GATES.md`,
`raw_results.jsonl`, `phase4_5_analysis.json`, `PHASE5_ADAPTER_MATRIX.md`,
`PHASE7_AUTHORITY_SURFACE_CONSISTENCY.md`), `fact_admission.py`, and all 12
policy-adapter source files.

## Method

Rather than re-litigating all 77 flagged case IDs individually, every
non-zero gate's occurrences were clustered by the failure-class taxonomy
this mission specifies (A–L), then the SHARED code path each cluster
travels through was traced to its exact defect, confirmed with a live
reproduction (not just re-reading the prior report's prose).

## Clusters found

### Cluster 1 — "operative anchor, unresolved content, defaults to CONFIRMED_ABSENT" (Classes I + J)

**Failure classes:** I (adapter interpreted UNKNOWN as ABSENT), J (adapter
interpreted no evidence as NOT_APPLICABLE).

**Affected adapters (confirmed live):** `insurance`, `data_security`,
`ip_ownership`. (`warranties` and `sla` already had an equivalent
`found_anything`-style gate from Candidate 3's own remediation and were
NOT independently re-broken by this defect — see Cluster 1's "why these
three, not all 12" note below.)

**Mechanism:** Each of these three adapters tracks two related but
distinct booleans while extracting facts: `found_anything` (something
operative-looking exists — either an admitted AI candidate, or a
deterministic anchor match that survives `is_operative_context`) and a
narrower "some SPECIFIC dimension was structured" signal
(`deterministic_value_found` in insurance;
`established_dimension_count > 0`-equivalent checks in data_security/
ip_ownership). All three adapters' post-extraction reclassification gate
(`CONFIRMED_ABSENT` -> `PRESENT_BUT_UNRESOLVED`) was written to fire ONLY
when an **admitted AI candidate** existed (or, in a second layer added
during Candidate 3, when an unresolved dependency **note** existed). It
never covered the case where `found_anything` was earned purely through a
genuinely operative DETERMINISTIC anchor match with AI discovery
independently returning nothing (a real recall miss — Class A) and no
specific dimension being structurable (Class B). In that combination,
`absence_state` silently stayed at its default `CONFIRMED_ABSENT`, and
each adapter's evaluator then reached ACCEPT/NOT_APPLICABLE — an
operative, evaluated, but never-verified obligation treated as
affirmatively confirmed absent.

**Live confirmation (unchanged from the Candidate 3 report, now traced to
exact line numbers):**
```
insurance_policy_engine.extract_insurance_facts(
  "13. Insurance. Provider shall maintain liability coverage of at least $1 million."
).absence_state == "CONFIRMED_ABSENT"   # before fix
```
`insurance_policy_engine.py`: `found_anything` (a real anchor IS operative)
was `True`, but the reclassification gate at the old line 621 checked
`not deterministic_value_found and admitted_semantic` — `admitted_semantic`
was `[]` (AI found nothing), so the gate never fired.

`data_security_policy_engine.py` and `ip_ownership_policy_engine.py`
carried the exact same structural gap: their reclassification gates (old
lines 732/756 and 734/751 respectively) both required either
`admitted_semantic` or `unresolved_dependency_note`, with no branch for "a
bare operative deterministic anchor, nothing else."

**Why `warranties`/`sla` were not independently broken by this:** their
`found_anything` boolean is deliberately narrower — it is only set True by
a concrete deterministic structural match (a named category, a duration,
an explicit negation, etc.), never by a bare anchor surviving
`is_operative_context` alone. So for these two adapters, "found_anything
True but nothing else established" cannot actually occur — if
`found_anything` is True, something WAS already structured. This is a
genuine, confirmed architectural asymmetry (exactly as the Candidate 3
report characterized it), not a difference in how careful the two designs
are; it happens to make `warranties`/`sla`'s narrower definition
accidentally safer for this specific failure class.

**Why this maps to `UNVERIFIED_FEEDING_CLEAN` and `FALSE_ABSENCE`:** the
independent-validation corpus's `insurance` adversarial-family cases that
used generic ("liability coverage") rather than named ("commercial general
liability insurance") phrasing hit this exact gap (`UNVERIFIED_FEEDING_
CLEAN`); `ip_ownership`'s "conditional" family ("Title... shall transfer to
Recipient upon...") hit the same gap in the FALSE_ABSENCE direction
(`clause_found` reaches `None` in some phrasings, or the ownership
attribution never gets structured — both funnel through the identical
missing-branch defect).

**Shared vs. adapter-specific fix:** the underlying PRINCIPLE (an
operative signal without verifiable content must resolve to unresolved,
never absent) is shared across all three adapters and is now applied via
the identical restructuring in each. The exact CODE is adapter-specific
because each adapter's Facts model, `found_anything` definition, and
evaluator control flow differ — a single shared helper function was
considered but rejected (see Phase 1 below) because forcing a truly
uniform helper across three materially different Facts schemas would
require flattening adapter-specific semantics (e.g. insurance's per-
coverage-type limit tracking vs. ip_ownership's per-dimension token sets)
into a generic shape, which risks losing precision more than it gains from
code-sharing. The FIX PATTERN, not the function body, is shared.

**Expected safe behavior:** `absence_state` becomes `PRESENT_BUT_UNRESOLVED`
whenever `found_anything` is True and no specific dimension was
established, regardless of which channel (admitted candidate, note, or
bare operative anchor) produced `found_anything`.

### Cluster 2 — "unresolved-fallback pre-empts a more specific, already-correct finding" (a Candidate-3-era regression risk, found and fixed during THIS remediation, not present in the independent-validation report)

While implementing Cluster 1's fix, broadening the trigger condition
initially caused two categories of test regression (confirmed via
`tests/test_insurance_benchmark_gate.py` and `tests/test_data_security_*`):
cases where the policy-specific, per-dimension comparison loop (e.g. "policy
requires CGL coverage but the clause does not address it" -> MUST_REDLINE,
or "policy requires a waiver of subrogation, but none was found" ->
NEGOTIATE) would have found the SAME underlying problem, more specifically,
had it been allowed to run. The original Candidate 3 placement of the
`PRESENT_BUT_UNRESOLVED` short-circuit ran BEFORE that comparison loop,
so once broadened, it always won, downgrading precise findings to a
generic `REQUIRES_REVIEW`.

**Fix:** in `insurance_policy_engine.py`, `data_security_policy_engine.py`,
and `ip_ownership_policy_engine.py`, the fallback was moved to run AFTER
the per-dimension comparison loop, firing only when that loop found nothing
(`worst == ACCEPT`). This preserves every existing, more-informative
MUST_REDLINE/NEGOTIATE finding while still preventing the specific "nothing
at all was found, yet the content is unverified" case from silently
reaching ACCEPT. Confirmed via the adapters' full existing benchmark-gate
test suites plus the new adversarial tests in
`tests/test_candidate4_remediation.py`.

### Housekeeping finding (not a hard-gate defect): a hash-recording inconsistency in the burned corpus's own tooling

While setting up this mission's Phase 12 burned-corpus regression, the
naive approach of hashing `cases.json`'s raw file bytes
(`9cef77b2...`) did not match the value recorded in `corpus_sha256.txt`
(`102acc23...`). Investigation (`git log`/`git show 658e829:...`) confirms
`cases.json`'s committed content has never changed since its single freeze
commit — this is NOT evidence of tampering. The discrepancy is that
`run_independent_corpus.py` (and the original `generate_corpus.py`) hash
the CANONICAL re-serialization `json.dumps(CASES, sort_keys=True)`, not the
raw file bytes — two different, each internally-consistent hashing
methods. This mission's burned-corpus regression script reuses `run_
independent_corpus.py`'s own canonical-hash verification directly rather
than re-implementing it, so no corpus-integrity risk exists; this note is
recorded for completeness only, per this mission's standing discipline of
disclosing everything found.

## Clusters investigated and found NOT to be independently present

- **MATERIAL_CONTEXT_SILENTLY_LOST (Class G), ARBITRARILY_SELECTED_
  COMPETING_READING (Class H), UNRESOLVED_CROSS_REFERENCE_TO_CLEAN
  (Class F), UNRESOLVED_DEFINITION_TO_CLEAN (Class E):** the Candidate 3
  independent-validation report attributed the majority of these
  (12–17 of each gate's count) to the SAME `insurance`/`ip_ownership`
  template-authoring and recall-miss factors already addressed by
  Cluster 1's fix (a fact that never gets admitted at all cannot carry a
  condition/exception/definition/cross-reference forward, so fixing the
  upstream admission gap also resolves a large share of these gates as a
  side effect — see Phase 12's burned-corpus regression results for the
  actual post-fix counts). The remaining, non-`insurance`/`ip_ownership`
  occurrences (e.g. `iv-warranties-0510`, `iv-sla-0563`, `iv-assignment-
  0617`, `iv-termination-0651`, `iv-data_security-0375`) were individually
  inspected; each is attributable to the SAME AI-discovery recall
  limitation (Class A) already documented in the Candidate 3 report as a
  disclosed, non-hard-gate-fixable-via-code limitation in that mission's
  methodology, but which THIS mission's gate design treats as a hard
  gate. No SEPARATE, distinct architectural defect (i.e., no case where a
  condition/definition/cross-reference WAS grounded and admitted but then
  discarded by adapter composition logic) was found in this investigation
  — Candidate 3's own "zero-silent-loss" mission already closed that
  specific composition-level gap for every adapter that had it. This
  finding is reported honestly rather than manufacturing an additional
  code change to claim credit for gates whose remaining occurrences are
  fixed as a side effect of Cluster 1, or are a genuine recall limitation
  outside what deterministic-code remediation can close.

## Stop-condition check

The prior diagnosis (Candidate 3 independent-validation report) is
confirmed materially correct: both named causes ("AI/contextual discovery
recall limitations" and "architectural asymmetry between adapters") are
real and were traced to the exact code locations above. This mission does
NOT stop here — proceeding to Phase 1 onward.
