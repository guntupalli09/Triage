"""Step 4A.11 Phase 2 — dedicated DEVELOPMENT benchmark for conditional
applicability (indemnification, liability, payment_terms adapters).

Built and run BEFORE any production code in this phase is modified, per
the phase-2 specification's explicit ordering requirement.

DEVELOPMENT ONLY. Not the final Step 4A.11 frozen validation corpus.
Iteration against this corpus is expected; the final frozen corpus is
authored independently, later, after candidate freeze, and run exactly
once.

Each case declares:
  id, tags, adapter ("indemnification"|"liability"|"payment_terms"), text,
  expected_status in {"UNCONDITIONAL", "ESTABLISHED", "NOT_ESTABLISHED",
                       "CONFLICTING"},
  expected_condition_type (informational, not scored as a hard gate —
      condition connector FAMILY, when the case is meant to exercise one),
  notes.

Status meanings (the three-state model, Section 8 of the phase spec):
  UNCONDITIONAL   -- no material condition modifies this fact; the fact
                     itself should still extract as ESTABLISHED/clean.
  ESTABLISHED     -- a condition is present AND its attachment to this
                     specific material fact is deterministically clear.
  NOT_ESTABLISHED -- condition-like language exists nearby, but either it
                     doesn't attach to this fact (wrong owner/wrong
                     obligation/example/heading/non-operative) or its
                     precise scope can't be confirmed -- must NOT be
                     silently treated as either "no condition" or "always
                     satisfied."
  CONFLICTING     -- two operative provisions impose incompatible
                     conditions on the same fact that cannot be
                     deterministically reconciled.

The authority rule under test: a conditional fact may become
authoritative (participate in a clean automatic decision) only WITH its
condition preserved. A case whose material fact is genuinely conditional
must never be reported as an unconditional clean fact -- that is the
"stripped-condition authoritative fact" failure mode this phase exists to
eliminate, and it is scored as a hard, safety-critical mismatch by the
runner, independent of whether the overall corpus otherwise looks good.
"""

from typing import Any, Dict, List, Optional


def case(id: str, tags: List[str], adapter: str, text: str, expected_status: str,
         expected_condition_type: Optional[str] = None, notes: str = "") -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "adapter": adapter, "text": text,
        "expected_status": expected_status,
        "expected_condition_type": expected_condition_type,
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# ===========================================================================
# A. IF / WHEN -- leading conditional clause, indemnification
# ===========================================================================
CASES += [
    case("cond-if-01", ["A_if_when", "leading"], "indemnification",
         "12. Indemnification. If Customer breaches its confidentiality obligations under this "
         "Agreement, Vendor shall indemnify, defend, and hold harmless Customer from and against "
         "any third-party claims arising from such breach.",
         "ESTABLISHED", "if_when",
         notes="Classic leading-IF conditional obligation -- must never collapse to an unconditional "
               "'Vendor indemnifies Customer.'"),
    case("cond-when-01", ["A_if_when", "leading"], "indemnification",
         "12. Indemnification. When a third party asserts a claim of intellectual property "
         "infringement against Customer arising from the Licensed Software, Vendor shall "
         "indemnify, defend, and hold harmless Customer against such claim.",
         "ESTABLISHED", "if_when"),
]

