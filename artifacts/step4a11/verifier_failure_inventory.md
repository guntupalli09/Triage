# Step 4A.11 — Read-Only Verifier Failure Inventory (Section 4)

**Read-only. No production code touched to produce this document.**

## Provenance and an honest limitation, disclosed upfront

The instruction asks to classify held-out positive cases (semantic
discovery found the provision, evidence-integrity requirements passed,
but the result did not reach clean `VERIFIED`) into the taxonomy A–N.
The only existing held-out evidence of this shape in the repository is
Step 4A.10's Phase 17 bottleneck taxonomy
(`artifacts/step4a10/analysis_full.json` →
`phase17_bottleneck_taxonomy`, 161 `PRESENT_BUT_UNRESOLVED` true
positives out of 220 total, from the 394-case Step 4A.10 corpus). That
taxonomy is explicitly labeled in its own source as **"heuristic
keyword-based classification... diagnostic only, not modified/fixed."**
It does not carry per-case source text or a human-adjudicated rationale
in the artifact — only case IDs and auto-assigned reason codes. I did
not re-derive it from scratch this session (the underlying 394-case
corpus text is not preserved as a standalone artifact I could re-run
against), and I am not fabricating a fresh manual adjudication over
text I don't have. What follows re-maps that existing, disclosed,
heuristic taxonomy onto the finer A–N categories this step requests,
and is presented with that provenance clearly marked — not as a new,
independently-verified inventory.

## Mapping: Step 4A.10 Phase 17 codes → Step 4A.11 taxonomy A–N

| Step 4A.11 category | Step 4A.10 source code(s) | Count | % of 161 |
|---|---|---|---|
| A. structural-pattern unsupported | Q_verifier_lacks_structural_pattern | 88 | 54.7% |
| B. cross-reference / schedule resolution | N_evidence_boundary_insufficient_cross_reference | 52 | 32.3% |
| C. conditional applicability | K_conditional_applicability_unresolved | 26 | 16.1% |
| D. party/role attribution unresolved | *(not separately coded in the source taxonomy — see limitation below)* | — | — |
| E. monetary/value extraction unresolved | *(not separately coded — often co-occurs inside Q/N, not isolated)* | — | — |
| F. scope/category unresolved | *(not separately coded)* | — | — |
| G. causation-standard unresolved | E_causation_standard_unresolved | 7 | 4.3% |
| H. defense-control unresolved | *(not separately coded — no source case in this corpus isolated defense-control as the sole blocker)* | — | — |
| I. temporal/survival unresolved | *(not separately coded — the Step 4A.10 corpus predates the Step 4A.10.2 survival dimension)* | — | — |
| J. conflicting provisions | L_conflicting_definitions | 1 | 0.6% |
| K. evidence ownership ambiguous | M_chained_delegation (delegated/chained value ownership unresolved) | 6 | 3.7% |
| L. multiple candidate ambiguity | O_multiple_candidate_interpretations | 14 | 8.7% |
| M. legitimate SHOULD_REVIEW / inherently ambiguous | P_explicit_textual_ambiguity | 14 | 8.7% |
| N. other | — | 0 | 0% |

(Percentages sum >100% — the source taxonomy allows multi-reason
cases.) Categories D/E/F/H/I have no isolated count in the source data
— this is a genuine gap in the read-only evidence available, not a
claim those failure modes don't exist. It means this inventory cannot
honestly report per-category counts for them from held-out evidence;
it can only note that they are plausible sub-patterns embedded inside
the dominant Q/A ("structural-pattern unsupported") bucket, which is
undifferentiated by WHICH structured fact was unrecoverable.

## Interpretation, category by category

**A (54.7%, largest single bucket).** The deterministic structuring
regexes (`_OBLIGATION_RE`, `_SYNONYM_OBLIGATION_RES`, and their
liability/payment-terms counterparts) require the operative sentence to
match a still-finite (if repeatedly widened across Steps 4A.5–4A.10.9)
set of grammatical shapes. A semantically-discovered candidate whose
sentence doesn't match any of them produces `PRESENT_BUT_UNRESOLVED`,
correctly, per the architecture's own non-negotiable rule (semantic
evidence alone never authorizes a structured fact) — but every such
case is also lost automation, not just a safety-correct abstention.
**Whether solvable deterministically**: partially. The Step 4A.10.3→
4A.10.9 sequence demonstrated repeatedly that STRUCTURAL generalization
(grammatical-shape matching instead of phrase enumeration) can close
real slices of this bucket without weakening safety — e.g. the
reciprocal-opener quantifier generalization, the self-referential
defense-control pattern. The same approach — identify the underlying
GRAMMATICAL PROPOSITION an obligation sentence expresses, independent
of its specific verb choice — is the correct target for the primary
obligation-sentence regex itself, not merely the symmetry-comparison
paths already hardened. **Increases CA or reduces unnecessary review**:
increases CA (genuinely new verified facts, not just fewer reviews).
**New general mechanism required**, not lexical expansion — this is
exactly the instruction's own warning example ("make whole"/"make
good"/"answerable for" should not be solved by an ever-growing synonym
list).

