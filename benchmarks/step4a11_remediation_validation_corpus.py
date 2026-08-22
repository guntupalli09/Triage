"""Step 4A.11 Remediation — Phase 7 LOCKED fresh remediation-validation
corpus. Independent of the Step 4A.10/4A.10.x corpora, Step 4A.11 Phase
1-4 DEV/battery corpora, the Phase 6 final 393-case corpus, and the
Phase 2 role-boundary DEV benchmark (rb-*) -- entirely fresh vocabulary,
headings, connectors, capitalization, and grammatical structures. Does
NOT copy or paraphrase the originally discovered defect case.

Focus (per remediation spec): ~60 role/boundary/heading stress,
~40 material-fact ownership, ~30 reciprocal/symmetry, ~30 compound.
Executed exactly once against frozen remediation production
(2f8d4762cec595ec6b5f7a16edd5b885e9bde67d) -- no tuning after results.
"""
from typing import Any, Dict, List, Optional

from benchmarks.step4a11_remediation_validation_vocab import (
    IND_ACTORS, IND_BENEFICIARIES, LIA_PARTIES, PAY_PARTIES,
)

CASES: List[Dict[str, Any]] = []


def case(cid: str, focus: str, adapter: str, text: str, expected_status: str,
         expected: Optional[Dict[str, Any]] = None, expected_dimension: Optional[str] = None,
         notes: str = "") -> Dict[str, Any]:
    return {"id": cid, "focus": focus, "adapter": adapter, "text": text,
            "expected_status": expected_status, "expected": expected,
            "expected_dimension": expected_dimension, "notes": notes}

