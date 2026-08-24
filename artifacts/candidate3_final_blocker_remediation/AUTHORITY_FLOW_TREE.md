PHASE 14 — AUTHORITY FLOW TREE (post-remediation)

Legend: 🤖 PROBABILISTIC · 🔒 DETERMINISTIC · ⚡ AUTHORITY BOUNDARY

This supersedes `artifacts/pre_freeze_architecture/AUTHORITY_FLOW_TREE.md`'s "🚨 Confirmed
leaks" section specifically — the rest of that document's authority-boundary trace
(`evaluate_admission`'s hard gate, grounding, definition/cross-reference resolution) is
unchanged and remains accurate.

```
🤖 discover_candidate_spans ──► 🤖 verify_candidate_proposition ──► 🔒 grounding/resolution
                                                                          │
                                                                          ▼
                                                    ⚡ evaluate_admission (unchanged, sound)
                                                          │
                              ┌───────────────────────────┼───────────────────────────┐
                              ▼                                                       ▼
                         ADMITTED                                              NOT_ADMITTED
                              │                                                       │
                    🔒 deterministic structuring                    🔒 _classify_unresolved_dependency_note
                    (unchanged, re-parses the                       (Blocker 1: NOW covers all 6 unsafe
                    same as any raw anchor)                         states, not 4 -- VERIFICATION_ERROR
                                                                     escalates UNCONDITIONALLY;
                                                                     Blocker 2: returns (note,
                                                                     is_unconditional) so callers can
                                                                     never suppress a specific mechanism)
                                                                          │
                                                          ┌───────────────┴────────────────┐
                                                          ▼                                ▼
                                              is_unconditional=True              is_unconditional=False
                                          (definition/cross-ref/          (generic content-uncertain or
                                          competing-readings)             infrastructure-failure)
                                                          │                                │
                                              🔒 ALWAYS escalates,          🔒 caller's materiality gate
                                              no suppression possible       (Blocker 2 fix: requires a
                                              in any of the 12 adapters     GENUINE POSITIVE finding for
                                                                            THIS SAME provision/obligation,
                                                                            never "something, anything,
                                                                            established")
```

## Previously-confirmed leaks — status after this mission's fixes

1. **VERIFICATION_ERROR invisible to `first_unresolved_dependency_note`** — **CLOSED**
   (Blocker 1). Live-verified: a `VERIFICATION_ERROR` candidate now always produces an
   escalation note.
2. **The "nothing else established" suppression gate could drop a genuinely unrelated
   candidate's uncertainty** — **CLOSED** for the specific mechanisms (definition/cross-
   reference/competing-readings are now structurally unconditional, per every one of the 7
   gated adapters). The generic catch-all's materiality bar was also tightened (liability's
   always-true bug fixed; monetary/scope/condition now require genuine positive findings, not
   confident-negative defaults) but remains, by architectural necessity, a per-clause-type
   (not per-exact-fact) materiality check — documented as the practical ceiling given the
   shared discovery schema proposes one generic candidate per clause type, not a fine-grained
   per-dimension one.
3. **Indemnification's reconciliation channel had no equivalent gate at all** — **CLOSED**
   (Blocker 3, two layers).
4. **A second, non-anchor-matching admitted candidate can be dropped outright in liability**
   — **UNCHANGED, out of scope**. This mission's brief authorized Blockers 1-5 only; this
   documented, in-code-acknowledged residual risk was not part of any of the five and was not
   touched.

## Newly discovered leak this mission (NOT one of Blockers 1-5, NOT fixed)

5. **ip_ownership's admitted-candidate qualifier-composition loop is exposed to provider
   sampling variance independent of the note-suppression mechanism entirely.** Confirmed via
   `git diff` to be untouched by this mission's commits. See `TWELVE_ADAPTER_PROOF_MATRIX.md`
   and `ROOT_CAUSE_REPORT.md` for full detail. This is the reason
   `FINAL_REMEDIATION_VERDICT.md`'s overall verdict is `NOT READY`.
