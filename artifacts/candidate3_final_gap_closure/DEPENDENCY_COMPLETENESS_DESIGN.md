# Dependency Completeness Design (Root Cause B)

## What existed before this mission

Six adapters each independently wrote their own "delegated to an external document" regex: `insurance_policy_engine._SCHEDULE_CROSSREF_RE`, `payment_terms_policy_engine._SCHEDULE_CROSSREF_RE`, `sla_policy_engine._SCHEDULE_CROSSREF_RE`, `warranties_policy_engine._SCHEDULE_CROSSREF_RE`, `ip_ownership_policy_engine._SOW_CROSSREF_RE`, `data_security_policy_engine._DPA_CROSSREF_RE`. All six independently reinvented the same "as set forth in the (attached) Schedule/Exhibit/..." shape, and all six independently required the literal word "the" — a shared bug pattern from six separate authorings, not one shared and reused primitive. Separately, `fact_admission.resolve_definition()` IS shared, but only serves the AI-admitted-candidate path; the deterministic-anchor path (which fires regardless of AI) had no definition-dependency detector of any kind.

## What this mission changes

**Detection vs. resolution, made explicit:**
- REFERENCE DETECTION — "does this clause point to an external Schedule/Exhibit/Addendum/etc.?" — stays adapter-local (each adapter's own vocabulary for what a schedule/exhibit is called in its domain: "Insurance Schedule" for insurance, "SOW" for ip_ownership, "DPA"/"Addendum" for data_security), because the vocabulary genuinely differs by adapter and forcing one shared vocabulary risks false negatives. What's shared is the STRUCTURAL FIX: none of these adapter-local regexes should have required the literal word "the" in the first place. Fixed uniformly across all six by changing `in\s+the\s+` to `in\s+(?:the\s+)?` in each adapter's own regex (a one-line change per adapter, same fix applied identically, not six different patches).
- TARGET RESOLUTION — "is the referenced document's content actually available in this text?" — was never attempted before (correctly: resolving an external document's content is out of scope for a single-document extraction pipeline) and remains out of scope here. What changes is that DETECTION of "the referenced document is explicitly NOT attached" is now itself a completeness signal, handled by a new **shared** primitive:

```python
# policy_engine_core.py
EXTERNAL_DEFINITION_NOT_ATTACHED_RE = re.compile(
    r"(?:as\s+)?defined\s+in\s+(?:the\s+)?[^,.;]{1,80},?\s+which\s+is\s+not\s+attached"
    r"|is\s+defined\s+in\s+(?:the\s+)?[^,.;]{1,80}\s*[,.]?\s*(?:that\s+document\s+is\s+)?not\s+attached",
    re.I,
)
```

This IS shared (not adapter-local) because the shape — "a defined term's definition is delegated to an external document, and the text itself states that document is not attached" — is adapter-agnostic; the term being defined and the external document's name vary, but the structural claim does not. Wired into `insurance_policy_engine.py`, `data_security_policy_engine.py`, and `ip_ownership_policy_engine.py` (the three adapters with confirmed `UNRESOLVED_DEFINITION_TO_CLEAN` cases) as an additional trigger alongside each adapter's own schedule/SOW/DPA cross-reference regex.

**Explicit completeness states considered:** the mission's suggested vocabulary (`RESOLVED`/`NOT_MATERIAL`/`MISSING`/`UNRESOLVED`/`CONFLICTING`/`TARGET_NOT_FOUND`/`MISSING_ATTACHMENT`) was evaluated against what the codebase can actually determine from a single document. Given this pipeline only ever sees one document (never the referenced Schedule/Exhibit/DPA's actual content), the only states reachable in practice are:
- **RESOLVED** — the referenced information is fully present in-document (no cross-reference at all, or the cross-reference target's content is inline).
- **MISSING_ATTACHMENT** — a cross-reference or a definition explicitly states the target is not attached/included (`EXTERNAL_DEFINITION_NOT_ATTACHED_RE`, `_SCHEDULE_CROSSREF_RE`-family).
- **UNRESOLVED** (folded into each adapter's `PRESENT_BUT_UNRESOLVED` absence-state, Candidate 3 remediation Root Cause 1) — a candidate was admitted but nothing could be deterministically structured from it.

`TARGET_NOT_FOUND` and `CONFLICTING` (a genuinely two-place state: "the document references a target AND separately states something inconsistent about it") were evaluated and rejected for this mission as not reachable from a single-document input without inventing behavior the pipeline cannot actually verify — introducing them now would be undocumented behavior, not a real capability. Documented here rather than silently dropped, per the mission's instruction to consider but not blindly implement every listed state.

**One new field, not a new schema:** `ip_ownership_policy_engine.IPFacts.definition_dependency_unresolved` (distinct from the pre-existing `sow_cross_reference`) — because `sow_cross_reference`'s consuming logic intentionally suppresses its unresolved-note when something else was already established (a schedule delegating ADDITIONAL terms doesn't need to block an already-clear ownership statement), but a definition dependency that scopes an ALREADY-established fact ("Customer shall own all 'Deliverable Materials.' That term is defined in the Order Form, which is not attached.") changes what that established fact actually covers, and must surface regardless. This is a targeted, one-field extension to the existing `CandidateMaterialFact`-adjacent adapter dataclasses, not a new 12-way schema — consistent with the Candidate 3 remediation mission's earlier `CANONICAL_PRIMARY_FACT_SCHEMA.md` decision to extend narrowly rather than redesign broadly.

## Verification

7/7 confirmed burned-corpus cases (4 cross-reference + 3 definition) re-tested directly against the fixed adapters: all now reach a non-`ACCEPT` decision (`REQUIRES_REVIEW` or `ESCALATE`). `benchmarks/ip_ownership_corpus.py` and the full `tests/test_ip_ownership_benchmark_gate.py`/equivalent gates for the other five adapters re-run: zero regressions. Full suite: baseline unchanged.
