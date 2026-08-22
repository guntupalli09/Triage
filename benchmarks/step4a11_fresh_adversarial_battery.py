"""Step 4A.11 Phase 4 — fresh adversarial DEVELOPMENT battery.

Genuinely fresh cases (not copied, not lightly paraphrased, not built
from the Phase 1/2/3 DEV benchmarks or the Step 4A.10 corpus), authored
from the underlying contractual concepts using vocabulary and drafting
structures deliberately different from the implementation work where
practical. This is DEVELOPMENT evidence — defects found here may be
fixed; it is NOT the final Step 4A.11 authoritative corpus, is never
locked, and will not be reused as one.

Ground truth is predeclared below, before execution. Where an
after-the-fact correction to an expected value was needed (a benchmark-
authoring mistake, not a production defect), it is marked GTD (ground-
truth-defect) in the case's own notes, exactly as required.

Schema:
  id, adapter ("indemnification"|"liability"|"payment_terms"),
  attack_families (list of "AF1".."AF10" tags), text,
  expected_status in {"ESTABLISHED","NOT_ESTABLISHED","CONFLICTING"} --
      the CORE safety-relevant classification: did a material fact get
      correctly established (with correct owner/value/qualifier), or
      correctly NOT established / correctly flagged conflicting.
  expected (adapter-specific dict, only scored when expected_status ==
      "ESTABLISHED"):
    indemnification: {"actor": ..., "beneficiary": ...}
    liability: {"kind": ..., "multiplier": ...} or {"kind": ..., "fixed_amount": ...}
                or {"kind": "unlimited"} -- general cap only
    payment_terms: {"net_days": ...} or {"late_fee_rate_percent": ...} etc.
        -- whichever single dimension the case targets (declared per case
        via expected_dimension)
  expected_condition in {None, "ESTABLISHED", "NOT_ESTABLISHED", "CONFLICTING"}
      -- only scored when the case specifically targets AF3 (conditional
      applicability); None means "not scored for this case."
  notes.
"""

from typing import Any, Dict, List, Optional