# ===========================================================================
# B. UNLESS
# ===========================================================================
CASES += [
    case("cond-unless-01", ["B_unless", "trailing"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of this Agreement, unless "
         "such claims arise from Customer's own negligence or willful misconduct.",
         "ESTABLISHED", "unless"),
    case("cond-unless-liability-01", ["B_unless", "trailing"], "liability",
         "12. Limitation of Liability. In no event shall either party's aggregate liability under "
         "this Agreement exceed 2 times the total annual fees paid, unless such liability arises "
         "from a party's breach of its confidentiality obligations, in which case no such "
         "limitation shall apply.",
         "ESTABLISHED", "unless"),
]

# ===========================================================================
# C. PROVIDED / PROVIDED THAT
# ===========================================================================
CASES += [
    case("cond-provided-that-01", ["C_provided_that", "trailing"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's willful misconduct, provided that "
         "Customer gives Vendor prompt written notice of any such claim.",
         "ESTABLISHED", "provided_that"),
    case("cond-provided-however-that-01", ["C_provided_that", "trailing"], "liability",
         "12. Limitation of Liability. Vendor's aggregate liability shall not exceed $1,000,000, "
         "provided, however, that this limitation shall apply only to claims arising from Vendor's "
         "performance of the Services under Section 3.",
         "ESTABLISHED", "provided_that",
         notes="The example from the phase spec itself -- a qualifier that materially limits "
               "applicability, must not become an unconditional $1M cap."),
]

# ===========================================================================
# D. ONLY IF
# ===========================================================================
CASES += [
    case("cond-only-if-01", ["D_only_if", "leading"], "indemnification",
         "12. Indemnification. Only if a court of competent jurisdiction finds Vendor liable for "
         "gross negligence, Vendor shall indemnify Customer for the resulting damages.",
         "ESTABLISHED", "only_if"),
    case("cond-but-only-if-01", ["D_only_if", "trailing"], "payment_terms",
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of invoice, but "
         "only if Vendor has delivered the Deliverables in accordance with the applicable statement "
         "of work.",
         "ESTABLISHED", "only_if"),
]

# ===========================================================================
# E. TO THE EXTENT
# ===========================================================================
CASES += [
    case("cond-to-the-extent-01", ["E_to_the_extent", "trailing"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims, to the extent such claims arise from Vendor's breach of "
         "its representations and warranties under this Agreement.",
         "ESTABLISHED", "to_the_extent"),
    case("cond-only-to-the-extent-01", ["E_to_the_extent", "trailing"], "liability",
         "12. Limitation of Liability. Vendor's aggregate liability shall not exceed 2 times the "
         "total annual fees paid, only to the extent such liability arises from ordinary breach of "
         "this Agreement.",
         "ESTABLISHED", "to_the_extent"),
]

# ===========================================================================
# F. SUBJECT TO -- both the cross-reference form (handled by Phase 1) and the
#    "subject to conditions/consent" form new to this phase
# ===========================================================================
CASES += [
    case("cond-subject-to-conditions-01", ["F_subject_to", "midclause"], "indemnification",
         "12. Indemnification. Vendor shall indemnify Customer, subject to the following conditions: "
         "Customer must provide prompt written notice and reasonable cooperation in the defense.",
         "ESTABLISHED", "subject_to_conditions"),
    case("cond-subject-to-consent-01", ["F_subject_to", "midclause"], "indemnification",
         "12. Indemnification. Vendor shall indemnify Customer for third-party IP claims, subject "
         "to Customer's prior written consent to any settlement.",
         "ESTABLISHED", "subject_to_conditions"),
    case("cond-subject-to-section-01", ["F_subject_to", "cross_reference"], "indemnification",
         "9. Limitation of Liability. Aggregate liability shall not exceed $750,000.\n\n"
         "12. Indemnification. Vendor shall indemnify Customer, subject to the limitation of "
         "liability set forth in Section 9.",
         "ESTABLISHED", "cross_reference",
         notes="This is the Phase 1 cross-reference mechanism, not a Phase 2 condition -- included "
               "here as a boundary case confirming the two mechanisms don't collide (this resolves "
               "to a VALUE delegation, not an applicability condition)."),
]

# ===========================================================================
# G. EXCEPT / EXCEPT WHEN / EXCEPT TO THE EXTENT
# ===========================================================================
CASES += [
    case("cond-except-when-01", ["G_except", "trailing"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's performance of the Services, except "
         "when such claims arise from Customer's modification of the deliverables.",
         "ESTABLISHED", "except"),
    case("cond-except-to-the-extent-01", ["G_except", "trailing"], "liability",
         "12. Limitation of Liability. Vendor's aggregate liability shall not exceed $500,000, "
         "except to the extent such liability arises from Vendor's fraud.",
         "ESTABLISHED", "except"),
]

# ===========================================================================
# H. UPON
# ===========================================================================
CASES += [
    case("cond-upon-occurrence-01", ["H_upon", "midclause"], "indemnification",
         "12. Indemnification. Upon the occurrence of a data breach affecting Customer's data, "
         "Vendor shall indemnify, defend, and hold harmless Customer from and against any resulting "
         "third-party claims.",
         "ESTABLISHED", "upon"),
    case("cond-upon-receipt-01", ["H_upon", "midclause"], "indemnification",
         "12. Indemnification. Vendor shall indemnify Customer, upon receipt of written notice from "
         "Customer describing the claim in reasonable detail.",
         "ESTABLISHED", "upon"),
    case("cond-upon-termination-01", ["H_upon", "midclause"], "payment_terms",
         "9. Payment Terms. Upon termination of this Agreement, Customer shall pay Vendor all fees "
         "accrued through the effective date of termination within Net 30 days.",
         "ESTABLISHED", "upon"),
]

# ===========================================================================
# I. WHERE / WHERE APPLICABLE
# ===========================================================================
CASES += [
    case("cond-where-applicable-01", ["I_where", "midclause"], "indemnification",
         "12. Indemnification. Vendor shall indemnify Customer for third-party claims arising from "
         "Vendor's breach, where applicable law does not otherwise limit such indemnification.",
         "ESTABLISHED", "where_applicable"),
]

# ===========================================================================
# J. CONTINGENT / CONDITIONED UPON
# ===========================================================================
CASES += [
    case("cond-contingent-on-01", ["J_contingent", "midclause"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach, contingent on Customer "
         "providing Vendor sole control of the defense of any such claim.",
         "ESTABLISHED", "contingent"),
    case("cond-conditioned-upon-01", ["J_contingent", "midclause"], "liability",
         "12. Limitation of Liability. The cap stated in this Section is conditioned upon Customer's "
         "timely payment of all undisputed invoices.",
         "ESTABLISHED", "contingent"),
]

# ===========================================================================
# K. SO LONG AS / AS LONG AS
# ===========================================================================
CASES += [
    case("cond-so-long-as-01", ["K_so_long_as", "trailing"], "indemnification",
         "12. Indemnification. Vendor shall indemnify Customer for third-party claims arising from "
         "Vendor's breach, so long as Customer notifies Vendor within thirty (30) days of becoming "
         "aware of the claim.",
         "ESTABLISHED", "so_long_as"),
    case("cond-as-long-as-01", ["K_so_long_as", "trailing"], "payment_terms",
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of invoice, as "
         "long as Vendor's invoice is accompanied by supporting documentation.",
         "ESTABLISHED", "so_long_as"),
]

# ===========================================================================
# L. UNTIL / DURING / AFTER / BEFORE (temporal changes to applicability)
# ===========================================================================
CASES += [
    case("cond-temporal-not-until-01", ["L_temporal"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of this Agreement. This "
         "indemnification obligation shall not apply until Customer has exhausted its available "
         "insurance coverage for the claim.",
         "ESTABLISHED", "temporal"),
    case("cond-temporal-only-after-01", ["L_temporal"], "liability",
         "12. Limitation of Liability. The liability cap stated in this Section shall apply only "
         "after the parties have completed the escalation procedure described in Section 20.",
         "ESTABLISHED", "temporal"),
    case("cond-temporal-during-term-negative-01", ["L_temporal", "negative"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of this Agreement during the "
         "Term.",
         "UNCONDITIONAL", None,
         notes="Negative control -- ordinary 'during the Term' duration language is ambient scope, "
               "not a material applicability condition; must not be flagged as conditional."),
]

# ===========================================================================
# M. COMPOUND CONDITIONS
# ===========================================================================
CASES += [
    case("cond-compound-if-and-01", ["M_compound"], "indemnification",
         "12. Indemnification. If a third party asserts a claim against Customer and such claim "
         "arises from Vendor's gross negligence, Vendor shall indemnify Customer for the resulting "
         "damages.",
         "ESTABLISHED", "if_when"),
    case("cond-compound-if-unless-01", ["M_compound"], "indemnification",
         "12. Indemnification. If a third party asserts an IP infringement claim against Customer, "
         "Vendor shall indemnify Customer, unless the claim arises from Customer's unauthorized "
         "modification of the Licensed Software.",
         "ESTABLISHED", "if_when",
         notes="Compound leading-IF plus trailing-UNLESS on the same obligation -- both are real "
               "conditions on the same fact; the mechanism only needs to detect at least one and "
               "must not silently drop the fact into 'unconditional.'"),
    case("cond-compound-provided-except-01", ["M_compound"], "liability",
         "12. Limitation of Liability. Vendor's aggregate liability shall not exceed $1,000,000, "
         "provided that this cap applies to claims arising under this Agreement, except where "
         "applicable law prohibits limitation of liability for gross negligence.",
         "ESTABLISHED", "provided_that"),
]

# ===========================================================================
# N. CONDITIONS LOCATED IN ANOTHER SENTENCE
# ===========================================================================
CASES += [
    case("cond-backref-another-sentence-01", ["N_backref"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's infringement of intellectual "
         "property rights. This indemnification obligation does not apply if Customer has modified "
         "the Licensed Software without Vendor's prior written consent.",
         "ESTABLISHED", "backref",
         notes="The condition sits in the sentence AFTER the obligation sentence but explicitly "
               "refers back to 'this indemnification obligation.'"),
    case("cond-backref-another-sentence-02", ["N_backref"], "liability",
         "12. Limitation of Liability. Vendor's aggregate liability shall not exceed 2 times the "
         "total annual fees paid. The foregoing limitation shall not apply to claims arising from "
         "Vendor's breach of its confidentiality obligations.",
         "ESTABLISHED", "backref"),
]

# ===========================================================================
# O. CONDITIONS LOCATED IN A REFERENCED SECTION (exercises the Phase 1
#    cross-reference mechanism: SOURCE -> REFERENCE -> TARGET -> CONDITION ->
#    MATERIAL FACT)
# ===========================================================================
CASES += [
    case("cond-xref-target-condition-01", ["O_xref_condition"], "indemnification",
         "9. Limitation of Liability. In no event shall liability exceed $500,000. The foregoing "
         "limitation applies only to third-party claims arising under this Agreement.\n\n"
         "12. Indemnification. Vendor shall indemnify Customer, subject to the limitations in "
         "Section 9.",
         "ESTABLISHED", "cross_reference_condition",
         notes="Required chain: SOURCE -> REFERENCE -> TARGET -> CONDITION -> MATERIAL FACT. "
               "Section 9's own text conditions the $500,000 value -- the resolved fact must carry "
               "that condition, not silently drop it."),
    case("cond-xref-missing-target-01", ["O_xref_condition", "negative"], "indemnification",
         "12. Indemnification. Vendor shall indemnify Customer, subject to the limitations in "
         "Section 42.",
         "NOT_ESTABLISHED", None,
         notes="Target absent -- chain breaks at TARGET, must fail closed (this is scored by the "
               "Phase 1 mechanism already; included here as a Phase 2 boundary re-check)."),
    case("cond-xref-wrong-target-01", ["O_xref_condition", "negative"], "indemnification",
         "9. Insurance. Vendor shall maintain commercial general liability insurance with limits of "
         "$1,000,000, applicable only to bodily injury claims.\n\n"
         "12. Indemnification. Vendor shall indemnify Customer, subject to the limitations in "
         "Section 9.",
         "NOT_ESTABLISHED", None,
         notes="Target resolves but governs an unrelated concept (insurance) -- must not adopt "
               "either its value or its condition."),
    case("cond-xref-conflicting-target-01", ["O_xref_condition", "negative"], "indemnification",
         "9. Limitation of Liability. Liability shall not exceed $500,000.\n\n"
         "Restated elsewhere in the document:\n\n"
         "9. Limitation of Liability. Liability shall not exceed $2,000,000, and this limitation "
         "applies only to claims arising after the Effective Date.\n\n"
         "12. Indemnification. Vendor shall indemnify Customer, subject to the limitations in "
         "Section 9.",
         "NOT_ESTABLISHED", None,
         notes="Ambiguous target (two distinct Section 9 headings) -- must not guess which "
               "condition or value applies."),
    case("cond-xref-multiple-referenced-sections-01", ["O_xref_condition"], "indemnification",
         "9. Limitation of Liability. Liability shall not exceed $500,000. This limitation applies "
         "only to claims arising from ordinary breach.\n\n"
         "14. Insurance. Insurance limits are $1,000,000.\n\n"
         "12. Indemnification. Vendor shall indemnify Customer, subject to the limitation of "
         "liability set forth in Section 9, without regard to the insurance limits referenced in "
         "Section 14.",
         "ESTABLISHED", "cross_reference_condition",
         notes="The FIRST (earliest) reference governs, consistent with Phase 1's own "
               "'closest stated position wins' rule -- Section 9's condition attaches, Section 14 is "
               "irrelevant."),
]

# ===========================================================================
# NEGATIVE CONTROLS -- condition-like language present, but the material
# fact must NOT be treated as conditional, or the condition does NOT
# attach to the extracted fact. Tests CONDITION OWNERSHIP, not merely
# condition-word detection.
# ===========================================================================
CASES += [
    case("cond-neg-if-in-example-01", ["negative", "example"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of this Agreement. For "
         "example, if a customer of Customer's sues Customer over a defect in the Licensed "
         "Software, Vendor would owe indemnification.",
         "UNCONDITIONAL", None,
         notes="The 'if' clause is an illustrative example following the real obligation sentence, "
               "not a condition on it -- the obligation sentence itself is unconditional."),
    case("cond-neg-when-timing-only-01", ["negative", "timing"], "payment_terms",
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of invoice. "
         "Invoices are issued when Deliverables are accepted.",
         "UNCONDITIONAL", None,
         notes="'when' here describes invoice TIMING, an unrelated fact, not a condition on the "
               "Net 30 payment obligation."),
    case("cond-neg-subject-noun-01", ["negative", "subject_noun"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of this Agreement. The "
         "subject of any such claim shall be documented in writing.",
         "UNCONDITIONAL", None,
         notes="'subject' used as a noun ('the subject of...'), not the connector 'subject to' -- "
               "must not be matched as a condition at all."),
    case("cond-neg-provided-supplied-01", ["negative", "provided_verb"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from defects in materials provided by Vendor under "
         "this Agreement.",
         "UNCONDITIONAL", None,
         notes="'provided by' is the verb 'to provide' (supplied), not 'provided that' -- must not "
               "be matched as a condition connector."),
    case("cond-neg-except-unrelated-01", ["negative", "except_unrelated"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of this Agreement. Except for "
         "Exhibit A, this Agreement contains the entire understanding of the parties.",
         "UNCONDITIONAL", None,
         notes="'Except for Exhibit A' modifies the entire-agreement/merger clause, an unrelated "
               "sentence, not the indemnification obligation."),
    case("cond-neg-condition-other-obligation-01", ["negative", "wrong_obligation"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of this Agreement. Customer "
         "shall indemnify Vendor for claims arising from Customer's misuse of the Services, "
         "provided that Customer's misuse was not authorized by Vendor.",
         "UNCONDITIONAL", None,
         notes="The trailing proviso belongs to CUSTOMER's obligation (the second sentence), not "
               "Vendor's (the first) -- scored against Vendor's obligation, which is unconditional."),
    case("cond-neg-condition-other-party-01", ["negative", "wrong_party"], "liability",
         "12. Limitation of Liability. Vendor's aggregate liability shall not exceed $500,000. "
         "Customer's aggregate liability shall not exceed $500,000, provided that Customer's breach "
         "was not intentional.",
         "UNCONDITIONAL", None,
         notes="The proviso conditions CUSTOMER's cap, not Vendor's -- Vendor's own $500,000 figure "
               "is unconditional and must not inherit Customer's condition."),
    case("cond-neg-nonoperative-heading-01", ["negative", "heading"], "indemnification",
         "12. IF APPLICABLE: SPECIAL INDEMNIFICATION TERMS\n\n"
         "Vendor shall indemnify, defend, and hold harmless Customer from and against any "
         "third-party claims arising from Vendor's breach of this Agreement.",
         "UNCONDITIONAL", None,
         notes="'IF APPLICABLE' is part of a section heading, not an operative conditional clause "
               "governing the obligation sentence below it."),
    case("cond-neg-quoted-example-01", ["negative", "quoted"], "indemnification",
         "This Agreement's indemnification clause is intended to read: \"If Vendor breaches this "
         "Agreement, Vendor shall indemnify Customer.\" That sentence does not actually appear "
         "anywhere in this document. 12. Indemnification. Vendor shall indemnify, defend, and hold "
         "harmless Customer from and against any third-party claims arising from Vendor's breach of "
         "this Agreement.",
         "UNCONDITIONAL", None,
         notes="The quoted/negated example must not attach its own 'If' clause to the real, "
               "separate, unconditional obligation stated afterward -- reuses the protected "
               "is_operative_context boundary from Step 4A.10.x."),
    case("cond-neg-upon-execution-ambient-01", ["negative", "upon_ambient"], "payment_terms",
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of invoice. "
         "This Agreement is effective upon execution by both parties.",
         "UNCONDITIONAL", None,
         notes="'upon execution' describes contract effectiveness generally, an unrelated ambient "
               "fact, not a condition on the payment obligation."),
    case("cond-neg-where-located-01", ["negative", "where_locative"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of this Agreement, where such "
         "claims are brought in a court located in the state where Customer maintains its principal "
         "place of business.",
         "UNCONDITIONAL", None,
         notes="'where' here is locative (describes a court's location), not the conditional "
               "'where applicable' family -- must not be matched as a condition connector."),
]

# ===========================================================================
# CONFLICTING -- incompatible conditions from different operative provisions
# ===========================================================================
CASES += [
    case("cond-conflicting-provisions-01", ["conflicting"], "indemnification",
         "9. Special Terms. Vendor's indemnification obligation under Section 12 shall apply only "
         "to claims arising after the Effective Date.\n\n"
         "15. Additional Terms. Vendor's indemnification obligation under Section 12 shall apply "
         "only to claims arising before the Effective Date.\n\n"
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of this Agreement.",
         "CONFLICTING", None,
         notes="Two separately operative provisions impose directly incompatible temporal "
               "conditions on the same obligation -- cannot be deterministically reconciled; must "
               "not silently pick one."),
]

# ===========================================================================
# ADDITIONAL PAYMENT_TERMS AND LIABILITY COVERAGE (breadth across adapters)
# ===========================================================================
CASES += [
    case("cond-payment-unless-01", ["B_unless"], "payment_terms",
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of invoice, "
         "unless Customer disputes the invoice in good faith within fifteen (15) days of receipt.",
         "ESTABLISHED", "unless"),
    case("cond-payment-to-the-extent-01", ["E_to_the_extent"], "payment_terms",
         "9. Payment Terms. Customer shall pay late fees of 1.5% per month on overdue amounts, to "
         "the extent such amounts remain undisputed.",
         "ESTABLISHED", "to_the_extent"),
    case("cond-liability-only-if-01", ["D_only_if"], "liability",
         "12. Limitation of Liability. The liability cap of $1,000,000 stated in this Section shall "
         "apply only if Vendor maintains the insurance coverage required under Section 14.",
         "ESTABLISHED", "only_if"),
    case("cond-liability-unconditional-negative-01", ["negative"], "liability",
         "12. Limitation of Liability. In no event shall either party's aggregate liability under "
         "this Agreement exceed 2 times the total annual fees paid in the twelve (12) months "
         "preceding the claim.",
         "UNCONDITIONAL", None,
         notes="Plain, ordinary clean cap with no conditional language at all -- baseline negative "
               "control confirming the mechanism doesn't manufacture conditions out of nothing."),
    case("cond-payment-unconditional-negative-01", ["negative"], "payment_terms",
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of invoice.",
         "UNCONDITIONAL", None),
    case("cond-indemnification-unconditional-negative-01", ["negative"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of this Agreement.",
         "UNCONDITIONAL", None),
]

# ===========================================================================
# COMPOUND: negation/override interaction with conditional language (must
# not be confused with the Phase 1 negation/override guard, which concerns
# cross-reference DELEGATION, not applicability conditions)
# ===========================================================================
CASES += [
    case("cond-compound-negation-not-a-condition-01", ["compound", "negation"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of this Agreement. This "
         "obligation is not subject to any condition precedent.",
         "UNCONDITIONAL", None,
         notes="Explicitly NEGATES the existence of any condition -- the mechanism must not "
               "manufacture a condition out of the word 'condition' appearing in a sentence that "
               "denies one exists."),
    case("cond-compound-notwithstanding-plus-if-01", ["compound", "override"], "liability",
         "9. Limitation of Liability. Liability shall not exceed $500,000.\n\n"
         "12. Indemnification. Notwithstanding the limitation of liability set forth in Section 9, "
         "if a claim arises from Vendor's willful misconduct, Vendor's indemnification obligations "
         "shall not exceed 3 times the total annual fees paid.",
         "ESTABLISHED", "if_when",
         notes="Combines the Phase 1 'notwithstanding' override (own 3x value governs, not "
               "Section 9's $500,000) with a genuine Phase 2 leading-IF condition on that same "
               "3x value -- both mechanisms must cooperate correctly."),
]

# ===========================================================================
# ADDITIONAL BREADTH -- more NOT_ESTABLISHED/CONFLICTING coverage (thin
# above), and remaining condition families H/I/J/K/L represented in
# liability and payment_terms, not just indemnification.
# ===========================================================================
CASES += [
    case("cond-not-established-ambiguous-scope-01", ["not_established", "ambiguous"], "indemnification",
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims. Certain conditions set forth elsewhere in this Agreement "
         "may apply.",
         "NOT_ESTABLISHED", None,
         notes="Explicitly signals a condition exists ('certain conditions... may apply') without "
               "identifying it -- attachment/scope cannot be established; must not be treated as "
               "either unconditional or as a resolvable condition."),
    case("cond-not-established-vague-backref-01", ["not_established", "ambiguous"], "liability",
         "12. Limitation of Liability. Vendor's aggregate liability shall not exceed $500,000. "
         "Certain limitations described elsewhere in this Agreement may further restrict this cap.",
         "NOT_ESTABLISHED", None,
         notes="Vague forward-pointing reference with no locatable target and no specific "
               "condition text -- fails closed rather than guessing."),
    case("cond-conflicting-monetary-and-condition-01", ["conflicting"], "liability",
         "9. Special Terms. The liability cap in Section 12 applies only to claims filed within one "
         "year of the Effective Date.\n\n"
         "16. Additional Terms. The liability cap in Section 12 applies only to claims filed within "
         "two years of the Effective Date.\n\n"
         "12. Limitation of Liability. Vendor's aggregate liability shall not exceed $500,000.",
         "CONFLICTING", None,
         notes="Two separately operative provisions state incompatible temporal conditions on the "
               "same cap -- cannot be deterministically reconciled."),
    case("cond-liability-upon-01", ["H_upon"], "liability",
         "12. Limitation of Liability. Upon a final, non-appealable judgment establishing Vendor's "
         "gross negligence, the liability cap stated in this Section shall not apply.",
         "ESTABLISHED", "upon"),
    case("cond-payment-upon-01", ["H_upon"], "payment_terms",
         "9. Payment Terms. Upon Vendor's material breach of this Agreement, Customer's obligation "
         "to pay any then-outstanding invoices shall be suspended pending cure.",
         "ESTABLISHED", "upon"),
    case("cond-liability-where-applicable-01", ["I_where"], "liability",
         "12. Limitation of Liability. Vendor's aggregate liability shall not exceed $1,000,000, "
         "where applicable law does not mandate a higher cap.",
         "ESTABLISHED", "where_applicable"),
    case("cond-payment-contingent-01", ["J_contingent"], "payment_terms",
         "9. Payment Terms. Customer's obligation to pay the final milestone invoice is contingent "
         "on Vendor's delivery of the signed acceptance certificate.",
         "ESTABLISHED", "contingent"),
    case("cond-payment-so-long-as-01", ["K_so_long_as"], "payment_terms",
         "9. Payment Terms. Customer shall continue to pay the recurring subscription fee so long as "
         "Vendor maintains the Service Level Agreement uptime commitment.",
         "ESTABLISHED", "so_long_as"),
    case("cond-liability-temporal-until-01", ["L_temporal"], "liability",
         "12. Limitation of Liability. The uncapped liability exception for data breaches stated in "
         "this Section shall not apply until the Vendor has been notified in writing of the breach.",
         "ESTABLISHED", "temporal"),
    case("cond-neg-during-payment-ambient-01", ["negative", "temporal_ambient"], "payment_terms",
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of invoice "
         "during the Term of this Agreement.",
         "UNCONDITIONAL", None,
         notes="'during the Term' is ordinary ambient scope language, not a material applicability "
               "condition on the Net 30 obligation."),
]
