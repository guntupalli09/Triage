"""
Build synthetic NDA dataset with controlled clause toggles.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add experiments parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from experiments.config import DATA_DIR, NUM_SYNTHETIC_NDAS
from experiments.utils_io import save_text, save_json


# Base NDA template
BASE_NDA = """NON-DISCLOSURE AGREEMENT

This Agreement is entered into between Company A ("Disclosing Party") and Company B ("Receiving Party").

1. CONFIDENTIAL INFORMATION
Confidential Information means all non-public information disclosed by one party to the other.

2. OBLIGATIONS
The Receiving Party agrees to maintain the confidentiality of all Confidential Information.

3. TERM
{confidentiality_term}

4. INDEMNIFICATION
{indemnification_clause}

5. LIMITATION OF LIABILITY
{liability_clause}

6. INTELLECTUAL PROPERTY
{ip_clause}

7. ATTORNEYS' FEES
{attorneys_fees_clause}

8. RENEWAL
{renewal_clause}

9. AUDIT RIGHTS
{audit_clause}

10. LATE FEES
{late_fees_clause}

11. GOVERNING LAW
{governing_law_clause}

12. DEFINITIONS
{definitions_clause}

This Agreement is executed on {date}.
"""


# Clause variations targeting specific rules
CLAUSE_VARIANTS = {
    "confidentiality_obligations": {
        "standard": "The Receiving Party agrees to maintain the confidentiality of all Confidential Information.",
        "perpetual": "The Receiving Party agrees to maintain the confidentiality of all Confidential Information. These obligations shall be perpetual and continue indefinitely.",
    },
    "confidentiality_term": {
        "limited": "This Agreement shall remain in effect for three (3) years from the date of execution.",
        "perpetual": "This Agreement shall remain in effect in perpetuity with no expiration date.",
        "indefinite": "This Agreement shall remain in effect indefinitely and shall survive termination.",
    },
    "indemnification_clause": {
        "none": "No indemnification obligations apply under this Agreement.",
        "unlimited": "The Receiving Party shall indemnify, defend, and hold harmless the Disclosing Party from and against all claims, losses, and damages, without limit, arising from any breach of this Agreement.",
        "capped": "The Receiving Party shall indemnify the Disclosing Party up to a maximum of $100,000 for claims arising from breach of this Agreement.",
        "limited_by_law": "The Receiving Party shall indemnify the Disclosing Party to the extent required by law for all claims arising from breach of this Agreement.",
    },
    "liability_clause": {
        "capped": "Each party's liability under this Agreement is limited to the total fees paid hereunder.",
        "uncapped": "No event shall be limited by the limitation of liability clause. Liability shall not be limited under any circumstances.",
        "carveout": "Limitation of liability shall not apply to indemnification, confidentiality, or intellectual property claims.",
        "carveout_law": "Limitation of liability shall not apply to indemnification, except as required by applicable law.",
    },
    "ip_clause": {
        "none": "No intellectual property provisions apply.",
        "broad_assignment": "All work product and deliverables created hereunder shall be assigned to the Disclosing Party. The Receiving Party hereby assigns all right, title, and interest in such work product.",
        "license": "The Receiving Party grants a non-exclusive license to use the work product.",
        "excludes_preexisting": "All work product shall be assigned to the Disclosing Party, excluding pre-existing intellectual property owned by the Receiving Party.",
    },
    "attorneys_fees_clause": {
        "none": "Each party shall bear its own attorneys' fees.",
        "one_way": "The Receiving Party shall pay all attorneys' fees and costs incurred by the Disclosing Party in enforcing this Agreement.",
        "prevailing_party": "The prevailing party shall be entitled to recover attorneys' fees from the non-prevailing party.",
        "mutual": "Each party shall pay its own attorneys' fees unless the other party prevails.",
    },
    "renewal_clause": {
        "none": "This Agreement may be renewed by mutual written consent.",
        "auto_renewal": "This Agreement shall automatically renew for additional one-year terms unless either party provides written notice of non-renewal at least 30 days prior to expiration.",
        "auto_renewal_terminated": "This Agreement automatically renews for additional terms unless terminated by either party.",
    },
    "audit_clause": {
        "none": "No audit rights are granted under this Agreement.",
        "with_notice": "The Disclosing Party may audit the Receiving Party's records upon reasonable notice during normal business hours.",
        "inspect_records": "The Disclosing Party may inspect all records related to compliance with this Agreement.",
    },
    "late_fees_clause": {
        "none": "No late fees apply.",
        "high_interest": "Late payments shall accrue interest at a rate of 18% per annum.",
        "reasonable_interest": "Late payments shall accrue interest at a rate of 2% per annum.",
        "late_fee": "A late fee of 5% shall apply to all overdue payments.",
    },
    "governing_law_clause": {
        "none": "This Agreement is governed by applicable law.",
        "specific": "This Agreement shall be governed by the laws of the State of California. The parties agree to exclusive jurisdiction in California courts.",
        "exclusive_jurisdiction": "The parties agree to exclusive jurisdiction in New York courts for any disputes arising from this Agreement.",
    },
    "definitions_clause": {
        "specific": "Confidential Information means information marked as confidential.",
        "broad": "Confidential Information means, including but not limited to, all technical data, business plans, customer information, financial information, and any other proprietary information.",
    },
}


def get_expected_rules(variants: dict) -> tuple:
    """Determine expected rule_ids based on clause variants."""
    expected_present = []
    expected_absent = []
    
    # M_CONF_01: Perpetual/indefinite confidentiality
    if variants.get("confidentiality_term") in ["perpetual", "indefinite"]:
        expected_present.append("M_CONF_01")
    else:
        expected_absent.append("M_CONF_01")
    
    # H_INDEM_01: Unlimited indemnification
    if variants.get("indemnification_clause") == "unlimited":
        expected_present.append("H_INDEM_01")
    elif variants.get("indemnification_clause") == "limited_by_law":
        # Should still trigger but may be downgraded by suppression
        expected_present.append("H_INDEM_01")
    else:
        expected_absent.append("H_INDEM_01")
    
    # H_LOL_01: Uncapped liability
    if variants.get("liability_clause") == "uncapped":
        expected_present.append("H_LOL_01")
    else:
        expected_absent.append("H_LOL_01")
    
    # H_LOL_CARVEOUT_01: Liability cap carveout
    if variants.get("liability_clause") in ["carveout", "carveout_law"]:
        expected_present.append("H_LOL_CARVEOUT_01")
    else:
        expected_absent.append("H_LOL_CARVEOUT_01")
    
    # H_IP_01: Broad IP assignment
    if variants.get("ip_clause") == "broad_assignment":
        expected_present.append("H_IP_01")
    elif variants.get("ip_clause") == "excludes_preexisting":
        # Should trigger but may be suppressed
        expected_present.append("H_IP_01")
    else:
        expected_absent.append("H_IP_01")
    
    # H_ATTFEE_01: One-way attorneys' fees
    if variants.get("attorneys_fees_clause") == "one_way":
        expected_present.append("H_ATTFEE_01")
    else:
        expected_absent.append("H_ATTFEE_01")
    
    # M_RENEW_01: Auto-renewal
    if variants.get("renewal_clause") in ["auto_renewal", "auto_renewal_terminated"]:
        expected_present.append("M_RENEW_01")
    else:
        expected_absent.append("M_RENEW_01")
    
    # M_AUDIT_01: Audit rights
    if variants.get("audit_clause") in ["with_notice", "inspect_records"]:
        expected_present.append("M_AUDIT_01")
    else:
        expected_absent.append("M_AUDIT_01")
    
    # L_LATEFEE_01: Late fees
    if variants.get("late_fees_clause") in ["high_interest", "late_fee"]:
        expected_present.append("L_LATEFEE_01")
    else:
        expected_absent.append("L_LATEFEE_01")
    
    # L_GOVLAW_01: Governing law
    if variants.get("governing_law_clause") in ["specific", "exclusive_jurisdiction"]:
        expected_present.append("L_GOVLAW_01")
    else:
        expected_absent.append("L_GOVLAW_01")
    
    # L_BROADDEF_01: Broad definitions
    if variants.get("definitions_clause") == "broad":
        expected_present.append("L_BROADDEF_01")
    else:
        expected_absent.append("L_BROADDEF_01")
    
    return expected_present, expected_absent


def create_synthetic_nda(idx: int, variants: dict) -> None:
    """Create a synthetic NDA with specified clause variants."""
    doc_id = f"synthetic_{idx:02d}"
    
    # Build NDA text
    nda_text = BASE_NDA.format(
        date="2024-01-01",
        **{k: CLAUSE_VARIANTS[k][v] for k, v in variants.items()}
    )
    
    # Save text
    text_path = DATA_DIR / f"{doc_id}.txt"
    save_text(nda_text, text_path)
    
    # Determine expected rules
    expected_present, expected_absent = get_expected_rules(variants)
    
    # Save metadata
    meta = {
        "id": doc_id,
        "type": "synthetic",
        "synthetic": True,
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "variants": variants
    }
    meta_path = DATA_DIR / f"{doc_id}.meta.json"
    save_json(meta, meta_path)
    
    # Save truth labels
    truth = {
        "expected_rule_ids_present": expected_present,
        "expected_rule_ids_absent": expected_absent
    }
    truth_path = DATA_DIR / f"{doc_id}.truth.json"
    save_json(truth, truth_path)


def build_synthetic_ndas():
    """Build all synthetic NDA files with varied clause combinations."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create diverse combinations targeting different rules
    test_cases = [
        # High-risk focused
        {"confidentiality_term": "limited", "indemnification_clause": "unlimited", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "uncapped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "broad_assignment", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "one_way", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "limited_by_law", "liability_clause": "carveout", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "carveout_law", "ip_clause": "excludes_preexisting", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        
        # Medium-risk focused
        {"confidentiality_term": "perpetual", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "indefinite", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "auto_renewal", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "auto_renewal_terminated", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "with_notice", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "inspect_records", "late_fees_clause": "none", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        
        # Low-risk focused
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "high_interest", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "late_fee", "governing_law_clause": "none", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "specific", "definitions_clause": "specific", "confidentiality_obligations": "standard"},
        {"confidentiality_term": "limited", "indemnification_clause": "none", "liability_clause": "capped", "ip_clause": "none", "attorneys_fees_clause": "none", "renewal_clause": "none", "audit_clause": "none", "late_fees_clause": "none", "governing_law_clause": "exclusive_jurisdiction", "definitions_clause": "broad", "confidentiality_obligations": "standard"},
    ]
    
    for i, variants in enumerate(test_cases[:NUM_SYNTHETIC_NDAS], 1):
        create_synthetic_nda(i, variants)
    
    print(f"Created {NUM_SYNTHETIC_NDAS} synthetic NDA files in {DATA_DIR}")


if __name__ == "__main__":
    build_synthetic_ndas()
