# Contract Review Exception UX — Audit & Redesign

**Scope**: audit and design only, against the actual merged implementation as of commit `2d34b69`. No policy engine, authoring semantics, or application behavior changed to produce this report. Covers exactly the production contract-review experience: `templates/review.html` (795 lines), `review_workflow.py`, `main.py`'s `/contract/{id}/review*` routes, `policy_enforcement.py`'s finding construction, and `docx_export.py`'s export path. File:line citations throughout refer to this commit.

---

## 0. Verdict

**The page does not yet support review by exception — it supports review by omission.** Only actionable findings are generated in the first place (`policy_enforcement.py:267`, `_ACTIONABLE_STATES` excludes `ACCEPT`/`ACCEPT_WITH_NOTE`/`NOT_APPLICABLE`), so a lawyer never has to click through a wall of green checkmarks — that part is already correct and should not be rebuilt. But everything the lawyer *does* see is flat: one undifferentiated list (`renderPanelList()`, `review.html:424-445`), ordered by document position, not by severity; no visible count of how many total policy checks ran; no "X policy checks passed" line anywhere (there is nothing to collapse *behind*, because passed checks were never rendered as an artifact of "review by exception" — they were rendered as an artifact of "the finding list happens to be short"). Since the Phase 4.1 remediation (`2d34b69`), the governance layer (escalation, override history, request-exception language) is real and correctly wired — but it lives entirely *inside* a finding's detail popover. Nothing about it is visible from the queue, so a lawyer scanning the list before opening anything gets zero signal about which findings are governance-grade exceptions versus ordinary redline suggestions.

---

## 1–12. Direct answers

**1. Which findings should be visible by default?**
Every finding whose `policy_state` is `PROHIBITED`, `MUST_REDLINE`, or `ESCALATE` (from a `policy_decision` finding), plus every `critical`/`high` severity rule-engine finding. These are exactly the items that can produce a materially wrong decision if missed — the P0 tier from `docs/architecture/playbook_ux_audit.md`'s own severity model.

**2. Which should be collapsed?**
Three categories, each with its own collapsed rail rather than one undifferentiated pile: (a) `NEGOTIATE` / `medium` severity — real issues, but negotiable-range, not deal-blocking; (b) `REQUIRES_REVIEW` (policy) and low-severity rule-engine findings needing a decision but carrying no redline; (c) anything already resolved this session (accepted/edited/rejected/flagged/dismissed) — currently these stay inline in the list, dimmed (`.is-resolved`, `review.html:110-112`), rather than moving out of the way. Passed policy checks are not "collapsed" today because they're never materialized as findings at all — see Q11.

**3. Ordering.**
`PROHIBITED` → `MUST_REDLINE` → `ESCALATE` → `NEGOTIATE` → `REQUIRES_REVIEW` → (acceptable states never appear as findings — see Q11). Within each tier, rule-engine `critical`/`high` findings interleave with `PROHIBITED`/`MUST_REDLINE` policy findings at the top; `medium` rule-engine findings interleave with `NEGOTIATE`. Today's actual order is `FINDINGS` array order, i.e. whatever order `run_analysis()`/`apply_policies_for_review()` happened to append findings in (rule-engine findings first, then policy findings appended per clause type in `pa.CLAUSE_TYPES` order — see `policy_enforcement.py:213-232`) — visually this means a `low`-severity rule-engine finding can sit above a `PROHIBITED` policy finding simply because it occurs earlier in the document (`renderDocument()`'s in-document marks follow position; `renderPanelList()`'s list follows `FINDINGS` array order, which is *not* severity-sorted either).

**4. What should the lawyer see before opening a finding?**
Today: a colored dot (severity only, `pli-dot`), a number, and a title (`review.html:428-434`) — no state, no whether it's a policy decision or a pattern match, no whether it requires formal exception handling. That is not enough to triage 40 findings without opening each one. Minimum needed pre-click: state badge (translated, not raw enum), a one-line "counterparty said X, you require Y" summary, and — for governance-tier findings — a small badge indicating escalation is required and to whom.

**5. What should open inside the finding?**
The hierarchy this task asks for is already *present* in the popover's data (`policy_source`, `our_position`/`counterparty_position`, `negotiation_ladder`, `rationale`, `redline`, `escalate_to`, the post-decision governance record) but not *ordered* that way visually — see §2 below for the exact target sequence.

