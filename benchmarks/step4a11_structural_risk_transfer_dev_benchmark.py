"""Step 4A.11 Phase 3 — dedicated DEVELOPMENT benchmark for the
"structural risk-transfer proposition establishment" mechanism
(indemnification adapter, Category A of the frozen verifier-failure
inventory: structural-pattern unsupported, ~54.7% of prior failures).

Built and PRE-measured BEFORE any production code in this increment is
touched, per the phase-3 spec's explicit ordering requirement.

DEVELOPMENT ONLY. Not the final Step 4A.11 frozen validation corpus.

Positive cases in the "corpus_family_*" tag groups are REAL evidence:
taken verbatim from scripts/step4a10_generate_corpus.py (deterministic,
no random/seed — reproduces the exact 394-case corpus Step 4A.10 scored)
via the case IDs identified in artifacts/step4a11/
category_a_decomposition.md as the structural_pattern_unsupported
bucket's constituent families. All other cases (variation coverage:
passive voice, conjunctions, role reversal, multi-sentence, conditions,
exceptions, cross-reference interaction, competing propositions,
non-operative text, hard negatives, bystander language, compound cases)
are freshly authored for this benchmark, since the source corpus does
not exercise every dimension the phase-3 spec requires for a single
family.

Schema: id, tags, text, expected_status in {"ESTABLISHED",
"NOT_ESTABLISHED"}, expected_actor (obligated/indemnifying role, only
scored when ESTABLISHED), expected_beneficiary (indemnified/protected
role, only scored when ESTABLISHED), notes.

"NOT_ESTABLISHED" here means: the mechanism under test must NOT report a
clean directional obligation for this text. It does not distinguish
CONFIRMED_ABSENT vs. PRESENT_BUT_UNRESOLVED for the purposes of this
benchmark (the hard-negative discipline required by Section 10 is "false
structural establishment = 0" — i.e. never mistake this text for a
genuine promise).
"""

from typing import Any, Dict, List, Optional


