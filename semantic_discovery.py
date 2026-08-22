"""Step 4A.9.1 — bounded, NON-authoritative semantic discovery layer.

SIMULATED: this module stands in for a real LLM/embedding-based semantic
discovery provider. No such provider is reachable from this sandboxed
session (see artifacts/step4a9_1/hybrid_discovery_design.md Section 0 for
why). It is implemented as ordinary Python so this POC can genuinely test
the authority-boundary architecture end to end, but its recall numbers must
NOT be read as representative of a real model's recall.

HARD RULE: nothing in this module may return, compute, or imply an
authoritative policy fact (who owes what to whom, a cap, a multiplier, a
policy outcome). It may only propose spans of the input document that a
downstream DETERMINISTIC verifier should look at. See DiscoveryCandidate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from typing import Dict, List, Optional


@dataclass(frozen=True)
class DiscoveryCandidate:
    """Non-authoritative candidate span. Deliberately has NO fields for
    party, side, cap, multiplier, or policy result — see the field-audit
    test in tests/test_semantic_discovery_authority_boundary.py, which
    fails the build if an authoritative-looking field is ever added here."""
    concept: str
    evidence_span: str
    start_offset: int
    end_offset: int
    source: str = "SEMANTIC"
    discovery_metadata: Dict[str, object] = field(default_factory=dict)


_FORBIDDEN_FIELD_NAMES = {
    "our_side", "counterparty_side", "cap_amount", "multiplier",
    "policy_result", "compliant", "prohibited", "obligation_direction",
    "final_classification", "indemnifying_role", "indemnified_role",
    "indemnifying_side", "indemnified_side", "state", "decision",
}


def assert_authority_boundary_intact() -> None:
    """Runtime guard, also exercised as a test: raises if the dataclass
    schema ever grows an authoritative-looking field."""
    names = {f.name for f in fields(DiscoveryCandidate)}
    violation = names & _FORBIDDEN_FIELD_NAMES
    if violation:
        raise RuntimeError(
            f"DiscoveryCandidate authority boundary violated: {violation}"
        )


# A vocabulary deliberately DIFFERENT from and WIDER than the deterministic
# regex sets in indemnification_policy_engine.py's _RISK_TRANSFER_SIGNAL_RE
# / _SYNONYM_OBLIGATION_RES, standing in for what a semantic model's fuzzy
# concept match might surface. Built from the legal concept (a party
# absorbing/covering another party's loss, cost, or exposure arising from
# a claim), not copied from production regex source.
_SEMANTIC_TRIGGER_RE = re.compile(
    r"\b("
    r"make\s+good\s+to|"
    r"recompense[a-z]*(?:\s+\w+){0,4}\s+in\s+full\s+for|"
    r"be\s+answerable\s+to|"
    r"shall\s+settle\s+on(?:\s+\w+){0,3}'s\s+behalf|"
    r"shoulder\s+(?:the\s+)?(?:cost|expense|burden)|"
    r"absorb\s+(?:any|the)\s+loss|"
    r"be\s+on\s+the\s+hook\s+for|"
    r"stand\s+behind(?:\s+\w+){0,3}\s+(?:against|with\s+respect\s+to)|"
    r"undertake\s+to\s+make\s+\w+\s+whole|"
    r"cover\s+(?:the\s+)?cost\s+of\s+(?:any|such)\s+(?:claim|loss|damage)|"
    r"backstop|"
    r"take\s+on\s+(?:the\s+)?(?:risk|liability|exposure)\s+(?:of|for)|"
    r"pick\s+up\s+the\s+(?:tab|cost|expense)\s+for"
    r")\b",
    re.I,
)

_ROLE_NOUN_RE = re.compile(r"\b([A-Z][A-Za-z]{2,30}|the (?:Company|Client|Vendor|Contractor|Provider|Customer|Landlord|Tenant|Licensor|Licensee|Buyer|Seller|Member|Manager))\b")


def discover_candidate_spans(
    document_text: str,
    concept: str,
    *,
    _fault_mode: Optional[str] = None,
) -> List[DiscoveryCandidate]:
    """Propose candidate evidence spans for `concept` in `document_text`.

    Returns [] on anything it isn't confident enough about — recall over
    precision is acceptable here BECAUSE downstream deterministic
    verification (not this function) is what's allowed to reject or accept.

    `_fault_mode` exists ONLY for adversarial testing (Phases 9/14/15/18)
    and simulates a misbehaving/attacking/unavailable provider. Production
    callers never pass it.
    """
    assert_authority_boundary_intact()

    if _fault_mode == "timeout":
        raise TimeoutError("simulated semantic-discovery timeout")
    if _fault_mode == "outage":
        raise ConnectionError("simulated semantic-discovery outage")
    if _fault_mode == "malformed":
        return None  # type: ignore[return-value]  # simulates a provider returning garbage
    if _fault_mode == "fabricated_quote":
        return [DiscoveryCandidate(
            concept=concept, evidence_span="This exact sentence is not in the document.",
            start_offset=0, end_offset=42, source="SEMANTIC",
            discovery_metadata={"fault": "fabricated_quote"},
        )]
    if _fault_mode == "bad_offsets":
        return [DiscoveryCandidate(
            concept=concept, evidence_span=document_text[:20] if document_text else "x",
            start_offset=999999, end_offset=1000050, source="SEMANTIC",
            discovery_metadata={"fault": "bad_offsets"},
        )]
    if _fault_mode == "wrong_concept":
        return [DiscoveryCandidate(
            concept="termination", evidence_span=document_text[:30] if document_text else "x",
            start_offset=0, end_offset=min(30, len(document_text)), source="SEMANTIC",
            discovery_metadata={"fault": "wrong_concept"},
        )]
    if _fault_mode == "duplicate_flood":
        base = discover_candidate_spans(document_text, concept)
        return base * 5
    if _fault_mode == "unrelated_clause":
        m = re.search(r"\bforce\s+majeure\b.{0,80}", document_text, re.I)
        if m:
            return [DiscoveryCandidate(
                concept=concept, evidence_span=m.group(0), start_offset=m.start(),
                end_offset=m.end(), source="SEMANTIC",
                discovery_metadata={"fault": "unrelated_clause"},
            )]
        return []

    if concept != "indemnification":
        return []

    candidates: List[DiscoveryCandidate] = []
    for m in _SEMANTIC_TRIGGER_RE.finditer(document_text):
        lo = max(0, m.start() - 80)
        hi = min(len(document_text), m.end() + 160)
        # widen to sentence-ish boundaries for a more realistic span
        span_start = document_text.rfind(".", lo, m.start())
        span_start = span_start + 1 if span_start != -1 else lo
        span_end = document_text.find(".", m.end(), hi)
        span_end = span_end + 1 if span_end != -1 else hi
        span_text = document_text[span_start:span_end].strip()
        if not span_text:
            continue
        real_start = document_text.find(span_text, max(0, span_start - 5))
        if real_start == -1:
            continue
        real_end = real_start + len(span_text)
        candidates.append(DiscoveryCandidate(
            concept=concept,
            evidence_span=span_text,
            start_offset=real_start,
            end_offset=real_end,
            source="SEMANTIC",
            discovery_metadata={"heuristic": "risk_transfer_semantic_v1", "trigger": m.group(0)},
        ))
    return candidates
