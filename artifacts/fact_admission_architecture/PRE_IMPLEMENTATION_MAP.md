# PRE_IMPLEMENTATION_MAP — Fact Admission / Semantic Verification Architecture

Status: **STEP 0 investigation only. No production code has been modified.**
Repo state at time of writing: branch `claude/triage-fact-admission-verification-k5h57x`,
HEAD `576ea7d` ("Merge pull request #66 ... Step 4B FINAL FROZEN VALIDATION: PASS").

This map is deliberately conservative: every claim below is anchored to a file
and, where useful, a line range, so it can be checked rather than trusted.

---

## 0. Headline finding

**This codebase has already implemented most of the architecture the mission
describes — but only for one adapter (indemnification), and only for one
dimension of that adapter (clause-presence / candidate-span discovery).**
The mission's job is therefore not "build this from nothing," it is:

1. Extract indemnification's already-proven fact-admission pattern into a
   shared, adapter-agnostic framework.
2. Extend real semantic verification (not just candidate discovery) to the
   other 11 adapters, each of which today is 100% deterministic regex/rules
   with no AI participation at all.
3. Wire the already-built, already-correct `document_aggregation.py`
   aggregator into the actual user-facing surfaces — it currently is **not**
   called from `main.py`'s dashboard/listing/review-page rendering paths.
4. Close a small number of real gaps (near-empty/OCR-failed extraction,
   provider-abstraction duplication, and adversarial-verification framing —
   the existing semantic layer proposes candidates but does not yet actively
   try to *disprove* them).