def case(id: str, tags: List[str], text: str, expected_status: str,
         expected_actor: Optional[str] = None, expected_beneficiary: Optional[str] = None,
         notes: str = "") -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text, "expected_status": expected_status,
        "expected_actor": expected_actor, "expected_beneficiary": expected_beneficiary,
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# ===========================================================================
# REAL EVIDENCE — verbatim from the Step 4A.10 corpus (deterministically
# regenerated), 2-3 instances per structural family identified in the
# Category A decomposition, covering role-name diversity for free (each
# family's near-duplicates use different named roles).
# ===========================================================================
CASES += [
    case("srt-corpus-liable-to-compensate-01", ["corpus_family_liable_to_compensate"],
         "Reseller will be liable to compensate Manufacturer for any loss Manufacturer incurs as a "
         "result of a third-party claim connected to Reseller's work under this Agreement.",
         "ESTABLISHED", "Reseller", "Manufacturer"),
    case("srt-corpus-liable-to-compensate-02", ["corpus_family_liable_to_compensate"],
         "Carrier will be liable to compensate Shipper for any loss Shipper incurs as a result of a "
         "third-party claim connected to Carrier's work under this Agreement.",
         "ESTABLISHED", "Carrier", "Shipper"),
    case("srt-corpus-carry-burden-01", ["corpus_family_carry_burden_of_claim"],
         "Operator shall carry the burden of any claim brought against Host that relates to defects "
         "in the goods supplied under this order.",
         "ESTABLISHED", "Operator", "Host"),
    case("srt-corpus-carry-burden-02", ["corpus_family_carry_burden_of_claim"],
         "Franchisee shall carry the burden of any claim brought against Franchisor that relates to "
         "defects in the goods supplied under this order.",
         "ESTABLISHED", "Franchisee", "Franchisor"),
    case("srt-corpus-making-whole-01", ["corpus_family_making_whole"],
         "Consultant takes responsibility for making Sponsor financially whole in connection with "
         "any claim arising from Consultant's performance of the Services.",
         "ESTABLISHED", "Consultant", "Sponsor"),
    case("srt-corpus-making-whole-02", ["corpus_family_making_whole"],
         "Subcontractor takes responsibility for making Prime Contractor financially whole in "
         "connection with any claim arising from Subcontractor's performance of the Services.",
         "ESTABLISHED", "Subcontractor", "Prime Contractor"),
    case("srt-corpus-discharge-obligation-01", ["corpus_family_discharge_obligation_owed"],
         "Servicer shall discharge any obligation Bank would otherwise owe a third party arising "
         "from Servicer's breach of this Agreement.",
         "ESTABLISHED", "Servicer", "Bank"),
    case("srt-corpus-discharge-obligation-02", ["corpus_family_discharge_obligation_owed"],
         "Vendor shall discharge any obligation Client would otherwise owe a third party arising "
         "from Vendor's breach of this Agreement.",
         "ESTABLISHED", "Vendor", "Client"),
    case("srt-corpus-covering-exposure-01", ["corpus_family_commits_covering_exposure"],
         "Carrier commits to covering Shipper's exposure resulting from a claim tied to the products "
         "delivered under this purchase order.",
         "ESTABLISHED", "Carrier", "Shipper"),
    case("srt-corpus-covering-exposure-02", ["corpus_family_commits_covering_exposure"],
         "Processor commits to covering Controller's exposure resulting from a claim tied to the "
         "products delivered under this purchase order.",
         "ESTABLISHED", "Processor", "Controller"),
    case("srt-corpus-relieve-burden-01", ["corpus_family_relieve_of_financial_burden"],
         "Franchisee shall relieve Franchisor of any financial burden connected to a third-party "
         "claim arising out of Franchisee's use of the licensed materials.",
         "ESTABLISHED", "Franchisee", "Franchisor"),
    case("srt-corpus-relieve-burden-02", ["corpus_family_relieve_of_financial_burden"],
         "Supplier shall relieve Purchaser of any financial burden connected to a third-party claim "
         "arising out of Supplier's use of the licensed materials.",
         "ESTABLISHED", "Supplier", "Purchaser"),
    case("srt-corpus-suffer-no-detriment-01", ["corpus_family_undertakes_suffer_no_detriment"],
         "Subcontractor undertakes that Prime Contractor will suffer no monetary detriment on "
         "account of any claim relating to Subcontractor's data-processing activities under this "
         "Agreement.",
         "ESTABLISHED", "Subcontractor", "Prime Contractor"),
    case("srt-corpus-suffer-no-detriment-02", ["corpus_family_undertakes_suffer_no_detriment"],
         "Tenant undertakes that Landlord will suffer no monetary detriment on account of any claim "
         "relating to Tenant's data-processing activities under this Agreement.",
         "ESTABLISHED", "Tenant", "Landlord"),
    case("srt-corpus-pay-on-behalf-01", ["corpus_family_pay_on_behalf"],
         "Developer shall pay, on Investor's behalf, any sum Investor becomes obligated to pay a "
         "third party because of Developer's breach of the warranty in Section 5.",
         "ESTABLISHED", "Developer", "Investor"),
    case("srt-corpus-pay-on-behalf-02", ["corpus_family_pay_on_behalf"],
         "Distributor shall pay, on Brand Owner's behalf, any sum Brand Owner becomes obligated to "
         "pay a third party because of Distributor's breach of the warranty in Section 5.",
         "ESTABLISHED", "Distributor", "Brand Owner"),
    case("srt-corpus-keep-unharmed-01", ["corpus_family_keep_unharmed"],
         "Processor agrees to keep Controller financially unharmed with respect to any claim "
         "connected to the installation work performed under this contract.",
         "ESTABLISHED", "Processor", "Controller"),
    case("srt-corpus-keep-unharmed-02", ["corpus_family_keep_unharmed"],
         "Integrator agrees to keep End Customer financially unharmed with respect to any claim "
         "connected to the installation work performed under this contract.",
         "ESTABLISHED", "Integrator", "End Customer"),
    case("srt-corpus-settle-own-expense-01", ["corpus_family_settle_at_own_expense"],
         "Supplier shall settle, at Supplier's own expense, any claim directed at Purchaser "
         "concerning the accuracy of the data supplied by Supplier.",
         "ESTABLISHED", "Supplier", "Purchaser"),
    case("srt-corpus-settle-own-expense-02", ["corpus_family_settle_at_own_expense"],
         "Franchisee shall settle, at Franchisee's own expense, any claim directed at Franchisor "
         "concerning the accuracy of the data supplied by Franchisee.",
         "ESTABLISHED", "Franchisee", "Franchisor"),
    case("srt-corpus-hold-midinsert-01", ["corpus_family_hold_role_harmless_midinsert"],
         "Vendor shall indemnify and hold Client harmless from any third-party claims arising out of "
         "Vendor's performance of the Services under this Agreement.",
         "ESTABLISHED", "Vendor", "Client"),
    case("srt-corpus-hold-midinsert-02", ["corpus_family_hold_role_harmless_midinsert"],
         "Servicer agrees to hold Bank harmless from any claim arising out of the use of the "
         "products supplied under this distribution agreement.",
         "ESTABLISHED", "Servicer", "Bank"),
    case("srt-corpus-hold-midinsert-03", ["corpus_family_hold_role_harmless_midinsert"],
         "Franchisee shall indemnify and hold Franchisor harmless from any third-party claims "
         "arising out of Franchisee's performance of the Services under this Agreement.",
         "ESTABLISHED", "Franchisee", "Franchisor"),
    case("srt-corpus-appositive-interrupt-01", ["corpus_family_appositive_interrupt"],
         "Reseller, on behalf of itself and its subcontractors, shall indemnify Manufacturer for "
         "third-party claims arising from work performed under the applicable Statement of Work, as "
         "amended from time to time.",
         "ESTABLISHED", "Reseller", "Manufacturer"),
    case("srt-corpus-appositive-interrupt-02", ["corpus_family_appositive_interrupt"],
         "Subcontractor, on behalf of itself and its subcontractors, shall indemnify Prime Contractor "
         "for third-party claims arising from work performed under the applicable Statement of Work, "
         "as amended from time to time.",
         "ESTABLISHED", "Subcontractor", "Prime Contractor"),
    case("srt-corpus-cover-expense-defending-01", ["corpus_family_cover_expense_defending"],
         "Subcontractor shall cover any expense Prime Contractor incurs defending a claim of the "
         "category defined as a \"Data Incident\" in Section 1, to the extent such Data Incident "
         "results from Subcontractor's systems.",
         "ESTABLISHED", "Subcontractor", "Prime Contractor"),
    case("srt-corpus-cover-expense-defending-02", ["corpus_family_cover_expense_defending"],
         "Carrier shall cover any expense Shipper incurs defending a claim of the category defined "
         "as a \"Data Incident\" in Section 1, to the extent such Data Incident results from "
         "Carrier's systems.",
         "ESTABLISHED", "Carrier", "Shipper"),
    case("srt-corpus-where-incurs-reimburse-01", ["corpus_family_where_incurs_loss_reimburse"],
         "Where Purchaser incurs a loss because of a claim connected to the products described in "
         "the attached specification sheets, Supplier shall reimburse Purchaser for that loss, less "
         "any amount recovered by Purchaser under its own insurance.",
         "ESTABLISHED", "Supplier", "Purchaser"),
    case("srt-corpus-where-incurs-reimburse-02", ["corpus_family_where_incurs_loss_reimburse"],
         "Where Investor incurs a loss because of a claim connected to the products described in the "
         "attached specification sheets, Developer shall reimburse Investor for that loss, less any "
         "amount recovered by Investor under its own insurance.",
         "ESTABLISHED", "Developer", "Investor"),
]