**6. Fastest safe path from issue → evidence → redline?**
Currently: click finding in list → popover opens with rationale + diff already visible → click Accept. That's already close to optimal for the *accept* path — one click to open, one to accept, no extra navigation (`openFinding()` → `popoverHTML()` renders everything inline, no second network round-trip needed to see the redline). The gap is upstream of that: finding *which* issue to open first, from an unordered list, is the actual bottleneck — not what happens once it's open.

**7. When should "Apply preferred redline" (i.e. Accept) be primary?**
Already correct: `.pop-btn.primary` styling is applied to Accept whenever a redline exists (`review.html:502`), and since `2d34b69` the label itself becomes "Apply approved redline" specifically for a `policy_decision` finding with a redline (`review.html:493-495`). This is good and should not be changed further.

**8. When should "Request exception" replace generic Reject?**
Already implemented as of `2d34b69`: for `policy_decision` findings whose state is in `{PROHIBITED, MUST_REDLINE, ESCALATE}` (`POLICY_GOVERNANCE_STATES`, `review.html:459`), Reject becomes "Request exception," the placeholder copy changes, and the confirm button reads "Confirm exception" (`review.html:496-499,534`). Correctly scoped — `NEGOTIATE` and ordinary rule-engine findings keep generic Reject, since those aren't governance violations.

**9. How should escalation authority appear?**
Currently: `escalateHTML` renders "Requires approval from `<name>`" inside the popover (`review.html:479,520`) — correct content, but only visible after opening the finding. It should also surface as a compact badge in the queue row before opening (Q4), and — once overridden — persist as part of the visible record (already done inside the popover via `governanceRecordHTML`, `:487-491`, but likewise invisible from the queue).

**10. How should an approved override remain visible without cluttering the queue?**
Today an overridden finding stays in the flat list, dimmed via `.is-resolved` (`:110-112`), with no visual distinction from "accepted a routine redline" — a governance exception and a rubber-stamped typo fix look identical from the queue. It needs a small, persistent "Exception granted" chip distinct from the generic resolved checkmark, without expanding back into a full card (see the Override-Completed wireframe, §4).

