# TriageCounsel Playbook — Production UX Audit

**Scope**: audit and design only. No application code, templates, CSS, JS, routes, models, or engines were modified to produce this report. All findings are sourced directly from the merged implementation on this branch — file:line citations are given throughout. Design docs (`docs/architecture/playbook_authoring_ux_design.md`, `phase2_extraction_mapping.md`, `phase4_cutover.md`) were consulted for intent only; the running code is authoritative.

---

## 0. Executive summary

The deterministic policy engine and the authoring lifecycle (Phase 0–4.1) are genuinely strong and, in several places, the UI already reflects real product thinking — tristate controls that prevent unanswered-vs-"No" confusion, a categorical (never numeric-confidence) import-review vocabulary, and a redline/accept/reject flow with a real audit trail. But the audit surfaced five defects severe enough that they would materially mislead a commercial lawyer, not just annoy one:

1. **Two disconnected playbook-creation systems coexist.** `/playbooks/new` (`main.py:2550`) is the pre-authoring-layer legacy flow — it still writes directly to `PolicyRule`, uses plain checkboxes for booleans, and never mentions the Workbench, deterministic import, or AI import. A lawyer who completes it believes they've configured their policy and has no path to discovering the actual six-clause system unless they separately click "Policy Workbench" off the playbook card afterward.
2. **The flagship trust feature is broken for every policy decision.** "Verify" (`/contract/{id}/review/verify`, `main.py:2327`) only replays `rule_engine.analyze()` (the 189 pattern rules). Every policy engine uses a static `RULE_ID` (`"POLICY_LOL_CAP"`, `liability_policy_engine.py:70`) that never appears in that replay, so verifying a policy finding **always** returns `verified=false` and the UI tells the lawyer "the stored finding may be stale" (`review.html:535`) — a false statement, every single time, about the product's core differentiator.
3. **Escalation has no UI.** `PolicyDecision.escalate_to` (`policy_engine_core.py:377`) is computed by the engine but never placed into the finding dict (`policy_enforcement.py:96-124`), never rendered in `review.html`, and no "override" affordance exists anywhere in the templates. An ESCALATE/PROHIBITED finding gets the identical Accept/Edit/Reject/Flag/Dismiss treatment as an ordinary rule-engine finding — with no name attached to who must approve it.
4. **Overrides are recorded but invisible.** `main.py:2279-2284` stores `policy_original_recommendation` specifically so an override is "never silent" — but nothing reads that field back. It isn't shown before the action, after it, or in the exported audit trail (`review_workflow.build_audit_trail_text`, `review_workflow.py:175-201` prints only `action`/`reason`). The code's own stated intent is not met by the shipped UI.
5. **Test Policy is not discoverable from the one place it needs to be.** The Workbench (`playbook_workbench.html`) — the screen explicitly built to answer "what will TriageCounsel enforce" in under a minute — has no Test Policy link on any clause card. The only entry point is a text link buried at the bottom of the individual clause-edit page (`playbook_position_edit_base.html:124`).

None of these require touching the deterministic engines. All five are template/view-model changes. Full detail, evidence, and remediation is below.

---

## 1. Current-state UX map (as implemented, not as designed)

| Step | Route(s) | Template | Lawyer's goal | Primary action | What's shown | Decision required | Friction / problems |
|---|---|---|---|---|---|---|---|
| Playbooks list | `GET /playbooks` (`main.py:2538`) | `playbooks.html` | See existing playbooks, start a new one | "Create New Playbook" | Cards with name, type, description, template-rule count, **two separate links: "Policy Workbench" and "Edit"** | Which link to click? | Two links per card with overlapping-sounding purpose but entirely different data models underneath (see §2) |
| Create playbook | `GET/POST /playbooks/new` (`main.py:2551,2616`) | `playbook_form.html` | Set up a playbook so contracts get reviewed against it | Upload template + optionally enable a Limitation-of-Liability rule | Name/type/description/file upload, one clause's worth of raw fields (checkboxes, not tristate) | Enable LoL rule? Fill multiplier fields? | **No mention of the Workbench, deterministic import, AI import, or the other five clause types anywhere on this page.** Writes to legacy `PolicyRule`, not `PolicyPosition` |
| Workbench | `GET /playbooks/{id}/workbench` (`playbook_workbench.py:157`) | `playbook_workbench.html` | See what's Active vs. what needs attention | Click a clause card | Coverage %, Active/Needs review/Not configured counts, high-impact gaps, six clause cards (label, status pill, one-line headline, missing-question count) | Which clause to configure next | No fallback text, no escalation authority, no provenance, no revision status, **no Test Policy link** anywhere on this page |
| Manual authoring | `GET/POST /playbooks/{id}/positions/{clause}/edit` (`playbook_workbench.py:184,202`) | `policy_position_fields/{clause}.html` | Answer the legal questions for one clause | Fill tristate/threshold/checklist controls, Save draft | Clause-specific fields with plain-English labels; evidence banner if EXTRACTED/CONFLICTING fields exist | Answer each field; several have no helper text | Save-then-separately-submit-for-review is two clicks where one intent exists; "Test this policy" link is a small text link at the very bottom |
| Deterministic import | `GET/POST /playbooks/{id}/import` (`playbook_workbench.py:457,467`) | `playbook_import.html` | Extract policy from an existing template contract | Upload + check "Extract proposed policy positions" | Dual-checkbox (deviation baseline vs. policy extraction) on one upload | Which checkbox(es) | Well-explained ("2× cap establishes Preferred=2×, not Acceptable/Negotiable"); good |
| Import review | `GET /playbooks/{id}/import/{doc}/review` (`playbook_workbench.py:570`) | `playbook_import_review.html` | Understand what was found vs. what needs a decision | Open a clause card, resolve or confirm | Directly established / Proposed interpretation / Conflicts / Needs input, each with evidence excerpts | Confirm, resolve conflict, or answer | This page is genuinely good — see §8 |
| AI-assisted import | `GET/POST /playbooks/{id}/ai-import` (`playbook_workbench.py:629,640`) | `playbook_ai_import.html` | Turn a prose playbook memo into positions | Consent checkbox + upload | Clear disclosure of what's sent externally, consent required, disabled-state message when off | Consent | Well-scoped; converges into the same review page as deterministic import |
| Conflict resolution | (no dedicated route — happens inside `/positions/{clause}/edit`) | `playbook_position_edit_base.html` | Pick the correct value when two sources disagree | Manually re-answer the field | Evidence banner shows both excerpts | Which value is right | No side-by-side compare UI — the two conflicting excerpts are just listed, not diffed (see §8) |
| Review & approval | `GET /playbooks/{id}/positions/{clause}/review` (`playbook_workbench.py:305`) | `playbook_position_review.html` | Confirm the position is legally correct before it governs anything | Approve | Human-readable summary lines, missing-questions blocker, approval history | Approve or return to draft | Good — see §9 |
| Activation | `POST /playbooks/{id}/positions/{clause}/activate` (`playbook_workbench.py:370`) | same page | Make the position live | Activate | Explicit separate step from Approve, with a one-line explanation of the distinction | Activate | Clear |
| Test policy | `GET/POST /playbooks/{id}/positions/{clause}/preview` (`playbook_workbench.py:412,426`) | `playbook_position_preview.html` | Build trust that the engine will do the right thing | Paste sample text, Run preview | State badge (raw enum, see §4), what was found, why, required action, matched language | None — read-only | No "your playbook says" comparison, no negotiation ladder, no evidence link — see §10 |
| Upload counterparty contract | `GET/POST /upload-page`, `/upload` (`main.py:1270,1280`) | `upload.html` | Get a contract reviewed | Select playbook, upload file | — | Which playbook | Not audited in depth (out of Playbook scope per the task, but flagged: playbook selection happens here, not on the Workbench) |
| Contract review | `GET /contract/{id}/review` (`main.py:2222`) | `review.html` | Find and resolve every issue that matters | Work through findings | Annotated contract text, margin map, sticky finding panel | Accept/Edit/Reject/Flag/Dismiss per finding | **Highest-priority page — full audit in §11–13** |
| Apply redline | `POST /contract/{id}/review/decision` (`main.py:2255`) | (JSON, in-page) | Fix the language quickly | Click Accept | Diff preview (strike/insert) | Accept as-is, edit, or reject with reason | Fast once open; getting to "the one that matters" is the real friction (§11) |
| Override/escalate | same route, `finding_type == "policy_decision"` | (JSON, in-page) | Make and record a considered exception | Same Accept/Reject as any finding | Nothing distinguishes this from a normal finding | — | **No override UI exists** — see §14 |
| Export | `GET /contract/{id}/review/package` (`main.py:2380`) | — (zip file) | Get a redlined document + record | Click "Generate Negotiation Package" | Redlined `.docx` + cover memo + audit trail | — | Audit trail doesn't include `policy_original_recommendation` (§14) |