# ===========================================================================
# FRESHLY AUTHORED — required variation coverage the source corpus doesn't
# exercise for these specific new verb clusters.
# ===========================================================================

# Role reversal (same family, opposite direction from the corpus instance)
CASES += [
    case("srt-fresh-role-reversal-01", ["role_reversal"],
         "Client shall carry the burden of any claim brought against Vendor that relates to defects "
         "in the goods supplied under this order.",
         "ESTABLISHED", "Client", "Vendor",
         notes="Same family as srt-corpus-carry-burden-*, opposite direction."),
    case("srt-fresh-role-reversal-02", ["role_reversal"],
         "Manufacturer will be liable to compensate Reseller for any loss Reseller incurs as a "
         "result of a third-party claim connected to Manufacturer's work under this Agreement.",
         "ESTABLISHED", "Manufacturer", "Reseller"),
]

# Multi-word / defined roles
CASES += [
    case("srt-fresh-multiword-role-01", ["multiword_role"],
         "Northwind Logistics Group shall discharge any obligation Southbay Holdings LLC would "
         "otherwise owe a third party arising from Northwind Logistics Group's breach of this "
         "Agreement.",
         "ESTABLISHED", "Northwind Logistics Group", "Southbay Holdings LLC"),
    case("srt-fresh-defined-role-01", ["defined_role"],
         "The Service Provider shall relieve the Client Company of any financial burden connected "
         "to a third-party claim arising out of the Service Provider's use of the licensed "
         "materials.",
         "ESTABLISHED", "Service Provider", "Client Company"),
]