**11. How should passed policy checks be summarized?**
There is currently no mechanism to do this at all. `_ACTIONABLE_STATES` (`policy_enforcement.py:267`) deliberately excludes `ACCEPT`/`ACCEPT_WITH_NOTE`, so an accepted policy decision **never becomes a finding** — meaning the total number of policy checks that ran (accept + actionable) is not preserved anywhere in the data reaching `review.html`. `contract.policy_decisions_json` *does* hold one entry per evaluated clause type including `ACCEPT`/`NOT_APPLICABLE` ones (`policy_enforcement.py:379-380`, `apply_active_policies`) and is already passed into the template context (`main.py`'s `review_contract` route: `"policy_decisions": contract.policy_decisions_json`) — it is simply never used to compute a passed-count today (only used for the top policy-banner loop, `review.html:235-244`, which itself only shows non-`NOT_APPLICABLE` states, including passing ones, as a redundant second signal — see Q12). The data to build "X policy checks passed" already exists in the page; it is just not aggregated or surfaced.

**12. What information currently duplicates or distracts?**
- The top-of-page policy banner (`review.html:235-244`) and the finding-panel list both render policy state information, in two different visual styles, with two different translation qualities (banner uses `pd.state|replace('_',' ')`, popover badge uses `f.policy_state.replace(/_/g,' ')` in JS) — same fact, shown twice, inconsistently.
- `f.rule_id` is shown directly in the popover title (`:516`) in monospace, competing with the finding title for attention, for information a lawyer using the product day-to-day has no use for.
- The "confidence" badge (`pop-conf`, `:506`) only ever renders for rule-engine findings (`cb` is always null for `policy_decision`, so it silently disappears) — inconsistent presence is itself a minor distraction; a lawyer may wonder why some findings show a confidence label and others don't, without any copy explaining that policy decisions are deterministic and don't have "confidence" as a concept.
- `negotiation_ladder` (`:470`) and the raw state badge both communicate "where does this fall on the accept→escalate spectrum," in two different visual languages (a horizontal step tracker vs. a colored pill) with no explicit link between them.

---

## 2. Target hierarchy for every actionable policy finding

```
DECISION                              (state badge, translated — not raw enum)
  ↓
COUNTERPARTY POSITION                 (what their contract actually says — f.our_position/counterparty_position, contract_language)
  ↓
YOUR PLAYBOOK                         (what you require — negotiation_ladder, policy_source/controlling_provision)
  ↓
RECOMMENDED ACTION                    (required_action / rationale, one sentence)
  ↓
PRIMARY CTA                           (Apply approved redline / Request exception, sized and colored to match §1's severity ordering)
  ↓
WHY THIS DECISION?                    (rationale, expandable — collapsed by default for governance-tier states where the CTA should not compete with a wall of text)
  ↓
EVIDENCE                              (evidence_report / matched_excerpt / escalate_to — the deepest, least-needed-by-default layer)
```

This is a reordering of data the popover already computes, not new data. The current DOM order (`popoverHTML()`, `review.html:513-543`) is: state badge + title + Verify → source → escalate → positions → rationale → ladder → diff → actions → verify-stamp → inputs → governance record. That interleaves "why" before "what to do," and buries the primary action beneath four blocks of context a lawyer may not need to read before deciding. The target order puts the decision and the two positions first (what a lawyer needs to *triage*), the action next (what a lawyer needs to *act*), and pushes rationale/evidence below the action (what a lawyer needs to *justify*, read only when the decision isn't already obvious or when writing the override reason).

---

## 3. Needs Your Attention / Passed Checks split

Design principle: two rails, not one list. The queue view (`renderPanelList()`'s replacement) becomes:

```
NEEDS YOUR ATTENTION                                    N
  [severity-grouped rows, per §1/§3 ordering]

▸ 12 POLICY CHECKS PASSED                                 (collapsed by default, expandable)
```

"12 policy checks passed" is computed from `contract.policy_decisions_json` (already in the template context) — count entries whose `state` is `ACCEPT`/`ACCEPT_WITH_NOTE`, plus (separately labeled, since they're a different kind of "nothing to flag") entries whose `state` is `NOT_APPLICABLE` shown as "N clause types not addressed in this contract" if that count is non-zero, so silence is never confused with "checked and fine." Rule-engine findings have no equivalent "passed" concept today (the rule engine only ever emits findings, never a positive "this clause is fine" record) — the collapsed section is scoped to policy checks specifically, and that scope should be labeled explicitly ("policy checks passed," not "checks passed") so it isn't read as a claim about the full 189-rule pattern-match pass.

---

## 4. Detailed text wireframes

### 4.1 Review summary header
Replaces/extends the current topbar (`review.html:217-233`) and the redundant policy-banner loop (`:235-244`) with one merged summary:

```
ACME SERVICES AGREEMENT                                    HIGH RISK
Playbook: Acme Vendor Playbook · 6 policy checks · 4 pattern findings

NEEDS ATTENTION            3 Prohibited/Must Redline · 2 Negotiate · 1 Needs Review
                                                    [Full Report & Audit Trail]  [?]
In Review · 4 of 6 resolved                                    [Finalize Review]
```
The per-clause policy banner (today's `.policy-banner` loop) is removed as a separate element — its information (state per clause) is now implicit in the queue rows themselves; repeating it above the fold added a second, differently-styled copy of the same fact (Q12).

### 4.2 Exception queue
```
NEEDS YOUR ATTENTION                                              3
──────────────────────────────────────────────────────────────────
🔴 PROHIBITED   Limitation of Liability                    ⚑ GC approval
   Counterparty: unlimited liability · Your playbook: max 2×
──────────────────────────────────────────────────────────────────
🔴 MUST REDLINE  Governing Law                              ⚑ redline ready
   Counterparty: New York · Your playbook: Delaware required
──────────────────────────────────────────────────────────────────
🟠 ESCALATE      Indemnification                            ⚑ GC approval
   Counterparty: uncapped indemnity · Your playbook: 3× cap
──────────────────────────────────────────────────────────────────
NEGOTIATE (2)                                       [expand ▾]
NEEDS REVIEW (1)                                    [expand ▾]
──────────────────────────────────────────────────────────────────
▸ 6 POLICY CHECKS PASSED
```
Each row is a single line plus one summary sub-line — enough to triage without opening. The ⚑ badge is new: "GC approval" when `escalate_to` is present, "redline ready" when a fallback exists and no escalation is required. `NEGOTIATE`/`REQUIRES_REVIEW` collapse into their own count-only rails by default (Q2), expandable per-tier rather than per-item, so a lawyer can choose to skip past negotiable items entirely on a first pass.

### 4.3 PROHIBITED finding (open state)
```
┌─────────────────────────────────────────────────┐
│ PROHIBITED                              ⟳ Verify │
│ Limitation of Liability                          │
├─────────────────────────────────────────────────┤
│ Counterparty position                            │
│   "...liability shall be unlimited..."           │
│ Your playbook                                    │
│   Maximum permitted: 2× fees · Unlimited: never  │
│ Requires approval from  General Counsel          │
├─────────────────────────────────────────────────┤
│ [Apply approved redline]   [Request exception]   │
├─────────────────────────────────────────────────┤
│ ▸ Why this decision?                             │
│ ▸ Evidence                                       │
└─────────────────────────────────────────────────┘
```
Rationale and evidence are collapsed by default here specifically — for a hard PROHIBITED block, the two CTAs are usually sufficient; forcing the lawyer past a paragraph of explanation before reaching the button is backwards for the most severe, least-ambiguous state.

### 4.4 NEGOTIATE finding (open state)
```
┌─────────────────────────────────────────────────┐
│ NEGOTIATE                               ⟳ Verify │
│ Termination                                      │
├─────────────────────────────────────────────────┤
│ Counterparty: 90 days' notice                    │
│ Your playbook: Preferred 30 · Acceptable ≤60     │
│ Preferred → Accept → Negotiate → Escalate  (●Neg)│
├─────────────────────────────────────────────────┤
│ [Apply fallback]  [Edit]  [Reject]  [Comment]    │
├─────────────────────────────────────────────────┤
│ Why this decision? 90 days exceeds your 60-day   │
│ acceptable threshold but remains within the      │
│ negotiable range — no escalation required.       │
└─────────────────────────────────────────────────┘
```
No "Request exception" here — `NEGOTIATE` is not a governance state (§0.3/Q8's existing scoping is correct); rationale stays visible by default since a negotiate call is more often genuinely disputable than a flat prohibition.

### 4.5 REQUIRES_REVIEW finding (open state)
```
┌─────────────────────────────────────────────────┐
│ NEEDS REVIEW                            ⟳ Verify │
│ Indemnification                                  │
├─────────────────────────────────────────────────┤
│ Indemnification language is present but its      │
│ structure could not be automatically classified. │
│ No redline is offered — this needs a human read. │
├─────────────────────────────────────────────────┤
│ [Flag for Manual Drafting]  [Dismiss]  [Comment] │
├─────────────────────────────────────────────────┤
│ ▸ Evidence (matched language)                    │
└─────────────────────────────────────────────────┘
```
Matches the existing no-redline action set (`review.html:507-510`) — this wireframe is mostly a relabeling/reordering of what's already there, not new mechanics.

### 4.6 Redline action (in-place, already-good behavior preserved)
```
BEFORE                                    AFTER (inline, on Apply)
"...liability shall not exceed          "...liability shall not exceed
five (5) times total fees..."     →      ~~five (5) times~~ two (2) times
                                          total fees...  [EDITED if hand-changed]
```
This is the existing `diff-box` + post-accept strike/insert mutation (`review.html:469`, `640-663`) — no changes recommended here; it is already fast and legible.

### 4.7 Escalation / exception request (new)
```
Request exception
Current decision:        PROHIBITED — Unlimited liability
Requires approval from:  General Counsel
Your decision:           [Accept exception ▾]
Reason (required):       [__________________________________]
                          [Cancel]           [Confirm exception]
```
This is what the existing "reject-input" textarea (`:532-535`) should visually become for governance-tier findings, rather than a generic rejection textarea with different placeholder text — same underlying `rejected` action and validation (`review_workflow.validate_decision`, unchanged), different visual framing.

### 4.8 Override-completed state (in queue, collapsed)
```
🔴 PROHIBITED   Limitation of Liability          ✓ Exception granted
   by Jane Smith · Aug 12, 2026
```
One line, not a full card — distinct from the generic resolved checkmark (`pli-check`, currently identical for every action type) via a labeled chip instead of a bare ✓, so a scanning lawyer or a later reviewer can tell "this was overridden" apart from "this was routinely accepted" without opening it.

### 4.9 Passed-checks collapsed section (expanded state)
```
▾ 6 POLICY CHECKS PASSED
   ✓ Confidentiality — mutual, 3-year term (within policy)
   ✓ Assignment — consent required (matches policy)
   ✓ Governing Law — Delaware (preferred jurisdiction)
   ...
```
Each line is `pa.CLAUSE_TYPE_LABELS[clause_type]` + `extracted_summary` from the corresponding `policy_decisions_json` entry — read-only, no actions, no evidence drawer (nothing to investigate about a passing check).

### 4.10 Evidence drawer
```
Evidence
CONTRACT
  "Neither party's aggregate liability shall exceed
   three times fees paid in the preceding twelve months."
DETECTED POSITION
  General cap = 3× fees
YOUR PLAYBOOK
  Preferred 1× · Auto-accept ≤2× · Negotiate ≤3×
DECISION
  NEGOTIATE
[⟳ Verify this decision]
```
This is `decision.render_evidence_report()` (already computed server-side, `policy_engine_core.py`) plus the existing Verify action, presented as a dedicated collapsed drawer rather than interleaved into the main popover body — pulling the "deepest trust layer" (Q5/§2) out from between the rationale and the action buttons where it currently sits.

### 4.11 Export / audit summary
The existing "Generate Negotiation Package" zip (`main.py`'s `/contract/{id}/review/package`, `docx_export.build_redlined_docx` + `review_workflow.build_cover_memo_text` + `review_workflow.build_audit_trail_text`) already includes, as of `2d34b69`, the original policy recommendation and decided-by for overridden findings (`review_workflow.py:192-199`). The completion-screen summary (`review.html:270-280`) should gain one line surfacing exception count specifically:

```
Review complete
18 accepted (2 edited) · 3 rejected · 1 flagged/dismissed
2 policy exceptions granted — see Audit Trail for approval record
[↻ Run it again — verify determinism]   [Generate Negotiation Package →]
```
"2 policy exceptions granted" is a filtered count of decisions where `policy_original_recommendation` is present and the resulting action differs from what a plain accept would represent — computable client-side from `DECISIONS` at finalize time, no new server data required.

---

## 5. Files/routes affected and priority

| # | Recommendation | Files / routes | Priority |
|---|---|---|---|
| 1 | Severity-grouped, ordered queue (replace flat `renderPanelList()`) | `templates/review.html` (`renderPanelList`, `:424-445`) | **P0** |
| 2 | "X policy checks passed" collapsed section, sourced from `contract.policy_decisions_json` | `templates/review.html` (new render function); `main.py`'s `review_contract` route already passes `policy_decisions` — no backend change needed | **P0** |
| 3 | Pre-click row summary (state badge translated, counterparty-vs-playbook one-liner, escalation badge) | `templates/review.html` (`renderPanelList`); optionally a small `FIELD`-style label dict in `policy_enforcement.py` or JS-side map, reusing the translation work already scoped for `docs/architecture/playbook_ux_audit.md` §3 | **P0** |
| 4 | Reorder popover body to Decision → Counterparty → Playbook → Action → Why → Evidence | `templates/review.html` (`popoverHTML()`, `:461-543`) | **P1** |
| 5 | Evidence as a collapsed drawer, not inline | `templates/review.html` (`popoverHTML()`) | **P1** |
| 6 | Distinct "Exception granted" chip in queue (not generic ✓) | `templates/review.html` (`renderPanelList`, `.pli-check` styling) | **P1** |
| 7 | Merge top policy-banner into the summary header (remove duplicate rendering) | `templates/review.html` (`:235-244`) | **P1** |
| 8 | Finalize/completion screen: exception-count line | `templates/review.html` (`:270-280`, finalize handler `:704-715`) | **P2** |
| 9 | De-emphasize `rule_id` in popover title | `templates/review.html` (`popoverHTML()`, `:516`) | **P3** |
| 10 | Explanatory copy for absent confidence badge on policy findings | `templates/review.html` (`popoverHTML()`, `:506`) | **P3** |
| 11 | Collapse-by-default rationale/evidence specifically for PROHIBITED/MUST_REDLINE (keep expanded for NEGOTIATE) | `templates/review.html` (`popoverHTML()`) | **P2** |

No changes are proposed to `policy_enforcement.py`'s finding construction, `review_workflow.py`'s decision validation/progress logic, `docx_export.py`, or any policy engine — every recommendation above is a `review.html` presentation change over data that already exists in the page (`findings`, `decisions`, `policy_decisions`) or is one small, additive server-side aggregation (item 2, and only if the per-row summary in item 3 needs data not already on the finding dict — it does not: `our_position`/`counterparty_position`/`policy_state` are already present).

---

## 6. What should not be touched

- The document-annotation layer (`renderDocument()`, `buildMarkGroups()`, the margin map) — genuinely good information architecture for long documents, not in scope for this audit and not a source of the review-by-exception gap.
- The redline diff/accept/edit mechanics (`diffHTML`, `submitDecision()`'s inline strike/insert) — already fast, already correct.
- The Verify fix and governance/override plumbing shipped in `2d34b69` — correct at the data layer; this audit's findings are entirely about *where* that data is (or isn't) surfaced, not about its correctness.
- Keyboard shortcuts (`j/k/a/e/r/c/v`) — functional and appropriately scoped; reordering the queue changes *which* finding `j`/`k` land on, not the mechanism itself.
