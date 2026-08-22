# Step 4B — `overall_risk` Consumer Map and Enforcement-Mode Contract

Read-only trace, full repository. Grep basis: `overall_risk` (36 files),
narrowed here to production (`main.py`, `models.py`, `templates/*.html`,
`policy_enforcement.py`, `evaluator.py`, `playbook_workbench.py`). Files
under `experiments/`, `triagebench*/`, and `tests/` are offline
eval/regression harnesses, not live consumers, and are excluded from the
map (they read `overall_risk` from their own recorded fixtures, not from a
running app).

## 1. Persistence

- `models.py:87` — `Contract.overall_risk = Column(String(20), nullable=True)`.
  Legacy pattern-match risk (`rules_engine.analyze()`), computed once at
  upload time, never recomputed.
- `models.py:147` — `Contract.policy_decisions_json = Column(EncryptedJSON, ...)`.
- `models.py:176` — `Contract.interaction_decisions_json = Column(EncryptedJSON, ...)`.

**Architectural constraint confirmed by code read**: `policy_decisions_json`
and `interaction_decisions_json` are `EncryptedJSON` (`encryption.py:219`) —
stored as an encrypted TEXT blob, decrypted only at the ORM row level after
fetch. **SQL cannot filter, aggregate, or index on their content** — no
`WHERE policy_decisions_json @> ...`, no `GROUP BY` on a key inside them,
is possible at the database layer, encrypted or not (even unencrypted JSON
columns in this schema are TEXT-backed per SQLite/Postgres portability
notes in `encryption.py`). Any document-level aggregate that reads these
two fields **must** be computed in Python after the ORM has decrypted the
row — this is not a design choice, it is forced by the existing encryption
architecture, and is the primary reason no DB-level `WHERE`/`COUNT`
aggregation is implemented in this increment (see §4).

## 2. Consumers of `overall_risk` (grouped by kind)

### A. Attention/gating surfaces (in scope for this increment)

| Surface | Location | Behavior today |
|---|---|---|
| Dashboard high-risk count | `main.py:1202-1204` | `Contract.overall_risk == "high"` DB filter, `COUNT`. |
| Dashboard recent-contracts row badge | `main.py:1212-1215` + `templates/dashboard.html:82-84` | Per-row color keyed on `c.overall_risk`. |
| `/history` risk filter | `main.py:1231` | `Contract.overall_risk == risk` DB filter (`risk` query param: `high`/`medium`/`low`). |
| `/history` listing row badge | `main.py:1236-1242` + `templates/history.html:87-89` | Per-row color keyed on `contract.overall_risk`. |

### B. Single-document presentation surfaces (per-document detail — already show policy/interaction findings as individual line items, see §3; headline badge still legacy-only)

| Surface | Location |
|---|---|
| Contract detail page | `main.py:1699-1769` (`results.html`) — `overall_risk` badge at `templates/results.html:179-185,869`. |
| Review workspace | `main.py:2242-2280` (`review.html`) — badge at `templates/review.html:291`; this route is otherwise the MOST policy-aware surface in the app (`review_queue.build_review_queue`, `policy_enforcement.enforcement_disclosure()`), and its exception-queue view already correctly separates passed/not-applicable/never-evaluated/evaluation-error at the per-finding level (confirmed in Step 4B Phase 0). |
| Public share link | `main.py:2615-2642` (`shared_report.html`) — badge at `templates/shared_report.html:166-176`. |
| PDF export | `main.py:1835-1867` (`_build_pdf_bytes`), used by single-contract and `/batch/{id}/download-all` — badge at `templates/pdf_report.html:400-439`. |

### C. Aggregate/business surfaces (out of scope for this increment — see §5)

