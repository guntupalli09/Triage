"""
Build synthetic Licensing Agreement dataset with controlled clause toggles.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add experiments parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from experiments.config import DATA_BASE_DIR
from experiments.utils_io import save_text, save_json


# Base Licensing Agreement template
BASE_LICENSING = """SOFTWARE LICENSING AGREEMENT

This Software Licensing Agreement ("Agreement") is entered into between Licensor Company ("Licensor") and Licensee Company ("Licensee").

1. GRANT OF LICENSE
{license_grant}

2. INTELLECTUAL PROPERTY OWNERSHIP
{ip_ownership}

3. PAYMENT TERMS
{payment_terms}

4. TERM AND TERMINATION
{termination_clause}

5. INDEMNIFICATION
{indemnification_clause}

6. LIMITATION OF LIABILITY
{liability_clause}

7. CONFIDENTIALITY
{confidentiality_clause}

8. WARRANTIES AND DISCLAIMERS
{warranty_clause}

9. DISPUTE RESOLUTION
{dispute_clause}

10. ATTORNEYS' FEES
{attorneys_fees_clause}

11. GOVERNING LAW
{governing_law}

This Agreement is effective as of {date}.
"""


# Test cases with controlled variations
TEST_CASES = [
    {
        "id": "lic_01",
        "license_grant": "Licensor grants Licensee a non-exclusive, worldwide license to use the Software for internal business purposes only.",
        "ip_ownership": "Licensor retains all ownership rights in the Software. Licensee receives no ownership interest.",
        "payment_terms": "Licensee shall pay an annual license fee of $50,000, due within 30 days of invoice date.",
        "termination_clause": "Either party may terminate with 60 days written notice. Licensor may terminate immediately upon breach.",
        "indemnification_clause": "Licensee shall indemnify Licensor against all claims, losses, and expenses without limitation arising from Licensee's use of the Software.",
        "liability_clause": "Licensor's liability is unlimited and not subject to any limitation of liability clause.",
        "confidentiality_clause": "Confidentiality obligations survive termination and continue in perpetuity.",
        "warranty_clause": "Licensor disclaims all warranties, express or implied, including merchantability and fitness for a particular purpose.",
        "dispute_clause": "All disputes must be resolved through binding arbitration under AAA rules.",
        "attorneys_fees_clause": "Licensor shall be entitled to recover all attorneys' fees and costs in any action to enforce this Agreement.",
        "governing_law": "This Agreement is governed by California law.",
        "date": "January 1, 2024",
        "expected_rule_ids_present": ["H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "lic_02",
        "license_grant": "Licensor grants Licensee a perpetual, exclusive license to use the Software for commercial purposes.",
        "ip_ownership": "Licensor retains ownership of the Software. Licensee receives a license only, with no ownership rights.",
        "payment_terms": "Licensee shall pay a one-time license fee of $100,000, due upon execution of this Agreement.",
        "termination_clause": "This Agreement may be terminated by mutual consent or by either party with 90 days notice.",
        "indemnification_clause": "Each party shall indemnify the other to the extent required by applicable law for third-party claims.",
        "liability_clause": "Each party's liability is limited to the total license fees paid under this Agreement.",
        "confidentiality_clause": "Confidentiality obligations continue for 3 years after termination.",
        "warranty_clause": "Licensor warrants that the Software will perform substantially in accordance with the documentation.",
        "dispute_clause": "Disputes shall be resolved through mediation, then litigation if mediation fails.",
        "attorneys_fees_clause": "Each party shall bear its own attorneys' fees.",
        "governing_law": "This Agreement is subject to New York state law.",
        "date": "February 1, 2024",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "lic_03",
        "license_grant": "Licensor grants Licensee a limited, non-transferable license to use the Software for Licensee's internal operations.",
        "ip_ownership": "All intellectual property rights in the Software remain with Licensor. Licensee acquires no ownership interest.",
        "payment_terms": "Licensee shall pay monthly license fees of $5,000, due on the first of each month. Late payments incur a 2% monthly fee.",
        "termination_clause": "Either party may terminate for convenience with 30 days written notice.",
        "indemnification_clause": "Licensee agrees to indemnify Licensor for claims arising from Licensee's breach of this Agreement, up to a maximum of $500,000.",
        "liability_clause": "Licensor's liability is capped at the total license fees paid in the preceding 12 months.",
        "confidentiality_clause": "Confidentiality obligations survive termination and continue for 5 years.",
        "warranty_clause": "Licensor provides the Software 'as-is' with no warranties, except as expressly stated.",
        "dispute_clause": "Any disputes shall be resolved in the courts of the State of Delaware.",
        "attorneys_fees_clause": "The prevailing party in any dispute shall be entitled to recover reasonable attorneys' fees.",
        "governing_law": "Delaware law governs this Agreement.",
        "date": "March 1, 2024",
        "expected_rule_ids_present": ["H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01"],
    },
    {
        "id": "lic_04",
        "license_grant": "Licensor grants Licensee a worldwide, perpetual, non-exclusive license to use, modify, and distribute the Software.",
        "ip_ownership": "Licensor retains all ownership rights. Licensee receives a license only, with no assignment of rights.",
        "payment_terms": "Licensee shall pay annual license fees as specified in Schedule A, due within 45 days of invoice date.",
        "termination_clause": "This Agreement may be terminated by either party with 60 days written notice for any reason.",
        "indemnification_clause": "Mutual indemnification: each party indemnifies the other for its own negligence, capped at annual license fees.",
        "liability_clause": "Each party's liability is limited to the greater of $1,000,000 or the annual license fees.",
        "confidentiality_clause": "Confidentiality obligations continue for 2 years after termination.",
        "warranty_clause": "Licensor warrants that the Software will substantially conform to the specifications in the documentation.",
        "dispute_clause": "Disputes shall be resolved through good faith negotiation between authorized representatives.",
        "attorneys_fees_clause": "Each party is responsible for its own legal expenses.",
        "governing_law": "This Agreement is governed by Massachusetts state law.",
        "date": "April 1, 2024",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "lic_05",
        "license_grant": "Licensor grants Licensee an exclusive license to use the Software in Licensee's territory for commercial purposes.",
        "ip_ownership": "All intellectual property rights in the Software, including modifications, shall be owned by Licensor. Licensee assigns all such rights to Licensor.",
        "payment_terms": "Licensee shall pay a one-time license fee of $250,000, due within 15 days. Late payments accrue interest at 18% per annum.",
        "termination_clause": "Licensor may terminate immediately upon Licensee's breach. Licensee requires 90 days notice to terminate.",
        "indemnification_clause": "Licensee shall defend, indemnify, and hold harmless Licensor from all claims, without limitation, arising from Licensee's use of the Software.",
        "liability_clause": "Licensor's liability is unlimited for indemnification, confidentiality, and intellectual property claims.",
        "confidentiality_clause": "Confidentiality obligations are perpetual and survive termination indefinitely.",
        "warranty_clause": "Licensor warrants that the Software will perform in accordance with all specifications and applicable laws.",
        "dispute_clause": "All disputes must be resolved through binding arbitration under the rules of JAMS.",
        "attorneys_fees_clause": "In any action to enforce this Agreement, Licensor shall recover all attorneys' fees, costs, and expenses from Licensee.",
        "governing_law": "This Agreement is governed by California law, and parties consent to exclusive jurisdiction in California courts.",
        "date": "May 1, 2024",
        "expected_rule_ids_present": ["H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "lic_06",
        "license_grant": "Licensor grants Licensee a non-exclusive, revocable license to use the Software for evaluation purposes only.",
        "ip_ownership": "Licensor retains all ownership rights. Licensee receives no ownership interest in the Software or any modifications.",
        "payment_terms": "No license fees apply during the evaluation period. If Licensee purchases a full license, payment terms will be specified in a separate agreement.",
        "termination_clause": "Either party may terminate this evaluation license with 7 days written notice.",
        "indemnification_clause": "Licensee shall indemnify Licensor to the extent required by law for claims arising from Licensee's use of the Software.",
        "liability_clause": "Licensor's liability is limited to the amount of any license fees actually paid by Licensee.",
        "confidentiality_clause": "Confidentiality obligations continue for 1 year after termination of the evaluation period.",
        "warranty_clause": "Licensor provides the Software 'as-is' with no warranties during the evaluation period.",
        "dispute_clause": "Disputes shall be resolved through direct negotiation between the parties.",
        "attorneys_fees_clause": "Each party bears its own legal costs.",
        "governing_law": "This Agreement is subject to Texas state law.",
        "date": "June 1, 2024",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "lic_07",
        "license_grant": "Licensor grants Licensee a perpetual, worldwide, non-exclusive license to use and modify the Software for Licensee's internal business operations.",
        "ip_ownership": "All modifications and derivative works created by Licensee shall be owned by Licensor. Licensee hereby assigns all such rights to Licensor.",
        "payment_terms": "Licensee shall pay annual maintenance fees of $25,000, due on the anniversary date. Late payments incur a 3% monthly fee.",
        "termination_clause": "This Agreement may be terminated by either party with 45 days written notice for convenience.",
        "indemnification_clause": "Licensee agrees to indemnify Licensor for all claims, damages, and expenses, without limitation, arising from Licensee's modifications to the Software.",
        "liability_clause": "Notwithstanding any limitation of liability, Licensor's liability for indemnification is unlimited.",
        "confidentiality_clause": "Confidentiality obligations survive termination and continue for 4 years.",
        "warranty_clause": "Licensor disclaims all warranties, express or implied, including merchantability and fitness for a particular purpose.",
        "dispute_clause": "Disputes shall be resolved through mediation, then binding arbitration if mediation is unsuccessful.",
        "attorneys_fees_clause": "The prevailing party in any dispute shall recover reasonable attorneys' fees from the other party.",
        "governing_law": "This Agreement is governed by Florida state law.",
        "date": "July 1, 2024",
        "expected_rule_ids_present": ["H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "lic_08",
        "license_grant": "Licensor grants Licensee a limited, non-exclusive license to use the Software for a specific number of users as specified in Schedule B.",
        "ip_ownership": "Licensor retains all intellectual property rights. Licensee receives a license only, with no ownership or assignment rights.",
        "payment_terms": "Licensee shall pay per-user license fees as set forth in Schedule B, due within 30 days of invoice date.",
        "termination_clause": "Either party may terminate for convenience with 30 days written notice, or immediately upon material breach.",
        "indemnification_clause": "Mutual indemnification: each party indemnifies the other for claims arising from its own breach, capped at $750,000 per claim.",
        "liability_clause": "Each party's liability is limited to the total license fees paid in the preceding calendar year.",
        "confidentiality_clause": "Confidentiality obligations continue for 3 years after termination of this Agreement.",
        "warranty_clause": "Licensor warrants that the Software will substantially conform to the documentation provided to Licensee.",
        "dispute_clause": "Any disputes shall be resolved in the courts of the State of Virginia.",
        "attorneys_fees_clause": "Each party shall pay its own attorneys' fees unless the other party prevails in the dispute.",
        "governing_law": "Virginia law governs this Agreement.",
        "date": "August 1, 2024",
        "expected_rule_ids_present": ["H_ATTFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01"],
    },
    {
        "id": "lic_09",
        "license_grant": "Licensor grants Licensee a worldwide, exclusive license to use, distribute, and sublicense the Software in Licensee's designated territory.",
        "ip_ownership": "All intellectual property rights in the Software and any modifications shall be owned by Licensor. Licensee assigns all such rights to Licensor.",
        "payment_terms": "Licensee shall pay royalties of 15% of gross revenue from Software sales, due monthly. Late payments accrue interest at 2% per month.",
        "termination_clause": "Licensor may terminate immediately upon Licensee's breach. Licensee requires 60 days notice to terminate.",
        "indemnification_clause": "Licensee shall defend, indemnify, and hold harmless Licensor from all claims, without limitation, arising from Licensee's distribution or use of the Software.",
        "liability_clause": "Licensor's liability is unlimited for indemnification obligations and breaches of intellectual property provisions.",
        "confidentiality_clause": "Confidentiality obligations are perpetual and continue indefinitely after termination.",
        "warranty_clause": "Licensor warrants that the Software does not infringe any third-party intellectual property rights.",
        "dispute_clause": "All disputes must be resolved through binding arbitration under AAA Commercial Arbitration Rules.",
        "attorneys_fees_clause": "Licensor shall be entitled to recover all attorneys' fees, court costs, and expenses from Licensee in any enforcement action.",
        "governing_law": "This Agreement is governed by California law, and parties consent to exclusive jurisdiction in California courts.",
        "date": "September 1, 2024",
        "expected_rule_ids_present": ["H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "lic_10",
        "license_grant": "Licensor grants Licensee a non-exclusive, perpetual license to use the Software for Licensee's internal business purposes only.",
        "ip_ownership": "Licensor retains ownership of the Software. Licensee receives a license only, with no ownership or assignment rights.",
        "payment_terms": "Licensee shall pay a one-time license fee of $75,000, due upon execution of this Agreement.",
        "termination_clause": "This Agreement may be terminated by mutual written consent or by either party with 90 days notice.",
        "indemnification_clause": "Each party shall indemnify the other for claims arising from its own negligence, capped at the license fee amount.",
        "liability_clause": "Each party's liability is limited to the total fees paid under this Agreement.",
        "confidentiality_clause": "Confidentiality obligations survive termination and continue for 2 years.",
        "warranty_clause": "Licensor provides the Software 'as-is' with no warranties, express or implied.",
        "dispute_clause": "Disputes shall be resolved through good faith negotiation between the parties.",
        "attorneys_fees_clause": "Each party is responsible for its own attorneys' fees and costs.",
        "governing_law": "This Agreement is subject to Illinois state law.",
        "date": "October 1, 2024",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "lic_11",
        "license_grant": "Licensor grants Licensee a limited, non-transferable license to use the Software for a specific number of concurrent users as specified in the license certificate.",
        "ip_ownership": "All modifications, enhancements, and derivative works created by Licensee shall be owned by Licensor. Licensee hereby assigns all such rights to Licensor.",
        "payment_terms": "Licensee shall pay annual license fees of $60,000, due on the anniversary date. Overdue payments incur interest at 1.5% per month.",
        "termination_clause": "Either party may terminate for convenience with 45 days written notice.",
        "indemnification_clause": "Licensee agrees to indemnify Licensor for all claims, losses, and expenses, without limitation, arising from Licensee's use or modification of the Software.",
        "liability_clause": "Licensor's liability is unlimited for indemnification claims and intellectual property breaches.",
        "confidentiality_clause": "Confidentiality obligations continue for 5 years after termination of this Agreement.",
        "warranty_clause": "Licensor disclaims all warranties except as expressly stated in the documentation.",
        "dispute_clause": "Disputes shall be resolved through mediation, then arbitration if mediation fails.",
        "attorneys_fees_clause": "The prevailing party in any dispute shall be entitled to recover reasonable attorneys' fees.",
        "governing_law": "This Agreement is governed by Arizona state law.",
        "date": "November 1, 2024",
        "expected_rule_ids_present": ["H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "lic_12",
        "license_grant": "Licensor grants Licensee a worldwide, non-exclusive license to use the Software for Licensee's business operations, including the right to make backup copies.",
        "ip_ownership": "Licensor retains all ownership rights in the Software. Licensee receives no ownership interest or assignment rights.",
        "payment_terms": "Licensee shall pay monthly subscription fees of $3,000, due on the first of each month.",
        "termination_clause": "Either party may terminate this Agreement with 30 days written notice for any reason.",
        "indemnification_clause": "Mutual indemnification: each party indemnifies the other for its own breach, capped at annual subscription fees.",
        "liability_clause": "Each party's liability is limited to the total fees paid in the 12 months preceding the claim.",
        "confidentiality_clause": "Confidentiality obligations continue for 18 months after termination.",
        "warranty_clause": "Licensor warrants that the Software will perform substantially in accordance with the user documentation.",
        "dispute_clause": "Disputes shall be resolved through direct negotiation between authorized representatives.",
        "attorneys_fees_clause": "Each party bears its own legal expenses.",
        "governing_law": "This Agreement is subject to Colorado state law.",
        "date": "December 1, 2024",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "lic_13",
        "license_grant": "Licensor grants Licensee an exclusive license to use and distribute the Software in Licensee's designated geographic territory.",
        "ip_ownership": "All intellectual property, including modifications and enhancements, shall be owned by Licensor. Licensee assigns all such rights to Licensor.",
        "payment_terms": "Licensee shall pay upfront license fees of $200,000, due within 10 days. Late payments accrue interest at 3% per month.",
        "termination_clause": "Licensor may terminate immediately upon Licensee's material breach. Licensee requires 90 days notice to terminate.",
        "indemnification_clause": "Licensee shall defend, indemnify, and hold harmless Licensor from all claims, damages, and expenses, without limitation, arising from Licensee's distribution or use of the Software.",
        "liability_clause": "Notwithstanding any limitation of liability clause, Licensor's liability for indemnification is unlimited.",
        "confidentiality_clause": "Confidentiality obligations are perpetual and survive termination without any time limitation.",
        "warranty_clause": "Licensor warrants that the Software will comply with all applicable laws and regulations.",
        "dispute_clause": "All disputes must be resolved through binding arbitration under the rules of the International Chamber of Commerce.",
        "attorneys_fees_clause": "In any action to enforce this Agreement, Licensor shall recover all attorneys' fees, costs, and expenses from Licensee.",
        "governing_law": "This Agreement is governed by California law, and parties submit to exclusive jurisdiction in California courts.",
        "date": "January 1, 2025",
        "expected_rule_ids_present": ["H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "lic_14",
        "license_grant": "Licensor grants Licensee a non-exclusive, revocable license to use the Software for evaluation and testing purposes only.",
        "ip_ownership": "Licensor retains all ownership rights. Licensee receives no ownership interest in the Software.",
        "payment_terms": "No fees apply during the evaluation period. If Licensee purchases a full license, payment terms will be specified separately.",
        "termination_clause": "Either party may terminate this evaluation license with 14 days written notice.",
        "indemnification_clause": "Licensee shall indemnify Licensor to the extent required by applicable law for claims arising from Licensee's evaluation use.",
        "liability_clause": "Licensor's liability is limited to the amount of any fees actually paid by Licensee, if any.",
        "confidentiality_clause": "Confidentiality obligations continue for 6 months after termination of the evaluation period.",
        "warranty_clause": "Licensor provides the Software 'as-is' with no warranties during the evaluation period.",
        "dispute_clause": "Disputes shall be resolved through good faith discussion between the parties.",
        "attorneys_fees_clause": "Each party is responsible for its own legal costs.",
        "governing_law": "This Agreement is subject to Nevada state law.",
        "date": "February 1, 2025",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "lic_15",
        "license_grant": "Licensor grants Licensee a perpetual, worldwide, non-exclusive license to use, modify, and create derivative works from the Software for Licensee's internal operations.",
        "ip_ownership": "All modifications, enhancements, and derivative works created by Licensee shall become the exclusive property of Licensor. Licensee hereby irrevocably assigns all such rights to Licensor.",
        "payment_terms": "Licensee shall pay annual license and maintenance fees of $80,000, due on the anniversary date. Overdue payments incur a late fee of 5% plus interest at 2% per month.",
        "termination_clause": "Licensor may terminate immediately upon Licensee's breach. Licensee requires 60 days notice to terminate.",
        "indemnification_clause": "Licensee shall indemnify Licensor for all claims, losses, damages, and expenses, without limitation, arising from Licensee's modifications or use of the Software.",
        "liability_clause": "Licensor's liability is unlimited for indemnification, confidentiality, and intellectual property claims, and is not subject to any cap.",
        "confidentiality_clause": "Confidentiality obligations are perpetual and continue indefinitely, without any expiration or time limitation.",
        "warranty_clause": "Licensor warrants that the Software will substantially conform to the specifications in the documentation provided to Licensee.",
        "dispute_clause": "All disputes must be resolved through mandatory binding arbitration under AAA Commercial Arbitration Rules.",
        "attorneys_fees_clause": "Licensor shall be entitled to recover all attorneys' fees, court costs, and expenses from Licensee in any action to enforce or interpret this Agreement.",
        "governing_law": "This Agreement is governed by California law, and the parties consent to exclusive jurisdiction in California courts.",
        "date": "March 1, 2025",
        "expected_rule_ids_present": ["H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
]


def build_synthetic_licensing():
    """Generate synthetic Licensing Agreement documents with ground-truth labels."""
    print("Building synthetic Licensing Agreement dataset...")
    
    lic_dir = DATA_BASE_DIR / "licensing"
    lic_dir.mkdir(parents=True, exist_ok=True)
    
    for case in TEST_CASES:
        doc_id = case["id"]
        
        # Generate document text
        doc_text = BASE_LICENSING.format(
            license_grant=case["license_grant"],
            ip_ownership=case["ip_ownership"],
            payment_terms=case["payment_terms"],
            termination_clause=case["termination_clause"],
            indemnification_clause=case["indemnification_clause"],
            liability_clause=case["liability_clause"],
            confidentiality_clause=case["confidentiality_clause"],
            warranty_clause=case["warranty_clause"],
            dispute_clause=case["dispute_clause"],
            attorneys_fees_clause=case["attorneys_fees_clause"],
            governing_law=case["governing_law"],
            date=case["date"],
        )
        
        # Save text file
        save_text(doc_text, lic_dir / f"{doc_id}.txt")
        
        # Create metadata
        metadata = {
            "id": doc_id,
            "type": "synthetic",
            "contract_type": "Licensing",
            "generated_date": datetime.now().isoformat(),
            "source": "synthetic_generator",
        }
        save_json(metadata, lic_dir / f"{doc_id}.meta.json")
        
        # Create ground-truth labels
        truth = {
            "expected_rule_ids_present": case["expected_rule_ids_present"],
            "expected_rule_ids_absent": case["expected_rule_ids_absent"],
            "contract_type": "Licensing",
        }
        save_json(truth, lic_dir / f"{doc_id}.truth.json")
        
        print(f"  Generated {doc_id}")
    
    print(f"\nGenerated {len(TEST_CASES)} synthetic Licensing Agreement documents in {lic_dir}")


if __name__ == "__main__":
    build_synthetic_licensing()
