# Duplication / Promotion Review — Six Adapters

Read-only architecture review. No code was changed, no adapter behavior was
modified, and no new clause types were added while conducting this review.
Every classification below was reached by reading the current source of
`policy_engine_core.py`, `liability_policy_engine.py`,
`indemnification_policy_engine.py`, `termination_policy_engine.py`,
`confidentiality_policy_engine.py`, `assignment_policy_engine.py`, and
`governing_law_policy_engine.py` as they exist today.

**Legend**

- **A** — genuinely clause-agnostic, ready for core promotion
- **B** — structurally similar surface, semantically clause-specific underneath
- **C** — accidental duplication that should be eliminated (no semantic content at all)
- **D** — intentionally adapter-local, correctly so

Governing Law is used throughout as the negative control it was designed to
be: every proposed promotion is checked against "would this force Governing
Law (or any other adapter) through machinery it doesn't naturally need?"
Where the answer is yes, that is treated as a disqualifying finding, not a
detail to shrug off.

---

## 1. Directed role resolution — **B**, one narrow sub-fragment is **A**

Four independent implementations of "split a list of clause-specific items
into ours-vs-the-counterparty's by mapping each item's role through
`side_for_role`":

| Adapter | Function | Shape |
|---|---|---|
| Indemnification | `_resolve_obligations_for_side` | singular slot each side, **with** same-side conflict detection via a `(kind, value)` key |
| Termination | `_resolve_rights_for_side` | **list** each side (many independently-true rights can land on either side), no conflict detection (nothing to conflict — every right is independently valid) |
| Confidentiality | `_resolve_obligations_for_side` | singular slot each side, **with** conflict detection via `(duration_years, perpetual)` key |
| Assignment | `_resolve_restrictions_for_side` | singular slot each side, **no** conflict detection at all — a second same-side restriction silently overwrites the first |

All four also share, verbatim in spirit: a `mutual`/`named` split, a
`contract_side == "mutual"` guard that refuses to resolve a directional
contract against a mutual policy, and a per-item "role could not be mapped to
our configured contract side" abstention reason.

**Why this is B, not A:** the singular-slot-with-conflict-detection shape
(Indemnification, Confidentiality) and the list-accumulation shape
(Termination) are genuinely different data models, not cosmetic variants —
Termination's rights are independently true and never conflict by
construction; Indemnification's and Confidentiality's obligations occupy one
"true" slot per side and a second, disagreeing one is a real ambiguity.
Forcing these through one signature would mean either the list-shaped
adapters carry an unused conflict-detection code path, or the singular-slot
adapters lose their conflict detection to a lowest-common-denominator
"append to a list" model — silently removing a real check three call sites
depend on. That is exactly the kind of correctness cost this review was
told to avoid.

Also worth naming plainly: Assignment's silent-overwrite-on-conflict is not
a duplication finding at all, it's a coverage gap discovered as a side
effect of this review. Not a fix to make now (explicitly out of scope), but
flagged so it isn't lost.

**LoL is not part of this cluster.** `_resolve_directional_position` (LoL,
already core-backed via `resolve_directional_position`) resolves a
different question — "of two stated VALUES of the same concept, which one is
mine" via dedup-key equality across a flat candidate list — not "which
ROLE-OWNED items are on my side." No `mutual`/`named` split exists in LoL at
all, because LoL has no reciprocal-clause concept. This is a confirmed,
previously-reported finding, not a new one: **B**, correctly kept separate.

**Narrow promotable sub-fragment (A):** the `mutual`/`named` split itself
(`[o for o in items if o.is_mutual]` / `[o for o in items if not
o.is_mutual]`) and the "directional contract vs. mutual policy" abstention
reason are byte-identical in spirit across all four and carry zero semantic
weight — a small `split_mutual_from_named(items)` helper and a
`mutual_policy_conflict_reason(named)` helper could be promoted without
touching the part that actually differs (how the split items get combined
into our/their). This is worth doing in isolation from the larger
resolve-for-side question.

**Governing Law check:** has no directionality at all — `contract_side` is
read nowhere in its evaluator, confirmed by an explicit corpus case
(`no-directionality-02`). Nothing here would touch it either way; correctly
excluded from any version of this promotion.

---

## 2. Reciprocal symmetry verification — **A**, the strongest candidate in this review

Four independent implementations of the identical shape: scan a window for
role-attributed sub-clauses via an adapter-specific attribution regex,
snapshot N adapter-specific facts per named role into a dict, then compare
snapshots pairwise and emit human-readable disagreement reasons.