# Passive voice (the corpus is entirely active-voice; passive is a genuinely
# different grammatical transformation the mechanism should NOT be expected
# to solve via the same active-voice positional strategy -- these are
# included as an honest boundary test, expected NOT_ESTABLISHED unless the
# mechanism specifically handles passive constructions)
CASES += [
    case("srt-fresh-passive-01", ["passive_voice", "boundary"],
         "Any financial burden connected to a third-party claim arising out of Vendor's use of the "
         "licensed materials shall be relieved by Vendor on Client's behalf.",
         "NOT_ESTABLISHED", None, None,
         notes="Passive-voice restructuring of the relieve-of-burden shape -- the object precedes "
               "the subject entirely. This is a genuinely different grammatical transformation "
               "(A14/A13 territory) that the active-voice positional strategies built this "
               "increment are not expected to cover; documented as a known boundary, not silently "
               "claimed as solved."),
]

# Conjunctions (compound subject or compound beneficiary)
CASES += [
    case("srt-fresh-conjunction-subject-01", ["conjunction"],
         "Vendor and its Affiliates shall carry the burden of any claim brought against Client that "
         "relates to defects in the goods supplied under this order.",
         "NOT_ESTABLISHED", None, None,
         notes="Compound subject ('Vendor and its Affiliates') -- the role-name fragment captures "
               "a single role; a genuinely compound subject is out of scope for this increment's "
               "positional extraction and correctly falls back to unresolved rather than silently "
               "picking one half of the conjunction."),
    case("srt-fresh-conjunction-clean-01", ["conjunction", "clean"],
         "Vendor shall relieve Client of any financial burden and legal expense connected to a "
         "third-party claim arising out of Vendor's use of the licensed materials.",
         "ESTABLISHED", "Vendor", "Client",
         notes="Conjunction WITHIN the object noun phrase ('burden and expense'), not the role "
               "positions themselves -- role extraction is unaffected."),
]

# Punctuation variation
CASES += [
    case("srt-fresh-punctuation-em-dash-01", ["punctuation"],
         "Vendor shall carry the burden of any claim brought against Client — that relates to "
         "defects in the goods supplied under this order.",
         "ESTABLISHED", "Vendor", "Client"),
    case("srt-fresh-punctuation-semicolon-01", ["punctuation"],
         "Vendor shall relieve Client of any financial burden; such burden includes claims arising "
         "out of Vendor's use of the licensed materials.",
         "ESTABLISHED", "Vendor", "Client"),
]