No fundamental conflict with an existing safety invariant was found. See
§13 for the one design question that needs a decision before Step 1
(adversarial-verification framing vs. the existing "propose, then verify
deterministically" pattern) — this is a design choice, not a stop condition.

---

## 1. Authoritative 12-adapter list

Confirmed directly from the module list actually imported by production
(`playbook_ai_extraction.py:48-62`, and independently by
`ls *_policy_engine.py`):

1. `liability_policy_engine.py` — limitation of liability
2. `indemnification_policy_engine.py`
3. `confidentiality_policy_engine.py`
4. `payment_terms_policy_engine.py`
5. `ip_ownership_policy_engine.py`
6. `insurance_policy_engine.py`
7. `data_security_policy_engine.py`
8. `governing_law_policy_engine.py`
9. `termination_policy_engine.py`
10. `warranties_policy_engine.py`
11. `sla_policy_engine.py`
12. `assignment_policy_engine.py`

This matches the prompt's suggested list exactly. `assignment_policy_engine.py`
is confirmed live (it is imported and its facts flow through
`policy_enforcement.py` / `interaction_engine_core.py` alongside the other 11).

---

## 2. Overall authoritative call chain (all 12 adapters)

```
raw contract text (main.py:1445, upload_security-hardened, main.py:285-310)
  -> rules_engine.RuleEngine.analyze()          [LEGACY keyword/regex engine — rules_engine.py:4622]
  -> policy_enforcement.apply_policies_for_review()  [main.py:1514/1657]
       -> policy_enforcement.evaluate_active_policies()  [policy_enforcement.py:418]
            for each of the 12 clause_types with an ACTIVE PolicyPosition:
              extract_<clause>_facts(text)        # per-adapter, deterministic
              evaluate_<clause>_policy(facts, position)  # per-adapter, deterministic
              -> PolicyDecision (policy_engine_core.py:39-46 state vocabulary:
                 ACCEPT / ACCEPT_WITH_NOTE / NEGOTIATE / MUST_REDLINE /
                 PROHIBITED / ESCALATE / REQUIRES_REVIEW / NOT_APPLICABLE)
            one clause_type's extractor/evaluator raising -> isolated,
              recorded as EVALUATION_ERROR (policy_enforcement.py:464-466,546),
              never crashes the other 11 adapters' evaluation
       -> stored: Contract.policy_decisions_json, Contract.policy_revision_metadata_json
  -> interaction_engine_core.evaluate()          [interaction_engine_core.py:244]
       consumes ONLY Dict[clause_type, PolicyDecision] — never raw text, never
       an extractor, never an LLM (interaction_engine_core.py:8-13)
       -> stored: Contract.interaction_decisions_json
  -> document_aggregation.aggregate_document_state()  [document_aggregation.py:147]
       pure function over the three persisted fact sources — NOT currently
       called from any main.py route (document_aggregation.py:16-20)
  -> UI (review_contract route, dashboard, history) renders
       Contract.overall_risk (legacy) + findings_json + policy_decisions_json
       + interaction_decisions_json directly — no single authoritative
       document-state field is currently surfaced to the user.
```

Two independent decision-producing engines run today: the **legacy**
`RuleEngine` (keyword/regex based, produces `overall_risk` + `findings`) and
the **newer** deterministic Policy Engine (12 adapters, produces
`policy_decisions_json`). `document_aggregation.py`'s own state model already
anticipates this: `DOC_CLEAN_LEGACY_ATTENTION` exists specifically so a
legacy `overall_risk == "high"` can never be silently collapsed into
`DOC_CLEAN` (document_aggregation.py:192-194) — but since this function is
unwired, that protection is not actually reaching users yet.

---

## 3. Per-adapter extraction path / current semantic fallback

| Adapter | Extraction | Real AI semantic discovery? | Absence-state granularity |
|---|---|---|---|
| indemnification | `indemnification_policy_engine.py:extract_indemnification_facts` (regex) **plus** `_run_semantic_discovery` (line 2656) which calls `semantic_discovery_real.discover_candidate_spans_real` (Anthropic) | **YES — the only adapter wired to a real model** | 4-way: `CONFIRMED_ABSENT` / `RECOGNITION_UNCERTAIN` (line 2723) / `PRESENT_BUT_UNRESOLVED` (line 2991) / `PRESENT_AND_VERIFIED` (line 3037) |
| liability | `liability_policy_engine.py:1603 extract_liability_facts` | No | Adapter-local (not yet inventoried in this pass — see ADAPTER_MATRIX.md, to be produced in Step 1) |
| confidentiality | `confidentiality_policy_engine.py:209` | No | " |
| payment_terms | `payment_terms_policy_engine.py:637` | No | " |
| ip_ownership | `ip_ownership_policy_engine.py` | No | " |
| insurance | `insurance_policy_engine.py` | No | " |
| data_security | `data_security_policy_engine.py` | No | " |
| governing_law | `governing_law_policy_engine.py` | No | " |
| termination | `termination_policy_engine.py` | No | " |
| warranties | `warranties_policy_engine.py` | No | " |
| sla | `sla_policy_engine.py` | No | " |
| assignment | `assignment_policy_engine.py` | No | " |

Every non-indemnification adapter's module docstring opens with a
`SEMANTIC MODEL:` section (e.g. `confidentiality_policy_engine.py:7`,
`payment_terms_policy_engine.py:18`, `insurance_policy_engine.py:15`) — this
is **documentation of the adapter's conceptual/legal model** (what facts
matter and how they relate), not an actual AI call. Grepping every adapter
for `semantic_discovery_real`, `ANTHROPIC_API_KEY`, or
`discover_candidate_spans` returns zero hits outside indemnification. This
is the central, expected gap the mission exists to close — confirmed, not
assumed.

`semantic_discovery_real.py:86-87` hard-codes
`if concept != "indemnification": return []` — the real-provider path is
explicitly scoped to one concept today, by design, not by oversight
(comment at semantic_discovery.py:1-13 frames it as a bounded POC).

---

## 4. Existing fact-admission-shaped states already in the codebase

There are already **three independent, non-identical vocabularies** that
each partially express what the mission calls ESTABLISHED /
NOT_ESTABLISHED / AMBIGUOUS / etc. A shared framework must pick names that
either reuse or clearly compose with all three, not invent a fourth:

1. **Indemnification's absence_state** (`indemnification_policy_engine.py:1717,2723,2991,3037`):
   `CONFIRMED_ABSENT`, `RECOGNITION_UNCERTAIN`, `PRESENT_BUT_UNRESOLVED`,
   `PRESENT_AND_VERIFIED`. This is the closest existing analogue to the
   mission's candidate-fact admission states, and it is already proven in
   production benchmarks (Step 4A series).

2. **PolicyPositionField status** (`models.py:366`, used by the *playbook
   authoring* AI-import path, `playbook_ai_extraction.py`):
   `ESTABLISHED`, `NOT_ESTABLISHED`, `CONFLICTING`,
   `REQUIRES_LAWYER_INTERPRETATION`. Note this is scoped to **defining what
   the playbook's policy should be** (an authoring-time human-in-the-loop
   flow), not to **evaluating a contract against an existing playbook**
   (the review-time flow this mission targets). Same shape, different use
   case — worth reusing the shape, not the exact enum, to avoid conflating
   "we are drafting policy" with "we are admitting a candidate fact from a
   contract."