# ===========================================================================
# FOCUS 1: role/boundary/heading stress (~60 cases, indemnification-only --
# this is the mechanism that was fixed; liability/payment_terms were
# confirmed unaffected by the original root-cause analysis)
# ===========================================================================
_RB_TEMPLATES = [
    # ALL-CAPS heading + ALL-CAPS operative clause, entirely fresh structure
    ("17. RISK ALLOCATION PROVISIONS OF {A} -- {A} SHALL INDEMNIFY AND HOLD "
     "HARMLESS {B} FOR ANY LOSS ARISING OUT OF A BREACH OF SECTION 8.",
     "ab", "AF-heading-allcaps"),
    ("SECTION 11: LOSS TRANSFER -- {A} SHALL INDEMNIFY {B} AGAINST ANY CLAIM "
     "RELATING TO A DEFECTIVE COMPONENT.", "ab", "AF-heading-allcaps"),
    ("ARTICLE VII -- INDEMNITY -- {A} SHALL INDEMNIFY {B} WITH RESPECT TO ANY "
     "CLAIM UNDER THIS AGREEMENT.", "ab", "AF-heading-allcaps"),
    ("9. COMPENSATION AND INDEMNIFICATION -- {A} SHALL INDEMNIFY {B} FOR ANY "
     "CLAIM INCLUDING THOSE ARISING FROM A LABELING ERROR.", "ab", "AF-heading-allcaps"),
    ("RISK AND LIABILITY TRANSFER -- {A} SHALL INDEMNIFY {B} SUBJECT TO THE "
     "TERMS OF THIS SECTION.", "ab", "AF-heading-allcaps"),
    # Title-Case heading + dash
    ("14. Indemnification Provisions -- {A} shall indemnify and hold "
     "harmless {B} from any claim arising from a breach of warranty.",
     "ab", "AF-heading-titlecase"),
    ("Loss Allocation Terms -- {A} shall indemnify {B} for claims arising "
     "from a shipping delay.", "ab", "AF-heading-titlecase"),
    # Colon-separated heading
    ("Indemnification: {A} shall indemnify and hold harmless {B} from any "
     "regulatory penalty.", "ab", "AF-heading-colon"),
    ("Section 12 Indemnity: {A} shall indemnify {B} for claims traceable to "
     "a certification failure.", "ab", "AF-heading-colon"),
    # Inline heading, no punctuation at all before the sentence
    ("14 Loss Transfer Provisions {A} shall indemnify {B} for claims arising "
     "from a design defect.", "ab", "AF-heading-none",
     "Genuinely unpunctuated heading -- known irreducible limitation class (compare rb-E-01); outcome may safely be fail-closed on the actor."),
    # Numbered/lettered sections
    ("9. {A} shall indemnify {B} for any claim arising from a data breach.",
     "ab", "AF-numbered"),
    ("(c) {A} shall indemnify {B} for claims traceable to a licensing "
     "violation.", "ab", "AF-lettered"),
    ("Section 9(d): {A} shall indemnify {B} for any claim arising from a "
     "billing error.", "ab", "AF-lettered"),
    # Long legitimate names (negative controls -- must NOT be truncated)
    ("Metropolitan Regional Fabrication Alliance shall indemnify National "
     "Standard Insurance Partners for any claim arising from a defect.",
     "literal:Metropolitan Regional Fabrication Alliance:National Standard Insurance Partners", "AF-long-name"),
    ("Great Northern Industrial Holdings Corp shall indemnify Central "
     "Atlantic Risk Management Group for any claim.",
     "literal:Great Northern Industrial Holdings Corp:Central Atlantic Risk Management Group", "AF-long-name"),
    # Hyphenated/dotted/ampersand/apostrophe names
    ("Best-of-Breed Manufacturing Corp shall indemnify Cross-Market Retail "
     "Partners for claims arising from a packaging defect.",
     "literal:Best-of-Breed Manufacturing Corp:Cross-Market Retail Partners", "AF-hyphenated"),
    ("U.S.-Pacific Trading Corp shall indemnify E.U.-Atlantic Holdings for "
     "any claim arising from a customs delay.",
     "literal:U.S.-Pacific Trading Corp:E.U.-Atlantic Holdings", "AF-dotted"),
    ("Marlowe & Fenn Partners LLP shall indemnify Castellan & Rourke Group "
     "for any claim arising from a filing error.",
     "literal:Marlowe & Fenn Partners LLP:Castellan & Rourke Group", "AF-ampersand"),
    ("St. Cuthbert's Health Trust shall indemnify D'Arcy & Whitlock LLP for "
     "any claim arising from a billing dispute.",
     "literal:St. Cuthbert's Health Trust:D'Arcy & Whitlock LLP", "AF-apostrophe"),
    # Connector-word attacks (fresh phrasing, NOT reusing rb-* wording)
    ("{A} shall indemnify {B} from any claim traceable to a supply chain "
     "failure.", "ab", "AF-connector-from"),
    ("{A} shall indemnify {B} for any claim relating to a warranty dispute.",
     "ab", "AF-connector-relating"),
    ("{A} shall indemnify {B} subject to the notice requirements in "
     "Section 5.", "ab", "AF-connector-subject"),
    ("{A} shall indemnify {B} provided that written notice is delivered "
     "within fifteen days.", "ab", "AF-connector-provided"),
    ("{A} shall indemnify {B} except for claims caused by {B}'s own gross "
     "negligence.", "ab", "AF-connector-except"),
    ("{A} shall indemnify {B} including any claim brought by a government "
     "agency.", "ab", "AF-connector-including"),
    ("{A} shall indemnify {B} against any claim arising under applicable "
     "environmental law.", "ab", "AF-connector-against"),
    ("VESTRON INDUSTRIAL PARTNERS SHALL INDEMNIFY HARLOW MUNICIPAL SERVICES "
     "WITH RESPECT TO ANY CLAIM ARISING FROM A SAFETY VIOLATION.",
     "literal:VESTRON INDUSTRIAL PARTNERS:HARLOW MUNICIPAL SERVICES", "AF-connector-allcaps-1"),
    ("BRIGHTFORGE MANUFACTURING CO SHALL INDEMNIFY CASTLEROCK INSURANCE "
     "GROUP INCLUDING ANY CLAIM RELATING TO A PRODUCT RECALL.",
     "literal:BRIGHTFORGE MANUFACTURING CO:CASTLEROCK INSURANCE GROUP", "AF-connector-allcaps-2"),
    ("DRAVENPORT LOGISTICS ALLIANCE SHALL INDEMNIFY EASTGATE RETAIL "
     "PARTNERS PROVIDED THAT NOTICE IS DELIVERED PROMPTLY.",
     "literal:DRAVENPORT LOGISTICS ALLIANCE:EASTGATE RETAIL PARTNERS", "AF-connector-allcaps-3"),
    # Reciprocal opener (mutual, no named roles)
    ("18. INDEMNIFICATION -- EITHER PARTY SHALL INDEMNIFY AND HOLD HARMLESS "
     "THE OTHER PARTY AGAINST ANY LOSS TRACEABLE TO ITS OWN MISCONDUCT.",
     "mutual", "AF-reciprocal-allcaps"),
    # Bystander names near a heading
    ("{A} maintains a separate, unrelated contract with a third party not "
     "addressed in this Agreement. 12. Indemnification -- {B} shall "
     "indemnify {A} for any claim arising from a facilities defect.",
     "ba", "AF-bystander"),
    # Heading containing role-shaped words
    ("13. LIABILITY, INDEMNIFICATION, AND RISK TRANSFER -- {A} SHALL "
     "INDEMNIFY {B} FOR ANY CLAIM ARISING FROM A BREACH OF WARRANTY.",
     "ab", "AF-heading-role-words"),
    # Defined term adjacent to heading
    ("9. Indemnification (the \"Risk Provision\") -- {A} shall indemnify "
     "{B} for any claim arising from a data breach.", "ab", "AF-defined-term"),
    # Non-operative heading (unrelated to indemnification) followed by
    # operative text
    ("SCHEDULE 7: GOVERNING LAW -- {A} SHALL INDEMNIFY {B} FOR ANY CLAIM "
     "ARISING FROM A BREACH OF CONFIDENTIALITY.", "ab", "AF-heading-unrelated"),
    # Unusual capitalization (legitimate)
    ("eCommerce Solutions Group shall indemnify iFinance Partners LLC for "
     "any claim arising from a payment processing error.",
     "literal:eCommerce Solutions Group:iFinance Partners LLC", "AF-unusual-caps"),
    # Two prior headings before the real one (must not bleed across breaks)
    ("12. Limitation of Liability -- {A}'s aggregate liability shall not "
     "exceed $600,000. 13. Indemnification -- {A} shall indemnify {B} for "
     "any claim arising from a facilities defect.", "ab", "AF-prior-heading"),
]

