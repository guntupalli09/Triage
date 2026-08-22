# Step 4A.9.1 Phase 2 — Hybrid Discovery Design Doc (written before implementation)

## 0. Critical environment decision (must be disclosed up front)

This sandbox exposes no end-user-callable LLM/semantic-provider API key to
Python code under test (checked: only Claude Code harness/session
infrastructure variables — OAuth token file descriptors, session sockets,
`ANTHROPIC_BASE_URL` — are present, all of which belong to the CLI harness
itself, not to arbitrary code running inside it, and are not an appropriate
credential to repurpose for this). Making real model calls from inside
`indemnification_policy_engine.py` is therefore not available in this
session.

**Decision:** the "semantic discovery" component in this POC is a
**simulated semantic layer**, implemented as ordinary Python, explicitly
and repeatedly disclosed as simulated throughout this step's artifacts and
final report. It is engineered to have the properties a real semantic
component would have for purposes of testing the ARCHITECTURE:
- it recognizes concept instances using signals broader/fuzzier than exact
  regex structuring (a bounded lexical/semantic-similarity heuristic over a
  larger vocabulary than the deterministic regexes use, not a closed
  phrase list copy of the eventual test benchmark);
- it is capable of being wrong: it is deliberately given a controlled
  false-positive rate and a "hallucination" mode (Phase 15) so the
  verification layer has something real to reject;
- it is capable of proposing malformed/malicious output for adversarial
  testing (Phases 9, 14, 15);
- it is NOT tuned by reading the locked benchmark's answer key, and the
  benchmark (Phase 5/6) is built from the legal concept, independently of
  this component's implementation, per the spec's own requirement.

This decision means Step 4A.9.1's result validates **the authority-boundary
architecture** (can a probabilistic candidate-proposal layer be safely
bounded by deterministic verification), NOT the real-world recall of any
particular commercial LLM. That distinction is carried through every
metric in this step's report. If a real provider becomes available later,
`discover_candidate_spans` is designed as a drop-in-replaceable interface
(see Point 3) — no caller-side code changes would be required.

## 1. Deterministic path (unchanged)

Existing `_OBLIGATION_RE` / `_SYNONYM_OBLIGATION_RES` / `_risk_transfer_
signal_present` structuring & discovery-signal code is untouched. It
remains the primary, cheap, high-precision path and runs first.

## 2. Semantic path

`discover_candidate_spans(document_text, concept)` (Phase 3) runs only for
`concept="indemnification"` in this POC (see Phase 25 for cross-adapter
applicability without implementation). It scans sentences for
indemnification-adjacent semantics beyond the regex vocabulary (a wider,
separately-authored trigger vocabulary + role-noun proximity heuristic —
see `semantic_discovery.py`) and returns zero or more `DiscoveryCandidate`
objects. It NEVER modifies or generates text — it only proposes
`(start_offset, end_offset)` spans of the input document.

## 3. Candidate representation

```python
@dataclass(frozen=True)
class DiscoveryCandidate:
    concept: str            # e.g. "indemnification"
    evidence_span: str      # the proposed verbatim text
    start_offset: int
    end_offset: int
    source: str             # "SEMANTIC" (this POC never emits "REGEX" candidates —
                             # regex stays on its existing direct path)
    discovery_metadata: dict  # confidence, heuristic name — NEVER read by
                               # policy code, diagnostic/audit only
```
No field for party, side, cap, multiplier, or policy result exists on this
type — enforced structurally (Phase 9 adds a runtime test asserting the
dataclass has exactly these fields and rejecting any attempt to add an
authoritative one).

## 4. Deduplication

A semantic candidate whose span overlaps (>50% char overlap) an already-
regex-discovered obligation span is dropped as redundant (the deterministic
path already covers it). Non-overlapping candidates proceed to
verification.

## 5. Evidence-span validation

Every candidate's `evidence_span` is checked against
`document_text[start_offset:end_offset]` for an exact match (Phase 4). Any
mismatch (fabricated quote, wrong offsets, off-by-one) => candidate is
discarded and logged to a diagnostic list, never reaches verification.