---

## 2. The ruthless standard, applied

**A. Create or import a playbook** — **Fails.** Two unrelated creation surfaces exist (`/playbooks/new` writing `PolicyRule`; the Workbench's "Import a template"/manual-authoring writing `PolicyPosition`), and the entry point a new lawyer actually lands on (`playbooks.html` → "Create New Playbook" → `/playbooks/new`) is the *legacy* one. There is no page that presents the three paths (manual / deterministic / AI) as a single decision, matching neither the task's wireframe nor any coherent product story. This is the single biggest gap between intended and implemented UX in the entire audit.

**B. Understand exactly what will be enforced** — **Partially fails.** The Workbench shows status and a one-line headline per clause, but omits fallback text, escalation authority, and provenance — exactly the fields the approval screen (`playbook_position_review.html`) *does* show well. A lawyer has to click into every clause to get the full picture the Workbench promises to summarize.

**C. Correct anything wrong** — **Passes for authoring**, since tristate controls make "not decided" structurally distinct from "No" (`_playbook_macros.html:6-25`), and unanswered-required-field blocking is enforced server-side (`playbook_authoring.validate_position_for_activation`) and shown clearly (`playbook_position_review.html:48-61`). **Fails at contract-review time** — there is no way to say "this policy call is wrong for this specific contract, here's why" distinctly from "the rule-engine pattern match was wrong" (§14).

**D. Approve and activate** — **Passes.** This is the best-executed part of the product. Plain-English summary ("What this policy will enforce"), explicit Draft→Needs Review→Approved→Active separation, append-only approval history. See §9.

**E. Test against sample language** — **Passes narrowly, fails on discoverability.** The mechanism itself (preview-only, no Contract record, real evaluator) is sound, but it's unreachable from the Workbench and the result screen shows a raw state string with no comparison to the playbook's own thresholds (§10).

**F. Review by exception** — **Passes structurally, undermined by two defects.** Only actionable states create findings (`policy_enforcement.py:107`, `_ACTIONABLE_STATES`) — passed/accepted clauses generate zero noise, which is the right default. But (1) there's no positive confirmation of *how many* checks ran and passed (a lawyer can't tell "6 policies checked, 5 fine, 1 issue" from "1 issue" alone — see §11), and (2) the Verify button lies about policy findings (§0.2).

**G. Understand why a decision occurred** — **Passes well for rule-engine findings, is materially weaker for policy findings** because of the Verify bug and because `escalate_to` never reaches the UI.

**H. Apply an approved redline quickly** — **Passes.** Accept is one click, the diff preview is immediate, and the applied redline is written inline into the document. See §12.

**I. Override/escalate with an audit trail** — **Fails.** No override UI exists at all (§0.3, §0.4, §14).

**J. Export** — **Passes** for the mechanics (docx + memo + trail in one zip); **fails** to carry the override/escalation record into that trail.

---

## 3. Implementation-terminology leakage (full inventory)

Legend: **OK** = correctly translated / never rendered · **TRANSLATE** = renders as text but only via `.replace('_',' ')` on the raw constant, not authored copy · **HIDE** = should not be shown to a lawyer at all in its current form.

| Term / pattern | Where it renders | Verdict | Fix |
|---|---|---|---|
| `PolicyPosition`, `PolicyPositionField`, `config_json`, `Protocol`, `adapter`, `evaluator`, `extractor` | Nowhere in any lawyer-facing template (confirmed by full-text search) | **OK** | None needed |
| `require_*`/`prohibit_*` raw field names | Only as invisible `name=` form attributes; visible label always goes through `FIELD_LABELS` (`playbook_authoring.py:1224`) | **OK** | None needed |
| `NOT_ESTABLISHED`, `ESTABLISHED`, `CONFLICTING`, `EXTRACTED` | Only as Jinja comparison literals (`selectattr(...,'equalto','EXTRACTED')`, `field_statuses.get(name,'NOT_ESTABLISHED')`) — never printed | **OK**, but fragile: 11 templates duplicate the literal `'NOT_ESTABLISHED'` string with no shared constant; one future template printing `field_statuses.get(name)` directly would leak it | Add a `FIELD_STATUS_LABELS` dict alongside `FIELD_LABELS`, even though nothing currently needs it — cheap insurance |
| `position.status` (DRAFT/NEEDS_REVIEW/APPROVED/ACTIVE) | `playbook_position_edit_base.html:25`, `playbook_position_review.html:24`, `playbook_position_preview.html:24`, `playbook_workbench.html:61` | **TRANSLATE** | Add a `POSITION_STATUS_LABELS` dict: `{"DRAFT": "Draft", "NEEDS_REVIEW": "Awaiting your review", "APPROVED": "Approved, not yet active", "ACTIVE": "Active"}` |
| `h.from_status`, `h.to_status` (approval history) | `playbook_position_review.html:98` — **rendered with zero filter** | **TRANSLATE** (currently worse than the others — completely raw) | Same dict as above, applied to both sides of the arrow |
| `h.action` (MARKED_REVIEWED/APPROVED/ACTIVATED/REVERTED/ARCHIVED) | `playbook_position_review.html:97` | **TRANSLATE** | `APPROVAL_ACTION_LABELS` dict, e.g. `"ACTIVATED": "Activated"`, `"REVERTED": "Sent back to draft"` |
| `position.source_type` non-MANUAL branch | `playbook_position_edit_base.html:31` — only `MANUAL` is translated ("Entered manually"); every other value (`UPLOADED_TEMPLATE`, `UPLOADED_PLAYBOOK`, `MIXED`) prints raw | **TRANSLATE** | Extend the existing `if/else` into a full `SOURCE_TYPE_LABELS` dict: `{"MANUAL": "Entered manually", "UPLOADED_TEMPLATE": "Extracted from your template", "UPLOADED_PLAYBOOK": "Extracted from your playbook document", "MIXED": "Combined from multiple sources"}` |
| `decision.state` (ACCEPT/ACCEPT_WITH_NOTE/NEGOTIATE/MUST_REDLINE/PROHIBITED/ESCALATE/REQUIRES_REVIEW) | `playbook_position_preview.html:41` (test policy), `review.html:235` (policy banner), `review.html:479` in JS (finding popover badge) | **TRANSLATE** (`.replace('_',' ')` only, no `title` filter even applied in two of the three) | One `DECISION_STATE_LABELS` dict/JS object shared by all three: `PROHIBITED → "Not acceptable"`, `MUST_REDLINE → "Must redline"`, `ESCALATE → "Needs approval to proceed"`, `NEGOTIATE → "Negotiate"`, `REQUIRES_REVIEW → "Needs manual review"`, `ACCEPT_WITH_NOTE → "Acceptable, noted"`, `ACCEPT → "Acceptable"`. Do not weaken legal precision — these are still six distinct concepts, just named for a reader instead of a state machine. |
| `clause_type` in the review-page policy banner | `review.html:236` — `{{ clause_type|replace('_','title') }}` instead of the `CLAUSE_TYPE_LABELS` dict already used correctly elsewhere (`playbook_position_edit_base.html:18`) | **TRANSLATE** (inconsistency, not a new dict needed) | Route through `CLAUSE_TYPE_LABELS`, which already exists and is already correct everywhere else |
| `f.rule_id` (e.g. `POLICY_LOL_CAP`, or a rule-engine ID) | `review.html:480,534` — shown directly in the finding popover title and the Verify confirmation text, mono-styled | **HIDE** (from primary text) / demote | Keep it, but move it out of the title line into a small "Reference: `POLICY_LOL_CAP`" caption a lawyer can ignore — currently it sits inline with the finding title, competing for attention with the thing that actually matters |
| Confidence percentages | Not found anywhere for policy decisions (`confidence_breakdown` is `null` for `finding_type == "policy_decision"`, `policy_enforcement.py`) | **OK** | None — this is a correctly-kept product decision from Phase 3; do not add percentages back in |

