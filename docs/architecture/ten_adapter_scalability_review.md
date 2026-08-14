# Ten-Adapter Scalability Review

**Scope**: fresh architecture review across all ten deterministic policy adapters
(`liability`, `indemnification`, `termination`, `confidentiality`, `assignment`,
`governing_law`, `data_security`, `ip_ownership`, `insurance`, `payment_terms`),
`policy_engine_core.py`, the policy schema (`models.py`/`playbook_authoring.py`),
and the full Playbook workflow (Workbench, review queue, Phase 2/3 extraction,
Phase 4 enforcement), performed before starting adapters #11 (Warranties) and
#12 (SLA / Service Levels).

**Method**: every one of the ten `*_policy_engine.py` files was read in full,
along with `policy_engine_core.py`, `models.py`, `playbook_authoring.py`,
`playbook_workbench.py`, `review_queue.py`, `playbook_extraction.py`,
`playbook_ai_extraction.py`, and `policy_enforcement.py`. Several bug-class
claims below were independently reproduced live against the current code
(not inferred from comments) — those are marked **[verified live]**.

No code was changed to produce this document.

---

## 1. Adapter architecture

### 1.1 Recurring reasoning shapes

Five genuinely distinct shapes recur across the ten adapters — not ten
different problems, five:

| Shape | Adapters | Characteristic |
|---|---|---|
| **Comparative single value, reconciled to one controlling provision** | `liability` | Multiple mentions of the same fact (a cap) must collapse to one answer; amendment/supersession and cross-reference resolution exist specifically because there can only be one correct cap. |
| **Directed obligation, possibly reciprocal, NOT reconciled** | `indemnification`, `termination` (rights), `confidentiality`, `assignment` | Two obligations pointing in different directions are two independently true facts, not a conflict. All four resolve "ours" vs. "theirs" via `contract_side`, and all four need a symmetry/asymmetry check for the reciprocal case. |
| **Catalog of independent commercial-economic facts** | `insurance` (six coverage types), `payment_terms` (ten dimensions), `data_security` (nine requirement axes), `ip_ownership` (fourteen license/ownership axes) | No single "clause_type = acceptable" verdict; each dimension is extracted and evaluated independently, several of which are also directional (who owes what to whom) nested inside the catalog. |
| **Uniform, non-directional** | `governing_law` | Applies identically to both parties; there is no "our side" to resolve. The only adapter of the ten with no `contract_side` resolution logic at all. |
| **Enumerated-topic checklist** | present as a sub-shape inside `confidentiality` (exclusions), `termination` (survival topics), `ip_ownership` (license terms), `liability`/`indemnification` (carve-out categories) | A closed vocabulary of tokens, each independently present/absent, validated against `_BOUNDED_VOCABULARIES`. |

`governing_law`'s own module docstring states this most directly, and is worth
quoting because it is the adapter that proves the others' shared shape is a
choice, not an accident: *"governing law... applies UNIFORMLY to both
parties — there is no 'our side vs. their side' to resolve at all... a
deliberate, honest architecture data point... not every clause needs that
shape."*

### 1.2 Duplicated extraction mechanisms — classified

**Case-sensitive party-name capture.** The pattern `(?-i:([A-Z][A-Za-z]{2,30}))`
(or a hand-rolled equivalent) appears independently in `liability`,
`indemnification`, `termination`, `confidentiality`, `assignment`, `insurance`,
and `payment_terms` — seven of ten adapters, always solving the identical
problem (a party name must look like a capitalized defined term, and the
overall regex is compiled with `re.I` for its verb phrases, which would
silently defeat `[A-Z]` without an explicit case-reset). `liability` alone
uses a different but equally correct technique (the whole pattern compiled
*without* `re.I`, with only the verb-phrase literals wrapped in `(?i:...)`).
This is genuinely the same problem solved seven-plus times with two
techniques, one of which has already been reintroduced buggy at least once
(§2.1).
**Classification: PROMOTE NOW** — not as a shared regex (the surrounding
verb phrases are irreplaceably clause-specific), but as a single documented
constant/snippet in `policy_engine_core.py` (e.g. `_PARTY_NAME_FRAGMENT =
r"(?-i:([A-Z][A-Za-z]{2,30}))"`) that every adapter's name-capture regex
interpolates, plus one comment explaining the hazard once instead of eight
times. This removes the only realistic way this bug class reappears: a new
author typing the pattern from memory instead of copying a working one.

**Local-window / sentence-boundary scoping.** Three independent
implementations exist:
- `termination_policy_engine._right_window` — cuts at the first `". "`
  boundary, deliberately *not* at `";"` (documented rationale: differentiated
  per-party provisos are semicolon-joined and the asymmetry check needs the
  full clause).
- `insurance_policy_engine._local_window` — cuts at the first `.` or `;`
  found via `text.find()`, naive character search.
- `payment_terms_policy_engine._local_window` — cuts at the first `.` or `;`
  found via a regex with a negative lookaround (`(?<!\d)\.(?!\d)`) so a
  decimal point inside a number (`1.5%`) is not mistaken for a sentence
  boundary.