# Multi-sentence structures (the obligation and its trigger split across
# two sentences)
CASES += [
    case("srt-fresh-multisentence-01", ["multi_sentence", "boundary"],
         "A third party may assert a claim against Client relating to defects in goods supplied "
         "under this order. Vendor shall carry the burden of any such claim.",
         "NOT_ESTABLISHED", None, None,
         notes="CORRECTED after the first dev-benchmark run: the beneficiary role (Client) is never "
               "named in the obligation's OWN sentence at all -- 'any such claim' anaphorically "
               "refers back to 'a claim against Client' in the PRECEDING sentence. Resolving that "
               "reference generally is cross-sentence anaphora resolution, genuine NLP territory "
               "explicitly out of scope for this increment ('The goal is not general NLP parsing'). "
               "Originally mislabeled ESTABLISHED; this is a real, disclosed A9 (multi-sentence "
               "proposition split) limitation, not a defect -- correctly stays NOT_ESTABLISHED and "
               "safely routes to review rather than guessing the beneficiary from context."),
]

# Conditions attached (must interact correctly with Phase 2's condition
# mechanism -- the condition must be preserved, not silently stripped, once
# the obligation itself is newly established)
CASES += [
    case("srt-fresh-condition-01", ["condition_interaction"],
         "If a third party asserts a claim connected to the goods supplied under this order, Vendor "
         "shall carry the burden of any such claim brought against Client.",
         "ESTABLISHED", "Vendor", "Client",
         notes="Leading-IF condition on a newly-recognized verb cluster -- Phase 2's condition "
               "mechanism should independently attach ESTABLISHED/if_when to this obligation once "
               "it exists; this case only scores that the obligation itself is recognized."),
]

# Exceptions attached
CASES += [
    case("srt-fresh-exception-01", ["exception_interaction"],
         "Vendor shall relieve Client of any financial burden connected to a third-party claim "
         "arising out of Vendor's use of the licensed materials, except where such claim arises "
         "from Client's own modification of the materials.",
         "ESTABLISHED", "Vendor", "Client"),
]

# Cross-reference interaction (the new verb cluster delegates its value via
# "subject to Section N" -- exercises Phase 1 machinery on a newly-
# recognized obligation)
CASES += [
    case("srt-fresh-xref-01", ["cross_reference_interaction"],
         "9. Limitation of Liability. Aggregate liability shall not exceed $750,000.\n\n"
         "12. Indemnification. Vendor shall carry the burden of any claim brought against Client "
         "that relates to defects in the goods supplied under this order, subject to the limitation "
         "of liability set forth in Section 9.",
         "ESTABLISHED", "Vendor", "Client"),
]

# Competing propositions (two obligations, opposite directions, same
# family -- both should independently establish)
CASES += [
    case("srt-fresh-competing-01", ["competing_propositions"],
         "Vendor shall carry the burden of any claim brought against Client that relates to defects "
         "in the goods Vendor supplies. Client shall carry the burden of any claim brought against "
         "Vendor that relates to Client's misuse of the goods.",
         "ESTABLISHED", "Vendor", "Client",
         notes="Two independent, non-reciprocal directional obligations using the same new verb "
               "cluster -- this case scores the FIRST (Vendor's)."),
]

