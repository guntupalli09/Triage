# Playbook Authoring UX & Architecture — Design Report

Status: **design only, nothing implemented**. Revised after review — see
"Revisions from review" below for what changed and why; the rest of the
document has been updated in place rather than left to contradict this
note. This closes out the policy-engine
architecture phase (Liability, Indemnification, Termination, Confidentiality,
Assignment, Governing Law — six adapters, one shared core, `benchmarks/
policy_engine_core_architecture_report.md` and `benchmarks/duplication_
promotion_review.md`) and defines the next phase: making those six engines
usable by a lawyer who has never seen `PolicyRuleLike` and never will.

Per instruction, no Batch B clause types and no changes to the six existing
policy engines are proposed here. Everything below is new authoring-layer
architecture that *consumes* the six engines as a fixed, already-verified
substrate — extraction functions, `PolicyDecision`, decision states, and the
`*PolicyRuleLike` Protocols are treated as read-only inputs to this design,
not things this document revises.

### Revisions from review

Five changes made after the first draft was reviewed:

1. **No inferred negotiation ladders from a single template data point**
   (§5.2). A template stating "2x fees" is evidence of the preferred
   position only. It is not evidence of an acceptable range, a negotiate
   ceiling, or an escalation threshold. The proposal builder no longer
   guesses those; unestablished ladder fields are surfaced as `NOT
   ESTABLISHED` and the UI asks the lawyer directly.
2. **No confidence scores in the lawyer-facing UI** (§3.3, §4.2, §2.5.1).
   Replaced with categorical provenance: *Extracted from source* /
   *Proposed from source* / *Entered by lawyer* / *Conflicting sources* /
   *Not established*. Bulk approval is gated on direct source evidence +
   schema validity + no conflicts + no unresolved dependencies, not a
   numeric threshold.
3. **The LLM privacy boundary is now an explicit, named product decision**
   (§5.3), not an implementation detail: "Deterministic/private import"
   (Path 2, no LLM, on by default) vs. "AI-assisted playbook import"
   (Path 1, explicit opt-in per use, and disable-able org-wide).
4. **One document upload, explicit dual-use checkboxes** (§8.2), not two
   separate uploads for the same file.
5. **Workbench coverage indicator added** (§3.2) — a playbook-level
   coverage bar and high-impact-gap list, framed for when Batch B expands
   the number of supported clause types.

The phased implementation order (§10) is also revised: manual authoring
(all six clause types) now ships before either import path, and the two
import paths are reordered so deterministic/private import ships before
AI-assisted import.

---

## 1. Current-State Assessment

Read directly from the codebase before writing anything below (models.py,
main.py, playbook_form.html, review.html, rules_engine.py, playbook_engine.py,
encryption.py, audit_log.py, review_workflow.py, extract_text_from_file,
evaluator.py, LLM_BOUNDARY.md).

### 1.1 What exists today

**One clause type is wired end-to-end; five are orphaned.** `PolicyRule`
(`models.py:206-256`) is a real table, but only `clause_type =
"limitation_of_liability"` is ever constructed (`main.py:2625`,
`_upsert_liability_policy_rule`). `playbook_form.html` has exactly one
clause section — "Enforce a Limitation of Liability policy" — with raw
technical fields (`lol_preferred`, `lol_acceptable_max`,
`lol_negotiate_max`, `lol_required_exceptions`, ...) that mirror
`PolicyRule` columns one-to-one. Indemnification, Termination,
Confidentiality, Assignment, and Governing Law exist as complete, tested,
benchmarked Python modules with their own `*PolicyRuleLike` Protocols, but
**no database column backs any of their fields, no route ever constructs
one, and no template ever renders a form for one.** `main.py` imports only
`liability_policy_engine`.

**Two parallel, independent comparison mechanisms already exist and must
both keep working:**

1. **Template-findings diff** (legacy, pre-dates the six policy engines):
   `Playbook.template_text` → `rules_engine.analyze()` →
   `Playbook.template_findings_json` (cached once, at playbook save time).
   On contract upload, `playbook_engine.PlaybookEngine.compare()` does a
   **rule-ID set diff** between the contract's findings and the template's
   findings → `Contract.deviations_json` (added risks / missing
   protections / shared findings), rendered only on `results.html`, never
   on `review.html`.
2. **Deterministic policy decision** (the six engines): `apply_liability_
   policy(...)` runs the one wired clause type against the contract text
   and the playbook's `PolicyRule` row, producing a `PolicyDecision` per
   clause type, stored in `Contract.policy_decisions_json`, surfaced as a
   banner + a specially-styled finding card in `review.html`.

These are unrelated: one is a keyword-rule-ID set difference against a
cached snapshot of a template document; the other is a typed, directional,
threshold-classified decision against a structured policy. A lawyer today
sees deviations on one page and the (single) policy decision on another,
with no visible relationship between them.

**Lifecycle: none.** Neither `Playbook` nor `PolicyRule` has a status
column. `PolicyRule.version` is an integer that no code path ever
increments — it is a stub, not a history mechanism. A `PolicyRule` row is
authoritative the instant it's saved; there is no draft state, no review
gate, no distinction between "the lawyer typed this" and "nothing has
verified this yet."

**Overrides exist, but only at the per-finding review level, not the
policy level.** There is no `PolicyOverride` table. What exists is
`Contract.review_decisions_json` (`review_workflow.py`): when an attorney
accepts/edits/rejects/flags/dismisses a `policy_decision` finding during
contract review, the system additionally stamps `policy_original_
recommendation` so the deterministic verdict is preserved alongside the
human's action, `decided_by`, `decided_at`, and (if edited) the redline
text. This is a real, working discipline — it is scoped to *reviewing a
contract*, not to *approving a policy*. There is no equivalent mechanism
for "a human confirmed this policy position is correct" at authoring time.

**Extraction is deterministic by default, LLM-walled-off by design.**
`extract_text_from_file()` (PDF via PyPDF2, DOCX via python-docx paragraphs
only — no tables/headers/footers, no OCR) feeds `rules_engine.analyze()`
(regex/keyword) and, separately, each of the six policy engines' own
`extract_*_facts()` functions (also regex, no LLM). `evaluator.py`'s LLM
call is architecturally forbidden from ever seeing contract text or
detecting anything — it only *explains* findings the deterministic layer
already produced, receives only fixed rule strings plus one sanitized
`matched_excerpt` per finding, and its output is validated to reference
only pre-identified findings (`LLM_BOUNDARY.md`). **This is the single most
important constraint on this design**: any LLM use this document proposes
must be a new, narrower, equally-enforced boundary — not a relaxation of
the existing one.

**Encryption and audit are solid, general-purpose primitives already
sufficient for this feature.** `EncryptedText`/`EncryptedJSON` (AES-256-GCM
envelope, key rotation via `ENCRYPTION_KEYS`/`ENCRYPTION_KEY_CURRENT`)
already encrypt `Playbook.template_text`, `template_findings_json`, and
`PolicyRule.fallback_text`. `AuditLog` is a generic, append-only,
actor/target/event/detail log already used for playbook create/edit/delete.
Both extend cleanly to new tables without new infrastructure.