These are not interchangeable — `termination`'s deliberately-not-`;`
behavior is load-bearing for its own domain, and payment_terms's decimal-safe
version was written specifically *because* the naive version (structurally
identical to insurance's current one) truncated windows mid-number. See §2.1
for why this is not just a taxonomy note but a live finding.
**Classification: PROMOTE NOW** for the payment_terms's decimal-safe
sentence-boundary regex specifically — it strictly dominates the naive
version (same behavior on every input that doesn't contain a decimal point
inside the scoped range, correct behavior where the naive version is wrong).
`termination`'s different-on-purpose window stays adapter-local
(**KEEP ADAPTER-LOCAL**) since its"don't cut at `;`" behavior is a genuine
domain difference, not an oversight.

**Forward-coverage-span exclusion-window logic.** `liability`'s
`_compute_exclusion_coverage` and `indemnification`'s `_classify_triggers`
implement near-identical mechanics (sentence/semicolon boundary detection,
plus an "and"-followed-by-a-new-cap-trigger truncation heuristic tuned
against named regression cases in each file). Both files carry an explicit
comment stating the duplication is deliberate: indemnification's docstring
says *"Deliberately reimplemented here rather than imported — the category
vocabulary is clause-specific... opposite polarity, not the same concept
wearing a different name."*
**Classification: POSSIBLE LATER.** The original authors already considered
and rejected promoting this once, with a stated reason. That reasoning is
plausible but was made with two data points; it should be revisited once a
third adapter needs the same forward-coverage-span mechanic (a real
candidate: Warranties' "except for" carve-outs from a warranty, see §9),
not decided again from scratch. Until then, KEEP ADAPTER-LOCAL is the
correct default per the prior authors' own documented judgment call.

**Accumulate-then-resolve conflict detection.** Present independently in
`liability` (`_find_cap_values`), `indemnification` (obligations list +
monetary-key conflict), `termination` (rights list, dedup by span),
`confidentiality` (obligations list + `_monetary_key` conflict guard),
`insurance` (dollar-amount lists resolved once per coverage type), and
`payment_terms` (every numeric/token dimension). This is a *pattern*, not
literal duplicated code — the "value" being accumulated differs by adapter
(a `CapValue`, a dollar amount, a day-count, a token set), so there is no
single function to extract. **Classification: KEEP ADAPTER-LOCAL** as code,
but the discipline itself (never resolve inside the same loop that finds
candidates; resolve once, after, from the full candidate set) is exactly
the kind of institutional knowledge that should live in a short
`CONTRIBUTING`-style note for adapter authors rather than be re-derived by
each new adapter from a benchmark failure — it already has been, at least
three times (see §2, `assignment`'s gap is exactly this discipline half-applied).

### 1.3 Duplicated role/direction resolution

`policy_engine_core.py` exports a generic solution for this
(`PositionCandidate` + `resolve_directional_position` + `side_for_role`), but
it is used by exactly **one** adapter (`liability`). Every other directional
adapter reimplements its own resolver with a different name and a
different return shape:

| Adapter | Function | Return shape |
|---|---|---|
| `liability` | `_resolve_directional_position` (wraps core) | one winning `CapExpression` + two position dicts |
| `indemnification` | `_resolve_obligations_for_side` | `(exposure, protection, reasons)` — two full obligation objects |
| `termination` | `_resolve_rights_for_side` | `(our_rights, their_rights, reasons)` — two lists |
| `confidentiality` | `_resolve_obligations_for_side` | `(exposure, protection, reasons)` — structurally same shape as indemnification's but a separately maintained function |
| `assignment` | `_resolve_restrictions_for_side` | `(our_restriction, their_restriction, reasons)` |
| `data_security` | `_resolve_our_role` | `(role, ambiguous: bool, unresolved: bool)` |
| `ip_ownership` | `_resolve_owner` | `(owner_side, unresolved: bool)`, called once per IP category |
| `insurance` | `_resolve_obligated_party` | `(party_side, unresolved: bool)`, called once per coverage type |
| `payment_terms` | `_resolve_payor_side`, `_resolve_tax_responsibility` | `(side, unresolved: bool)` |

Every one of these follows the same three-step algorithm underneath: map a
named party to `buy_side`/`sell_side` via `side_for_role`, compare against
`policy.contract_side`, and either assign a candidate to "ours"/"theirs" or
append an unresolved reason when the mapping is ambiguous, unmappable, or
conflicting. `side_for_role` itself is imported and actually called by seven
of the nine directional adapters; `liability` alone re-implements the same
lookup inline rather than calling the function it already imports — a small,
harmless, but real instance of not using an existing shared primitive.

**Classification: POSSIBLE LATER, not PROMOTE NOW.** The algorithmic shape
is genuinely identical nine times over — a strong signal — but the *payload*
type varies enough (single value vs. paired objects vs. paired lists vs.
dict-of-per-category flags) that a literal shared function would need either
a generic-over-T design or would have to give up some of these adapters'
specific conflict-key comparisons (`_monetary_key`, coverage-amount
resolution, etc.). `resolve_directional_position`/`PositionCandidate`
already exist in core specifically to be this abstraction and are used by
only one of nine eligible callers — that is itself evidence the original
generalization was scoped too narrowly around `liability`'s single-cap case
to fit the others without change, not evidence that generalizing is
pointless. Recommend: before building adapter #13, spend a short focused
pass generalizing `resolve_directional_position` to accept a
caller-supplied conflict-key function and multi-slot output (ours/theirs
each being 0..N candidates, not exactly one), and retrofit two or three of
the simpler existing resolvers (`insurance`, `payment_terms`) against it as
a real second/third proof before touching the more bespoke ones
(`indemnification`, `termination`). Doing this now, mid-Warranties/SLA,
would be scope creep against this review's own "do not implement" instruction
— it is explicitly a POSSIBLE LATER, not a blocker.

### 1.4 Document-wide reconciliation

Only `liability` has genuine document-wide reconciliation: it finds every
LoL-anchored provision, classifies each as amendment-flagged or not, and
picks the last amendment-flagged provision as controlling when one exists,
otherwise checks all provisions agree (`"consistent_duplicate"`) or reports
`"unreconciled"`. No other adapter has an equivalent
amendment-supersession mechanism — confirmed for `indemnification`
(explicit design choice, documented: obligations are never reconciled into
one, by design, since two directional obligations aren't in conflict),
`termination` (same "non-reconciliation discipline" for rights),
`confidentiality`, `assignment`, `governing_law` (first-match-only, no
multi-provision handling at all), and confirmed by direct grep for
`data_security`, `ip_ownership`, `insurance`, `payment_terms` — none of the
four adapters built this session contain `_AMENDMENT_SIGNAL_RE` or any
supersession-aware logic.

This is not a bug in nine adapters — for the directed-obligation-graph
shape, "don't reconcile, evaluate every direction independently" is the
*correct* design, not a missing feature. But for the catalog-of-facts shape
(`insurance`, `payment_terms`, `data_security`), a genuine amendment (e.g.
"Section 9 is hereby amended to change Net 30 to Net 45") produces no
amendment-aware resolution at all today — it is caught only incidentally,
by the generic accumulate-then-resolve conflict machinery treating the two
different Net-day values as a plain conflict and routing to
REQUIRES_REVIEW. That is a safe fallback (never a false-safe), but it means
`liability` is the only adapter that can give a *correct, deterministic*
answer for an amended numeric term; the other nine correctly abstain
instead. Worth naming precisely because it is easy to describe as "still
missing amendment handling" (true) versus "unsafe" (false) — the two are
different findings and only the first one is real.
**Classification: POSSIBLE LATER** for the specific mechanism (amendment
signal + "last amendment wins" resolution) generalized beyond `liability`,
gated on whether Warranties/SLA drafting in practice shows amendments to
numeric terms often enough to be worth it — no evidence either way yet.

### 1.5 Cross-reference handling

Two independent, non-equivalent implementations exist. `liability`'s
`_resolve_cross_reference` is the more capable one: given a Schedule/
Exhibit/Order Form/DPA/Section label, it searches the *entire remaining
document* for other occurrences of that label and attempts to resolve a
cap value from context, reporting ambiguity (not guessing) if multiple
distinct values are found. `indemnification`'s `_MONETARY_CROSS_REF_RE`
recognizes only one narrow pattern (delegation to the LoL clause's cap via
"subject to the limitation of liability... in Section N") and never
attempts resolution — any such delegation is treated as unresolved outright.
No Schedule/Exhibit/Order Form/DPA pattern exists in `indemnification` at
all. None of `termination`, `confidentiality`, `assignment`,
`governing_law`, `data_security`, `ip_ownership`, `insurance`, or
`payment_terms` have cross-reference resolution logic — `payment_terms`
has a `_SCHEDULE_CROSSREF_RE` presence-detector only (flags that material
terms may be delegated elsewhere, routes to REQUIRES_REVIEW), not a
resolver.
**Classification: KEEP ADAPTER-LOCAL for now.** `liability`'s
document-wide resolver is meaningfully more sophisticated than the "detect
and abstain" pattern used everywhere else, and that gap is intentional —
building a real resolver requires knowing what shape of value to look for
(a cap? a coverage amount? a warranty period?), which is clause-specific.
The "detect the delegation, don't guess, route to REQUIRES_REVIEW" half of
this, however, is exactly the kind of shared micro-pattern that is worth a
one-line note in a contributor doc, not a shared function.

### 1.6 Typed numeric/monetary representations

Not uniform, and that is appropriate: `liability`'s `CapExpression`/
`CapValue` is a genuinely compound structure (simple / greater-of /
lesser-of / per-claim-and-aggregate / unresolved) because LoL clauses
actually draft compound caps. `indemnification`'s `MonetaryTreatment` is
deliberately flatter (multiplier / fixed / unlimited / cross_reference /
not_stated, exactly one per obligation, no compound structures) because
indemnification obligations don't draft compound monetary treatments the
same way. `insurance`'s `CoverageRequirement` carries per-occurrence and
aggregate dollar amounts as two plain optional floats, no expression type,
because coverage limits genuinely are just two numbers. `payment_terms`
has no compound type at all — every numeric fact (net days, late-fee
percent, price-increase percent) is a plain `Optional[float]` plus a
`_conflict: bool` sibling flag.
**Classification: KEEP ADAPTER-LOCAL.** This is the review's clearest
example of surface-similar code (four dataclasses of "a number with some
metadata") that is not semantically equivalent — the compound-expression
need is real and specific to `liability`, and forcing the other three into
`CapExpression`'s shape would require most of them to always populate a
one-element `components` list, buying nothing.

### 1.7 Evidence/provenance construction

Fully uniform and already correctly centralized. Every adapter's
`PolicyDecision` (from `policy_engine_core.py`) carries the same
`contract_language` / `start_index` / `end_index` /
`controlling_provision: {label, excerpt, start_index, end_index}` /
`our_position` / `counterparty_position` shape, and every adapter's
intermediate `*Facts`/per-provision dataclass carries `raw_excerpt` /
`start_index` / `end_index` / `section_label`. The three label fields
(`summary_label`, `our_position_label`, `counterparty_position_label`) are
deliberately overridable per adapter with LoL's original wording as the
default, per an explicit comment in `policy_engine_core.py` — this is the
single cleanest example in the codebase of "generalize the shape, let each
adapter override only the words," and it has held across all ten adapters
without a single adapter needing to escape the shape.

### 1.8 REQUIRES_REVIEW construction

Structurally consistent across all ten, though not literally shared code:
every adapter has (a) zero, one, or two dedicated early-return
short-circuits for structural failures (no clause found → `NOT_APPLICABLE`;
clause word present but nothing parseable → immediate `REQUIRES_REVIEW`;
`liability`'s unreconciled-provisions case is a second, adapter-specific
early return), followed by (b) one accumulate-then-check gate
(`unresolved_facts: List[str]`, built up across every dimension being
evaluated, checked once with a single `if unresolved_facts:` before the
adapter's normal scoring logic runs). `governing_law` is the one partial
exception: its single REQUIRES_REVIEW branch (jurisdiction anchor found but
no jurisdiction parsed) uses a fixed string rather than the shared
`requires_review_explanation`/`requires_review_required_action` helpers —
documented in its own module comment as intentional, since there is no
list of unresolved facts to enumerate for a single-fact adapter.
**Classification: shape is already effectively promoted** (via the shared
`requires_review_explanation`/`requires_review_required_action` helpers
used by nine of ten adapters) — no further action needed.

### 1.9 Abstention patterns

`NOT_APPLICABLE` (no clause found) vs. `REQUIRES_REVIEW` (clause found,
something unresolved) is applied identically in all ten adapters — this
binary is itself the load-bearing abstention primitive of the whole system
and every adapter respects it without exception.

### 1.10 Duplicated regex/windowing infrastructure — summary table

| Mechanism | # independent implementations | Status |
|---|---|---|
| Case-sensitive party-name capture | 7-8 | PROMOTE NOW (shared fragment/constant) |
| Local-window sentence-boundary scoping | 3 (one still buggy) | PROMOTE NOW (the fixed version) |
| Forward-coverage-span exclusion window | 2 | POSSIBLE LATER (already reconsidered once) |
| Accumulate-then-resolve discipline | 6+ | KEEP ADAPTER-LOCAL (as code); document as convention |
| Named-party → our/their side resolution | 9 | POSSIBLE LATER (generalize core's existing but underused primitive) |
| Document-wide amendment/supersession | 1 (`liability` only) | POSSIBLE LATER |
| Cross-reference resolution (vs. detection) | 1 real resolver (`liability`), rest are detect-only | KEEP ADAPTER-LOCAL |
| Compound numeric/monetary types | 0 shared, 4 different shapes | KEEP ADAPTER-LOCAL (correctly) |
| Evidence/provenance shape | 1 shared (`PolicyDecision`) | Already correctly promoted |
| REQUIRES_REVIEW construction shape | 1 shared (helpers) + 1 documented exception | Already correctly promoted |

---

## 2. Bug classes still present in other adapters

Section 1 above already surfaces two of these; this section makes them the
explicit, standalone findings the review asked for, plus what was checked
and found clean.

### 2.1 Extraction-window bleed via a stale sentence-boundary implementation — LIVE, in `insurance_policy_engine.py`

`insurance_policy_engine._local_window` (lines ~239–251) still uses the
naive implementation:

```python
def _local_window(text: str, start: int, other_anchor_positions: List[int], max_radius: int = 400) -> str:
    end = min(len(text), start + max_radius)
    for stop_char in (".", ";"):
        idx = text.find(stop_char, start, end)
        if idx != -1:
            end = min(end, idx + 1)
    ...
```

This is the exact mechanism whose bug was found and fixed in
`payment_terms_policy_engine._local_window`, which replaced the naive
`.find(".")` scan with a negative-lookaround regex
(`_SENTENCE_END_RE = re.compile(r"(?<!\d)\.(?!\d)|;")`) specifically because
a decimal point inside a number (payment_terms's case: `"1.5%"`) was being
read as a sentence boundary and truncating the window before the actual
fact could be captured.

`insurance_policy_engine._DOLLAR_RE` explicitly supports decimal dollar
amounts (`r"\$\s?([\d,]+(?:\.\d+)?)\s*(million|M\b)?"`) — i.e. the same
shape of value ("$2.5 million") that would trigger the identical bug is a
first-class supported input to this adapter, not a hypothetical. The
current 79-case insurance corpus does not happen to include a case that
requires the window to extend *past* a decimal-valued dollar figure to
reach a subsequent qualifier (e.g. "$2.5 million, per occurrence" where the
qualifier is far enough after the decimal that truncation would drop it),
so the bug is latent, not benchmark-visible today. This is precisely the
review's instruction: *"Determine whether any equivalent bug class still
exists in another adapter. Report it; do not fix it."* — reported here,
not fixed.

### 2.2 Case-insensitive regex defeating a case-sensitive assumption — LIVE, in `governing_law_policy_engine.py` **[verified live]**

`_JURISDICTION_RE` and `_VENUE_RE` both compile with `re.I` and both capture
a jurisdiction/venue name via `[A-Z][A-Za-z\s]{2,30}?` with **no**
`(?-i:...)` case-reset around the capture group — unlike every other
adapter's party-name captures, all of which either avoid a blanket `re.I`
entirely (`liability`) or explicitly reset case-sensitivity with
`(?-i:...)` (`indemnification`, `termination`, `confidentiality`,
`assignment`, `insurance`, `payment_terms` — several of those files carry
an inline comment citing this exact hazard as "already fixed elsewhere in
this file"/"already fixed twice in indemnification_policy_engine.py").
`governing_law` never received that fix. Reproduced directly against the
current code:

```
>>> governing_law_policy_engine._JURISDICTION_RE.search(
...     "This Agreement shall be governed by the laws of the state of "
...     "new york, without regard to conflicts of law principles.")
...     .group(1)
'new york'
```

The `[A-Z]` was presumably intended as a light heuristic gate — "only
treat this as a real jurisdiction name if it looks like a proper noun" —
and under `re.I` that gate is silently inert. The practical risk is
narrower than the party-name version of this bug (there is no "us vs.
counterparty" misattribution possible here, since `governing_law` has no
directionality), but it does mean informally-cased or OCR'd jurisdiction
language is confidently extracted rather than failing to match or routing
to `REQUIRES_REVIEW` — the same "silently proceeds instead of abstaining"
shape as every other instance of this bug class.

### 2.3 Conflicting provisions silently overwritten — LIVE, in `assignment_policy_engine.py`

`assignment_policy_engine._resolve_restrictions_for_side` assigns
`our_restriction = r` / `their_restriction = r` inside its resolution loop
with no check for a prior assignment on the same side:

```python
elif r.restricted_side == contract_side:
    our_restriction = r          # second match on our side silently replaces the first
```

Compare this to the sibling function one file over,
`confidentiality_policy_engine._resolve_obligations_for_side`, which
handles the structurally identical situation correctly:

```python
if exposure is not None and _monetary_key(exposure) != _monetary_key(o):
    reasons.append("...")        # conflict is flagged, not silently overwritten
elif exposure is None:
    exposure = o
```

Both functions solve the same problem (accumulate named directional facts,
then assign the first one matching "our side" and the first matching
"their side," across a document that may state the restriction/obligation
more than once). `confidentiality` gets it right; `assignment`, written to
the same pattern, does not carry the same guard. This is exactly the "a
contract with two named assignment restrictions on the same side, with
different consent standards" case the review asked about, and it is
currently unhandled — the second-mentioned restriction wins with no
REQUIRES_REVIEW routing and no note that a conflict existed.

### 2.4 Checked and found clean

- **Adjacent-sentence attribution**: the shared core primitive
  `detect_role_attributed_asymmetry` (used by `indemnification`,
  `termination`, `confidentiality`, `assignment`) bounds each role's local
  snapshot to the next attribution match or a sentence boundary — this was
  the mechanism whose original bug ("next-attribution-bounded local
  window") was found and fixed once (in `confidentiality`, per its own
  comment) and then centralized; all four current users share the fix.
  `liability` never needed this mechanism (no reciprocal concept) and
  correctly doesn't use it.
- **Negation interpreted as affirmative**: every adapter that scans for
  clause presence via an `_ANCHOR_RE` filters out anchors immediately
  preceded by `"no "` (`\bno\s+$` lookback), consistently, across
  `termination`, `confidentiality`, `assignment`, `indemnification`
  (plus `indemnification`'s additional document-wide
  `_EXPLICIT_NO_OBLIGATION_RE` for the "mentioned once, negated in a
  separate sentence" case). `insurance` and `payment_terms` (built this
  session) carry adapter-specific negation guards for their own affirmative
  presence checks (e.g. "shall not be named as an additional insured,"
  "disputed amounts may not be withheld"). No gap found.
- **Percentages attributed to the wrong commercial dimension**: this exact
  bug class was found and fixed *within* `payment_terms` during its own
  build (late-fee-rate vs. price-increase-rate percentages colliding) via
  dimension-specific anchor scoping (`_INTEREST_ANCHOR_RE` /
  `_PRICE_INCREASE_ANCHOR_RE`). No other adapter extracts two
  independently-meaningful percentages from the same document region, so
  the specific collision cannot recur elsewhere today — but the
  *mechanism* (anchor a local window on a dimension-specific trigger
  phrase before extracting a bare number) is the correct general answer if
  Warranties or SLA introduce a second same-shaped numeric fact (see §9).
- **Numeric cross-contamination across coverage/dimension types**:
  `insurance` (`_local_window` + `other_anchor_positions` bounding one
  coverage type's dollar figures away from the next) and `payment_terms`
  both have dedicated scoping for this; `liability`'s `_ANCHOR_DEDUP_GAP`
  and per-role `_find_party_positions` serve the same purpose for cap
  values. No un-scoped multi-value extraction found elsewhere.
- **Role attribution ambiguity**: every directional adapter routes to
  `REQUIRES_REVIEW` rather than guessing when a named party cannot be
  mapped to a side — verified present in all nine directional adapters'
  resolver functions (§1.3 table). No adapter defaults an unmappable role
  to "ours" or "theirs."

---

## 3. Policy schema scalability

### 3.1 Current schema

`PolicyPosition` stores one JSON blob (`config_json`) per position, plus
three real columns shared by every clause type (`contract_side`,
`escalation_approval_authority`, `fallback_text`). Field-level
status/provenance lives in a **separate**, parallel table,
`PolicyPositionField` (one row per field name, carrying `status`, `source`,
`value_json`, evidence pointers, and append-only supersession via
`superseded_by_field_id`). `clause_type` is a free `String(64)` column with
**no DB-level enum/FK/CHECK constraint** — validity is enforced entirely in
`playbook_authoring.py` (`CLAUSE_TYPES = tuple(_ENGINE_PROTOCOLS)`).

The genuinely load-bearing scalability property of this design: **the
config schema for a clause type is never hand-declared anywhere in the
database or authoring layer.** `CLAUSE_TYPE_CONFIG_FIELDS` and
`ACTIVATION_REQUIRED_FIELDS` are both mechanically derived from each
adapter's own `*PolicyRuleLike` Protocol via `typing.get_type_hints()` —
adding adapter #11 means writing one Protocol in one new engine module and
registering it in one dict (`_ENGINE_PROTOCOLS`); the config schema,
activation-readiness rule, and validation all follow automatically with no
separate schema to keep in sync.

### 3.2 Can this cleanly support #11 (Warranties) and #12 (SLA)?

**Yes, for the two mechanically-derived pieces** — a Warranties or SLA
Protocol with its own boolean/float/Optional[str] fields will produce a
correct `CLAUSE_TYPE_CONFIG_FIELDS` entry and a correct
`ACTIVATION_REQUIRED_FIELDS` entry with zero schema changes, exactly as it
did for adapters #7–#10.

**No, not without touching hand-maintained code**, for everything else —
and this is the review's most important schema finding. Nine distinct
places in `playbook_authoring.py` require a manual, adapter-specific
addition for every new clause type, only two of which (`_ENGINE_PROTOCOLS`
registration and the one-line `BUILDERS` wrapper) are *inherent* to the
architecture (an adapter's engine module must be imported and its builder
registered somewhere). The other seven are accumulating, not shrinking, as
adapter count grows:

1. `_BOUNDED_VOCABULARIES` — per-clause-type dict entries, hand-written,
   pulling from each engine's own vocabulary constants.
2. `CLAUSE_TYPE_LABELS` — one hand-written string per clause type.
3. `CLAUSE_TYPE_IMPORTANCE` — a fixed, hand-ordered tuple with a
   hand-written prose paragraph justifying each addition's rank (four such
   paragraphs already exist, one per adapter #7–#10).
4. `FIELD_LABELS` — nested dict, one hand-written plain-English label per
   config field, per clause type (currently ~140 entries across ten
   clause types and growing linearly with field count).
5. `_SUMMARIZERS` / the ten independent `_summarize_<clause>` functions —
   one hand-written function per clause type enumerating every field.
6. A one-off `if clause_type == "governing_law" and field_name == ...`
   special-case branch inside `_parse_config_field` for the one field
   (`required_dispute_resolution`) whose form value needs bespoke parsing.
7. One new Jinja template per clause type
   (`templates/policy_position_fields/<clause>.html`), hand-written,
   confirmed for adapters #7–#10 in this session (each required a new
   template file with no shared macro covering the bounded-vocabulary
   radio-group pattern beyond the shared `tristate`/`number_input` macros).

None of these seven is a *correctness* risk in the way §2's bug classes
are — a missing `FIELD_LABELS` entry, for example, would show up
immediately as a broken form, not a silent misclassification. But all
seven are accumulating linear maintenance burden that the Protocol-derived
pieces were specifically designed to avoid, and the module's own docstring
claims the builder conversion logic "is clause-agnostic" without an
equivalent claim for these seven — an honest asymmetry, not a hidden one,
but one worth being explicit about before adapter #11 rather than after.

**Fields/assumptions becoming adapter-specific despite pretending to be
generic**: two are worth flagging directly for Warranties/SLA:

- `_BOUNDED_VOCABULARIES`'s two hand-authored entries
  (`governing_law.required_dispute_resolution`,
  `payment_terms.required_payment_trigger`) are commented, in the source,
  as *"not a Protocol-declared enum — inferred from the literal values the
  engine's own evaluate logic ever compares against."* That inference is
  currently done by a human reading the engine source and hand-transcribing
  the literal strings into a second location. If Warranties or SLA
  introduce another bounded-string field (plausible — e.g. an SLA remedy
  type: `"credit"` / `"termination_right"` / `"both"`), this manual step
  will recur with no compiler check that the two lists ever match.
- `ACTIVATION_REQUIRED_FIELDS`'s derivation rule (`bool` type hint +
  `require_` name prefix ⇒ activation-required) is mechanical and correct,
  but its governing comment explicitly states it *"was verified line-by-line
  for every boolean field in all six Protocols"* — stale text (ten
  Protocols exist today) that was never revisited when adapters #7–#10
  were added, even though the mechanical rule itself continued to apply
  correctly without anyone re-verifying it by hand. This is low-risk today
  (the rule held), but it is exactly the kind of claim that should be
  re-verified, not just re-derived, before Warranties/SLA in case either
  adapter's boolean fields don't cleanly fit the require\_/prohibit\_
  dichotomy the rule assumes (see §9 for why SLA in particular is a
  candidate to break this assumption).

### 3.3 Revision lifecycle and provenance

Sound for #11/#12 with no changes needed. Revisioning is per-`(playbook_id,
clause_type)` "family" of `PolicyPosition` rows (at most one ACTIVE, one
current-editable, the rest ARCHIVED) — this scales by adapter count
trivially since it's keyed generically on `clause_type`. Field-level
provenance (`PolicyPositionField`, append-only, `superseded_by_field_id`)
is likewise generic. Revision pinning for enforcement is handled outside
`playbook_authoring.py` entirely, on `Contract.policy_revision_metadata_json`
(a `{clause_type: {policy_position_id, revision_activated_at, config_hash,
source_type}}` map, keyed generically) — confirmed to require no
clause-type-specific code (§7).

---

## 4. Workbench scalability

### 4.1 What's already generic

The card list, per-card status, and coverage percentage are all correctly
derived from `pa.CLAUSE_TYPES` dynamically — a new `_ENGINE_PROTOCOLS`
entry produces a new card and an updated denominator with zero Workbench
code changes. All twelve-plus authoring/lifecycle/preview/import routes are
already parameterized by a single `{clause_type}` path segment validated
against `pa.CLAUSE_TYPES`, not duplicated per adapter. This part of the
Workbench will not need rework at 12, 20, or 30 adapters.

### 4.2 What will not hold up

The card grid itself is one flat, undifferentiated list — ten cards today,
rendered with no grouping, in whatever order `CLAUSE_TYPES` (i.e.
`_ENGINE_PROTOCOLS` dict insertion order) happens to be. At ten cards this
is still scannable. At twelve it is borderline. At twenty or thirty it
becomes a genuine discoverability problem: a lawyer opening the Workbench
for the first time has no way to know, at a glance, which of thirty cards
correspond to commercial risk they actually care about versus boilerplate
they can safely ignore, and "high-impact gaps" (the one piece of
prioritization that exists) surfaces only non-ACTIVE clause types ranked by
a single fixed, hand-maintained ordering — it doesn't group by category,
it flattens everything into one ranked list.

`CLAUSE_TYPE_IMPORTANCE` is doing double duty it wasn't designed for: it is
simultaneously "the ranking used to prioritize gap warnings" and, by being
the only ordering signal that exists at all, the closest thing today to
"which clause types are related to each other." Neither purpose is served
well by a single flat tuple once the count grows — gap-prioritization needs
a ranking, but discoverability needs a *grouping*, and conflating the two
in one data structure means fixing one will require re-deriving the other.

**Recommendation (not a redesign — per the instruction not to redesign
yet)**: yes, the Workbench needs categories before #12, not after. The five
categories the task proposes (Risk Allocation, Commercial, Data &
Technology, Operational, Legal / Boilerplate) map cleanly onto the existing
ten:

- **Risk Allocation**: `limitation_of_liability`, `indemnification`,
  `insurance`
- **Commercial**: `payment_terms`
- **Data & Technology**: `data_security`, `ip_ownership`
- **Operational**: `termination`, `assignment`
- **Legal / Boilerplate**: `confidentiality`, `governing_law`

This mapping is clean enough, on the existing ten, that it validates the
five-category scheme as workable rather than forcing an awkward fit — a
reasonable signal it will still fit Warranties (Risk Allocation) and SLA
(Operational, arguably Commercial) without inventing a sixth category. The
concrete recommendation is to add a `category` field to each adapter's
registration (wherever `_ENGINE_PROTOCOLS` lives) and use it for card
grouping, while keeping `CLAUSE_TYPE_IMPORTANCE` as a separate,
narrower-scoped signal used only for gap-ranking within (or across)
categories. This is scoped as a genuine, if modest, implementation task,
correctly deferred past this review's "do not implement" boundary — but it
should happen before, not after, #12, since retrofitting categories onto
twelve already-shipped cards is no harder than doing it at ten, and every
adapter added without categories increases the amount of later rework.

### 4.3 Approval workflow, Test Policy, imports, status visibility

All confirmed generic (parameterized by `clause_type`, iterating
`pa.CLAUSE_TYPES`/`_ENGINE_FUNCS` dynamically) and will not need adapter-
count-driven changes at 12, 20, or 30. The one exception worth flagging is
navigational, not architectural: `run_preview` ("Test Policy") and the
import review flows show one clause type at a time — at thirty adapters, a
lawyer running Test Policy across a full playbook has to do so thirty
times with no batch/summary view. That is a genuine future UX gap, but it
is a Workbench UX question, not a schema or engine-architecture one, and is
explicitly out of scope for "do not redesign yet."

---

## 5. Review UX scalability

`review_queue.py`'s merge logic is fully generic today — no clause-type
branching, a single `TIER_RANK` table
(`PROHIBITED`/`MUST_REDLINE`/`ESCALATE` all rank 0, `NEGOTIATE` ranks 1,
`REQUIRES_REVIEW`/`EVALUATION_ERROR` rank 2), sorted stably by
`(tier_rank, original_index)`. Working through the review's conceptual
test cases against this mechanism:

- **12 policies all pass**: works fine — `PASSED_STATES` collapses cleanly
  into a single "N of N passed" summary; no queue noise. Not a scaling
  problem.
- **8 pass / 4 exceptions**: works fine at this ratio — four items sorted
  into at most three tiers is still scannable.
- **12 exceptions (all clause types simultaneously flagged)**: this is
  where the current design starts to strain, not break. Everything at tier
  0 (`PROHIBITED`/`MUST_REDLINE`/`ESCALATE`) is currently
  presented as equally urgent, differentiated only by original array
  order (i.e., by `CLAUSE_TYPES` iteration order, which is adapter
  *registration* order, not risk order) — a `governing_law` `PROHIBITED`
  and a `limitation_of_liability` `PROHIBITED` sit next to each other with
  no visual or structural signal that one is a boilerplate jurisdiction
  mismatch and the other is an uncapped-liability exposure. `TIER_RANK`
  answers "how urgent" but not "how important," and at twelve
  simultaneous top-tier findings the two questions need to be answered
  separately for the queue to stay useful. `CLAUSE_TYPE_IMPORTANCE`
  already exists and already answers "how important" for the Workbench's
  gap-ranking — it is not currently consulted by `review_queue.py`'s
  sort key at all. This is a real, checkable gap: the ranking signal
  exists, it is simply not plumbed into the one place (the review queue)
  where it would matter most as adapter count grows.
- **Multiple REQUIRES_REVIEW**: handled uniformly today (tier 2, sorted
  after all top-tier findings) — no adapter-specific handling exists or is
  needed, since `REQUIRES_REVIEW`'s explanation text is itself
  standardized (`requires_review_explanation`) across nine of ten adapters.
  Scales fine.
- **Multiple PROHIBITED**: same tier-0 bucket as MUST_REDLINE/ESCALATE
  today — at low counts this is fine; at high counts it re-surfaces the
  "how important, not just how urgent" gap above, since a contract can
  plausibly have three or four genuinely PROHIBITED clauses at once as
  adapter count grows and none of them are visually distinguished by
  severity-within-severity.
- **Evaluation errors**: handled correctly and safely — `EVALUATION_ERROR`
  is a first-class synthetic finding routed to manual review, generically,
  with the underlying exception's type name (never a traceback or contract
  text) recorded; confirmed this cannot silently suppress or hide other
  clause types' findings (`policy_enforcement.py`'s per-clause try/except
  isolates failures, §7).
- **Overrides**: not examined in depth in this pass (out of the four
  fact-gathering agents' scope) — flagged as a gap in this review's own
  coverage, not a finding about the code; should be checked explicitly
  before #12 if override volume is expected to grow with adapter count.
- **Mixed policy + ordinary rule findings**: `finding_type ==
  "policy_decision"` is the only discriminator used; ordinary
  (non-policy) findings pass through the same `TIER_RANK`-based sort with
  no separate handling — this already works today with ten adapters
  coexisting with legacy rule-based findings and needs no adapter-count-
  driven change.

**Where the queue breaks down**: not at 10, not obviously at 12 either —
the mechanism is correct and generic. The identified strain point is
specifically *high simultaneous top-tier-finding counts* (many
`PROHIBITED`/`MUST_REDLINE`/`ESCALATE` findings on one contract at once),
which becomes more likely, not less, as adapter count grows, simply because
more independently-evaluated clause types means more opportunities for
several to land in the same top tier on the same contract. The fix is
narrow and already has its data source built (`CLAUSE_TYPE_IMPORTANCE`) —
it is a secondary sort key away from being solved, not a redesign.

---

## 6. Extraction scalability

### 6.1 Phase 2 (deterministic import)

Genuinely plug-in-like, confirmed by direct inspection. Dispatch is a
single dict lookup (`_PROPOSAL_FUNCS[clause_type]`), not an if/elif chain.
Adding adapter #11 means writing one new `_propose_warranties_fields`
function and one new dict entry — no existing code needs to change. Three
shared helpers (`_established`, `_not_established`, `_conflicting`) are
used identically by all ten current proposal functions, and the
initialization idiom (`{name: _not_established(...) for name in
pa.CLAUSE_TYPE_CONFIG_FIELDS[clause_type]}` then early-return if
`not facts.clause_found`) is followed by all ten without exception —
this is a real, working convention, not just an accident of similar code.

Per-adapter proposal function size tracks field count roughly linearly
(governing_law's 3-field adapter is ~17 lines; ip_ownership's 14-field
adapter is ~92 lines) — this is expected and healthy: it means the
*marginal* cost of adapter #11 is proportional to how many fields
Warranties actually needs, not to how many adapters already exist. There
is no sign of centralized mappings or conditionals accumulating in this
file as adapter count has grown from six to ten.

### 6.2 Phase 3 (AI-assisted import)

Same conclusion, more strongly. `_ANCHOR_RES[clause_type]` is the only
per-adapter registration point in the entire file; every downstream stage
(candidate-schema derivation, LLM-response parsing/validation,
authoritative verification/classification, per-clause-field merge) is
parameterized generically by `clause_type` against
`pa.CLAUSE_TYPE_CONFIG_FIELDS`/`pa._ENGINE_PROTOCOLS`, with **no**
clause-type string comparison found anywhere else in the file. This is the
strongest "still genuinely plug-in-like" evidence in the whole review —
Phase 3 was built (per the session history) *after* six adapters already
existed, specifically as a generic layer, and it has now absorbed four
more adapters with zero adapter-specific branches added.

### 6.3 False-establishment risk as field count grows

The four-condition authoritative gate in `verify_and_classify_candidate`
(quote verified against source text, extraction basis is EXTRACTED not
inferred, schema-valid against the Protocol, numeric grounding required for
numeric fields) is applied uniformly regardless of field count — it does
not get weaker as more fields exist to check, because it operates
per-candidate-field, not per-adapter. The risk that does grow with field
count is not in this gate itself but in the same place §3.2 already
flagged: `_BOUNDED_VOCABULARIES`'s hand-maintained vocabulary lists. If
Warranties or SLA introduces a bounded-string field and the corresponding
`_BOUNDED_VOCABULARIES` entry is forgotten or contains a stale value list,
Phase 3's schema-validity check (`vocab is not None and value not in
vocab`) would either wrongly reject a valid AI-proposed value (safe
failure mode — routes to REQUIRES_LAWYER_INTERPRETATION, not a
false-establishment) or, if the vocab list is simply missing that field
entirely, silently skip the vocabulary check (`vocab is None` ⇒ no check
runs) and let an out-of-vocabulary string through as ESTABLISHED if it's
otherwise well-formed. The second case is the real risk, and it is a
schema-completeness risk (§3.2), not a Phase 3 pipeline risk — Phase 3
itself does not introduce new false-establishment surface as field count
grows.

---

## 7. Enforcement scalability

### 7.1 What is genuinely generic

`evaluate_active_policies`/`apply_active_policies` (the cutover-mode
production path) iterate `pa.CLAUSE_TYPES` dynamically, in that tuple's
fixed order, for deterministic serialization. Each clause type's
evaluation is wrapped in its own `try/except`, so one adapter's exception
never aborts or affects another's outcome — confirmed this correctly
produces a synthetic `EVALUATION_ERROR` finding rather than silently
dropping the clause type. Revision pinning
(`Contract.policy_revision_metadata_json`) references a specific
`policy_position_id` plus a `config_hash` (SHA-256 over the position's
canonical config), not merely "whatever is currently ACTIVE" — replay/
verification (`verify_policy_finding`) checks the hash still matches before
trusting a re-evaluation. All of this is confirmed clause-type-agnostic
and will not need adapter-count-driven changes.

### 7.2 A hidden assumption about adapter count — but not the one the task expected

The task asked whether there are hidden assumptions about "six or ten"
adapters. The real finding is sharper: **shadow-mode comparison and the
fail-closed legacy-migration gate are hardcoded to exactly ONE clause
type — `limitation_of_liability`** — not six, not ten. Three functions in
`policy_enforcement.py` hardcode `clause_type == "limitation_of_liability"`
or filter `PolicyRule.clause_type == "limitation_of_liability"`:

- `run_shadow_comparison` — the mechanism that compares the legacy
  `PolicyRule`-based decision against the new `PolicyPosition`-based
  decision for zero-divergence verification — with an explicit docstring
  admitting this: *"for limitation_of_liability only (the only clause type
  with a legacy PolicyRule to compare against — the other [nine] have no
  legacy equivalent)."*
- `find_unmigrated_liability_policies` / `verify_migration_coverage_or_
  fail_closed` — the fail-closed gate that blocks cutover if any legacy
  `PolicyRule` row hasn't been migrated — scoped only to
  `limitation_of_liability`, because that is the only clause type that
  ever had legacy rows to migrate.
- `verify_policy_finding`'s fallback branch (for findings with no pinned
  `PolicyPosition` revision) has an explicit `elif clause_type ==
  "limitation_of_liability":` special case alongside its generic
  pinned-revision path.

This is **correct as designed** — nine of the ten adapters were born
directly into the `PolicyPosition` world and genuinely have no legacy
`PolicyRule` equivalent to shadow-compare against, so there is nothing
wrong with the shadow/migration machinery being scoped to the one clause
type that does. But it means the Phase 4 shadow-equivalence gate — the
release gate this project has run before every adapter's commit — has
**never verified**, and structurally **cannot verify**, anything about
adapters #7–#10 (or, going forward, #11–#12), because there is no legacy
baseline for it to compare against for those clause types. The zero-
divergence result reported at the end of every adapter's regression run is
a true and meaningful statement about `limitation_of_liability` specifically,
and says nothing about the other nine. This has been true since adapter #7
and is not a new problem introduced by this review, but it has not been
stated this explicitly before, and it is worth being precise about before
adding #11/#12: shadow mode is not, and cannot become without new legacy
data, a general adapter-onboarding safety net — it is a one-time migration-
verification tool for the single clause type that predates
`PolicyPosition`.

### 7.3 Stale documentation, not stale code

Multiple module docstrings and inline comments across `playbook_extraction.py`,
`playbook_workbench.py`, and `policy_enforcement.py` still say "the same
six extract_*_facts() functions" / "all six clause types" / "generalized to
all six adapters," left over from before adapters #7–#10 were added. In
every case checked, the *code* itself is dynamic (iterates
`pa.CLAUSE_TYPES`, currently ten elements) and functionally correct — these
are stale comments, not functional bugs, and were not treated as findings
in §2. They are worth listing here because they are exactly the kind of
drift that compounds: `playbook_authoring.py`'s own comments (the
`CLAUSE_TYPE_IMPORTANCE` per-adapter justification paragraphs) have been
kept current with every adapter addition, proving it's tractable to do so
— the other files simply haven't been. A one-time doc pass correcting
these before #11 would cost little and would remove a recurring source of
"is this actually generic or does it just look generic" doubt for future
readers, but it is documentation hygiene, not an architecture blocker.

---

## 8. Preparing for the future Interaction Engine (not building it)

The question: do today's `PolicyDecision`/`*Facts` outputs carry enough
structured information for a future cross-policy interaction layer to
reason over *without re-parsing the contract*? Assessed per relationship:

| Relationship | Classification | Why |
|---|---|---|
| **Liability ↔ Indemnification** | **READY FROM STRUCTURED FACTS** | `indemnification`'s `MonetaryTreatment.kind == "cross_reference"` already structurally records *that* an indemnification obligation delegates its monetary cap to the LoL clause (it just doesn't resolve the value itself — see §1.5). Both adapters expose typed monetary facts (`CapExpression`/`CapValue` vs. `MonetaryTreatment`) with directional `our_position`/`counterparty_position`. An interaction layer could join on `contract_side` and directly compare "our indemnification exposure is uncapped" against "our liability cap is 2x fees" without touching contract text again. |
| **Liability ↔ Insurance** | **READY FROM STRUCTURED FACTS** | `liability`'s resolved cap value (a dollar figure or multiplier) and `insurance`'s per-coverage-type `CoverageRequirement` (per-occurrence/aggregate dollar amounts, obligated party) are both fully typed and directional. "Is our liability cap covered by the counterparty's required insurance limits" is a direct numeric comparison over two already-structured outputs. |
| **Liability ↔ Data/Security** | **NEEDS SMALL OUTPUT EXTENSION** | `data_security`'s facts model tracks nine requirement axes (breach notification, audit rights, etc.) as presence/role facts, not monetary ones — there is no dollar figure to compare against a liability cap. The interesting interaction ("is data-breach liability specifically carved out of the general cap") is *partially* present: `liability`'s `category_treatments` list already includes a `data_breach` carve-out category by name (`_CATEGORY_KEYWORD_RE` includes `data_breach`). The extension needed is small and one-directional: `data_security`'s facts would need to expose whether the clause it found is the *same* carve-out `liability` already detects, most cheaply via a shared `start_index`/`end_index` overlap check the interaction layer could do itself — no new extraction required, just documenting that both adapters' spans are comparable. |
| **Indemnification ↔ IP** | **NEEDS SMALL OUTPUT EXTENSION** | `indemnification`'s `_TRIGGER_KEYWORD_RE` includes `ip_infringement` as a trigger category, and `ip_ownership` has its own `require_infringement_remedy_reference` field — both adapters already "know about" IP infringement independently, but neither currently cross-references the other's span or resolved value. The extension is the same shape as above: no new *extraction* logic, just a documented convention (e.g. a `related_spans` or `cross_adapter_tags` field on the shared facts base) that lets an interaction layer find "these two adapters both flagged text about the same IP-infringement provision" without re-scanning the document. |
| **Indemnification ↔ Insurance** | **READY FROM STRUCTURED FACTS** | Same shape as Liability↔Insurance: `indemnification`'s per-obligation `MonetaryTreatment` and `insurance`'s per-coverage `CoverageRequirement` are both typed, directional, and independently resolved. "Does our indemnification exposure exceed the counterparty's required coverage" is directly computable. |
| **Confidentiality ↔ Data/Security** | **READY FROM STRUCTURED FACTS** | Both adapters are directional, both resolve `our`/`their` obligation to protect information, and `confidentiality`'s `EXCLUSION_TOPICS` / `data_security`'s nine requirement axes are both closed-vocabulary token sets with independent resolution per obligation. An interaction layer could directly check "is personal data confidentiality (from `confidentiality`) at least as strong as `data_security`'s confidentiality-of-personal-data requirement" as a pure data comparison. |
| **Payment ↔ Termination** | **READY FROM STRUCTURED FACTS** | `payment_terms`'s facts already model exactly the two things this interaction needs — net-days/payment-trigger and, separately, whether non-payment is itself a termination trigger is already a first-class `termination` trigger type (`_TRIGGER_NONPAYMENT_RE`). Both are independently resolved, directional, and typed (a day-count and a trigger-category enum respectively). No extension needed — this is the cleanest of the eight relationships. |
| **IP ↔ Liability** | **NEEDS SMALL OUTPUT EXTENSION** | Same shape as Liability↔Data/Security: `liability`'s carve-out categories already include `ip_infringement` by name, and `ip_ownership` independently tracks `require_infringement_remedy_reference`, but the two adapters don't currently expose a shared key an interaction layer could join on beyond re-deriving span overlap itself. |

**Overall assessment**: four of eight are already `READY FROM
STRUCTURED FACTS` with no changes; the remaining four are all the *same*
small, low-risk extension (expose enough of a shared identifier — most
cheaply, the existing `start_index`/`end_index` spans, since every
adapter's facts already carry them — for an interaction layer to correlate
two adapters' findings about the same underlying contract language without
re-parsing). **None of the eight relationships would require
re-extraction.** This is a genuinely strong result and is the clearest
positive finding in this review: the discipline of typed, directional,
independently-resolved facts with consistent evidence/provenance fields —
applied consistently across all ten adapters specifically *because*
`policy_engine_core.py`'s `PolicyDecision` shape was held constant — has
produced, likely unintentionally, exactly the substrate a future
interaction layer needs. The one concrete recommendation worth flagging
for whoever eventually scopes the Interaction Engine (not for now): the
"small output extension" four relationships all want the same primitive
(a way to say "this adapter's finding and that adapter's finding are about
the same underlying clause text"), so that primitive, if built, should be
built once, generically, rather than four times.

---

## 9. Adapters #11 and #12 — reasoning architecture recommendation

### 9.1 Warranties

**Recommended shape: directed-obligation-graph, same family as
Indemnification/Confidentiality/Assignment**, not a new shape. A warranty
is structurally "who warrants what, to whom, for how long, subject to what
exclusions/remedies" — directly analogous to Confidentiality's "who
protects whose information, subject to what exclusions, for how long."
Reuse candidates, in order of confidence: the reciprocal/asymmetry-
detection pattern (`detect_role_attributed_asymmetry`, already promoted to
core and used by four adapters) for mutual-warranty clauses; the
`EXCLUSION_TOPICS`-style bounded-vocabulary pattern for standard warranty
disclaimers ("AS IS," "no warranty of merchantability," "no warranty of
non-infringement"); and, per §1.2's `POSSIBLE LATER` note on forward-
coverage-span exclusion windows, Warranties is the concrete third data
point that should settle whether that mechanism gets promoted — warranty
carve-outs ("except for defects caused by misuse") are the same shape of
problem as liability's and indemnification's exclusion coverage, for a
third, independently-drafted clause type.

**Does it introduce a genuinely new reasoning shape?** No — this is a
genuine, checkable negative result, not a hedge. Warranties does not need
a compound-value type (unlike liability's caps), does not need multiple
independently-true catalog facts (unlike insurance/payment_terms), and is
directional in the same way four existing adapters already are.

**Likely extraction failure modes, anticipated before implementation**:
- Implied vs. express warranty disclaimer language ("EXCEPT AS EXPRESSLY
  SET FORTH HEREIN, NO WARRANTIES...") is drafted in enough
  boilerplate variants that the anchor regex will need real adversarial
  testing, similar to `governing_law`'s dispute-resolution classification.
- Warranty duration ("for a period of ninety (90) days from delivery")
  will collide, in the same document, with unrelated day-counts
  (payment terms, cure periods, notice periods) unless scoped with the
  same dimension-specific-anchor discipline §2's findings show is not yet
  universal (`assignment`'s gap, `insurance`'s latent bug) — this is the
  single highest-confidence failure mode to design against from day one,
  not discover via benchmark.
- "Sole and exclusive remedy" language interacting with both warranty
  remedy and limitation-of-liability remedy in the same paragraph is a
  realistic drafting pattern that will need explicit adversarial corpus
  coverage given the Interaction Engine's flagged Liability↔Warranties-
  shaped relationship (not in the original eight, but an obvious ninth).

### 9.2 SLA / Service Levels

**Recommended shape: catalog of independent commercial-economic facts**,
same family as Insurance/Payment Terms/Data Security — **not** the
directed-obligation shape. An SLA is not "who owes what to whom" in the
same sense; it is a set of independently-measurable performance
commitments (uptime percentage, response-time tiers by severity,
resolution-time tiers, measurement window, exclusions from the SLA
calculation, and remedies — credits, termination rights, or both) each of
which is evaluated against its own threshold, not reconciled into one
verdict.

**Does it introduce a genuinely new reasoning shape?** Partially — this is
the one adapter of the twelve where the honest answer isn't a clean yes or
no. The catalog-of-facts shape itself is not new (three adapters already
use it). What may be new is the **tiered-threshold-by-severity** structure
(e.g. "Severity 1 issues: 1-hour response, 4-hour resolution; Severity 2:
4-hour response, 24-hour resolution") — none of the existing ten adapters
model a fact whose value is itself a small ordered table keyed by a
severity/tier enum, as opposed to a single number or a single token. This
is the concrete place `ACTIVATION_REQUIRED_FIELDS`'s `require_` boolean
assumption (§3.2) is most likely to strain: "require an uptime commitment"
is a clean boolean gate, but "require response-time commitments for every
severity tier" is not naturally one boolean — it's closer to "require this
whole sub-table to be populated," which the current schema has no
first-class way to express short of flattening it into
`require_severity_1_response_hours`-style per-tier booleans (workable, but
verbose, and a real design decision to make deliberately rather than
default into).

**Likely extraction failure modes, anticipated before implementation**:
- Explicitly flagged by this review's own boundary: the module docstring
  discipline established in `payment_terms` — *"do not unnecessarily
  absorb full SLA/service-credit reasoning into this adapter; SLA gets its
  own adapter later"* — means `payment_terms.service_credit_present` is a
  presence-only flag today. SLA's own service-credit modeling will need to
  either supersede or coexist with that flag without creating two
  adapters that both claim authority over the same contract language;
  this is a design decision to make explicitly at the start, not discover
  as a conflict later.
- Uptime-percentage extraction will face the identical
  cross-dimension-percentage collision risk §2.4 already names as the
  most likely recurring failure mode for any new adapter with a bare
  percentage fact (uptime % vs. any other nearby percentage — price
  increase, late fee, discount) — budget for dimension-specific anchor
  scoping from the first draft, not as a benchmark-driven fix.
- Measurement-window definitions ("calculated monthly, excluding scheduled
  maintenance") are exactly the kind of exclusion-coverage-span problem
  §1.2/§9.1 already flag as a recurring shape — SLA would be the fourth
  independent instance of "forward span of text carved out from an
  otherwise-affirmative commitment," making it the second data point (after
  Warranties) pushing toward promoting that mechanism.
- Tiered severity tables are very likely to be drafted as actual tables
  (markdown-like or genuinely tabular in the source PDF/DOCX) rather than
  prose sentences — worth confirming early, before writing extraction
  regexes, whether the existing text-extraction pipeline preserves enough
  table structure for regex-based extraction to work at all, or whether
  SLA is the first adapter that needs a fundamentally different extraction
  strategy for at least one of its facts.

---

## 10. Final verdict

**1. Is the architecture healthy at 10 adapters?**
Yes, with three specific, named exceptions (§2.1, §2.2, §2.3) that are
real but narrow — each is a single function or regex, not a systemic
pattern, and two of the three already have a correct sibling
implementation elsewhere in the codebase to copy from. The core
abstraction boundary (`policy_engine_core.py` never imports an adapter;
every adapter's typed facts flow through one shared `PolicyDecision`
shape) has held across four architecturally different reasoning shapes
without needing to bend, which is the single strongest piece of evidence
for "healthy" in this review.

**2. Can we safely proceed to 12?**
Yes, conditioned on fixing the three §2 findings first (small, scoped, no
architectural risk) and being deliberate about the two schema-strain
points flagged in §3.2/§9.2 (bounded-vocabulary hand-maintenance,
tiered-threshold fields) rather than defaulting into an ad hoc answer
mid-build. Nothing found in this review is a reason to stop or to do a
larger structural rework before #11.

**3. What must be fixed before #11?**
- §2.1 — insurance's `_local_window` naive sentence boundary (copy
  payment_terms's regex-based fix; this is a one-function, low-risk
  change with an existing correct reference implementation).
- §2.2 — governing_law's `_JURISDICTION_RE`/`_VENUE_RE` missing
  `(?-i:...)` reset (same fix pattern already applied seven times
  elsewhere).
- §2.3 — assignment's silent-overwrite conflict gap (copy
  confidentiality's `_monetary_key`-guarded pattern, its structural
  sibling).

None of these three requires a design decision — each has a working
reference implementation already in the codebase to copy.

**4. What can wait until after #12?**
- §1.3 — generalizing `resolve_directional_position` beyond `liability`
  (POSSIBLE LATER, explicitly).
- §1.4 — generalizing amendment/supersession beyond `liability`
  (POSSIBLE LATER, no evidence of need yet).
- §4.2 — Workbench categorization implementation (recommended *before*
  #12 in principle, but the review's own "do not implement" instruction
  makes the actual coding wait regardless; the design decision, not the
  code, is what shouldn't wait).
- §5 — plumbing `CLAUSE_TYPE_IMPORTANCE` into the review queue's sort key
  (small, but not urgent at 10-12; becomes worth prioritizing as
  simultaneous top-tier-finding counts grow).
- §7.3 — stale "six adapters" documentation cleanup (cosmetic).

**5. What should never be generalized?**
The four typed numeric/monetary representations (§1.6) — `CapExpression`,
`MonetaryTreatment`, `CoverageRequirement`, and payment_terms's plain
floats are each correctly shaped for their own domain's actual drafting
patterns, and forcing a single shared type would either lose real
compound-structure information (liability) or add unused complexity
everywhere else. Also: the adapter-specific exclusion-coverage
*vocabulary* (as opposed to the *mechanism*, which is a legitimate
POSSIBLE LATER) — `liability`'s and `indemnification`'s category lists are
genuinely different concepts that happen to share a windowing technique,
and merging the vocabularies themselves (not just the windowing code)
would be the one abstraction this review would actively recommend against
at any adapter count.

**6. Is the product layer genuinely adapter-agnostic?**
Mostly, and more so than a ten-adapter system has a right to be by
default — Phase 3 (§6.2) is essentially perfectly generic, Phase 2 is
generic with linearly-scaling (not accumulating) per-adapter code, and
`policy_enforcement.py`'s cutover path is generic. The honest exceptions:
`playbook_authoring.py`'s seven hand-maintained per-clause-type
registration points (§3.2) are real, load-bearing exceptions to
"adapter-agnostic," not edge cases — every one of the ten adapters
required all seven, and #11/#12 will too. "Genuinely adapter-agnostic"
is the right description of the *engine* and *extraction* layers; the
*authoring metadata* layer (labels, importance ranking, summaries,
templates) is better described as "adapter-parameterized with
consistently-applied, still-manual, per-adapter registration" — a real
and currently acceptable distinction, but a distinction, not a technicality.

**7. Are we accumulating technical debt that will make the Interaction
Engine difficult?**
No — this is the review's clearest good-news finding (§8). The discipline
that has been followed (typed facts, directional resolution, consistent
`start_index`/`end_index` provenance, `PolicyDecision`'s stable shape) is
precisely what a future interaction layer needs, and it has been followed
consistently across four different reasoning shapes without exception.
Zero of the eight examined relationships would require re-extraction.
The debt that does exist (§2's three bug-class instances, §3.2's seven
hand-maintained registration points) is real but orthogonal to the
Interaction Engine question — none of it is debt *in the facts model*,
which is the part that matters for that future layer.

**8. Three highest-risk architectural weaknesses today, ranked:**
1. **§2.3, the assignment silent-overwrite conflict gap** — ranked
   highest specifically because it is the one §2 finding that produces a
   *wrong, confident answer* (a policy decision made on the wrong,
   silently-overwritten restriction) rather than a safe abstention or a
   narrow, hard-to-trigger latent bug. It directly contradicts this
   project's own stated release-gate discipline (false-safe = 0) in a
   real, if narrow, way that has not yet been benchmark-caught.
2. **§3.2, the seven hand-maintained per-adapter registration points in
   `playbook_authoring.py`** — ranked second because it is the one finding
   that gets strictly worse, not just linearly larger, with every future
   adapter: each of the seven is a place a new adapter can be *silently
   incomplete* (missing a `FIELD_LABELS` entry breaks a form, but a
   forgotten `_BOUNDED_VOCABULARIES` entry silently disables a validation
   check with no error, per §6.3) — and unlike §2's three findings, none
   of these seven has a test that would catch the omission the way the
   ten adapters' own benchmarks catch extraction bugs.
3. **§7.2, shadow-mode's single-clause-type scope** — ranked third not
   because it's wrong (it isn't) but because it means the project's own
   headline release-gate language ("Phase 4 shadow-equivalence gate: 0
   divergences, PASS," reported after every adapter's regression run) is
   silently narrower than it reads. This is a communication/expectation
   risk more than a code risk, but at adapter #11/#12 it is worth stating
   in the same release report, explicitly, rather than letting the gate's
   name imply coverage it structurally cannot have.

---

## Recommendation

**PROCEED TO #11**, conditioned on first fixing the three named,
narrowly-scoped bugs in §2 (§10.3) — each has a working reference
implementation already in the codebase, none requires a design decision,
and none blocks or complicates the Warranties/SLA reasoning-architecture
recommendations in §9.

**Evidence for proceeding rather than stopping to fix architecture
first**: every duplication found across all ten adapters was correctly
classified as either already-promoted (evidence/provenance,
REQUIRES_REVIEW construction, role-attributed asymmetry detection),
correctly-kept-local (typed monetary representations, accumulate-then-
resolve as code), or a considered POSSIBLE LATER with a stated reason to
wait (directional resolution generalization, amendment/supersession
generalization, exclusion-coverage-window promotion) — none of the
duplication found rises to an active PROMOTE-NOW blocker except the two
narrow regex/window fixes already folded into §10.3's punch list. The
Interaction-Engine readiness result (§8, §10.7) is strong and positive
evidence the underlying facts-model discipline is sound, not just
adapter-count-lucky. The three highest-risk weaknesses (§10.8) are real
but are, respectively, a one-function fix, a maintenance-process gap with
no correctness impact on any adapter built so far, and a documentation-
precision issue — none is the kind of finding ("the schema can't express
what Warranties needs," "the engine boundary leaks," "extraction is
becoming a centralized if/elif ladder") that would justify pausing new
adapter work to rebuild architecture instead.