## 6. Deterministic verification (Phase 10)

The candidate's span (only — not the whole document) is run back through
the SAME deterministic structuring regexes used by the regex path
(`_OBLIGATION_RE`, `_SYNONYM_OBLIGATION_RES`, `_classify_monetary`, etc.,
widened to search within the local span/window). Three outcomes:
- **VERIFIED** — the span structures cleanly (role pair identifiable) =>
  becomes a normal `IndemnityObligation`, indistinguishable downstream from
  a regex-discovered one, with `discovery_source` recorded for audit.
- **UNRESOLVED** — span clearly indemnification-shaped (risk-transfer
  signal present) but roles/cap don't structure => becomes a
  `REQUIRES_REVIEW`-worthy fact, never a clean ACCEPT.
- **REJECTED** — evidence-span validation failed, or verification finds no
  indemnification-relevant content at all => discarded, no authoritative
  effect, logged only.

## 7. Unresolved-candidate behavior

An UNRESOLVED candidate feeds into the existing `unresolved_facts` /
REQUIRES_REVIEW mechanism (already in `evaluate_indemnification_policy`) —
no new state machine needed there, only a new source of unresolved facts.

## 8. Absence-state behavior (Phase 11)

Four states computed once per document at the top of
`extract_indemnification_facts`:
- `PRESENT_AND_VERIFIED` — >=1 VERIFIED obligation (regex or semantic).
- `PRESENT_BUT_UNRESOLVED` — 0 VERIFIED but >=1 UNRESOLVED candidate
  (regex risk-transfer-signal OR semantic).
- `RECOGNITION_UNCERTAIN` — semantic discovery unavailable/errored/
  timed-out (Phase 18) while regex also found nothing => cannot certify
  absence, must NOT collapse to CONFIRMED_ABSENT.
- `CONFIRMED_ABSENT` — regex found nothing AND semantic discovery ran
  successfully and found nothing.
Only `CONFIRMED_ABSENT` may produce `NOT_APPLICABLE`.

## 9. Auditability (Phase 22)

Each `IndemnityObligation` gains a `discovery_source: Literal["REGEX",
"SEMANTIC"]` and, for semantic ones, the verifying span and verification
outcome are retained in a parallel audit record — kept structurally
separate from `IndemnityObligation` itself so "candidate discovery" and
"fact establishment" are never the same object (Phase 22 requirement).

## 10. Determinism implications (Phase 17)

Regex path: 100% deterministic, as always. Semantic path (simulated): its
own internal heuristic is deterministic given fixed input (no randomness),
but is explicitly permitted to be non-deterministic in principle (a real
LLM would not be exactly reproducible) — this design tolerates that by
requiring only that the deterministic verification step be 100%
deterministic and that AUTHORITATIVE decisions never depend on which
non-deterministic candidate wording happened to be proposed, only on
whether *some* candidate verified. Phase 16/17 measure this explicitly.

## 11. Failure-if-unavailable behavior (Phase 18)

If `discover_candidate_spans` raises, times out, or returns malformed data,
it is caught and treated as "semantic discovery unavailable for this
document" — contributes zero candidates, and (per Point 8) forces
`RECOGNITION_UNCERTAIN` rather than `CONFIRMED_ABSENT` when regex also
found nothing. It must never silently degrade to "provision absent."

## 12. Privacy implications (Phase 23)

The simulated component runs in-process on the same document text the
deterministic engine already has full access to; no network call, no
third-party service, no additional data leaves the process. This POC
therefore does not have a real privacy exposure to audit — Phase 23's
report says so explicitly and separately describes what a REAL provider
integration would need to consider (minimum-necessary text, no training-
data retention terms, logging discipline) so that decision is not silently
assumed away for a future real integration.

## 13. Cost/latency implications (Phase 24)

Simulated component: sub-millisecond, in-process, zero marginal cost.
Phase 24's report states the real-provider cost model this doesn't
measure (network round trip, token cost) separately and explicitly, rather
than reporting a misleadingly cheap number as if it were representative of
a real integration.