3. **PolicyDecision.state** (`policy_engine_core.py:39-46`): `ACCEPT`,
   `ACCEPT_WITH_NOTE`, `NEGOTIATE`, `MUST_REDLINE`, `PROHIBITED`,
   `ESCALATE`, `REQUIRES_REVIEW`, `NOT_APPLICABLE` — this is the
   **deterministic, authoritative decision** vocabulary. The new
   fact-admission states must feed into this, never merge with it or reuse
   its names for a candidate fact's own status (that would blur the exact
   authority line the mission requires).

4. **InteractionDecision.state** (`interaction_engine_core.py:63-83`):
   reuses most of (3) plus two interaction-only states, `NOT_TRIGGERED` and
   `INSUFFICIENT_FACTS` — and already implements exactly the "fail closed
   when a participant fact is unsafe" rule the mission asks for in STEP 9
   (`_gate_participants`, interaction_engine_core.py:222-241,
   `_UNSAFE_PARTICIPANT_STATES = {"NOT_APPLICABLE", "REQUIRES_REVIEW",
   "EVALUATION_ERROR"}`). **This already fully satisfies STEP 9 today** —
   the only new work is making sure new fact-admission states that should
   be unsafe (AMBIGUOUS, CONFLICTING, DEPENDENCY_UNRESOLVED,
   VERIFICATION_ERROR) surface as one of `{REQUIRES_REVIEW,
   EVALUATION_ERROR, NOT_APPLICABLE}` at the PolicyDecision layer, since
   that is the only vocabulary the interaction gate currently reads.

---

## 5. Current decision authority / AI boundary discipline

Already enforced, independently, in at least three places:

- `semantic_discovery.py:22-52` — `DiscoveryCandidate` is a frozen dataclass
  with a **hard-coded forbidden-field list**
  (`_FORBIDDEN_FIELD_NAMES`, line 36-41) and a runtime assertion
  (`assert_authority_boundary_intact`, line 44-52) that raises if the schema
  ever grows an authoritative-looking field (`policy_result`, `compliant`,
  `decision`, etc.), enforced by a dedicated test
  (`tests/test_semantic_discovery_authority_boundary.py`, referenced at
  line 27).
- `semantic_discovery_real.py:1-30` docstring states the same rule for the
  real-provider version and additionally requires exact substring
  verification of every quote before it can become an offset (lines
  139-144) — a hallucinated/non-verbatim quote is silently discarded, never
  trusted.
- `playbook_ai_extraction.py:14-35` states the same boundary for the
  *authoring* AI path: "There is no code path from an LLM candidate
  directly to an ACTIVE PolicyPosition." A candidate can only become
  `ESTABLISHED` after a verification gate, and even then it lands as a
  DRAFT requiring human approval before activation.

**Conclusion: AI-never-decides is already a first-class, tested invariant
in this codebase for the one place AI currently touches the review path.**
The mission's job is to hold that same line while widening AI's reach to
11 more adapters and to genuine semantic *verification* (not just
candidate discovery) — not to invent the boundary from scratch.

---

## 6. Provider abstraction(s) actually in use

There are **two independent, already-existing provider integrations** —
neither should be duplicated by a third:

1. **Anthropic, raw HTTP** — `semantic_discovery_real.py:50-153`.
   - Reads `ANTHROPIC_API_KEY` from environment only when actually needed
     (line 89), never logged, never defaulted.
   - Model pinned as a module constant (`_MODEL`, line 51).
   - 30s timeout (`_TIMEOUT_SECONDS`, line 52).
   - Any failure mode (`urllib.error.URLError`, malformed JSON, missing
     key) either raises `RuntimeError` or returns `None` — **never**
     returns an empty list that could be misread as "confirmed absent"
     (explicit callout in the module docstring, line 26-29, and enforced by
     the caller contract in `indemnification_policy_engine.py`'s
     `_run_semantic_discovery`).
   - Call-level telemetry (`CALL_LOG`, lines 44-48, 156-163) exists but is
     explicitly documented as "not read by any policy code" — diagnostic
     only.

