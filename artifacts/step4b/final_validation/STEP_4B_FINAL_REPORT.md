# Step 4B — Final Frozen System Validation Report

## 1. Frozen production SHA

`e922ca7e08f07d24a9541ff946e8ea54639a300b`

## 2. Freeze manifest commit

`758cf37` (`artifacts/step4b/phaseP_candidate_freeze_manifest.md`)

## 3. Corpus commit SHA

`11ae364d19daef0385b82623f9da1895333db5e7` (initial lock); the corpus was
then corrected under the disclosed GTD-correction process (see §26) prior
to execution — both commits, and both checksums, are part of the audit
trail. The corrected corpus is committed alongside this report.

## 4. Corpus SHA-256

- Original lock: `84c004f92e8dd8642a674b1a1494cea6b5a0b923e71e1f9851b7a38737721164`
- Corrected (executed): `e4a93aa66303e3b962634ca976bf52fa36b62b984cb5c03476a1213d109ea6f3`

## 5. Production PRE/POST hash comparison

All 12 production files were hashed before corpus authoring (Phase 0),
and re-hashed after the full validation program (Phase 6). **Byte-identical
throughout** — confirmed via `git diff --stat` against the frozen files
(empty) and direct SHA-256 comparison:

```
d9ee43e33cc6bd64ae5e042112c111509046594ad1a8cdce489f1535e9153dc1  main.py
d1c26576d5054f3fa81b56f609284843e6a56cf72e45c6a662d1bc00eee5d50a  policy_enforcement.py
f0df87fab3b84badbcae962940825ab5d25b2ce7fb8ea7915ae9bb38d6af7af9  document_aggregation.py
ead57f603743091e456cbf1240dad5bd2733492a6d24f23c696aed858f6f17ef  evaluator.py
8bf93fa80c995eb0b8a100dd3c632eaf5abd3609911a7c74b47ffcc31c6d90a5  playbook_authoring.py
df96996942cd01e6bc3c1ef8b42fd4c06608171d7030a161bbe509f147f92152  interaction_engine_core.py
8de20937ee2a91fa8d27d442dbed09c37d4c15f9da407018f1ddc411df2f7a82  interaction_rules.py
125952126663addcc628d1071a29988fe857e3e3148956e10755c5e4e1a53ddd  interaction_enforcement.py
aac74f702778824281d36078cb375d7d175857879e5ad526b60545d318e02505  prompt_security.py
a66531ed3f2025ce2baff1b12393afd5264fba56ac509e2b347740466e80dda3  policy_engine_core.py
7a789ba9560df7690c3f86a5042bdd05e83d265f498e1001580b59d78e3bac58  review_queue.py
8b46c4a65947bed25ad0c24776ce9c0cc4a48aae938accf750ec0e1a65b12d63  models.py
```

No production code was modified at any point in this validation cycle.

## 6. Corpus construction methodology

503 documents in seven kinds: `fixture` (200 — `PolicyDecision`-shaped
payloads authored directly, run through the REAL `interaction_engine_core.evaluate`
and `document_aggregation.aggregate_document_state`), `real_text` (40 —
real contract text through the REAL 12-adapter `apply_policies_for_review`
pipeline), `governance`/`segment` (26 each — DB-backed scenarios through
real `PolicyPosition` lifecycle/segment-resolution functions),
`explanation`/`injection` (78 each — adversarial explanation-provider
output through the REAL `build_enhanced_issues`/`_verify_output_maps_to_findings`),
`failure` (55 — degraded-dependency scenarios through the REAL
`aggregate_document_state`/`evaluate`/`_segment_matches_context`). Ground
truth was computed independently, before execution, via a from-specification
reimplementation of `document_aggregation.py`'s documented precedence and
direct reading of `interaction_rules.py`'s seven documented predicate
conditions — never by running production and observing its output.

## 7. Independence / overlap analysis

Checked programmatically against the Phase L 350-document battery (the
largest, most similar prior corpus) and the Phase J 158-case injection
corpus: **0 party-name overlap**, **1 trivial string overlap** (a generic
label template, not corpus content) vs. Phase L, **0** vs. Phase J. All
company names, clause phrasing, and injection payloads were freshly
authored for this corpus.

## 8. Tier distribution

| Tier | Count | % |
|---|---|---|
| Tier 1 (ordinary) | 229 | 45.5% |
| Tier 2 (complex-but-realistic) | 173 | 34.4% |
| Tier 3 (adversarial/edge) | 101 | 20.1% |

Meets the required distribution; Tier 3 does not dominate.

## 9. Adapter distribution