| Adapter | Function | Snapshot fields |
|---|---|---|
| Indemnification | `_detect_reciprocal_asymmetry` | monetary, scope, defense_control, triggers, broad_beneficiary |
| Termination | `_detect_right_asymmetry` | notice, cure, immediate |
| Confidentiality | `_detect_confidentiality_asymmetry` | duration_years, perpetual, care |
| Assignment | `_detect_restriction_asymmetry` | consent_standard, exceptions |

The **control-flow skeleton is identical and carries zero clause semantics**:
run the attribution regex, skip generic role words, bound each match's local
window at the position of the *next* attribution match (not just the next
sentence period), build a snapshot dict via adapter-supplied classifiers,
compare the first role's snapshot against every other role's pairwise, and
collect a reason string per disagreement. Only the attribution regex and the
per-role snapshot/compare logic are genuinely adapter-specific — those are
naturally supplied as parameters (a compiled regex, a generic-word set, a
snapshot callable), not copied code.

**This is the strongest promotion case in the whole review, for a concrete,
already-proven reason:** the window-bleed bug (a role's local window
extending into the *next* role's clause when they're separated by `, and`
rather than a period, silently corrupting priority-ordered classification
like "sole discretion checked before reasonable regardless of position")
was found once, in Assignment, fixed there, and then had to be *manually,
proactively* ported to Confidentiality's structurally identical function
before its own benchmark happened to expose it. Termination's and
Indemnification's versions were written before this fix existed and were
not checked against it as part of this review (see the open item at the end
of this document). Centralizing this skeleton means a fix like that lands
once, not N times with a manual audit needed to find the other copies.

**Governing Law check:** has no reciprocal/mutual concept and would not be
touched by this promotion — confirms the mechanism is genuinely opt-in per
adapter shape, not a forced-fit.

**Recommendation (not implemented): promote a parameterized core helper**
along the lines of `detect_role_attributed_asymmetry(window, attribution_re,
generic_role_words, snapshot_fn) -> List[str]`, with the snapshot-comparison
logic itself either generic (compare all keys, flag any pairwise
inequality) or left to the caller. Four call sites, one shared bug surface,
zero forced conformity on any adapter that doesn't have this shape (LoL,
Governing Law).

---

## 3. Typed monetary/value expressions — **D** (as a whole), **B** for a narrower sub-primitive

Three real monetary-typed-value implementations, plus one same-shape analog
that isn't money:

| Adapter | Type | Kinds supported | Extra structure |
|---|---|---|---|
| LoL | `CapValue` / `CapExpression` | fee_multiplier, fixed_amount, unlimited | typed `basis` (FEES/PURCHASE_PRICE/CONTRACT_VALUE/...); compound `structure` (simple/greater_of/lesser_of/per_claim_and_aggregate) |
| Indemnification | `MonetaryTreatment` | multiplier, fixed, unlimited, **cross_reference**, not_stated | flat, no compound structures |
| Termination | `TerminationFee` | multiplier, fixed, unlimited, not_stated, **not_mentioned** | flat, no compound structures |
| Confidentiality | duration fields (`duration_years`/`duration_perpetual`) | not typed as a class at all — same "scalar-or-unlimited-sentinel" shape, different unit (years, not dollars) | — |