_RB_A_IDX = 0
_RB_B_IDX = 0
for _ti, entry in enumerate(_RB_TEMPLATES):
    tmpl, exp_kind, tag = entry[0], entry[1], entry[2]
    notes = entry[3] if len(entry) > 3 else ""
    reps = 2
    for _r in range(reps):
        a = IND_ACTORS[_RB_A_IDX % len(IND_ACTORS)]
        b = IND_BENEFICIARIES[_RB_B_IDX % len(IND_BENEFICIARIES)]
        _RB_A_IDX += 1
        _RB_B_IDX += 1
        if exp_kind == "ba":
            text = tmpl.format(A=a, B=b)
            expected = {"actor": b, "beneficiary": a}
        elif exp_kind.startswith("literal:"):
            _, lit_a, lit_b = exp_kind.split(":")
            text = tmpl
            expected = {"actor": lit_a, "beneficiary": lit_b}
        elif exp_kind == "mutual":
            text = tmpl
            expected = None
        else:
            text = tmpl.format(A=a, B=b)
            expected = {"actor": a, "beneficiary": b}
        status = "ESTABLISHED"
        cid = f"rv-rb-{tag}-{_ti:02d}-{_r}"
        CASES.append(case(cid, "role_boundary", "indemnification", text, status, expected, None, notes))

# ===========================================================================
# FOCUS 2: material-fact ownership (~40 cases, all 3 adapters)
# ===========================================================================
_OWN_IND_TEMPLATES = [
    "{A} separately maintains an unrelated services contract with a "
    "third party not addressed in this Agreement. 12. Indemnification -- "
    "{A} shall indemnify {B} for any claim arising from a shipment defect.",
    "A different, unrelated dispute between {B} and a former contractor "
    "is outside the scope of this Agreement. {A} shall indemnify {B} for "
    "any claim arising from a data breach.",
    "{B}'s facilities director, who is not a party to this Agreement, "
    "separately carries professional liability insurance. {A} shall "
    "indemnify {B} for any claim arising from an equipment failure.",
]
_OWN_LIA_TEMPLATES = [
    "{A} separately maintains $8,000,000 of umbrella coverage for matters "
    "unrelated to this Agreement. 12. Limitation of Liability. {A}'s "
    "aggregate liability to {B} shall not exceed $450,000.",
    "A different vendor of {B}'s is subject to a $3,000,000 cap under an "
    "unrelated contract. 12. Limitation of Liability. {A}'s aggregate "
    "liability to {B} shall not exceed 2 times the annual fees.",
]
_OWN_PAY_TEMPLATES = [
    "{A} separately reimburses employees within ten days under an "
    "internal policy unrelated to this Agreement. 9. Payment Terms. {A} "
    "shall pay {B} within Net 30 days of receipt of invoice.",
    "A different vendor of {B}'s is paid on Net 15 terms under an "
    "unrelated contract. 9. Payment Terms. {A} shall pay {B} within Net "
    "45 days of receipt of invoice.",
]