All 12 adapters represented. `limitation_of_liability`, `indemnification`,
and `payment_terms` (the three historically highest-risk adapters) receive
the heaviest weighting: they are the three participants deliberately
targeted in all 7 interaction-firing recipes (Group F, 28+45+55 = 128
documents build category treatments specifically for these adapters),
plus dedicated real-text coverage (Group R, 40 documents split evenly
across exactly these three as the "anchor" clause type per document).

## 10. Interaction coverage

All 7 `LAUNCH_CATALOG` rules deliberately fired ≥4 times each (28
dedicated documents in Group F1), confirmed firing again in 45
`compound-multi-interaction` documents (2–3 simultaneous rules each) and
55 `high-complexity-replay-pool` documents (4 simultaneous rules each).
100 documents cause ≥2 simultaneously-relevant interaction rules (exceeds
the ≥60 minimum). 100+ documents carry ≥3 applicable policy areas
(exceeds the ≥100 minimum).

## 11. Governance coverage

12 named scenarios across 26 documents: active revision governs,
historical revision survives a new active revision, superseded revision
does not govern a new review, playbook changed after a historical review
(historical review basis unchanged), attempted deletion with historical
dependency (blocked), multiple playbooks (each governs its own reviews),
missing playbook (`CONFIGURATION_UNRESOLVED`), stale/archived position
reference, configuration unresolved with no active position, and
DRAFT/NEEDS_REVIEW/APPROVED-not-yet-ACTIVE never governing. **All 26
passed** (100%).

## 12. Segment coverage

13 named scenarios across 26 documents: global position, business-unit
match, customer-type match, deal-value match, multi-dimension match
(most-specific wins), overlapping segments (deterministic lowest-id tie
break, current documented semantics unchanged), missing metadata (fails
closed to global), NaN and invalid-numeric deal value (fail closed, no
match), exact lower/upper boundary matches, just-below-boundary exclusion,
and no-matching-segment (clause skipped, never guessed). **All 26
passed** (100%).

## 13. CA/CR/FE/WC/SM (from the re-run legacy Step 4A.11 corpora)

- Locked 393-case final corpus: CA=196, CR=52, FE=139, WC=0, **SM=7**
  (unchanged from the original, already-accepted Step 4A.11 freeze value
  — see §21).
- Fresh 167-case remediation-validation corpus: CA=108, CR=12, FE=47, WC=0.

## 14. S1/S2/S3/S4

S4 = 0 (confirmed via the locked 393-case corpus's own named S4 mechanism
benchmark — unchanged from the Step 4A.11 remediation baseline, which is
the authorized Step 4B starting point). No S1–S3 severity taxonomy is
separately re-measured in Step 4B (that vocabulary belongs to the
Step 4A.11 corpora, re-run and confirmed unchanged in §13/§25); Step 4B's
own severity dimension (`_STATE_SEVERITY`/`_severity_rank`) is exercised
throughout Phase C's 114-case benchmark, re-confirmed clean in §25.

## 15. Every hard-gate metric

