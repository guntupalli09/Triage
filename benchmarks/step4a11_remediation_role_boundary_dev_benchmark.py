"""Step 4A.11 Remediation — Phase 2 DEVELOPMENT benchmark for the role-name
boundary defect (see artifacts/step4a11_remediation/ROOT_CAUSE.md).

DEVELOPMENT evidence: may be iterated against while fixing production, per
the remediation's own process rule. NOT the fresh remediation-validation
corpus (that comes later, in Phase 7, and must never reuse these cases).

Each case declares expected_actor/expected_beneficiary as either:
- a literal string (the capture must equal exactly this — a positive
  control, including legitimate long/hyphenated/punctuated names that must
  NOT be truncated by an overzealous fix), or
- None (the case must NOT cleanly establish a wrong-bounded role at all —
  fail-closed is required; NOT_ESTABLISHED or a correctly-shorter/-bounded
  capture are both acceptable, but a capture that swallows heading text,
  a repeated clause fragment, or a connector-word run is not).
"""
from typing import Optional, Dict, Any, List

CASES: List[Dict[str, Any]] = []


def case(cid: str, category: str, text: str, expected_actor: Optional[str],
         expected_beneficiary: Optional[str], notes: str = "") -> Dict[str, Any]:
    return {"id": cid, "category": category, "text": text,
            "expected_actor": expected_actor, "expected_beneficiary": expected_beneficiary,
            "notes": notes}


