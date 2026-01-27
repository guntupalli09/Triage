"""
Build public NDA dataset from templates.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add experiments parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from experiments.config import DATA_DIR, NUM_PUBLIC_NDAS
from experiments.utils_io import save_text, save_json


# Well-known NDA template text (recreated from common templates)
# Marked as public_template_recreated since we can't download in this environment
PUBLIC_NDA_TEMPLATES = [
    """NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into on {date} between {party1} ("Disclosing Party") and {party2} ("Receiving Party").

1. Definition of Confidential Information
Confidential Information means all non-public, proprietary or confidential information disclosed by the Disclosing Party to the Receiving Party, whether orally, in writing, or in any other form.

2. Obligations
The Receiving Party agrees to hold and maintain the Confidential Information in strict confidence and to take all reasonable precautions to protect such Confidential Information.

3. Term
This Agreement shall remain in effect indefinitely and shall survive termination of any business relationship between the parties.

4. Return of Information
Upon termination, the Receiving Party shall return all Confidential Information to the Disclosing Party.

5. Governing Law
This Agreement shall be governed by the laws of the State of California.

IN WITNESS WHEREOF, the parties have executed this Agreement.""",
    
    """MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement is made between {party1} and {party2}.

CONFIDENTIAL INFORMATION
Each party may disclose confidential information to the other party. Confidential Information includes, without limitation, all technical, business, financial, and proprietary information.

OBLIGATIONS
Each party agrees to:
(a) Hold the other party's Confidential Information in strict confidence;
(b) Not disclose such information to any third party without prior written consent;
(c) Use such information solely for the purpose of evaluating potential business opportunities.

TERM
The obligations under this Agreement shall continue in perpetuity and shall survive any termination of discussions between the parties.

INDEMNIFICATION
Each party shall indemnify and hold harmless the other party from and against all claims, losses, damages, and expenses, without limit, arising out of any breach of this Agreement.

LIMITATION OF LIABILITY
Notwithstanding any other provision, neither party's liability shall be limited under this Agreement.

INTELLECTUAL PROPERTY
All work product and deliverables created hereunder shall be owned exclusively by {party1}. The receiving party hereby assigns all right, title, and interest in such work product.

ATTORNEYS' FEES
The prevailing party in any dispute shall be entitled to recover all attorneys' fees and costs from the non-prevailing party.

This Agreement is governed by the laws of New York.""",
    
    """STANDARD NDA TEMPLATE

BETWEEN {party1} AND {party2}

1. CONFIDENTIAL INFORMATION
"Confidential Information" means all information disclosed by one party to the other, including but not limited to technical data, business plans, customer lists, and financial information.

2. NON-DISCLOSURE
The Receiving Party shall not disclose any Confidential Information to any third party without the prior written consent of the Disclosing Party.

3. DURATION
This Agreement shall remain in effect for a period of five (5) years from the date of execution.

4. REMEDIES
The parties acknowledge that monetary damages may be inadequate for breach of this Agreement. Therefore, the Disclosing Party shall be entitled to seek injunctive relief without posting bond or other security.

5. ASSIGNMENT
Neither party may assign this Agreement without the prior written consent of the other party, except in connection with a change of control transaction.

Governing Law: Delaware""",
    
    """CONFIDENTIALITY AGREEMENT

This Confidentiality Agreement is entered into between {party1} and {party2}.

CONFIDENTIAL INFORMATION
Confidential Information includes all proprietary information, trade secrets, business plans, financial data, and technical information disclosed by either party.

OBLIGATIONS
Each party agrees to maintain the confidentiality of the other party's Confidential Information and to use such information solely for the purpose of evaluating potential business opportunities.

TERM
This Agreement shall remain in effect for three (3) years from the date of execution, after which the obligations shall terminate.

RETURN OF MATERIALS
Upon termination, each party shall return or destroy all Confidential Information received from the other party.

Governing Law: Texas""",

    """NON-DISCLOSURE AND CONFIDENTIALITY AGREEMENT

BETWEEN {party1} ("Discloser") AND {party2} ("Recipient")

1. DEFINITION
Confidential Information means all non-public information, whether oral, written, or electronic, disclosed by Discloser to Recipient.