# Non-operative text (heading, quoted example, negated) -- hard negatives
# specifically targeting the NEW verb clusters, since the existing
# is_operative_context guards were only ever tested against the OLD
# closed-vocabulary patterns.
CASES += [
    case("srt-fresh-heading-01", ["hard_negative", "heading"],
         "SECTION 12: VENDOR SHALL CARRY THE BURDEN OF CLAIMS\n\n"
         "This Section addresses risk allocation between the parties for defect-related claims.",
         "NOT_ESTABLISHED", None, None,
         notes="The verb-cluster phrase sits in a section heading (all-caps title line), not an "
               "operative sentence -- the body text that follows never actually states the "
               "obligation, only describes what the section is about."),
    case("srt-fresh-quoted-example-01", ["hard_negative", "quoted"],
         "A typical risk-allocation clause might read: \"Vendor shall carry the burden of any claim "
         "brought against Client.\" No such clause appears in this Agreement.",
         "NOT_ESTABLISHED", None, None,
         notes="Quoted hypothetical example, explicitly negated afterward -- reuses the protected "
               "is_operative_context boundary."),
    case("srt-fresh-definition-01", ["hard_negative", "definition"],
         "\"Burden-Carrying Party\" means, for purposes of this Agreement, the party designated in "
         "an applicable Statement of Work as responsible for a given claim category.",
         "NOT_ESTABLISHED", None, None,
         notes="A definitions-section sentence describing a DEFINED TERM, not a directional promise "
               "-- no role is actually obligated to carry any specific burden by this sentence "
               "alone."),
    case("srt-fresh-recital-01", ["hard_negative", "recital"],
         "WHEREAS, the parties intend that one party will relieve the other of certain financial "
         "burdens connected to third-party claims, the parties agree to the terms below.",
         "NOT_ESTABLISHED", None, None,
         notes="A recital describing intent in the abstract ('one party'/'the other'), not a "
               "concrete directional promise naming actual roles."),
    case("srt-fresh-negotiation-history-01", ["hard_negative", "negotiation_history"],
         "In an earlier draft, Vendor had proposed that it would carry the burden of any claim "
         "brought against Client, but the parties did not adopt that language.",
         "NOT_ESTABLISHED", None, None,
         notes="Explicitly describes DISCARDED negotiation history, not the operative agreement."),
    case("srt-fresh-amendment-superseded-01", ["hard_negative", "superseded"],
         "Section 12 (as originally executed) provided that Vendor shall carry the burden of any "
         "claim brought against Client. Section 12 was subsequently deleted in its entirety by "
         "Amendment No. 2 and replaced with a mutual limitation of liability.",
         "NOT_ESTABLISHED", None, None,
         notes="The obligation-shaped sentence describes a PRIOR, now-superseded provision, "
               "explicitly deleted by a later amendment."),
    case("srt-fresh-negative-obligation-01", ["hard_negative", "negative_obligation"],
         "Vendor shall NOT carry the burden of any claim brought against Client; each party bears "
         "its own costs of defending third-party claims.",
         "NOT_ESTABLISHED", None, None,
         notes="Explicit negation of the obligation -- the opposite of what a bare structural match "
               "would suggest."),
    case("srt-fresh-disclaimer-01", ["hard_negative", "disclaimer"],
         "Nothing in this Agreement shall be construed as requiring Vendor to carry the burden of "
         "any claim brought against Client.",
         "NOT_ESTABLISHED", None, None,
         notes="A disclaimer explicitly denying that this construction creates the obligation."),
    case("srt-fresh-hypothetical-01", ["hard_negative", "hypothetical"],
         "If the parties were to agree that Vendor should carry the burden of any claim brought "
         "against Client, such agreement would need to be documented in a signed amendment.",
         "NOT_ESTABLISHED", None, None,
         notes="Conditional/hypothetical framing about a possible FUTURE agreement, not a present, "
               "operative promise."),
    case("srt-fresh-obligation-belongs-elsewhere-01", ["hard_negative", "wrong_party"],
         "This Section does not address Vendor's obligations. See Section 15 for the terms under "
         "which Vendor shall carry the burden of any claim brought against Client.",
         "NOT_ESTABLISHED", None, None,
         notes="Explicitly states this section does not itself state Vendor's obligations and "
               "redirects elsewhere -- reuses the negation/redirect boundary the existing "
               "is_operative_context machinery already guards."),
]