2. **OpenAI, via the `openai` SDK** — used in two places with the same
   initialization idiom (env-var name and default model repeated
   verbatim, so it is one *pattern*, not one shared function today):
   - `evaluator.py:26,55-65` — reads `OPENAI_API_KEY` / `OPENAI_MODEL`
     (default `gpt-4o-mini`), used for the narrative/explanation layer on
     top of the legacy `RuleEngine` findings (`llm_evaluator.evaluate(...)`,
     `main.py:347`). This is explicitly a **non-authoritative summary
     generator** — `run_analysis()` (`main.py:346-354`) already treats any
     exception or falsy result as "fall back to a templated explanation"
     (`create_fallback_response`), never as a finding or a policy state.
   - `playbook_ai_extraction.py:283-293` — same `OPENAI_API_KEY`/
     `OPENAI_MODEL` idiom, used for the playbook-authoring candidate
     proposer described in §5. Already gated by a server-level env-var
     kill switch (`AI_ASSISTED_IMPORT_ENABLED`, lines 69-81) and a
     `LLMUnavailableError` that "degrades safely ... exactly like 'the
     model found nothing'" (lines 94-98).

**Recommendation for Step 1 (not yet implemented):** the new shared
semantic verifier should reuse the Anthropic integration pattern from
`semantic_discovery_real.py` (it is the one already proven against a real
adversarial-testing benchmark suite, per `tests/test_step4a9_2_real_provider_adversarial.py`
and `scripts/step4a10_outage_and_malicious.py`), factored into one shared
callable both existing adapters and the 11 new ones can use, rather than
copying the raw-HTTP block a 12th time or introducing the `openai` SDK into
the policy-decision path (which has never touched it). No new provider
integration is needed. No credential was read, printed, or logged during
this investigation — only environment variable *names* were confirmed via
`os.environ.get(...)` / `os.getenv(...)` call sites.

---

## 7. Interaction-engine participation on unsafe facts (STEP 9)

Already correct today, see §4 point 4 and `interaction_engine_core.py:222-332`.
`document_aggregation.py:41-44` and `:93-105` additionally distinguish a
structurally-inapplicable `INSUFFICIENT_FACTS` (every missing participant
was never evaluated at all because the playbook has no ACTIVE position for
it — genuinely not applicable) from a genuinely-uncertain one (a
participant was evaluated but landed in an unsafe state) — the latter must
still escalate to document-level `REQUIRES_REVIEW`
(`document_aggregation.py:56-59`). This distinction is exactly the kind of
subtlety STEP 6/9 warn against getting wrong, and it is already handled.

---

## 8. Document-level aggregation (STEP 10) — the real gap

`document_aggregation.py` is a complete, already-correct implementation of
the mission's STEP 10 requirement:
- 6-state model: `HAS_CRITICAL_INTERACTION` > `HAS_POLICY_VIOLATION` >
  `REQUIRES_REVIEW` > `CONFIGURATION_UNRESOLVED` > `CLEAN` /
  `CLEAN_LEGACY_ATTENTION` (precedence at lines 26-39).
- Malformed-data hardening so a corrupted `EncryptedJSON` row can never be
  misread as "no findings, therefore clean" (`_malformed_reasons`, lines
  108-131; `_state_of`, lines 134-144).
- Never lets the legacy `overall_risk` masquerade as the authoritative
  result — a legacy-high-risk-but-no-deterministic-finding document is
  `CLEAN_LEGACY_ATTENTION`, a visibly distinct state, never plain `CLEAN`
  (lines 192-196).

