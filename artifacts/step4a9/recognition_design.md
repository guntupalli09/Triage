# Step 4A.9 — Indemnification Recognition Architecture Redesign

## Diagnosis (Phase 1/2)

`extract_indemnification_facts` currently has exactly two ways to produce an
`IndemnityObligation`: the canonical `_OBLIGATION_RE` ("X shall indemnify,
defend, and hold harmless Y") and `_MUTUAL_RECIPROCAL_RE`, plus a fixed list
of four **full-phrase** synonym idioms (`_SYNONYM_OBLIGATION_RES`) — each
one a specific, rigidly-ordered multi-word template, not a verb. If none of
these six patterns match anywhere in the text, `extract_indemnification_facts`
returns `None`, and `evaluate_indemnification_policy` reports
`NOT_APPLICABLE` — the same terminal state used for a document that
genuinely has no risk-transfer language at all. **Discovery failure and
confirmed absence are the same code path.** This is Lee-2/Lee-3 by
construction, not by accident.

All 16 Step 4A.8 SM-CRITICAL cases trace to this single gate: 15 used a
fresh verb/structure combination not in the 4-idiom list; 1 (`S48-I-N-03`)
used an idiom that IS in the list but with its trailing "on X's behalf"
qualifier reordered to precede rather than follow the claim noun, which the
idiom's rigid word-order regex does not tolerate.

Pipeline trace for one representative case (`S48-I-T1-D-01`, "Alderbrook
Custom Signage Fabricators shall be responsible for, and shall reimburse
Retail Client in full for, any losses arising from Alderbrook's negligent
acts..."):
1. Provision discovery: N/A — there is no separate "provision discovery"
   stage; `_ANCHOR_RE` (`indemnif\w*`) is checked as an entry gate elsewhere
   in the module, but this text contains no `indemnif*` token at all.
2. Candidate obligation discovery: all 6 patterns tested, none match — "shall
   be responsible for, and shall reimburse... in full for" is not among the
   4 synonym idioms.
3. Result: `obligations = []` → `extract_indemnification_facts` returns
   `None` → `NOT_APPLICABLE`.

Failure category (Phase 1, Q5): **lexical idiom enumeration** — not syntax,
not actor attribution, not trigger recognition; those stages are never
reached because discovery itself never fires.

Gate classification (Phase 2):

| Gate | Current mechanism | Class | Enumeration-dependent? |
|---|---|---|---|
| Obligation discovery | `_OBLIGATION_RE` + 4 synonym idioms + `_MUTUAL_RECIPROCAL_RE` | DISCOVERY | Yes — closed set |
| Trigger/category | `_TRIGGER_KEYWORD_RE` | INTERPRETATION | Yes, but degrades safely (not_addressed, not absence) |
| Scope (3rd/1st party) | `_THIRD_PARTY_ONLY_RE`/`_FIRST_PARTY_SIGNAL_RE` | INTERPRETATION | Partial |
| Defense control | `_DEFENSE_*_RE` | INTERPRETATION | Partial |
| Monetary | `_classify_monetary` (conflict/chain/conditional checks first, then multiplier/fixed/xref) | VERIFICATION | Yes — bare-digit only (Finding #2) |
| Role/side resolution | `resolve_role_side` + vocabulary | VERIFICATION | No — already escalates on failure (this is the *correct* pattern) |
| Reciprocal asymmetry | `_detect_reciprocal_asymmetry` | VERIFICATION | No — already escalates on failure |

Every VERIFICATION-stage gate in this table already follows the correct
"can't establish → escalate" pattern (that's why role/side resolution and
asymmetry detection are not among the SM-CRITICAL findings). **Only the
DISCOVERY gate collapses failure into absence.** The fix belongs entirely
at that one gate — the verification-stage architecture does not need to be
rebuilt, it needs to be given something to verify.

## Design

### A. Broad risk-transfer discovery (recall-favoring, non-authoritative)

New regex `_RISK_TRANSFER_SIGNAL_RE`: a **verb cluster**, not a phrase
enumeration — `indemnif\w*`, `hold\s+\w+\s+harmless`, `reimburse`,
`make\s+\w+\s+whole`, `bear\s+(?:the\s+cost\s+of|full\s+)?responsibility`,
`assume\s+(?:all\s+)?liability`, `(?:shall|will)\s+be\s+responsible\s+for`,
`protect\s+\S+\s+from`, `satisfy\s+(?:such\s+)?claims?`, `stand\s+in\s+\S+'s?\s+place`,
`answer\s+for`, `save\s+harmless`, `assume\s+the\s+defense\s+of` — checked
in combination with a nearby claim/loss noun (`claims?|losses?|damages?|
liabilit\w+|expenses?|judgments?`) and evidence of two distinct role
mentions in the surrounding window. This is a SIGNAL, not an obligation —
it never itself produces policy state.

### B. Generalized obligation structuring

The rigid 4-idiom `_SYNONYM_OBLIGATION_RES` list is replaced with ONE
generalized regex built on the same verb cluster as (A), but requiring the
full role-verb-role-claim skeleton with FLEXIBLE ordering for trailing
qualifiers (`on X's behalf` may appear before or after the claim noun —
this directly fixes the `S48-I-N-03` word-reordering failure). Where this
generalized regex successfully captures actor + beneficiary + claim
reference, an `IndemnityObligation` is built exactly as before (same
downstream trigger/scope/defense/monetary classification — this reuses the
verification stage unchanged, per Phase 2's finding that it's already
sound).

### C. Independent verification / D. Absence safety

When (A) fires (risk-transfer language is plausibly present) but (B) fails
to structure a directional obligation (actor/beneficiary/claim skeleton not
confidently resolved), the outcome is **`REQUIRES_REVIEW`** with an honest
`"risk-transfer language was detected but could not be confidently
structured into a directional obligation — manual review required"`
message, carrying the matched span as evidence — never `NOT_APPLICABLE`.
`NOT_APPLICABLE` is now reserved for the case where (A) *also* fails to
fire: no risk-transfer signal anywhere in the text at all. This is the
`CONFIRMED_ABSENT` vs. `POSSIBLE_BUT_UNRESOLVED` vs. `PRESENT_AND_
ESTABLISHED` distinction Phase 3.D requires, implemented as three concrete,
distinguishable code paths rather than a label.

Both (A) and (B) are broader than the current 4-idiom list but remain
**closed, deterministic regex** — this is not a claim that verb-cluster
matching now "understands" indemnification language in general; it is a
wider, still-finite net with an explicit safety net underneath it (C/D) so
that the NEXT unanticipated verb still escalates instead of going silent.
That safety net, not the widened verb list, is the actual architectural
change.