2. CONFIDENTIALITY OBLIGATIONS
Recipient agrees to:
- Hold Confidential Information in strict confidence
- Not disclose to any third party without prior written consent
- Use only for the purpose of evaluating business opportunities
- Take reasonable precautions to protect confidentiality

3. TERM
This Agreement shall remain in effect indefinitely and shall survive termination of any business relationship.

4. EXCEPTIONS
Confidential Information does not include information that:
- Is publicly available
- Was already known to Recipient
- Is independently developed by Recipient

5. GOVERNING LAW
This Agreement is governed by California law.""",

    """MUTUAL CONFIDENTIALITY AGREEMENT

This Mutual Confidentiality Agreement is made on {date} between {party1} and {party2}.

PURPOSE
The parties wish to explore potential business opportunities and may disclose confidential information to each other.

CONFIDENTIAL INFORMATION
Confidential Information means all proprietary information disclosed by one party to the other, including technical data, business strategies, customer information, and financial information.

OBLIGATIONS
Each party agrees to:
(a) Maintain strict confidentiality
(b) Not use the information for any purpose other than evaluating business opportunities
(c) Return or destroy all Confidential Information upon request

DURATION
Confidentiality obligations shall continue for two (2) years after termination of discussions.

Governing Law: New York""",

    """STANDARD CONFIDENTIALITY AGREEMENT

PARTIES: {party1} and {party2}

1. CONFIDENTIAL INFORMATION
All non-public information disclosed by either party, including but not limited to technical specifications, business plans, financial data, and customer lists.

2. NON-DISCLOSURE
Neither party shall disclose the other's Confidential Information to any third party without prior written authorization.

3. PERMITTED USE
Confidential Information may be used solely for the purpose of evaluating potential business relationships between the parties.

4. TERM
This Agreement shall remain in effect for four (4) years from the date of execution.

5. REMEDIES
Breach of this Agreement may cause irreparable harm. The non-breaching party shall be entitled to seek injunctive relief.

Governing Law: Delaware""",

    """CONFIDENTIALITY AND NON-DISCLOSURE AGREEMENT

This Agreement is entered into between {party1} and {party2} on {date}.

DEFINITIONS
"Confidential Information" means all proprietary or confidential information disclosed by one party to the other, whether in oral, written, or electronic form.

OBLIGATIONS
The Receiving Party agrees to:
- Maintain the confidentiality of all Confidential Information
- Not disclose to any third party without written consent
- Use Confidential Information only for the stated business purpose
- Implement reasonable security measures

TERM AND SURVIVAL
This Agreement shall remain in effect for five (5) years. Confidentiality obligations shall survive termination.

RETURN OF INFORMATION
Upon termination or upon request, the Receiving Party shall return all Confidential Information and destroy all copies.

Governing Law: Massachusetts""",

    """NON-DISCLOSURE AGREEMENT (NDA)

BETWEEN {party1} ("Disclosing Party") AND {party2} ("Receiving Party")

ARTICLE 1 - CONFIDENTIAL INFORMATION
Confidential Information includes all non-public, proprietary information disclosed by Disclosing Party to Receiving Party, including technical data, business information, financial information, and trade secrets.

ARTICLE 2 - CONFIDENTIALITY OBLIGATIONS
Receiving Party shall:
(a) Hold all Confidential Information in strict confidence
(b) Not disclose to any third party without prior written consent
(c) Use Confidential Information solely for evaluating business opportunities
(d) Take reasonable precautions to protect confidentiality

ARTICLE 3 - DURATION
This Agreement shall remain in effect indefinitely and shall survive termination of any business relationship.

ARTICLE 4 - GOVERNING LAW
This Agreement is governed by the laws of the State of California.

ARTICLE 5 - ENTIRE AGREEMENT
This Agreement constitutes the entire agreement between the parties regarding confidentiality.""",

    """MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement is entered into on {date} between {party1} and {party2}.

RECITALS
The parties wish to explore potential business opportunities and may exchange confidential information.

1. DEFINITION OF CONFIDENTIAL INFORMATION
Confidential Information means all proprietary information, whether oral, written, or electronic, disclosed by one party to the other.

2. MUTUAL OBLIGATIONS
Each party agrees to maintain the confidentiality of the other party's Confidential Information and to use such information only for evaluating business opportunities.

