"""Regression tests for contract PDF export (/contract/{id}/pdf)."""
import os

os.environ.setdefault("DEV_MODE", "true")

from main import _build_pdf_bytes, _pdf_safe


def test_pdf_safe_handles_none_and_unicode():
    assert _pdf_safe(None) == ""
    assert _pdf_safe(42) == "42"
    assert "\u2014" not in _pdf_safe("em\u2014dash")
    assert _pdf_safe("em\u2014dash") == "em-dash"


def test_build_pdf_bytes_with_unicode_findings():
    """Export must not 500 on curly quotes, em dashes, or null JSON fields."""
    pdf = _build_pdf_bytes(
        "TriageCounsel_Mock_SaaS.pdf",
        "high",
        {"critical": 0, "high": 2, "medium": 1, "low": 0},
        "7.2.0",
        ["Summary with \u201csmart quotes\u201d and an em\u2014dash"],
        [
            {
                "title": "Indemnification cap missing \u2013 review",
                "severity": "high",
                "rationale": None,
                "matched_excerpt": "Vendor shall indemnify \u2026 without limitation",
                "confidence_breakdown": {
                    "confidence": "medium",
                    "reason": "Pattern matched near \u201cunlimited\u201d language",
                },
                "redline": {
                    "issue": "Uncapped indemnity exposure",
                    "problem": "No monetary cap on vendor indemnity.",
                    "negotiation_difficulty": "medium",
                    "confidence": "high",
                    "supporting_deterministic_rules": ["indemnification_uncapped"],
                },
            }
        ],
        metadata={"contract_type": "SaaS / Subscription Agreement"},
        legal_risk_score=2,
        business_risk_score=18,
        negotiation_difficulty_score=4,
        document_state="HAS_POLICY_VIOLATION",
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500