_OWN_A_IDX = 0
_OWN_B_IDX = 0
for _ti, tmpl in enumerate(_OWN_IND_TEMPLATES):
    for _r in range(5):
        a = IND_ACTORS[_OWN_A_IDX % len(IND_ACTORS)]
        b = IND_BENEFICIARIES[_OWN_B_IDX % len(IND_BENEFICIARIES)]
        _OWN_A_IDX += 1
        _OWN_B_IDX += 1
        text = tmpl.format(A=a, B=b)
        CASES.append(case(f"rv-own-ind-{_ti:02d}-{_r}", "ownership", "indemnification",
                           text, "ESTABLISHED", {"actor": a, "beneficiary": b}, None,
                           "Bystander unrelated value/name must not contaminate the real obligation."))

_LIA_IDX = 0
for _ti, tmpl in enumerate(_OWN_LIA_TEMPLATES):
    for _r in range(5):
        a, b = LIA_PARTIES[_LIA_IDX % len(LIA_PARTIES)]
        _LIA_IDX += 1
        text = tmpl.format(A=a, B=b)
        if "450,000" in tmpl:
            expected = {"kind": "fixed", "fixed_amount": 450000.0}
        else:
            expected = {"kind": "multiplier", "multiplier": 2.0}
        CASES.append(case(f"rv-own-lia-{_ti:02d}-{_r}", "ownership", "liability",
                           text, "ESTABLISHED", expected, "general_cap",
                           "Bystander unrelated cap figure must not contaminate the real cap."))

_PAY_IDX = 0
for _ti, tmpl in enumerate(_OWN_PAY_TEMPLATES):
    for _r in range(5):
        a, b = PAY_PARTIES[_PAY_IDX % len(PAY_PARTIES)]
        _PAY_IDX += 1
        text = tmpl.format(A=a, B=b)
        days = 30.0 if "Net 30" in tmpl else 45.0
        CASES.append(case(f"rv-own-pay-{_ti:02d}-{_r}", "ownership", "payment_terms",
                           text, "ESTABLISHED", {"net_days": days}, "net_days",
                           "Bystander unrelated day figure must not contaminate the real payment window."))

# ===========================================================================
# FOCUS 3: reciprocal/symmetry interactions (~30 cases)
# ===========================================================================
_SYM_TEMPLATES = [
    ("18. INDEMNIFICATION -- BOTH PARTIES SHALL INDEMNIFY AND HOLD "
     "HARMLESS THE OTHER PARTY AGAINST ANY LOSS TRACEABLE TO ITS "
     "RESPECTIVE ACTS OF MISCONDUCT.", "ind", "mutual", None),
    ("Both parties shall indemnify the other party for claims traceable "
     "to its own reckless conduct.", "ind", "mutual", None),
    ("{A} shall indemnify {B} for claims arising from a data breach, "
     "capped at $500,000; {B} shall indemnify {A} for claims arising "
     "from a data breach, capped at $150,000.", "ind", "asym", None),
    ("12. Limitation of Liability. The aggregate liability of either "
     "party to the other shall not exceed one time the total fees the "
     "other party paid during the preceding twelve-month period.", "lia", "mutual_lia", None),
    ("12. Limitation of Liability. {A}'s aggregate liability to {B} "
     "shall not exceed $400,000. {B}'s aggregate liability to {A} shall "
     "not exceed $1,800,000.", "lia", "asym_lia", None),
]

