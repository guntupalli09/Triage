"""
Build synthetic Employment Agreement dataset with controlled clause toggles.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add experiments parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from experiments.config import DATA_BASE_DIR
from experiments.utils_io import save_text, save_json


# Base Employment Agreement template
BASE_EMPLOYMENT = """EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into between Employer Company ("Employer") and Employee Name ("Employee").

1. POSITION AND DUTIES
Employee agrees to serve as {position} and perform duties as assigned by Employer.

2. COMPENSATION
{compensation_clause}

3. INTELLECTUAL PROPERTY
{ip_clause}

4. CONFIDENTIALITY AND NON-DISCLOSURE
{confidentiality_clause}

5. NON-COMPETE AND NON-SOLICITATION
{noncompete_clause}

6. TERM AND TERMINATION
{termination_clause}

7. INDEMNIFICATION
{indemnification_clause}

8. DISPUTE RESOLUTION
{dispute_clause}

9. ATTORNEYS' FEES
{attorneys_fees_clause}

10. GOVERNING LAW
{governing_law}

This Agreement is effective as of {date}.
"""


# Test cases with controlled variations
TEST_CASES = [
    {
        "id": "emp_01",
        "position": "Senior Software Engineer",
        "compensation_clause": "Employee shall receive an annual salary of $150,000, payable in bi-weekly installments.",
        "ip_clause": "All inventions, discoveries, and work product created by Employee during employment shall be the exclusive property of Employer. Employee hereby assigns all rights, title, and interest in such work product to Employer.",
        "confidentiality_clause": "Employee agrees to maintain confidentiality of all proprietary information indefinitely, even after termination of employment.",
        "noncompete_clause": "Employee agrees not to compete with Employer for a period of 2 years after termination, within a 50-mile radius.",
        "termination_clause": "Either party may terminate this Agreement at will, with or without cause, upon 2 weeks written notice.",
        "indemnification_clause": "Employee shall indemnify Employer against all claims, losses, and expenses without limitation arising from Employee's actions.",
        "dispute_clause": "All disputes shall be resolved through binding arbitration in accordance with AAA rules.",
        "attorneys_fees_clause": "Employer shall be entitled to recover all attorneys' fees and costs in any action to enforce this Agreement.",
        "governing_law": "This Agreement is governed by the laws of the State of California.",
        "date": "January 1, 2024",
        "expected_rule_ids_present": ["H_IP_01", "M_CONF_01", "H_INDEM_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "emp_02",
        "position": "Product Manager",
        "compensation_clause": "Employee shall receive a base salary of $120,000 plus performance bonuses as determined by Employer.",
        "ip_clause": "Employee retains ownership of pre-existing intellectual property. Employer receives a license to use work product created during employment.",
        "confidentiality_clause": "Confidentiality obligations continue for 2 years after termination of employment.",
        "noncompete_clause": "No non-compete restrictions apply.",
        "termination_clause": "This Agreement may be terminated by either party with 30 days written notice.",
        "indemnification_clause": "Employee shall indemnify Employer to the extent required by applicable law for claims arising from Employee's gross negligence.",
        "dispute_clause": "Disputes shall be resolved through mediation, then litigation if mediation fails.",
        "attorneys_fees_clause": "Each party shall bear its own attorneys' fees and costs.",
        "governing_law": "This Agreement is subject to New York state law.",
        "date": "February 15, 2024",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_IP_01", "H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "emp_03",
        "position": "Chief Technology Officer",
        "compensation_clause": "Employee shall receive compensation as set forth in the attached compensation schedule, including equity grants.",
        "ip_clause": "All intellectual property developed by Employee in the course of employment, including inventions and trade secrets, shall be owned by Employer. Employee assigns all such rights to Employer.",
        "confidentiality_clause": "Employee must maintain confidentiality of all trade secrets and proprietary information in perpetuity.",
        "noncompete_clause": "Employee agrees not to work for competitors or solicit Employer's customers for 18 months after termination.",
        "termination_clause": "Employer may terminate for cause immediately. Employee may terminate with 60 days notice.",
        "indemnification_clause": "Employee agrees to indemnify Employer for all legal costs and damages resulting from Employee's breach of this Agreement, up to a maximum of $500,000.",
        "dispute_clause": "Any disputes shall be resolved exclusively in the courts of Delaware.",
        "attorneys_fees_clause": "The prevailing party in any legal action shall recover reasonable attorneys' fees from the other party.",
        "governing_law": "Delaware law governs this Agreement.",
        "date": "March 1, 2024",
        "expected_rule_ids_present": ["H_IP_01", "M_CONF_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01"],
    },
    {
        "id": "emp_04",
        "position": "Data Scientist",
        "compensation_clause": "Employee's compensation includes a base salary of $140,000 and eligibility for annual bonuses.",
        "ip_clause": "Work product created during employment is jointly owned by Employer and Employee, with Employer receiving an exclusive license for business use.",
        "confidentiality_clause": "Confidentiality obligations survive termination and continue for 3 years.",
        "noncompete_clause": "Employee may not compete within the same industry for 1 year after termination, within Employer's primary market area.",
        "termination_clause": "This Agreement may be terminated by mutual agreement or by either party with 90 days written notice.",
        "indemnification_clause": "Mutual indemnification: each party indemnifies the other for its own negligence, capped at annual compensation.",
        "dispute_clause": "Disputes shall be resolved through good faith negotiation between the parties.",
        "attorneys_fees_clause": "Each party is responsible for its own legal expenses.",
        "governing_law": "This Agreement is governed by Massachusetts state law.",
        "date": "April 10, 2024",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_IP_01", "H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "emp_05",
        "position": "Vice President of Engineering",
        "compensation_clause": "Employee shall receive an annual salary of $200,000, payable monthly, plus stock options as detailed in the equity agreement.",
        "ip_clause": "All work product, inventions, and intellectual property created by Employee during the term of employment shall become the sole and exclusive property of Employer. Employee hereby irrevocably assigns all such rights to Employer.",
        "confidentiality_clause": "Employee agrees to maintain strict confidentiality of all proprietary information, trade secrets, and business strategies indefinitely, without any time limitation.",
        "noncompete_clause": "Employee shall not engage in any competitive business activity or solicit Employer's employees or customers for a period of 3 years following termination.",
        "termination_clause": "Employer may terminate this Agreement at any time, with or without cause. Employee requires 4 weeks notice to terminate.",
        "indemnification_clause": "Employee shall defend, indemnify, and hold harmless Employer from any and all claims, damages, losses, and expenses, without limitation, arising from Employee's performance of duties or breach of this Agreement.",
        "dispute_clause": "All disputes must be resolved through mandatory binding arbitration under the rules of the American Arbitration Association.",
        "attorneys_fees_clause": "In any action to enforce this Agreement, Employer shall be entitled to recover all attorneys' fees, court costs, and expenses from Employee.",
        "governing_law": "This Agreement is governed by California law, and the parties consent to exclusive jurisdiction in California courts.",
        "date": "May 1, 2024",
        "expected_rule_ids_present": ["H_IP_01", "M_CONF_01", "H_INDEM_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": [],
    },
    # Additional test cases for expanded dataset (6-20)
    {
        "id": "emp_06",
        "position": "Software Engineer",
        "compensation_clause": "Employee shall receive a base salary of $130,000 per year, payable bi-weekly.",
        "ip_clause": "All inventions and work product created by Employee during employment shall be assigned to Employer. Employee hereby assigns all rights, title, and interest.",
        "confidentiality_clause": "Employee must maintain confidentiality of all proprietary information for a period of 5 years after termination.",
        "noncompete_clause": "Employee agrees not to work for competitors for 12 months after termination within a 25-mile radius.",
        "termination_clause": "Either party may terminate this Agreement with 2 weeks written notice.",
        "indemnification_clause": "Employee shall indemnify Employer for all claims arising from Employee's breach of this Agreement, up to $100,000.",
        "dispute_clause": "Disputes shall be resolved through binding arbitration.",
        "attorneys_fees_clause": "Employer shall be entitled to recover reasonable attorneys' fees in any enforcement action.",
        "governing_law": "This Agreement is governed by Washington state law.",
        "date": "June 1, 2024",
        "expected_rule_ids_present": ["H_IP_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01"],
    },
    {
        "id": "emp_07",
        "position": "Marketing Director",
        "compensation_clause": "Employee's compensation includes a base salary of $110,000 plus performance-based bonuses.",
        "ip_clause": "Employee retains ownership of pre-existing intellectual property. Employer receives a license to use work product.",
        "confidentiality_clause": "Confidentiality obligations continue for 18 months after termination.",
        "noncompete_clause": "No non-compete restrictions apply to this position.",
        "termination_clause": "This Agreement may be terminated by either party with 30 days written notice.",
        "indemnification_clause": "Employee shall indemnify Employer to the extent required by law for claims arising from Employee's gross negligence.",
        "dispute_clause": "Disputes shall be resolved through mediation, then litigation if needed.",
        "attorneys_fees_clause": "Each party shall bear its own attorneys' fees.",
        "governing_law": "This Agreement is subject to Pennsylvania state law.",
        "date": "July 15, 2024",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_IP_01", "H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "emp_08",
        "position": "Senior Data Analyst",
        "compensation_clause": "Employee shall receive an annual salary of $145,000, payable monthly.",
        "ip_clause": "All intellectual property developed by Employee in the course of employment shall be owned by Employer. Employee assigns all such rights to Employer.",
        "confidentiality_clause": "Employee agrees to maintain confidentiality of all trade secrets and proprietary information in perpetuity.",
        "noncompete_clause": "Employee may not compete with Employer for 2 years after termination within the same geographic market.",
        "termination_clause": "Employer may terminate for cause immediately. Employee may terminate with 30 days notice.",
        "indemnification_clause": "Employee agrees to indemnify Employer for all legal costs resulting from Employee's breach, capped at $300,000.",
        "dispute_clause": "Any disputes shall be resolved exclusively in the courts of New Jersey.",
        "attorneys_fees_clause": "The prevailing party in any legal action shall recover reasonable attorneys' fees.",
        "governing_law": "New Jersey law governs this Agreement.",
        "date": "August 1, 2024",
        "expected_rule_ids_present": ["H_IP_01", "M_CONF_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01"],
    },
    {
        "id": "emp_09",
        "position": "Operations Manager",
        "compensation_clause": "Employee's compensation includes a base salary of $125,000 and eligibility for equity grants.",
        "ip_clause": "Work product created during employment is owned by Employer, with Employee receiving a royalty-free license for personal portfolio use.",
        "confidentiality_clause": "Confidentiality obligations survive termination and continue for 4 years.",
        "noncompete_clause": "Employee may not work for direct competitors for 18 months after termination.",
        "termination_clause": "This Agreement may be terminated by mutual agreement or by either party with 60 days notice.",
        "indemnification_clause": "Mutual indemnification: each party indemnifies the other for its own negligence, capped at annual salary.",
        "dispute_clause": "Disputes shall be resolved through good faith negotiation.",
        "attorneys_fees_clause": "Each party is responsible for its own legal expenses.",
        "governing_law": "This Agreement is governed by Connecticut state law.",
        "date": "September 1, 2024",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_IP_01", "H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "emp_10",
        "position": "Director of Sales",
        "compensation_clause": "Employee shall receive a base salary of $150,000 plus commission as detailed in the compensation plan.",
        "ip_clause": "All work product, inventions, and intellectual property created by Employee during employment shall become the exclusive property of Employer. Employee hereby assigns all such rights to Employer.",
        "confidentiality_clause": "Employee must maintain strict confidentiality of all proprietary information, customer lists, and business strategies indefinitely.",
        "noncompete_clause": "Employee shall not engage in competitive business activities or solicit Employer's customers for 2 years following termination.",
        "termination_clause": "Employer may terminate at will. Employee requires 3 weeks notice to terminate.",
        "indemnification_clause": "Employee shall defend, indemnify, and hold harmless Employer from all claims, without limitation, arising from Employee's actions or breach of this Agreement.",
        "dispute_clause": "All disputes must be resolved through mandatory binding arbitration.",
        "attorneys_fees_clause": "In any action to enforce this Agreement, Employer shall recover all attorneys' fees and costs from Employee.",
        "governing_law": "This Agreement is governed by California law, and parties consent to exclusive jurisdiction in California courts.",
        "date": "October 1, 2024",
        "expected_rule_ids_present": ["H_IP_01", "M_CONF_01", "H_INDEM_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "emp_11",
        "position": "UX Designer",
        "compensation_clause": "Employee shall receive an annual salary of $120,000, payable bi-weekly.",
        "ip_clause": "Provider retains ownership of pre-existing designs. Employer receives a non-exclusive license to use work product created during employment.",
        "confidentiality_clause": "Confidentiality obligations continue for 2 years after termination of employment.",
        "noncompete_clause": "No non-compete restrictions apply.",
        "termination_clause": "Either party may terminate this Agreement with 2 weeks written notice.",
        "indemnification_clause": "Employee shall indemnify Employer to the extent required by applicable law for claims arising from Employee's willful misconduct.",
        "dispute_clause": "Disputes shall be resolved through mediation, then arbitration if mediation fails.",
        "attorneys_fees_clause": "Each party shall pay its own attorneys' fees unless the other party prevails.",
        "governing_law": "This Agreement is subject to Oregon state law.",
        "date": "November 1, 2024",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_IP_01", "H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "emp_12",
        "position": "Financial Analyst",
        "compensation_clause": "Employee's compensation includes a base salary of $135,000 and eligibility for annual performance bonuses.",
        "ip_clause": "All intellectual property developed by Employee in the course of employment shall be owned by Employer. Employee assigns all such rights to Employer.",
        "confidentiality_clause": "Employee agrees to maintain confidentiality of all financial information and trade secrets in perpetuity.",
        "noncompete_clause": "Employee may not work for competitors or solicit Employer's clients for 15 months after termination.",
        "termination_clause": "This Agreement may be terminated by either party with 45 days written notice.",
        "indemnification_clause": "Employee agrees to indemnify Employer for claims arising from Employee's breach of this Agreement, up to a maximum of $200,000.",
        "dispute_clause": "Any disputes shall be resolved in the courts of the State of Virginia.",
        "attorneys_fees_clause": "The prevailing party in any dispute shall be entitled to recover reasonable attorneys' fees.",
        "governing_law": "Virginia law governs this Agreement.",
        "date": "December 1, 2024",
        "expected_rule_ids_present": ["H_IP_01", "M_CONF_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01"],
    },
    {
        "id": "emp_13",
        "position": "Business Development Manager",
        "compensation_clause": "Employee shall receive a base salary of $140,000 plus commission based on sales performance.",
        "ip_clause": "Provider grants Employer a perpetual, exclusive license to use all work product created during employment for Employer's business purposes.",
        "confidentiality_clause": "Confidentiality obligations survive termination and continue for 3 years.",
        "noncompete_clause": "Employee may not compete within the same industry for 1 year after termination, within Employer's service area.",
        "termination_clause": "Either party may terminate for convenience with 30 days written notice.",
        "indemnification_clause": "Mutual indemnification: each party indemnifies the other for its own negligence, capped at annual compensation.",
        "dispute_clause": "Disputes shall be resolved through good faith negotiation.",
        "attorneys_fees_clause": "Each party bears its own legal costs.",
        "governing_law": "This Agreement is governed by Georgia state law.",
        "date": "January 1, 2025",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01", "H_ATTFEE_01"],
    },
    {
        "id": "emp_14",
        "position": "Research Scientist",
        "compensation_clause": "Employee shall receive an annual salary of $160,000, payable monthly, plus research grants as available.",
        "ip_clause": "All inventions, discoveries, and intellectual property created by Employee during employment shall be the exclusive property of Employer. Employee hereby irrevocably assigns all such rights to Employer.",
        "confidentiality_clause": "Employee must maintain strict confidentiality of all research data, proprietary methods, and trade secrets indefinitely, without any time limitation.",
        "noncompete_clause": "Employee shall not engage in competitive research or solicit Employer's research partners for 3 years following termination.",
        "termination_clause": "Employer may terminate this Agreement at any time, with or without cause. Employee requires 60 days notice to terminate.",
        "indemnification_clause": "Employee shall defend, indemnify, and hold harmless Employer from any and all claims, damages, losses, and expenses, without limitation, arising from Employee's research activities or breach of this Agreement.",
        "dispute_clause": "All disputes must be resolved through binding arbitration under the rules of the American Arbitration Association.",
        "attorneys_fees_clause": "Employer shall be entitled to recover all attorneys' fees, court costs, and expenses from Employee in any enforcement action.",
        "governing_law": "This Agreement is governed by California law, and the parties consent to exclusive jurisdiction in California courts.",
        "date": "February 1, 2025",
        "expected_rule_ids_present": ["H_IP_01", "M_CONF_01", "H_INDEM_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "emp_15",
        "position": "HR Manager",
        "compensation_clause": "Employee's compensation includes a base salary of $115,000 and eligibility for annual bonuses.",
        "ip_clause": "Employee retains ownership of pre-existing HR methodologies. Employer receives a license to use work product created during employment.",
        "confidentiality_clause": "Confidentiality obligations continue for 2 years after termination of this Agreement.",
        "noncompete_clause": "No non-compete restrictions apply to this position.",
        "termination_clause": "This Agreement may be terminated by either party with 30 days written notice.",
        "indemnification_clause": "Each party shall indemnify the other for claims arising from its own breach, capped at $150,000 per claim.",
        "dispute_clause": "Disputes shall be resolved through direct negotiation between the parties.",
        "attorneys_fees_clause": "Each party is responsible for its own attorneys' fees and costs.",
        "governing_law": "This Agreement is subject to North Carolina state law.",
        "date": "March 1, 2025",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_IP_01", "H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "emp_16",
        "position": "Quality Assurance Engineer",
        "compensation_clause": "Employee shall receive a base salary of $125,000 per year, payable bi-weekly.",
        "ip_clause": "All work product and deliverables created by Employee during employment shall be owned by Employer. Employee assigns all rights, title, and interest to Employer.",
        "confidentiality_clause": "Employee agrees to maintain confidentiality of all proprietary testing methods and trade secrets for a period of 4 years after termination.",
        "noncompete_clause": "Employee may not work for competitors for 18 months after termination within a 50-mile radius.",
        "termination_clause": "Either party may terminate with 2 weeks written notice.",
        "indemnification_clause": "Employee shall indemnify Employer for all claims arising from Employee's breach of this Agreement, up to $250,000.",
        "dispute_clause": "Disputes shall be resolved through binding arbitration.",
        "attorneys_fees_clause": "Employer shall be entitled to recover reasonable attorneys' fees in any enforcement action.",
        "governing_law": "This Agreement is governed by Minnesota state law.",
        "date": "April 1, 2025",
        "expected_rule_ids_present": ["H_IP_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01"],
    },
    {
        "id": "emp_17",
        "position": "Content Strategist",
        "compensation_clause": "Employee shall receive an annual salary of $105,000 plus performance bonuses.",
        "ip_clause": "Provider grants Employer a worldwide, perpetual license to use all content and work product created during employment.",
        "confidentiality_clause": "Confidentiality obligations survive termination and continue for 2 years.",
        "noncompete_clause": "Employee may not compete within the same market for 12 months after termination.",
        "termination_clause": "This Agreement may be terminated by either party with 30 days written notice.",
        "indemnification_clause": "Mutual indemnification: each party indemnifies the other for its own negligence, capped at annual salary.",
        "dispute_clause": "Disputes shall be resolved through mediation, then litigation if mediation fails.",
        "attorneys_fees_clause": "The prevailing party in any dispute shall recover reasonable attorneys' fees.",
        "governing_law": "This Agreement is governed by Colorado state law.",
        "date": "May 1, 2025",
        "expected_rule_ids_present": ["H_ATTFEE_01"],
        "expected_rule_ids_absent": ["H_INDEM_01", "H_IP_01"],
    },
    {
        "id": "emp_18",
        "position": "DevOps Engineer",
        "compensation_clause": "Employee's compensation includes a base salary of $155,000 and stock option grants.",
        "ip_clause": "All intellectual property, code, and technical work product created by Employee during employment shall become the sole and exclusive property of Employer. Employee hereby assigns all such rights to Employer.",
        "confidentiality_clause": "Employee must maintain strict confidentiality of all proprietary systems, architectures, and trade secrets in perpetuity, without any time limitation.",
        "noncompete_clause": "Employee shall not engage in competitive activities or solicit Employer's technical staff for 2 years following termination.",
        "termination_clause": "Employer may terminate at will. Employee requires 4 weeks notice to terminate.",
        "indemnification_clause": "Employee shall defend, indemnify, and hold harmless Employer from all claims, without limitation, arising from Employee's technical work or breach of this Agreement.",
        "dispute_clause": "All disputes must be resolved through mandatory binding arbitration under AAA rules.",
        "attorneys_fees_clause": "In any action to enforce this Agreement, Employer shall recover all attorneys' fees, costs, and expenses from Employee.",
        "governing_law": "This Agreement is governed by California law, and parties consent to exclusive jurisdiction in California courts.",
        "date": "June 1, 2025",
        "expected_rule_ids_present": ["H_IP_01", "M_CONF_01", "H_INDEM_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": [],
    },
    {
        "id": "emp_19",
        "position": "Customer Success Manager",
        "compensation_clause": "Employee shall receive a base salary of $118,000 plus commission based on customer retention metrics.",
        "ip_clause": "Work product created during employment is jointly owned, with Employer receiving an exclusive license for business use.",
        "confidentiality_clause": "Confidentiality obligations continue for 2.5 years after termination of employment.",
        "noncompete_clause": "Employee may not work for direct competitors for 1 year after termination within the same geographic region.",
        "termination_clause": "Either party may terminate for convenience with 45 days written notice.",
        "indemnification_clause": "Each party indemnifies the other for its own breach, capped at the annual contract value.",
        "dispute_clause": "Disputes shall be resolved through good faith negotiation.",
        "attorneys_fees_clause": "Each party bears its own legal expenses.",
        "governing_law": "This Agreement is subject to Wisconsin state law.",
        "date": "July 1, 2025",
        "expected_rule_ids_present": [],
        "expected_rule_ids_absent": ["H_IP_01", "H_INDEM_01", "H_ATTFEE_01"],
    },
    {
        "id": "emp_20",
        "position": "Security Engineer",
        "compensation_clause": "Employee shall receive an annual salary of $170,000, payable monthly, plus security clearance bonuses.",
        "ip_clause": "All security methodologies, tools, and intellectual property developed by Employee during employment shall be owned by Employer. Employee assigns all such rights to Employer.",
        "confidentiality_clause": "Employee agrees to maintain strict confidentiality of all security protocols, vulnerabilities, and proprietary systems indefinitely, without expiration.",
        "noncompete_clause": "Employee shall not work for competitors or disclose security information for 3 years following termination.",
        "termination_clause": "Employer may terminate immediately upon security breach. Employee requires 60 days notice to terminate.",
        "indemnification_clause": "Employee shall indemnify Employer for all claims, damages, and expenses, without limitation, arising from Employee's security work or breach of confidentiality.",
        "dispute_clause": "All disputes must be resolved through binding arbitration under the rules of the International Chamber of Commerce.",
        "attorneys_fees_clause": "Employer shall be entitled to recover all attorneys' fees, court costs, and expenses from Employee in any enforcement or breach action.",
        "governing_law": "This Agreement is governed by California law, and parties submit to exclusive jurisdiction in California courts.",
        "date": "August 1, 2025",
        "expected_rule_ids_present": ["H_IP_01", "M_CONF_01", "H_INDEM_01", "H_ATTFEE_01"],
        "expected_rule_ids_absent": [],
    },
]


def build_synthetic_employment():
    """Generate synthetic Employment Agreement documents with ground-truth labels."""
    print("Building synthetic Employment Agreement dataset...")
    
    emp_dir = DATA_BASE_DIR / "employment"
    emp_dir.mkdir(parents=True, exist_ok=True)
    
    for case in TEST_CASES:
        doc_id = case["id"]
        
        # Generate document text
        doc_text = BASE_EMPLOYMENT.format(
            position=case["position"],
            compensation_clause=case["compensation_clause"],
            ip_clause=case["ip_clause"],
            confidentiality_clause=case["confidentiality_clause"],
            noncompete_clause=case["noncompete_clause"],
            termination_clause=case["termination_clause"],
            indemnification_clause=case["indemnification_clause"],
            dispute_clause=case["dispute_clause"],
            attorneys_fees_clause=case["attorneys_fees_clause"],
            governing_law=case["governing_law"],
            date=case["date"],
        )
        
        # Save text file
        save_text(doc_text, emp_dir / f"{doc_id}.txt")
        
        # Create metadata
        metadata = {
            "id": doc_id,
            "type": "synthetic",
            "contract_type": "Employment",
            "generated_date": datetime.now().isoformat(),
            "source": "synthetic_generator",
        }
        save_json(metadata, emp_dir / f"{doc_id}.meta.json")
        
        # Create ground-truth labels
        truth = {
            "expected_rule_ids_present": case["expected_rule_ids_present"],
            "expected_rule_ids_absent": case["expected_rule_ids_absent"],
            "contract_type": "Employment",
        }
        save_json(truth, emp_dir / f"{doc_id}.truth.json")
        
        print(f"  Generated {doc_id}")
    
    print(f"\nGenerated {len(TEST_CASES)} synthetic Employment Agreement documents in {emp_dir}")


if __name__ == "__main__":
    build_synthetic_employment()