| Surface | Location |
|---|---|
| Batch results page + per-batch high/medium/low stats | `main.py:1587-1601` (`batch_results.html:93-95`). |
| Admin/internal analytics dashboard (risk distribution, recent-contracts risk column) | `main.py:3606-3612, 3663-3669` (`admin_dashboard.html`) — operator business-analytics surface, not a lawyer-facing attention queue. |
| LLM explanation prompt anchor | `evaluator.py:112,130,367` — `overall_risk` is fed into the LLM prompt as "Deterministic Overall Risk (already computed)" and the LLM's own output `overall_risk` key is force-overwritten back to the deterministic value (`evaluator.py:328`) regardless of what the model said — this is the semantic layer correctly NEVER being allowed to originate or override the authoritative signal, exactly per the non-negotiable authority model. No change needed or made here. |
| Playbook template scoring | `playbook_workbench.py:607`, `main.py:2790,2902` — scores an example/template document while building a Playbook, not a live contract review; no `policy_decisions_json`/`interaction_decisions_json` exists in this flow at all. Out of scope. |
| Demo/anonymous preview (`/demo`, `/demo/start`, token-based unauthenticated `results.html` render at `main.py:3523-3539`) | No playbook, no `apply_policies_for_review` call — `policy_decisions_json`/`interaction_decisions_json` are never populated for these Contract rows. Structurally cannot exhibit the false-clean gap; out of scope. |

### D. Findings-list surfaces (already correct — noted for completeness, not touched)

`findings_json` is passed by reference into `apply_policies_for_review`
(`main.py:1392-1394`) and mutated in place by `apply_active_policies`/
`interaction_enforcement.apply_interaction_rules` (cutover mode) BEFORE
being persisted (`main.py:1401`) — so every synthetic policy/interaction
finding already appears as an individual line item in `top_issues`/
`all_issues` on `results.html`, `review.html`, and `shared_report.html`.
**The false-clean gap is exclusively in the aggregate/headline signal
(§A), never in the per-finding detail a user sees once they open a
contract.** This was confirmed by tracing the exact object-identity
mutation path, not assumed.

## 3. Enforcement-mode contract (explicit truth table)

Traced directly against `policy_enforcement.py:734-792`
(`apply_policies_for_review`) and `get_enforcement_mode()`
(`policy_enforcement.py:140-153`, `DEFAULT_MODE` = `"shadow"`).

| | legacy | shadow | cutover |
|---|---|---|---|
| Policy adapters executed? | No (legacy `apply_liability_policy` only — single clause type, not the 12-adapter layer) | No (same as legacy) | Yes — all 12 adapters via `apply_active_policies` |
| Interaction Engine executed? | No | No (`interaction_decisions` is unconditionally `None`) | Yes — `interaction_enforcement.apply_interaction_rules` |
| Document aggregation (`aggregate_document_state`) executable? | Degenerate — only ever sees the single legacy liability decision, `interaction_decisions=None` | Same as legacy | Full — all 12 adapters + 7 interaction rules feed it |
| Legacy `overall_risk` preserved? | Yes, unconditionally, in all three modes — `rule_engine.analyze()` runs before `apply_policies_for_review` regardless of mode | Yes | Yes |
| Authoritative policy state available (`is_policy_authoritative()`)? | No | No — this is the critical, already-load-bearing distinction: shadow is **not** "policy evaluated but not shown," it is **"policy layer not evaluated at all, beyond one diagnostic-only liability comparison logged to AuditLog."** | Yes |
| Dashboard attention-state source (today, before this increment) | `overall_risk` only | `overall_risk` only | `overall_risk` only (bug — should be aggregation-aware) |
| `/history` filtering source (today) | `overall_risk` only | `overall_risk` only | `overall_risk` only (same bug) |
| User-visible policy findings available? | Legacy liability finding only (folded into normal findings, as it always was pre-Step-4B) | Same as legacy | All 12 adapters' findings + interaction findings, already correctly appended to `findings_json` (§2.D) |

### Answers to the seven required questions

1. **Does legacy execute the policy layer?** No — only the single legacy
   liability engine (`apply_liability_policy`), which predates the 12-
   adapter Step 4A architecture and is not "the policy layer" in the
   Step 4B sense.
2. **Does shadow execute it?** No. It runs `run_shadow_comparison` — a
   liability-only diagnostic comparison written to `AuditLog`, wrapped in
   `except Exception: pass` so it can never affect the visible result, and
   never surfaced to any UI, dashboard, or report. This is not a shadow
   evaluation of the 12-adapter policy layer or the Interaction Engine —
   neither is invoked in shadow mode at all.
3. **Does cutover execute it?** Yes — the only mode that runs
   `apply_active_policies` (12 adapters) and `apply_interaction_rules`.
4. **Which mode currently supplies user-visible review status?** The
   legacy path (`apply_liability_policy`) in legacy and shadow; the full
   12-adapter + interaction result in cutover. All three modes always
   supply `overall_risk` from `rule_engine.analyze()`, unconditionally.