CASES += [
    # A. ALL-CAPS headings followed by operative clauses
    case("rb-A-01", "A", "13. INDEMNIFICATION OBLIGATIONS OF Harrowdale Systems Corp -- "
         "Harrowdale Systems Corp SHALL INDEMNIFY AND HOLD HARMLESS Fenwick Retail Group "
         "FROM ANY THIRD-PARTY CLAIM ARISING OUT OF A BREACH OF THE WARRANTIES IN SECTION 6.",
         "Harrowdale Systems Corp", "Fenwick Retail Group",
         "The exact discovered defect shape -- heading label + ALL-CAPS operative clause."),
    case("rb-A-02", "A", "14. LIABILITY FOR DEFECTS -- Coalbrook Manufacturing LLC SHALL "
         "INDEMNIFY Ashgrove Retail Partners FOR ANY LOSS ARISING FROM A PRODUCT DEFECT.",
         "Coalbrook Manufacturing LLC", "Ashgrove Retail Partners", ""),
    case("rb-A-03", "A", "RISK TRANSFER -- Nettlefield Logistics Inc SHALL INDEMNIFY AND "
         "DEFEND Brackenmoor Holdings AGAINST ANY CLAIM RELATING TO A SHIPPING DELAY.",
         "Nettlefield Logistics Inc", "Brackenmoor Holdings", ""),
    case("rb-A-04", "A", "9. INDEMNITY OBLIGATIONS -- Wrenhollow Data Corp SHALL INDEMNIFY "
         "Castlemoor Insurance Group WITH RESPECT TO ANY CLAIM UNDER THIS SECTION.",
         "Wrenhollow Data Corp", "Castlemoor Insurance Group", ""),
    case("rb-A-05", "A", "INDEMNIFICATION -- Thornbury Analytics LLC SHALL INDEMNIFY "
         "Marlstone Health Partners SUBJECT TO THE LIMITATIONS SET FORTH IN SECTION 12.",
         "Thornbury Analytics LLC", "Marlstone Health Partners", ""),
    # B. Title Case headings followed by operative clauses
    case("rb-B-01", "B", "13. Indemnification Obligations -- Kettlewood Consulting Group "
         "shall indemnify and hold harmless Oxendown Municipal Trust from any claim.",
         "Kettlewood Consulting Group", "Oxendown Municipal Trust", ""),
    case("rb-B-02", "B", "Risk Allocation Terms -- Silvermere Engineering Corp shall "
         "indemnify Brambleford Insurance Alliance for claims arising from a defect.",
         "Silvermere Engineering Corp", "Brambleford Insurance Alliance", ""),
    # C. Inline headings (no line break, colon or dash before the clause)
    case("rb-C-01", "C", "Indemnification: Foxdale Manufacturing Co shall indemnify "
         "Ravenscroft Retail Partners for any claim arising from a labeling error.",
         "Foxdale Manufacturing Co", "Ravenscroft Retail Partners", ""),
    case("rb-C-02", "C", "Section 9 Indemnity: Larkspur Freight Solutions shall indemnify "
         "Hollowgate Municipal Services for claims traceable to a delivery delay.",
         "Larkspur Freight Solutions", "Hollowgate Municipal Services", ""),
    # D. Colon-separated headings
    case("rb-D-01", "D", "12. Indemnification: Amberwood Consulting LLC shall indemnify "
         "and hold harmless Thistlemere Insurance Group from any regulatory fine.",
         "Amberwood Consulting LLC", "Thistlemere Insurance Group", ""),
    case("rb-D-02", "D", "Risk Transfer: Copperfield Analytics Corp shall indemnify "
         "Wrenfield Health Trust against any claim arising from a data breach.",
         "Copperfield Analytics Corp", "Wrenfield Health Trust", ""),
    # E. Headings without punctuation
    case("rb-E-01", "E", "13 Indemnification Obligations Milltown Fabrication Group shall "
         "indemnify Hartsfield Municipal Authority for claims arising from a defect.",
         None, "Hartsfield Municipal Authority",
         "No dash/colon/case-change separates the heading from the operative sentence at all -- "
         "genuinely irreducible from local text alone (both the heading words and the real name "
         "are ordinary Title Case, with no punctuation, capitalization, or connector-word signal "
         "distinguishing them). Accepted as a disclosed, fail-closed-safe residual limitation: "
         "actor is intentionally left unchecked (None) rather than demanding an impossible "
         "resolution; the beneficiary is unaffected and must still resolve correctly."),
    # F. Numbered sections
    case("rb-F-01", "F", "9. Bellwright Robotics Inc shall indemnify Sablewood Property "
         "Trust for any claim arising from an equipment malfunction.",
         "Bellwright Robotics Inc", "Sablewood Property Trust", ""),
    case("rb-F-02", "F", "12.3 Pemberton Aerospace Components shall indemnify Ursaline "
         "Medical Devices Corp for claims traceable to a certification failure.",
         "Pemberton Aerospace Components", "Ursaline Medical Devices Corp", ""),
    # G. Lettered subsections
    case("rb-G-01", "G", "(a) Quillon Data Ventures shall indemnify Vantree Retail "
         "Holdings for any claim arising from a licensing violation.",
         "Quillon Data Ventures", "Vantree Retail Holdings", ""),
    case("rb-G-02", "G", "Section 9(b): Yarrow Hospitality Group shall indemnify Zephrine "
         "Transport Authority for claims traceable to a booking error.",
         "Yarrow Hospitality Group", "Zephrine Transport Authority", ""),
    # H. Role names containing legitimate capitalized words (must NOT be truncated)
    case("rb-H-01", "H", "North American Fulfillment Group shall indemnify United "
         "Regional Health Partners for any claim arising from a shipping error.",
         "North American Fulfillment Group", "United Regional Health Partners",
         "Every word capitalized (ordinary title-case company name), mixed-case surrounding text -- must resolve in full, not truncate at the first word."),
    case("rb-H-02", "H", "Great Lakes Industrial Supply Corp shall indemnify Pacific "
         "Coast Retail Alliance LLC for claims arising from a defective shipment.",
         "Great Lakes Industrial Supply Corp", "Pacific Coast Retail Alliance LLC", ""),
    # I. Long corporate names
    case("rb-I-01", "I", "Northgate Fabrication and Precision Works LLC shall indemnify "
         "Continental Regional Insurance and Casualty Group for any claim.",
         None, None,
         "'and' as an internal name connector is NOT part of this remediation's scope (the "
         "existing connector allowance only ever supported of/the/for, unrelated to the "
         "role-boundary defect being fixed here) -- accepted as a pre-existing, disclosed, "
         "fail-closed-safe coverage gap rather than expanded within this bounded fix."),
    # J. Hyphenated role/company names
    case("rb-J-01", "J", "Best-in-Class Logistics Corp shall indemnify Riverside-Fenwick "
         "Holdings LLC for any claim arising from a delivery delay.",
         "Best-in-Class Logistics Corp", "Riverside-Fenwick Holdings LLC",
         "Regression control for the Phase 4 hyphenated-name fix -- must still work."),
    case("rb-J-02", "J", "State-of-the-Art Manufacturing Inc shall indemnify Cross-Town "
         "Retail Partners for claims traceable to a manufacturing defect.",
         "State-of-the-Art Manufacturing Inc", "Cross-Town Retail Partners", ""),
    # K. Dotted abbreviations
    case("rb-K-01", "K", "U.S. Fulfillment Corp shall indemnify U.K. Retail Partners for "
         "any claim arising from a customs violation.",
         "U.S. Fulfillment Corp", "U.K. Retail Partners", ""),
    # L. Ampersands
    case("rb-L-01", "L", "Harrington & Voss LLP shall indemnify Danforth & Reyes Inc for "
         "any claim arising from a filing error.",
         "Harrington & Voss LLP", "Danforth & Reyes Inc", ""),
    # M. Apostrophes
    case("rb-M-01", "M", "St. Aidan's Facilities Group shall indemnify Q&R Municipal "
         "Services for any claim arising from a maintenance failure.",
         "St. Aidan's Facilities Group", "Q&R Municipal Services", ""),
    # N. Role names followed by connector/preposition words -- attack examples,
    # NOT a stop-word list to hardcode. Each of these is an ordinary mixed-case
    # sentence (the connector word itself is lowercase) -- the fix must not
    # regress ordinary case-sensitive stopping, which already works today.
    case("rb-N-01", "N", "Marrow Bay Engineering PLLC shall indemnify Trelawney "
         "Municipal Utilities from any claim arising from a design defect.",
         "Marrow Bay Engineering PLLC", "Trelawney Municipal Utilities", "Connector: FROM"),
    case("rb-N-02", "N", "Thistledown Textiles Ltd shall indemnify Ursaline Medical "
         "Devices Corp for any claim relating to a labeling error.",
         "Thistledown Textiles Ltd", "Ursaline Medical Devices Corp", "Connector: FOR/RELATING"),
    case("rb-N-03", "N", "Kestrel Point Software Co shall indemnify Whitmore "
         "Agricultural Cooperative subject to the limitations in Section 12.",
         "Kestrel Point Software Co", "Whitmore Agricultural Cooperative", "Connector: SUBJECT"),
    case("rb-N-04", "N", "Amberlyn Construction Group shall indemnify Farrowmoor "
         "Publishing House provided that notice is given within 30 days.",
         "Amberlyn Construction Group", "Farrowmoor Publishing House", "Connector: PROVIDED"),
    case("rb-N-05", "N", "Foxglove Chemical Solutions shall indemnify Grantham Water "
         "Utility except for claims arising from Grantham's own negligence.",
         "Foxglove Chemical Solutions", "Grantham Water Utility", "Connector: EXCEPT"),
    case("rb-N-06", "N", "Rutledge & Marsh Consulting shall indemnify Hollowmere "
         "Research Institute including any claim brought by a regulator.",
         "Rutledge & Marsh Consulting", "Hollowmere Research Institute", "Connector: INCLUDING"),
    # -- The ALL-CAPS equivalents of the same connector attacks (these are
    # the genuine attack instances; N above are the mixed-case controls that
    # must keep passing).
    case("rb-N-07", "N", "IRONVALE MANUFACTURING CO SHALL INDEMNIFY LINDENHURST NURSING "
         "FACILITIES WITH RESPECT TO ANY CLAIM UNDER SECTION 9.",
         "IRONVALE MANUFACTURING CO", "LINDENHURST NURSING FACILITIES",
         "ALL-CAPS + connector: WITH (verbatim ALL-CAPS expected)"),
    case("rb-N-08", "N", "MOORCROFT LEGAL SERVICES PLLC SHALL INDEMNIFY EVERLINE PACKAGING "
         "SYSTEMS UNDER THE TERMS SET FORTH IN THIS AGREEMENT.",
         "MOORCROFT LEGAL SERVICES PLLC", "EVERLINE PACKAGING SYSTEMS",
         "ALL-CAPS + connector: UNDER (verbatim ALL-CAPS expected)"),
    case("rb-N-09", "N", "HARTSFIELD PRECISION TOOLS LLC SHALL INDEMNIFY MILLBROOK "
         "STAFFING PARTNERS AGAINST ANY CLAIM ARISING FROM A DEFECT.",
         "HARTSFIELD PRECISION TOOLS LLC", "MILLBROOK STAFFING PARTNERS",
         "ALL-CAPS + connector: AGAINST/ARISING (verbatim ALL-CAPS expected)"),
    # O. Multiple roles in the same clause
    case("rb-O-01", "O", "13. Indemnification -- Nightshade Security Solutions shall "
         "indemnify Oakmere Financial Group and its officers and directors from any "
         "claim arising from a data breach.",
         "Nightshade Security Solutions", None,
         "Beneficiary has a trailing appositive list ('and its officers and directors') -- acceptable outcome is either the bare beneficiary name or a correctly bounded capture, never a capture that also swallows 'from any claim arising from a' into the name."),
    # P. Reciprocal obligations (must still recognize the mutual pattern)
    case("rb-P-01", "P", "13. INDEMNIFICATION -- EACH PARTY SHALL INDEMNIFY AND HOLD "
         "HARMLESS THE OTHER PARTY FROM ANY CLAIM ARISING OUT OF ITS OWN BREACH.",
         None, None,
         "ALL-CAPS reciprocal opener -- 'mutual' shape, not named-role shape; must still be recognized as reciprocal, not mis-captured as named roles 'EACH PARTY'/'THE OTHER'."),
    # Q. Bystander corporate names
    case("rb-Q-01", "Q", "Pemberton Aerospace Components separately maintains a contract "
         "with Quillon Data Ventures unrelated to this Agreement. 13. Indemnification "
         "-- Kelbrook Telecommunications shall indemnify Lindenhurst Nursing Facilities "
         "for any claim arising from a data breach.",
         "Kelbrook Telecommunications", "Lindenhurst Nursing Facilities",
         "A bystander sentence naming two OTHER companies must not contaminate the real obligation's actor/beneficiary."),
    # R. Headings containing words that resemble roles
    case("rb-R-01", "R", "12. LIABILITY AND INDEMNIFICATION -- Moorcroft Legal Services "
         "PLLC SHALL INDEMNIFY Hartsfield Precision Tools LLC FOR ANY CLAIM ARISING "
         "FROM A BREACH OF WARRANTY.",
         "Moorcroft Legal Services PLLC", "Hartsfield Precision Tools LLC",
         "Heading itself contains 'INDEMNIFICATION' plus role-shaped words ('LIABILITY AND') that must not be absorbed into the actor."),
    # S. Defined terms adjacent to headings
    case("rb-S-01", "S", "9. Indemnification (the \"Indemnity Section\") -- Bellwright "
         "Robotics Inc shall indemnify Sablewood Property Trust for any claim.",
         "Bellwright Robotics Inc", "Sablewood Property Trust",
         "Parenthetical defined-term aside directly in the heading, before the operative sentence."),
    # T. Non-operative headings followed by operative text
    case("rb-T-01", "T", "ARTICLE IX: MISCELLANEOUS PROVISIONS -- Culver Ridge Analytics "
         "Inc shall indemnify Millbrook Staffing Partners for any claim arising from "
         "a breach of confidentiality.",
         "Culver Ridge Analytics Inc", "Millbrook Staffing Partners",
         "Heading is entirely unrelated to indemnification ('MISCELLANEOUS PROVISIONS') -- must not be absorbed into the actor merely because it is ALL-CAPS and adjacent."),
    # U. Legitimate role names with unusual capitalization
    case("rb-U-01", "U", "eBay-Style Marketplace Solutions LLC shall indemnify iRetail "
         "Partners Group for any claim arising from a listing error.",
         "eBay-Style Marketplace Solutions LLC", "iRetail Partners Group",
         "Legitimate brand-style names with an internal lowercase-then-uppercase pattern ('eBay', 'iRetail') -- must not be treated as a heading/clause boundary."),
    case("rb-U-02", "U", "3M-Adjacent Fulfillment Co shall indemnify B2B Wholesale "
         "Partners for any claim arising from a mislabeled shipment.",
         "3M-Adjacent Fulfillment Co", "B2B Wholesale Partners",
         "Digit-leading brand-style name plus alphanumeric beneficiary token."),
    # Additional negative controls: legitimate LONG multi-word names at the
    # boundary of what a naive truncation-based fix might wrongly cut short.
    case("rb-NEG-01", "NEG", "Northgate Fabrication Works LLC shall indemnify Sablewood "
         "Property Trust for any claim arising from a defect in materials.",
         "Northgate Fabrication Works LLC", "Sablewood Property Trust",
         "Ordinary mixed-case control -- must keep working unchanged."),
    case("rb-NEG-02", "NEG", "Ashford Data Systems Corp shall indemnify Trelawney "
         "Municipal Utilities for any claim arising from a service outage.",
         "Ashford Data Systems Corp", "Trelawney Municipal Utilities", ""),
    case("rb-NEG-03", "NEG", "Culver Ridge Analytics Inc shall indemnify Ursaline "
         "Medical Devices Corp for any claim arising from a data breach.",
         "Culver Ridge Analytics Inc", "Ursaline Medical Devices Corp", ""),
    case("rb-NEG-04", "NEG", "12. Limitation of Liability. Marrow Bay Engineering PLLC's "
         "aggregate liability shall not exceed $500,000. 13. Indemnification. Marrow "
         "Bay Engineering PLLC shall indemnify Vantree Retail Holdings for any claim "
         "arising from a design defect.",
         "Marrow Bay Engineering PLLC", "Vantree Retail Holdings",
         "A real heading ('12. Limitation of Liability.') and an unrelated sentence appear BEFORE the indemnification heading -- must not leak into the actor capture across the section break."),
    case("rb-NEG-05", "NEG", "Amberlyn Construction Group -- a specialty contractor -- "
         "shall indemnify Foxglove Chemical Solutions for any claim arising from a "
         "site accident.",
         "Amberlyn Construction Group", "Foxglove Chemical Solutions",
         "A parenthetical-style dash-delimited APPOSITIVE ('-- a specialty contractor --') sits between the actor and the modal verb -- must not be absorbed into the actor name, and must not break recognition of the actor either."),
]