**Net assessment**: the *authoring* surface (clause forms, macros, import review) is disciplined about translation. The *state-machine vocabulary* (position status, approval actions, source type, decision state) is not — it's translated inconsistently, sometimes not at all, and the review page (the highest-stakes surface) has the worst instance of the pattern.

---

## 4. Playbook creation — the actual experience vs. the wireframe

The task's proposed three-card chooser (Upload playbook / Upload template / Build manually) **does not exist in the implementation at all.** What exists instead:

1. `playbooks.html` → "Create New Playbook" → `/playbooks/new` → `playbook_form.html`. This is a single form: name, type, description, one file upload, and an optional "Enforce a Limitation of Liability policy" section using **plain checkboxes** for `prohibit_unlimited` and `require_consequential_damages_exclusion` (`playbook_form.html:166,195`) — the exact unchecked-vs-explicit-False ambiguity that Phase 1's tristate work exists specifically to prevent, just not applied here because this form predates that work and was never migrated.
2. Only *after* creating a playbook this way does a "Policy Workbench" link appear on the playbook card (`playbooks.html:62`), leading to the real six-clause system.
3. Deterministic import and AI import are each one more click deep, off the Workbench ("Import a template" button, `playbook_workbench.html:19`) and off `playbook_import.html`'s footer link, respectively — never mentioned at playbook-creation time.

**Recommendation** (design only): replace `playbook_form.html`'s role as the primary creation entry point. `/playbooks/new` should become a minimal "name your playbook" step that redirects straight into a three-path chooser resembling the task's wireframe, reusing copy already proven to work well in `playbook_import.html`/`playbook_ai_import.html`:

```
Create Playbook
──────────────────────────────────────────
Name: [________________________]  Contract type: [dropdown]

How would you like to start?

┌────────────────────────────────────┐
│ Upload your legal playbook          │
│ AI-assisted · sends excerpts        │
│ externally, with your consent       │
│                                      │
│ Turn a written guidelines memo      │
│ into positions you review and       │
│ approve.                            │
└────────────────────────────────────┘
┌────────────────────────────────────┐
│ Upload a standard contract          │
│ Private · deterministic             │
│                                      │
│ Extract positions directly from     │
│ your own template. Nothing leaves   │
│ this server.                        │
└────────────────────────────────────┘
┌────────────────────────────────────┐
│ Build it yourself                   │
│                                      │
│ Answer plain-English questions      │
│ for each clause type.               │
└────────────────────────────────────┘

You can combine these later — e.g. import a template, then
manually fill in what it couldn't establish.
```

The privacy distinction is already well-worded in the existing pages (`playbook_import.html:18-19`: *"DETERMINISTIC & PRIVATE — no document content is ever sent to an AI model"*; `playbook_ai_import.html:19`: *"DIFFERENT FROM DETERMINISTIC IMPORT — this path sends document excerpts to an AI provider"*). Reuse that copy verbatim on the chooser cards rather than re-explaining it — it is not scary, it is precise, and precision is what a lawyer wants here.

