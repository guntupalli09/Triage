# Step 4B Phase B — Deduplication/Suppression Read-Only Inventory

Read-only trace of every code path that deduplicates, merges, groups,
filters, sorts, or truncates findings, performed before modifying any
production file.

## Findings pipeline stages inspected

1. **`rules_engine.RuleEngine.analyze()`** (`rules_engine.py:4622`) — own
   documented internal contract (its docstring, step 4): "Deduplicate
   findings by `(rule_id, clause_number)`" — deliberately preserves two
   occurrences of the same rule at two different clause locations.
   Confirmed by direct docstring read, not assumed. Proximity-match
   dedup (`rules_engine.py:981-988`) also keys on more than the bare
   rule_id (a `key` tuple, not inspected further since it precedes and is
   already subsumed by the step-4 contract above). **No suppression risk
   found here — this stage already gets the distinction right.**

2. **`policy_enforcement.apply_active_policies`** (`policy_enforcement.py:536`) —
   one `PolicyDecision`, therefore at most one `_finding_from_decision`
   entry, per clause type per review, by construction (an adapter never
   emits two decisions for one review). No dedup logic present or needed.

3. **`interaction_enforcement.apply_interaction_rules`** (`interaction_enforcement.py:81`) —
   `interaction_engine_core.evaluate()`'s own contract guarantees "one
   `InteractionDecision` per rule" (never omitted, never duplicated) — see
   its docstring. No dedup logic present or needed.

4. **`main.build_enhanced_issues`** (`main.py:397`) — **the one real
   suppression point found.** Merges all three finding sources
   (legacy rule findings + injected `policy_decision` findings + injected
   `interaction_decision` findings) into one display list, consumed by
   `results.html`, `review.html`, and `shared_report.html`'s `top_issues`.
   Originally deduplicated on `rule_id` alone (`seen_rule_ids` set) — see
   defect below. Also does a final `all_issues.sort(...)` by
   `(severity_order, title)` — a stable, non-lossy sort (confirmed by
   reading the full function body; no slicing/truncation after the sort).

5. **`review_queue.build_review_queue`** (`review_queue.py:140`) —
   inventoried directly: the only list-order operations are two
   `.sort(key=...)` calls (`review_queue.py:173-174`) on index lists,
   stable and index-preserving; no `del`, no `.pop()`, no `[:N]`
   truncation, no `seen_*`/dedup set anywhere in the file (confirmed via
   grep across the whole module). **Already correct — this was also
   independently confirmed in Step 4B Phase 0.**

6. **`triagebench*/`, `experiments/`** — offline eval harnesses, not part
   of the live findings-display path; out of scope (same reasoning as the
   Phase-0/consumer-map exclusion of these directories elsewhere).

## Defect found and fixed

`main.build_enhanced_issues`'s dedup key was `rule_id` alone. Reproduced
directly (two legacy findings, same `rule_id`, different `clause_number`/
`start_index`/`end_index` — i.e. the SAME pattern-match rule firing on two
genuinely separate provisions in one document, which
`rules_engine.analyze()` itself deliberately preserves per its own
documented `(rule_id, clause_number)` contract): `build_enhanced_issues`
silently collapsed the two distinct findings down to one — a real,
reproducible **materially distinct finding suppression** defect, directly
contradicting the upstream engine's own already-correct distinction.

**Fix** (`main.py`): dedup key changed to
`(rule_id, start_index, end_index, clause_number)`. Verified directly:
two genuinely distinct occurrences of the same `rule_id` now both survive;
an exact duplicate entry (same rule_id AND same location) still correctly
collapses to one. `policy_decision`/`interaction_decision` synthetic
findings are unaffected — each is already unique per `rule_id` by
construction (at most one `PolicyDecision`/`InteractionDecision` per
clause_type/interaction_id per review), so the added location fields do
not change their dedup outcome at all.

Full benchmark methodology, PRE/POST results, and regression: see
`artifacts/step4b/phaseB_dedup_report.md`.
