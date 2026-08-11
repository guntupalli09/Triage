# Policy Engine Core — Architecture Findings from the Second Adapter

Indemnification was built as the second clause adapter specifically to test whether `policy_engine_core.py` (extracted from Limitation of Liability alone) is genuinely reusable or was shaped around LoL's specifics without anyone noticing. This report answers that question directly: what survived unchanged, what required legitimate generalization, and where the boundary was wrong.

## Headline result

Both adapters hold their release gates simultaneously, and the LoL golden snapshot (all 109 cases' full decision output) is **byte-identical** to before this work started — confirmed by diff, not assumption.

| | Liability (109 cases) | Indemnification (43 cases) |
|---|---|---|
| False-safe | 0 | 0 |
| False-escalation | 0 | 0 |
| Determinism | 100% | 100% |
| Policy-state accuracy | 98.2% | 100% (first pass — see caveat below) |

**Caveat on the 100%:** this is a first pass on a corpus I wrote *and* debugged against in the same session, unlike LoL's corpus, which was hardened across three separate review cycles with a genuinely adversarial gap between authoring and fixing. Two real labeling errors were caught and corrected as part of getting here (below) — the process was honest, but 43 cases with one debugging pass behind them is not yet the same evidentiary weight as 109 cases with three. Treat 100% as "no known failures in this corpus," not "solved."

## What survived unchanged (genuinely clause-agnostic, validated by reuse)

- **Decision-state vocabulary** (`ACCEPT` … `NOT_APPLICABLE`) and the negotiation-ladder ordering. Indemnification uses all eight states with no new ones needed — the review's instruction ("support policy states through the existing vocabulary rather than inventing clause-specific outcome states") held with zero pressure to violate it.
- **`build_ladder`** — indemnification's ladder is "exposure cap" instead of "general cap" in the descriptions, but the passed/current/not-reached mechanics are untouched.
- **`classify_by_threshold`** — used exactly as designed for the exposure monetary cap. This is the piece the review specifically flagged as likely reusable ("cap treatment can plug into the generic threshold machinery later"), and it did, with zero modification.
- **`escalate_to_for_state` / `fallback_text_for_state`** — reused directly.
- **`PolicyDecision` / evidence rendering** — reused, with one real gap found and fixed (below).
- **Benchmark safety metrics** (`is_false_safe`, `is_false_escalation`, `check_deterministic`) — both benchmark harnesses import the same functions from core. Nothing clause-specific leaked into them.
- **`BUY_SIDE_ROLES` / `SELL_SIDE_ROLES` / `side_for_role`** — promoted to core *during this work* (see "required legitimate generalization" below), then immediately validated by a second, independent consumer.

## What required legitimate generalization (the core was incomplete, not wrong)

**1. Evidence-report labels were hardcoded LoL wording.** `render_evidence_report()` printed literal `"Counterparty cap:"` and `"Our liability:"` — fine when there was one adapter, actively wrong once a second one existed (indemnification isn't a "cap," it's an "exposure"). Fixed by adding `our_position_label` / `counterparty_position_label` / `summary_label` fields with defaults that reproduce the original LoL strings exactly (verified: the LoL evidence report text is unchanged), overridable per adapter. This is exactly the kind of thing a single adapter can't reveal on its own — it takes a second consumer to notice a hardcoded string masquerading as a shared format.

**2. Party-role vocabulary (`BUY_SIDE_ROLES`/`SELL_SIDE_ROLES`) was sitting in the LoL adapter.** Genuinely clause-agnostic — a "Customer" is buy-side whether the clause is about liability caps or indemnification. Promoted to core, LoL now imports it instead of defining it locally. Re-verified against the golden snapshot after the move: zero diffs.

**3. `resolve_directional_position`'s abstention wording was LoL-specific.** The message text ("cannot determine which cap applies to us") is now built from adapter-supplied `position_label`/`value_label` parameters rather than hardcoded. Indemnification doesn't use this function at all (see below), but the fix was necessary infrastructure work regardless, done and verified before indemnification needed anything from it.

## What proved wrong — the core boundary mismatches, reported honestly

**`resolve_directional_position` does not fit indemnification's directionality, and indemnification does not use it.** This is the central finding the review asked me to surface if I found it, and I found it immediately at the design stage, before writing extraction code.

LoL's asymmetry is: two named parties, **each has their own value for the same concept** (a liability cap), and the question is "which of these two values is ours." That's a same-concept-different-value shape, and `resolve_directional_position`'s `PositionCandidate(role, side, dedup_key, summary)` — dedup by value equality, pick the one matching our side — fits it exactly.

Indemnification's asymmetry is: **a directed relationship between two different roles** — "Vendor indemnifies Customer" is not a value Vendor holds that Customer also holds a different value of; it's a promise pointing from one named role to another. The question is not "which of two values is ours," it's "which of these directed edges points away from us (our exposure) and which points toward us (our protection)" — and a reciprocal clause can state a symmetric pair of such edges that are *both simultaneously true*, which has no LoL analog at all (LoL's multiple-provisions case always means "these are competing candidates for the one true value," never "these are both correct at once").