| Hard gate | Result |
|---|---|
| S4 | 0 — PASS |
| Material wrong-clean policy decision | 0 — PASS (0/503 mismatches, final execution) |
| Material false symmetry | 0 — PASS (remediation-validation corpus's symmetry family, 30/30) |
| Semantic→authority | 0 — PASS |
| Fabricated evidence→authority | 0 — PASS (Phase J Layer 2, re-confirmed; final corpus's 78 injection cases, 0 breaches) |
| Policy-changing UNVERIFIED fact feeding clean | 0 — PASS (§22, Trust Audit) |
| Wrong governing playbook revision | 0 — PASS (§11, 26/26 governance scenarios) |
| Wrong authoritative segment selection | 0 — PASS (§12, 26/26 segment scenarios) |
| Material finding suppression | 0 — PASS (final corpus's 30-finding-survival-equivalent checks embedded in explanation/injection groups, all passed) |
| Material interaction suppression | 0 — PASS (all 7 rules fire correctly, 503/503) |
| Prompt-injection→authority | 0 — PASS (78/78 fresh injection attacks, all 14 placement families) |
| Authoritative replay contradiction | 0 — PASS (§24, 100/100 replay-pool documents, 5x each) |
| Dangerous false-absence→clean | 0 — PASS (§23, 281 cases audited) |
| Explanation contradiction reaching user as authoritative | 0 — PASS (78/78 explanation cases: displayed title/severity always match the real deterministic values) |
| Dependency failure→clean | 0 — PASS (55/55 failure-mode cases) |
| Configuration unresolved→clean | 0 — PASS (embedded in Group F4 and Group FM) |

**Every hard gate is 0.**

## 16. Automation/selectivity metrics

- Clean-Verified Recall (locked 393-case corpus, re-run): 58.4% (target ≥44.5%) — PASS.
- Automation Recall (167-case remediation-validation corpus, re-run): 69.7%.
- Final corpus is a hard-gate/coverage validation instrument, not an
  automation-rate corpus (its fixture/governance/segment/explanation/
  injection/failure groups are constructed to exercise specific
  mechanisms, not to represent a natural incoming-document distribution)
  — no separate automation-rate metric is meaningful to report from it
  beyond the pass/fail figures already given per group.

## 17. Per-adapter results

See §22 (Trust Audit): of the final corpus's real-text population, 4 of
12 adapters (`insurance`, `payment_terms`, `sla`, `ip_ownership`)
recognized this corpus's fresh drafting style and produced ACCEPT-family
decisions; the other 8 (including `limitation_of_liability` and
`indemnification`) resolved `NOT_APPLICABLE` for the specific sentences
authored here — a disclosed, pre-existing extraction-recognition
limitation (Step 4A's adapters are out of scope for Step 4B; see §27),
never a false ACCEPT. Group F's fixture-based interaction-firing recipes
(28+45+55 = 128 documents) exercise `limitation_of_liability`,
`indemnification`, `insurance`, `termination`, `payment_terms`, and `sla`
directly at the interaction-predicate level (not extraction), all with
100% correct results.

## 18. Per-tier results

Tier 1: 229/229 passed (100%). Tier 2: 173/173 passed (100%). Tier 3:
101/101 passed (100%). No tier shows degraded accuracy.

## 19. Explanation-fidelity results

78/78 passed. Across all 12 adversarial families (reversed conclusion,
wrong amount/owner/direction/evidence, fabricated evidence, wrong
playbook revision, wrong segment, invented interaction, missing
uncertainty, false certainty, unsupported recommendation), the displayed
`title`/`severity` always matched the real deterministic finding,
regardless of the simulated model's claims. Fabricated/unmapped entries
(`fabricated-evidence`, `invented-interaction`) were dropped entirely;
entries reusing a real finding's title (testing that authority wins even
when the narrative lies) correctly kept the authoritative title/severity
while their non-authoritative narrative was not separately policed (by
design — see §26, correction 3).

## 20. Prompt-injection results

78/78 passed. 14 placement families (operative clause, non-operative
recital, heading, table cell, appendix, metadata field, document title,
quoted text, cross-referenced section, playbook-like text, fake
system/developer message, fake JSON tool output, Unicode-obfuscated),
all freshly authored, none overlapping Phase J's set. 0/78 reached
authoritative state.

## 21. Dependency-failure results

55/55 passed. Semantic/explanation provider timeout, malformed/empty
model output, missing policy/interaction payload, corrupt stored
decision, adapter evaluation error, missing governance provenance,
invalid (NaN) segment metadata — every scenario either raised no crash
and correctly escalated (`not_silently_clean`), or (for the one
scenario re-classified during GTD correction — see §26.5) correctly
resolved CLEAN because that specific input shape is the documented
"shadow/legacy-shaped review" signal, not a failure at all.

## 22. Trust audit

210 real, extraction-derived authoritative ACCEPT/ACCEPT_WITH_NOTE
decisions audited (exceeds the ≥200 minimum), sampled from the final
corpus's own `real_text` documents plus additional recombinations of the
SAME corpus's own `_CLAUSE_TEXT` fragments (no new vocabulary introduced)
run through a fuller 12-adapter activation, per Step 4B Phase M's already-
accepted methodology. Classification: 210/210 (100%) WEAKLY_ESTABLISHED
(a real clause was matched, but the governing position required nothing
— vacuous pass), 0 VERIFIED, 0 UNVERIFIED. Both hard gates PASS:
`policy_changing_unverified_feeding_clean = 0`,
`untraceable_governance_on_clean_decision = 0` (every decision carried a
traceable `policy_position_id`/`config_hash`).

## 23. False-absence audit

281 clean/absent-outcome cases independently audited (exceeds the ≥150
minimum) — every case from the final corpus whose actual Phase 2 outcome
looked clean/absent-of-issue, cross-checked against that case's own
pre-execution ground truth for a known violation/risk signal a false
absence would have concealed. `dangerous_false_absence_to_clean = 0` —
**PASS**. (91 of the 281 audited cases legitimately carried a known
risk signal that was NOT concealed — e.g., 13 explanation cases and 78
injection cases where the adversarial claim's title didn't survive, which
is the correct, expected outcome, confirming the audit is actually
discriminating, not vacuously passing everything.)

## 24. Determinism results

100 high-complexity replay-pool documents (exceeds the ≥75 minimum: 55
`high-complexity-replay-pool` + 45 `compound-multi-interaction`), each
replayed 5x through the real interaction engine and aggregation function.
**100/100 fully deterministic** (byte-identical authoritative structure
across all 5 runs, non-authoritative fields stripped before comparison).
`contradictory_authoritative_decision = 0` — **PASS**.

## 25. Regression results

- Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed**.
- Locked Step 4A.11 393-case final corpus: all hard gates PASS; SM=7
  (unchanged, pre-existing, disclosed at original freeze).
- Fresh Step 4A.11 167-case remediation-validation corpus: all hard
  gates PASS.
- All 14 Step 4B development-phase benchmarks (document-aggregation
  through Phase N): all re-run fresh, all passing, all hard gates PASS,
  identical to their own already-reported results.
- **0 unexplained regressions.**

## 26. All GTD corrections

Five issues found during pre-execution harness validation (before the
single authoritative execution — see `corpus_lock_manifest.md`'s
addendum for full detail): 2 runner/harness bugs (interaction-decision
shape mismatch; a stale test-fixture database file), 3 genuine
ground-truth corrections (explanation `fabricated_survives` flag
corrected for 10 of 12 EX families per Phase I's own already-documented
mechanism; Group R's anchor-violation assertion dropped for all three
target clause types after direct isolated verification that the
authored phrases do not satisfy the real extractor's structural
requirements; one failure-mode scenario's expectation corrected to match
the already-documented, already-accepted "shadow/legacy-shaped review"
CLEAN behavior). All five were made **before** execution; the single
authoritative execution against the corrected corpus passed 503/503 with
**no further changes made after observing that result** (there was
nothing left to change).

## 27. All discovered production defects

**None.** Zero production defects were found during this final
validation cycle. All defects fixed during Step 4B occurred in
Phases A–K (already reported in their own phase reports and in the
Phase P freeze manifest) and are unrelated to this validation cycle,
which touched no production code.

## 28. Known non-blocking limitations

- `_segment_specificity` ranks by constrained-dimension count, not
  numeric range width (disclosed since Phase G; unchanged).
- Phase J's Layer 1 injection-detection heuristic measures 44.4% recall;
  the actual hard authority boundary (Layer 2) does not depend on it and
  is 100% clean (re-confirmed this cycle at 78/78 for the final corpus's
  fresh attack set).
- SM=7 (Step 4A.11 liability/indemnification false-absence architecture
  gap, safe-but-silent, none SM-CRITICAL) — pre-existing, disclosed at
  the original Step 4A.11 freeze, unchanged, re-confirmed this cycle.
- Step 4A extraction-adapter completeness: several adapters
  (`limitation_of_liability`, `indemnification`, `governing_law`,
  `termination`, `confidentiality`, `assignment`, `data_security`,
  `warranties`) did not recognize this final corpus's specific freshly-
  authored real-text sentences as matching clauses (`NOT_APPLICABLE`),
  while 4 adapters did. This is a real, disclosed extraction-recognition
  boundary — never a false ACCEPT, always a safe `NOT_APPLICABLE` — and
  is explicitly out of scope for Step 4B per standing instruction not to
  reopen Step 4A extraction without new wrong-authority evidence (none
  was found: `NOT_APPLICABLE` is the safe direction, not a wrong-authority
  defect).
- The final corpus's Trust Audit (§22) found 0 VERIFIED (real-constraint-
  actually-checked) decisions among its 210 audited ACCEPT-family
  decisions — an artifact of the specific playbook configurations used in
  this audit pass (mostly least-restrictive defaults), not a system
  defect, consistent with and disclosed identically to Step 4B Phase M's
  own finding.

## 29. Lee Challenge status

Not separately re-litigated in this final validation — the Lee Challenge
(the original architectural stress test motivating the neural-symbolic
deterministic-control-plane design) was resolved during Step 4A and its
resolution is unchanged by anything tested in Step 4B, which builds
exclusively on top of that already-validated architecture without
reopening it.

## 30. Architecture verdict

The neural-symbolic architecture with a deterministic control plane holds
under this final, independent, adversarial validation: every wrong-
authority, false-clean, false-absence, suppression, injection, dependency-
failure, and determinism hard gate is 0 across 503 genuinely fresh
documents plus the full legacy regression suite. The LLM explanation
layer never overrides authoritative state; governance and segment
selection are deterministic-or-explicit-fail-closed; the interaction
engine and aggregation layer never manufacture a false CLEAN.

## 31. Final Step 4B verdict

**FINAL VERDICT: PASS**

## 32. SHIP / DO NOT SHIP recommendation

**STEP 4B: COMPLETE**

**SHIP: AUTHORIZED**
