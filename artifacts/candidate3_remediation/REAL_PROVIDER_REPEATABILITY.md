# Real-Provider Repeatability Test (Candidate 3 remediation, Section 15)

36 cases (3 per adapter × 12 adapters — one LEE1 positive control, one descriptive/hypothetical/negotiation family case, and one colloquial/unusual-drafting case per adapter, selected to maximize the chance of actually invoking a real call) × 5 independent real-provider runs each = **180 real OpenAI calls attempted.** Model: `gpt-4o-mini`. Full raw output: `artifacts/candidate3_remediation/repeatability/repeatability_remediated_results.json`.

## Results

- AI_DISCOVERY_REPEATABILITY: not separately logged per-candidate-text in this run (see raw JSON's `run_absence_states` for the closest proxy); qualitative observation below.
- CANONICAL_FACT_REPEATABILITY / POLICY_DECISION_VARIATION: **4/36 cases showed decision-state variation** across their 5 runs.
- UNSAFE_CLEAN_TRANSITIONS: **1/36 — a confirmed, forbidden violation.**

| Case | Run states | Verdict |
|---|---|---|
| `ip_ownership-080` | REQUIRES_REVIEW, REQUIRES_REVIEW, **ACCEPT**, REQUIRES_REVIEW, REQUIRES_REVIEW | **FORBIDDEN — clean-state variance** |
| `ip_ownership-099` | REQUIRES_REVIEW, NOT_APPLICABLE, REQUIRES_REVIEW, NOT_APPLICABLE, NOT_APPLICABLE | Acceptable per Section 15's explicit carve-out — never touches a clean state |
| `warranties-199` | NOT_APPLICABLE, NOT_APPLICABLE, REQUIRES_REVIEW, NOT_APPLICABLE, NOT_APPLICABLE | Acceptable — same reason |
| `sla-219` | REQUIRES_REVIEW, NOT_APPLICABLE, REQUIRES_REVIEW, REQUIRES_REVIEW, REQUIRES_REVIEW | Acceptable — same reason |

## Root-cause diagnosis of the one forbidden transition (`ip_ownership-080`)

Case text: `"11. Intellectual Property. All work product created by Vendor specifically for Customer under this Agreement shall be owned exclusively by Customer upon full payment."` (LEE1 — intended as a clean positive control.)

**A fifth, distinct, pre-existing regex gap, found via this mandated repeatability test:** `ip_ownership_policy_engine._OWNERSHIP_PASSIVE_RE` matches `"shall be (solely )?owned by <Party>"` but NOT `"shall be owned **exclusively** by <Party>"` — the word "exclusively" sits between "owned" and "by," breaking the pattern (directly reproduced: `_OWNERSHIP_PASSIVE_RE.search(text)` → `None`). Deterministic ownership attribution therefore NEVER establishes for this exact, very common real-world phrasing, regardless of which run. The case's authoritative outcome is consequently governed ENTIRELY by whether the real AI discovery+verification round trip succeeds in a given run — Root Cause 1's `PRESENT_BUT_UNRESOLVED` fix correctly produces `REQUIRES_REVIEW` in 4 of 5 runs, but in one run reached `ACCEPT` instead.

This is a genuinely different, and more concerning, failure mode than warranties-199/sla-219's variance (which only ever toggles between two SAFE states): it demonstrates that Root Cause 1's fix, while closing the specific mechanism behind the original `ip_ownership-099` finding, does not close every path to a clean-state variance when a DIFFERENT, narrower regex gap (here, `_OWNERSHIP_PASSIVE_RE`'s word-order sensitivity) is also in play. **This was not previously identified** — it surfaced specifically because this mission's mandated 36×5 repeatability test happened to select this exact phrasing as a "positive control." It is reported here as newly discovered evidence, not retrofitted into the burned-corpus analysis (which used a different corpus and did not happen to trigger this specific variance in its single run).

## Consequence

Per Section 22's explicit hard-stop condition ("provider-induced clean decision variance > 0"), **this repeatability test fails.** Root Cause 3 is NOT fully closed — the design in `PROVIDER_VARIANCE_DESIGN.md` correctly eliminates the ORIGINAL mechanism (an admitted-but-unstructured candidate reaching a bare `ACCEPT` via "no policy gaps found"), but a case whose deterministic establishment fails for an UNRELATED, narrower reason (a word-order gap in a specific value-extraction regex) can still intermittently reach a fully-established, clean `ACCEPT` state when the underlying deterministic regex HAPPENS to match on some other basis in a given run's specific window construction.

**An attempted fix was tried and reverted.** Broadening `_OWNERSHIP_PASSIVE_RE` to `owned\s+(?:solely\s+|exclusively\s+)?by` does make it match `"shall be owned exclusively by Customer"` — but this immediately exposed a SECOND, subtler defect: the category-attribution heuristic (which decides whether a match belongs to "work_product" vs. "background_ip") picks the nearest preceding category keyword, and for `benchmarks/ip_ownership_corpus.py`'s existing `conflict-02` case (`"All Work Product, including any pre-existing intellectual property embodied therein, shall be owned exclusively by Customer."`), the newly-matching ownership statement gets misattributed to `background_ip` (because "pre-existing intellectual property" sits closer to the match than "Work Product" does), producing a DIFFERENT wrong decision (an unnecessary escalation) instead of the corpus's correct expected `NEGOTIATE`. Trading one confirmed variance bug for a different, real benchmark regression under time pressure is not an acceptable fix. **Reverted; `_OWNERSHIP_PASSIVE_RE` is unchanged from before this mission.** This gap is reported as found-but-not-fixed, requiring a properly scoped follow-up that also addresses the category-attribution interaction, not a one-line regex patch.