3. TERM
The confidentiality obligations under this Agreement shall continue for three (3) years from the date of execution.

4. EXCEPTIONS
Confidential Information does not include information that is publicly available or independently developed.

5. RETURN OF MATERIALS
Upon termination, each party shall return all Confidential Information received from the other party.

Governing Law: Illinois""",

    """CONFIDENTIALITY AGREEMENT

PARTIES: {party1} and {party2}
DATE: {date}

WHEREAS, the parties wish to explore potential business opportunities;
WHEREAS, such exploration may require disclosure of confidential information;

NOW, THEREFORE, the parties agree as follows:

1. CONFIDENTIAL INFORMATION
All non-public information disclosed by either party, including technical data, business strategies, financial information, and customer information.

2. CONFIDENTIALITY OBLIGATIONS
Each party agrees to:
- Maintain strict confidentiality
- Not disclose to third parties without consent
- Use information solely for stated business purpose
- Take reasonable security measures

3. DURATION
This Agreement shall remain in effect for two (2) years from the date of execution.

4. GOVERNING LAW
This Agreement is governed by the laws of the State of Washington.

IN WITNESS WHEREOF, the parties have executed this Agreement.""",

    """STANDARD NDA TEMPLATE

This Non-Disclosure Agreement is made between {party1} and {party2}.

CONFIDENTIAL INFORMATION
Confidential Information means all proprietary or confidential information disclosed by one party to the other, whether in oral, written, or electronic form, including but not limited to technical data, business plans, financial information, and customer lists.

OBLIGATIONS
The Receiving Party agrees to:
(a) Hold Confidential Information in strict confidence
(b) Not disclose to any third party without prior written authorization
(c) Use Confidential Information only for evaluating business opportunities
(d) Return or destroy Confidential Information upon request

TERM
This Agreement shall remain in effect for four (4) years from the date of execution.

REMEDIES
The parties acknowledge that breach of this Agreement may cause irreparable harm, and the non-breaching party shall be entitled to seek injunctive relief.

Governing Law: Colorado""",

    """MUTUAL CONFIDENTIALITY AGREEMENT

BETWEEN {party1} AND {party2}

PREAMBLE
The parties wish to explore potential business opportunities and may exchange confidential information for this purpose.

1. DEFINITION
"Confidential Information" means all non-public, proprietary information disclosed by either party to the other.

2. MUTUAL OBLIGATIONS
Each party agrees to maintain the confidentiality of the other party's Confidential Information and to use such information solely for the stated business purpose.

3. TERM AND SURVIVAL
This Agreement shall remain in effect indefinitely. Confidentiality obligations shall survive termination of any business relationship.

4. RETURN OF INFORMATION
Upon termination or upon request, each party shall return all Confidential Information received from the other party.

5. GOVERNING LAW
This Agreement is governed by the laws of the State of Florida.

EXECUTED on {date}.""",
]


def create_public_nda(idx: int, template: str) -> None:
    """Create a public NDA file with metadata."""
    doc_id = f"public_{idx:02d}"
    
    # Fill template with placeholders
    filled = template.format(
        date="2024-01-01",
        party1="Company A",
        party2="Company B"
    )
    
    # Save text
    text_path = DATA_DIR / f"{doc_id}.txt"
    save_text(filled, text_path)
    
    # Save metadata
    meta = {
        "id": doc_id,
        "type": "public",
        "source_url": "template_recreated",
        "public_template_recreated": True,
        "download_date": datetime.now().strftime("%Y-%m-%d"),
        "note": "Template recreated from common NDA boilerplate language"
    }
    meta_path = DATA_DIR / f"{doc_id}.meta.json"
    save_json(meta, meta_path)


def build_public_ndas():
    """Build all public NDA files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Use templates cyclically
    for i in range(1, NUM_PUBLIC_NDAS + 1):
        template_idx = (i - 1) % len(PUBLIC_NDA_TEMPLATES)
        create_public_nda(i, PUBLIC_NDA_TEMPLATES[template_idx])
    
    print(f"Created {NUM_PUBLIC_NDAS} public NDA files in {DATA_DIR}")


if __name__ == "__main__":
    build_public_ndas()