I built `_resolve_obligations_for_side` as adapter-local code rather than forcing this into `resolve_directional_position`. It shares the *philosophy* (never guess; an unmappable role or a mutual-policy-facing-directional-contract returns a reason, not a default) but not the mechanism. I did not attempt to retrofit `resolve_directional_position` into something that could serve both shapes — that would have meant either weakening LoL's simpler, already-battle-tested version, or building an abstraction general enough to cover "same-value asymmetry" and "directed-relationship asymmetry" under one API, which is a materially harder generalization I don't have a second directional clause type's evidence to justify yet. Recommendation: leave this as two adapter-local implementations until a *third* clause type reveals which shape (or a third shape) actually recurs — generalizing from n=2 here would be guessing.

**`CapValue`/`CapExpression` (LoL's typed cap representation) is not in core, and indemnification needed a smaller, separately-implemented version of the same underlying regex family.** Indemnification's `MonetaryTreatment` supports multiplier/fixed/unlimited/cross-reference/not-stated — a real subset of what `CapExpression` supports (no greater-of/lesser-of/per-claim-and-aggregate compound structures; indemnification monetary language in practice is simpler than liability caps, at least in this corpus). This is genuine duplication: two adapters now each own a "parse a dollar-multiplier-or-fixed-amount-or-unlimited expression from English" regex family, independently maintained. Unlike the abstention-topology mismatch above, this one *is* a plausible future promotion — the underlying concept ("a monetary expression, typed by basis, possibly compound") is not liability-specific, and the review predicted this exact tension. I did not do the migration in this pass: moving `CapValue`/`CapExpression` out of the benchmark-locked LoL adapter mid-PR, in the same change that also ships a new adapter, is exactly the kind of compound risk the golden-snapshot discipline exists to avoid. Recommendation: if a third clause type also needs typed monetary expressions, that's the trigger to extract a shared `MonetaryExpression` primitive — two data points, not one, and not bundled with unrelated adapter work.

**A regex correctness bug, exposed by testing indemnification's reciprocal-clause pattern, revealed a latent issue with the same shape in the LoL adapter (not touched, but worth flagging).** `_OBLIGATION_RE` was compiled with `re.I` applied to the *entire* pattern, including its `[A-Z][A-Za-z]{2,25}` role-name capture groups. Python's `re.IGNORECASE` applies to character classes, not just literals — so `[A-Z]` under `re.I` matches lowercase too, and the regex silently captured `"party"`/`"the"` as role names out of "**Each party** shall indemnify … **the** other party." Fixed by removing the blanket flag and scoping `(?i:...)` to just the verb-phrase literals, leaving the role-name character classes case-sensitive (which is also more correct: real contract role names are capitalized defined terms). **LoL's `_ROLE_POSITION_RE` has the identical `re.I`-over-`[A-Z]` construction** and was not modified in this pass — the golden-snapshot discipline (requirement 1: preserve LoL exactly) means a bug fix there is out of scope for this change even though it's the same latent risk. Flagging explicitly rather than silently leaving it undiscovered: this is a real, if currently unobserved, extraction gap in the LoL adapter, worth its own follow-up with proper regression tests, not bundled into an unrelated adapter's PR.

## Bugs found and fixed in the indemnification adapter itself (not core findings, listed for completeness)

Three real bugs surfaced by the benchmark, all fixed before this report:
1. The `re.I`-over-`[A-Z]` bug above, which made every reciprocal-clause case fail (false-escalation, since the corrupted role names couldn't be mapped to a side).
2. `_resolve_obligations_for_side` flagged *any* second same-direction obligation as an unresolvable conflict, even when its terms agreed with the first — should only flag genuine disagreement (mirrors the LoL adapter's "consistent duplicate" leniency, reimplemented locally since the shapes differ as described above).
3. A monetary treatment of `"not_stated"` on the exposure obligation was explicitly *not* penalized in the first draft — a direct repeat of the exact "extracted but not consumed" mistake flagged in the Liability work's Priority 5. Caught by the corpus, not by review discipline, which is itself worth noting: the benchmark is doing the job it's for.

Two labeling errors in my own corpus were also caught and corrected (documented individually in `benchmarks/indemnification_corpus.py`, not silently fixed): `asym-01` had exposure and protection swapped, and `malformed-01`'s expected state was corrected from `REQUIRES_REVIEW` to `NOT_APPLICABLE` once I re-applied the same reasoning already established for the LoL corpus's malformed-heading cases (a destroyed anchor means honestly finding nothing, not a redline instruction implying a clause exists).

## Overall verdict

The core survived as a real, validated boundary for: decision states, ladder mechanics, threshold classification, escalation/fallback routing, evidence structure, and benchmark metrics. It required two small, well-justified generalizations (evidence labels, role vocabulary) that a single adapter genuinely could not have revealed. It was **correctly not extended** to cover indemnification's directional-obligation topology, because that topology is a different shape, not a parametrization of LoL's — building a forced joint abstraction here would have been the "ugly special case" the review warned against. One duplication (monetary expression parsing) is flagged as a plausible future promotion, deliberately not acted on with only two data points.

This is not yet proof of a fully general contract-policy platform — it's proof that the *specific* boundary drawn after one adapter correctly separated "genuinely universal" from "looked universal because there was only one example," and that the process for finding out which was which (build the second adapter, let its benchmark find the seams, report honestly) works. A third clause type is the next real test, particularly for the monetary-expression duplication and for whether `resolve_directional_position` vs. adapter-local resolution turns out to be the right long-term split or just the right split for these two.

Per instruction: no third clause type started. Stopping here for review.

---

## Phase 3 update — after Indemnification hardening (43 → 100 cases)

The findings above were a first pass: a 43-case corpus written and debugged in the same session as the adapter itself. Per the review's explicit instruction, before touching a third clause type, the Indemnification corpus was expanded to 100 adversarial cases (Phase 1) and an isolated, pre-existing LoL regex risk was investigated and fixed (Phase 2). This section reports what that additional evidence changed, reaffirmed, or left open — not a rewrite of the findings above, which still hold.

### Headline result, updated

| | Liability (109 cases) | Indemnification (100 cases) |
|---|---|---|
| False-safe | 0 | 1 (documented, named exception — see below) |
| False-escalation | 0 | 0 |
| Determinism | 100% | 100% |
| Policy-state accuracy | 98.2% | 96.0% |

The LoL golden snapshot is byte-identical to before Phase 1/2 work started, except for the single, named, justified `perclaim-04` exception from the Phase 2 regex fix (documented in `benchmarks/liability_benchmark_report.md`, unrelated to Indemnification). Indemnification's 100-case pass is a real drop from the first pass's reported 100%, and that drop is the *point*, not a regression — the first 43-case number was, as flagged at the time, "no known failures in this corpus," not "solved." A larger, harder corpus found real failures. Most were fixed with genuinely generalizable changes (below); one was deliberately left open and named rather than patched under time pressure, matching the instruction not to chase 100%.

### What survived, now validated by a harder second pass, not just a first one

Everything listed as "survived unchanged" in the original report above held through Phase 1 with zero further changes needed: decision-state vocabulary, ladder mechanics, `classify_by_threshold`, `escalate_to_for_state`/`fallback_text_for_state`, `PolicyDecision`/evidence rendering, the benchmark safety-metric functions, and `BUY_SIDE_ROLES`/`SELL_SIDE_ROLES`/`side_for_role`. None of the three genuine engine bugs Phase 1 found (scope-silence, first-party-signal gaps, explicit-negation detection) touched core at all — every fix was adapter-local, inside `indemnification_policy_engine.py`. That is itself evidence the core/adapter boundary is drawn in the right place: 57 new adversarial cases, deliberately including categories the adapter had never been tested against (bodily injury, breach-of-contract triggers, duty-to-defend-without-"indemnify", advancement/reimbursement, settlement-consent, broad indemnified-party groups, amendment language, passive voice), put pressure on the *adapter's* extraction and evaluation logic, never on the shared state machine, ladder, or evidence format underneath it.

### A recurring bug class found independently in both adapters — a shared discipline, not shared code

Phase 2 fixed `liability_policy_engine.py`'s `_ROLE_POSITION_RE`, which had the identical `re.I`-applied-over-`[A-Z]` construction already found and fixed in `indemnification_policy_engine.py`'s `_OBLIGATION_RE` during the original build, and Phase 1 required the same care again when adding `_FIRST_PARTY_SIGNAL_RE`'s new "claims by X against Y" alternative (scoped with `(?-i:...)` specifically to avoid reintroducing it a third time). This is worth naming precisely because it is *not* a core-promotion candidate — there's no runtime value or function to extract; it's an authoring discipline ("role-name character classes must stay case-sensitive inside an otherwise case-insensitive regex") that every future adapter's own regex family needs to re-apply for itself. If a third clause type is authorized, its extraction regexes should be reviewed for this specific pattern before, not after, a corpus finds it.

### Duplication candidates — still not promoted, now with more (still not sufficient) evidence

`CapValue`/`CapExpression` (LoL) and `MonetaryTreatment` (Indemnification) remain separate, adapter-local implementations of the same underlying idea — a dollar-multiplier-or-fixed-amount-or-unlimited-or-delegated expression, parsed from English. Phase 1 added real pressure on Indemnification's side of this duplication (super caps, cap-exclusion semantic inversion, alternate cross-reference phrasings) without closing the gap between the two representations: `CapExpression` still supports compound structures (`greater_of`/`lesser_of`/`per_claim_and_aggregate`) that `MonetaryTreatment` has never needed, and `MonetaryTreatment`'s `cross_reference` kind has no `CapExpression` equivalent. Per the explicit instruction for this review: **not promoted**. Two data points, one of which just got harder without forcing convergence, is still not three.

### `resolve_directional_position` vs. adapter-local resolution — reaffirmed, with a new data point that argues *against* unification, not for it

Per the explicit instruction for this review, no attempt was made to unify `resolve_directional_position` with `_resolve_obligations_for_side`. Phase 1 produced a new reason not to: `false-reciprocal-01` (a clause that opens with "each party shall indemnify... the other party" — the reciprocal/symmetric shape — but then states *different* per-party monetary terms in a differentiated proviso) is a failure mode that has no LoL analog at all, because LoL has no concept of a claimed-symmetric relationship whose truth needs verifying. LoL's asymmetry is always "two parties, two independently-stated values, which one is ours" — never "a single provision claims both parties are treated identically; is that claim actually true throughout the provision." Indemnification's reciprocal-verification gap is a new, third directional shape, not a variation on either of the two already documented (LoL's same-concept-different-value shape, or indemnification's basic directed-edge shape). Three shapes now observed across two adapters is stronger evidence for "these stay separate until a clause genuinely recurs on one of them" than the original one-shape-each finding was — not weaker.

### The one open, named finding: reciprocal-claim verification — since closed at the architectural cause

`false-reciprocal-01` was previously the sole entry in `KNOWN_FALSE_SAFE_EXCEPTIONS`. It has since been fixed, not by special-casing the benchmark string, but by naming and closing the underlying gap: a mutual/reciprocal match (`_MUTUAL_RECIPROCAL_RE`) was applying the first monetary figure found anywhere in its window symmetrically to both directions, without checking whether the window also contained differentiated, per-party-attributed terms contradicting that symmetry.

**The third directional shape, characterized.** LoL's asymmetry is "two parties, two independently stated values of the same concept, which one is ours" (a comparative-value problem). Indemnification's base asymmetry is "a directed edge from one named role to another" (a directed-obligation-graph problem). This finding is neither: a clause makes an explicit **symmetry claim** ("each party"/"the parties shall mutually indemnify each other") that may or may not hold once the rest of the provision is read — a claim-verification problem, not a value-comparison or edge-direction problem. Concretely, the same clause can differentiate the two parties' actual terms along several independent axes: the monetary cap, the covered triggers, the claim scope (third-party-only vs. first-party-inclusive), defense-control assignment, or the indemnified-party group (e.g., one side's affiliates/officers/directors covered, the other's not). A genuinely reciprocal clause never states two different named parties' terms differently on any of these axes; when it does, the opener's claim is unverified, not false — the honest answer is "cannot confirm," not a guess in either direction.

**Fix, at the cause.** `indemnification_policy_engine.py` gained `_detect_reciprocal_asymmetry()`: when a mutual/reciprocal match is extracted, the same window is scanned for sub-clauses that attribute terms to one *specific named* role (`"Vendor's indemnification obligations..."`, `"Customer's obligations under this Section..."` — generic phrasing like `"each party's"` or `"the indemnifying party's"` is explicitly excluded, since it isn't asymmetry evidence). Each named role's local snapshot (monetary, trigger coverage, claim scope, defense control, indemnified-party breadth) is compared pairwise; any disagreement is recorded on the obligation as `asymmetry_reasons`. `_resolve_obligations_for_side()` then refuses to treat a reciprocal obligation with non-empty `asymmetry_reasons` as both our exposure and our protection — it returns `None, None` with a named reason, which routes through the adapter's existing `unresolved_facts` mechanism to `REQUIRES_REVIEW`, the same abstention path already used for unmappable roles and ambiguous carve-outs. No new state was invented, and `resolve_directional_position` was not touched or generalized toward this — the fix is entirely adapter-local, consistent with the instruction to preserve the LoL/Indemnification separation.

Ten regression tests (`TestReciprocalSymmetryVerification`) were written and confirmed to fail against the unfixed code before the fix was applied (verified by temporarily disabling the new gate and re-running: all 7 asymmetry-detection tests failed as expected, the 3 genuine-reciprocity/unilateral baseline tests still passed in both states, confirming the mechanism doesn't over-trigger). Variants cover: no per-party attribution (baseline), agreeing per-party attribution (baseline), pure two-obligation unilateral drafting (unaffected — never engages this path), and one test per asymmetry axis (monetary, trigger coverage, claim scope, defense control, indemnified-party group), plus a second reciprocal-opener idiom ("the parties shall mutually indemnify each other") and an explanation-content check.

`false-reciprocal-01`'s corpus label was corrected from `ESCALATE` to `REQUIRES_REVIEW` (documented in `benchmarks/indemnification_corpus.py`) — the original label assumed the engine could confidently identify the 5x figure as controlling, which is itself an unjustified guess given the ambiguous drafting; `REQUIRES_REVIEW` is the more defensible answer and is what the instruction authorizing this fix explicitly sanctioned as correct ("If reciprocity cannot be established deterministically, return REQUIRES_REVIEW or the applicable escalation state"). `KNOWN_FALSE_SAFE_EXCEPTIONS` has been removed from `tests/test_indemnification_benchmark_gate.py` — the gate is a strict zero-tolerance gate again, with no named exceptions.

This mechanism has known, honestly-scoped limits worth naming rather than glossing over: it only fires when at least two DIFFERENT named roles are each explicitly attributed their own terms within the same window (a single-sided attribution, or generic phrasing throughout, produces no comparison and falls through to the prior symmetric-application behavior unchanged); and the underlying `_ROLE_ATTRIBUTION_RE` pattern is scoped to `"<Role>'s (indemnification )?obligations..."` phrasing specifically, not every conceivable way English can attribute a term to a named party. A differentiated reciprocal clause phrased outside that pattern would not be caught. This is the same class of honestly-reported extraction-pattern narrowness as `xref-03`/`xref-04`/`cap-excluded-01` below, not a claim of general natural-language symmetry verification.

### Net assessment against the stated bar for a third clause type

Per the review's stated bar: Liability holds 109 cases, 0 false-safe, 0 false-escalation, 100% determinism, and is unchanged except for one named, justified exception. Indemnification now holds 100 cases, **0 false-safe**, 0 false-escalation, 100% determinism, and 97.0% policy-state accuracy (up from 96.0%, since fixing the reciprocal-symmetry gap at its cause also corrected the one case it was masking). Indemnification now meets the same zero-false-safe, zero-false-escalation, 100%-determinism bar Liability holds. **This bar was met, and clause #3 (Termination) was subsequently authorized** — see the next section.

---

## Clause #3 — Termination

Termination was chosen deliberately, per the authorizing review, to stress a reasoning shape neither prior adapter exercises. This section reports what building it found, at the same level of honesty as the sections above: what survived unchanged, what required genuine generalization, what stayed adapter-local, and what the third data point changes about earlier "not yet, only two data points" judgment calls.

### Headline result

| | Liability (109 cases) | Indemnification (100 cases) | Termination (40 cases) |
|---|---|---|---|
| False-safe | 0 | 0 | 0 |
| False-escalation | 0 | 0 | 0 |
| Determinism | 100% | 100% | 100% |
| Policy-state accuracy | 98.2% | 97.0% | 100% (first pass — see caveat) |

**Caveat on the 100%, same one given for Indemnification's first pass:** a 40-case corpus authored and debugged in the same session as the adapter is "no known failures in this corpus," not "solved." The number that matters more at this stage is that the false-safe/false-escalation/determinism gates hold at all on a genuinely new reasoning shape, not the accuracy percentage.

### The reasoning shape, characterized

Liability is a comparative-value problem: two parties, one concept (a cap), which value is ours. Indemnification is a directed-obligation-graph problem: a promise pointing from one named role to another, possibly stated reciprocally. Termination is neither — it is **a catalog of independently-true contingent rights**. A single document routinely states three or more separately-triggered rights (convenience, for-cause, insolvency, non-payment) in adjacent sentences, each with its own trigger, its own conditions (notice period, cure period, or immediate/no-cure), and none of them competing candidates for one "true" answer the way Liability's multiple cap mentions do. This is the same "track independently, don't reconcile" discipline Indemnification already established for its obligations — reused as a design PRINCIPLE, not as shared code, since a `TerminationRight` (trigger/notice/cure) and an `IndemnityObligation` (trigger/scope/monetary) are different fact shapes.

### What survived unchanged, a third time

Every core primitive Indemnification validated held again with zero modification: decision-state vocabulary (Termination uses ACCEPT/ACCEPT_WITH_NOTE/NEGOTIATE/MUST_REDLINE/PROHIBITED/ESCALATE/REQUIRES_REVIEW/NOT_APPLICABLE, no new states needed), `build_ladder`, `classify_by_threshold` (reused directly for the termination-fee multiplier — third independent consumer), `escalate_to_for_state`/`fallback_text_for_state`, `PolicyDecision`/evidence rendering (via adapter-supplied `summary_label`/`our_position_label`/`counterparty_position_label`, same mechanism as the other two), the benchmark safety-metric functions, and `BUY_SIDE_ROLES`/`SELL_SIDE_ROLES`/`side_for_role`. Three adapters now import the identical role vocabulary without any adapter needing its own.

### A real bug, found before the benchmark even ran

Termination clauses routinely stack multiple rights as consecutive sentences in one paragraph ("...for convenience upon 90 days notice. ...for cause if...fails to cure within 30 days. ...immediately upon insolvency."). An initial implementation used a single large fixed-size window per right for trigger/notice/cure classification — large enough to hold one right's own trailing clause, but also large enough for the NEXT right's trigger keyword (e.g. "insolvency") to leak into the classification of an earlier right, misclassifying its trigger type. This was caught by a direct sanity check before the benchmark corpus was even written, and fixed by bounding classification to the right's own sentence. Notably, Indemnification never surfaced this failure mode because it rarely states more than one or two directional obligations in tight sequence the way a Termination section conventionally lists three or four distinct rights — this is a finding specific to Termination's "catalog of several independently-true facts, densely packed" shape, and is itself evidence the reasoning-shape choice was a good stress test, not just a formality.

### The reciprocal-symmetry pattern recurs — reused as principle, not code, a third time

Termination rights can be stated reciprocally ("either party may terminate...") with a differentiated proviso naming different notice/cure terms per party afterward — the identical "opener claims symmetry, provisos may contradict it" shape found and fixed in Indemnification. `_detect_right_asymmetry()` in `termination_policy_engine.py` reimplements the same verification LOGIC locally (role-attribution scan, pairwise comparison, refuse-to-treat-as-both-sides-if-disagreeing), deliberately not importing or generalizing Indemnification's `_detect_reciprocal_asymmetry()`. Building it a second time surfaced a real generalization the first implementation didn't need: the window used for asymmetry detection must extend past semicolons (a differentiated proviso is conventionally punctuated as one semicolon-joined sentence with the reciprocal opener, not a new sentence), while the window used for trigger-type classification must NOT extend past sentence periods (see the bug above) — two different windowing needs serving the same provision, resolved with two different cut rules in the same adapter. This is now the **third independent instance** of the same underlying idea (a claimed-symmetric relationship whose truth must be verified against differentiated per-party language elsewhere in its own window) — see the promotion discussion below.

### Duplication candidates — a third data point on two separate open questions

**Monetary/fee expression parsing.** `TerminationFee` is a third adapter-local reimplementation of "parse a dollar-multiplier-or-fixed-amount-or-unlimited expression from English," alongside LoL's `CapExpression`/`CapValue` and Indemnification's `MonetaryTreatment`. Three independent implementations of the same underlying concept is real pressure — this report still does not promote it (that decision belongs to a dedicated pass, not a side effect of building an unrelated third adapter), but the "two data points isn't enough" reasoning from the Indemnification report no longer applies verbatim. This is now the strongest promotion candidate in the codebase.

**The "resolve directed facts into ours-vs-theirs" pattern.** Both Indemnification's `_resolve_obligations_for_side` and Termination's `_resolve_rights_for_side` independently implement: split a list of directional/attributable facts into "ours" and "the counterparty's against us" by role-to-side mapping, never guessing on an unmapped role, and handling a mutual/reciprocal item as applying to both lists unless proven asymmetric. This is now genuinely a candidate DIFFERENT from `resolve_directional_position` (LoL's same-concept-different-value shape) — a second, distinct recurring shape with two independent implementations. Not promoted here either, for the same reason as the fee-parsing duplication: a promotion decision deserves its own dedicated review with regression discipline, not a rider on the clause-#3 report. Flagged explicitly so it isn't lost.

**`resolve_directional_position` itself remains unused by a third adapter.** Termination did not reach for it, for the same reason Indemnification didn't: a termination right is a privilege held by a role, not a same-concept-different-value comparison. Three adapters, zero uses outside LoL, is now reasonably strong evidence this function is LoL-specific rather than a general primitive that happened to be extracted early — worth naming plainly rather than continuing to hedge.

### What Termination needed that neither prior adapter did

- **A window-cutting rule sensitive to punctuation convention** (period vs. semicolon), driven by the fact that Termination clauses pack multiple independently-true facts more densely than either prior clause type typically does.
- **A trigger classification with a same-clause priority order** (insolvency and non-payment checked before the more generic "material breach" pattern, since insolvency language is sometimes itself framed as a breach) — a clause-specific vocabulary decision, fully adapter-local, no core involvement.
- Nothing else. The rest of the adapter — extraction dataclasses, per-role attribution scanning, worst-state accumulation via a local `_worse()` helper (same pattern as Indemnification's), REQUIRES_REVIEW-first abstention — is a direct application of patterns already established, not new core surface.

### Overall verdict

The core boundary drawn after one adapter, and re-validated after a second, held through a third adapter deliberately chosen to reason differently from both. Nothing needed to be added to `policy_engine_core.py` to build Termination. Two duplication questions that were legitimately "not enough evidence yet" after two adapters (typed monetary expressions, directed-resolution-by-side) now have a third independent data point each and are worth a dedicated promotion review — separately from any fourth clause type, not bundled with one. `resolve_directional_position` remains validated as correctly LoL-specific, not under-generalized core.

Per the review's own framing: this is the point where the architecture stops being "promising" and starts being a credible reusable pattern — three adapters, three different reasoning shapes, one unmodified core, zero false-safe across all of them. The batches (Confidentiality/Assignment/Governing Law, IP ownership/Data protection/Insurance/Payment terms, Warranty/Force majeure/Audit rights/Non-solicit) and the product-layer work (policy hierarchy, governance, authoring UX, redline workflow, analytics) described in the authorizing review are **not started** — this report covers clause #3 only, per the same "report and stop" discipline used after clause #2.

---

## Batch A — Confidentiality, Assignment, Governing Law

Per instruction, Batch A was built for breadth rather than as another deep architecture exercise — one combined report, not three per-adapter essays. All three reuse the established core (decision states, ladder, evidence rendering, safety metrics) with zero changes to `policy_engine_core.py`.

### Headline result

| | Liability (109) | Indemnification (100) | Termination (40) | Confidentiality (24) | Assignment (19) | Governing Law (22) |
|---|---|---|---|---|---|---|
| False-safe | 0 | 0 | 0 | 0 | 0 | 0 |
| False-escalation | 0 | 0 | 0 | 0 | 0 | 0 |
| Determinism | 100% | 100% | 100% | 100% | 100% | 100% |
| Policy-state accuracy | 98.2% | 97.0% | 100%* | 100%* | 100%* | 100%* |

\* First-pass corpora (19–40 cases), authored and debugged in the same session — the same "no known failures yet, not solved" caveat given to every prior adapter's first pass. Per your explicit instruction, Termination's 40-case corpus was not expanded before starting this batch; none of the three new corpora were hardened past a first pass either. All six gates hold; that's the meaningful signal at this stage, not the accuracy percentages.

### Confidentiality and Assignment: the pattern recurs a fourth and fifth time

Both reuse the "resolve directed facts into ours-vs-theirs by role, verify reciprocal-symmetry claims" shape independently, adapter-local, not shared code — the same idea now implemented five times (LoL's `resolve_directional_position` is the odd one out at a *different*, same-value shape; Indemnification, Termination, Confidentiality, and Assignment all independently built their own resolver for "directed facts, possibly reciprocal, possibly asymmetric despite a symmetric opener"). This is not a new finding so much as the same one getting harder to ignore each time; it's tracked, not acted on, per the standing "needs a dedicated promotion review, not a rider on an unrelated adapter" position.

### A real, generalizable bug found and fixed proactively — not just reactively

Building Assignment's reciprocal-symmetry check surfaced a genuine defect: the per-role local window used to classify a differentiated proviso ("Vendor's... reasonable care, and Customer's... sole discretion.") only cut at the next sentence period, and two attributions separated by ", and" inside one semicolon-joined sentence share a single trailing period — so a role's own classification window could bleed into the NEXT role's clause. For a *positional* fact (a number, found via leftmost-match search) this self-corrects, because each role's own value is the nearest one ahead in its own window. For a *priority-ordered* classification (Assignment's consent standard checks "sole discretion" before "reasonable" regardless of position; Confidentiality's standard-of-care check has the identical shape) the bleed silently produced the WRONG answer — a role whose own clause said "reasonable" could misclassify as "sole discretion" merely because that phrase appeared later, in the other role's clause, inside the bled-over window.

Found while building Assignment, fixed there with a proper before/after test, and — because the same priority-ordered-classification shape was recognized as the cause — proactively checked against Confidentiality's structurally identical `_classify_care` function *before* shipping it, without waiting for its own corpus to happen to expose it. It hadn't yet: a quick targeted check confirmed the same bug was live and silent there too, fixed identically, with its own regression test. This is a different discipline than the reactive "adversarial corpus finds a bug, then we fix it" pattern used throughout this project so far — recognizing a bug CLASS from one adapter and checking a sibling adapter for the same defect before its own benchmark would have found it. Recorded here because it's a better process than what came before it, not because either engine shipped with the bug live.

### Governing Law: the first adapter that does NOT need the recurring pattern

Governing Law was chosen deliberately as the structural outlier of the batch: it is a categorical/set-membership problem (is the named jurisdiction on a preferred/acceptable/prohibited list), not a directional graph at all. There is no "our side vs. their side" — governing law binds both parties identically, `contract_side` is read nowhere in the evaluator, and `no-directionality-02` in its corpus explicitly asserts that a `contract_side="mutual"` configuration is never itself an unresolved fact here, unlike every other adapter built so far. This is an honest, useful negative result: not every clause needs the directed-resolution shape the other five converged on, and Governing Law was not forced into it. `classify_by_threshold` also goes unused here (there's no numeric ladder — jurisdiction membership is a lookup, not a threshold), the second core function (after `resolve_directional_position`) now confirmed as legitimately adapter-specific-in-usage rather than universal.

### Net assessment

Six adapters, three genuinely different reasoning shapes (comparative-value, directed-fact-resolution-with-reciprocal-verification, categorical-lookup-with-no-directionality), one core untouched since Liability's extraction. Batch A is complete. Per instruction, Batch B (IP ownership, Data/Security, Insurance, Payment Terms) and the product-layer work (Playbook Authoring UX and beyond) are **not started**.