The legacy single-clause `PolicyRule` path in `playbook_form.html` should be retired from the creation flow entirely once this ships (kept only as the `/playbooks/{id}/edit` metadata/template-text editor it also serves, stripped of the LoL section — which duplicates, and can drift from, the Workbench's Limitation of Liability card).

---

## 5. The Workbench — does it answer "what will TriageCounsel enforce" in 30–60 seconds?

**Mostly, with two real gaps.** `playbook_workbench.html:22-49` (coverage bar + Active/Needs review/Not configured counts + high-impact gaps) is a good, scannable summary — this part matches the spirit of the task's wireframe closely. The per-clause card grid (`:51-74`) is where it falls short:

- **Shown**: label, status pill, one-line `card.headline` (from `playbook_authoring.card_headline`), a missing-question count if incomplete.
- **Not shown, despite being exactly what "what will TriageCounsel enforce" means**: the actual thresholds (preferred/acceptable/negotiate), fallback text presence, escalation authority, provenance (manual/extracted/AI), or revision state (is this card's ACTIVE position superseded by an unapproved draft sitting behind it?).
- **Not shown at all**: a Test Policy affordance. This is the biggest concrete gap versus the task's hypothesis card design — the wireframe's `[Edit policy] [Test policy]` button pair does not exist; only `[Configure →]`/`[Open →]` does (`:69-71`).

**Recommendation**: expand each card to show the two or three numbers that matter most for that clause type (reusing the `summarize_position`/`_summarize_*` helpers already in `playbook_authoring.py`, which compute exactly this for the approval screen — see §9 — but are not currently called from the Workbench card-building path), add a fallback/escalation presence indicator (even just "✓ Fallback set" / "⚠ No fallback"), and add `[Test policy →]` next to the existing edit link. This is additive to the existing `card` view-model, not a rebuild.

**On scaling beyond six clause types**: the current grid (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`) degrades gracefully by wrapping, so it will not "break" at 10–12 clause types, but it will stop being scannable in 30–60 seconds. Before Batch B ships, the coverage summary section should absorb a filter/search affordance ("Show: Needs attention only"), and the high-impact-gaps callout (already present and already the right idea) should become the primary way a lawyer with 12 clause types prioritizes, rather than scanning every card.

---

## 6. The six manual-authoring experiences

Spot-audited all six templates (`templates/policy_position_fields/*.html`) plus the shared macros (`_playbook_macros.html`) and base shell (`playbook_position_edit_base.html`).

**What's right and should not be redesigned**:
- Tristate controls (`tristate()` macro) with "Yes, require this / No, we explicitly do not require this / Not decided yet" — this is exactly the right pattern and is used consistently across all 15 boolean fields across the six clause types.
- Threshold questions use a shared `ladder_group()` macro (Preferred / Auto-accept up to / Negotiate up to) with one consistent explanatory line ("Anything above 'negotiate up to' is routed to escalation... Leave any of these blank if not yet decided") — a lawyer only has to learn this pattern once and it applies to Liability, Indemnification exposure, and Termination fees identically.
- Question grouping roughly follows legal logic (e.g. Indemnification: "What they owe us" then "What we're willing to owe them" — `indemnification.html:5,10` — mirrors how a lawyer actually thinks about mutual indemnification).
- The evidence banner ("Why TriageCounsel proposed these values", `playbook_position_edit_base.html:50-74`) correctly appears only when there's something to explain, and shows conflicting sources with their excerpts inline.

**What's inconsistent**:
- Helper text (`help=` argument) is present for the first tristate field in Liability and Indemnification but **absent** for several later fields in the same clause type — `require_defense_control_for_exposure` and `require_notice_and_cooperation_for_exposure` (`indemnification.html:19,22`), `require_jury_trial_waiver` (`governing_law.html:15`) rely entirely on the `field_labels` phrase to carry the full legal meaning, with no room to explain the consequence of choosing Yes vs. No the way `prohibit_unlimited`'s helper text does ("If 'No,' an uncapped liability clause still gets flagged for escalation instead of being auto-blocked" — `limitation_of_liability.html:12`). A lawyer new to the product will understand *what* they're being asked less consistently than *why* it matters.
- Governing Law's jurisdiction fields are free-text comma-separated strings (`jurisdiction_list()` macro) with no autocomplete/validation against real jurisdiction names — reasonable given "there's no fixed list" (`governing_law.html:9`), but no help exists if a lawyer types "Delaware, NY" vs. "Delaware, New York" and the engine's matching is stricter than expected; this is worth a determinism note in the help text, not a validation change.
- Save behavior: "Save draft" is always the button label regardless of whether the position is DRAFT or already NEEDS_REVIEW/APPROVED being re-edited — and re-editing silently reverts status to DRAFT (`playbook_authoring.apply_position_update`, correct behavior) but the *button* never says so; a lawyer editing an already-Approved position could be surprised their edit un-approved it, discoverable only after the fact on the review page.

**Recommendation**: do not replace these with a generic schema-driven form generator — the clause-specific grouping and phrasing is doing real work a generic renderer would lose. Instead: (1) add a one-line consequence explainer for every currently-bare tristate field (11 identified fields across four clause types), (2) change the save button's helper caption to say "This position is currently Approved — saving will return it to Draft for re-review" when applicable.

---

## 7. Deterministic and AI-assisted import review

Both paths converge on `playbook_import_review.html` for deterministic import and the same review page for AI-confirmed clauses (via the shared `established`/`proposed_interpretation`/`conflicting`/`needs_input` bucketing in `playbook_workbench.py`). **This is one of the best-executed pages in the product.** The four-bucket vocabulary is exactly right and already matches the task's target language almost verbatim:

- "Directly established" (green, `:37`) — with inline collapsible evidence (`&lt;details&gt;`, `:44-47`).
- "Proposed interpretation" (indigo, `:56-58`) — explicit copy: *"AI interpretation of qualitative or unconfirmed language — requires your confirmation, never treated as established on its own."*
- "Conflicts to resolve" (red, `:74`) — shows the excerpt, links to "Resolve →".
- "Needs your input" (amber, `:90`) — explicit copy: *"These are unanswered — not answered 'no,' not permissive by default."*

No confidence percentages anywhere. No raw provenance enum values leak through — every bucket label is hand-authored.

**The one real gap**: conflict resolution (`:73-86`) lists the conflicting evidence items but does not diff them side-by-side the way the task's wireframe suggests (`Main Agreement: Within general cap` / `DPA: Unlimited`, compared in one view). Currently a lawyer sees a list of excerpts and must click through to the clause-edit page to actually resolve it, where the two sources are shown as separate bullet points (`playbook_position_edit_base.html:54-60`) rather than a true comparison. This is a real but modest gap — the information exists, it's just not laid out for quick side-by-side reading.

**Recommendation**: on the conflict card, render the two (or more) evidence excerpts as a two-column comparison (source label + excerpt on each side) with the resolution control inline, rather than requiring a navigation to the clause-edit page to make the call.

---

## 8. Approval and activation

**This is the strongest part of the product.** `playbook_position_review.html:37` — *"What this policy will enforce"* — followed by `summary_lines` (built by `playbook_authoring.summarize_position` and its six `_summarize_*` clause-specific helpers) reads exactly like the target output in the task brief:

```
Preferred                     1× fees
Accept without approval       ≤2× fees
Maximum negotiable            3× fees
...
```

No JSON, no field names, no database language. The blocking state ("Before this can be approved or activated" / disabled Approve button with a tooltip explaining why, `:48-61,68`) is correct and prevents the exact failure mode ("approve an incomplete policy") the whole authoring layer exists to avoid. Draft → Needs Review → Approved → Active is stated in plain language at every screen (`:83`: *"Approving and activating are separate steps — approving records that this position is correct; activating makes it govern live contract review"*).

**Two gaps, both P2**: (1) approval history (`:91-104`) prints raw `from_status`/`to_status` with no translation (see §3 — the only unfixed instance in this otherwise-clean page); (2) there's no visual indicator on this page of whether an ACTIVE sibling exists and what specifically changed between this revision and the one it would supersede — a lawyer re-approving an edited position can't see a diff of what changed, only the new final state.

---

## 9. Test Policy

The mechanism is sound: real evaluator, real extractor, explicit "PREVIEW ONLY" badge (`playbook_position_preview.html:18-20`), no Contract or review record created. What's missing versus the task's target interaction:

- No "Your playbook" comparison panel — the result shows what was found and why, but never restates the position's own thresholds next to the finding the way the task's wireframe does (`Your playbook: Preferred 1× / Accept ≤2× / Negotiate ≤3×`). A lawyer has to remember what they configured to judge whether the result is sensible.
- No negotiation ladder visualization (this exact widget already exists and is well-built in `review.html`'s popover, `:458` — it is simply not reused here).
- The state badge is the raw-enum leak identified in §3.
- No link to "View evidence" beyond the plain matched-language block already shown.

**Recommendation**: this page should visually and structurally resemble a single finding popover from `review.html` (reusing `ladderHTML`/the state-badge translation once fixed) rather than being a separate, simpler design — the two experiences (testing a policy, reviewing a live finding) are the same mental model and should look like it, which also means fixing the vocabulary bug once fixes it in both places if the label dict is shared.

**Discoverability** is the dominant issue (§5) — the mechanism itself, once found, would likely satisfy the "major trust-building interaction" bar reasonably well.

---

## 10. Contract review — the highest-priority page

`review.html` (738 lines) is the most sophisticated page in the product: a sticky annotated-document + margin-map + finding-panel three-column layout, keyboard shortcuts (j/k/a/e/r/c/v/⌘⏎), a real deterministic-replay verify feature, and inline diff-based redline application. Several things are already right and should be preserved:

- **Only actionable states create findings** — passed/accepted policy checks are silent by design (`policy_enforcement.py:107`, `_ACTIONABLE_STATES` excludes `ACCEPT`/`ACCEPT_WITH_NOTE`/`NOT_APPLICABLE`). This already achieves "review by exception" for the policy layer specifically, which is the right default and should not be changed to show "31 passed" as a wall of green — see below for the one adjustment worth making instead.
- **Severity is color-coded consistently** (`.mark.sev-critical/high/medium/low`, `.mm-tick`, `.pli-dot`, `.pop-*` — all share the same four-color system, `review.html:58-69,81-83,107-109`) — a genuine, if narrow, hierarchy.
- **No confidence percentage for policy findings** (`cb` is null, `pop-conf` span renders empty) — correct, preserves the Phase 3 decision.
- **Redlining is fast**: Accept is one click, Reject requires (and gets) a reason, Edit is inline, and the applied change is written directly into the document view with a strike/insert pattern — this already approaches the task's "issue → understand → apply redline in seconds" target for the *accept* path.

**What's wrong, beyond the two P0 bugs already covered in §0**:

- **Findings of every kind are interleaved in one flat list** (`renderPanelList()`, `:421-442`) with no grouping by severity/state the way the task's target hierarchy (Prohibited/Must Redline dominate, then Negotiate/Needs Review, then a collapsed Acceptable section) proposes. A PROHIBITED liability finding and a low-severity rule-engine style-nit sit in the same undifferentiated list, ordered only by document position — a lawyer has no way to jump straight to "the one thing that could kill the deal" without scanning the whole list top to bottom.
- **No summary count of what was checked.** The topbar shows overall risk and a resolved/total count once decisions start being made, but there is no "42 policy checks: 5 flagged" framing anywhere — a lawyer landing on the page for the first time sees a list of N findings with no sense of how many clauses were checked in total, which matters for trust ("did it check indemnification? I don't see anything about it — is that because it's fine, or because nothing was configured?").
- **Policy state badges are the raw-enum leak** (§3) and sit in the same visual slot as the rule-engine severity label — a lawyer cannot tell at a glance "this came from the deterministic policy engine" vs. "this came from a pattern match," even though the two carry very different evidentiary weight (one is a reproducible legal-position comparison, the other is a keyword/regex hit).
- **The `rule_id`** is shown inline in the popover title (`:480`) competing for visual attention with the actual finding title.

**Recommendation** (design, not implementation): introduce a lightweight section header inside the finding-panel list — group by the four-tier severity bucket the task proposes (Prohibited/Must Redline first, Negotiate/Needs Review next, a collapsed "N checks passed, nothing to review" line last) — without changing what generates a finding in the first place (that logic is correct). Add one line to the topbar or a small badge per-finding distinguishing "Policy decision" from "Pattern match" (reusing the existing `finding_type_label` field, which is already computed server-side — `policy_enforcement.py:107` sets `"finding_type_label": "Policy Decision"` — and is simply not rendered anywhere in the template today).

---

## 11. Redlining

Already covered in §10's "what's right." The one clear improvement opportunity: **"Apply preferred redline" is not visually the dominant action even when approved fallback language exists.** Currently Accept/Edit/Reject/Comment are given equal visual weight (`.pop-btn` vs `.pop-btn.primary` — only `data-act="accepted"` gets the primary/green treatment, `:466`, which is *close* to right) — this is actually mostly correct already (Accept is styled primary), but there is no visual distinction between "accept the system's own fallback text" and "accept some other AI/rule-engine-suggested redline" — both look identical, when the former (an attorney-authored, pre-approved fallback clause) deserves more confidence-signaling than the latter (a generated suggestion).

---

## 12. Evidence and trust

The negotiation-ladder widget (`review.html:458`, `.pop-ladder`/`.ladder-step`) and the position-chip pair (our position vs. counterparty position, `:460-463`) are close to the task's target "why this decision" flow already — contract excerpt → detected position → your playbook → decision, shown compactly in one popover. What's missing to complete the picture the task describes:

- No explicit "Action" line separate from "Required action" text buried in the rationale — the redline/action IS shown, but not labeled as the terminal step of the reasoning chain the way the wireframe frames it.
- The controlling-provision/source line (`sourceHTML`, `:459`) is present but visually de-emphasized (small gray text) relative to how much trust work it's doing (it's the citation for a legal conclusion).
- **Determinism itself is never explained to the lawyer** — the Verify button (once fixed, see §0.2) is the *demonstration* of determinism but there's no one-line explanation anywhere of *why* that matters ("the same contract, run against the same approved playbook, will always produce the same result — nothing here depends on which day you upload it"). The task explicitly warns against "plastering DETERMINISTIC everywhere," and the current implementation actually errs the other way — it demonstrates determinism (well) but never names the concept, so a lawyer who doesn't click Verify never learns this is the product's core guarantee.

**Recommendation**: keep the current "evidence chain" shape (excerpt → position → playbook → decision → action), just make the Action line explicit and label the source citation with slightly more visual weight; add one sentence near Verify (not repeated everywhere) naming what determinism means for the lawyer, once per review rather than zero times.

---

## 13. Override and escalation

**No implementation exists.** Full detail already covered in §0.3/§0.4 and §2C of the research. To restate the concrete gap precisely: `main.py:2279-2284`'s own comment says "Policy overrides must never be silent," and the mechanism to make that true (`policy_original_recommendation`, stored on every policy-decision-finding's decision entry) is real and correctly captured — but it is read by nothing. It doesn't appear in `review.html`, and `review_workflow.build_audit_trail_text` (`review_workflow.py:175-201`) exports only `action`/`reason`/timestamp, not the original recommendation being overridden.

There is also no distinct interaction for the override *decision itself* — accepting a PROHIBITED finding uses the same "Reject" (with reason) flow as rejecting a false-positive rule-engine keyword match. A prohibited-liability override and a "this isn't actually a liability clause" dismissal look identical in the UI and in the exported record, even though one is a considered legal exception with real consequence and the other is correcting a tooling mistake.

**Recommendation**: for any finding where `finding_type == "policy_decision"` and the state is in `{PROHIBITED, ESCALATE, MUST_REDLINE}`, replace the generic Reject/Flag/Dismiss actions with a distinct "Override this policy decision" interaction:

```
Override playbook decision
Current decision:    PROHIBITED — Unlimited liability
Escalation required:  General Counsel        ← from position.escalation_approval_authority
Your decision:       [ Accept exception ▾ ]
Reason (required):   [_______________________________]
                      [Cancel]      [Confirm override]
```

Persist and render `policy_original_recommendation` on the finding panel after the fact ("Overridden — was: Prohibited"), and add it to `build_audit_trail_text`'s output. This closes the gap between the code's stated intent and its actual behavior with the smallest possible surface change — the data already exists; it only needs to be displayed and exported.

---

## 14. Visual hierarchy

Typography and spacing are consistent and professional throughout (Inter font, consistent `premium-card` treatment, disciplined `text-[#0F172A]`/`text-gray-500` two-tone hierarchy). The specific finding from §10 — a flat, ungrouped finding list — is the main structural hierarchy gap; severity is color-coded but not spatially grouped, so "everything has roughly equal visual weight" is a fair characterization of the finding *list*, even though individual finding severity coloring is well done. Buttons correctly use one primary color (`#4F46E5` indigo / `#059669` green-for-accept) with everything else neutral, avoiding the common internal-tool failure of every button being the same loud color.

**Accessibility gap, concretely**: `review.html` — the single most important page — has almost no ARIA/semantic markup on its dynamic surface. No `role`/`aria-live` on the finding panel (which replaces its content via `innerHTML` on every navigation, `:433,517`), no `aria-label` on `.mark` spans (which carry severity and title information conveyed only visually), the keyboard-shortcut overlay (`.kbd-overlay`) has no `role="dialog"` or focus trap, and the custom single-letter hotkeys (`j/k/a/e/r/c/v`) have no announced equivalent for a screen-reader user. `base_app.html`'s share modal *does* use `role="dialog" aria-modal="true" aria-labelledby="..."` correctly (`:477`) — proving the team knows the pattern — it simply wasn't applied to `review.html`'s popover/finding-panel, which updates far more dynamically and needs it more.

---

## 15. Vocabulary separation

The three vocabularies the task asks to keep distinct are, in practice, **already reasonably separated in the code's naming** (contract decisions vs. `POLICY_POSITION_STATUSES` vs. `POLICY_POSITION_FIELD_SOURCES` are three separate constants in `models.py`) but **blur together on screen** in exactly the places identified in §3: the review-page badge conflates "decision state" language with generic "severity" language in one visual slot (`SEV_LABEL[f.severity] || f.severity` fallback, `review.html:479`, used interchangeably with `f.policy_state`), and `position.status`/`h.from_status`/`h.to_status` (lifecycle) are rendered with the same casual `.replace('_',' ')|title` treatment as decision states, inviting a reader to treat them as the same kind of concept when they are not. Fixing the three label dictionaries proposed in §3 (`DECISION_STATE_LABELS`, `POSITION_STATUS_LABELS`, `SOURCE_TYPE_LABELS`/`APPROVAL_ACTION_LABELS`) as three visually-distinct dictionaries, rather than one shared "prettify an enum" filter, is itself most of the fix for this section.

---

## 16. Non-happy paths

| State | Where | Current behavior | Verdict |
|---|---|---|---|
| No playbooks | `playbooks.html:72-84` | Clear empty state with contextual copy depending on plan | Good |
| Empty/incomplete playbook | Workbench coverage bar shows 0%, cards show "Not set" | Adequate, but no "start here" CTA beyond the generic cards | P3 |
| No active policies at contract-review time | Not explicitly audited in this pass (no route/template surfaced it in the research) — worth verifying directly | **Unverified — flag for follow-up**, not claimed as a finding here |
| Unsupported clause types | N/A (six adapters cover the fixed set; not a runtime state) | N/A | — |
| Deterministic import: no evidence found | `playbook_import_review.html:21-26` | Clear message + link back to Workbench for manual entry | Good |
| AI import disabled | `playbook_ai_import.html:23-28` | Explicit message + link to deterministic import instead | Good — matches Phase 3's server-side-disable requirement |
| AI import: no candidates | Same page structure as deterministic (`clauses` empty) — inherits the same good empty state | Good |
| Conflicting source positions | `playbook_import_review.html:73-86`, evidence banner in edit page | Present, but not diffed (§7) | P2 |
| Evaluation error (Phase 4 failure isolation) | `policy_enforcement._error_finding` — produces a "Automated evaluation failed... requires manual review" finding, high severity | Correctly surfaces as a finding rather than failing silently, per Phase 4's own design | Good |
| Superseded policy | No explicit "this was superseded by revision X" UI found on the review or history screens — only the approval-history log implies it | **Gap** — worth a "Superseded" badge state, not just an absence from the Active list | P2 |
| Missing fallback / missing escalation authority | Both fields are optional at the form level; an ACTIVE position with no fallback text simply shows no redline at contract-review time (`f.redline` is falsy) and falls to the Flag/Dismiss action set | Functionally fine, but the Workbench card gives no warning that a clause is Active with no fallback configured — a lawyer wouldn't know until a contract actually needs one | P1 (ties to §5's card-expansion recommendation) |

---

## 17. Quantified friction

Click counts are given only where directly traceable through the route table; everything else is stated as an assumption.

| Workflow | Current friction | Steps/clicks (traced) | Proposed | Expected improvement |
|---|---|---|---|---|
| Create playbook | High — wrong system by default | `/playbooks` → `/playbooks/new` → submit (3) but lands in the **legacy** system; +1 more click to discover Workbench exists | 3-path chooser at creation time, same click count, correct destination | Eliminates a silent dead-end, not just clicks |
| Manual LoL setup | Low once found | Workbench card → edit → fill → save → submit-for-review → review → approve → activate (7 page loads) | Same — this sequence is legally meaningful and shouldn't be shortened | Convert Save+Submit into one action where the position is already complete (assumption: worth user-testing, not assumed correct) |
| Deterministic import | Low | Import page → upload → review page → per-clause confirm (3-4) | Same, plus inline conflict diff (§7) | Fewer clause-edit-page round-trips for conflicts specifically |
| AI import | Low, well-scoped | AI-import page → consent → upload → review (3) | Same | — |
| Resolve conflict | Medium — requires leaving the review page | Import review → clause edit page → re-answer (2 page loads) | Inline compare + resolve on the import-review page itself | Removes 1 page load per conflict |
| Approve/activate | Low, correct as designed | Review page → Approve → Activate (2 explicit clicks, by design) | Unchanged | — |
| Test policy | **Unknown discoverability cost** — assumption: many lawyers will not find this without training, given zero Workbench affordance | 1 click once found; 0 known path from Workbench today | Add Workbench card CTA | Assumption: materially higher usage; unverifiable without user testing |
| Review contract | Low per-finding, unknown aggregate | 1 click to open a finding (assumption: findable primarily by scrolling, not by priority) | Severity-grouped panel (§10) | Assumption: faster time-to-first-actionable-issue; needs measurement |
| Inspect evidence | Low | Evidence is inline in the open popover (0 extra clicks) | Unchanged | — |
| Apply redline | Very low | 1 click (Accept) | Unchanged | — |
| Override | **Not measurable — no distinct interaction exists** | N/A | New interaction, ~2 clicks (open finding → confirm override with reason) | Cannot regress below "does not exist" |
| Export | Low | 1 click ("Generate Negotiation Package") | Unchanged, add override data to the trail | — |

---

## 18. Prioritized findings

### P0 — lawyer can misunderstand policy, make the wrong decision, or cannot complete a core workflow

**P0-1 — Dual, disconnected playbook-creation systems**
- *Current*: `/playbooks/new` (`main.py:2550-2696`) creates a legacy `PolicyRule` via checkboxes; the Workbench/`PolicyPosition` system is only reachable afterward, by chance, via a second link on the playbooks list.
- *Why it's a problem*: a lawyer can complete "playbook creation" and believe their policy is fully configured while having touched only one of six clause types, through a form with a known unsafe-boolean pattern, with the real system undiscovered.
- *Proposed solution*: §4's three-path chooser as the actual creation entry point; retire the LoL section from `playbook_form.html`.
- *Expected impact*: removes the single largest gap between intended and implemented UX in the product.
- *Implementation complexity*: Medium — new template + route logic, no data-model or engine change; `/playbooks/{id}/edit` keeps serving metadata edits.
- *Regression risk*: Low if `/playbooks/new`'s existing POST handler is left intact for the "Build manually"/legacy-compat path and only the *entry template* changes.

**P0-2 — "Verify" is false for every policy-decision finding**
- *Current*: `main.py:2327-2356` replays only `rule_engine.analyze()`; policy `RULE_ID`s (e.g. `POLICY_LOL_CAP`) never match, so `verified` is always `false` and the UI states the finding "may be stale" (`review.html:535`) — which is never true, since it was never actually re-checked.
- *Why it's a problem*: this is the product's flagship deterministic-replay trust demonstration, and it actively produces a false negative on the class of finding it should be proudest of.
- *Proposed solution*: extend `/review/verify` to also re-run the appropriate `evaluate_*_policy` when `finding_type == "policy_decision"`, comparing against the pinned revision metadata already recorded by Phase 4 (`Contract.policy_revision_metadata_json`).
- *Expected impact*: converts a trust-destroying bug into the product's best trust-building moment for the majority of high-stakes findings.
- *Implementation complexity*: Medium — needs the pinned `policy_position_id`/`config_hash` from Phase 4's revision metadata to know which policy to replay against; logic exists, wiring does not.
- *Regression risk*: Low — additive branch in an existing endpoint; rule-engine verify path is untouched.

**P0-3 — No override/escalation UI**
- *Current*: no distinct interaction exists; `escalate_to` and `escalation_approval_authority` are computed/stored but never rendered; `policy_original_recommendation` is captured but never displayed or exported.
- *Why it's a problem*: overriding a PROHIBITED or ESCALATE decision — the highest-stakes action in the product — is indistinguishable in the UI from dismissing a false-positive keyword match, and the audit trail the code explicitly promises ("must never be silent," `main.py:2281`) does not reach the exported record.
- *Proposed solution*: §13's dedicated override interaction + surfacing `policy_original_recommendation` + adding it to `build_audit_trail_text`.
- *Expected impact*: closes a real legal/audit liability gap, not just a UX one.
- *Implementation complexity*: Medium — mostly template + `review_workflow.py` export changes; the data already exists end-to-end.
- *Regression risk*: Low.

**P0-4 — Test Policy has no Workbench affordance**
- *Current*: `playbook_workbench.html` cards have no test-policy CTA; the only link is `playbook_position_edit_base.html:124`, a small text link at the bottom of the edit page.
- *Why it's a problem*: the task explicitly frames Test Policy as "a major trust-building interaction," and the one page designed to be scanned in 30–60 seconds gives it zero visibility.
- *Proposed solution*: §5's `[Test policy →]` card addition.
- *Expected impact*: assumption (untested) — materially higher usage of an already-working feature.
- *Implementation complexity*: Low — one link addition to an existing template.
- *Regression risk*: None.

### P1 — major friction or trust problem

**P1-1 — Raw decision-state vocabulary leaks in three places** (`playbook_position_preview.html:41`, `review.html:235`, `review.html:479`) — see §3 for the full dictionary-based fix. *Impact*: legibility, not comprehension-blocking, but inconsistent with the product's otherwise-careful translation discipline. *Complexity*: Low (one shared dict + three call-site swaps). *Risk*: None.

**P1-2 — Workbench cards omit fallback/escalation/provenance** — a lawyer cannot answer "what will this enforce" from the Workbench alone, contradicting its stated single job. *Complexity*: Low-Medium (view-model already computes this data for the approval screen; needs threading into the card builder). *Risk*: Low.

**P1-3 — Findings list has no severity grouping** (`review.html:421-442`) — flat list undermines "review by exception" at scale on documents with many findings. *Complexity*: Medium (client-side grouping + a small header component; no server change needed since `policy_state`/`severity` already ride on each finding). *Risk*: Low.

**P1-4 — No visibility into whether an Active clause has a fallback/escalation authority configured** — a gap only discovered when a real contract needs one. *Complexity*: Low (extension of P1-2's card work). *Risk*: None.

### P2 — meaningful usability improvement
- Conflict resolution isn't a true side-by-side compare (§7).
- Inconsistent helper text across the six clause forms (§6).
- No "Superseded" state badge distinct from simple absence from the Active list (§16).
- Approval-history `from_status`/`to_status` unfiltered raw strings (§3, §9).
- No diff view when re-approving an edited-then-resubmitted position (§9).

### P3 — cosmetic/polish
- `rule_id` visual placement in the popover title competes with the finding title (§3, §10).
- Save-button caption doesn't warn that editing an Approved position reverts it to Draft (§6).
- No autocomplete/format guidance on jurisdiction free-text fields (§6).

---

## 19. Text wireframes

Sixteen wireframes covering the requested surfaces. These are intentionally close to what already exists — the product's bones are sound; the wireframes below are the audit's proposed *fixes*, not a rebuild.

**1. Playbooks list** — unchanged from current `playbooks.html`; each card's two links become "Workbench" (primary) and a small "Rename / edit template" (secondary, was "Edit").

**2. Create Playbook** — per §4's three-path chooser.

**3. Workbench** — per §5:
```
ACME VENDOR PLAYBOOK                                  [Import a template]
82% READY  ████████████░░░  5 Active · 1 Needs review · 0 Not configured
High-priority gaps: none

┌─────────────────────────────┐ ┌─────────────────────────────┐
│ LIMITATION OF LIABILITY ●ACTIVE│ │ INDEMNIFICATION  ⚠ NEEDS REVIEW│
│ Preferred 1× · Accept ≤2×    │ │ 4 of 6 positions established │
│ ✓ Fallback set · GC escalation│ │ 2 decisions needed           │
│ [Edit]        [Test policy]  │ │ [Finish setup]                │
└─────────────────────────────┘ └─────────────────────────────┘
```

**4. Clause authoring** — unchanged structurally; add consequence-explainer helper text to the 11 currently-bare tristate fields identified in §6.

**5. Deterministic import review** — unchanged; add the two-column conflict compare from §7 in place of the current stacked-excerpt conflict card.

**6. AI-assisted import review** — same page as (5); no separate design needed, this is already correctly unified.

**7. Conflict resolution** (inline card, replacing the current stacked list):
```
CONFLICT — Data breach treatment
┌───────────────────────┐  ┌───────────────────────┐
│ Main Agreement          │  │ DPA (Schedule B)        │
│ "...within the general  │  │ "...liability for data  │
│ liability cap..."        │  │ breach shall be         │
│                          │  │ unlimited..."            │
└───────────────────────┘  └───────────────────────┘
Which governs?  ( ) Main Agreement   ( ) DPA   ( ) Neither — decide manually
[Resolve]
```

**8. Approval** — unchanged, already matches the target (§9).

**9. Activation** — unchanged, already correct.

**10. Test Policy** — per §9, restyled to match a `review.html` finding popover:
```
Test this policy                              PREVIEW ONLY
[paste sample clause...........................] [Run test]

MUST REDLINE
What we found              Your playbook
General cap: 3× fees       Preferred: 1×
Fraud: uncapped            Accept without approval: ≤2×
Consequential: excluded    Negotiate up to: 3×
Preferred → Auto-accept → Negotiate → Escalate   (● Negotiate)
Why: 3× exceeds your automatic acceptance threshold but remains
within your approved negotiation range.
[View evidence]
```

**11. Contract Playbook Review** — per §10, with severity grouping added above the existing flat list:
```
ACME SERVICES AGREEMENT — PLAYBOOK REVIEW
6 policy checks · 5 findings need attention

NEEDS YOUR ATTENTION                                    5
▾ Not acceptable / Must redline (2)
  [existing finding rows, unchanged]
▾ Negotiate / Needs review (3)
  [existing finding rows, unchanged]
▸ 1 check passed — nothing to review
```

**12. Finding detail** — unchanged mechanically; policy_state now shows translated text and a small "Policy decision" chip distinct from rule-engine findings (reusing the already-computed but unused `finding_type_label`).

**13. "Why this decision?"** — unchanged shape, `escalate_to` line added when the state is ESCALATE:
```
Escalate to: General Counsel        ← new, from decision.escalate_to
```

**14. Redline interaction** — unchanged; Accept stays primary-styled; no new design needed.

**15. Override/escalation** — per §13's wireframe.

**16. Revision/history** — approval-history list translated per §3/§9, plus a "Superseded" badge on any position row that has since been replaced by a newer ACTIVE revision.

---

## 20. Golden paths

**A lawyer already has a written playbook**: Playbooks → Create → "Upload your legal playbook" (AI-assisted) → consent → upload → Import review (confirm Directly-established, resolve Needs-input/Conflicts) → per-clause Approve → Activate → done. Currently this path *exists* but starts from the wrong entry point (§4) — fixing the creation chooser makes this the shortest real path already implemented; no new mechanism is needed.

**A lawyer has only a standard contract template**: Playbooks → Create → "Upload a standard contract" (deterministic) → upload → Import review → same confirm/resolve/approve/activate sequence. Also already implemented end-to-end once entry is fixed.

**A lawyer has neither**: Playbooks → Create → "Build it yourself" → Workbench → six clause cards, fill each (reusing the existing, well-built tristate forms) → Approve/Activate each. Longest path, but each step is already well-designed individually (§6, §9); the length is inherent to genuinely configuring six clause types by hand and shouldn't be artificially shortened.

**Shortest safe path in all three cases**, once §4 ships: *Create playbook → choose a path → resolve what needs resolving → approve → activate → upload a contract → review by exception → redline → export.* Every step in that sentence already exists in the codebase today; the only missing connective tissue is the creation chooser and the Workbench's Test Policy link.

---

## 21. Five-lawyer usability test design

**Setup**: 5 commercial lawyers (mixed seniority, none previously exposed to TriageCounsel), one 60–90 minute session each, think-aloud protocol, minimal instruction ("here's a login, here's a sample template contract and a sample counterparty contract — get the counterparty contract reviewed against a policy you set up from the template").

**Tasks** (as specified) mapped to what to watch for:
1. Create/import a playbook — *watch whether they land on `/playbooks/new` and get stuck in the legacy form, or find the Workbench unassisted.*
2. Resolve one missing policy decision — seed one clause as NEEDS_REVIEW with an unanswered field.
3. Identify what TriageCounsel will enforce — ask them to describe it back in their own words; check against actual configured thresholds.
4. Activate it.
5. Test a clause — *do not tell them Test Policy exists; time-to-discovery is itself a metric.*
6. Review a counterparty agreement (seeded with at least one PROHIBITED, one NEGOTIATE, and one clean pass).
7. Identify the three most important issues — measure whether severity/grouping (once P1-3 ships) actually produces the right answer faster than the current flat list.
8. Explain why one decision occurred — success = they can name the contract language, the playbook threshold, and the resulting action without guessing.
9. Apply a redline.
10. Override one decision — *this task will currently fail outright since no override UI exists; run it as a baseline/control before P0-3 ships, then re-test after.*
11. Export.

**Metrics**: completion rate per task; time per task; misclicks (define as: click on a non-actionable element, or backtrack); requests for help (count + what triggered it); policy-configuration errors (an unintended value ends up in a saved position); time to first actionable issue on the review page; time to first completed redline; whether they open "View evidence"/"Why" before deciding, and on what fraction of findings; whether they can correctly restate why the system reached a decision (score 0/1/2 — wrong, partially right, fully right); a 1–5 trust rating collected post-task, not pre-task (avoid anchoring).

**Explicit pass/fail thresholds** (defensible ones only — the task warned against inventing unfounded ones):
- Task 1 (create/import): **fail** if the lawyer configures a playbook but never reaches the six-clause Workbench in the session — this is a binary outcome, not a judgment call, given P0-1.
- Task 6 (review by exception): **fail** if a lawyer cannot correctly identify the single most severe finding within 60 seconds of landing on the review page — this is directly testable against the "review by exception, not review everything" standard the task sets.
- Task 8 (explain why): **fail** if a lawyer cannot name the specific playbook threshold that produced the decision, even after opening the finding — this tests whether §12's evidence chain is legible.
- Task 10 (override): **not scored as pass/fail before P0-3 ships** — record as a known gap, not a usability failure of what exists.
- All other tasks: no invented numeric threshold; report completion rate and time distribution, and let the deployment operator judge sufficiency, consistent with this audit's own refusal (per Phase 4.1's precedent) to manufacture false precision.

---

## 22. Keep / Simplify / Merge / Move / Hide / Remove

| Component | Verdict | Why |
|---|---|---|
| Tristate boolean controls | **KEEP** | Correctly prevents the unanswered-vs-No bug; the product's best single UI decision |
| Import-review four-bucket vocabulary | **KEEP** | Already matches the target language; don't touch the copy |
| Approval-screen plain-English summary | **KEEP** | Best-executed screen in the product |
| `review.html` margin-map + sticky finding panel | **KEEP** | Genuinely good information architecture for long documents |
| Negotiation-ladder widget | **KEEP**, reuse elsewhere (Test Policy, §9) | Already well-built, currently under-used |
| `/playbooks/new` legacy LoL section | **REMOVE** from the creation flow (§4); the surrounding metadata form can stay for `/edit` | Duplicates and can drift from the real system |
| Workbench card content | **SIMPLIFY the label, EXPAND the data shown** (§5) | Currently under-informative for its stated job |
| Decision-state/position-status raw enum rendering | **HIDE via translation dicts** (§3) | Not wrong, just unfinished |
| Conflict-resolution stacked-excerpt list | **MERGE into a compare view** (§7) | Information exists, layout doesn't help |
| Override mechanism | **currently absent — this is a build, not a KEEP/REMOVE call** | See P0-3 |
| Verify button copy ("Re-ran all 189 rules") | **SIMPLIFY once fixed** — don't hardcode "189" (a magic number that will drift and, once policy replay is added, will be wrong on its face) | Use a generic "re-ran the analysis" phrasing that doesn't need updating when rule counts change |
| `rule_id` in the popover title | **MOVE** to a de-emphasized caption (§3) | Competes with the actual finding title |

---

## 23. Implementation phases (proposed — not implemented)

**UX-A — Information architecture + terminology**
- Files: `playbook_authoring.py` (add `POSITION_STATUS_LABELS`, `DECISION_STATE_LABELS`, `SOURCE_TYPE_LABELS`, `APPROVAL_ACTION_LABELS`, `FIELD_STATUS_LABELS` alongside the existing `FIELD_LABELS`/`CLAUSE_TYPE_LABELS`); `playbook_position_edit_base.html`, `playbook_position_review.html`, `playbook_position_preview.html`, `playbook_workbench.html`, `review.html` (swap raw `.replace('_',' ')` calls for dict lookups).
- Backend/view-model: none beyond the new dicts (pure presentation).
- Persistence: none.
- Tests: template-rendering assertions that no raw enum string appears in rendered HTML for a representative fixture of each status/state value (extends the existing `test_playbook_workbench.py` pattern).
- Regression risk: Very low — additive dicts, mechanical call-site swaps.
- Expected impact: closes §3 in full; foundational for every later phase's copy.

**UX-B — Playbook creation + Workbench**
- Files: new template for the three-path chooser; `main.py`'s `/playbooks/new` GET/POST split into a thin "name it" step + redirect; `playbook_workbench.html` card expansion (fallback/escalation/provenance/Test Policy link); `playbook_workbench.py`'s card-building function extended to surface `summarize_position`'s output already computed for the approval screen.
- Backend/view-model: `playbook_workbench.py`'s workbench route needs to call the existing `summarize_position` per card (already exists, currently only called from the review route).
- Persistence: none required — no new data, only more of the existing `PolicyPosition` surfaced.
- Tests: extend `test_playbook_workbench.py` for card content assertions; new creation-flow integration tests.
- Regression risk: Low-Medium — touches a heavily-used entry route; needs care to keep `/playbooks/new`'s existing POST contract for any external links/bookmarks.
- Expected impact: resolves P0-1 and P0-4, the two highest-severity findings that don't require new data model work.

**UX-C — Manual authoring**
- Files: the six `policy_position_fields/*.html` templates (add missing helper text), `playbook_position_edit_base.html` (save-button caption).
- Backend/view-model: none.
- Persistence: none.
- Tests: none beyond existing template tests; this is copy-only.
- Regression risk: None.
- Expected impact: P2-level consistency improvement.

**UX-D — Import review**
- Files: `playbook_import_review.html` (two-column conflict compare); `playbook_workbench.py`'s conflict-bucketing logic may need to expose both excerpts as a structured pair rather than a flat list (check `_field_evidence_summary` — likely already has both excerpts available, needs a small view-model reshape, not new data).
- Persistence: none.
- Tests: extend `test_playbook_import_workflow.py`/`test_playbook_ai_import_workflow.py` for the new conflict-card shape.
- Regression risk: Low.
- Expected impact: closes the one real gap in an otherwise-strong page (§7).

**UX-E — Contract exception review**
- Files: `review.html` (severity-grouped finding-panel list; `finding_type_label` badge; `escalate_to` line in the popover).
- Backend/view-model: `policy_enforcement.py`'s `_finding_from_decision` needs `escalate_to` added to the finding dict (currently omitted despite being on `PolicyDecision`) — this is the one place in the whole audit where a (small, additive) non-template change is needed.
- Persistence: none.
- Tests: extend the Phase 4 finding-injection tests to assert `escalate_to` is present when state is ESCALATE.
- Regression risk: Low — additive dict key, no behavior change to `evaluate_*_policy` itself.
- Expected impact: directly enables P0-3's escalation-authority display; resolves P1-3.

**UX-F — Evidence + redline + override**
- Files: `review.html` (override interaction, `policy_original_recommendation` display), `review_workflow.py` (`build_audit_trail_text` — add original-recommendation line), `main.py`'s `/review/verify` (extend to replay policy decisions using Phase 4's pinned `policy_revision_metadata_json`).
- Backend/view-model: the verify-extension is the one genuinely new piece of logic in this whole plan — it needs to look up the pinned `policy_position_id`/`config_hash` from `Contract.policy_revision_metadata_json`, rebuild the policy rule via `build_policy_rule_for_enforcement`, and re-run the same `evaluate_*_policy` used at review time, comparing the resulting decision's `state` (and ideally full `as_dict()`) against what's stored.
- Persistence: none — reads existing Phase 4 columns.
- Tests: new tests specifically for policy-decision verify (currently zero coverage of this path, since it's currently entirely broken and untested-because-unbuilt).
- Regression risk: Medium — touches the review page's most-used interactive endpoint; must not regress the existing rule-engine verify path (keep as two branches on `finding_type`, not a rewrite).
- Expected impact: resolves P0-2 and P0-3 together — the two most severe trust/correctness findings in the audit.

**UX-G — Accessibility/responsive/polish**
- Files: `review.html` (ARIA roles/live regions on the finding panel and popover, focus trap on the keyboard-shortcut overlay, `aria-label`s on `.mark` spans); spot-check `playbook_workbench.html`/clause forms for label association (largely already correct via `<label for=...>`, per the base-template pattern).
- Backend/view-model: none.
- Persistence: none.
- Tests: none currently exist for accessibility in this codebase; consider adding automated `axe-core`-style checks to the existing Playwright/browser test infrastructure if one exists, or manual audit checklist as a lighter-weight starting point.
- Regression risk: Low — additive attributes only.
- Expected impact: unmeasured without dedicated accessibility testing, but closes a category (§17) that current usability testing (§20) would not surface with sighted, mouse-using participants.

**Suggested order**: UX-A first (foundational, zero risk, unblocks clean copy everywhere else) → UX-B and UX-E in parallel (the two P0-heaviest phases, independent files) → UX-F (depends on UX-E's `escalate_to` plumbing) → UX-C and UX-D (lower urgency, no dependencies) → UX-G last (benefits from a stable DOM structure in `review.html`, which UX-E will have just changed).

---

## 24. Final recommendation

### Current UX score /10

| Area | Score | Why |
|---|---|---|
| Playbook creation | **3** | Wrong system by default; real system undiscoverable without luck |
| Workbench | **6** | Good coverage summary, under-informative cards, no Test Policy link |
| Manual authoring | **8** | Best-in-class tristate pattern, minor helper-text inconsistency |
| Import review | **8** | Vocabulary and structure already match the target closely |
| Approval/activation | **9** | The strongest screen in the product |
| Test Policy | **5** | Sound mechanism, near-zero discoverability, weak comparison UI |
| Contract review | **6** | Strong information architecture undermined by the Verify bug and flat finding list |
| Evidence/trust | **6** | Good evidence chain, undermined by the same Verify bug and unexplained determinism |
| Redlining | **8** | Fast, clear, well-built |
| Override/escalation | **1** | Does not functionally exist |
| **Overall** | **5.5** | A strong deterministic core and a surprisingly well-designed authoring lifecycle, let down by exactly the surfaces where trust and legal accountability matter most |

### Biggest reason a lawyer would abandon the product today
**The Verify button lies to them about policy decisions** (P0-2). A lawyer who tries the product's own "prove it's deterministic" feature on the finding type that matters most will be told the finding might be stale — the single fastest way to destroy the trust this entire architecture exists to build, on the first real test a skeptical lawyer would run.

### Biggest reason a lawyer would pay for the product
**The approval/activation flow and the deterministic policy engine underneath it are real.** `playbook_position_review.html`'s "What this policy will enforce" screen, backed by an engine that genuinely reproduces the same decision every time (once Verify is fixed to prove it for policy findings, not just rule-engine findings), is a legitimate, differentiated capability — "you approve legal positions, not database state" is already true of the implementation, not just the pitch.

### Top 5 changes before design-partner demos
1. Fix Verify for policy decisions (P0-2) — non-negotiable before showing this to a skeptical lawyer.
2. Fix the creation entry point (P0-1) — a demo that starts on `/playbooks/new` today demos the wrong product.
3. Build the override interaction (P0-3) — lawyers will ask about this in the first five minutes of any real demo.
4. Add the Workbench Test Policy link (P0-4) — cheap, and it's the feature most likely to win the room once seen.
5. Fix the three raw-enum leaks in `review.html`/`playbook_position_preview.html` (P1-1) — five minutes of work, visible in every screenshot.

### What should explicitly wait until after lawyer testing
- The severity-grouped finding list (§10/P1-3) — the current flat list may already work fine for typical finding counts; group it only if usability testing (§21, Task 7) actually shows lawyers missing the most severe issue.
- The conflict-resolution two-column redesign (§7/P2) — the current stacked-list version is functional; don't invest in a compare UI until testing shows lawyers actually struggle with it.
- Scaling the Workbench beyond six cards (§5's filter/search idea) — speculative until Batch B actually adds clause types; do not build ahead of that need.
- Any change to the tristate/ladder authoring pattern — it's already good; resist the urge to "improve" it without a specific observed failure.
- Accessibility work beyond the minimum ARIA additions in UX-G — invest further only if a screen-reader user is part of the design-partner pool or explicitly required by a customer's procurement process.