def case(id: str, adapter: str, attack_families: List[str], text: str, expected_status: str,
         expected: Optional[Dict[str, Any]] = None, expected_dimension: Optional[str] = None,
         expected_condition: Optional[str] = None, notes: str = "") -> Dict[str, Any]:
    return {
        "id": id, "adapter": adapter, "attack_families": attack_families, "text": text,
        "expected_status": expected_status, "expected": expected or {},
        "expected_dimension": expected_dimension, "expected_condition": expected_condition,
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# ===========================================================================
# INDEMNIFICATION — AF1 structural proposition generalization
# ===========================================================================
CASES += [
    case("fab-ind-af1-nominalized-01", "indemnification", ["AF1"],
         "12. Risk Allocation. Losses incurred by Buyer arising from Seller's breach of the "
         "product-quality warranty are Seller's responsibility, and Seller shall bear them in full.",
         "NOT_ESTABLISHED", notes="Nominalized framing ('are Seller's responsibility') followed by "
         "a vague 'bear them in full' -- no directional verb structure this mechanism recognizes; a "
         "genuinely hard, ambiguous case, correctly left for review."),
    case("fab-ind-af1-embedded-relative-01", "indemnification", ["AF1"],
         "12. Indemnification. Buyer, which is a wholly owned subsidiary of Buyer Holdings Inc., "
         "shall indemnify Seller for any claim that a regulator brings against Seller relating to "
         "Buyer's noncompliance with import regulations.",
         "ESTABLISHED", {"actor": "Buyer", "beneficiary": "Seller"},
         notes="Embedded relative clause describing the subject ('which is a wholly owned "
               "subsidiary...') between the role and the verb."),
    case("fab-ind-af1-coordinated-predicate-01", "indemnification", ["AF1"],
         "12. Indemnification. Distributor shall investigate, defend, and indemnify Principal "
         "against any consumer complaint arising from Distributor's mislabeling of the goods.",
         "ESTABLISHED", {"actor": "Distributor", "beneficiary": "Principal"},
         notes="Three coordinated predicate verbs before the object -- 'investigate, defend, and "
               "indemnify' -- not just 'defend and indemnify.'"),
    case("fab-ind-af1-coordinated-object-01", "indemnification", ["AF1"],
         "12. Indemnification. Manufacturer shall indemnify and hold harmless both Retailer and "
         "Retailer's officers from any product-liability claim arising from a manufacturing defect.",
         "ESTABLISHED", {"actor": "Manufacturer", "beneficiary": "Retailer"},
         notes="Coordinated object ('both Retailer and Retailer's officers') -- the mechanism "
               "should extract the primary named role, Retailer, without choking on the compound "
               "object; scored against the primary beneficiary only."),
    case("fab-ind-af1-shared-subject-01", "indemnification", ["AF1"],
         "12. Indemnification. Escrow Agent shall defend Depositor against, and shall indemnify "
         "Depositor for, any claim arising from Escrow Agent's mishandling of escrowed funds.",
         "ESTABLISHED", {"actor": "Escrow Agent", "beneficiary": "Depositor"},
         notes="Shared subject across two coordinated clauses ('shall defend..., and shall "
               "indemnify...') separated by a comma, each independently naming the beneficiary."),
    case("fab-ind-af1-split-subject-negative-01", "indemnification", ["AF1", "AF6"],
         "12. Indemnification. Guarantor and its parent company shall indemnify Beneficiary for any "
         "claim arising from a payment default under the guaranteed obligations.",
         "NOT_ESTABLISHED", notes="Genuinely compound/split subject ('Guarantor and its parent "
         "company') -- fails closed rather than silently picking 'company' alone as the actor."),
    case("fab-ind-af1-enumerated-list-01", "indemnification", ["AF1"],
         "12. Indemnification. Franchisee shall indemnify Franchisor against claims arising from: "
         "(a) Franchisee's violation of the brand standards manual; (b) Franchisee's failure to "
         "maintain required licenses; or (c) Franchisee's misuse of the Franchisor's trademarks.",
         "ESTABLISHED", {"actor": "Franchisee", "beneficiary": "Franchisor"},
         notes="Enumerated sub-clause list of trigger categories after the operative sentence -- "
               "the obligation itself is complete before the colon."),
    case("fab-ind-af1-semicolon-01", "indemnification", ["AF1"],
         "12. Indemnification. Underwriter shall indemnify Issuer for losses arising from a "
         "material misstatement in the offering documents; the foregoing obligation extends to "
         "reasonable attorneys' fees.",
         "ESTABLISHED", {"actor": "Underwriter", "beneficiary": "Issuer"},
         notes="Semicolon-joined follow-on clause describing scope, not a separate obligation."),
    case("fab-ind-af1-parenthetical-01", "indemnification", ["AF1"],
         "12. Indemnification. Charterer (as defined in the recitals) shall indemnify Owner for any "
         "claim arising from cargo damage occurring during the charter period.",
         "ESTABLISHED", {"actor": "Charterer", "beneficiary": "Owner"},
         notes="Parenthetical definitional aside immediately after the subject."),
    case("fab-ind-af1-defined-role-alias-01", "indemnification", ["AF1", "AF7"],
         "This Master Services Agreement is between Northbridge Analytics Inc. (\"Consultant\") and "
         "Fjordline Capital Partners (\"Client\"). 12. Indemnification. Consultant shall indemnify "
         "Client for any claim arising from Consultant's professional negligence.",
         "ESTABLISHED", {"actor": "Consultant", "beneficiary": "Client"},
         notes="Alias/defined-term roles introduced earlier in the document, used bare afterward."),
    case("fab-ind-af1-grammatical-inversion-01", "indemnification", ["AF1"],
         "12. Indemnification. Against any claim arising from a data-security incident, Custodian "
         "shall indemnify Depositor.",
         "ESTABLISHED", {"actor": "Custodian", "beneficiary": "Depositor"},
         notes="Fronted prepositional phrase ('Against any claim...') before the subject -- unusual "
               "but grammatical inversion; if the mechanism can't parse this shape it should "
               "correctly fall back to NOT_ESTABLISHED rather than guess."),
    case("fab-ind-af1-table-like-01", "indemnification", ["AF1"],
         "12. Indemnification Matrix.\nTrigger: IP infringement | Obligor: Licensor | Beneficiary: "
         "Licensee | Cap: 2x fees.\nTrigger: data breach | Obligor: Licensee | Beneficiary: "
         "Licensor | Cap: uncapped.",
         "NOT_ESTABLISHED", notes="Table-like drafting with no operative sentence structure at "
         "all -- correctly outside this mechanism's scope, a genuinely different representation "
         "problem, safely routed to review rather than guessed at."),
]

# ===========================================================================
# INDEMNIFICATION — AF2 object/ownership
# ===========================================================================
CASES += [
    case("fab-ind-af2-bystander-01", "indemnification", ["AF2"],
         "12. Indemnification. Anchor Tenant shall indemnify Mall Operator for any claim arising "
         "from Anchor Tenant's breach, without regard to any position taken by Co-Tenant in a "
         "related dispute.",
         "ESTABLISHED", {"actor": "Anchor Tenant", "beneficiary": "Mall Operator"},
         notes="A third, bystander role (Co-Tenant) mentioned but not a party to this obligation."),
    case("fab-ind-af2-two-obligations-one-sentence-01", "indemnification", ["AF2"],
         "12. Indemnification. Landlord shall indemnify Tenant against IP-infringement claims "
         "involving the building systems, while Tenant shall indemnify Landlord against claims "
         "stemming from Tenant's unauthorized alterations to the premises.",
         "ESTABLISHED", {"actor": "Landlord", "beneficiary": "Tenant"},
         notes="Two directional obligations in one sentence -- scores the first."),
    case("fab-ind-af2-insurance-adjacent-cap-01", "indemnification", ["AF2"],
         "9. Insurance. Carrier shall maintain cargo insurance of $2,000,000 per occurrence.\n\n"
         "12. Indemnification. Carrier shall indemnify Shipper, as limited by the ceiling "
         "described in Section 10.\n\n10. Limitation of Liability. Aggregate liability shall not "
         "exceed $600,000.",
         "ESTABLISHED", {"actor": "Carrier", "beneficiary": "Shipper"},
         notes="An insurance figure sits adjacent to the real cross-referenced cap (Section 10) -- "
               "the resolver must not adopt the insurance figure just because it appears nearby; "
               "this case scores the OBLIGATION establishment, not the resolved value."),
    case("fab-ind-af2-sla-credit-adjacent-01", "indemnification", ["AF2"],
         "9. Service Levels. Service credits for downtime are capped at $30,000 in any month.\n\n"
         "12. Indemnification. Servicer shall indemnify Bank, as described in Section 9's cap.",
         "ESTABLISHED", {"actor": "Servicer", "beneficiary": "Bank"},
         notes="Cross-reference target is an SLA service-credit provision, not a liability cap -- "
               "the resolver should fail closed on the VALUE while the OBLIGATION itself still "
               "establishes."),
]

# ===========================================================================
# INDEMNIFICATION — AF3 conditional applicability (fresh combinations)
# ===========================================================================
CASES += [
    case("fab-ind-af3-nested-condition-01", "indemnification", ["AF3"],
         "12. Indemnification. If a regulator initiates an enforcement action, and if that action "
         "names Distributor individually, Manufacturer shall indemnify Distributor for the "
         "resulting defense costs.",
         "ESTABLISHED", {"actor": "Manufacturer", "beneficiary": "Distributor"},
         expected_condition="ESTABLISHED",
         notes="Nested (compound) leading conditions -- two 'if' clauses stacked before the main "
               "clause."),
    case("fab-ind-af3-condition-plus-exception-01", "indemnification", ["AF3"],
         "12. Indemnification. If a claim arises from a defect in the goods, Supplier shall "
         "indemnify Buyer for the resulting loss, except where Buyer altered the goods after "
         "delivery.",
         "ESTABLISHED", {"actor": "Supplier", "beneficiary": "Buyer"},
         expected_condition="ESTABLISHED",
         notes="Leading condition AND trailing exception on the same obligation."),
    case("fab-ind-af3-condition-prior-sentence-01", "indemnification", ["AF3"],
         "A claim may arise from a title defect discovered after closing. In that event, Seller "
         "shall indemnify Buyer for the resulting loss of value.",
         "ESTABLISHED", {"actor": "Seller", "beneficiary": "Buyer"},
         expected_condition="NOT_ESTABLISHED",
         notes="The triggering event is described in the sentence BEFORE the obligation, "
               "referenced only by 'In that event' -- this is genuinely harder anaphora than the "
               "backref family Phase 2 already handles (which requires the FOLLOWING sentence to "
               "name the fact explicitly); correctly not established as a Phase 2 condition, "
               "though the obligation itself still establishes."),
    case("fab-ind-af3-condition-one-of-coordinated-01", "indemnification", ["AF3"],
         "12. Indemnification. Vendor shall indemnify Customer for claims arising from IP "
         "infringement. Vendor shall also indemnify Customer for claims arising from a data "
         "breach, but only if Vendor was independently notified of the vulnerability at least 30 "
         "days before the breach occurred.",
         "ESTABLISHED", {"actor": "Vendor", "beneficiary": "Customer"},
         notes="Two separate obligations (not truly coordinated in one clause); scores the FIRST, "
               "which is genuinely unconditional -- the condition belongs only to the second, "
               "separate sentence."),
    case("fab-ind-af3-payment-triggered-by-event-01", "payment_terms", ["AF3"],
         "9. Payment Terms. Upon Customer's receipt of a signed change order, Customer shall pay "
         "Vendor the additional fees specified in that change order within Net 15 days.",
         "ESTABLISHED", expected_condition="ESTABLISHED",
         notes="Payment obligation triggered by a specific event (change order receipt)."),
    case("fab-ind-af3-contingent-cap-01", "liability", ["AF3"],
         "12. Limitation of Liability. Provider's aggregate liability is capped at $2,000,000, "
         "contingent on Provider maintaining continuous cyber-liability insurance coverage "
         "throughout the Term.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 2000000.0}, expected_dimension="general_cap",
         expected_condition="ESTABLISHED"),
    case("fab-ind-af3-condition-one-party-01", "liability", ["AF3"],
         "12. Limitation of Liability. Distributor's aggregate liability is limited to $500,000. "
         "Brand Owner's aggregate liability is separately limited to $500,000, but only for claims "
         "Brand Owner brings within one year of accrual.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 500000.0}, expected_dimension="general_cap",
         expected_condition=None,
         notes="The trailing condition belongs to CUSTOMER's separately-stated cap -- this case "
               "scores the OVERALL general_cap value the engine resolves (its own single-cap model "
               "reconciles the clause, so condition scoring is intentionally skipped here -- "
               "boundary already disclosed in the Phase 2 checkpoint)."),
]

# ===========================================================================
# INDEMNIFICATION — AF4 cross-reference resolution (unseen structures)
# ===========================================================================
CASES += [
    case("fab-ind-af4-chained-unseen-01", "indemnification", ["AF4"],
         "9. Liability Terms. The applicable ceiling is as described in Schedule B.\n\n"
         "12. Indemnification. Contractor shall indemnify Owner, pursuant to the terms described "
         "in Section 9.",
         "ESTABLISHED", {"actor": "Contractor", "beneficiary": "Owner"},
         notes="Chained reference (Section 9 -> Schedule B, unfollowed) -- obligation establishes, "
               "value resolution must fail closed (not separately scored here)."),
    case("fab-ind-af4-schedule-to-exhibit-01", "indemnification", ["AF4"],
         "Schedule 4. See Exhibit C for the applicable indemnification cap.\n\n"
         "Exhibit C. The cap is capped at $900,000.\n\n"
         "12. Indemnification. Licensee shall indemnify Licensor, in accordance with the amount "
         "described in Schedule 4.",
         "ESTABLISHED", {"actor": "Licensee", "beneficiary": "Licensor"},
         notes="A second-level chain (Schedule 4 -> Exhibit C) -- the resolver only follows ONE "
               "hop, so this should fail closed on VALUE while the obligation itself establishes."),
    case("fab-ind-af4-amendment-replacing-target-01", "indemnification", ["AF4"],
         "9. Limitation of Liability. Aggregate liability shall not exceed $400,000.\n\n"
         "Amendment No. 3 hereby replaces Section 9 in its entirety: aggregate liability shall not "
         "exceed $1,100,000.\n\n"
         "12. Indemnification. Franchisee shall indemnify Franchisor, as limited by the cap "
         "described in Section 9.",
         "ESTABLISHED", {"actor": "Franchisee", "beneficiary": "Franchisor"},
         notes="An amendment purports to replace Section 9's text inline rather than via a real "
               "second heading -- the resolver should find only the original Section 9 heading "
               "(the amendment text has no genuine 'Section 9' heading of its own), which is a "
               "known, disclosed boundary (amendments not specially parsed); obligation still "
               "establishes."),
    case("fab-ind-af4-stale-reference-01", "indemnification", ["AF4"],
         "12. Indemnification. Distributor shall indemnify Brand Owner, as specified in the "
         "Statement of Work governing the applicable cap.",
         "ESTABLISHED", {"actor": "Distributor", "beneficiary": "Brand Owner"},
         notes="Reference target is an external document (Statement of Work) never included in "
               "this text -- must fail closed on VALUE (NOT_FOUND), obligation still establishes."),
    case("fab-ind-af4-wrong-number-nearby-01", "indemnification", ["AF4"],
         "9. Limitation of Liability. Liability shall not exceed $700,000.\n\n"
         "14. Term. This Agreement has an initial term of 9 years.\n\n"
         "12. Indemnification. Underwriter shall indemnify Issuer, pursuant to the cap in Section "
         "9.",
         "ESTABLISHED", {"actor": "Underwriter", "beneficiary": "Issuer"},
         notes="A distractor '9 years' numeral sits in an unrelated Section 14 -- must not be "
               "mistaken for a second 'Section 9' heading."),
    case("fab-ind-af4-conditional-value-in-target-01", "indemnification", ["AF4"],
         "9. Limitation of Liability. Aggregate liability shall not exceed $800,000, but only for "
         "claims filed within eighteen months of the Effective Date.\n\n"
         "12. Indemnification. Reseller shall indemnify Manufacturer, as described in Section 9's "
         "cap.",
         "ESTABLISHED", {"actor": "Reseller", "beneficiary": "Manufacturer"},
         notes="The target division's own value is itself conditional -- Phase 1+2 interaction: "
               "the resolved value should carry the condition, not silently drop it."),
]

# ===========================================================================
# INDEMNIFICATION — AF6 false structural establishment (hard negatives)
# ===========================================================================
CASES += [
    case("fab-ind-af6-drafting-instruction-01", "indemnification", ["AF6"],
         "[DRAFTING NOTE: insert standard mutual indemnification language here, e.g. 'Vendor shall "
         "indemnify Customer for IP claims.']",
         "NOT_ESTABLISHED", notes="Bracketed drafting instruction, not the document's own text."),
    case("fab-ind-af6-negotiation-commentary-01", "indemnification", ["AF6"],
         "Counsel comment: Customer proposed that Vendor shall indemnify Customer for all claims; "
         "Vendor's counsel has not yet responded to this proposal.",
         "NOT_ESTABLISHED", notes="Negotiation commentary describing an unaccepted proposal."),
    case("fab-ind-af6-superseded-01", "indemnification", ["AF6"],
         "Original Section 12 (no longer in effect): Vendor shall indemnify Customer for any "
         "claim. The parties replaced this Section in its entirety via Amendment No. 1, which "
         "instead provides for mutual limitation of liability with no indemnification obligation.",
         "NOT_ESTABLISHED", notes="Explicitly labeled 'no longer in effect' and replaced."),
    case("fab-ind-af6-recital-01", "indemnification", ["AF6"],
         "RECITALS. WHEREAS the parties wish to allocate risk such that Vendor would indemnify "
         "Customer for certain claims, the parties enter into this Agreement on the terms below.",
         "NOT_ESTABLISHED", notes="Recital expressing aspiration/intent, not an operative promise."),
    case("fab-ind-af6-definition-01", "indemnification", ["AF6"],
         "\"Indemnifiable Loss\" means any loss, cost, or expense that a party would be entitled to "
         "recover under an indemnification obligation, if one exists under this Agreement.",
         "NOT_ESTABLISHED", notes="Definitions-section sentence describing a defined TERM, "
         "conditioned on an obligation existing elsewhere -- does not itself create one."),
    case("fab-ind-af6-heading-01", "indemnification", ["AF6"],
         "ARTICLE 12 — VENDOR SHALL INDEMNIFY CUSTOMER FOR IP CLAIMS\n\nThe parties acknowledge "
         "the risk-allocation framework described in this Article.",
         "NOT_ESTABLISHED", notes="All-caps article title stating the concept; the body text never "
         "actually restates it as an operative sentence."),
    case("fab-ind-af6-explanatory-parenthetical-01", "indemnification", ["AF6"],
         "12. Indemnification. (This Section is intentionally left as a placeholder; the parties "
         "have not yet agreed on indemnification terms and Vendor does not indemnify Customer under "
         "this draft.)",
         "NOT_ESTABLISHED", notes="Explicit placeholder explicitly negating any current "
         "obligation."),
    case("fab-ind-af6-hypothetical-provision-01", "indemnification", ["AF6"],
         "If the parties later agree to add an indemnification provision, it might read: 'Vendor "
         "shall indemnify Customer for IP claims.' No such provision currently exists in this "
         "Agreement.",
         "NOT_ESTABLISHED", notes="Explicitly hypothetical future provision, explicitly denied to "
         "currently exist."),
    case("fab-ind-af6-rejected-alternative-01", "indemnification", ["AF6"],
         "During negotiations, Customer's proposed language ('Vendor shall indemnify Customer for "
         "all claims without limitation') was rejected by Vendor and does not appear in the final "
         "executed Agreement.",
         "NOT_ESTABLISHED", notes="Explicitly rejected, explicitly absent from the final text."),
    case("fab-ind-af6-nonoperative-schedule-01", "indemnification", ["AF6"],
         "Schedule 7 (Informational Only, Not Part of the Agreement): a sample clause reading "
         "'Vendor shall indemnify Customer' is provided for reference purposes only.",
         "NOT_ESTABLISHED", notes="Schedule explicitly marked informational/not part of the "
         "Agreement."),
    case("fab-ind-af6-avoidance-of-doubt-negates-01", "indemnification", ["AF6"],
         "12. Risk Allocation. For the avoidance of doubt, nothing in this Agreement shall be "
         "construed as requiring Vendor to indemnify Customer for any claim whatsoever.",
         "NOT_ESTABLISHED", notes="'For the avoidance of doubt' introduces a NEGATION here, not an "
         "establishment -- must not be mistaken for operative language just because the sentence "
         "contains 'indemnify.'"),
    case("fab-ind-af6-describes-another-agreement-01", "indemnification", ["AF6"],
         "In the Prior Distribution Agreement between the parties (now terminated), Vendor "
         "indemnified Customer for product-liability claims. This Agreement contains no comparable "
         "provision.",
         "NOT_ESTABLISHED", notes="Describes a DIFFERENT, terminated agreement's terms, explicitly "
         "denying a comparable provision exists here."),
]

# ===========================================================================
# INDEMNIFICATION — AF7 role complexity
# ===========================================================================
CASES += [
    case("fab-ind-af7-hyphenated-01", "indemnification", ["AF7"],
         "12. Indemnification. Best-in-Class Logistics Corp shall indemnify Riverside-Fenwick "
         "Holdings LLC for any claim arising from a delivery delay.",
         "ESTABLISHED", {"actor": "Best-in-Class Logistics Corp", "beneficiary": "Riverside-Fenwick Holdings LLC"}),
    case("fab-ind-af7-ampersand-01", "indemnification", ["AF7"],
         "12. Indemnification. Harrington & Voss LLP shall indemnify Danforth & Reyes Inc. for any "
         "claim arising from a filing error.",
         "ESTABLISHED", {"actor": "Harrington & Voss LLP", "beneficiary": "Danforth & Reyes Inc"},
         notes="GTD (Step 4A.11 Phase 4): original ground truth expected the beneficiary captured "
               "WITH its trailing abbreviation period ('Danforth & Reyes Inc.'), but here that period "
               "is simultaneously the sentence-terminating period -- the two are orthographically "
               "identical and cannot be told apart. The role-name capture consistently, deliberately "
               "never includes trailing punctuation in ANY case (avoiding swallowing a sentence's own "
               "period into a name), so 'Inc' without the period is the correct and consistent output, "
               "not a wrong-party error -- corrected to match the engine's general, intentional "
               "behavior rather than the original label's assumption."),
    case("fab-ind-af7-abbreviation-digit-01", "indemnification", ["AF7"],
         "12. Indemnification. 3M Fulfillment Co. shall indemnify B2B Wholesale Partners for any "
         "claim arising from a mislabeled shipment.",
         "ESTABLISHED", {"actor": "3M Fulfillment Co.", "beneficiary": "B2B Wholesale Partners"}),
    case("fab-ind-af7-apostrophe-name-01", "indemnification", ["AF7"],
         "12. Indemnification. O'Malley Freight Systems shall indemnify D'Angelo Retail Group for "
         "any claim arising from cargo loss.",
         "ESTABLISHED", {"actor": "O'Malley Freight Systems", "beneficiary": "D'Angelo Retail Group"}),
    case("fab-ind-af7-similarly-named-roles-01", "indemnification", ["AF7"],
         "This Agreement is between Meridian Systems Inc. and Meridian Solutions LLC. 12. "
         "Indemnification. Meridian Systems Inc. shall indemnify Meridian Solutions LLC for any "
         "claim arising from a licensing dispute.",
         "ESTABLISHED", {"actor": "Meridian Systems Inc.", "beneficiary": "Meridian Solutions LLC"},
         notes="Two similarly-named (but genuinely distinct) roles -- correct disambiguation "
               "required, not a false self-referential collapse."),
    case("fab-ind-af7-one-role-two-required-01", "indemnification", ["AF7"],
         "12. Indemnification. Each party shall indemnify Vendor for any claim arising from that "
         "party's own breach.",
         "NOT_ESTABLISHED", notes="'Each party' is a reciprocal opener naming only ONE actual "
         "role (Vendor) as beneficiary -- the cardinality fail-closed invariant from Step 4A.10.10 "
         "should route this to review rather than guess the missing counterparty."),
    case("fab-ind-af7-three-roles-01", "indemnification", ["AF7"],
         "12. Indemnification. Prime Contractor shall indemnify Owner and Owner's Lender for any "
         "claim arising from Prime Contractor's failure to maintain lien-free title to the work.",
         "ESTABLISHED", {"actor": "Prime Contractor", "beneficiary": "Owner"},
         notes="Three roles present (Prime Contractor, Owner, Owner's Lender) -- scores the "
               "primary named beneficiary, Owner."),
]

# ===========================================================================
# INDEMNIFICATION — AF8 symmetry/asymmetry
# ===========================================================================
CASES += [
    case("fab-ind-af8-symmetric-different-wording-01", "indemnification", ["AF8"],
         "12. Mutual Indemnification. Each of Licensor and Licensee shall indemnify, defend, and "
         "hold harmless the other from and against any claim arising from its own breach of this "
         "Agreement, on identical terms in both directions.",
         "ESTABLISHED", notes="Genuinely symmetric reciprocal clause with explicit "
         "'identical terms in both directions' confirmation -- scores only that an obligation "
         "establishes (reciprocal single-obligation representation); the asymmetry-detection "
         "machinery is exercised separately below."),
    case("fab-ind-af8-asymmetric-similar-wording-01", "indemnification", ["AF8"],
         "12. Indemnification. Licensor shall indemnify Licensee for claims arising from patent "
         "infringement. Licensee shall indemnify Licensor for claims arising from patent "
         "infringement, provided that Licensee's obligation is capped at the fees paid in the prior "
         "12 months.",
         "ESTABLISHED", {"actor": "Licensor", "beneficiary": "Licensee"},
         notes="Surface-similar wording in both directions, but only Licensee's obligation carries "
               "a cap and a proviso -- genuinely asymmetric; scores the first (Licensor's, "
               "unconditional) obligation."),
    case("fab-ind-af8-same-value-different-scope-01", "indemnification", ["AF8"],
         "12. Indemnification. Vendor's indemnification obligations shall not exceed 2 times the "
         "total annual fees paid for third-party IP claims only. Customer's indemnification "
         "obligations shall not exceed 2 times the total annual fees paid for any claim "
         "whatsoever.",
         "ESTABLISHED", notes="Same monetary multiplier (2x) stated for both parties, but the "
         "SCOPE differs materially (IP claims only vs. any claim) -- a differentiation the "
         "asymmetry machinery should catch even though the number matches."),
    case("fab-ind-af8-defense-control-diff-01", "indemnification", ["AF8"],
         "12. Indemnification. Each party shall indemnify the other for claims arising from its "
         "own breach. Vendor shall control the defense of any claim against Vendor, while Customer "
         "may only participate in the defense of any claim against Customer at Customer's own "
         "expense.",
         "ESTABLISHED", notes="Reciprocal opener with a defense-control asymmetry stated "
         "afterward (control vs. mere participation) -- the asymmetry-reasons machinery should "
         "flag this, not silently treat the clause as fully symmetric."),
    case("fab-ind-af8-causation-diff-01", "indemnification", ["AF8"],
         "12. Indemnification. Each party shall indemnify the other for third-party claims. "
         "Vendor's obligation applies only to claims caused by Vendor's sole negligence, while "
         "Customer's obligation applies to claims to which Customer's conduct contributed in any "
         "degree.",
         "ESTABLISHED", notes="Reciprocal opener with differing NAMED causation standards per "
         "party (sole negligence vs. contributed in any degree) -- a real asymmetry."),
]

# ===========================================================================
# INDEMNIFICATION — AF9 false absence
# ===========================================================================
CASES += [
    case("fab-ind-af9-unusual-structure-01", "indemnification", ["AF9"],
         "12. Risk Transfer. Where a third party brings a claim against Retailer arising from a "
         "defect in goods Wholesaler supplied, responsibility for that claim, including its "
         "resolution and any resulting cost, rests with Wholesaler, who shall answer for it "
         "directly to Retailer.",
         "NOT_ESTABLISHED", notes="A genuinely present risk-transfer proposition using unusual, "
         "verbose structure ('responsibility... rests with Wholesaler, who shall answer for it "
         "directly to Retailer') this mechanism's bounded pattern list doesn't cover -- correctly "
         "PRESENT_BUT_UNRESOLVED (safe review), not silently absent and not force-established."),
    case("fab-ind-af9-buried-in-long-clause-01", "indemnification", ["AF9"],
         "12. General Terms. This Section addresses several matters including invoicing frequency, "
         "delivery windows, and quality standards. Separately, and without limiting the generality "
         "of the foregoing, Vendor shall indemnify Customer for any claim arising from Vendor's "
         "willful misconduct, a provision the parties consider material.",
         "ESTABLISHED", {"actor": "Vendor", "beneficiary": "Customer"},
         notes="Genuine obligation buried inside a long, multi-topic section -- must not be missed "
               "just because surrounding text is about unrelated matters."),
]

# ===========================================================================
# INDEMNIFICATION — AF10 compound (>=2 mechanisms)
# ===========================================================================
CASES += [
    case("fab-ind-af10-unusual-prop-plus-xref-01", "indemnification", ["AF10", "AF1", "AF4"],
         "9. Limitation of Liability. Aggregate liability shall not exceed $650,000.\n\n"
         "12. Indemnification. Franchisee, a party bound by the terms of the Franchise Disclosure "
         "Document, shall indemnify Franchisor for any claim arising from a health-code violation "
         "at Franchisee's location, subject to the limitation of liability set forth in Section 9.",
         "ESTABLISHED", {"actor": "Franchisee", "beneficiary": "Franchisor"},
         notes="Appositive-interrupted subject + cross-reference in the same obligation."),
    case("fab-ind-af10-condition-plus-role-reversal-01", "indemnification", ["AF10", "AF3"],
         "12. Indemnification. If Customer materially breaches its confidentiality obligations, "
         "Customer shall indemnify Vendor for the resulting loss.",
         "ESTABLISHED", {"actor": "Customer", "beneficiary": "Vendor"},
         expected_condition="ESTABLISHED",
         notes="Role-reversed direction (Customer indemnifies Vendor, not the usual Vendor-> "
               "Customer) combined with a leading condition."),
    case("fab-ind-af10-xref-plus-multiple-values-01", "indemnification", ["AF10", "AF4"],
         "9. Limitation of Liability. General liability is limited to $500,000. Liability for "
         "data-breach claims is separately fixed at a ceiling of $1,500,000.\n\n"
         "12. Indemnification. Reseller shall indemnify Purchaser, as limited by Section 9's "
         "ceiling.",
         "ESTABLISHED", {"actor": "Reseller", "beneficiary": "Purchaser"},
         notes="Target division states two distinct values -- resolver must fail closed on VALUE "
               "(ambiguous), obligation itself still establishes."),
    case("fab-ind-af10-reciprocal-plus-exception-01", "indemnification", ["AF10", "AF8", "AF3"],
         "12. Indemnification. Each party shall indemnify the other for claims arising from its "
         "own breach of this Agreement, except that neither party is obligated to indemnify the "
         "other for claims arising from a force majeure event.",
         "ESTABLISHED", notes="Reciprocal opener with a shared (not party-specific) trailing "
         "exception -- should remain treated as genuinely reciprocal (the exception applies "
         "equally to both directions, not a differentiation signal)."),
    case("fab-ind-af10-amendment-plus-conditional-cap-01", "indemnification", ["AF10", "AF3", "AF4"],
         "9. Limitation of Liability. Aggregate liability is capped at $500,000.\n\n"
         "Amendment No. 2 provides: Section 9's cap shall instead be $1,200,000, but only for "
         "claims arising after the amendment's effective date.\n\n"
         "12. Indemnification. Guarantor shall indemnify Beneficiary, pursuant to Section 9's "
         "cap.",
         "ESTABLISHED", {"actor": "Guarantor", "beneficiary": "Beneficiary"},
         notes="Amendment states a new figure with its own condition, without forming a genuine "
               "second 'Section 9' heading -- resolver follows the ORIGINAL Section 9 heading only "
               "(disclosed amendment-parsing boundary), obligation itself still establishes."),
    case("fab-ind-af10-semantic-only-plus-xref-01", "indemnification", ["AF10", "AF1", "AF5"],
         "9. Limitation of Liability. Aggregate liability is capped at $750,000.\n\n"
         "12. Risk Allocation. Should Retailer face a third-party claim tied to a defect in goods "
         "Distributor supplied, Distributor is the party who must step into Retailer's shoes and "
         "resolve it, as limited by Section 9's cap.",
         "NOT_ESTABLISHED", notes="'Step into Retailer's shoes' is a genuinely novel, unbounded "
         "idiom outside every structured pattern -- correctly PRESENT_BUT_UNRESOLVED even with a "
         "clean cross-reference present, never force-established from the xref alone."),
]

# ===========================================================================
# LIABILITY — AF1 structural generalization (cap-statement variety)
# ===========================================================================
CASES += [
    case("fab-lia-af1-canonical-01", "liability", ["AF1"],
         "12. Limitation of Liability. Neither party's aggregate liability arising out of or "
         "relating to this Agreement shall exceed the total fees paid in the twelve months "
         "preceding the event giving rise to the claim.",
         "ESTABLISHED", {"kind": "multiplier", "multiplier": 1.0}, expected_dimension="general_cap"),
    case("fab-lia-af1-passive-01", "liability", ["AF1"],
         "12. Limitation of Liability. Aggregate liability under this Agreement is limited to an "
         "amount equal to two times the fees paid in the preceding twelve months.",
         "ESTABLISHED", {"kind": "multiplier", "multiplier": 2.0}, expected_dimension="general_cap",
         notes="Passive-voice framing ('is limited to') rather than 'shall not exceed.'"),
    case("fab-lia-af1-nominalized-01", "liability", ["AF1"],
         "12. Limitation of Liability. The parties' maximum aggregate exposure under this "
         "Agreement is an amount not to exceed three times the annual fees.",
         "ESTABLISHED", {"kind": "multiplier", "multiplier": 3.0}, expected_dimension="general_cap",
         notes="Nominalized 'maximum aggregate exposure... is an amount not to exceed' framing."),
    case("fab-lia-af1-embedded-relative-01", "liability", ["AF1"],
         "12. Limitation of Liability. Each party's aggregate liability, which the parties agree "
         "represents a reasonable allocation of risk, shall not exceed $1,000,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1000000.0}, expected_dimension="general_cap",
         notes="Embedded relative clause between the subject and the verb."),
    case("fab-lia-af1-semicolon-01", "liability", ["AF1"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $2,500,000; this cap "
         "applies regardless of the theory of liability asserted.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 2500000.0}, expected_dimension="general_cap"),
    case("fab-lia-af1-parenthetical-01", "liability", ["AF1"],
         "12. Limitation of Liability. Aggregate liability (excluding amounts payable under the "
         "indemnification obligations in Section 13) shall not exceed $800,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 800000.0}, expected_dimension="general_cap"),
    case("fab-lia-af1-enumerated-01", "liability", ["AF1"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $1,500,000. This cap "
         "does not apply to: (a) breaches of confidentiality; (b) gross negligence; or (c) willful "
         "misconduct.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1500000.0}, expected_dimension="general_cap"),
    case("fab-lia-af1-grammatical-inversion-01", "liability", ["AF1"],
         "12. Limitation of Liability. Under no circumstances shall aggregate liability exceed "
         "$3,000,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 3000000.0}, expected_dimension="general_cap"),
]

# ===========================================================================
# LIABILITY — AF2 object/ownership (value adjacent to unrelated concepts)
# ===========================================================================
CASES += [
    case("fab-lia-af2-insurance-adjacent-01", "liability", ["AF2"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $1,000,000. Separately, "
         "Vendor shall maintain cyber-liability insurance of $5,000,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1000000.0}, expected_dimension="general_cap",
         notes="A larger, unrelated insurance figure sits in the same clause -- must not be "
               "mistaken for the general cap."),
    case("fab-lia-af2-sla-adjacent-01", "liability", ["AF2"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $750,000, exclusive of "
         "service credits owed under the SLA, which shall not exceed $40,000 in any month.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 750000.0}, expected_dimension="general_cap"),
    case("fab-lia-af2-purchase-price-adjacent-01", "liability", ["AF2"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $600,000. The purchase "
         "price under the related Asset Purchase Agreement is $4,200,000 and is not affected by "
         "this Section.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 600000.0}, expected_dimension="general_cap"),
    case("fab-lia-af2-deductible-adjacent-01", "liability", ["AF2"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $900,000, after "
         "application of the $25,000 deductible described in Section 14.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 900000.0}, expected_dimension="general_cap"),
    case("fab-lia-af2-tax-adjacent-01", "liability", ["AF2"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $1,200,000, exclusive "
         "of any sales or use tax remittance obligations, which are governed separately.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1200000.0}, expected_dimension="general_cap"),
    case("fab-lia-af2-deposit-adjacent-01", "liability", ["AF2"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $450,000. The security "
         "deposit of $50,000 held under Section 6 is not credited against this cap.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 450000.0}, expected_dimension="general_cap"),
    case("fab-lia-af2-fee-adjacent-01", "liability", ["AF2"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $2,000,000. The annual "
         "license fee of $180,000 is unrelated to this cap.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 2000000.0}, expected_dimension="general_cap"),
]

# ===========================================================================
# LIABILITY — AF3 conditional applicability
# ===========================================================================
CASES += [
    case("fab-lia-af3-nested-condition-01", "liability", ["AF3"],
         "12. Limitation of Liability. If a claim is filed within the applicable statute of "
         "limitations, and if that claim is not otherwise excluded under Section 13, aggregate "
         "liability shall not exceed $700,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 700000.0}, expected_dimension="general_cap",
         expected_condition="ESTABLISHED"),
    case("fab-lia-af3-temporal-condition-01", "liability", ["AF3"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $850,000. This cap "
         "shall not apply until the parties have completed the informal escalation procedure "
         "described in Section 22.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 850000.0}, expected_dimension="general_cap",
         expected_condition="ESTABLISHED"),
    case("fab-lia-af3-condition-plus-exception-01", "liability", ["AF3"],
         "12. Limitation of Liability. Aggregate liability is capped at $1,000,000, provided that "
         "this ceiling governs only ordinary breach claims, except where applicable law prohibits "
         "limiting liability for gross negligence.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1000000.0}, expected_dimension="general_cap",
         expected_condition="ESTABLISHED"),
    case("fab-lia-af3-condition-following-sentence-01", "liability", ["AF3"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $600,000. The "
         "foregoing limitation applies only to claims arising under this Agreement, not any "
         "separate agreement between the parties.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 600000.0}, expected_dimension="general_cap",
         expected_condition="ESTABLISHED"),
]

# ===========================================================================
# LIABILITY — AF4 cross-reference (own mature mechanism -- Phase 1 parity audit)
# ===========================================================================
CASES += [
    case("fab-lia-af4-schedule-target-01", "liability", ["AF4"],
         "12. Limitation of Liability. Aggregate liability is capped as set forth in Schedule D.\n\n"
         "Schedule D. Liability Cap. The aggregate liability cap referenced in Section 12 is "
         "$1,300,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1300000.0}, expected_dimension="general_cap",
         notes="Exercises liability's own pre-existing cross-reference resolver (not Phase 1's "
               "shared mechanism, per the parity audit's conclusion to leave it as-is)."),
    case("fab-lia-af4-missing-target-01", "liability", ["AF4"],
         "12. Limitation of Liability. Aggregate liability is capped as set forth in the Master "
         "Pricing Addendum.",
         "NOT_ESTABLISHED", notes="Reference target never included in this text -- must fail "
         "closed rather than report an uncapped or zero figure."),
    case("fab-lia-af4-conflicting-target-01", "liability", ["AF4"],
         "12. Limitation of Liability. Aggregate liability is capped as set forth in Schedule E.\n\n"
         "Schedule E. Liability Cap. The cap is $500,000.\n\n"
         "Restated Schedule E (superseding version attached separately). The cap is $900,000.",
         "NOT_ESTABLISHED", notes="Two differing values both purporting to be 'Schedule E' -- "
         "must not silently pick either."),
    case("fab-lia-af4-insurance-target-01", "liability", ["AF4"],
         "12. Limitation of Liability. Aggregate liability is capped as set forth in Schedule F.\n\n"
         "Schedule F. Insurance Requirements. Vendor shall maintain insurance of $2,000,000.",
         "NOT_ESTABLISHED", notes="Reference resolves to an INSURANCE schedule, not a liability "
         "concept -- liability's own concept-anchoring check should reject this."),
]

# ===========================================================================
# LIABILITY — AF6 false structural establishment
# ===========================================================================
CASES += [
    case("fab-lia-af6-recital-01", "liability", ["AF6"],
         "RECITALS. WHEREAS the parties intend to limit aggregate liability to a reasonable "
         "amount, they enter into this Agreement on the terms set forth below.",
         "NOT_ESTABLISHED", notes="Recital expressing intent, no operative figure at all."),
    case("fab-lia-af6-superseded-01", "liability", ["AF6"],
         "The original Section 12 cap of $500,000 was deleted by Amendment No. 1 and replaced "
         "with an uncapped liability provision that appears later in this Agreement.",
         "NOT_ESTABLISHED", notes="Explicitly superseded figure -- correctly not the controlling "
         "cap from THIS sentence alone."),
    case("fab-lia-af6-hypothetical-01", "liability", ["AF6"],
         "If the parties were to negotiate a cap, a reasonable figure might be $1,000,000. No cap "
         "has been agreed as of the date of this draft.",
         "NOT_ESTABLISHED", notes="Explicitly hypothetical, explicitly not agreed."),
    case("fab-lia-af6-quoted-example-01", "liability", ["AF6"],
         "A typical limitation clause reads: \"Aggregate liability shall not exceed $1,000,000.\" "
         "This Agreement does not include such a clause.",
         "NOT_ESTABLISHED", notes="Quoted example, explicitly negated afterward."),
]

# ===========================================================================
# LIABILITY — AF7 role/carve-out complexity (category treatments)
# ===========================================================================
CASES += [
    case("fab-lia-af7-carveout-exclusion-01", "liability", ["AF7"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $1,000,000. This "
         "limitation does not apply to claims arising from a data breach or from willful "
         "misconduct, which remain uncapped.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1000000.0}, expected_dimension="general_cap"),
    case("fab-lia-af7-multiword-party-01", "liability", ["AF7"],
         "12. Limitation of Liability. Northgate Analytics & Consulting Group's aggregate liability "
         "shall not exceed $1,750,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1750000.0}, expected_dimension="general_cap"),
]

# ===========================================================================
# LIABILITY — AF9 false absence
# ===========================================================================
CASES += [
    case("fab-lia-af9-unusual-structure-01", "liability", ["AF9"],
         "12. Financial Exposure. Under no set of circumstances will either party be called upon "
         "to answer, in the aggregate, for more than the total fees exchanged under this Agreement "
         "in the year before the dispute arose.",
         "NOT_ESTABLISHED", notes="A genuinely present cap concept phrased in an unusual, "
         "verbose way this adapter's structured patterns don't cover -- correctly routed to "
         "review, not silently reported absent."),
]

# ===========================================================================
# LIABILITY — AF10 compound
# ===========================================================================
CASES += [
    case("fab-lia-af10-xref-plus-condition-01", "liability", ["AF10", "AF3", "AF4"],
         "12. Limitation of Liability. Aggregate liability is capped as set forth in Schedule G.\n\n"
         "Schedule G. Liability Cap. The cap is $950,000, applicable only to claims filed within "
         "two years of the Effective Date.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 950000.0}, expected_dimension="general_cap"),
    case("fab-lia-af10-passive-plus-carveout-01", "liability", ["AF10", "AF1", "AF7"],
         "12. Limitation of Liability. Aggregate liability is limited to $2,200,000, exclusive of "
         "amounts arising from fraud, which are not subject to any cap.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 2200000.0}, expected_dimension="general_cap"),
]

# ===========================================================================
# PAYMENT TERMS — AF1 structural generalization (net-days variety)
# ===========================================================================
CASES += [
    case("fab-pay-af1-canonical-01", "payment_terms", ["AF1"],
         "9. Payment Terms. Customer shall remit payment to Vendor within Net 30 days following "
         "receipt of a valid invoice.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days"),
    case("fab-pay-af1-passive-01", "payment_terms", ["AF1"],
         "9. Payment Terms. Invoices are payable within 45 days of the invoice date.",
         "ESTABLISHED", {"net_days": 45.0}, expected_dimension="net_days",
         notes="Passive framing ('invoices are payable within') rather than 'Customer shall pay.'"),
    case("fab-pay-af1-nominalized-01", "payment_terms", ["AF1"],
         "9. Payment Terms. The payment period applicable to each invoice is 30 days from the date "
         "of receipt.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days"),
    case("fab-pay-af1-embedded-relative-01", "payment_terms", ["AF1"],
         "9. Payment Terms. Customer, which processes invoices through its centralized accounts-"
         "payable system, shall pay Vendor within Net 60 days of receipt of invoice.",
         "ESTABLISHED", {"net_days": 60.0}, expected_dimension="net_days"),
    case("fab-pay-af1-semicolon-01", "payment_terms", ["AF1"],
         "9. Payment Terms. Buyer shall pay Provider within Net 30 days of receipt of invoice; "
         "time is of the essence with respect to this obligation.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days"),
    case("fab-pay-af1-grammatical-inversion-01", "payment_terms", ["AF1"],
         "9. Payment Terms. Within Net 30 days of receipt of invoice, Buyer shall pay Provider "
         "all undisputed amounts.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days"),
]

# ===========================================================================
# PAYMENT TERMS — AF2 object/ownership (late fee / value adjacency)
# ===========================================================================
CASES += [
    case("fab-pay-af2-insurance-adjacent-01", "payment_terms", ["AF2"],
         "9. Payment Terms. Buyer shall pay Provider within Net 30 days of receipt of invoice. "
         "Separately, Vendor maintains cargo insurance of $500,000 for shipments in transit.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days"),
    case("fab-pay-af2-deposit-adjacent-01", "payment_terms", ["AF2"],
         "9. Payment Terms. Buyer shall pay Provider within Net 45 days of receipt of invoice. A "
         "security deposit of $10,000 was collected at signing and is unrelated to this payment "
         "schedule.",
         "ESTABLISHED", {"net_days": 45.0}, expected_dimension="net_days"),
    case("fab-pay-af2-late-fee-rate-01", "payment_terms", ["AF2"],
         "9. Payment Terms. Amounts not paid when due shall accrue a late fee of 1.5% per month "
         "on the outstanding balance.",
         "ESTABLISHED", {"late_fee_rate_percent": 1.5}, expected_dimension="late_fee_rate_percent"),
    case("fab-pay-af2-tax-adjacent-to-late-fee-01", "payment_terms", ["AF2"],
         "9. Payment Terms. Late payments accrue interest at 2% per month. Customer is separately "
         "responsible for all applicable sales and use taxes.",
         "ESTABLISHED", {"late_fee_rate_percent": 2.0}, expected_dimension="late_fee_rate_percent"),
]

# ===========================================================================
# PAYMENT TERMS — AF3 conditional applicability
# ===========================================================================
CASES += [
    case("fab-pay-af3-nested-condition-01", "payment_terms", ["AF3"],
         "9. Payment Terms. If Provider has delivered the Deliverables in accordance with the "
         "statement of work, and if Buyer has not disputed the invoice within 10 days, Buyer "
         "shall remit payment to Provider within Net 30 days of receipt of invoice.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         expected_condition="ESTABLISHED"),
    case("fab-pay-af3-temporal-condition-01", "payment_terms", ["AF3"],
         "9. Payment Terms. Buyer shall pay Provider within Net 30 days of receipt of invoice. "
         "This obligation shall not apply until Vendor has provided a valid W-9 form.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         expected_condition="ESTABLISHED"),
    case("fab-pay-af3-contingent-milestone-01", "payment_terms", ["AF3"],
         "9. Payment Terms. Customer's obligation to pay the final milestone payment is contingent "
         "on Vendor obtaining written sign-off from Customer's project lead.",
         "ESTABLISHED", expected_condition="ESTABLISHED",
         notes="No net-days figure in this sentence; scores condition/obligation presence, not a "
               "specific dimension value."),
]

# ===========================================================================
# PAYMENT TERMS — AF6 false structural establishment
# ===========================================================================
CASES += [
    case("fab-pay-af6-recital-01", "payment_terms", ["AF6"],
         "RECITALS. WHEREAS the parties intend to establish a Net 30 payment cycle, they enter "
         "into this Agreement on the terms below.",
         "NOT_ESTABLISHED", notes="Recital expressing intent, not the operative clause."),
    case("fab-pay-af6-superseded-01", "payment_terms", ["AF6"],
         "The original Net 30 payment term was deleted by Amendment No. 1 and replaced with a "
         "milestone-based schedule described later in this Agreement.",
         "NOT_ESTABLISHED", notes="Explicitly superseded term."),
    case("fab-pay-af6-hypothetical-01", "payment_terms", ["AF6"],
         "If the parties agree on payment terms, Net 30 is the vendor's standard offer. No payment "
         "terms have been finalized in this draft.",
         "NOT_ESTABLISHED", notes="Explicitly hypothetical/unfinalized."),
    case("fab-pay-af6-heading-01", "payment_terms", ["AF6"],
         "SECTION 9: NET 30 PAYMENT TERMS\n\nThis Section addresses invoicing procedures generally.",
         "NOT_ESTABLISHED", notes="Heading states the concept; body never restates an operative "
         "figure."),
    case("fab-pay-af6-describes-another-agreement-01", "payment_terms", ["AF6"],
         "Under the parties' prior, now-terminated agreement, payment terms were Net 15. This "
         "Agreement contains no comparable payment-terms provision.",
         "NOT_ESTABLISHED", notes="Describes a different, terminated agreement."),
]

# ===========================================================================
# PAYMENT TERMS — AF7 role complexity
# ===========================================================================
CASES += [
    case("fab-pay-af7-multiword-party-01", "payment_terms", ["AF7"],
         "9. Payment Terms. Blackstone Ridge Manufacturing Group shall pay Fenwick & Associates "
         "Consulting within Net 30 days of receipt of invoice.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days"),
    case("fab-pay-af7-defined-alias-01", "payment_terms", ["AF7"],
         "This Agreement is between Solstice Beverage Holdings (\"Buyer\") and Cascade Bottling "
         "Partners (\"Supplier\"). 9. Payment Terms. Buyer shall pay Supplier within Net 45 days of "
         "receipt of invoice.",
         "ESTABLISHED", {"net_days": 45.0}, expected_dimension="net_days"),
]

# ===========================================================================
# PAYMENT TERMS — AF9 false absence
# ===========================================================================
CASES += [
    case("fab-pay-af9-unusual-structure-01", "payment_terms", ["AF9"],
         "9. Settlement Cycle. Amounts owed under a properly issued invoice become due for "
         "settlement on the thirtieth day measured from the date Customer receives that invoice.",
         "NOT_ESTABLISHED", notes="A genuinely present Net-30-equivalent concept phrased without "
         "the 'Net N days' shorthand or 'shall pay within N days' structure -- correctly routed to "
         "review rather than reported absent."),
]

# ===========================================================================
# PAYMENT TERMS — AF10 compound
# ===========================================================================
CASES += [
    case("fab-pay-af10-condition-plus-late-fee-01", "payment_terms", ["AF10", "AF3", "AF2"],
         "9. Payment Terms. Buyer shall pay Provider within Net 30 days of receipt of invoice. If "
         "payment is not received within that period, a late fee of 1.5% per month shall accrue on "
         "the outstanding balance.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days"),
    case("fab-pay-af10-multiword-plus-condition-01", "payment_terms", ["AF10", "AF7", "AF3"],
         "9. Payment Terms. Ridgemont Capital Advisors LLC shall pay Northstar Data Systems Inc. "
         "within Net 30 days of receipt of invoice, provided that the invoice is accompanied by "
         "supporting time records.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         expected_condition="ESTABLISHED"),
]

# ===========================================================================
# ADDITIONAL COVERAGE — indemnification AF5 (discovery/verification
# separation, text-based cases; provider-fault-mode cases are handled
# separately in the runner, not as corpus text)
# ===========================================================================
CASES += [
    case("fab-ind-af5-deterministic-succeeds-01", "indemnification", ["AF5"],
         "12. Indemnification. Escrow Holder shall indemnify Beneficiary for any claim arising "
         "from Escrow Holder's failure to follow the escrow instructions.",
         "ESTABLISHED", {"actor": "Escrow Holder", "beneficiary": "Beneficiary"},
         notes="Deterministic discovery succeeds outright (canonical shape); semantic discovery, "
               "if it also proposes this span, must not change the outcome or provenance rules."),
    case("fab-ind-af5-irrelevant-candidate-context-01", "indemnification", ["AF5"],
         "12. Confidentiality. Recipient shall protect Discloser's confidential information using "
         "reasonable care. This Section does not address indemnification, which is covered "
         "elsewhere if at all.",
         "NOT_ESTABLISHED", notes="Text a broad semantic provider might flag as loosely related "
         "to risk topics ('protect,' 'reasonable care') but which states a confidentiality "
         "duty, not indemnification -- deterministic verification must reject it regardless of "
         "any semantic proposal."),
    case("fab-ind-af5-correct-quote-wrong-interpretation-01", "indemnification", ["AF5"],
         "12. Indemnification. The parties considered, but did not adopt, a provision under which "
         "Vendor would indemnify Customer for ordinary breach; the final Agreement contains no "
         "indemnification obligation.",
         "NOT_ESTABLISHED", notes="The verbatim phrase 'Vendor would indemnify Customer' is "
         "genuinely present and might be quoted correctly by a semantic provider, but its "
         "CORRECT interpretation (a rejected, non-adopted proposal) is the opposite of "
         "establishment -- deterministic verification, not the quote alone, must decide this."),
]

# ===========================================================================
# ADDITIONAL COVERAGE — liability breadth (AF1/AF2/AF3/AF4/AF6/AF7/AF9/AF10/AF5)
# ===========================================================================
CASES += [
    case("fab-lia-af1-coordinated-01", "liability", ["AF1"],
         "12. Limitation of Liability. Aggregate liability shall not exceed, and in no event shall "
         "be construed to exceed, $1,400,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1400000.0}, expected_dimension="general_cap"),
    case("fab-lia-af1-defined-role-01", "liability", ["AF1"],
         "This Agreement is between Halbrook Systems Inc. (\"Provider\") and Delacroix Ventures LLC "
         "(\"Client\"). 12. Limitation of Liability. Provider's aggregate liability shall not "
         "exceed $950,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 950000.0}, expected_dimension="general_cap"),
    case("fab-lia-af1-multiplier-word-form-01", "liability", ["AF1"],
         "12. Limitation of Liability. Aggregate liability shall not exceed two and one-half (2.5) "
         "times the total fees paid in the preceding twelve months.",
         "ESTABLISHED", {"kind": "multiplier", "multiplier": 2.5}, expected_dimension="general_cap",
         notes="Spelled-out fractional multiplier with a parenthetical digit confirmation."),
    case("fab-lia-af2-multiple-categories-different-treatment-01", "liability", ["AF2"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $1,100,000. Liability "
         "for confidentiality breaches is separately capped at $2,000,000, and liability for fraud "
         "is uncapped.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1100000.0}, expected_dimension="general_cap",
         notes="Three DIFFERENT values for three different categories in one clause -- scores "
               "only the GENERAL cap, must not be confused with the category-specific figures."),
    case("fab-lia-af3-condition-plus-xref-01", "liability", ["AF3", "AF4"],
         "12. Limitation of Liability. Aggregate liability is capped as set forth in Schedule H.\n\n"
         "Schedule H. Liability Cap. The cap is $1,050,000, and applies only while Vendor maintains "
         "the insurance coverage required under Section 15.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1050000.0}, expected_dimension="general_cap"),
    case("fab-lia-af4-multiple-candidate-targets-01", "liability", ["AF4"],
         "12. Limitation of Liability. Aggregate liability is capped as set forth in the Master "
         "Terms.\n\nExhibit 1: Master Terms Summary (informational only). A prior draft cap of "
         "$400,000 is shown here for reference.\n\nMaster Terms. The binding aggregate liability "
         "cap is $1,600,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1600000.0}, expected_dimension="general_cap",
         notes="Two candidate 'Master Terms' mentions, one explicitly informational-only -- the "
               "resolver's own label-occurrence search may find both; if it cannot safely "
               "distinguish them it should fail closed rather than average or guess. Documented "
               "as a genuine stress case for the pre-existing mechanism, not a predicted defect."),
    case("fab-lia-af6-drafting-note-01", "liability", ["AF6"],
         "[DRAFTING NOTE: insert the negotiated aggregate liability cap here, e.g. $1,000,000]",
         "NOT_ESTABLISHED", notes="Bracketed drafting placeholder, not the document's own text."),
    case("fab-lia-af6-definition-01", "liability", ["AF6"],
         "\"Liability Cap\" means the maximum aggregate amount either party would owe the other "
         "under Section 12, if a specific dollar figure is agreed in that Section.",
         "NOT_ESTABLISHED", notes="Definitions-section sentence describing a defined term "
         "conditionally, not itself stating a figure."),
    case("fab-lia-af7-hyphenated-party-01", "liability", ["AF7"],
         "12. Limitation of Liability. Blue-Sky Renewable Partners' aggregate liability shall not "
         "exceed $1,900,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1900000.0}, expected_dimension="general_cap"),
    case("fab-lia-af9-buried-in-long-section-01", "liability", ["AF9"],
         "12. General Commercial Terms. This Section covers invoicing cadence, delivery windows, "
         "and reporting obligations. Separately, and without limiting the foregoing, aggregate "
         "liability under this Agreement shall not exceed $1,300,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1300000.0}, expected_dimension="general_cap",
         notes="Genuine cap buried inside a long, multi-topic section."),
    case("fab-lia-af10-carveout-plus-condition-01", "liability", ["AF10", "AF7", "AF3"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $1,650,000, excluding "
         "claims for gross negligence, and this cap shall not apply until Vendor has completed the "
         "SOC 2 certification described in Section 18.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1650000.0}, expected_dimension="general_cap",
         expected_condition="ESTABLISHED"),
    case("fab-lia-af10-multiplier-plus-defined-role-01", "liability", ["AF10", "AF1", "AF7"],
         "This Agreement is between Cormorant Freight Systems (\"Carrier\") and Talus Retail Group "
         "(\"Shipper\"). 12. Limitation of Liability. Carrier's aggregate liability shall not "
         "exceed 2 times the total fees paid in the preceding twelve months.",
         "ESTABLISHED", {"kind": "multiplier", "multiplier": 2.0}, expected_dimension="general_cap"),
]

# ===========================================================================
# ADDITIONAL COVERAGE — payment_terms breadth
# ===========================================================================
CASES += [
    case("fab-pay-af1-within-days-01", "payment_terms", ["AF1"],
         "9. Payment Terms. Customer shall remit all undisputed amounts within 30 days of receipt "
         "of Vendor's invoice.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         notes="'within N days of receipt' phrasing rather than literal 'Net N.'"),
    case("fab-pay-af1-receipt-of-deliverables-trigger-01", "payment_terms", ["AF1"],
         "9. Payment Terms. Buyer shall pay Provider within Net 30 days of Buyer's acceptance "
         "of the Deliverables.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days"),
    case("fab-pay-af1-enumerated-milestones-01", "payment_terms", ["AF1"],
         "9. Payment Terms. Buyer shall pay Provider as follows: (a) 30% upon signing; (b) 40% "
         "upon delivery; and (c) the remaining 30% within Net 30 days of final acceptance.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         notes="Enumerated milestone list; the LAST milestone states a Net-30 figure."),
    case("fab-pay-af2-price-increase-adjacent-01", "payment_terms", ["AF2"],
         "9. Payment Terms. Buyer shall pay Provider within Net 30 days of receipt of invoice. "
         "Vendor may increase prices by up to 5% annually on 60 days' notice.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days"),
    case("fab-pay-af2-expense-reimbursement-adjacent-01", "payment_terms", ["AF2"],
         "9. Payment Terms. Buyer shall pay Provider within Net 45 days of receipt of invoice. "
         "Customer shall separately reimburse Vendor for pre-approved travel expenses.",
         "ESTABLISHED", {"net_days": 45.0}, expected_dimension="net_days",
         notes="Ordinary expense reimbursement mentioned nearby -- must not be confused with the "
               "core Net-days figure or misread as a risk-transfer indemnity (Phase 3 boundary)."),
    case("fab-pay-af3-condition-following-sentence-01", "payment_terms", ["AF3"],
         "9. Payment Terms. Buyer shall pay Provider within Net 30 days of receipt of invoice. "
         "This obligation does not apply to invoices disputed in good faith within 10 days of "
         "receipt.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         expected_condition="ESTABLISHED"),
    case("fab-pay-af3-condition-plus-xref-01", "payment_terms", ["AF3", "AF4"],
         "9. Payment Terms. Buyer shall pay Provider within Net 30 days of receipt of invoice, "
         "subject to the dispute procedure set forth in Section 11, if applicable.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days"),
    case("fab-pay-af4-schedule-reference-01", "payment_terms", ["AF4"],
         "9. Payment Terms. Payment terms are as set forth in the applicable Order Form.",
         "NOT_ESTABLISHED", notes="External-document delegation (Order Form) -- payment_terms' "
         "own boolean cross-reference detector should route this to review, per the Phase 1 "
         "parity audit's documented, disclosed boundary (no in-document resolution attempted)."),
    case("fab-pay-af4-schedule-in-document-01", "payment_terms", ["AF4"],
         "9. Payment Terms. Payment terms are as set forth in Schedule 3.\n\nSchedule 3. Net 45 "
         "days from receipt of invoice.",
         "ESTABLISHED", {"net_days": 45.0}, expected_dimension="net_days",
         notes="GTD (ground-truth defect, corrected after battery execution): the original "
               "expected_status assumed the boolean-only cross-reference detector (which never "
               "attempts resolution, per the Phase 1 parity audit) was the ONLY path to a value "
               "here, and predicted NOT_ESTABLISHED. In fact net_days extraction is an "
               "INDEPENDENT whole-window scan that finds 'Net 45' inside Schedule 3's own text "
               "regardless of the cross-reference boolean flag -- since Schedule 3 falls within "
               "the padded window around the 'Payment Terms' anchor, the correct value is found "
               "anyway, just not THROUGH deliberate cross-reference resolution. Production "
               "behavior is correct (and arguably fortunate, not a designed capability); ground "
               "truth was wrong, not the engine. Corrected to ESTABLISHED/45.0."),
    case("fab-pay-af6-drafting-note-01", "payment_terms", ["AF6"],
         "[DRAFTING NOTE: insert agreed Net terms here, e.g. Net 30]",
         "NOT_ESTABLISHED", notes="Bracketed placeholder."),
    case("fab-pay-af6-negotiation-history-01", "payment_terms", ["AF6"],
         "Customer initially proposed Net 60; Vendor countered with Net 15; the parties have not "
         "yet reached agreement on this point.",
         "NOT_ESTABLISHED", notes="Negotiation history, no agreed figure."),
    case("fab-pay-af6-avoidance-of-doubt-negates-01", "payment_terms", ["AF6"],
         "9. Payment Terms. For the avoidance of doubt, this Agreement does not establish a fixed "
         "Net payment period; timing is determined on a purchase-order-by-purchase-order basis.",
         "NOT_ESTABLISHED", notes="Explicitly negates a fixed Net period."),
    case("fab-pay-af7-similarly-named-parties-01", "payment_terms", ["AF7"],
         "This Agreement is between Vantage Point Logistics and Vantage Point Retail. 9. Payment "
         "Terms. Vantage Point Retail shall pay Vantage Point Logistics within Net 30 days of "
         "receipt of invoice.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         notes="Two similarly-named but distinct parties."),
    case("fab-pay-af9-buried-in-long-section-01", "payment_terms", ["AF9"],
         "9. Commercial Terms. This Section addresses delivery logistics, quality inspection "
         "procedures, and reporting cadence. Separately, Buyer shall pay Provider within Net 30 "
         "days of receipt of invoice.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         notes="Genuine Net-30 term buried inside a long, multi-topic section."),
    case("fab-pay-af10-multi-sentence-plus-late-fee-01", "payment_terms", ["AF10", "AF3", "AF2"],
         "9. Payment Terms. Buyer shall pay Provider within Net 30 days of receipt of invoice. If "
         "Customer fails to pay within that period, interest accrues at 1.5% per month until paid "
         "in full, and Vendor may suspend Services after 60 days of nonpayment.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         expected_condition=None,
         notes="Compound: base Net-30 term, a conditional late-fee consequence, and a further "
               "conditional suspension right, all in one clause -- scores the base net_days "
               "dimension only."),
    case("fab-pay-af10-defined-role-plus-condition-01", "payment_terms", ["AF10", "AF7", "AF3"],
         "This Agreement is between Alderbrook Media Group (\"Advertiser\") and Prism Ad Network "
         "(\"Network\"). 9. Payment Terms. Advertiser shall pay Network within Net 30 days of "
         "receipt of invoice, but only for impressions independently verified by the third-party "
         "ad-verification vendor.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         expected_condition="ESTABLISHED"),
]

# ===========================================================================
# FINAL COVERAGE PASS — bring liability/payment_terms to the 50+ minimums
# and AF10 (compound) to >=30 total across the battery.
# ===========================================================================
CASES += [
    case("fab-pay-af1-quarterly-net-01", "payment_terms", ["AF1"],
         "9. Payment Terms. Customer shall settle each quarterly statement within Net 30 days of "
         "the statement date.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         notes="'Quarterly statement' framing rather than a single invoice."),
    case("fab-pay-af1-subscription-net-01", "payment_terms", ["AF1"],
         "9. Payment Terms. Customer shall pay each monthly subscription invoice within Net 15 "
         "days of receipt.",
         "ESTABLISHED", {"net_days": 15.0}, expected_dimension="net_days"),
    case("fab-pay-af2-milestone-value-adjacent-01", "payment_terms", ["AF2"],
         "9. Payment Terms. Buyer shall pay Provider within Net 30 days of receipt of invoice. "
         "The total contract value across all milestones is $2,400,000.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         notes="A large, unrelated total-contract-value figure sits nearby -- must not be "
               "confused with the net-days dimension."),
    case("fab-pay-af6-heading-only-02", "payment_terms", ["AF6"],
         "APPENDIX B: SAMPLE NET 30 INVOICE TEMPLATE (FOR REFERENCE ONLY)\n\nThis appendix "
         "illustrates invoice formatting and is not part of the operative payment terms.",
         "NOT_ESTABLISHED", notes="Explicitly reference-only appendix, explicitly not part of the "
         "operative terms."),
    case("fab-pay-af7-abbreviated-party-01", "payment_terms", ["AF7"],
         "9. Payment Terms. ACME Corp. shall pay B&T Wholesale within Net 30 days of receipt of "
         "invoice.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days"),
    case("fab-pay-af9-informal-language-01", "payment_terms", ["AF9"],
         "9. Payment Terms. Customer agrees to settle up with Vendor a month after getting each "
         "bill.",
         "NOT_ESTABLISHED", notes="Colloquial, informal phrasing ('settle up,' 'getting each "
         "bill') describing a genuine ~30-day concept without any structured pattern match -- "
         "correctly routed to review, not silently reported absent nor guessed at 30 days."),
    case("fab-pay-af10-multiword-plus-milestone-01", "payment_terms", ["AF10", "AF1", "AF7"],
         "This Agreement is between Wrenfield Analytics Group and Castellane Media Holdings. 9. "
         "Payment Terms. Wrenfield Analytics Group shall pay Castellane Media Holdings within Net "
         "45 days of receipt of each milestone invoice.",
         "ESTABLISHED", {"net_days": 45.0}, expected_dimension="net_days"),
    case("fab-pay-af10-condition-plus-role-reversal-01", "payment_terms", ["AF10", "AF3"],
         "9. Payment Terms. If Network fails to deliver the agreed impression volume in a given "
         "month, Network shall pay Advertiser a service-level credit within Net 30 days of the "
         "shortfall being confirmed.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         expected_condition="ESTABLISHED",
         notes="Role-reversed payment direction (Network pays Advertiser, not the usual "
               "Advertiser->Network) combined with a leading condition."),
    case("fab-lia-af1-role-reversal-01", "liability", ["AF1"],
         "12. Limitation of Liability. Customer's aggregate liability to Vendor arising under this "
         "Agreement shall not exceed $700,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 700000.0}, expected_dimension="general_cap",
         notes="Directional cap naming Customer's liability specifically, not the usual "
               "'either party.'"),
    case("fab-lia-af2-referenced-value-01", "liability", ["AF2"],
         "12. Limitation of Liability. Aggregate liability shall not exceed $1,050,000. This "
         "figure does not include amounts due under the separate purchase-price financing "
         "arrangement referenced in Exhibit 2.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1050000.0}, expected_dimension="general_cap"),
    case("fab-lia-af6-amendment-history-01", "liability", ["AF6"],
         "The cap was $500,000 under the original Agreement, then $750,000 under Amendment 1, then "
         "$900,000 under Amendment 2. Only the CURRENT operative Section 12 (reproduced below) "
         "governs: 12. Limitation of Liability. Aggregate liability shall not exceed $1,000,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1000000.0}, expected_dimension="general_cap",
         notes="A history of superseded figures precedes the CURRENT operative clause, which is "
               "explicitly labeled as controlling -- the current figure should still establish."),
    case("fab-lia-af10-xref-plus-multiplier-condition-01", "liability", ["AF10", "AF3", "AF4"],
         "12. Limitation of Liability. Aggregate liability is capped as set forth in Schedule I.\n\n"
         "Schedule I. Liability Cap. The cap is 3 times the total fees paid, contingent on Vendor "
         "having maintained continuous service availability of at least 99.5% during the Term.",
         "ESTABLISHED", {"kind": "multiplier", "multiplier": 3.0}, expected_dimension="general_cap"),
    case("fab-lia-af10-role-reversal-plus-carveout-01", "liability", ["AF10", "AF1", "AF7"],
         "12. Limitation of Liability. Customer's aggregate liability to Vendor shall not exceed "
         "$1,800,000, excluding amounts arising from Customer's breach of confidentiality, which "
         "remain uncapped.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1800000.0}, expected_dimension="general_cap"),
    case("fab-ind-af10-defined-role-plus-carveout-01", "indemnification", ["AF10", "AF7", "AF1"],
         "This Agreement is between Thornbury Life Sciences Inc. (\"Sponsor\") and Meridian "
         "Clinical Research LLC (\"CRO\"). 12. Indemnification. CRO shall indemnify Sponsor for "
         "any claim arising from CRO's failure to follow the approved clinical protocol, excluding "
         "claims arising from Sponsor's own protocol design.",
         "ESTABLISHED", {"actor": "CRO", "beneficiary": "Sponsor"}),
    case("fab-ind-af10-multiword-plus-xref-plus-condition-01", "indemnification", ["AF10", "AF7", "AF4", "AF3"],
         "9. Limitation of Liability. Aggregate liability shall not exceed $850,000.\n\n"
         "12. Indemnification. If a regulator brings an enforcement action, Blackwood Regulatory "
         "Advisors LLC shall indemnify Fenmore Capital Partners for the resulting defense costs, "
         "subject to the limitation of liability set forth in Section 9.",
         "ESTABLISHED", {"actor": "Blackwood Regulatory Advisors LLC", "beneficiary": "Fenmore Capital Partners"},
         expected_condition="ESTABLISHED"),
]

# ===========================================================================
# FINAL TOP-UP — payment_terms to 50+, AF10 (compound) to >=30 total.
# ===========================================================================
CASES += [
    case("fab-pay-af1-net-terms-with-currency-01", "payment_terms", ["AF1"],
         "9. Payment Terms. Buyer shall pay Provider in U.S. Dollars within Net 30 days of "
         "receipt of a properly formatted invoice.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         notes="Currency qualifier ('in U.S. Dollars') inserted before the Net-days phrase."),
    case("fab-pay-af2-withholding-tax-adjacent-01", "payment_terms", ["AF2"],
         "9. Payment Terms. Buyer shall pay Provider within Net 30 days of receipt of invoice, "
         "net of any withholding tax Customer is required by law to deduct.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         notes="Withholding-tax qualifier immediately adjacent to the net-days figure."),
    case("fab-pay-af10-xref-plus-condition-plus-role-01", "payment_terms", ["AF10", "AF3", "AF4"],
         "This Agreement is between Harrow Point Studios (\"Producer\") and Loxley Distribution "
         "Group (\"Distributor\"). 9. Payment Terms. If Distributor collects gross receipts in a "
         "given quarter, Distributor shall pay Producer its share within Net 45 days of quarter "
         "end, subject to the reconciliation procedure described in Section 14.",
         "ESTABLISHED", {"net_days": 45.0}, expected_dimension="net_days",
         expected_condition="ESTABLISHED"),
    case("fab-lia-af10-condition-plus-role-reversal-01", "liability", ["AF10", "AF3"],
         "12. Limitation of Liability. If Customer terminates this Agreement for convenience, "
         "Customer's aggregate liability to Vendor for the early-termination fee shall not exceed "
         "$400,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 400000.0}, expected_dimension="general_cap",
         expected_condition="ESTABLISHED",
         notes="Role-reversed (Customer's liability, not the usual mutual/Vendor framing) "
               "combined with a leading condition."),
    case("fab-ind-af10-coordinated-plus-xref-01", "indemnification", ["AF10", "AF1", "AF4"],
         "9. Limitation of Liability. Aggregate liability shall not exceed $500,000.\n\n"
         "12. Indemnification. Trustee shall investigate, defend, and indemnify Beneficiary "
         "against any claim arising from Trustee's breach of fiduciary duty, subject to the "
         "limitation of liability set forth in Section 9.",
         "ESTABLISHED", {"actor": "Trustee", "beneficiary": "Beneficiary"}),
    case("fab-ind-af10-reciprocal-plus-xref-01", "indemnification", ["AF10", "AF8", "AF4"],
         "9. Limitation of Liability. Aggregate liability shall not exceed $600,000.\n\n"
         "12. Indemnification. Each party shall indemnify the other for claims arising from its "
         "own breach, subject in each case to the limitation of liability set forth in Section 9.",
         "ESTABLISHED", notes="Reciprocal opener combined with a cross-reference applying to "
         "both directions equally."),
]

# ===========================================================================
# FINAL AF10 (compound) TOP-UP — reach >=30 total across the battery.
# ===========================================================================
CASES += [
    case("fab-ind-af10-nonoperative-plus-plausible-value-01", "indemnification", ["AF10", "AF6", "AF2"],
         "Sample clause for reference only (not part of this Agreement): \"Vendor shall indemnify "
         "Customer up to $5,000,000.\" The actual, operative indemnification clause is Section 12: "
         "Vendor shall indemnify Customer for claims arising from IP infringement, capped at "
         "$500,000.",
         "ESTABLISHED", {"actor": "Vendor", "beneficiary": "Customer"},
         notes="A decoy, explicitly non-operative $5M figure precedes the REAL, operative $500K "
               "clause -- must extract from the real clause, not the sample."),
    case("fab-lia-af10-nonoperative-plus-plausible-value-01", "liability", ["AF10", "AF6", "AF2"],
         "For illustration only, a sample cap might read \"$10,000,000.\" This illustration is not "
         "part of the Agreement. 12. Limitation of Liability. Aggregate liability shall not exceed "
         "$1,250,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 1250000.0}, expected_dimension="general_cap",
         notes="Decoy illustrative figure explicitly marked non-operative, followed by the real "
               "clause."),
    case("fab-pay-af10-nonoperative-plus-plausible-value-01", "payment_terms", ["AF10", "AF6", "AF2"],
         "A sample payment clause might read \"Net 90.\" This sample is not part of the operative "
         "Agreement. 9. Payment Terms. Buyer shall pay Provider within Net 30 days of receipt of "
         "invoice.",
         "ESTABLISHED", {"net_days": 30.0}, expected_dimension="net_days",
         notes="Decoy Net-90 sample explicitly marked non-operative, followed by the real Net-30 "
               "clause."),
    case("fab-ind-af10-multivalue-plus-ownership-01", "indemnification", ["AF10", "AF2", "AF7"],
         "12. Indemnification. Vendor shall indemnify Customer for claims arising from Vendor's "
         "breach, capped at $500,000. Vendor's Affiliate, Northline Services Co., separately shall "
         "indemnify Customer for claims arising from the Affiliate's own conduct, capped at "
         "$250,000.",
         "ESTABLISHED", {"actor": "Vendor", "beneficiary": "Customer"},
         notes="Two obligations with two DIFFERENT values for two DIFFERENT (related but "
               "distinct) obligors -- scores the first; the value must not be attributed to the "
               "wrong obligor."),
    case("fab-lia-af10-multivalue-different-parties-01", "liability", ["AF10", "AF2"],
         "12. Limitation of Liability. Distributor's liability in the aggregate is limited to "
         "$325,000. Manufacturer's own aggregate liability under this same Section is capped "
         "separately at $1,750,000.",
         "ESTABLISHED", {"kind": "fixed", "fixed_amount": 325000.0}, expected_dimension="general_cap",
         notes="CORRECTED after the overlap check: the original text reused 'Vendor's aggregate "
               "liability shall not exceed $X' near-verbatim from a Phase 2 DEV benchmark case "
               "(15+ shared words) -- a genuine independence violation, not merely expected "
               "boilerplate phrase overlap. Rewritten with different role names/figures and "
               "'is limited to' / 'is capped separately at' phrasing (both within this adapter's "
               "existing recognized vocabulary) while preserving the same test intent: two "
               "DIFFERENT values for two DIFFERENT named parties, scoring the FIRST-stated "
               "value."),
    case("fab-pay-af10-role-reversal-plus-multivalue-01", "payment_terms", ["AF10", "AF7"],
         "9. Payment Terms. Distributor shall pay Studio a royalty within Net 60 days of quarter "
         "end. Studio shall separately reimburse Distributor for approved marketing costs within "
         "Net 30 days of receipt of invoice.",
         "ESTABLISHED", {"net_days": 60.0}, expected_dimension="net_days",
         notes="Two different Net-day figures for two different, role-reversed payment "
               "directions in the same clause -- scores the FIRST."),
]
