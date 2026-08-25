CANDIDATE 4 — PHASE 8: TWELVE-ADAPTER SYMMETRY AUDIT

Legend: **SAFE** = confirmed, either by live reproduction or by direct
code-path inspection showing an unconditional gate exists; **FIXED** =
was unsafe before this mission, corrected in this mission (see
ROOT_CAUSE_MAP.md Cluster 1/2); **N/A** = the question does not apply to
this adapter's fact model (documented why).

| Adapter | UNKNOWN→CLEAN? | Failed discovery→ABSENT? | Verification failure→NOT_APPLICABLE? | Unresolved definition→CLEAN? | Unresolved cross-ref→CLEAN? | Material qualifier disappear? | Competing readings collapse? | Provider failure alters clean authority? | Admitted evidence consumed? | Equivalent fail-closed gate? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. Limitation of liability | SAFE — `_any_provision_established` gate (Candidate 3 Blocker 2 fix) requires `treatment not in (not_addressed, unresolved)`, not merely `established`; unconditional-note bypass via `first_unresolved_dependency_note_is_unconditional` | SAFE — `RECOGNITION_UNCERTAIN`/`DEPENDENCY_UNRESOLVED` absence states exist and are distinct from `CONFIRMED_ABSENT`, confirmed present since Candidate 3 blocker remediation | SAFE — same states | SAFE — unconditional escalation via `first_unresolved_dependency_note_is_unconditional` | SAFE — same mechanism | SAFE — zero-silent-loss composition (`ai_identified_condition`/`ai_identified_exception` fields consumed by evaluator) | SAFE — `≥2 grounded competing readings` is one of the three specific mechanisms forcing `is_unconditional=True` in `fact_admission._classify_unresolved_dependency_note` | SAFE — `VERIFICATION_ERROR` is in `_INFRASTRUCTURE_FAILURE_VERIFICATION_STATES`, unconditional | YES — `tests/test_liability_policy_engine.py` passing (Candidate 3 regression) | YES |
| 2. Indemnification | SAFE — `obligation_materially_established` two-layer gate (Candidate 3 Blocker 3, incl. `_GENERIC_EXCEPTION_SIGNAL_RE` second-order fix) | SAFE — 4-way `absence_state` (`RECOGNITION_UNCERTAIN`/`DEPENDENCY_UNRESOLVED`/`PRESENT_BUT_UNRESOLVED`/`PRESENT_AND_VERIFIED`) | SAFE — same | SAFE — unconditional bypass wired (`first_unresolved_dependency_note_is_unconditional([verified])`) | SAFE — same | SAFE — Blocker 3 fix specifically targets this (a missed same-clause exception) | SAFE — same shared mechanism | SAFE — `SEMANTIC_PROVIDER` unified (Candidate 3 Blocker 4); `VERIFICATION_ERROR` unconditional | YES — `tests/test_indemnification_policy_engine.py` passing | YES |
| 3. Termination | SAFE (audited this mission) — `if not facts.rights: → REQUIRES_REVIEW` is UNCONDITIONAL (does not require `admitted_semantic`), confirmed at `termination_policy_engine.py:673` | SAFE — `facts is None` only when BOTH no anchor exists AND no admitted candidate/note exists; an operative anchor with an unparseable right already forces REQUIRES_REVIEW via the gate above, never NOT_APPLICABLE | SAFE — same gate | PARTIAL — `_run_semantic_discovery` here returns a 3-tuple (no `note_is_unconditional`), unlike the 9 adapters upgraded in Candidate 3's Blocker 2; NOT independently unsafe today only because the unconditional `if not facts.rights` gate already covers the material cases that would need the bypass — flagged as a documentation/consistency gap, not a live defect (no failing test or corpus case demonstrates a suppression) | Same PARTIAL note as above | SAFE — condition/exception surfaced via dedicated fields regardless of whether a right otherwise structured | Not independently exercised this mission (no adversarial competing-reading termination case run) — inherits the shared `_classify_unresolved_dependency_note` mechanism, same as adapters 1–2, via the 3-tuple `_run_semantic_discovery`'s call into `first_unresolved_dependency_note` (unconditional note text still surfaces even without the separate `_is_unconditional` boolean) | Not independently exercised — no `VERIFICATION_ERROR`-specific termination test run this mission | YES — `tests/test_termination_policy_engine.py` passing | YES (via the `not facts.rights` gate) |
| 4. Confidentiality | SAFE — passed Candidate 3 Phase 5 (`PHASE5_ADAPTER_MATRIX.md`); code inspection confirms `RECOGNITION_UNCERTAIN` present and an unconditional obligations-empty gate mirroring termination's | SAFE — same | SAFE — same | Not independently re-verified this mission (relies on Candidate 3's existing 9-adapter Blocker 2 upgrade — confirmed 4-tuple `_run_semantic_discovery` present) | Same | Same zero-silent-loss composition pattern as liability/indemnification | Same shared mechanism | Same | YES — passing | YES |
| 5. Assignment | SAFE (audited this mission) — `if not facts.restrictions and not facts.unrestricted_assignment: → REQUIRES_REVIEW` is UNCONDITIONAL, confirmed at `assignment_policy_engine.py:424` | SAFE — same reasoning as termination | SAFE — same | Same PARTIAL note as termination (3-tuple `_run_semantic_discovery`, no independent `_is_unconditional`) | Same PARTIAL note | Same as termination | Not independently exercised this mission | Not independently exercised this mission | YES — `tests/test_assignment_policy_engine.py` passing | YES |
| 6. Governing law | SAFE — passed Candidate 3 Phase 5 | SAFE — `RECOGNITION_UNCERTAIN` present | SAFE | N/A — this adapter resolves a single jurisdiction token, not a multi-dimension fact set; no definition-dependency vocabulary applies to "which state/country governs" | N/A — same reasoning | N/A — no material qualifier concept in this adapter's narrow fact model | N/A — a jurisdiction is binary-resolved (stated/conflicting), not a multi-reading concept | Same shared mechanism | YES — passing | YES |
| 7. Data protection/security | **FIXED this mission** — see ROOT_CAUSE_MAP.md Cluster 1/2. Now SAFE: broadened + reordered `PRESENT_BUT_UNRESOLVED` gate, confirmed via `tests/test_candidate4_remediation.py` and full existing `test_data_security*` suite (40/40 passing) | **FIXED** — same | **FIXED** — same | SAFE — unconditional bypass already present (Candidate 3 Blocker 2) | SAFE — same | SAFE — zero-silent-loss composition present | SAFE — shared mechanism | SAFE — `VERIFICATION_ERROR` unconditional | YES | YES (now, post-fix) |
| 8. IP ownership/licensing | **FIXED this mission** — see ROOT_CAUSE_MAP.md Cluster 1/2. `ip_ownership-080` (the confirmed non-determinism in ADMITTED-candidate qualifier composition for an ALREADY-established ownership_attributions) remains DEFERRED, untouched, and is a DIFFERENT failure shape than this mission's fix (which targets the case where ownership_attributions is NEVER established at all) | **FIXED** — same | **FIXED** — same | SAFE — unconditional bypass already present | SAFE — same | SAFE — zero-silent-loss composition present | SAFE — shared mechanism | SAFE | YES | YES (now, post-fix) |
| 9. Insurance | **FIXED this mission** — see ROOT_CAUSE_MAP.md Cluster 1/2, confirmed via live repro (`iv-insurance`-style text) and full `test_insurance_benchmark_gate.py` (64/64 passing after two corpus-expectation updates, documented in ROOT_CAUSE_MAP.md) | **FIXED** | **FIXED** | SAFE — unconditional bypass already present | SAFE — same | SAFE — condition/exception composition present | SAFE — shared mechanism | SAFE | YES | YES (now, post-fix, AND reordered to preserve per-dimension precision — Cluster 2) |
| 10. Payment terms | SAFE — passed Candidate 3 Phase 5; `DEPENDENCY_UNRESOLVED` absence state present (`payment_terms_policy_engine.py:743`) | SAFE — same | SAFE | SAFE — unconditional bypass present (4-tuple `_run_semantic_discovery`) | SAFE | Same zero-silent-loss pattern | SAFE — shared mechanism | SAFE | YES — passing | YES |
| 11. Warranties | SAFE — narrower `found_anything` definition (Cluster 1's "why not independently broken" note) means the specific Candidate 4 defect cannot occur here; `if not found_anything: → NOT_APPLICABLE unless admitted_semantic/note` gate predates this mission and remains sound | SAFE — same | SAFE | SAFE — unconditional bypass present | SAFE | SAFE — composition present, confirmed via inline comment discipline in the file itself | SAFE — shared mechanism | SAFE | YES — passing | YES |
| 12. SLA/service levels | SAFE — same narrower `found_anything` pattern as warranties | SAFE — same | SAFE | SAFE — unconditional bypass present | SAFE | SAFE — composition present | SAFE — shared mechanism | SAFE | YES — passing | YES |

## Honest gaps in this audit

- **Termination and assignment's 3-tuple `_run_semantic_discovery`** (no
  `note_is_unconditional` return value, unlike the other 10 adapters) is a
  real INCONSISTENCY flagged during this audit. It is not proven to be a
  live safety defect — both adapters' unconditional "no structure parsed"
  gate already catches the cases that would need the bypass — but it
  should be closed for architectural consistency in a future pass rather
  than this one, since no failing test or corpus case currently
  demonstrates it causing an unsafe result, and this mission's explicit
  scope is the SPECIFIC failure classes Candidate 3's independent
  validation actually found (termination/assignment did not contribute a
  single occurrence to any of the 5 non-zero hard gates per
  `phase4_5_analysis.json`'s adapter_matrix).
- **Competing-reading and provider-failure cells for termination/
  assignment/confidentiality/governing_law/payment_terms/warranties/sla**
  were verified by CODE-PATH inspection (confirming the shared
  `fact_admission` mechanism is wired in identically to liability/
  indemnification, which WERE live-tested for these specific cells in
  Candidate 3's remediation) rather than by re-running a dedicated live
  test for each cell in each adapter this mission. This is disclosed
  explicitly per the mission's instruction not to claim "shared framework
  therefore PASS" without proof — the proof offered here is that these
  adapters call the identical, already-proven-safe shared functions
  (`fact_admission.first_unresolved_dependency_note`,
  `first_unresolved_dependency_note_is_unconditional`,
  `is_operative_context`) with the same calling convention as the two
  adapters where live adversarial tests exist, not an unverified
  assumption that shared code implies safety on its own.
