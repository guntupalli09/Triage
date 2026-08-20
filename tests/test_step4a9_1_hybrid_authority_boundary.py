"""Step 4A.9.1 Phases 9/14/15/18 — adversarial and authority-boundary tests
for the hybrid discovery architecture. These are NOT part of the locked
benchmark; they exist to prove the architecture rejects bad input safely."""
import indemnification_policy_engine as ie
from semantic_discovery import DiscoveryCandidate, assert_authority_boundary_intact


def setup_function(_):
    ie.HYBRID_DISCOVERY_ENABLED = True


# ---- Phase 9: schema-level authority boundary ----

def test_discovery_candidate_has_no_authoritative_fields():
    assert_authority_boundary_intact()


def test_discovery_candidate_schema_is_minimal():
    names = {f for f in DiscoveryCandidate.__dataclass_fields__}
    assert names == {"concept", "evidence_span", "start_offset", "end_offset", "source", "discovery_metadata"}


# ---- Phase 15: malicious/hallucinated discovery ----

def test_fabricated_quote_is_rejected():
    text = "The Vendor shall perform services in a professional manner. No indemnification language appears here at all."
    # Directly exercise the verification helper with a candidate whose
    # evidence_span does not match the document at the claimed offsets.
    bad = DiscoveryCandidate(concept="indemnification", evidence_span="fabricated text not in document",
                              start_offset=0, end_offset=10, source="SEMANTIC")
    outcome, obligation = ie._verify_semantic_candidate(text, bad)
    assert outcome == "REJECTED"
    assert obligation is None


def test_bad_offsets_are_rejected():
    text = "Short document."
    bad = DiscoveryCandidate(concept="indemnification", evidence_span="Short document.",
                              start_offset=999, end_offset=1050, source="SEMANTIC")
    outcome, obligation = ie._verify_semantic_candidate(text, bad)
    assert outcome == "REJECTED"
    assert obligation is None


def test_wrong_concept_is_rejected():
    text = "Vendor shall indemnify Client for any claim."
    bad = DiscoveryCandidate(concept="termination", evidence_span=text[:14],
                              start_offset=0, end_offset=14, source="SEMANTIC")
    outcome, obligation = ie._verify_semantic_candidate(text, bad)
    assert outcome == "REJECTED"


def test_end_to_end_hallucinated_candidate_never_becomes_a_fact(monkeypatch):
    text = "The Vendor shall perform routine maintenance services for the Client under this Agreement."

    def fake_discover(document_text, concept, **kw):
        return [DiscoveryCandidate(
            concept="indemnification", evidence_span="a completely fabricated indemnification promise",
            start_offset=0, end_offset=10, source="SEMANTIC",
            discovery_metadata={"confidence": 0.99},
        )]

    monkeypatch.setattr(ie, "_discover_candidate_spans", fake_discover)
    facts = ie.extract_indemnification_facts(text)
    # A hallucinated candidate with a mismatched evidence span must never
    # produce an obligation, regardless of its claimed confidence.
    assert facts is None or not facts.obligations


def test_duplicate_flood_does_not_produce_duplicate_obligations(monkeypatch):
    text = ("Vendor shall make good to Client in full for any third-party claim arising "
            "from Vendor's breach of this Agreement.")

    def flood(document_text, concept, **kw):
        real = [c for c in _real_candidates(document_text)]
        return real * 20

    def _real_candidates(document_text):
        from semantic_discovery import discover_candidate_spans
        return discover_candidate_spans(document_text, "indemnification")

    monkeypatch.setattr(ie, "_discover_candidate_spans", flood)
    facts = ie.extract_indemnification_facts(text)
    assert facts is not None
    assert len(facts.obligations) <= 1


# ---- Phase 18: outage / timeout / malformed / disabled ----

def test_semantic_timeout_does_not_become_confirmed_absent(monkeypatch):
    text = "The Vendor shall make good to the Client for losses caused by the Vendor."

    def boom(document_text, concept, **kw):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(ie, "_discover_candidate_spans", boom)
    facts = ie.extract_indemnification_facts(text)
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_semantic_outage_with_regex_hit_still_verifies(monkeypatch):
    text = "Vendor shall indemnify, defend, and hold harmless Client from and against any claim arising from Vendor's negligence."

    def boom(document_text, concept, **kw):
        raise ConnectionError("simulated outage")

    monkeypatch.setattr(ie, "_discover_candidate_spans", boom)
    facts = ie.extract_indemnification_facts(text)
    assert facts is not None
    assert facts.absence_state == "PRESENT_AND_VERIFIED"
    assert len(facts.obligations) == 1


def test_malformed_response_treated_as_unavailable_not_absent(monkeypatch):
    text = "Vendor shall make good to Client for any claim arising from Vendor's conduct."

    def malformed(document_text, concept, **kw):
        return None

    monkeypatch.setattr(ie, "_discover_candidate_spans", malformed)
    facts = ie.extract_indemnification_facts(text)
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"


def test_disabled_hybrid_reproduces_regex_only_behavior():
    ie.HYBRID_DISCOVERY_ENABLED = False
    text = "Vendor shall make good to Client for any claim arising from Vendor's conduct."
    facts = ie.extract_indemnification_facts(text)
    assert facts is None
    ie.HYBRID_DISCOVERY_ENABLED = True


# ---- Phase 14: hard-negative false-positive stress (subset; bulk in benchmark) ----

def test_insurance_clause_never_verified_via_semantic():
    text = "Vendor shall maintain commercial general liability insurance with limits of $2,000,000 per occurrence."
    facts = ie.extract_indemnification_facts(text)
    assert facts is None


def test_limitation_of_liability_clause_never_verified_via_semantic():
    text = "In no event shall Vendor's aggregate liability to Client exceed the fees paid in the preceding year."
    facts = ie.extract_indemnification_facts(text)
    assert facts is None