Four data points now (three monetary, one duration-shaped cousin), which is
enough to take the promotion question seriously — this is exactly the
finding already flagged after Termination shipped ("the strongest promotion
candidate in the codebase") and after Batch A. It remains **not ready**, for
two concrete, non-hand-wavy reasons rather than "not enough data points":

1. **LoL's compound-structure and typed-basis machinery has no analog in
   the other two.** Neither Indemnification nor Termination has ever needed
   `greater_of`/`lesser_of`/`per_claim_and_aggregate`, and neither has ever
   needed to distinguish a fees-basis multiplier from a purchase-price-basis
   one. Promoting LoL's full `CapExpression` would mean two adapters carry
   dead structure fields forever, or a promoted type gets *simplified* to
   the lowest common denominator and LoL loses real, benchmark-tested
   correctness machinery (the whole reason `effective_cap()` exists is to
   refuse to guess across a compound structure).
2. **Indemnification's `cross_reference` kind and LoL's cross-reference
   handling are different DESIGN CHOICES for the same situation, not the
   same mechanism under different names.** LoL treats "delegates elsewhere"
   as a resolution *process* applied before a `CapValue` is even produced
   (see §8 below) — cross-reference is not a `CapValue.kind` in LoL at all.
   Indemnification chose to make `cross_reference` a first-class
   `MonetaryTreatment.kind` and never attempts resolution. Unifying these
   would require picking one design and retrofitting the other adapter to
   match it, which is not a duplication fix, it's an uninstructed behavior
   change.

**Narrower candidate (B, not currently recommended):** the low-level "parse
a plain `N times/x <basis words>`, a `$X` fixed amount, or an unlimited-
signal phrase" regex-and-classify layer is structurally near-identical
across all three monetary adapters. It is not promoted here because the
*exact* lead-in phrasing differs meaningfully per clause (LoL's fixed-amount
regex accepts several lead-ins — "maximum liability of", "capped at",
"limited to" — none of which are appropriate as Indemnification's or
Termination's default; Termination's requires the words "termination fee"
adjacent). A shared primitive would need per-adapter phrase injection
anyway, which is most of the value a promotion is supposed to remove. Worth
revisiting if a Batch B clause (Payment Terms is a strong candidate) turns
out to need genuine monetary parsing again — a fourth true monetary data
point, not a duration-shaped cousin.

**Governing Law check:** has no monetary concept whatsoever — nothing here
touches it, and nothing should.

---

## 4. Evidence/provenance construction — **A**, already correctly promoted

`PolicyDecision` and `render_evidence_report()` already live in
`policy_engine_core.py` and are used, unmodified, by all six adapters via
the `summary_label`/`our_position_label`/`counterparty_position_label`
override fields established when Indemnification was built. This is not a
new finding — it is a confirmation that the existing promotion continues to
hold under the negative control: Governing Law sets
`our_position_label="N/A"`, `counterparty_position_label="N/A"` rather than
being forced to fabricate a directional position it doesn't have, which is
exactly the intended escape hatch working as designed.

`category_treatments` (a generic `List[Dict]` of sub-treatments) is reused
by five of six adapters for meaningfully different content — carve-out
categories with cap summaries (LoL), trigger treatments (Indemnification),
right-trigger classifications (Termination), exclusion topics
(Confidentiality), standing exceptions (Assignment) — and correctly left
empty by Governing Law, which has no sub-treatment concept. No changes
recommended; this slot is already general enough.

---

## 5. Abstention / unresolved-fact handling — **A**

Every adapter (all six) accumulates a `List[str]` of `unresolved_facts` and,
when non-empty, returns a `REQUIRES_REVIEW` `PolicyDecision` built from a
formulaic explanation string that is duplicated near-verbatim six times:

> `Contract language: "{excerpt}". This {clause} could not be evaluated
> deterministically — the following fact(s) required for a policy decision
> could not be reliably established: {joined reasons}. Result:
> REQUIRES_REVIEW.`

This carries no clause semantics at all — the only per-adapter variation is
the excerpt, the joined reasons list (already adapter-supplied), and the
label naming what "this" refers to. This is functionally identical to the
excerpt-formatting utilities in §9 below: a pure construction helper with
zero decision logic. A `build_requires_review_decision(rule_id, clause_type,
excerpt, unresolved_facts, ladder, category_treatments, ..., labels)` core
function would remove five-to-six near-identical 15–20 line blocks with no
loss of adapter-specific control (every adapter still supplies its own
`unresolved_facts` list and labels).

**Governing Law check:** has the identical shape for its own "jurisdiction
could not be parsed" case — not a forced fit, an independent convergence on
the same pattern, which is itself supporting evidence this is genuinely
universal rather than coincidentally similar.

---

## 6. Threshold classification — **A**, already correctly promoted and correctly *not* over-adopted

`classify_by_threshold` already lives in core. It is used, unmodified, by
exactly three of six adapters — LoL (multiplier vs. cap ladder),
Indemnification (exposure multiplier), Termination (fee multiplier) — all
three sharing the identical "value ≤ preferred → ACCEPT; ≤ acceptable →
ACCEPT_WITH_NOTE; ≤ negotiate → NEGOTIATE; else ESCALATE" four-tier,
monotonic, "smaller is better" shape.

The other three adapters correctly do **not** use it, for real structural
reasons rather than oversight:

- **Confidentiality's** duration-adequacy check is a *minimum*-threshold
  binary (adequate/inadequate), not a four-tier "smaller is better" ladder —
  inverted direction (bigger duration is better) and a different tier count.
  Forcing this through `classify_by_threshold` would require either
  contorting the comparison direction or padding it with unused tiers.
- **Assignment** has no numeric ladder at all — consent standard and
  exception completeness are categorical checks.
- **Governing Law** has no numeric ladder at all — jurisdiction membership
  is a set lookup, not a threshold comparison.

This is a good confirmation that the *existing* promotion was scoped
correctly: it wasn't generalized further than the adapters that actually
share its exact shape needed, and the three adapters that don't share that
shape were not forced to pretend they do. No changes recommended.

---

## 7. Negotiation ladders — **A** (core) / **D** (adapter wording), already correctly split

`build_ladder`/`LadderStep` (core) plus each adapter's own `_build_ladder`
wrapper — which builds five `(label, description)` tuples in clause-specific
language and hands them to the core function for passed/current/not-reached
positioning — is used by all six adapters with zero further duplication
worth removing. The split is already exactly right: core owns the
state-to-ladder-position mapping (pure mechanics, zero clause knowledge),
each adapter owns the description text (100% clause-specific: "annual fees"
vs. "exposure cap" vs. "termination fee" vs. "confidentiality terms" vs.
"jurisdiction"). Tightening this further — e.g., making the core function
also own the step count or generic label names — would be exactly the kind
of forced conformity the review was told to avoid, for no duplication
savings (the descriptions were never going to be shareable text). No changes
recommended.

---

## 8. Cross-reference resolution — **D**, not duplicated in any meaningful sense

Only LoL has real cross-reference *resolution*: `_detect_cross_reference` +
`_resolve_cross_reference` — detect a delegation phrase naming a target
(Schedule/Exhibit/Appendix/Section/Order Form/DPA), search the full document
for that label outside the current provision, extract nearby cap values,
resolve deterministically only if unique or all-agreeing, else return a
named reason.

Indemnification has only cross-reference *detection* — `MonetaryTreatment`'s
`cross_reference` kind captures the referenced label via a single regex and
deliberately does **not** search the document or attempt resolution; it
always routes to `REQUIRES_REVIEW`. This was a documented, deliberate design
choice from the original Indemnification build (the `xref-01`/`xref-02`
corpus cases were labeled `REQUIRES_REVIEW` on purpose), not an
under-implementation of LoL's mechanism.

Termination, Confidentiality, Assignment, and Governing Law have no
cross-reference concept at all.

**With one real implementation and one adapter that deliberately chose a
simpler cousin, there is nothing here to eliminate or promote.** A shared
"detect + resolve a document-wide reference" primitive would be pure
speculation with n=1 real consumer. If a future clause (a Batch B or C
clause that commonly says "see the Insurance requirements in Exhibit B," for
example) needs real resolution rather than detection-only, that would be the
second data point that makes this worth revisiting — not before.

---

## 9. Window / boundary handling — mixed: **A** for two pure utilities, **B** for the bounded-local-window idiom, **D** for provision-discovery/reconciliation

**`_excerpt(text, start, end, pad)`** — word-boundary-trimmed excerpt
extraction for human-readable evidence quotes. Byte-for-byte identical
across all six adapters, including Governing Law. Zero adapter-specific
parameters, zero semantic content. This is the cleanest possible promotion
candidate in the entire review — genuinely **A**, and simultaneously a
textbook **C** (accidental, valueless duplication) — the two classifications
coincide here because there is no meaningful parameterization to argue
about.

**`_section_label_before(text, anchor_start)`** — finds the last 1–3 digit
(optionally decimal) number in the ~30 characters before an anchor, to label
"Section 12." Also byte-for-byte identical across all six adapters,
including Governing Law. Same classification: **A**/**C**.

**The "local window bounded at the next sentence period" idiom**
(`_local_clause_window` in Indemnification/Termination/Confidentiality/
Assignment, and an inline equivalent embedded in LoL's `_classify_category`)
— structurally identical mechanics (search a boundary regex within
`max_chars`, fall back to `max_chars` if none found) with a **genuinely
varying parameter**: which boundary regex counts. Termination deliberately
cuts at `. ` only (semicolons must NOT end a window, because a differentiated
proviso is conventionally semicolon-joined to its reciprocal opener — this
was a real bug found and fixed during the Termination build). Confidentiality
and Assignment now cut at the *next role-attribution match*, not just a
sentence boundary (the window-bleed fix from §2). This is **B**: the search-
with-fallback skeleton is shareable, but treating "what counts as a
boundary" as a hardcoded regex rather than a parameter would be exactly the
kind of behavior-flattening the review was warned against, since that
choice has already been shown to matter (twice, as real bugs). If promoted,
it must take the boundary pattern as an argument, not assume one.

**Provision/window discovery and multi-provision reconciliation** — LoL's
document-wide anchor discovery (with a 300-char anchor-dedup gap) plus
amendment-supersession / consistent-duplicate / unreconciled-conflict
reconciliation has no equivalent anywhere else, and should not: it exists
because LoL's model is "there is exactly one true general cap, and multiple
mentions are competing candidates to be reconciled into one." Indemnification,
Termination, Confidentiality, and Assignment do the opposite by design —
every matched item is independently true and none of them reconcile
obligations/rights/protections/restrictions into a single controlling
provision, because that would be semantically wrong for a "catalog of
independently-true facts" clause. This is the same **comparative-value vs.
catalog-of-independent-facts** distinction this project has reported at
every prior architecture checkpoint. Correctly **D** on both sides — LoL's
reconciliation machinery is not under-shared, it is inapplicable to the
other five by construction.

**Governing Law check:** has essentially no windowing machinery beyond the
two universal utilities — one `.search()` call across the whole document,
no provision-window concept at all, because there is exactly one
governing-law statement to find, never several competing or independently-
true ones. This is the cleanest possible confirmation that the "provision
window" family of mechanisms (LoL's discovery+reconciliation, the four
adapters' local-window idiom) is genuinely optional machinery some clause
shapes need and others simply do not — nothing here should be forced onto
it, and nothing was.

---

## Summary table

| # | Mechanism | Classification | Action recommended |
|---|---|---|---|
| 1 | Directed role resolution (whole) | B | None — keep adapter-local; the singular-slot-with-conflict vs. list-accumulation difference is real |
| 1a | `mutual`/`named` split + mutual-policy-conflict reason | A | Promotable in isolation, low risk |
| 2 | Reciprocal symmetry verification | **A** | **Strongest candidate** — parameterized core helper, proven bug-surface argument |
| 3 | Typed monetary/value expressions (whole) | D | None — LoL's compound/basis richness and Indemnification's cross-reference-as-kind are real design divergences |
| 3a | Low-level scalar-or-unlimited regex parsing | B | Not yet — revisit with a 4th true monetary consumer (e.g. Payment Terms) |
| 4 | Evidence/provenance (`PolicyDecision`, evidence report) | A (done) | None — already correctly promoted and holding |
| 5 | Abstention / REQUIRES_REVIEW decision construction | **A** | Promotable — pure formatting helper, six near-identical call sites |
| 6 | Threshold classification | A (done) | None — correctly promoted and correctly not over-adopted |
| 7 | Negotiation ladders | A (core) / D (wording) | None — already correctly split |
| 8 | Cross-reference resolution | D | None — one real consumer, one deliberate simpler cousin, not duplication |
| 9a | `_excerpt`, `_section_label_before` | **A** / C | **Trivial, safe promotion** — byte-identical across all six including Governing Law |
| 9b | Bounded-local-window idiom | B | Promotable only if boundary regex is a parameter, not hardcoded |
| 9c | Provision discovery & reconciliation | D | None — LoL-specific by construction, inapplicable elsewhere |

---

## If promotions were authorized (not being done now)

In priority order, by duplication-removed-per-risk-taken:

1. **`_excerpt` / `_section_label_before`** (§9a) — zero risk, zero semantic
   change, six call sites become one each.
2. **Reciprocal-symmetry-verification skeleton** (§2) — moderate
   implementation effort, highest payoff, and directly closes the gap that
   already caused one bug to require manual, proactive porting across
   adapters instead of being fixed once.
3. **REQUIRES_REVIEW decision construction** (§5) — low risk, moderate
   payoff, purely a formatting helper.
4. **`mutual`/`named` split fragment** (§1a) — low risk, small payoff, worth
   bundling with #2 since they touch the same functions.

Explicitly **not recommended**: unifying the typed monetary/value systems
(§3), unifying `resolve_directional_position` with the four adapters'
resolve-for-side functions (§1), or promoting cross-reference resolution
(§8). Each would either force a real design choice onto an adapter that made
a different one deliberately, or speculate ahead of the evidence.

## One open item surfaced by this review, not acted on

The window-bleed fix (§2, §9b) was applied to Assignment (where it was
found) and proactively ported to Confidentiality (checked and fixed before
its own benchmark exposed it) during the Batch A session. This review did
**not** re-verify whether Indemnification's `_detect_reciprocal_asymmetry`
or Termination's `_detect_right_asymmetry` — both written before that fix
existed — have the same latent defect. Per this review's own "no behavior
changes" scope, that check (and any resulting fix) is intentionally left
for separate, explicit authorization rather than folded into this document.
