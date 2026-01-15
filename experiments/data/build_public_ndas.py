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