**B (32.3%, second-largest).** A candidate's evidence sits alongside a
cross-reference ("subject to the cap in Schedule 3," "as set forth in
Section 9") the verifier cannot resolve into an actual value, because
resolving it requires locating the target provision elsewhere in the
document, confirming it is the SAME concept (not a differently-labeled
value that merely happens to be nearby), and only then treating the
referenced value as established. Section 8 of this step's mandate
describes exactly this SOURCE→REFERENCE→TARGET→CONCEPT→VALUE chain.
**Whether solvable deterministically**: yes, in the specific and
common case of an in-document reference to a section/schedule/exhibit
label that itself contains a locatable, single, unambiguous value for
the same concept — this is a bounded, structural graph-resolution
problem, not open-ended language understanding. **Increases CA**.
**Requires a new general mechanism** (a reference-resolution graph),
not phrase expansion.

**C (16.1%, third-largest).** A conditional clause ("only if," "unless,"
"provided that," "to the extent") wraps the obligation/value; today's
regexes generally extract the underlying value while dropping the
condition, or refuse to extract at all when the condition disrupts the
expected sentence shape. **Whether solvable deterministically**: yes for
the narrower, safer half of this problem — DETECTING that a condition
is present and preserving/flagging it (Section 9's option B: mark
applicability NOT_ESTABLISHED rather than silently stripping the
condition) is a bounded pattern-matching task. Fully EVALUATING whether
a stated condition is satisfied from contract text alone is a much
harder, likely out-of-scope-for-this-step problem — this step should
target detection-and-preservation, not condition evaluation.
**Reduces unnecessary review only in the narrow case where the
condition can be confirmed as met from the same local text (e.g. an
inherent/unconditional trigger restated) — otherwise it converts a
silent-strip risk into an honest REQUIRES_REVIEW**, which is exactly
the instruction's own priority (never manufacture certainty).

**G/J/K/L/M (small, single digits to low teens each).** Lower-leverage
individually. G (causation standard) and J (conflicting provisions) are
already partially addressed by existing named-standard/differentiation
machinery from the 4A.7/4A.10.x sequence; K (chained/delegated
ownership) is a direct instance of the evidence-ownership problem
Section 6 of this step's mandate targets and should be addressed
alongside B, not separately; L (multiple candidates) and M (legitimate
ambiguity) are largely NOT fixable by more extraction power — M by
definition should stay `REQUIRES_REVIEW`, and L requires exactly the
kind of deterministic disambiguation-or-abstain logic this step's
"evidence ownership" section already calls for.

## Priority ranking for Step 4A.11 implementation

1. **A — structural-pattern unsupported (54.7%)**: highest raw count,
   but also the vaguest/broadest category (any sentence shape gap at
   all). Attacking it well requires the SAME "grammatical proposition,
   not verb list" method already proven in Steps 4A.10.3–4A.10.9, now
   applied to the primary obligation-extraction regex family. High
   effort, high potential yield, real risk of becoming exactly the kind
   of open-ended "understand everything" project explicitly ruled out
   of scope by Section 22.
2. **B — cross-reference resolution (32.3%)**: second-largest, and the
   most CONCRETELY specified in this step's own mandate (Section 8's
   explicit chain model). Bounded, structural, high-confidence to
   implement safely (a reference either resolves to a locatable single
   value for the same concept, or it doesn't — binary, auditable).
   **Selected as the first mechanism implemented this session** (see
   Section E below) precisely because it is both large and
   well-bounded.
3. **C — conditional applicability (16.1%)**: bounded to
   detection-and-preservation as scoped above; natural second
   candidate.
4. Categories D/E/F/H/I/G/J/K/L/M/N: lower individual leverage or
   already partially addressed; deferred.

## Quantitative target (frozen before implementation, per Section 19)

Baseline (Step 4A.10, hybrid arm, 394-case corpus, 220 true positives):
**Clean-Verified Recall = 24.5% (54/220)**.

Target, chosen and frozen now, before any implementation this step:
**≥20 percentage-point absolute improvement — i.e. Clean-Verified
Recall ≥ 44.5% — on this step's own final frozen corpus**, using the
suggested minimum from Section 19 directly (the corpus denominator here
is large enough, per Section 19's own guidance, that the absolute
target is appropriate rather than the relative alternative). This
target is stated here, in this read-only-phase document, before any
production code in this step is modified.