for _ti, (tmpl, adapter, kind, _unused) in enumerate(_SYM_TEMPLATES):
    for _r in range(6):
        if adapter == "ind":
            a = IND_ACTORS[_RB_A_IDX % len(IND_ACTORS)]
            b = IND_BENEFICIARIES[_RB_B_IDX % len(IND_BENEFICIARIES)]
            _RB_A_IDX += 1
            _RB_B_IDX += 1
            text = tmpl.format(A=a, B=b) if "{A}" in tmpl else tmpl
            expected = None if kind in ("mutual", "asym") else {"actor": a, "beneficiary": b}
            CASES.append(case(f"rv-sym-{_ti:02d}-{_r}", "symmetry", "indemnification",
                               text, "ESTABLISHED", expected, None,
                               "Reciprocal/asymmetric interaction -- must not be falsely reported symmetric when values differ." if kind == "asym" else "Canonical reciprocal opener."))
        else:
            a, b = LIA_PARTIES[_LIA_IDX % len(LIA_PARTIES)]
            _LIA_IDX += 1
            text = tmpl.format(A=a, B=b) if "{A}" in tmpl else tmpl
            if kind == "mutual_lia":
                expected = {"kind": "multiplier", "multiplier": 1.0}
            else:
                expected = {"kind": "fixed", "fixed_amount": 400000.0}
            CASES.append(case(f"rv-sym-{_ti:02d}-{_r}", "symmetry", "liability",
                               text, "ESTABLISHED", expected, "general_cap",
                               "Directional caps with different values -- controlling provision must reflect the actor's own side."))

# ===========================================================================
# FOCUS 4: compound interactions -- role extraction + conditions/
# cross-references/non-operative text (~30 cases)
# ===========================================================================
_COMPOUND_TEMPLATES = [
    ("17. INDEMNIFICATION OBLIGATIONS -- {A} SHALL INDEMNIFY {B} AS SET "
     "FORTH IN THE MASTER RISK TERMS REFERENCED IN SECTION 4, PROVIDED "
     "THAT {B} GIVES {A} PROMPT WRITTEN NOTICE.", "ind", "ab_condition",
     "Compound: ALL-CAPS heading + cross-reference (target not included) + trailing proviso. Obligation directly stated -- actor/beneficiary establish; scope delegated."),
    ("{A} shall indemnify {B} as described in the Master Risk Terms "
     "referenced in Section 3, but only for claims asserted within two "
     "years.", "ind", "ab_condition", "Compound: cross-reference + temporal condition, mixed case."),
    ("A sample indemnification clause, shown here for reference only and "
     "not part of the Agreement, reads: \"{A} shall indemnify {B}.\" "
     "13. Indemnification -- {A} shall indemnify {B} for any claim "
     "arising from a facilities defect, provided that notice is given "
     "within 10 days.", "ind", "ab_condition",
     "Compound: non-operative quoted example followed by the real, operative heading+clause+condition."),
    ("12. Limitation of Liability -- the ceiling on {A}'s exposure to {B} "
     "is governed by the terms in the Commercial Risk Annex, so long as "
     "{A} keeps its coverage current.", "lia", "none",
     "Compound: cross-reference (uncontained target, different phrasing than prior corpora) + leading condition -- correctly unresolved."),
    ("9. Payment Terms -- amounts owed by {A} to {B} are governed by the "
     "Billing Framework Annex, unless that annex has not yet been "
     "countersigned by both parties.", "pay", "none",
     "Compound: cross-reference (uncontained target) + condition, different phrasing than prior corpora -- correctly unresolved."),
]

for _ti, (tmpl, adapter, kind, notes) in enumerate(_COMPOUND_TEMPLATES):
    for _r in range(6):
        if adapter == "ind":
            a = IND_ACTORS[_RB_A_IDX % len(IND_ACTORS)]
            b = IND_BENEFICIARIES[_RB_B_IDX % len(IND_BENEFICIARIES)]
            _RB_A_IDX += 1
            _RB_B_IDX += 1
            text = tmpl.format(A=a, B=b)
            expected = {"actor": a, "beneficiary": b}
            CASES.append(case(f"rv-cmp-{_ti:02d}-{_r}", "compound", "indemnification",
                               text, "ESTABLISHED", expected, None, notes))
        elif adapter == "lia":
            a, b = LIA_PARTIES[_LIA_IDX % len(LIA_PARTIES)]
            _LIA_IDX += 1
            text = tmpl.format(A=a, B=b)
            CASES.append(case(f"rv-cmp-{_ti:02d}-{_r}", "compound", "liability",
                               text, "NOT_ESTABLISHED", None, None, notes))
        else:
            a, b = PAY_PARTIES[_PAY_IDX % len(PAY_PARTIES)]
            _PAY_IDX += 1
            text = tmpl.format(A=a, B=b)
            CASES.append(case(f"rv-cmp-{_ti:02d}-{_r}", "compound", "payment_terms",
                               text, "NOT_ESTABLISHED", None, None, notes))