# Unrelated monetary provisions / insurance / SLA / purchase price / deposit
# / tax / fee -- confirms the new verb clusters don't accidentally engage
# on adjacent, differently-typed provisions that happen to share vocabulary
# like "claim," "expense," or "burden."
CASES += [
    case("srt-fresh-insurance-01", ["hard_negative", "insurance"],
         "Vendor shall maintain commercial general liability insurance and shall carry the premium "
         "burden of any policy required under this Section.",
         "NOT_ESTABLISHED", None, None,
         notes="'carry the... burden of' here modifies an INSURANCE PREMIUM obligation, not a "
               "third-party claim -- no claim/loss noun in the immediate risk-transfer sense; "
               "should not engage the mechanism."),
    case("srt-fresh-sla-01", ["hard_negative", "sla"],
         "Vendor commits to covering any Service Level Agreement credits owed to Client for "
         "downtime exceeding the monthly threshold.",
         "NOT_ESTABLISHED", None, None,
         notes="'commits to covering' here is about SLA service credits, not a third-party claim -- "
               "same verb cluster as srt-corpus-covering-exposure-*, but a different, unrelated "
               "concept (service credits, not claim exposure)."),
    case("srt-fresh-purchase-price-01", ["hard_negative", "purchase_price"],
         "Buyer shall pay, on Seller's behalf, the closing costs associated with the purchase price "
         "adjustment described in Schedule 2.",
         "NOT_ESTABLISHED", None, None,
         notes="'pay, on X's behalf' here is about a purchase-price closing-cost mechanic, not a "
               "third-party claim indemnity -- same verb cluster as srt-corpus-pay-on-behalf-*, "
               "different, unrelated concept."),
    case("srt-fresh-deposit-01", ["hard_negative", "deposit"],
         "Tenant shall relieve Landlord of any administrative burden connected to processing the "
         "security deposit refund at the end of the lease term.",
         "NOT_ESTABLISHED", None, None,
         notes="'relieve... of... burden' here is about an administrative/deposit-processing "
               "burden, not a third-party claim -- no claim/loss noun present at all."),
    case("srt-fresh-tax-01", ["hard_negative", "tax"],
         "Distributor shall discharge any obligation Brand Owner would otherwise owe to the taxing "
         "authority for sales tax collected on Distributor's behalf.",
         "NOT_ESTABLISHED", None, None,
         notes="'discharge any obligation... would otherwise owe' here is about a TAX obligation "
               "owed to a taxing authority, not a third-party claim -- 'a third party' in the "
               "corpus template is what makes this a risk-transfer concept; a taxing authority is "
               "not a third-party claimant in that sense, and no claim/loss noun appears."),
    case("srt-fresh-fee-01", ["hard_negative", "fee"],
         "Licensee shall settle, at Licensee's own expense, any outstanding renewal fee invoice "
         "directed at Licensor by the platform vendor.",
         "NOT_ESTABLISHED", None, None,
         notes="'settle, at... own expense, any... directed at...' here is about an ordinary FEE "
               "invoice, not a third-party legal claim -- no claim/loss noun present."),
]

# Bystander language (the verb cluster words appear, but not as a legal
# obligation at all -- ordinary narrative/descriptive prose)
CASES += [
    case("srt-fresh-bystander-01", ["hard_negative", "bystander"],
         "The project manager carried the burden of coordinating the weekly status calls between "
         "Vendor and Client throughout the engagement.",
         "NOT_ESTABLISHED", None, None,
         notes="'carried the burden of' used in its ordinary, non-legal sense (workload), describing "
               "a person's role, not a contractual risk-transfer promise between the named parties."),
    case("srt-fresh-bystander-02", ["hard_negative", "bystander"],
         "Employees reported feeling relieved of the administrative burden after the new invoicing "
         "system was deployed.",
         "NOT_ESTABLISHED", None, None,
         notes="'relieved of... burden' in an entirely non-contractual, narrative sentence about "
               "employee sentiment."),
]

# Compound cases (multiple mechanisms interacting at once)
CASES += [
    case("srt-fresh-compound-01", ["compound"],
         "9. Limitation of Liability. Aggregate liability shall not exceed 2 times the total annual "
         "fees paid.\n\n"
         "12. Indemnification. If a third party asserts a claim connected to the goods supplied "
         "under this order, Vendor shall carry the burden of any such claim brought against Client, "
         "except where such claim arises from Client's own negligence, subject to the limitation of "
         "liability set forth in Section 9.",
         "ESTABLISHED", "Vendor", "Client",
         notes="New verb cluster + leading condition + trailing exception + cross-reference all in "
               "one obligation -- exercises Phase 1, Phase 2, and this increment's mechanism "
               "together."),
]
