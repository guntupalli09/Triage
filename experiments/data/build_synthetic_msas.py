"""
Build synthetic MSA (Master Service Agreement) dataset with controlled clause toggles.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add experiments parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from experiments.config import DATA_BASE_DIR
from experiments.utils_io import save_text, save_json


# Base MSA template
BASE_MSA = """MASTER SERVICE AGREEMENT

This Master Service Agreement ("Agreement") is entered into between Service Provider ("Provider") and Client Company ("Client").

1. SERVICES
Provider agrees to provide the services described in attached Statements of Work.

2. PAYMENT TERMS
{payment_terms}

3. INTELLECTUAL PROPERTY
{ip_clause}

4. INDEMNIFICATION
{indemnification_clause}

5. LIMITATION OF LIABILITY
{liability_clause}

6. TERM AND TERMINATION
{termination_clause}

7. CONFIDENTIALITY
{confidentiality_clause}

8. WARRANTIES
{warranty_clause}

9. DISPUTE RESOLUTION
{dispute_clause}

10. GOVERNING LAW
{governing_law}

11. ATTORNEYS' FEES
{attorneys_fees_clause}

12. MODIFICATIONS
This Agreement may only be modified in writing signed by both parties.
"""


# Test cases with controlled variations
TEST_CASES = [
    {
        "id": "msa_01",
        "payment_terms": "Payment is due within 30 days of invoice date.",
        "ip_clause": "All work product and deliverables shall be owned by Client. Provider hereby assigns all rights, title, and interest in the work product to Client.",
        "indemnification_clause": "Provider shall indemnify Client against all claims, losses, and expenses without limitation.",
        "liability_clause": "In no event shall Provider's liability exceed the total fees paid under this Agreement.",
        "termination_clause": "Either party may terminate with 30 days written notice.",
        "confidentiality_clause": "Both parties agree to maintain confidentiality of proprietary information for a period of 2 years after termination.",
        "warranty_clause": "Provider warrants that services will be performed in a professional manner.",
        "dispute_clause": "Disputes shall be resolved through binding arbitration.",
        "governing_law": "This Agreement shall be governed by the laws of the State of California.",
        "attorneys_fees_clause": "In the event of any dispute, Client shall be entitled to recover reasonable attorneys' fees and costs.",
        "expected_rule_ids_present": ["H_IP_01", "H_INDEM_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "msa_02",
        "payment_terms": "Payment is due within 15 days. Late payments incur a 2% monthly fee.",
        "ip_clause": "Provider retains ownership of pre-existing intellectual property. Client receives a non-exclusive license to use deliverables.",
        "indemnification_clause": "Each party shall indemnify the other to the extent required by applicable law.",
        "liability_clause": "Provider's liability is limited to the amount paid in the 12 months preceding the claim, except for gross negligence or willful misconduct.",
        "termination_clause": "Either party may terminate immediately upon material breach.",
        "confidentiality_clause": "Confidentiality obligations survive termination indefinitely.",
        "warranty_clause": "Provider disclaims all warranties except as expressly stated herein.",
        "dispute_clause": "Disputes shall be resolved through mediation, then arbitration if mediation fails.",
        "governing_law": "This Agreement shall be governed by the laws of the State of New York.",
        "attorneys_fees_clause": "Each party shall bear its own attorneys' fees.",
        "expected_rule_ids_present": ["L_LATEFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01", "H_ATTFEE_01"],
    },
    {
        "id": "msa_03",
        "payment_terms": "Payment terms are as specified in each Statement of Work.",
        "ip_clause": "All intellectual property developed under this Agreement shall be jointly owned by both parties.",
        "indemnification_clause": "Provider agrees to indemnify Client for third-party claims arising from Provider's breach of this Agreement, up to a maximum of $500,000.",
        "liability_clause": "Neither party's liability shall exceed the total contract value.",
        "termination_clause": "This Agreement may be terminated by mutual written consent or upon 60 days notice.",
        "confidentiality_clause": "Confidential information must be kept confidential for 3 years after termination.",
        "warranty_clause": "Provider warrants compliance with all applicable laws and regulations.",
        "dispute_clause": "Any disputes shall be resolved in the courts of the State of Delaware.",
        "governing_law": "This Agreement is governed by Delaware state law.",
        "attorneys_fees_clause": "The prevailing party in any dispute shall be entitled to recover reasonable attorneys' fees.",
        "expected_rule_ids_present": ["H_ATTFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01"],
    },
    {
        "id": "msa_04",
        "payment_terms": "Client shall pay Provider monthly in advance based on the service schedule.",
        "ip_clause": "Provider grants Client a perpetual, non-exclusive license to use deliverables for Client's internal business purposes only.",
        "indemnification_clause": "Mutual indemnification: each party indemnifies the other for claims arising from its own negligence, capped at the annual contract value.",
        "liability_clause": "Liability is capped at the greater of $1,000,000 or the annual contract value, except for indemnification obligations.",
        "termination_clause": "Either party may terminate for convenience with 90 days written notice.",
        "confidentiality_clause": "Confidentiality obligations continue for 5 years after termination.",
        "warranty_clause": "Provider provides services on an 'as-is' basis with no warranties.",
        "dispute_clause": "Disputes shall be resolved through good faith negotiation.",
        "governing_law": "This Agreement is subject to the laws of the State of Texas.",
        "attorneys_fees_clause": "Each party bears its own legal costs.",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01", "H_ATTFEE_01"],
    },
    {
        "id": "msa_05",
        "payment_terms": "Payment is due net 45 days. Interest accrues on overdue amounts at 1.5% per month.",
        "ip_clause": "All deliverables and work product become the exclusive property of Client upon payment. Provider waives all moral rights.",
        "indemnification_clause": "Provider shall defend, indemnify, and hold harmless Client from any and all claims, without limitation, arising from Provider's performance of services.",
        "liability_clause": "Notwithstanding any other provision, Provider's liability for indemnification claims is unlimited.",
        "termination_clause": "Client may terminate immediately. Provider requires 30 days notice.",
        "confidentiality_clause": "Confidentiality survives termination and continues in perpetuity.",
        "warranty_clause": "Provider warrants that all services will meet industry standards and comply with specifications.",
        "dispute_clause": "All disputes must be resolved through binding arbitration in accordance with AAA rules.",
        "governing_law": "This Agreement is governed by California law, without regard to conflict of law principles.",
        "attorneys_fees_clause": "Client is entitled to recover all attorneys' fees and costs in any action to enforce this Agreement.",
        "expected_rule_ids_present": ["H_IP_01", "H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    # Additional test cases for expanded dataset (6-20)
    {
        "id": "msa_06",
        "payment_terms": "Payment is due net 30 days. Interest accrues at 1.5% per month on overdue amounts.",
        "ip_clause": "All deliverables become the exclusive property of Client upon final payment. Provider waives all moral rights.",
        "indemnification_clause": "Provider shall defend and indemnify Client from all third-party claims, without limitation, arising from Provider's services.",
        "liability_clause": "Provider's liability for indemnification claims is unlimited and not subject to any cap.",
        "termination_clause": "Client may terminate immediately. Provider requires 60 days notice.",
        "confidentiality_clause": "Confidentiality survives termination and continues in perpetuity.",
        "warranty_clause": "Provider warrants that all services meet industry standards and comply with specifications.",
        "dispute_clause": "All disputes must be resolved through binding arbitration under AAA rules.",
        "governing_law": "This Agreement is governed by California law, without regard to conflict of law principles.",
        "attorneys_fees_clause": "Client is entitled to recover all attorneys' fees and costs in any action to enforce this Agreement.",
        "expected_rule_ids_present": ["H_IP_01", "H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "msa_07",
        "payment_terms": "Payment terms are specified in each Statement of Work. Late payments accrue interest at 2% per month.",
        "ip_clause": "Provider retains ownership of all pre-existing intellectual property. Client receives a limited license for deliverables.",
        "indemnification_clause": "Each party indemnifies the other to the extent required by applicable law for claims arising from its own breach.",
        "liability_clause": "Each party's liability is limited to the annual contract value, except as required by law.",
        "termination_clause": "Either party may terminate with 45 days written notice for convenience.",
        "confidentiality_clause": "Confidentiality obligations continue for 4 years after termination.",
        "warranty_clause": "Provider warrants services will be performed in accordance with industry standards.",
        "dispute_clause": "Disputes shall be resolved through good faith negotiation, then mediation if needed.",
        "governing_law": "This Agreement is subject to New York state law.",
        "attorneys_fees_clause": "Each party bears its own legal costs unless the other party prevails.",
        "expected_rule_ids_present": ["L_LATEFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01", "H_ATTFEE_01"],
    },
    {
        "id": "msa_08",
        "payment_terms": "Client shall pay Provider within 20 days of invoice date. A late fee of 5% applies to overdue amounts.",
        "ip_clause": "All work product created under this Agreement shall be assigned to Client. Provider hereby assigns all right, title, and interest.",
        "indemnification_clause": "Provider shall indemnify, defend, and hold harmless Client from all claims, losses, and expenses, without limit.",
        "liability_clause": "Notwithstanding any other provision, Provider's liability is unlimited for indemnification and confidentiality breaches.",
        "termination_clause": "This Agreement may be terminated by either party with 30 days written notice.",
        "confidentiality_clause": "Confidentiality obligations are perpetual and survive termination indefinitely.",
        "warranty_clause": "Provider provides services on an 'as-is' basis with no express or implied warranties.",
        "dispute_clause": "Any disputes shall be resolved exclusively in the courts of Delaware.",
        "governing_law": "Delaware law governs this Agreement.",
        "attorneys_fees_clause": "The prevailing party in any legal action shall recover reasonable attorneys' fees from the other party.",
        "expected_rule_ids_present": ["H_IP_01", "H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "msa_09",
        "payment_terms": "Payment is due upon completion of services as specified in the Statement of Work.",
        "ip_clause": "Intellectual property developed during the term of this Agreement shall be jointly owned by Provider and Client.",
        "indemnification_clause": "Mutual indemnification: each party indemnifies the other for its own negligence, capped at $250,000 per claim.",
        "liability_clause": "Each party's liability is capped at the total fees paid in the preceding 12 months.",
        "termination_clause": "Either party may terminate for convenience with 60 days written notice.",
        "confidentiality_clause": "Confidentiality obligations continue for 2 years after termination.",
        "warranty_clause": "Provider warrants that services will be performed in a professional and workmanlike manner.",
        "dispute_clause": "Disputes shall be resolved through mediation followed by binding arbitration if mediation fails.",
        "governing_law": "This Agreement is governed by Massachusetts state law.",
        "attorneys_fees_clause": "Each party is responsible for its own attorneys' fees.",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01", "H_ATTFEE_01"],
    },
    {
        "id": "msa_10",
        "payment_terms": "Payment is due within 45 days. Overdue payments accrue interest at 18% per annum.",
        "ip_clause": "All deliverables and work product shall become the sole and exclusive property of Client. Provider assigns all rights to Client.",
        "indemnification_clause": "Provider agrees to indemnify Client for all claims, damages, and expenses, without limitation, arising from Provider's performance.",
        "liability_clause": "Provider's liability is unlimited and not subject to any limitation of liability clause.",
        "termination_clause": "Client may terminate immediately. Provider requires 90 days notice.",
        "confidentiality_clause": "Confidentiality obligations are perpetual and continue without time limitation.",
        "warranty_clause": "Provider warrants compliance with all applicable laws, regulations, and industry standards.",
        "dispute_clause": "All disputes must be resolved through mandatory binding arbitration in accordance with JAMS rules.",
        "governing_law": "This Agreement is governed by Texas law, and parties consent to exclusive jurisdiction in Texas courts.",
        "attorneys_fees_clause": "In any action to enforce this Agreement, Client shall recover all attorneys' fees, costs, and expenses from Provider.",
        "expected_rule_ids_present": ["H_IP_01", "H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "msa_11",
        "payment_terms": "Payment terms are as set forth in the applicable Statement of Work. Late payments incur a 3% monthly fee.",
        "ip_clause": "Provider grants Client a worldwide, perpetual, exclusive license to use all deliverables for any purpose.",
        "indemnification_clause": "Provider shall indemnify Client to the extent required by applicable law for third-party claims.",
        "liability_clause": "Provider's liability is limited to the fees paid in the 6 months preceding the claim.",
        "termination_clause": "This Agreement may be terminated by mutual agreement or by either party with 30 days notice.",
        "confidentiality_clause": "Confidentiality obligations survive termination for 3 years.",
        "warranty_clause": "Provider disclaims all warranties, express or implied, except as specifically stated.",
        "dispute_clause": "Disputes shall be resolved through negotiation, then litigation if negotiation fails.",
        "governing_law": "This Agreement is subject to Illinois state law.",
        "attorneys_fees_clause": "The prevailing party in any dispute shall be entitled to recover reasonable attorneys' fees.",
        "expected_rule_ids_present": ["H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01"],
    },
    {
        "id": "msa_12",
        "payment_terms": "Client shall pay Provider according to the payment schedule in each Statement of Work.",
        "ip_clause": "Provider retains all rights in pre-existing intellectual property. Client receives a non-exclusive, non-transferable license.",
        "indemnification_clause": "Each party shall indemnify the other for claims arising from its own gross negligence or willful misconduct, capped at annual contract value.",
        "liability_clause": "Each party's liability is limited to the total contract value, except for indemnification obligations.",
        "termination_clause": "Either party may terminate for convenience with 45 days written notice.",
        "confidentiality_clause": "Confidentiality obligations continue for 5 years after termination of this Agreement.",
        "warranty_clause": "Provider warrants that services will be performed in accordance with the Statement of Work.",
        "dispute_clause": "Disputes shall be resolved through good faith discussion between the parties.",
        "governing_law": "This Agreement is governed by the laws of the State of Washington.",
        "attorneys_fees_clause": "Each party shall pay its own attorneys' fees and costs.",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01", "H_ATTFEE_01"],
    },
    {
        "id": "msa_13",
        "payment_terms": "Payment is due within 25 days. Interest on overdue amounts accrues at 1% per month.",
        "ip_clause": "All intellectual property developed under this Agreement shall be owned by Client. Provider hereby assigns all such rights to Client.",
        "indemnification_clause": "Provider shall indemnify Client against all claims, losses, damages, and expenses, without limitation, arising from Provider's breach of this Agreement.",
        "liability_clause": "Provider's liability is unlimited for indemnification, confidentiality, and intellectual property claims.",
        "termination_clause": "Client may terminate immediately upon written notice. Provider requires 45 days notice.",
        "confidentiality_clause": "Confidentiality obligations are perpetual and continue indefinitely after termination.",
        "warranty_clause": "Provider warrants that all services will meet or exceed the specifications in the Statement of Work.",
        "dispute_clause": "All disputes must be resolved through binding arbitration under the rules of the American Arbitration Association.",
        "governing_law": "This Agreement is governed by California law, and parties submit to exclusive jurisdiction in California courts.",
        "attorneys_fees_clause": "Client shall be entitled to recover all attorneys' fees, court costs, and expenses from Provider in any enforcement action.",
        "expected_rule_ids_present": ["H_IP_01", "H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "msa_14",
        "payment_terms": "Payment terms are net 30 days from invoice date. A late payment fee of 4% applies to overdue amounts.",
        "ip_clause": "Provider grants Client a royalty-free, perpetual license to use deliverables for Client's business operations.",
        "indemnification_clause": "Mutual indemnification: each party indemnifies the other for its own negligence, up to $1,000,000 per claim.",
        "liability_clause": "Each party's liability is capped at the greater of $500,000 or the annual contract value.",
        "termination_clause": "This Agreement may be terminated by either party with 60 days written notice for any reason.",
        "confidentiality_clause": "Confidentiality obligations survive termination and continue for 4 years.",
        "warranty_clause": "Provider provides services 'as-is' with no warranties except as expressly stated.",
        "dispute_clause": "Disputes shall be resolved through mediation, then arbitration if mediation is unsuccessful.",
        "governing_law": "This Agreement is governed by Florida state law.",
        "attorneys_fees_clause": "The prevailing party in any dispute shall recover reasonable attorneys' fees from the non-prevailing party.",
        "expected_rule_ids_present": ["H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01"],
    },
    {
        "id": "msa_15",
        "payment_terms": "Client shall pay Provider monthly in advance based on the service schedule. Late payments incur interest at 2% per month.",
        "ip_clause": "All work product and deliverables created by Provider under this Agreement shall be the exclusive property of Client. Provider assigns all rights to Client.",
        "indemnification_clause": "Provider shall defend, indemnify, and hold harmless Client from all claims, without limit, arising from Provider's services or breach of this Agreement.",
        "liability_clause": "Notwithstanding the limitation of liability clause, Provider's liability for indemnification is unlimited.",
        "termination_clause": "Either party may terminate for convenience with 30 days written notice.",
        "confidentiality_clause": "Confidentiality obligations are perpetual and survive termination without time limitation.",
        "warranty_clause": "Provider warrants that services will be performed in a professional manner and comply with all applicable laws.",
        "dispute_clause": "Any disputes arising from this Agreement shall be resolved exclusively through binding arbitration.",
        "governing_law": "This Agreement is governed by the laws of the State of Colorado.",
        "attorneys_fees_clause": "In any action to enforce this Agreement, the prevailing party shall recover all attorneys' fees and costs from the other party.",
        "expected_rule_ids_present": ["H_IP_01", "H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "msa_16",
        "payment_terms": "Payment is due within 35 days of invoice date. Overdue payments accrue interest at 1.5% per month.",
        "ip_clause": "Provider retains ownership of all pre-existing intellectual property. Client receives a limited, non-exclusive license for deliverables.",
        "indemnification_clause": "Each party shall indemnify the other to the extent required by applicable law for claims arising from its own breach.",
        "liability_clause": "Each party's liability is limited to the total fees paid under this Agreement in the preceding calendar year.",
        "termination_clause": "This Agreement may be terminated by mutual written consent or by either party with 90 days notice.",
        "confidentiality_clause": "Confidentiality obligations continue for 3 years after termination of this Agreement.",
        "warranty_clause": "Provider warrants compliance with all applicable laws and regulations in performing services.",
        "dispute_clause": "Disputes shall be resolved through good faith negotiation between authorized representatives.",
        "governing_law": "This Agreement is subject to Oregon state law.",
        "attorneys_fees_clause": "Each party bears its own legal expenses in connection with any dispute.",
        "expected_rule_ids_present": ["L_LATEFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01", "H_ATTFEE_01"],
    },
    {
        "id": "msa_17",
        "payment_terms": "Payment terms are specified in each Statement of Work. Late payments incur a late fee of 6% of the overdue amount.",
        "ip_clause": "All intellectual property developed during the term of this Agreement shall be jointly owned by Provider and Client, with each party having the right to use and license such IP.",
        "indemnification_clause": "Provider agrees to indemnify Client for third-party claims arising from Provider's gross negligence, up to a maximum of $750,000 per claim.",
        "liability_clause": "Provider's liability is capped at the total contract value, except for indemnification obligations which are unlimited.",
        "termination_clause": "Either party may terminate immediately upon material breach by the other party.",
        "confidentiality_clause": "Confidentiality obligations survive termination and continue for 6 years.",
        "warranty_clause": "Provider provides services on an 'as-is' basis with no warranties, express or implied.",
        "dispute_clause": "Disputes shall be resolved through mediation, and if unsuccessful, through binding arbitration.",
        "governing_law": "This Agreement is governed by Arizona state law.",
        "attorneys_fees_clause": "The prevailing party in any legal proceeding shall be entitled to recover reasonable attorneys' fees.",
        "expected_rule_ids_present": ["H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01"],
    },
    {
        "id": "msa_18",
        "payment_terms": "Client shall pay Provider according to the payment schedule in the Statement of Work. Interest accrues at 2.5% per month on overdue amounts.",
        "ip_clause": "All deliverables and work product created under this Agreement shall become the sole and exclusive property of Client. Provider hereby irrevocably assigns all such rights to Client.",
        "indemnification_clause": "Provider shall indemnify, defend, and hold harmless Client from any and all claims, losses, damages, and expenses, without limitation, arising from Provider's performance of services.",
        "liability_clause": "Provider's liability is unlimited and not subject to any cap, including for indemnification, confidentiality, and intellectual property claims.",
        "termination_clause": "Client may terminate this Agreement at any time with or without cause. Provider requires 60 days written notice to terminate.",
        "confidentiality_clause": "Confidentiality obligations are perpetual and continue indefinitely, without any time limitation.",
        "warranty_clause": "Provider warrants that all services will be performed in accordance with industry best practices and applicable standards.",
        "dispute_clause": "All disputes must be resolved through mandatory binding arbitration in accordance with the rules of the International Chamber of Commerce.",
        "governing_law": "This Agreement is governed by California law, and the parties consent to exclusive jurisdiction in California courts.",
        "attorneys_fees_clause": "In any action to enforce or interpret this Agreement, Client shall be entitled to recover all attorneys' fees, costs, and expenses from Provider.",
        "expected_rule_ids_present": ["H_IP_01", "H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "msa_19",
        "payment_terms": "Payment is due within 40 days of invoice date. Late payments incur interest at 1% per month.",
        "ip_clause": "Provider grants Client a worldwide, perpetual, non-exclusive license to use deliverables for Client's internal business purposes.",
        "indemnification_clause": "Mutual indemnification: each party indemnifies the other for claims arising from its own breach, capped at the annual contract value.",
        "liability_clause": "Each party's liability is limited to the total fees paid in the 24 months preceding the claim.",
        "termination_clause": "This Agreement may be terminated by either party with 45 days written notice for convenience.",
        "confidentiality_clause": "Confidentiality obligations continue for 2 years after termination of this Agreement.",
        "warranty_clause": "Provider warrants that services will be performed in a professional and workmanlike manner.",
        "dispute_clause": "Disputes shall be resolved through direct negotiation between the parties' authorized representatives.",
        "governing_law": "This Agreement is governed by the laws of the State of Nevada.",
        "attorneys_fees_clause": "Each party shall pay its own attorneys' fees and costs in connection with any dispute.",
        "expected_rule_ids_present": ["L_LATEFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01", "H_ATTFEE_01"],
    },
    {
        "id": "msa_20",
        "payment_terms": "Payment terms are as set forth in each Statement of Work. Overdue payments accrue interest at 3% per month.",
        "ip_clause": "All work product, inventions, and intellectual property created by Provider under this Agreement shall be owned by Client. Provider assigns all such rights to Client.",
        "indemnification_clause": "Provider shall indemnify Client for all claims, damages, losses, and expenses, without limitation, resulting from Provider's breach of this Agreement or negligence.",
        "liability_clause": "Provider's liability is unlimited for indemnification obligations and breaches of confidentiality or intellectual property provisions.",
        "termination_clause": "Either party may terminate for convenience with 30 days written notice, or immediately upon material breach.",
        "confidentiality_clause": "Confidentiality obligations survive termination and continue in perpetuity without expiration.",
        "warranty_clause": "Provider warrants that all services will comply with applicable laws, regulations, and industry standards.",
        "dispute_clause": "All disputes arising from this Agreement shall be resolved through binding arbitration under AAA Commercial Arbitration Rules.",
        "governing_law": "This Agreement is governed by California law, without regard to conflict of law principles.",
        "attorneys_fees_clause": "The prevailing party in any dispute or enforcement action shall recover all attorneys' fees, costs, and expenses from the non-prevailing party.",
        "expected_rule_ids_present": ["H_IP_01", "H_INDEM_01", "H_LOL_CARVEOUT_01", "H_ATTFEE_01", "L_LATEFEE_01"],
        "expected_rule_ids_absent": [],
    },
]


def build_synthetic_msas():
    """Generate synthetic MSA documents with ground-truth labels."""
    print("Building synthetic MSA dataset...")
    
    msa_dir = DATA_BASE_DIR / "msas"
    msa_dir.mkdir(parents=True, exist_ok=True)
    
    for case in TEST_CASES:
        doc_id = case["id"]
        
        # Generate document text
        doc_text = BASE_MSA.format(
            payment_terms=case["payment_terms"],
            ip_clause=case["ip_clause"],
            indemnification_clause=case["indemnification_clause"],
            liability_clause=case["liability_clause"],
            termination_clause=case["termination_clause"],
            confidentiality_clause=case["confidentiality_clause"],
            warranty_clause=case["warranty_clause"],
            dispute_clause=case["dispute_clause"],
            governing_law=case["governing_law"],
            attorneys_fees_clause=case["attorneys_fees_clause"],
        )
        
        # Save text file
        save_text(doc_text, msa_dir / f"{doc_id}.txt")
        
        # Create metadata
        metadata = {
            "id": doc_id,
            "type": "synthetic",
            "contract_type": "MSA",
            "generated_date": datetime.now().isoformat(),
            "source": "synthetic_generator",
        }
        save_json(metadata, msa_dir / f"{doc_id}.meta.json")
        
        # Create ground-truth labels
        truth = {
            "expected_rule_ids_present": case["expected_rule_ids_present"],
            "expected_rule_ids_absent": case["expected_rule_ids_absent"],
            "contract_type": "MSA",
        }
        save_json(truth, msa_dir / f"{doc_id}.truth.json")
        
        print(f"  Generated {doc_id}")
    
    print(f"\nGenerated {len(TEST_CASES)} synthetic MSA documents in {msa_dir}")


if __name__ == "__main__":
    build_synthetic_msas()
