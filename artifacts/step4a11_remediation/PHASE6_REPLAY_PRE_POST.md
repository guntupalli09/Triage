# Step 4A.11 Remediation — Phase 6: Locked 393-Case Corpus Replay (regression evidence, not independent validation)

| Metric | PRE (pre-remediation) | POST (post-remediation) |
|---|---|---|
| CA | 196 | 199 |
| CR | 52 | 52 |
| FE | 139 | 142 |
| **WC (wrong_clean)** | **6** | **0** |
| SM | 7 | 7 (unchanged — separate, disclosed, out-of-scope architecture gaps) |
| Clean-Verified Recall | 57.5% | 58.4% (slight improvement, not a regression) |
| Tier 1 Clean-Verified Recall | 69.1% | 69.1% (unchanged) |
| Tier 3 Clean-Verified Recall | 56.3% | 56.6%* |
| semantic_authority_diffs | 0 | 0 |
| determinism mismatches (5x) | 0 | 0 |

*Tier 3 total grew from 87→114 cases denominator note: figures recomputed
directly from this replay's own output, not carried over arithmetically.

**The discovered role-boundary wrong-clean defect is eliminated (WC 6→0).**
Both example cases from the original finding now resolve safely:
`fin-ind-t3-27` (mixed-case heading + operative sentence) now correctly
establishes `Millbrook Staffing Partners -> Ironvale Manufacturing Co`
(previously corrupted). `fin-ind-t3-26` (fully ALL-CAPS operative clause)
now correctly returns NO obligation at all rather than a corrupted one —
a safe non-establishment (FE), not a wrong-clean decision, consistent with
the fail-closed material-fact-ownership invariant this remediation added.

No material regression to Clean-Verified Recall, false symmetry, false
absence, ownership, conditional applicability, cross-reference resolution,
or the authority boundary. SM (7, unchanged) reflects the two
already-disclosed, explicitly out-of-scope findings from the original
final report (liability's missing broad discovery signal; indemnification
AF9 phrasing this remediation was never asked to fix) — reproducing
identically confirms this remediation did not silently touch that
unrelated mechanism.

Per protocol: ground truth in the locked corpus was NOT modified for this
replay.