5. **Which mode is safe for production integration [of the aggregation
   function]?** All three, by construction — `aggregate_document_state`
   degrades correctly and provably (confirmed by the `shadow-mode`/
   `legacy-mode` benchmark family, 10/10 correct) when
   `interaction_decisions` is `None` and `policy_decisions` holds only the
   legacy liability decision. Wiring it in does not require or imply a
   mode change.
6. **Is "shadow" genuinely shadow evaluation, or is it effectively
   policy-disabled?** **Effectively policy-disabled**, as far as the
   12-adapter layer and Interaction Engine are concerned. It IS a genuine
   shadow evaluation of the single legacy liability clause only (that
   diagnostic comparison is real and does run) — but the name "shadow" as
   applied to the Step 4B system (multi-policy + interactions) is
   misleading if read as "the richer system is running invisibly." It is
   not running at all in that mode. This must be stated plainly rather
   than implied to provide coverage it does not.
7. **Are there compatibility assumptions/tests around the current
   default?** Yes — `policy_enforcement.py`'s own module docstring and the
   `verify_migration_coverage_or_fail_closed` function describe cutover as
   requiring an explicit, human-authorized, evidence-backed migration
   (referenced in Step 4A.11/Phase-4.1 material as "production shadow
   evidence" gating a cutover decision). `DEFAULT_MODE = "shadow"` is a
   deliberate, documented rollback-safe default, not an oversight. This
   increment does not touch it.

**No change to `POLICY_ENFORCEMENT_MODE`'s default is made or recommended
here.**

## 4. Persistence decision (required before wiring)

**No schema migration is performed in this increment.** `document_state`
is computed **at read time**, in Python, inside each of the two in-scope
route handlers (`/dashboard`, `/history`), directly from already-persisted
`Contract.overall_risk` / `.policy_decisions_json` / `.interaction_decisions_json`
via `document_aggregation.aggregate_document_state()`. This is possible
without persistence because:

- The three inputs are already fully persisted per contract at review
  time (`main.py:1400,1411,1413`) — nothing new needs to be computed or
  stored to call the function.
- `aggregate_document_state` is a pure, cheap function (dict lookups over
  already-decrypted, already-in-memory JSON — no re-parsing of
  `contract_text`, no re-running any adapter).
- The encryption constraint in §1 means a persisted, SQL-filterable
  "attention" column would still not allow a `WHERE`-clause optimization
  over the JSON *content* even if it existed — the JSON fields it reads
  are encrypted regardless. A persisted boolean/enum summary column would
  only remove the per-request Python recomputation cost, which — at the
  scale of one user's own `/dashboard` and `/history` views (already
  bounded by `Contract.user_id ==`, the same scope the existing `total`/
  `high_count` queries use) — is not a demonstrated performance problem
  and is not attempted here. If this bounded increment's approach is
  later found to be too slow at scale, that is a proposed, separate,
  explicitly-authorized schema change — not something to add speculatively
  now.

`Contract.overall_risk` itself is **not** redefined, recomputed, or
removed anywhere in this increment — see §5.

## 5. Scope decision for this increment

**In scope** (§2.A — the two surfaces the task names as minimum required,
plus their row-level listing representation, since a count with no
matching visible rows would itself be a new inconsistency):

- `/dashboard` — high-risk/attention count, recent-contracts row badges.
- `/history` — risk filter (adds a new filterable `attention` value;
  existing `high`/`medium`/`low` values are unchanged, still filter on
  legacy `overall_risk` exactly as before), listing row badges.

**Out of scope for this increment, explicitly** (§2.B/C — not touched, no
route/template/behavior change made to any of these):

- Single-document badges (`results.html`, `review.html`,
  `shared_report.html`, `pdf_report.html`) — these already show the
  underlying policy/interaction findings as individual line items (§2.D);
  their headline badge is a smaller-consequence gap than a document
  disappearing from a queue entirely, and is a reasonable next increment
  rather than being bundled into this one, per "keep changes minimal" and
  "do not change unrelated UI."
- `batch_results.html` stats, `admin_dashboard.html` analytics — business/
  operator surfaces, not the lawyer-facing attention queue the task is
  concerned with.
- `evaluator.py`, `playbook_workbench.py`, demo/anonymous flows — traced
  and confirmed structurally unaffected or correctly out of scope (§2.C).