### 1.2 What this means for the design

- The six engines and their Protocols are the **destination format** —
  correct, tested, not to be touched. The job here is building everything
  *before* a `PolicyRuleLike`-shaped object exists: how a lawyer gets one
  into existence without knowing what a Protocol is.
- The legacy template-findings/deviations mechanism cannot be silently
  replaced — it has to be explicitly migrated or explicitly kept running
  in parallel, visibly, forever if needed (see §8).
- There is no policy-level approval primitive to build on. It has to be
  designed from scratch, but can closely mirror the existing review-decision
  discipline (`decided_by`/`decided_at`/original-value-preserved) that
  already works and that lawyers using the product have already seen.
- Five-sixths of the "clause card" UI, routes, and data columns this
  document proposes are net-new, not extensions of existing UI. The one
  Liability form in `playbook_form.html` should be treated as the thing
  being replaced by the new pattern, not as a template to copy five more
  times (it's raw-field UX, exactly what this redesign exists to remove).

---

## 2. Lawyer Workflows

Four workflows, all converging on the same clause-card review surface.

### 2.1 Start a new playbook

1. Lawyer clicks "New Playbook," names it, picks a contract type (existing
   field, unchanged).
2. Chooses a creation path — this is a fork, not a wizard the lawyer must
   step through linearly:
   - **"I have a playbook document"** → Path 1 (§2.2)
   - **"I have a template/preferred contract"** → Path 2 (§2.3)
   - **"I'll set positions myself"** → Path 3 (§2.4)
   - Any combination — a lawyer can do all three for the same playbook
     (e.g. upload a template contract for Liability and Confidentiality,
     then manually configure Governing Law, then later upload a playbook
     memo that proposes updates to Indemnification). The playbook is a
     bucket of six independent clause positions, each with its own
     lifecycle; the creation path is a per-clause-position provenance
     tag, not a whole-playbook mode.
3. Lands on the **Playbook Workbench** (§3.2) — six clause cards, each
   showing its current lifecycle state.

### 2.2 Path 1 — Upload an existing legal playbook

1. Upload a document (Word/PDF/text) that is *prose describing legal
   positions* — a firm's internal negotiation playbook, an outside
   counsel memo, a redline-standards document. This is not a contract;
   it's a document *about* contracting positions.
2. System extracts text, runs the bounded LLM proposal step (§5.3) against
   it, and produces zero or more **inferred** clause-card proposals — one
   attempt per clause type the document seems to address. A document that
   only discusses Liability and Confidentiality produces two proposals and
   four untouched (still-empty) clause cards, not six low-confidence
   guesses.
3. Lawyer lands on the Workbench with a banner: "4 positions proposed from
   your playbook document — review before they take effect." Every
   proposed field is visibly paired with the source sentence(s) it came
   from (§6, evidence).
4. Lawyer reviews via bulk approval + per-card editing (§2.5).

### 2.3 Path 2 — Upload a preferred/template contract

1. Upload an actual contract — the org's own template, or a heavily
   favorable prior deal the lawyer wants to use as the standard.
2. System runs the six `extract_*_facts()` functions (deterministic,
   already-shipped, unmodified) against the document. For each clause
   type the document actually addresses, this produces **extracted
   facts** — what the document's own language actually says (e.g. "the
   template's Section 12 caps liability at 2x fees, excludes data
   breach and IP infringement from that cap").
3. Those facts are run through a **proposal builder** (new, §5.2) that
   populates only the fields the document actually establishes — e.g.
   `preferred_multiplier = 2x` (what the template says, `EXTRACTED`).
   Fields the template gives no evidence for — `acceptable_max`,
   `negotiate_max`, escalation thresholds — are **not** guessed. They are
   written as explicit `NOT ESTABLISHED` fields that the Needs-Review
   queue surfaces with a direct question ("Your template establishes the
   preferred position. How far may negotiators deviate?").
4. Clause cards distinguish extraction (what the document says, exact
   quote, `EXTRACTED`) from gaps (`NOT ESTABLISHED`, nothing proposed,
   nothing to silently accept) — see §6.
5. Same bulk-approval flow as Path 1, but bulk approval never closes a
   `NOT ESTABLISHED` field — those always require a lawyer's answer.

### 2.4 Path 3 — Build manually

1. Lawyer opens a clause card directly from the Workbench ("Configure
   Confidentiality") with no source document at all.
2. Fills in plain-English controls (§3.3/§7) — sliders, toggles, tag
   pickers, never a raw field name, never a JSON blob.
3. Because there is no machine proposal to confirm, manual entry skips
   `NEEDS_REVIEW` entirely: `DRAFT` while incomplete, `APPROVED` the
   moment the lawyer explicitly finishes and confirms the card (the
   lawyer authored it directly — there is nothing separate to "review").

### 2.5 Reviewing, approving, activating

1. **Bulk approval** for anything the system doesn't need the lawyer to
   inspect field-by-field: "Approve all clean positions" approves every
   `NEEDS_REVIEW` clause card whose *every* field satisfies **all** of:
   direct source evidence (`EXTRACTED`), valid against the clause type's
   schema, no conflicting proposal from another source (§5.4), and no
   `NOT ESTABLISHED` dependency left open. This is a categorical bar, not
   a numeric confidence threshold — see the note on confidence in §4.2.
   One action, one confirmation showing exactly what's being approved
   (never a silent bulk action).
2. **Clause-level editing** for anything the lawyer wants to inspect or
   change: open the card, see the source evidence next to each field,
   adjust, save. Editing a field marks that specific field
   `lawyer_confirmed` regardless of its original source.
3. **Needs-review queue**: anything low-confidence, contradictory (e.g.
   two different template documents disagreed), or simply never
   addressed by any source document surfaces in a single cross-clause
   list so a lawyer can process leftovers without hunting through six
   cards.
4. **Activation**: once a clause card is `APPROVED`, the lawyer (or an
   org policy requiring a second approver, see §6.4) activates it. Only
   `ACTIVE` clause positions are used by `evaluate_*_policy()` during
   contract review. A playbook can be "live" with some clauses `ACTIVE`
   and others still `DRAFT`/`NEEDS_REVIEW` — partial activation is a
   first-class, expected state, not an error condition.

---

## 3. Proposed Information Architecture

### 3.1 Object model, conceptually (not yet the DB schema — see §4)

```
Playbook
 └─ PolicyPosition (one per clause type, 0-6 present)
     ├─ lifecycle status (DRAFT / NEEDS_REVIEW / APPROVED / ACTIVE)
     ├─ shared fields (contract_side, escalation authority, fallback text)
     ├─ clause-specific config (the *PolicyRuleLike fields, plain-English-labeled)
     ├─ PolicyPositionField[] — one row per individual field, each carrying:
     │    - value (or none, if status is NOT_ESTABLISHED)
     │    - source: EXTRACTED | INFERRED | MANUAL
     │    - status: ESTABLISHED | NOT_ESTABLISHED | CONFLICTING (categorical, no score)
     │    - evidence (source document + excerpt span, if any)
     │    - confirmed_by / confirmed_at (once a lawyer has looked at it)
     └─ PolicyPositionApproval[] — append-only approval/activation history
```

A `PolicyPosition` is the authoring-side analogue of today's `PolicyRule`
row, extended with lifecycle and provenance. The field-level granularity
(`PolicyPositionField`) is what makes "extraction vs. inference vs.
manual," per-field provenance, and per-field evidence possible — a clause
card is not one blob with one score, it's a set of independently sourced
facts that happen to be grouped by clause type for review.

### 3.2 The Playbook Workbench (replaces the current single-page `playbook_form.html`)

One page per playbook, a coverage summary above a fixed grid of clause
cards (not a form to scroll through — a dashboard):

```
Acme Vendor MSA

Policy coverage
████████████████░░  82%

Active policies        4
Needs review            1
Not configured           1

High-impact gaps
⚠ Indemnification      Needs review — 3 fields need your input
○ Assignment            Not activated
```

This is deliberately a coverage/gap summary, not a raw "5/6 configured"
count — it is the surface that has to keep making sense as the number of
supported clause types grows past six (Batch B and beyond), so it is
framed here as "how much of what we support is actually governing this
playbook" rather than a fraction tied to today's specific clause count.
"High-impact gaps" ranks unconfigured/unreviewed positions by clause type
importance (a fixed, documented ranking — not inferred), so a lawyer
scanning the Workbench sees what's missing that matters most, not just
what's missing.

```
┌─────────────────────────────────────────────────────────────┐
│ Playbook: Acme Vendor MSA Playbook          [Activate All ▾] │
│ 4 Active · 1 Needs Review · 1 Not Configured                 │
├───────────────┬───────────────┬───────────────┬─────────────┤
│ Liability      │ Indemnification│ Termination   │ Confidentiality│
│ ● ACTIVE       │ ⚠ NEEDS REVIEW │ ○ NOT SET     │ ● ACTIVE       │
│ 2x fees        │ 3 fields need  │ Configure →   │ Mutual, 5yr    │
│ [Open]         │ your review    │               │ [Open]         │
├───────────────┼───────────────┼───────────────┼─────────────┤
│ Assignment     │ Governing Law  │                │                │
│ ● DRAFT        │ ● ACTIVE       │                │                │
│ Not activated  │ Delaware       │                │                │
│ [Open]         │ [Open]         │                │                │
└───────────────┴───────────────┴───────────────┴─────────────┘
```

Each tile: clause name, lifecycle badge, one-line plain-English summary of
the current position (not a field dump — "2x fees" not
"preferred_multiplier: 2.0"), an "Open" action. A tile in `NOT_SET` state
offers the three creation paths directly (upload playbook excerpt / upload
template / configure manually) scoped to just that clause type, for the
common case of filling one gap rather than re-running a whole-document
import.

### 3.3 The Clause Card (detail view, one per clause type)

Three regions, top to bottom:

1. **Position summary strip** — the plain-English ladder, always visible,
   never requiring a scroll to understand "what does this policy say":
   `Preferred → Acceptable → Negotiate → Escalate → Prohibited`, rendered
   as a horizontal ladder (reusing the same visual language `review.html`
   already uses for the negotiation-ladder display during contract
   review — a lawyer configuring the policy and a lawyer later seeing it
   applied see the same shape).
2. **Field groups**, plain-English labeled (§7 has the full mapping per
   clause type), each field showing:
   - Its current value (editable in place), or, if the field has no
     established value yet, an explicit `Not established` state with an
     inline prompt for the lawyer to answer
   - A provenance chip using categorical labels only, never a numeric
     score: `Extracted from source` / `Proposed from source` / `You
     entered this` / `Conflicting sources` / `Not established` (§4.2 has
     the full rationale for why this is categorical, not a confidence
     percentage)
   - For extracted/proposed fields, an expandable evidence panel: source
     document name, the exact excerpt, and (for template-contract
     extraction) the same kind of controlling-provision citation
     `review.html` already renders for `PolicyDecision.controlling_provision`
3. **Approval bar** — current lifecycle state, who last touched it, and
   the single action available at each state (`Mark reviewed` →
   `Approve` → `Activate`), never more than one primary action visible
   at once.

### 3.4 Cross-clause Needs-Review queue

A single filtered list, reachable from the Workbench header, showing every
`PolicyPositionField` across all six clause types still awaiting
confirmation, grouped by playbook. This is the "process the leftovers"
surface — a lawyer working through Path 1/2 imports doesn't have to open
six cards to find the three fields nobody's looked at yet.

---

## 4. Data-Model Changes

Three real design choices, each argued rather than asserted.

### 4.1 How to store clause-specific config: one JSON column, not 40 sparse columns, not EAV

Three options considered:

- **(A) One column per field across all six engines' Protocols** (~40
  nullable columns on `PolicyRule`). Rejected: extremely sparse (a
  Governing-Law position uses ~6 of 40 columns), every future clause type
  (Batch B) requires a migration, and it re-creates exactly the
  "technical field name as UI" problem this project exists to remove —
  it's the current Liability-only pattern, just six times wider.
- **(B) A fully generic EAV table** (`PolicyPositionField(policy_position_id,
  field_name, field_value, ...)`), clause-type-agnostic. Rejected: loses
  typing entirely, makes "does this position pass its engine's Protocol"
  unverifiable at the database level, and every read requires
  reconstructing a typed object from loose rows — more moving parts than
  the problem needs.
- **(C, chosen) A small set of real typed columns for the fields every
  clause type shares** (`contract_side`, `escalation_approval_authority`,
  `fallback_text` — already exist on `PolicyRule` today) **plus one
  `config_json` column holding the clause-specific fields as a typed
  dict**, validated at write time against a per-clause-type schema
  (reusing each engine's own `*PolicyRuleLike` Protocol as the source of
  truth for what's valid — no new schema to maintain separately from the
  engines). A thin per-clause-type **policy rule builder** function
  (`build_liability_policy_rule(position) -> object matching
  PolicyRuleLike`, one per engine, six total, new code, not a change to
  the engines) converts a `PolicyPosition` row into the exact object each
  `evaluate_*_policy()` function already expects — the same pattern the
  benchmark harnesses already use (`FakePolicy` dataclasses in each
  `tests/test_*_policy_engine.py`), just promoted from test fixture to
  production adapter.

  This keeps the table narrow, keeps typing enforceable (validate
  `config_json` against the Protocol's field list and types on every
  write, reject unknown fields), and means a Batch B clause type needs
  zero schema migration — only a new builder function, a new clause-card
  UI section, and a new field-mapping entry (§7's pattern extends without
  new columns).

### 4.2 New tables

```
PolicyPosition
  id, playbook_id (FK), clause_type,
  status: DRAFT | NEEDS_REVIEW | APPROVED | ACTIVE | ARCHIVED
  contract_side, escalation_approval_authority,
  fallback_text (EncryptedText),
  config_json (EncryptedJSON)  -- clause-specific fields, see 4.1
  source_type: NONE | UPLOADED_PLAYBOOK | UPLOADED_TEMPLATE | MANUAL | MIXED
  created_at, updated_at,
  activated_at, activated_by_user_id (nullable FK)
  UNIQUE(playbook_id, clause_type)

PolicyPositionField
  id, policy_position_id (FK), field_name,
  value_json (EncryptedJSON, nullable)  -- null when status=NOT_ESTABLISHED
  source: EXTRACTED | INFERRED | MANUAL
  status: ESTABLISHED | NOT_ESTABLISHED | CONFLICTING
  rank_score: Float, nullable  -- internal-only, for proposal ordering;
                               -- never rendered to a lawyer, never a
                               -- factor in bulk-approval eligibility (see
                               -- note below)
  evidence_document_id (nullable FK -> PlaybookSourceDocument)
  evidence_excerpt (EncryptedText, nullable)
  evidence_start_index / evidence_end_index (nullable)
  confirmed_by_user_id (nullable FK), confirmed_at (nullable)
  superseded_by_field_id (nullable, self-FK) -- see 4.3, history
  created_at
```

**No lawyer-facing confidence score.** The first draft of this design had
a `confidence: Float` column and proposed bulk-approving anything above a
configurable threshold. Removed. TriageCounsel's whole premise is
deterministic, defensible decision-making — putting "87% confidence" in
front of a lawyer during policy authoring undercuts that premise at the
one moment it matters most (deciding what becomes an enforceable rule).
Two things replace it:

1. **Categorical status**, shown to the lawyer: `ESTABLISHED` (has a
   value, from extraction/inference/manual entry) / `NOT_ESTABLISHED` (no
   source ever stated this) / `CONFLICTING` (two sources disagreed, §5.4).
   No numeric gradient anywhere in this state.
2. **`rank_score`**, internal only, never rendered: if a future proposal
   builder or Path 1 LLM step genuinely needs to order multiple candidate
   values for internal tie-breaking, that's a private ranking signal, not
   a UX element and not an eligibility test. Bulk-approval eligibility
   (§2.5.1) is a categorical bar — direct evidence, valid schema, no
   conflict, no open `NOT_ESTABLISHED` dependency — that never reads
   `rank_score`.

```
PlaybookSourceDocument
  id, playbook_id (FK), uploaded_by_user_id (FK),
  document_type: LEGAL_PLAYBOOK | TEMPLATE_CONTRACT
  original_filename, extracted_text (EncryptedText),
  uploaded_at
  use_as_deviation_baseline: Boolean, default False  -- see 8.2
  use_for_policy_extraction: Boolean, default False  -- see 8.2

PolicyPositionApproval
  id, policy_position_id (FK), actor_user_id (FK),
  action: MARKED_REVIEWED | APPROVED | ACTIVATED | REVERTED | ARCHIVED
  from_status, to_status,
  reason (nullable text),
  created_at
  -- append-only, mirrors AuditLog's own "never UPDATE/DELETE" convention
```

`PolicyPositionApproval` is deliberately a dedicated table rather than
routing everything through the generic `AuditLog` — `AuditLog` remains the
place for *system-level* security/account events; `PolicyPositionApproval`
is the *domain* history a lawyer needs to see inline on a clause card
("Sarah approved this Feb 3, reason: matches firm standard"), which would
be an awkward query against a generic event log. Every `PolicyPosition-
Approval` write is still mirrored into `AuditLog` (one line, `event_type=
"policy_position_approved"`) so security/compliance tooling that already
watches `AuditLog` doesn't need to learn a second table.

### 4.3 History without a full version table

Rather than a parallel `PolicyPositionHistory` table duplicating every
column, field-level history is achieved by never updating a
`PolicyPositionField` row in place once `confirmed_at` is set: an edit to
a confirmed field writes a *new* row and sets `superseded_by_field_id` on
the old one. This gives exact field-level history (who changed what, from
what, when, replacing today's dead `PolicyRule.version` int) without a
second schema to keep in sync, and it composes with `PolicyPositionApproval`
for the position-level story ("approved," "activated," "reverted").

### 4.4 Encryption

Everything holding contract-adjacent or policy-substantive text follows
the existing pattern exactly: `PlaybookSourceDocument.extracted_text`,
`PolicyPosition.fallback_text`/`config_json`, `PolicyPositionField.
value_json`/`evidence_excerpt` are all `EncryptedText`/`EncryptedJSON`,
identical mechanism to today's `Playbook.template_text` and `PolicyRule.
fallback_text`. No new encryption infrastructure — this is pure
application of the existing `encryption.py` primitives to new columns.

---

## 5. Extraction / Import Architecture

New module, e.g. `playbook_authoring.py`, sitting *above* the six engines
and the existing extraction pipeline — never inside them.

### 5.1 Shared front door

Both Path 1 and Path 2 start the same way: `extract_text_from_file()`
(existing, unmodified) → `PlaybookSourceDocument` row with `document_type`
set to distinguish which path produced it. This is the only shared step;
the two paths diverge immediately after because they need fundamentally
different extraction strategies (§1.2 already established why: one is
prose about positions, the other is an actual contract in the shape the
six engines already parse).

### 5.2 Path 2 — deterministic extraction + inference-from-one-example

```
document text
  → extract_liability_facts(text)          [existing, unmodified]
    extract_indemnification_facts(text)    [existing, unmodified]
    extract_termination_facts(text)        [existing, unmodified]
    extract_confidentiality_facts(text)    [existing, unmodified]
    extract_assignment_facts(text)         [existing, unmodified]
    extract_governing_law_facts(text)      [existing, unmodified]
  → per-clause-type Facts object (or None if that clause type isn't in the document)
  → PROPOSAL BUILDER (new, one per clause type)
      - facts that map directly become EXTRACTED fields, evidence = the
        Facts object's own raw_excerpt/start_index/end_index (already
        computed by the engine — reused, not recomputed)
      - facts that would require generalizing a single stated number into
        a ladder (preferred → acceptable → negotiate → escalate) are
        NOT inferred. A template stating one number is evidence for that
        one number, not for a range around it — inventing a ladder from a
        single data point is a deterministic-looking guess, still a
        guess. These fields are written as NOT_ESTABLISHED, with the
        already-extracted preferred value shown alongside so the lawyer
        sees exactly what the template did and didn't establish
      - anything the extractor couldn't establish at all (its own
        REQUIRES_REVIEW-shaped abstention) also surfaces as NOT_ESTABLISHED,
        with the same "not found in this document" framing — the two
        cases (found-one-value-but-not-a-range vs. found-nothing) are
        distinguished by whether the field has a value, not by a
        different status
  → PolicyPosition(status=NEEDS_REVIEW) + PolicyPositionField[] rows
```

No LLM anywhere in Path 2, and no formula-based guessing either. This
path only ever writes what the document's own language states. This is
"deterministic/private import" (§5.3 draws the line here, not just on the
LLM question): it never leaves the machine, uses no external model call,
and produces no field the source document doesn't directly support. The
tradeoff, made deliberately: more `NOT_ESTABLISHED` fields land in the
Needs-Review queue than a first draft of this design would have produced,
in exchange for zero risk of a plausible-looking invented number becoming
policy.

### 5.3 Path 1 — "AI-assisted playbook import" (new boundary, explicit product decision, not just an implementation detail)

This is the one place in the whole design where a model reads free text
and proposes structure, and it is the first place in the product where a
full uploaded document — not a short rule-selected excerpt — reaches an
LLM prompt. That is a genuine, user-visible product distinction, not an
internal implementation detail, so it is surfaced as one:

- **Path 2 is named "Deterministic/private import"** in the product:
  upload a template contract, the existing deterministic extractors run,
  nothing ever leaves the system, no LLM involved. This is the default
  path and requires no opt-in.
- **Path 1 is named "AI-assisted playbook import"** in the product: upload
  a prose playbook document, and the UI states plainly, before upload
  completes, that an AI model will read the full document to propose
  positions. This requires **explicit per-use opt-in** — a lawyer must
  affirmatively choose this path each time, it is never the default or an
  automatic fallback if Path 2's extraction comes back empty.
- **Organization-wide disable switch**: an org admin can turn off Path 1
  entirely for the organization. When disabled, the "AI-assisted playbook
  import" option is not offered at all — Path 2 and Path 3 remain fully
  available. This is a real architectural constraint on the feature, not
  a cosmetic toggle: the upload endpoint checks the org setting before
  invoking anything in §5.3 below, and a disabled org's traffic never
  reaches the model call.

This product-level framing exists because TriageCounsel's differentiation
partly rests on "your contract text never reaches a model beyond a
sanitized excerpt used only to explain a finding we already made
deterministically." Path 1 is a deliberate, bounded exception to that
claim for a different kind of document (a playbook, not a contract), and
pretending otherwise — folding it into Path 2's messaging, defaulting to
it, or omitting the org-level kill switch — would weaken a claim the
product depends on. Everything below in this section describes how the
model call itself is bounded once a lawyer has opted in; it must be held
to a standard at least as strict as `evaluator.py`'s existing one, adapted
to a different job (existing: explain pre-detected findings; this:
propose structure from prose that has no pre-detected findings to anchor
it, because it isn't a contract). Concretely:

1. **Scope of what the model sees**: the full text of the uploaded
   playbook document — this is unavoidable, since prose about legal
   positions has to be read holistically, unlike `evaluator.py`'s
   short, rule-selected `matched_excerpt`. This is a genuine, explicit
   widening relative to the existing contract-review boundary, and must
   be named as such rather than described as "the same as today." What
   is *not* widened: the model still never writes anything that
   becomes authoritative on its own (§5.4), and the text still goes
   through the same sanitization discipline as `matched_excerpt` today
   (`prompt_security.py`'s length caps, injection-pattern detection,
   delimiter escaping/isolation — extended to a longer document rather
   than a short excerpt, same techniques).
2. **Schema-locked output**: the model may only emit values conforming
   to a fixed schema keyed by clause type and field name (the same
   fields each engine's `*PolicyRuleLike` Protocol defines — this schema
   is *generated from* the Protocols, not maintained separately, so it
   can never drift out of sync with what the engines actually accept).
   Any output field that doesn't validate against the target type
   (multiplier must be numeric, jurisdiction must be a string, exception
   list must be a list of known category tokens) is dropped, not
   coerced.
3. **Citation-required**: every proposed field must be accompanied by a
   verbatim quote from the source document. The system verifies the
   quote is an actual substring of the uploaded text (character-offset
   located, same `start_index`/`end_index` shape the six engines already
   use for their own excerpts) before accepting the field at all. A
   proposal with no locatable quote is discarded — not stored as
   lower-confidence, discarded, on the theory that an ungrounded
   proposal is worse than no proposal (silently inventing a position is
   the one failure mode this entire feature exists to prevent).
4. **Never authoritative**: every field this step produces is written as
   `PolicyPositionField(source=INFERRED)` under a `PolicyPosition` whose
   status is (and can only be) `NEEDS_REVIEW`. There is no code path
   from this function to `ACTIVE`, or even to `APPROVED`, without a
   human action in between — enforced the same way `evaluator.py`
   enforces "never overwrite `overall_risk`": a hard assertion in the
   write path, not a convention.
5. **Degrades safely**: if the API call fails or the key is unset, the
   clause card for that clause type simply stays unaddressed (`NOT_SET`)
   — exactly `evaluator.py`'s existing fallback discipline, applied here.

This is a new, narrower boundary purpose-built for "propose structure from
policy prose," documented as its own section of (an updated)
`LLM_BOUNDARY.md` rather than folded into the existing contract-review
entry, since the two use cases have different inputs and different
failure consequences and should be reviewable independently.

### 5.4 Merge policy across paths (the same clause type, multiple sources)

If a lawyer runs Path 1 and Path 2 against the same clause type (a
playbook memo *and* a template contract both address Liability):
`EXTRACTED` (Path 2, deterministic, from an actual contract) always
outranks `INFERRED` (Path 1, LLM, from prose) for the same field on
conflict — extraction from real contract language is strictly better
evidence than an LLM's reading of a memo describing intent. Conflicts are
not silently resolved by rank alone, though: a conflicting lower-ranked
value is preserved as a visible "also proposed, from a different source"
note on the field rather than discarded, so a lawyer reviewing the card
can see that two sources disagreed rather than only ever seeing the
winner.

---

## 6. Approval / Governance Lifecycle

### 6.1 States

```
DRAFT        — being built (manual entry in progress) or holding fields
               not yet touched by any review action. Not usable by
               evaluate_*_policy() under any circumstance.
NEEDS_REVIEW — contains at least one EXTRACTED or INFERRED field that no
               lawyer has confirmed. Not usable by evaluate_*_policy().
APPROVED     — every field has been either confirmed (extraction/inference
               reviewed and accepted or edited) or manually entered by a
               lawyer. Still not automatically live — see 6.3.
ACTIVE       — the position evaluate_*_policy() actually uses for new
               contract reviews. Requires an explicit activation action
               distinct from approval (6.3).
ARCHIVED     — superseded by a later position (e.g. the lawyer replaced
               the whole card via a new upload); retained for history,
               never used for evaluation.
```

State transitions are one-directional except for explicit "revert" actions
(`ACTIVE`/`APPROVED` → back to `NEEDS_REVIEW`, e.g. if a lawyer decides an
already-active position needs another look), and every transition writes a
`PolicyPositionApproval` row — no silent status changes anywhere, including
system-driven ones (e.g. Path 1/2 import always creates `NEEDS_REVIEW`, an
explicit approval action, not an implicit side effect of upload finishing).

### 6.2 Extraction vs. inference vs. enforcement — enforced, not just documented

This distinction is the spine of the whole design and is enforced at three
separate layers so no single bug collapses it:

1. **Storage**: `PolicyPositionField.source` is a required, non-nullable
   enum (`EXTRACTED`/`INFERRED`/`MANUAL`). There is no "unspecified"
   value — every field must declare its provenance the moment it's
   written.
2. **Write path**: the only code that can set `source=EXTRACTED` is the
   Path 2 proposal builder calling the six engines' own extraction
   functions; the only code that can set `source=INFERRED` is the Path 1
   LLM proposal step (or Path 2's ladder-generalization heuristic, which
   is deterministic-but-still-inferred, see 5.2); the only code that can
   set `source=MANUAL` is the clause-card edit endpoint, which requires
   an authenticated lawyer session performing the edit. No shared code
   path can produce more than one of these.
3. **Activation gate**: `evaluate_*_policy()` is only ever invoked (from
   the contract-review pipeline) using a `PolicyPosition` whose `status
   == ACTIVE`. A position can only reach `ACTIVE` via an explicit
   activation action performed by an authenticated user on an `APPROVED`
   position — this is the same enforcement style as `evaluator.py`'s
   hard assertion against `contract_text`, applied to the new boundary
   ("no unconfirmed field is ever load-bearing").

### 6.3 Why approval and activation are two separate actions, not one

Approval means "I have reviewed and confirmed every field is correct."
Activation means "this position now governs live contract review." These
are often the same moment for a lawyer working alone, but keeping them
separate supports two real cases without extra machinery: (a) an org that
wants a second approver before a position goes live (approve as reviewer,
activate as a partner/admin — enforceable later as a permission check on
the activation action without touching the approval step at all), and (b)
a lawyer who wants to finish reviewing all six clause types before
anything goes live, rather than each clause independently affecting
in-flight contract reviews the moment it's confirmed.

### 6.4 Escalation authority stays a config field, not a workflow (for now)

`escalation_approval_authority` remains what it is today — a named string
a lawyer types into the position, surfaced verbatim in `PolicyDecision.
escalate_to` during contract review. This document does not propose
building an actual routing/notification workflow around it; that's a
distinct, larger feature (real approval routing, notifications, SLAs) out
of scope here. Noting the gap explicitly rather than silently treating
"named a person" as "built a workflow."

---

## 7. UI — Clause Card Field Mapping (plain English, per clause type)

The concrete answer to "configure positions through plain-English controls
rather than internal engine terminology," field by field, for all six
engines' `*PolicyRuleLike` Protocols as they exist today.

**Shared across every clause card** (three fields every engine's Protocol
has in common):
- `contract_side` → **"Which side are we?"** — segmented control: *We're
  the Vendor/Seller* / *We're the Customer/Buyer* / *Position applies
  equally to both sides*
- `escalation_approval_authority` → **"Who signs off if this needs
  escalation?"** — free-text/role picker
- `fallback_text` → **"Fallback language to propose"** — rich text,
  shown inline with a live preview of how it will appear in a redline

**Liability** (`liability_policy_engine.PolicyRuleLike`):
| Field | Plain-English control |
|---|---|
| `preferred_multiplier` | "Ideal cap" — slider/stepper, "× annual fees" |
| `acceptable_max_multiplier` | "Auto-accept up to" |
| `negotiate_max_multiplier` | "Negotiate up to before escalating" |
| `prohibit_unlimited` | Toggle: "Never accept unlimited liability" |
| `required_exceptions_json` | Checklist: "These must stay uncapped" — Data Breach, IP Infringement, Confidentiality, Indemnification, Fraud, Gross Negligence, Willful Misconduct |
| `require_consequential_damages_exclusion` | Toggle: "Require exclusion of consequential/indirect damages" |
| `required_consequential_carveouts_json` | Checklist (shown only if above is on): "...except claims for" |

**Indemnification** (`indemnification_policy_engine.IndemnificationPolicyRuleLike`):
| Field | Plain-English control |
|---|---|
| `required_protection_triggers_json` | Checklist: "They must indemnify us for" — IP infringement, Data breach, Confidentiality breach, Negligence, Gross negligence, Willful misconduct |
| `prohibited_exposure_triggers_json` | Checklist: "We will never indemnify for" |
| `require_exposure_third_party_only` | Toggle: "Our indemnity only covers third-party claims" |
| `require_defense_control_for_exposure` | Toggle: "We must control our own defense" |
| `require_notice_and_cooperation_for_exposure` | Toggle: "Require prompt notice and cooperation first" |
| `prohibit_uncapped_exposure` | Toggle: "Never accept uncapped indemnity" |
| `exposure_preferred/acceptable/negotiate_multiplier` | Same ladder pattern as Liability, labeled "Our indemnity cap" |

**Termination** (`termination_policy_engine.TerminationPolicyRuleLike`):
| Field | Plain-English control |
|---|---|
| `require_mutual_convenience_termination` | Toggle: "We must have the same walk-away right they do" |
| `min_notice_days_against_us` | "Minimum notice before they can end the deal" (days) |
| `min_cure_days_against_us` | "Minimum time to fix a problem before they terminate for cause" (days) |
| `prohibit_immediate_termination_for_cause` | Toggle: "Never allow immediate termination without a chance to fix it" |
| `required_survival_topics_json` | Checklist: "These must survive termination" — Confidentiality, Payment Obligations, Limitation of Liability, Indemnification, IP Ownership, Audit Rights |
| `fee_preferred/acceptable/negotiate_multiplier` | Ladder pattern, "Termination fee we'll accept" |

**Confidentiality** (`confidentiality_policy_engine.ConfidentialityPolicyRuleLike`):
| Field | Plain-English control |
|---|---|
| `required_exclusions_json` | Checklist: "Standard carve-outs that must be included" — Public knowledge, Independently developed, Received from a third party, Required by law |
| `min_protection_duration_years` | "Minimum years they must protect our information" |
| `max_exposure_duration_years` | "Maximum years we'll protect theirs" |
| `require_mutual_confidentiality` | Toggle: "Protection must run both ways" |

**Assignment** (`assignment_policy_engine.AssignmentPolicyRuleLike`):
| Field | Plain-English control |
|---|---|
| `required_exceptions_json` | Checklist: "Allow assignment without consent for" — Affiliate transfer, Change of control, Merger/Acquisition |
| `prohibit_sole_discretion_consent` | Toggle: "Never accept 'sole discretion' consent language" |
| `require_consent_for_counterparty_assignment` | Toggle: "They need our consent too, if we need theirs" |

**Governing Law** (`governing_law_policy_engine.GoverningLawPolicyRuleLike`):
| Field | Plain-English control |
|---|---|
| `preferred_jurisdictions_json` | Tag list: "Preferred" |
| `acceptable_jurisdictions_json` | Tag list: "Also acceptable" |
| `prohibited_jurisdictions_json` | Tag list: "Never acceptable" |
| `required_dispute_resolution` | Choice: "No preference" / "Require arbitration" / "Require litigation" |
| `require_jury_trial_waiver` | Toggle: "Require jury trial waiver" |

No control anywhere surfaces a Python field name, a JSON key, or the word
"multiplier"/"threshold"/"Protocol." A lawyer reading a clause card should
never need to know these engines exist.

---

## 8. Migration Strategy

The template-findings/deviations mechanism is **not touched, not
deprecated in this phase, and not silently reinterpreted.**

1. **`Playbook.template_text`/`template_findings_json`/`template_risk`
   remain exactly as they are**, continue to power `playbook_engine.
   compare()` and the deviations view on `results.html`, unchanged. A
   lawyer's existing playbooks keep producing the same deviations report
   they do today, byte for byte, after this feature ships.
2. **`PlaybookSourceDocument` is a new, additive concept, not a
   replacement for `template_text`, but a single upload can power both
   mechanisms.** Uploading a template contract does not touch
   `template_text` directly, but the upload UI presents two independent
   checkboxes so the lawyer doesn't have to upload the same file twice:

   ```
   Use this document for:
   ☑ Contract deviation baseline   (feeds template_findings_json, as today)
   ☑ Extract proposed playbook positions   (feeds PolicyPosition, §5.2)
   ```

   Checking the first box runs the existing `rules_engine.analyze()` path
   and writes `Playbook.template_text`/`template_findings_json` exactly as
   it does today (unchanged code, unchanged output). Checking the second
   runs the new Path 2 extraction pipeline against the same uploaded
   bytes. The two `PlaybookSourceDocument` boolean columns (§4.2) record
   which were selected; a lawyer can revisit the same document later and
   turn on the box they skipped, without re-uploading. This keeps the two
   mechanisms's outputs fully independent (checking one box never writes
   to the other mechanism's tables) while removing the duplicate-upload
   step — same explicit semantics as two separate uploads, without the
   redundant UX.
3. **Existing `PolicyRule` (Liability-only) rows migrate, not
   disappear.** A one-time backfill creates a `PolicyPosition(clause_
   type="limitation_of_liability", status=ACTIVE, source_type=MANUAL,
   config_json=<mapped from the existing PolicyRule row>)` for every
   existing `PolicyRule` row, and every field is written with
   `source=MANUAL, confirmed_by=<original creating user, if recoverable,
   else null>, confirmed_at=<PolicyRule.updated_at>` — status starts at
   `ACTIVE` because these rows are, today, already governing live
   contract review; treating them as anything less on migration day
   would be a silent behavior change (a currently-enforced policy
   suddenly not enforced), which is exactly what this migration must
   avoid. The old `PolicyRule` table and its route/template are kept
   functional in parallel for one deprecation window (not deleted in
   the same change that introduces the new path), with the new
   `PolicyPosition` row as the actual source of truth once migrated —
   `apply_liability_policy()`'s call site switches to reading from
   `PolicyPosition` via the new builder function (§4.1) rather than the
   raw `PolicyRule` columns, but the columns themselves aren't dropped
   until a later, separate cleanup change with its own verification
   pass.
4. **No contract's historical `policy_decisions_json` is touched.**
   Those are frozen snapshots of a past decision and stay exactly as
   stored, regardless of any later change to the `PolicyRule`/
   `PolicyPosition` that produced them — this is already the existing
   discipline (`models.py` comments note findings are persisted, not
   recomputed, specifically so history survives later changes) and this
   migration doesn't touch it.
5. **Rollback path**: because old `PolicyRule` rows and routes stay
   live through the deprecation window, a failed or partial migration
   can be backed out by simply not switching the evaluation call site —
   the new tables can be dropped without having removed anything the
   product depended on.

---

## 9. Security / Audit Implications

- **No new encryption model** — every new column holding policy
  substance or document text uses the existing `EncryptedText`/
  `EncryptedJSON` types (§4.4), inheriting key rotation and the
  existing envelope format for free.
- **New attack surface: the Path 1 ("AI-assisted playbook import") LLM
  proposal step.** This is the first place in the product where a full
  uploaded document (not a short rule-selected excerpt) reaches a model
  prompt — which is why §5.3 treats it as an explicit, opt-in, org-
  disable-able product surface rather than a variant of existing
  extraction. Mitigations,
  restated from §5.3 because they are the security-relevant core of
  this whole document: schema-locked output, citation-required (every
  field must resolve to a real substring of the source, or it's
  discarded), and — the actual backstop — **the blast radius of a
  successful prompt injection here is bounded by the same fact that
  bounds every other risk in this design**: nothing the model produces
  can become `ACTIVE`, or even `APPROVED`, without an explicit human
  action. Worst case for a successful injection is a bad *proposal*
  sitting in `NEEDS_REVIEW` that a lawyer has to reject — not a live
  policy, not data exfiltration, not privilege escalation. This mirrors
  `THREAT_MODEL.md`'s existing acceptance of prompt-injection residual
  risk on the grounds that the model can't alter deterministic output;
  the same argument now needs to additionally cover "can't make itself
  authoritative," which the DRAFT/NEEDS_REVIEW gate provides.
- **Audit trail extends, doesn't fork.** `PolicyPositionApproval` is a
  new table but every write also emits one `AuditLog` row (§4.2), so
  existing security/compliance tooling watching `AuditLog` sees these
  events without modification.
- **Who can approve/activate is a new permission surface.** This design
  assumes, but does not fully specify, that approval and (especially)
  activation should be gated by role/permission — the two-action split
  in §6.3 is what makes a later "activation requires a senior
  reviewer" rule addable without re-architecting anything, but the
  actual permission model (who counts as a "senior reviewer," how
  that's configured per org) is out of scope for this document and
  should be its own design pass before implementation, not assumed.
- **Multi-tenant boundary**: `PlaybookSourceDocument`, `PolicyPosition`,
  and `PolicyPositionField` all inherit their tenant boundary from
  `Playbook.user_id` exactly as `PolicyRule` does today — no new
  cross-tenant surface introduced, but this should be explicitly
  verified in implementation (every new query filtered by the owning
  user/org, matching existing query patterns) rather than assumed from
  this document alone.

---

## 10. Phased Implementation Plan

Ordered so each phase ships something usable and de-risks the next one,
rather than one large release.

**Phase 0 — Data architecture + builders + migration tests.**
`PolicyPosition`/`PolicyPositionField`/`PlaybookSourceDocument`/
`PolicyPositionApproval` tables. Six policy-rule builder functions (one
per engine, §4.1). Migration script for existing `PolicyRule` rows (§8.3),
run and verified against a copy of production data, but the new tables
not yet wired to any route — this phase is pure plumbing, independently
testable (build a `PolicyPosition`, run it through a builder, confirm it
produces byte-identical output to today's `PolicyRule`→`PolicyRuleLike`
path for Liability).

**Phase 1 — Manual authoring (Path 3) for all six clause types.** No AI,
no import path, deliberately. The Workbench + clause-card UI (§3, incl.
the coverage indicator), plain-English field mapping (§7), full
DRAFT→APPROVED→ACTIVE lifecycle (no NEEDS_REVIEW yet — nothing to infer
without an import path). This is the phase that must be excellent before
anything else is layered on: create playbook → configure six policies →
approve → activate → upload contract → policies enforce correctly →
redlines generated, end to end, working well. This alone already fixes
the "five engines are orphaned" gap from §1 and is shippable/valuable on
its own.

**Phase 2 — Path 2, "Deterministic/private import" (template contract
upload).** No LLM, no inferred ladders (§5.2 — only what the document
actually states becomes `EXTRACTED`; everything else is `NOT_ESTABLISHED`
and left for the lawyer). `NEEDS_REVIEW` state, evidence panels, bulk
approval gated on the categorical bar in §2.5.1. This is the lower-risk
import path and, being purely deterministic, requires no new privacy
disclosure or opt-in.

**Phase 3 — Path 1, "AI-assisted playbook import" (playbook document
upload), bounded LLM, explicit opt-in.** The new LLM boundary (§5.3),
named as a distinct product surface with its own consent UI and the
org-wide disable switch, citation verification, schema-locked output,
updated `LLM_BOUNDARY.md`. Shipped last and separately because it's the
one component genuinely different in kind from everything else in this
design and deserves its own focused security review before going live.

**Phase 4 — Migration cutover + legacy cleanup.** Switch `apply_liability_
policy()`'s call site from `PolicyRule` to `PolicyPosition` (§8.3), run
the deprecation window, then remove the old form/route/columns in a
separate, reversible-until-merged change.

Batch B clause types are not started before Phase 4 completes — the
authoring layer needs to prove itself on the six already-built engines
first, and `config_json` (§4.1) means Batch B needs no schema work when
its turn comes.

Each phase includes its own before/after verification against the
existing benchmark corpora pattern already established for the six
engines — i.e., before touching the evaluation call site in Phase 4, capture
golden output for every existing `PolicyRule`-driven contract decision and
diff against the same contracts evaluated via the new `PolicyPosition`
path, exactly the discipline used throughout the engine-promotion work.

---

## 11. Major Failure Modes and Safeguards

| Failure mode | Safeguard |
|---|---|
| An LLM-inferred position becomes enforceable without a lawyer ever seeing it. | Three independent enforcement layers (§6.2: storage enum, write-path isolation, activation gate) rather than one convention. `evaluate_*_policy()` is architecturally unreachable from anything but an `ACTIVE` `PolicyPosition`, which is architecturally unreachable without a human activation action. |
| A hallucinated field (no real basis in the source document) reaches a clause card and looks legitimate. | Citation-required output (§5.3.3): every proposed field must resolve to a real substring of the source text or is discarded outright, not stored at lower confidence. |
| Two import paths silently overwrite each other's confirmed work. | `EXTRACTED`/`INFERRED`/`MANUAL` are permanent provenance tags on each field, not just at creation; conflicting values are surfaced, not silently replaced (§5.4); once `confirmed_at` is set, further changes create a new field row rather than mutating the confirmed one (§4.3), so "what did the lawyer actually confirm" is never ambiguous after the fact. |
| A migrated Liability policy silently stops being enforced (or starts being enforced with different values) the day this ships. | Migration writes `status=ACTIVE` immediately for existing rows (§8.3), and the evaluation call site isn't switched to the new table until Phase 4, after independent golden-output verification — there is no moment where an existing policy is live under the old path and silently inactive under the new one. |
| The legacy template-findings/deviations report quietly breaks or starts disagreeing with the new clause cards. | Explicitly not touched by this design (§8.1) — separate storage, separate route, separate template, no shared code path with the new `PolicyPosition` machinery. |
| A lawyer bulk-approves something they didn't actually mean to approve. | Bulk approval only ever targets fields meeting the categorical bar in §2.5.1 (direct evidence, valid schema, no conflict, no open gap) — never a numeric confidence threshold — and always shows the exact set being approved before confirming, never a blind "approve everything" action. |
| A deterministic-looking inferred negotiation range (e.g. "acceptable = preferred × 1.5") is treated as fact because it came from a formula, not a guess. | Removed from the design entirely (§5.2 revision) — Path 2 never infers a ladder from a single template data point. Unestablished ladder fields are always `NOT_ESTABLISHED` and require a lawyer's direct answer. |
| A lawyer uses "AI-assisted playbook import" without realizing their document's full text is being sent to a model, or an org's compliance stance requires disabling that entirely. | Path 1 is a named, opt-in product surface with disclosure before upload completes (§5.3), and an org-wide disable switch that removes the option from the UI and blocks the upload endpoint before any model call — not a per-request client-side toggle. |
| A prompt-injection attempt inside an uploaded playbook document tries to manipulate the LLM proposal step. | Same sanitization discipline as `matched_excerpt` today, applied to the (necessarily larger) document text (§5.3.1); and even a fully successful injection is bounded to producing a rejectable `NEEDS_REVIEW` proposal, never an active policy (§9) — the blast radius argument, not just the input-filtering one. |
| Field-level history becomes unreadable/unaudit-able after many edits. | `superseded_by_field_id` chains (§4.3) plus `PolicyPositionApproval`'s append-only log (§4.2) together answer both "what does this field say now" and "who confirmed what, when" without a parallel version table to keep in sync. |
| A Batch B clause type (out of scope to build now, but the architecture must not preclude it later) requires a schema migration just to get a clause card. | `config_json` (§4.1) means a new clause type needs a new builder function and a new §7-style field mapping, not a new set of columns — validated directly against that engine's own Protocol, so the schema can never drift from what the engine actually accepts. |
| An org wants a second approver before a position goes live, and the product can't support it without a rearchitecture. | Approval and activation are already two separate actions/permissions (§6.3) specifically so this is a permission-model addition later, not a new workflow to build from scratch. |

---

## What this document does not do

Per instruction: no code, no migrations, no template changes, no route
changes, and no modification to any of the six policy engines or their
Protocols — this is a design for review, not a plan already underway.
Two things are explicitly flagged as needing their own separate design
pass before implementation, not silently assumed here: the actual
permission/role model behind "who can approve vs. activate" (§9), and any
real escalation-routing/notification workflow behind `escalation_
approval_authority` (§6.4).