# --- Second batch: push volume past 80, filling out categories A/H/I/J/K/L/M/N/O/Q/R/S/T/U ---
CASES += [
    case("rb-A-06", "A", "9. PAYMENT AND INDEMNIFICATION -- Cravenhurst Legal Partners "
         "SHALL INDEMNIFY Ivywell Research Consortium FOR ANY CLAIM ARISING FROM A "
         "BILLING ERROR.", "Cravenhurst Legal Partners", "Ivywell Research Consortium", ""),
    case("rb-A-07", "A", "12. RISK ALLOCATION -- Barrowmere Chemical Products SHALL "
         "INDEMNIFY Juniperfall Logistics Group AGAINST ANY REGULATORY FINE.",
         "Barrowmere Chemical Products", "Juniperfall Logistics Group", ""),
    case("rb-A-08", "A", "SECTION 14: LOSS ALLOCATION -- Nettlecombe IT Services SHALL "
         "INDEMNIFY Kingswharf Shipping Alliance FOR ANY CLAIM RELATING TO DATA LOSS.",
         "Nettlecombe IT Services", "Kingswharf Shipping Alliance", ""),
    case("rb-H-03", "H", "West Coast Regional Distribution Group shall indemnify East "
         "Coast National Insurance Alliance for claims arising from a delivery error.",
         "West Coast Regional Distribution Group", "East Coast National Insurance Alliance", ""),
    case("rb-H-04", "H", "American Standard Fabrication Corp shall indemnify National "
         "Union Retail Partners for any claim arising from a defect.",
         "American Standard Fabrication Corp", "National Union Retail Partners", ""),
    case("rb-I-02", "I", "Southern Regional Manufacturing and Distribution Alliance LLC "
         "shall indemnify Northern Metropolitan Insurance and Risk Group for claims.",
         None, None,
         "Same pre-existing 'and'-connector coverage gap as rb-I-01, out of this remediation's scope."),
    case("rb-J-03", "J", "Cross-Border Freight Solutions Inc shall indemnify Well-"
         "Grounded Insurance Partners for any claim arising from a customs delay.",
         "Cross-Border Freight Solutions Inc", "Well-Grounded Insurance Partners", ""),
    case("rb-J-04", "J", "Ready-to-Ship Logistics Corp shall indemnify Made-to-Order "
         "Manufacturing Partners for any claim arising from a packaging defect.",
         "Ready-to-Ship Logistics Corp", "Made-to-Order Manufacturing Partners", ""),
    case("rb-K-02", "K", "N.A. Fulfillment Corp shall indemnify E.U. Retail Partners for "
         "any claim arising from a customs violation.",
         "N.A. Fulfillment Corp", "E.U. Retail Partners", ""),
    case("rb-K-03", "K", "J.P. Holdings Group shall indemnify R.T. Insurance Partners "
         "for any claim arising from a coverage dispute.",
         "J.P. Holdings Group", "R.T. Insurance Partners", ""),
    case("rb-L-02", "L", "Fenwick & Ashcombe Partners LLC shall indemnify Delacroix & "
         "Munro Holdings for any claim arising from a breach of contract.",
         "Fenwick & Ashcombe Partners LLC", "Delacroix & Munro Holdings", ""),
    case("rb-L-03", "L", "A&B Manufacturing Corp shall indemnify C&D Retail Partners "
         "for any claim arising from a shipping defect.",
         "A&B Manufacturing Corp", "C&D Retail Partners", ""),
    case("rb-M-02", "M", "O'Rourke & Fennimore LLP shall indemnify D'Angelo Insurance "
         "Group for any claim arising from a professional liability matter.",
         "O'Rourke & Fennimore LLP", "D'Angelo Insurance Group", ""),
    case("rb-M-03", "M", "St. Bridget's Medical Partners shall indemnify O'Halloran-"
         "Deveraux Group for any claim arising from a billing dispute.",
         "St. Bridget's Medical Partners", "O'Halloran-Deveraux Group", ""),
    case("rb-N-10", "N", "Silverpine Engineering Corp shall indemnify Fallowfield "
         "Agricultural Trust arising from any claim traceable to a design defect.",
         "Silverpine Engineering Corp", "Fallowfield Agricultural Trust", "Connector: ARISING"),
    case("rb-N-11", "N", "Rookwood Financial Advisors shall indemnify Glenhaven "
         "Property Management to the extent permitted by applicable law.",
         "Rookwood Financial Advisors", "Glenhaven Property Management", "Connector: TO"),
    case("rb-N-12", "N", "WINTERMARSH SECURITY SYSTEMS SHALL INDEMNIFY HOLLYFIELD "
         "DISTRIBUTION CO PROVIDED THAT NOTICE IS GIVEN WITHIN THIRTY DAYS.",
         "WINTERMARSH SECURITY SYSTEMS", "HOLLYFIELD DISTRIBUTION CO",
         "ALL-CAPS + connector: PROVIDED (verbatim ALL-CAPS expected -- source is ALL-CAPS, correct behavior preserves case)"),
    case("rb-N-13", "N", "RAVENSCROFT DESIGN STUDIO SHALL INDEMNIFY LAMBOURNE TEXTILES "
         "LTD EXCEPT FOR CLAIMS ARISING FROM LAMBOURNE'S OWN NEGLIGENCE.",
         "RAVENSCROFT DESIGN STUDIO", "LAMBOURNE TEXTILES LTD",
         "ALL-CAPS + connector: EXCEPT (verbatim ALL-CAPS expected)"),
    case("rb-N-14", "N", "FOXDOWN ANALYTICS PARTNERS SHALL INDEMNIFY MILLGATE "
         "BROADCASTING CORP INCLUDING ANY CLAIM BROUGHT BY A REGULATOR.",
         "FOXDOWN ANALYTICS PARTNERS", "MILLGATE BROADCASTING CORP",
         "ALL-CAPS + connector: INCLUDING (verbatim ALL-CAPS expected)"),
    case("rb-O-02", "O", "13. Indemnification -- Halloway Media Productions shall "
         "indemnify Farthingale Retail Chain, its parent, and its subsidiaries from "
         "any claim arising from a licensing dispute.",
         "Halloway Media Productions", None,
         "Beneficiary followed by an appositive list of related entities -- acceptable outcome is the bare name or a safely-bounded capture, never a capture that also swallows 'from any claim arising from a'."),
    case("rb-Q-02", "Q", "Brackenfield Software Corp's unrelated dispute with a former "
         "employee is not addressed in this Agreement. 9. Indemnification -- "
         "Greymantle Industrial Supply shall indemnify Harrowgate Municipal Services "
         "for any claim arising from a supply defect.",
         "Greymantle Industrial Supply", "Harrowgate Municipal Services",
         "Bystander sentence naming an unrelated dispute and a third company must not contaminate the real actor/beneficiary."),
    case("rb-R-02", "R", "13. INDEMNIFICATION AND RISK TRANSFER -- Duskwillow "
         "Engineering Group SHALL INDEMNIFY Ingleside Hospitality Partners FOR ANY "
         "CLAIM ARISING FROM A SAFETY VIOLATION.",
         "Duskwillow Engineering Group", "Ingleside Hospitality Partners", ""),
    case("rb-S-02", "S", "12. Indemnification (as defined in Section 1.2) -- Emberfall "
         "Analytics Inc shall indemnify Jarrowfield Insurance Brokers for any claim.",
         "Emberfall Analytics Inc", "Jarrowfield Insurance Brokers", ""),
    case("rb-T-02", "T", "SCHEDULE 4: DEFINITIONS -- Kettlebrook Security Corp shall "
         "indemnify Pennywhistle Research Labs for any claim arising from a breach "
         "of confidentiality.",
         "Kettlebrook Security Corp", "Pennywhistle Research Labs",
         "Heading entirely about definitions, unrelated to indemnification, must not leak into the actor."),
    case("rb-U-03", "U", "McAllister-Grant Holdings LLC shall indemnify DeVries Retail "
         "Partners for any claim arising from a contract breach.",
         "McAllister-Grant Holdings LLC", "DeVries Retail Partners",
         "Internal-capital surname-style names (McAllister, DeVries)."),
    case("rb-NEG-06", "NEG", "Larkhollow Financial Group shall indemnify Quarrymoor "
         "Insurance Alliance for any claim arising from a reporting error.",
         "Larkhollow Financial Group", "Quarrymoor Insurance Alliance", ""),
    case("rb-NEG-07", "NEG", "Millthorpe Logistics Partners shall indemnify Ravensmere "
         "Construction Co for any claim arising from a scheduling failure.",
         "Millthorpe Logistics Partners", "Ravensmere Construction Co", ""),
    case("rb-NEG-08", "NEG", "9. Payment Terms. Nightingdale Systems Corp shall pay "
         "Silverbrook Municipal Trust within Net 30 days. 13. Indemnification. "
         "Nightingdale Systems Corp shall indemnify Silverbrook Municipal Trust for "
         "any claim arising from a billing dispute.",
         "Nightingdale Systems Corp", "Silverbrook Municipal Trust",
         "An unrelated payment-terms heading and sentence precede the indemnification heading -- must not leak across the section break."),
    case("rb-NEG-09", "NEG", "Hartwell Data Solutions -- acting through its authorized "
         "representative -- shall indemnify Marrowbrook Legal Group for any claim "
         "arising from a data breach.",
         "Hartwell Data Solutions", "Marrowbrook Legal Group",
         "Dash-delimited appositive between actor and modal verb, distinct company names from rb-NEG-05."),
    case("rb-NEG-10", "NEG", "12. Limitation of Liability -- Ironbridge Consulting "
         "Partners' aggregate liability shall not exceed $750,000. 13. Indemnification "
         "-- Ironbridge Consulting Partners shall indemnify Nettlewood Distribution "
         "Co for any claim arising from a service failure.",
         "Ironbridge Consulting Partners", "Nettlewood Distribution Co",
         "Two consecutive ALL-CAPS-adjacent headings with an unrelated liability sentence between them -- must not bridge across both section breaks."),
]

CASES += [
    case("rb-A-09", "A", "SECTION 13: INDEMNIFICATION -- Corrigan Industrial Supply "
         "SHALL INDEMNIFY Wrenfield Municipal Authority FOR ANY CLAIM ARISING FROM "
         "A DELIVERY FAILURE.", "Corrigan Industrial Supply", "Wrenfield Municipal Authority", ""),
    case("rb-NEG-11", "NEG", "Kettleworth Software Labs shall indemnify Brambleton "
         "School Trust for any claim arising from a data breach.",
         "Kettleworth Software Labs", "Brambleton School Trust", ""),
    case("rb-NEG-12", "NEG", "Ashgrove Freight Solutions shall indemnify Dunmore "
         "Manufacturing Alliance for any claim arising from a transit delay.",
         "Ashgrove Freight Solutions", "Dunmore Manufacturing Alliance", ""),
    case("rb-H-05", "H", "Metropolitan National Insurance Group shall indemnify "
         "International Standard Manufacturing Corp for any claim arising from a "
         "product defect.",
         "Metropolitan National Insurance Group", "International Standard Manufacturing Corp", ""),
]