**But it is explicitly not wired into main.py** (module docstring, lines
16-20: "intentionally NOT wired into main.py's dashboard/listing queries in
this increment ... exercised here only by its own development benchmark").
This means the actual product today has no single authoritative
document-state field reaching the UI — `main.py`'s review/dashboard routes
render `overall_risk`, `findings_json`, `policy_decisions_json`, and
`interaction_decisions_json` as separate signals. **This is the most
concrete, highest-leverage gap for STEP 10/STEP 21 (live product
validation)**: without wiring, no screenshot of triagecounsel.com can show
"document cannot display authoritative CLEAN while material state
unresolved," because there is no single authoritative CLEAN badge yet to
falsify. Closing this gap is in scope for this mission and does not
conflict with any invariant — it is additive, and `document_aggregation.py`
was seemingly built and frozen exactly in anticipation of this kind of
follow-on wiring.

---

## 9. Historical reproducibility (STEP 11)

Already implemented and more complete than the mission's minimum ask:
- `models.py:150-163` — `policy_revision_metadata_json`: per-clause-type
  `policy_position_id`, `revision_activated_at`, a deterministic
  `config_hash` (computed in `policy_enforcement.py`), and `source_type`.
  Comment states explicitly: "Never recomputed from the current playbook
  state."
- `models.py:224-238` — `review_business_unit` / `review_customer_type` /
  `review_deal_value` persisted on the Contract row itself (not re-derived)
  for segment-position resolution reproducibility.
- `interaction_engine_core.py:146-152,211-219` — `InteractionDecision`
  carries a `participating_decision_snapshot` (state + sha256 content hash
  per participating clause type), enough to detect staleness
  (`interaction_enforcement.verify_interaction_finding`, referenced at line
  151) without needing to re-run anything.
- `policy_engine_core.py:2319-2328` — `decision_hash()` / `check_deterministic()`
  already exist as a generic determinism-checking utility (same pattern
  duplicated one layer up in `interaction_engine_core.py:335-346`).

**Gap for the new architecture:** none of these hashes currently include a
semantic-verifier version or prompt/schema version, because no adapter
outside indemnification calls a verifier yet, and even indemnification's
`_run_semantic_discovery` does not appear (from this pass) to write its own
version string into `policy_revision_metadata_json`. Step 1's shared
fact-admission framework needs to add `semantic_verifier_version` /
`verifier_prompt_schema_version` fields alongside the existing
`config_hash`/`policy_position_id` — an additive column/key, not a
migration of existing semantics.

---

## 10. Ingestion / text-quality gate (STEP 12)

`main.py:285-310` (`extract_text_from_file`) is the single choke point for
all upload paths, already hardened against magic-byte spoofing, malware,
zip/PDF bombs, and oversized extracted text
(`upload_security.py:validate_magic_bytes/scan_for_malware/validate_pdf_page_count/enforce_extracted_text_limit`).

`main.py:1440,1446-1447` already rejects a **fully empty** extraction with
a user-facing message that explicitly suggests OCR
("We couldn't find any text in that document. If it's a scanned PDF, run
OCR first and re-upload.").

**Real gap:** there is no gate for **near-empty** extraction — a scanned
PDF that yields a small amount of extractable text (running headers, page
numbers, a cover-page title) passes `if not contract_text.strip()` and
proceeds into `run_analysis()` as if it were a normal, fully-readable
document, which is exactly the "the contract contains no relevant
language" vs. "we failed to obtain enough text to determine that" ambiguity
STEP 12 calls out. No OCR dependency exists in the codebase today
(confirmed by grep for `pdfplumber|PyPDF|fitz|pdfminer|ocr` across the
repo — the only PDF library in use is the one already relied on for
extraction, no OCR library is installed). Per the mission's own
instruction not to introduce a major OCR dependency without justifying it,
the recommended fix is a **length/density heuristic gate** (e.g. extracted
character count below a threshold relative to page count, or below an
absolute floor) that routes to a new fail-closed ingestion state rather
than silently proceeding — no new dependency required.

---

## 11. Prior related work already on record (do not duplicate)

The repository already contains an extensive "Step 4A" / "Step 4B" program
(`artifacts/step4a3_final_report.md` and `artifacts/step4a4` through
`step4a11_remediation`, `artifacts/step4b/`) that appears to have already
built, adversarially tested, and **frozen-validated** exactly indemnification's
semantic-discovery + absence-state + document-aggregation architecture,
including a real-provider adversarial benchmark
(`tests/test_step4a9_2_real_provider_adversarial.py`) and outage/malicious-input
testing (`scripts/step4a10_outage_and_malicious.py`). The most recent commit
on this branch (`889fbef`, `576ea7d`) is literally titled "Step 4B FINAL
FROZEN VALIDATION: PASS — SHIP AUTHORIZED." This mission's job is to
**generalize** that already-shipped, already-validated pattern to the
other 11 adapters — not to redo it, and not to treat indemnification as a
green-field adapter. Reusing its exact hard rules (see
`semantic_discovery_real.py:10-29`) for the new shared framework is a
requirement, not a suggestion — this codebase has already paid for those
lessons once.

---

## 12. Architectural gaps to close (Step 1 onward)

1. No shared fact-admission dataclass/module exists — each adapter would
   otherwise reinvent absence-state logic an 11th time (the codebase
   already flags this exact anti-pattern in its own comments, e.g.
   `interaction_engine_core.py:97-100`, about `_worse()` having been
   "independently duplicated" three times before being promoted once).
2. Semantic verification exists only as *candidate discovery*
   (propose-a-span), never as *adversarial verification* of a candidate
   proposition (STEP 3's "actively try to disprove X" framing is new work,
   not an extension of existing code).
3. 11 of 12 adapters have zero AI participation today — extending them
   requires, per adapter, identifying its own material dimensions (STEP 8)
   before any verifier prompt can be written; this is real design work, not
   mechanical.
4. `document_aggregation.py` is unwired from the actual product surfaces.
5. No semantic-verifier version metadata is captured for reproducibility.
6. No near-empty-extraction gate exists in the ingestion path.
7. Two separate provider-integration idioms exist (`openai` SDK pattern,
   raw Anthropic HTTP pattern) — the new framework should consolidate on
   one (recommend the already-adversarially-tested Anthropic pattern) for
   the fact-admission verifier specifically, without touching the existing
   `openai`-based narrative-explanation or playbook-authoring call sites
   (out of scope, working, no reason to touch).

---

## 13. One design question to resolve before Step 1 (not a stop condition)

The existing indemnification pattern is "propose candidates broadly
(recall over precision), then verify deterministically." STEP 2/3 of the
mission ask for something adjacent but distinct: a **semantic verifier**
that receives a candidate proposition (already produced by deterministic
or semantic discovery) and adversarially tries to disprove it, with a
strict machine-readable schema. These compose cleanly — discovery proposes
a span, the new verifier judges the proposition the span appears to
support, deterministic grounding re-checks the verifier's own evidence
citation against the source text — but it means the "semantic verifier" is
a **new module**, not a relabeling of `semantic_discovery_real.py` (which
stays a discovery-only tool with no propositional/adversarial reasoning
today). Flagging this now so Step 1's shared framework is designed with
three distinct stages (discover -> verify -> ground), matching the
mission's own architecture diagram, rather than collapsing verify into
discovery the way indemnification's current code does.

---

## 14. No stop-condition triggered

None of the STOP conditions in the mission brief are triggered by this
investigation:
- No existing safety invariant would need to be weakened — every invariant
  found is additive-compatible.
- The existing provider integrations can be safely reused (§6).
- No credential handling issue was found (env-var names only were
  inspected; no value was ever read, printed, or logged during this pass).
- No migration is implied that would destroy historical provenance — new
  fields are additive to `policy_revision_metadata_json`.
- No adapter inspected so far appears incapable of supporting the shared
  architecture without changing its semantics (full per-adapter dimension
  audit is Step 1's `ADAPTER_MATRIX.md` deliverable, not yet produced).

---

## 15a. Addendum — deep verification pass (independent second read)

A second, independent trace (file:line level, all 12 adapters, all provider
call sites) confirmed every finding above and surfaced additional facts
material to scoping Step 1. Recorded here rather than folded silently into
the sections above, so the correction/addition is visible:

1. **`DEPENDENCY_UNRESOLVED` does not exist anywhere in the codebase today**
   (zero grep hits). The closest existing concept is
   `interaction_engine_core.py`'s `DEPENDENCY` *kind* (line 46) combined
   with the `INSUFFICIENT_FACTS` *state* — but that is a rule-kind label,
   not a fact-level state. This is genuinely net-new vocabulary for Step 1,
   not a rename.

2. **The most load-bearing prior finding for scoping expectations**:
   `artifacts/step4a9_2/step4a9_2_final_report.md` already measured, with
   200 real Anthropic API calls against indemnification, that semantic
   discovery moved recall **into `REQUIRES_REVIEW`** (30/30 novel-phrasing
   cases recovered, 0/30 under regex-only) but **0/200** semantic-sourced
   candidates ever reached `PRESENT_AND_VERIFIED`/clean-accept — the
   deterministic structuring regexes (`_OBLIGATION_RE` /
   `_SYNONYM_OBLIGATION_RES`) are the actual bottleneck on clean-accept
   recall, not discovery breadth. **Conclusion for Step 1: adding a
   semantic verifier to the other 11 adapters should be expected to move
   cases from `NOT_APPLICABLE`/silent-miss into `REQUIRES_REVIEW`, not into
   `ACCEPT`** — any Step 1 design or Step 20 success metric that assumes
   otherwise is miscalibrated against this codebase's own prior evidence.

3. **The false-absence gap is officially disclosed, not just discoverable**:
   `artifacts/step4b/final_validation/STEP_4B_FINAL_REPORT.md` §28 logs it
   verbatim as `SM=7` ("Step 4A.11 liability/indemnification false-absence
   architecture gap, safe-but-silent, none SM-CRITICAL — pre-existing,
   disclosed at the original Step 4A.11 freeze, unchanged, re-confirmed
   this cycle"), and §17 records that **8 of 12 adapters** (including
   liability and indemnification themselves, not only the other 11) missed
   freshly-authored real-text phrasing in the Step 4B corpus, always
   landing safely on `NOT_APPLICABLE`, never a false accept. This mission's
   job is the already-anticipated follow-on to that disclosure.

4. **Provider call sites: three, not two, and no shared wrapper.**
   `evaluator.py:54-68` (`LLMEvaluator`, OpenAI) and
   `playbook_ai_extraction.py:281-324` (`OpenAIExtractionClient`, OpenAI)
   are two independently-implemented classes sharing only an init idiom
   (same env var names, same default model, explicitly cross-referenced in
   comments) — not one shared class. `semantic_discovery_real.py` remains
   the third, Anthropic-only, raw-HTTP site. None of the three share retry
   logic; each independently does "one attempt, catch broadly, degrade to
   unavailable/None." Reinforces §6's recommendation: Step 1 introduces the
   *first* shared provider wrapper in this codebase, modeled on
   `semantic_discovery_real.py`'s hard rules, used only by the new
   fact-admission verifier — the two OpenAI call sites are out of scope and
   should not be touched or consolidated as part of this work.

5. **Ingestion quality gate, more precisely scoped**: no per-page
   text-density heuristic, no garbled-text/non-printable-ratio heuristic,
   and no quality metadata of any kind is threaded from
   `extract_text_from_file()` to any downstream adapter today — the only
   signal available anywhere past ingestion is the raw `contract_text`
   string itself. A near-empty-extraction gate for Step 1 therefore needs
   to both compute a quality signal at ingestion time *and* thread it
   through as new data (there is no existing field to repurpose).

6. **Reproducibility, additional primitives confirmed reusable**:
   `policy_enforcement.config_hash_for_position()` (`policy_enforcement.py:373-393`,
   sha256 over `{clause_type, contract_side, escalation_approval_authority,
   fallback_text, config_json}`, sorted keys) is the actual hashing function
   behind `policy_revision_metadata_json`, and
   `PolicyPositionField.extraction_version` (`models.py:488-494`, e.g.
   `"phase3-ai-assisted-v1"`) already establishes the precedent of stamping
   an extraction/verifier version string for auditability. Step 1's new
   `semantic_verifier_version`/`verifier_prompt_schema_version` fields
   should follow this exact precedent rather than inventing a new pattern.

7. **Vocabulary convention confirmed**: every state across all three
   layers (clause/interaction/document) is a bare module-level string
   constant compared via `in`/`==` — there is no shared Python `Enum`
   class anywhere in `models.py` or `policy_engine_core.py`. Step 1's new
   fact-admission states should follow this same convention (plain string
   constants + explicit membership sets) rather than introducing an `Enum`,
   for consistency with `document_aggregation._state_of()`'s deliberate
   refusal to trust a non-string state value.

---

## 15. Proposed next step

Per the mission's explicit instruction, **no production code will be
modified** until this plan is confirmed. The proposed Step 1 work, in
order:

1. Design and write `ARCHITECTURE.md` + `AUTHORITY_BOUNDARY.md` (naming the
   shared fact-admission dataclass, its states, and exactly how it composes
   with `PolicyDecision`/`InteractionDecision` without merging vocabularies).
2. Build the shared fact-admission module (discover -> verify -> ground ->
   admit), reusing the Anthropic call pattern from `semantic_discovery_real.py`.
3. Produce `ADAPTER_MATRIX.md`: for each of the 11 non-indemnification
   adapters, enumerate its material dimensions (per STEP 8's examples) and
   how each maps onto the shared framework, *before* writing any adapter
   integration code.
4. Wire `document_aggregation.py` into the actual review/dashboard routes,
   clearly labeling the legacy risk score per STEP 10.
5. Add the near-empty-extraction ingestion gate.
6. Only then begin adapter-by-adapter integration (indemnification's
   pattern generalized first, as the reference implementation), each as its
   own commit with targeted tests before moving to the next adapter.

Awaiting confirmation to proceed to Step 1.
