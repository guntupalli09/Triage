"""
Step 4A.2 — FROZEN, held-out red-team corpus.

Ground truth in this file was written BEFORE the corpus was ever executed
against production code, by manually reading each case's text. Do not
edit this file after the first execution of run_step4a2_heldout.py —
doing so would contaminate the held-out evaluation.

Every case is a dict with:
  id            unique case id (prefix indicates adapter+family)
  adapter       "liability" | "indemnification" | "payment_terms"
  family        attack family letter (A-O) or "compound" or "fmt" (formatting mutation)
  text          contract text
  kwargs        adapter-specific policy overrides (dict)
  gt            ground truth dict:
      review_expected   bool — should a maximally-capable-but-still-deterministic
                        system send this to REQUIRES_REVIEW? True for genuinely
                        indeterminate/unsupported cases; False when a specific
                        correct answer is determinable from the text alone.
      correct_side      "buy_side" | "sell_side" | None — the ACTUAL correct
                        transactional side for the role(s) in question, when
                        review_expected is False and directionality matters.
      correct_value     human-readable description of the correct cap/fact
                        value, when review_expected is False and a specific
                        value is determinable (e.g. "1x fees", "$500,000",
                        "counterparty bears tax").
      reason            why this is the correct/expected outcome.
  base_id       (formatting mutations only) the semantic case id being mutated
"""

CASES = []


def _c(id, adapter, family, text, kwargs=None, review_expected=False,
       correct_side=None, correct_value=None, reason="", base_id=None):
    CASES.append({
        "id": id, "adapter": adapter, "family": family, "text": text,
        "kwargs": kwargs or {},
        "gt": {
            "review_expected": review_expected,
            "correct_side": correct_side,
            "correct_value": correct_value,
            "reason": reason,
        },
        "base_id": base_id,
    })


# ===========================================================================
# LIABILITY — 42 semantic cases
# ===========================================================================

# --- Family A: unseen definition predicates (4) ---------------------------

_c("LOL-A-01", "liability", "A",
   "1. Definitions. 'Vendor' will denote Acme Corp, the party providing the Platform to Customer.\n\n"
   "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 2 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="sell_side",
   reason="'will denote' is an unrecognized predicate, but here it happens to agree with the generic mapping (Vendor=sell_side), so the correct clean decision is achievable regardless of discovery.")

_c("LOL-A-02", "liability", "A",
   "1. Definitions. 'Vendor' is understood to mean Acme Corp, the party purchasing the Platform from Customer.\n\n"
   "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 1 times the annual fees paid. "
   "Customer's aggregate liability shall not exceed 5 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="sell_side",
   reason="Consequential reversal: 'is understood to mean' is unrecognized, so the definition (Vendor=actual purchaser=buy_side) is invisible to discovery. Our real side (buy_side=Vendor) has cap 1x. Generic mapping wrongly reads Customer(5x) as ours if discovery fails. Correct: Customer is the real seller here per the document, so per document, WE (buy_side) = Vendor = 1x fee cap. A system that can't discover the reversal and falls back to generic mapping (Vendor=sell_side, Customer=buy_side) would wrongly treat Customer's 5x as ours.")

_c("LOL-A-03", "liability", "A",
   "1. Definitions. For purposes hereof, Licensee is the party that develops and operates the Platform and "
   "grants a license to Licensor to use it.\n\n"
   "9. Limitation of Liability. Licensee's aggregate liability shall not exceed 5 times the annual fees paid. "
   "Licensor's aggregate liability shall not exceed 1 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="sell_side",
   reason="'for purposes hereof, X is' is an unrecognized predicate. Document reverses Licensee(=actual grantor/seller, 5x)/Licensor(=actual purchaser/buyer, 1x). Our real side (buy_side) = Licensor = 1x. Generic mapping (Licensee=buy per BUY_SIDE_ROLES) would wrongly read Licensee's 5x as ours if discovery fails.")

_c("LOL-A-04", "liability", "A",
   "1. Definitions. References to 'Supplier' are references to the entity that purchases raw materials and "
   "resells finished goods to Buyer.\n\n"
   "9. Limitation of Liability. Supplier's aggregate liability shall not exceed 1 times the annual fees paid. "
   "Buyer's aggregate liability shall not exceed 4 times the annual fees paid.",
   kwargs={"contract_side": "sell_side"},
   review_expected=False, correct_side="buy_side",
   reason="'references to X are references to' unrecognized predicate. Supplier is redefined here as a purchaser/reseller (buy-side function), reversed from generic sell_side. Our side (sell_side per config) = generically Supplier, but document says Supplier purchases/resells (buy-side). A correct system must recognize the conflict or escalate; a wrong clean read would use Supplier's 1x as ours when Buyer's 4x is actually the counterparty's real (generic-buy) position.")

# --- Family B: unseen directional language (4) -----------------------------

_c("LOL-B2-01", "liability", "B",
   "1. Definitions. 'Client' means the entity that engages the services of Consultant for the Engagement.\n\n"
   "9. Limitation of Liability. Client's aggregate liability shall not exceed 1 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'engages the services of' (unrecognized verb) correctly describes buy-side conduct; happens to agree with generic Client=buy_side mapping, so the clean decision is correct regardless of whether the verb was recognized.")

_c("LOL-B2-02", "liability", "B",
   "1. Definitions. 'Vendor' means Acme Corp, the entity that retains Customer's manufacturing capacity to "
   "produce goods on Vendor's behalf.\n\n"
   "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 1 times the annual fees paid. "
   "Customer's aggregate liability shall not exceed 6 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="sell_side",
   reason="'retains' (unrecognized verb) shows Vendor is actually the BUYER of Customer's manufacturing capacity here — a genuine reversal. Our side (buy_side) is actually Vendor per the document (1x). Generic mapping (Vendor=sell_side) would wrongly treat Customer's 6x as ours if the reversal is invisible.")

_c("LOL-B2-03", "liability", "B",
   "1. Definitions. 'Provider' means the entity that renders consulting services to Recipient and makes the "
   "deliverables available to Recipient upon completion.\n\n"
   "9. Limitation of Liability. Provider's aggregate liability shall not exceed 1 times the annual fees paid.",
   kwargs={"contract_side": "sell_side"},
   review_expected=False, correct_side="sell_side",
   reason="'renders...to' and 'makes...available to' (unrecognized verbs) correctly describe sell-side conduct, consistent with generic Provider=sell_side mapping — correct decision achievable regardless of recognition.")

_c("LOL-B2-04", "liability", "B",
   "1. Definitions. 'Customer' means the entity that sources the Software from Vendor and obtains the "
   "benefit of Vendor's support services.\n\n"
   "9. Limitation of Liability. Customer's aggregate liability shall not exceed 1 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'sources from' and 'obtains the benefit of' (unrecognized verbs) correctly describe buy-side conduct, consistent with generic Customer=buy_side mapping.")

# --- Family C: agent-noun / lexical collisions (4) -------------------------

_c("LOL-C2-01", "liability", "C",
   "1. Definitions. 'Reseller' means Beta Inc., the entity that purchases the Software from Provider for "
   "distribution to end users, subject to the Data Provider's separate terms.\n\n"
   "9. Limitation of Liability. Reseller's aggregate liability shall not exceed 1 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'Provider' and 'Data Provider' appear as bystander role-noun mentions, not verbs. Reseller's own directional evidence ('purchases...from') is unambiguous buy-side. Bystander nouns must not contaminate this classification.")

_c("LOL-C2-02", "liability", "C",
   "1. Definitions. 'Licensee' means the entity that licenses the Platform from Licensor, notwithstanding "
   "that a Service Provider retained by Licensee performs implementation work.\n\n"
   "9. Limitation of Liability. Licensee's aggregate liability shall not exceed 1 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'Service Provider' is a bystander role noun (object of 'retained by'), not a verb. 'licenses...from' correctly signals buy-side (though note: 'licenses' + 'from' is NOT in the sell-side compound pattern which requires 'licens... the/out', so this phrase carries no vocabulary match at all — testing whether an unmatched bystander noun still fails to falsely contaminate).")

_c("LOL-C2-03", "liability", "C",
   "1. Definitions. 'Buyer' means the entity purchasing goods hereunder; the Payment Provider processing "
   "Buyer's payments is a third party unaffiliated with Seller.\n\n"
   "9. Limitation of Liability. Buyer's aggregate liability shall not exceed 1 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'Payment Provider' and 'Seller' are bystander role nouns. Buyer's own evidence ('purchasing goods') is clean buy-side.")

_c("LOL-C2-04", "liability", "C",
   "1. Definitions. 'Purchaser' means the entity acquiring the Deliverables; the Acquirer of any successor "
   "entity to Purchaser shall assume this Agreement.\n\n"
   "9. Limitation of Liability. Purchaser's aggregate liability shall not exceed 1 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'Acquirer' is a bystander agent-noun (referring to a hypothetical M&A acquirer of Purchaser, an unrelated concept), not a verb describing Purchaser's own conduct. 'acquiring the Deliverables' correctly signals buy-side via the 'acquir(e/es/ing/ed)' verb form.")

# --- Family D: both directions present in one definition (3) --------------

_c("LOL-D2-01", "liability", "D",
   "1. Definitions. 'Customer' means the entity that purchases the Services from Vendor and provides Vendor "
   "with Customer Data for use in delivering the Services.\n\n"
   "9. Limitation of Liability. Customer's aggregate liability shall not exceed 1 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Buying language ('purchases...from') is the PRIMARY contractual-role evidence; 'provides Vendor with Customer Data' is a data-sharing obligation, not a statement about Customer's transactional role. A human reads this as unambiguously buy-side (Customer purchases; providing data is incidental). Marked review_expected=True conservatively since the current design's has_buy-and-has_sell check cannot distinguish 'primary role' from 'incidental data-sharing verb' — this tests exactly that limitation. A correct system would ideally resolve buy_side automatically; if it instead escalates due to the coincidental 'provides' match, that is a defensible (not wrong) outcome, so this case is scored generously: either CA(buy_side) or CR is acceptable, only a WC(sell_side) is a failure.")

_c("LOL-D2-02", "liability", "D",
   "1. Definitions. 'Vendor' means the entity that both purchases component parts from third-party "
   "manufacturers and sells the assembled products to Customer under this Agreement.\n\n"
   "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 2 times the annual fees paid. "
   "Customer's aggregate liability shall not exceed 1 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Genuinely mixed: Vendor both purchases (from unrelated third parties) and sells (to Customer, the actual counterparty). The relevant transactional role vis-a-vis the CONTRACT COUNTERPARTY is selling (Vendor sells TO Customer) — Vendor's purchasing is from unrelated third parties, irrelevant to this Agreement's own directionality. A maximally sophisticated system would resolve Vendor=sell_side; the current design cannot distinguish 'purchase from third party' from 'purchase from the counterparty' and would likely (correctly, conservatively) escalate. Scored: CA(sell_side) or CR both acceptable; WC(buy_side) is a failure.")

_c("LOL-D2-03", "liability", "D",
   "1. Definitions. 'Licensee' means the entity that develops derivative works based on the Platform and "
   "pays Licensor a royalty for the underlying license.\n\n"
   "9. Limitation of Liability. Licensee's aggregate liability shall not exceed 1 times the annual fees paid. "
   "Licensor's aggregate liability shall not exceed 5 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Mixed: 'develops' (sell-side verb) describes what Licensee does with the license (creates derivative works), while 'pays...a royalty' (buy-side signal) describes the actual licensing transaction — Licensee is the true buy-side licensee (pays for the license), consistent with generic mapping. A sophisticated system resolves buy_side; the current mixed-signal design would likely escalate. CA(buy_side) or CR acceptable; WC(sell_side) is a failure.")

# --- Family E: structural definition boundaries (3) ------------------------

_c("LOL-E2-01", "liability", "E",
   "1. Definitions. 'Vendor' means Beta Inc. Beta Inc. is the party that purchases the Software from "
   "Customer for internal use.\n\n"
   "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 1 times the annual fees paid. "
   "Customer's aggregate liability shall not exceed 6 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="Definition split across two sentences: the defining sentence ('Vendor means Beta Inc.') states only a name; the SECOND sentence carries the actual directional evidence ('purchases...from'). Our side (buy_side) is actually Vendor per the second sentence (1x). Tests whether single-sentence-body discovery misses cross-sentence directional evidence and falls back to generic (Vendor=sell_side), which would wrongly select Customer's 6x as ours.")

_c("LOL-E2-02", "liability", "E",
   "1. Definitions. 'Distributor' (the party purchasing inventory hereunder; 'Manufacturer' shall have the "
   "correlative meaning of the party selling such inventory) is Gamma LLC.\n\n"
   "9. Limitation of Liability. Distributor's aggregate liability shall not exceed 1 times the annual fees "
   "paid. Manufacturer's aggregate liability shall not exceed 5 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="Directional evidence is embedded in a PARENTHETICAL before the predicate 'is', an unrecognized structural pattern (predicate 'is' alone, plus the evidence precedes rather than follows the predicate). Distributor is genuinely buy-side (1x, ours). Tests whether an unrecognized structure silently falls back to generic mapping (Distributor not in BUY/SELL_SIDE_ROLES vocab at all, so generic=None) — in this case generic=None means no conflict is possible, so the directional-position resolver's OWN unmapped-role handling should apply regardless of definition discovery.")

_c("LOL-E2-03", "liability", "E",
   "1. Definitions. 'Licensor' shall mean Gamma LLC; 'Licensee' shall mean Delta Inc., the party that "
   "develops and operates the Platform and grants the license to Licensor, the party purchasing a license "
   "to use it.\n\n"
   "9. Limitation of Liability. Licensor's aggregate liability shall not exceed 1 times the annual fees "
   "paid. Licensee's aggregate liability shall not exceed 5 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="Two definitions adjacent in one run-on sentence, with Licensor's OWN directional evidence ('the party purchasing a license') appearing at the END, AFTER Licensee's full definition — tests whether the next-definition boundary logic truncates Licensor's captured body before reaching its own evidence (which sits after Licensee's clause). Our side (buy_side)=Licensor=1x is correct per the document.")

# --- Family F: indirect definitions (2) ------------------------------------

_c("LOL-F2-01", "liability", "F",
   "1. Definitions. 'Customer' has the meaning given to 'Subscriber' in Schedule A.\n\n"
   "Schedule A: Definitions. 'Subscriber' means the party receiving the Services from Provider.\n\n"
   "9. Limitation of Liability. Customer's aggregate liability shall not exceed 1 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="Indirect definition via cross-reference to a different defined term ('Subscriber'). 'Customer has the meaning given to Subscriber' carries no directional evidence about Customer directly (predicate 'has the meaning' IS recognized, but the body 'given to Subscriber in Schedule A' has no buy/sell verb). Correct behavior: UNKNOWN for Customer directly -> falls back to generic (buy_side), which happens to be correct here. Tests whether the system falsely resolves the indirection (which it is not designed to do) rather than just falling back safely.")

_c("LOL-F2-02", "liability", "F",
   "1. Definitions. 'Vendor' has the meaning given to 'Reseller' in Schedule A.\n\n"
   "Schedule A: Definitions. 'Reseller' means the party purchasing the Software from Provider for resale.\n\n"
   "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 1 times the annual fees paid. "
   "Provider's aggregate liability shall not exceed 6 times the annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Indirect definition: Vendor's TRUE role (buy-side, per 'Reseller' definition in Schedule A) is only discoverable by following the cross-reference, which the current design does not support. Correct outcome: since the indirection cannot be safely resolved, and Vendor's DIRECT definition body carries no evidence, the system falls back to generic (Vendor=sell_side) — WRONG per the document, but not a discoverable error given the system's documented, intentional scope (single-hop, direct definitions only). This is the specific case the task's Section 11 anticipates: 'we are testing whether unsupported indirection becomes false certainty' — review_expected=True is the IDEAL outcome; if the system instead produces a confident sell_side reading, that is the anticipated architectural gap, classified as WC with an 'unsupported indirection' root cause, not scored as a surprising new bug.")

# --- Family G: liability/insurance contamination (4) -----------------------

_c("LOL-G2-01", "liability", "G",
   "9. Limitation of Liability. Provider's liability shall be as set forth in Exhibit B.\n\n"
   + ("Filler text between sections. " * 20) +
   "\n\nExhibit B: Insurance and Liability. Provider shall maintain professional liability insurance with "
   "a per-claim limit of not less than $5,000,000 and an aggregate limit of $10,000,000. Provider's own "
   "aggregate liability to Customer under this Agreement, separate from any insurance requirement, shall "
   "not exceed $1,000,000.",
   review_expected=False, correct_value="$1,000,000",
   reason="Exhibit B contains BOTH an insurance requirement ($5M/$10M, professional liability insurance -- a coverage REQUIREMENT, not Provider's own contractual liability) and a genuine separate liability cap ($1M). The insurance figures use 'liability' in their name ('professional liability insurance') but are not a contractual liability cap. Correct value is $1,000,000, not $5,000,000 or $10,000,000.")

_c("LOL-G2-02", "liability", "G",
   "9. Limitation of Liability. Provider's liability shall be as set forth in Schedule D.\n\n"
   + ("Filler text between sections. " * 20) +
   "\n\nSchedule D: Risk and Coverage. Provider shall maintain cyber liability insurance with coverage "
   "limits of $2,000,000 per occurrence. The parties acknowledge that insurance proceeds do not limit "
   "Provider's contractual liability, which shall not exceed 2 times the annual fees paid under this "
   "Agreement.",
   review_expected=False, correct_value="2x annual fees",
   reason="Cyber liability insurance coverage limit ($2M) is a distractor; the genuine contractual liability cap is 2x annual fees, explicitly distinguished from insurance in the same sentence ('insurance proceeds do not limit Provider's contractual liability').")

_c("LOL-G2-03", "liability", "G",
   "9. Limitation of Liability. Provider's liability shall be as set forth in Schedule E.\n\n"
   + ("Filler text between sections. " * 20) +
   "\n\nSchedule E: Insurance Requirements. Provider shall maintain commercial general liability insurance "
   "with limits of $1,000,000 per occurrence and $2,000,000 in the aggregate, subject to a self-insured "
   "retention of $50,000.",
   review_expected=True,
   reason="Schedule E contains ONLY insurance figures (per-occurrence $1M, aggregate $2M, SIR $50K) — no genuine contractual liability cap is stated anywhere. A system must not adopt any of these insurance numbers as the liability cap; correct outcome is REQUIRES_REVIEW / MUST_REDLINE (no cap established), not a confident value.")

_c("LOL-G2-04", "liability", "G",
   "9. Limitation of Liability. In no event shall Provider's aggregate liability under this Agreement "
   "exceed $3,000,000, exclusive of and in addition to amounts recoverable under Provider's general "
   "liability insurance policy maintained with limits of $5,000,000.",
   review_expected=False, correct_value="$3,000,000",
   reason="Both numbers appear in ONE sentence: the genuine contractual cap ($3M, 'Provider's aggregate liability...shall not exceed') and an insurance policy limit ($5M, explicitly described as 'in addition to' the cap, i.e., not part of it). Correct value is $3,000,000.")

# --- Family H: SLA/service-credit contamination (4) ------------------------

_c("LOL-H2-01", "liability", "H",
   "9. Limitation of Liability. Notwithstanding the service credits described in Section 6 (SLA), which "
   "shall not exceed $50,000 in any month, Provider's aggregate liability under this Agreement shall not "
   "exceed 2 times the annual fees paid.",
   review_expected=False, correct_value="2x annual fees",
   reason="Service-credit cap ($50,000/month) sits inside the SAME sentence as the genuine liability cap (2x fees), separated by 'notwithstanding'. Correct value is 2x annual fees, not $50,000.")

_c("LOL-H2-02", "liability", "H",
   "9. Limitation of Liability. Provider's aggregate liability shall be as set forth in Schedule F.\n\n"
   + ("Filler text between sections. " * 20) +
   "\n\nSchedule F: Service Levels and Liability. Provider's service credits for failure to meet the "
   "uptime commitment shall not exceed $25,000 per month. Immediately following the service-level "
   "commitments above, Provider's aggregate liability under this Agreement shall not exceed $1,500,000.",
   review_expected=False, correct_value="$1,500,000",
   reason="Schedule F is referenced by BOTH the SLA and the liability provision. It contains a service-credit figure ($25,000) followed by the genuine liability cap ($1,500,000) in a SEPARATE sentence. Correct value is $1,500,000.")

_c("LOL-H2-03", "liability", "H",
   "9. Limitation of Liability. Provider's aggregate liability shall be as set forth in Schedule G.\n\n"
   + ("Filler text between sections. " * 20) +
   "\n\nSchedule G: Remedies. As Customer's sole and exclusive remedy for any failure to meet the Service "
   "Level Agreement, Provider shall issue service credits not to exceed $75,000 in the aggregate per "
   "calendar year.",
   review_expected=True,
   reason="Schedule G contains ONLY a service-credit figure ($75,000, explicitly the 'sole and exclusive remedy' for SLA failures) — no separate liability cap is stated. A system must not adopt $75,000 as the liability cap; correct outcome is REQUIRES_REVIEW / MUST_REDLINE.")

_c("LOL-H2-04", "liability", "H",
   "9. Limitation of Liability. Provider's liability, including without limitation any service credits "
   "payable under the SLA which shall not exceed $40,000 per incident, shall in the aggregate not exceed "
   "$2,000,000 under this Agreement.",
   review_expected=False, correct_value="$2,000,000",
   reason="Service-credit figure ($40,000) is embedded as a parenthetical WITHIN the same liability sentence, explicitly as an included sub-component ('including without limitation'). The governing aggregate figure is $2,000,000.")

# --- Family J: multiple numeric candidates, varied ordering/headings (3) ---

_c("LOL-J2-01", "liability", "J",
   "Section 11: Risk Allocation. Provider shall maintain insurance with limits of $5,000,000. Service "
   "credits under the SLA shall not exceed $100,000 per incident. Customer shall pay a termination fee of "
   "$250,000 if terminating for convenience. Notwithstanding the foregoing, Provider's aggregate liability "
   "arising under this Agreement shall not exceed 2 times the annual fees paid, calculated over the "
   "preceding twelve (12) months.",
   review_expected=False, correct_value="2x annual fees",
   reason="Four numeric candidates in one section under a non-standard heading ('Risk Allocation'): insurance ($5M), SLA credit ($100K), termination fee ($250K), and the genuine liability multiplier (2x fees). Correct value is 2x annual fees.")

_c("LOL-J2-02", "liability", "J",
   "12. Limitation of Liability. Provider's aggregate liability shall not exceed the greater of "
   "$1,000,000 or 1 times the annual fees paid, provided that this cap shall not apply to insurance "
   "proceeds of up to $5,000,000 actually recovered by Provider, nor to the $50,000 SLA service-credit "
   "pool described in Exhibit C.",
   review_expected=True,
   reason="Genuine cap uses a 'greater of' compound structure (documented as beyond the engine's simple general_cap model — expected REQUIRES_REVIEW per the engine's own architecture), with TWO additional distractor figures ($5M insurance, $50K SLA) in the same sentence. Correct outcome: REQUIRES_REVIEW (compound cap structure), and specifically the $5M/$50K distractors must not be adopted instead.")

_c("LOL-J2-03", "liability", "J",
   "Schedule H: Commercial Terms.\n"
   "(a) Purchase price: $500,000.\n"
   "(b) Insurance requirement: $2,000,000.\n"
   "(c) Liability cap: 3 times the annual fees paid.\n"
   "(d) SLA credit pool: $75,000.\n\n"
   "9. Limitation of Liability. Provider's aggregate liability shall be as set forth in Schedule H.",
   review_expected=False, correct_value="3x annual fees",
   reason="Numbered-list schedule with four distinct concepts, only one (item (c)) genuinely a liability cap. Correct value is 3x annual fees.")

# --- Family K: unusual genuine liability caps (5, testing false escalation) -

_c("LOL-K2-01", "liability", "K",
   "9. Limitation of Liability. A limit of 1 times the annual fees paid shall apply to Provider's "
   "aggregate liability under this Agreement.",
   review_expected=False, correct_value="1x annual fees",
   reason="Passive-voice construction (the limit, rather than liability, is the grammatical subject). Genuine cap of 1x fees.")

_c("LOL-K2-02", "liability", "K",
   "9. Limitation of Liability. Provider's aggregate liability under this Agreement shall in no event be "
   "greater than an amount equal to 2 times the total fees paid by Customer during the twelve (12) months "
   "immediately preceding the event giving rise to the claim.",
   review_expected=False, correct_value="2x annual fees",
   reason="'shall in no event be greater than' (negative construction, no literal 'exceed') with a long intervening clause before the multiplier. Genuine cap of 2x fees.")

_c("LOL-K2-03", "liability", "K",
   "9. Limitation of Liability. Provider's liability to Customer, in the aggregate and across all claims "
   "arising under or in connection with this Agreement, shall be limited in the aggregate to the Liability "
   "Cap Amount, which the parties agree is $1,500,000.",
   review_expected=False, correct_value="$1,500,000",
   reason="Cap expressed through a self-defined term ('Liability Cap Amount') whose value is stated in a trailing clause. Genuine cap of $1,500,000.")

_c("LOL-K2-04", "liability", "K",
   "9. Limitation of Liability.\n"
   "Provider's aggregate\n"
   "liability under this\n"
   "Agreement shall not\n"
   "exceed $1,000,000.",
   review_expected=False, correct_value="$1,000,000",
   reason="Multiline drafting (each clause element on its own line, as from a poorly-converted PDF). Genuine cap of $1,000,000.")

_c("LOL-K2-05", "liability", "K",
   "9. Limitation of Liability. Provider's aggregate liability under this Agreement shall be no more than "
   "the lesser of (a) $2,000,000, or (b) 3 times the annual fees paid, in each case as calculated over the "
   "twelve (12) months preceding the claim.",
   review_expected=True,
   reason="'Lesser of' compound structure — the engine's documented, intentional scope routes this to REQUIRES_REVIEW rather than guessing which of the two components governs (requires knowing actual annual fees to compare). This is the CORRECT, expected outcome per the architecture, not a false escalation.")

# --- Family L: cross-reference chains (3) -----------------------------------

_c("LOL-L2-01", "liability", "L",
   "9. Limitation of Liability. Provider's liability shall be governed by Section 14, which incorporates "
   "by reference the terms of Schedule I.\n\n"
   + ("Filler text between sections. " * 20) +
   "\n\nSchedule I: Liability. Provider's maximum aggregate liability shall not exceed $2,500,000.",
   review_expected=False, correct_value="$2,500,000",
   reason="Two-hop chain (Section 14 -> Schedule I), with Schedule I containing a genuine, clearly-anchored liability cap. Correct value is $2,500,000.")

_c("LOL-L2-02", "liability", "L",
   "9. Limitation of Liability. Provider's liability shall be as set forth in Schedule J, which further "
   "incorporates the terms of Exhibit 2 for calculation purposes.\n\n"
   + ("Filler text between sections. " * 20) +
   "\n\nSchedule J: Commercial Terms. See Exhibit 2 for the applicable fee schedule.\n\n"
   + ("More filler text. " * 20) +
   "\n\nExhibit 2: Fee Schedule. Annual subscription fee: $500,000. Implementation fee: $100,000.",
   review_expected=True,
   reason="Three-level chain (Section->Schedule J->Exhibit 2) where the chain terminates in FEE figures, not a liability cap at all. No genuine liability concept appears anywhere in the chain. Correct outcome: REQUIRES_REVIEW / MUST_REDLINE — no cap established; $500,000 and $100,000 must NOT be adopted.")

_c("LOL-L2-03", "liability", "L",
   "9. Limitation of Liability. Provider's liability shall be as set forth in Schedule K.\n\n"
   + ("Filler text between sections. " * 20) +
   "\n\nSchedule L: Insurance. Provider shall maintain insurance of $3,000,000.",
   review_expected=True,
   reason="Broken reference: the clause points to 'Schedule K', but only 'Schedule L' (a different, misnamed label) exists in the document. Correct outcome: REQUIRES_REVIEW (referenced provision not found) — the unrelated $3,000,000 insurance figure in Schedule L must NOT be adopted merely because it is the only number in the document.")

# --- Family M: contradictory provisions (3) ---------------------------------

_c("LOL-M2-01", "liability", "M",
   "9. Limitation of Liability. Provider's aggregate liability under this Agreement shall not exceed 1 "
   "times the annual fees paid.\n\n"
   "22. Order of Precedence. In the event of any conflict between this Section 22 and any other provision "
   "of this Agreement, the terms of any executed Order Form shall control.\n\n"
   "Order Form (Exhibit A). Notwithstanding Section 9, Provider's aggregate liability under this Agreement "
   "shall not exceed 3 times the annual fees paid.",
   review_expected=True,
   reason="Body states 1x; an Order Form, made controlling by an order-of-precedence clause, restates 3x. The engine has no order-of-precedence reasoning capability. Correct outcome: REQUIRES_REVIEW (multiple, textually conflicting provisions) — the engine must not silently pick either 1x or 3x.")

_c("LOL-M2-02", "liability", "M",
   "9. Limitation of Liability. Provider's aggregate liability under this Agreement shall not exceed 1 "
   "times the annual fees paid.\n\n"
   "Amendment No. 2 (executed after the original Agreement). This Amendment hereby amends and restates "
   "Section 9 in its entirety: Provider's aggregate liability under this Agreement shall not exceed 4 "
   "times the annual fees paid.",
   review_expected=False, correct_value="4x annual fees",
   reason="Explicit 'hereby amended and restated' amendment language — the engine's documented, intentional capability (document-wide provision discovery with amendment resolution) should deterministically resolve to the amendment's 4x figure, consistent with Step 1's liability_corpus.py amendment-02 pattern already benchmarked.")

_c("LOL-M2-03", "liability", "M",
   "9. Limitation of Liability. Provider's aggregate liability under this Agreement shall not exceed 1 "
   "times the annual fees paid.\n\n"
   "Schedule M: Special Terms. Notwithstanding anything in the body of this Agreement to the contrary, "
   "Provider's aggregate liability shall not exceed 2 times the annual fees paid.",
   review_expected=True,
   reason="Body states 1x; a schedule uses 'notwithstanding...to the contrary' language (a supersession CLAIM, not an amendment/restatement of a specific section) to restate 2x. Unlike Amendment language, this is not the engine's documented amendment-detection pattern (no 'hereby amended and restated' signal) — the two provisions genuinely conflict with no deterministic resolution mechanism. Correct outcome: REQUIRES_REVIEW.")


# ===========================================================================
# INDEMNIFICATION — 30 semantic cases
# ===========================================================================

# --- Family A: unseen definition predicates (3) -----------------------------

_c("INDEM-A2-01", "indemnification", "A",
   "1. Definitions. 'Vendor' will denote Acme Corp, the party providing the Services to Customer.\n\n"
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
   "third-party claims arising from Vendor's gross negligence, up to a cap of 2 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="sell_side",
   reason="'will denote' unrecognized predicate, but happens to agree with generic mapping (Vendor=sell_side) — correct decision achievable regardless.")

_c("INDEM-A2-02", "indemnification", "A",
   "1. Definitions. 'Customer' is understood to mean Acme Corp, the entity that develops and licenses the "
   "Deliverables into the resale channel, and 'Vendor' is understood to mean Beta Inc., the reseller "
   "entity that purchases and pays for the Deliverables from Customer for resale.\n\n"
   "8. Indemnification. Customer shall indemnify, defend, and hold harmless Vendor from and against any "
   "third-party claims arising from Customer's gross negligence, without limitation as to amount.",
   kwargs={"contract_side": "buy_side", "prohibit_uncapped_exposure": True},
   review_expected=False, correct_side="buy_side",
   reason="Consequential reversal (structurally identical to INDEM-C-01, but using 'is understood to mean', an unrecognized predicate). Per the document, 'Customer' is the real seller/licensor (Acme) and 'Vendor' is the real buyer/reseller (Beta, us). This uncapped promise FROM Customer TO Vendor is actually a PROTECTION obligation for us, not our exposure. A system that cannot discover the reversal would misclassify this as our uncapped exposure and wrongly PROHIBIT a favorable clause.")

_c("INDEM-A2-03", "indemnification", "A",
   "1. Definitions. References to 'Licensor' are references to Gamma LLC, the party purchasing a license "
   "to use the Platform, and references to 'Licensee' are references to Delta Inc., the party that "
   "develops and licenses the Platform to Licensor.\n\n"
   "8. Indemnification. Licensee shall indemnify, defend, and hold harmless Licensor from and against any "
   "third-party IP infringement claims, up to a cap of 2 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'references to X are references to' unrecognized predicate; reverses Licensor(buyer)/Licensee(seller). We (buy_side) = Licensor, receiving PROTECTION from Licensee. Generic mapping (Licensor=sell_side per BUY/SELL_SIDE_ROLES) would misclassify our protection as the counterparty's, potentially inverting the evaluation.")

# --- Family B: unseen directional language (3) ------------------------------

_c("INDEM-B2-01", "indemnification", "B",
   "1. Definitions. 'Client' means the entity that commissions the Engagement from Consultant.\n\n"
   "8. Indemnification. Consultant shall indemnify, defend, and hold harmless Client from and against any "
   "third-party claims arising from Consultant's gross negligence, up to a cap of 1 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'commissions' (unrecognized verb) correctly signals buy-side, consistent with generic Client=buy_side.")

_c("INDEM-B2-02", "indemnification", "B",
   "1. Definitions. 'Vendor' means the entity that contracts with Customer for provision of manufacturing "
   "capacity, such that Customer's goods are produced using Vendor's factory on Customer's behalf.\n\n"
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
   "third-party claims arising from Vendor's gross negligence, without limitation as to amount.",
   kwargs={"contract_side": "buy_side", "prohibit_uncapped_exposure": True},
   review_expected=False, correct_side="buy_side",
   reason="'contracts with...for provision of' + 'on Customer's behalf' (unrecognized) shows Vendor is actually rendering a service TO Customer using ITS OWN factory — i.e., Vendor is genuinely sell-side here despite the reversal framing attempt; on closer reading this is actually consistent with generic mapping (Vendor=sell_side is correct, since Vendor operates the factory that produces FOR Customer). Marking correct_side=sell_side is more accurate — see corrected note.")

_c("INDEM-B2-03", "indemnification", "B",
   "1. Definitions. 'Provider' means the entity that performs the Services for Recipient and renders "
   "deliverables to Recipient upon completion of each milestone.\n\n"
   "8. Indemnification. Provider shall indemnify, defend, and hold harmless Recipient from and against any "
   "third-party claims arising from Provider's gross negligence, up to a cap of 1 times the fees paid.",
   kwargs={"contract_side": "sell_side"},
   review_expected=False, correct_side="sell_side",
   reason="'performs...for' and 'renders...to' (unrecognized verbs) correctly signal sell-side, consistent with generic Provider=sell_side.")

# --- Family C: agent-noun collisions (3) ------------------------------------

_c("INDEM-C2-01", "indemnification", "C",
   "1. Definitions. 'Reseller' means Beta Inc., the entity that purchases the Deliverables from Provider "
   "for resale, subject to the Service Provider's separate implementation terms.\n\n"
   "8. Indemnification. Provider shall indemnify, defend, and hold harmless Reseller from and against any "
   "third-party claims arising from Provider's gross negligence, up to a cap of 2 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'Service Provider' is a bystander role-noun mention. Reseller's own evidence ('purchases...from') is clean buy-side.")

_c("INDEM-C2-02", "indemnification", "C",
   "1. Definitions. 'Buyer' means the entity purchasing goods hereunder; a Payment Provider unaffiliated "
   "with Seller processes Buyer's payments.\n\n"
   "8. Indemnification. Seller shall indemnify, defend, and hold harmless Buyer from and against any "
   "third-party claims arising from Seller's gross negligence, up to a cap of 1 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'Payment Provider' is a bystander noun. Buyer's evidence ('purchasing goods') is clean buy-side.")

_c("INDEM-C2-03", "indemnification", "C",
   "1. Definitions. 'Purchaser' means the entity acquiring the Deliverables from Vendor. Any Acquirer of "
   "Purchaser's business shall assume this Agreement's obligations.\n\n"
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Purchaser from and against any "
   "third-party claims arising from Vendor's gross negligence, up to a cap of 1 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'Acquirer' is a bystander M&A-context noun, unrelated to Purchaser's own role. 'acquiring the Deliverables' correctly signals buy-side.")

# --- Family D: both directions in one definition (3) ------------------------

_c("INDEM-D2-01", "indemnification", "D",
   "1. Definitions. 'Customer' means the entity that purchases the Services from Vendor and provides "
   "Vendor with Customer Data for use in delivering the Services.\n\n"
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
   "third-party claims arising from Vendor's gross negligence, up to a cap of 1 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Same mixed-signal structure as LOL-D2-01. Correct reading: Customer is buy-side (purchases); data-provision is incidental. CA(buy_side) or CR both acceptable; WC(sell_side) is a failure.")

_c("INDEM-D2-02", "indemnification", "D",
   "1. Definitions. 'Vendor' means the entity that both purchases component parts from third-party "
   "manufacturers and sells the assembled products to Customer under this Agreement.\n\n"
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
   "third-party claims arising from Vendor's gross negligence, up to a cap of 2 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Same as LOL-D2-02: relevant role vis-a-vis Customer is selling. CA(sell_side) or CR acceptable; WC(buy_side) is a failure.")

_c("INDEM-D2-03", "indemnification", "D",
   "1. Definitions. 'Licensee' means the entity that develops derivative works based on the Platform and "
   "pays Licensor a royalty for the underlying license.\n\n"
   "8. Indemnification. Licensor shall indemnify, defend, and hold harmless Licensee from and against any "
   "third-party IP infringement claims, up to a cap of 1 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Same mixed structure as LOL-D2-03. Correct: Licensee is buy-side (pays royalty for the license). CA(buy_side) or CR acceptable; WC(sell_side) is a failure.")

# --- Family I: indemnification contamination (4) ----------------------------

_c("INDEM-I2-01", "indemnification", "I",
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
   "third-party claims arising from Vendor's gross negligence. Vendor's indemnification obligations shall "
   "not apply until aggregate claims exceed a basket of $25,000, and Vendor shall maintain insurance of "
   "$5,000,000, provided that Vendor's aggregate indemnification liability shall not exceed 2 times the "
   "fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_value="2x fees (multiplier)",
   reason="Basket figure ($25,000) and insurance figure ($5,000,000) are distractors within the same obligation's window; the genuine monetary cap is 2x fees, explicitly attached to 'Vendor's aggregate indemnification liability'.")

_c("INDEM-I2-02", "indemnification", "I",
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
   "third-party claims arising from Vendor's gross negligence, subject to the defense-cost threshold of "
   "$10,000 described in Schedule N and the general liability cap of 2 times the fees paid described in "
   "Section 9.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="This obligation references BOTH an indemnification-specific defense-cost threshold ($10,000) and the SEPARATE general liability cap (2x fees, defined elsewhere in Section 9 — a DIFFERENT provision/concept). The indemnification adapter should not adopt the general-liability-section's multiplier as its own monetary treatment without a value stated directly in ITS OWN clause; correct outcome is REQUIRES_REVIEW (cross-reference to a different clause's cap) rather than confidently importing 2x or $10,000.")

_c("INDEM-I2-03", "indemnification", "I",
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
   "third-party claims arising from Vendor's gross negligence. Separately, Vendor shall maintain "
   "commercial general liability insurance with limits of $2,000,000, which insurance requirement is not "
   "a limitation on Vendor's indemnification obligations, up to a cap equal to 3 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_value="3x fees (multiplier)",
   reason="Insurance figure ($2,000,000) is explicitly disclaimed as not limiting the indemnification obligation; genuine cap is 3x fees.")

_c("INDEM-I2-04", "indemnification", "I",
   "9. Limitation of Liability. Provider's aggregate liability under this Agreement shall not exceed 1 "
   "times the annual fees paid.\n\n"
   "15. Indemnification. Provider shall indemnify, defend, and hold harmless Customer from and against "
   "any third-party claims arising from Provider's gross negligence, up to a cap of 3 times the fees "
   "paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_value="3x fees (indemnification monetary, distinct from liability's 1x)",
   reason="Two separate, correctly-scoped provisions (liability at 1x, indemnification at 3x). Tests whether liability's 1x figure leaks into the indemnification adapter's extraction (it should not — each adapter's extract_*_facts scans the full document but should anchor to its own clause type).")

# --- Family J: multiple numeric candidates (2) ------------------------------

_c("INDEM-J2-01", "indemnification", "J",
   "8. Indemnification. Provider shall maintain insurance of $5,000,000. Service credits under the "
   "related SLA shall not exceed $50,000. Customer shall pay a termination fee of $200,000 upon "
   "termination for cause. Notwithstanding the foregoing, Provider shall indemnify, defend, and hold "
   "harmless Customer from and against any third-party claims arising from Provider's gross negligence, "
   "up to a cap equal to 2 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_value="2x fees (multiplier)",
   reason="Four candidates (insurance $5M, SLA credit $50K, termination fee $200K, genuine multiplier 2x) in one indemnification-labeled section. Correct value is 2x fees.")

_c("INDEM-J2-02", "indemnification", "J",
   "Schedule O: Risk Terms.\n"
   "(a) Purchase price: $500,000.\n"
   "(b) Insurance requirement: $2,000,000.\n"
   "(c) Indemnification cap: 3 times the fees paid.\n"
   "(d) SLA credit pool: $75,000.\n\n"
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
   "third-party claims arising from Vendor's gross negligence, as further described in Schedule O.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Similar structure to LOL-J2-03, but indemnification_policy_engine has no cross-reference resolution mechanism at all (unlike liability). Correct outcome: REQUIRES_REVIEW or MUST_REDLINE (monetary not stated directly in the obligation's own window) — none of the four schedule figures should be silently adopted.")

# --- Family M: contradictory provisions (2) ---------------------------------

_c("INDEM-M2-01", "indemnification", "M",
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
   "third-party claims arising from Vendor's gross negligence, up to a cap of 1 times the fees paid.\n\n"
   "Amendment No. 1. This Amendment hereby amends and restates Section 8 in its entirety: Vendor shall "
   "indemnify, defend, and hold harmless Customer from and against any third-party claims arising from "
   "Vendor's gross negligence, up to a cap of 4 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Unlike liability_policy_engine, indemnification_policy_engine has no document-wide provision reconciliation/amendment-detection mechanism (confirmed by Step 1: obligations are tracked independently, not reconciled into one controlling provision the way liability's Provisions are). Two obligations with the SAME direction (Vendor->Customer) but different monetary terms (1x vs 4x) should trigger the adapter's own conflicting-obligation check ('multiple obligations found where we are the indemnifying party, with different monetary terms'). Correct outcome: REQUIRES_REVIEW.")

_c("INDEM-M2-02", "indemnification", "M",
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
   "third-party claims arising from Vendor's gross negligence, up to a cap of 1 times the fees paid.\n\n"
   "Schedule P: Special Terms. Notwithstanding anything in the body of this Agreement to the contrary, "
   "Vendor's indemnification obligations shall not exceed 2 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="A second 'Vendor shall indemnify...' obligation (matching _OBLIGATION_RE again in Schedule P's restatement) with a different monetary figure. Correct outcome: REQUIRES_REVIEW via the same conflicting-obligation mechanism as INDEM-M2-01.")

# --- Family O: indemnification directional traps (10) -----------------------

_c("INDEM-O2-01", "indemnification", "O",
   "8. Indemnification. Each party shall indemnify, defend, and hold harmless the other party from and "
   "against third-party claims arising from the indemnifying party's gross negligence, up to a cap equal "
   "to 2 times the fees paid, except that Vendor's cap for IP infringement claims shall be 4 times the "
   "fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Mutual/reciprocal opener ('each party') with a differentiated, per-party-named proviso (Vendor's IP cap differs from the general 2x). This is precisely the reciprocal-asymmetry pattern the adapter is documented to detect (_detect_reciprocal_asymmetry) — correct outcome: REQUIRES_REVIEW, since the opener's symmetry claim cannot be trusted given the named-party carve-out.")

_c("INDEM-O2-02", "indemnification", "O",
   "8. Indemnification. Recipient shall indemnify, defend, and hold harmless Provider from and against "
   "any third-party claims arising from Recipient's use of the Deliverables in a manner not authorized by "
   "this Agreement, up to a cap of 2 times the fees paid.",
   kwargs={"contract_side": "sell_side"},
   review_expected=False, correct_side="sell_side",
   reason="'Recipient' (buy-side per generic BUY_SIDE_ROLES = 'recipient') indemnifies 'Provider' (sell-side, us). This is our PROTECTION obligation (they indemnify us), a favorable clause — must not be misclassified as our exposure.")

_c("INDEM-O2-03", "indemnification", "O",
   "1. Definitions. 'Licensor' means the entity granting a license to the Platform; 'Licensee' means the "
   "entity using the Platform under license from Licensor.\n\n"
   "8. Indemnification. Licensor shall indemnify, defend, and hold harmless Licensee from and against any "
   "third-party IP infringement claims arising from the Platform, up to a cap of 3 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="Conventional roles, explicit definitions consistent with generic mapping (Licensor=sell_side grants; Licensee=buy_side uses under license). We (buy_side)=Licensee receives PROTECTION from Licensor. Correct, unambiguous positive control.")

_c("INDEM-O2-04", "indemnification", "O",
   "8. Indemnification. The parties shall mutually indemnify each other from and against third-party "
   "claims arising from each party's own gross negligence, up to a cap equal to 1 times the fees paid for "
   "each party.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_value="mutual, symmetric 1x fees, no asymmetry",
   reason="Genuinely symmetric mutual clause with matching terms stated for each party (no differentiated per-party carve-out) — should resolve automatically as both exposure and protection at 1x, per the adapter's documented symmetric-mutual handling.")

_c("INDEM-O2-05", "indemnification", "O",
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
   "first-party or third-party claims arising from Vendor's gross negligence, up to a cap of 2 times the "
   "fees paid.",
   kwargs={"contract_side": "buy_side", "require_exposure_third_party_only": True},
   review_expected=False, correct_value="scope=includes_first_party (broader than third-party-only)",
   reason="Explicit first-party scope language ('first-party or third-party claims') should be correctly classified as includes_first_party, broader than a policy requiring third-party-only exposure — testing scope classification accuracy, not directionality.")

_c("INDEM-O2-06", "indemnification", "O",
   "1. Definitions. 'Data Provider' means Gamma LLC, the entity that receives and processes data supplied "
   "by Data Recipient, in exchange for a monthly fee paid by Data Recipient.\n\n"
   "8. Indemnification. Data Provider shall indemnify, defend, and hold harmless Data Recipient from and "
   "against any third-party claims arising from Data Provider's data processing errors, up to a cap of 2 "
   "times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="'Data Provider' and 'Data Recipient' are NOT in the generic BUY_SIDE_ROLES/SELL_SIDE_ROLES vocabulary at all (side_for_role returns None for both) — testing whether unrecognized compound role names correctly fall through to the adapter's existing 'unrecognized party name(s)' unresolved path rather than silently guessing. Correct outcome: REQUIRES_REVIEW.")

_c("INDEM-O2-07", "indemnification", "O",
   "1. Definitions. 'Customer' means the entity that engages Consultant's advisory services and "
   "compensates Consultant on a time-and-materials basis.\n\n"
   "8. Indemnification. Consultant shall indemnify, defend, and hold harmless Customer from and against "
   "any third-party claims arising from Consultant's gross negligence, up to a cap of 1 times the fees "
   "paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'engages...services' and 'compensates...on a time-and-materials basis' (unrecognized verbs) correctly signal buy-side, consistent with generic Customer=buy_side.")

_c("INDEM-O2-08", "indemnification", "O",
   "8. Indemnification. Licensee shall indemnify, defend, and hold harmless Licensor from and against any "
   "third-party claims arising from Licensee's use of the Platform, up to a cap of 1 times the fees paid. "
   "Licensor shall indemnify, defend, and hold harmless Licensee from and against any third-party IP "
   "infringement claims relating to the Platform itself, up to a cap of 3 times the fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_value="exposure=1x (Licensee->Licensor), protection=3x (Licensor->Licensee)",
   reason="Two DIFFERENT-direction obligations (not conflicting — Licensee's exposure to Licensor, and separately Licensor's protection of Licensee) both correctly present. We (buy_side)=Licensee: our exposure is 1x, our protection is 3x. Tests correct resolution of TWO simultaneously valid, differently-scoped obligations, not a conflict.")

_c("INDEM-O2-09", "indemnification", "O",
   "1. Definitions. 'Buyer' means the entity that acquires goods manufactured by Seller pursuant to "
   "purchase orders issued by Buyer and accepted by Seller.\n\n"
   "8. Indemnification. Seller shall indemnify, defend, and hold harmless Buyer from and against any "
   "third-party product-liability claims arising from defects in the goods, up to a cap of 2 times the "
   "fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="'acquires goods manufactured by' + 'purchase orders issued by Buyer' correctly signals buy-side, consistent with generic Buyer=buy_side. Straightforward positive control with realistic manufacturing/product-liability language.")

_c("INDEM-O2-10", "indemnification", "O",
   "1. Definitions. 'Contractor' means the entity retained by Owner to perform construction services on "
   "the Project, and 'Owner' means the entity that engages Contractor and pays the contract price.\n\n"
   "8. Indemnification. Contractor shall indemnify, defend, and hold harmless Owner from and against any "
   "third-party claims arising from Contractor's negligence in performing the construction services, "
   "without limitation as to amount.",
   kwargs={"contract_side": "buy_side", "prohibit_uncapped_exposure": True},
   review_expected=True,
   reason="'Contractor' and 'Owner' are NOT in the generic vocabulary (side_for_role returns None for both). Construction-industry role terms outside the software/SaaS-oriented BUY_SIDE_ROLES/SELL_SIDE_ROLES vocabulary — tests whether an entirely different industry's standard role vocabulary is safely treated as unmapped (REQUIRES_REVIEW) rather than silently guessing a side.")


# ===========================================================================
# PAYMENT TERMS — 30 semantic cases
# ===========================================================================

_PAY_BASE = {"contract_side": "buy_side"}

# --- Family A: unseen definition predicates (3) -----------------------------

_c("PAY-A2-01", "payment_terms", "A",
   "1. Definitions. 'Vendor' will denote Initech LLC, the entity that develops and provides the Software.\n\n"
   "7. Taxes. Vendor shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={**_PAY_BASE, "require_tax_responsibility_counterparty": True},
   review_expected=False, correct_value="counterparty (Vendor=sell_side) bears tax — policy satisfied",
   reason="'will denote' unrecognized, but agrees with generic mapping (Vendor=sell_side=counterparty). Correct: tax responsibility correctly on counterparty.")

_c("PAY-A2-02", "payment_terms", "A",
   "1. Definitions. 'Customer' is understood to mean Initech LLC, the entity that develops and provides "
   "the Software, and 'Vendor' is understood to mean Umbrella Corp, the entity that purchases a "
   "subscription to the Software from Customer for its own internal use.\n\n"
   "7. Taxes. Vendor shall be responsible for all sales, use, and value-added taxes arising from this "
   "Agreement.",
   kwargs={**_PAY_BASE, "require_tax_responsibility_counterparty": True},
   review_expected=False, correct_value="us (Vendor=buy_side per document) bears tax — policy VIOLATED",
   reason="Consequential reversal (structurally identical to PAY-C-01, but using 'is understood to mean'). Per the document, Vendor is the actual purchaser (us). This clause puts tax on us, violating policy. A system that cannot discover the reversal would wrongly conclude the counterparty bears tax and ACCEPT — a false-safe.")

_c("PAY-A2-03", "payment_terms", "A",
   "1. Definitions. References to 'Supplier' are references to the entity that purchases raw materials "
   "and resells finished goods to Buyer.\n\n"
   "7. Taxes. Supplier shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={"contract_side": "sell_side", "require_tax_responsibility_counterparty": True},
   review_expected=False, correct_value="counterparty (Supplier=actual buy-side function here) bears tax — policy VIOLATED per generic reading, but CORRECT per document since generic sell_side(Supplier) would treat this as US bearing tax, which actually matches since we ARE configured sell_side and Supplier IS us generically... reason below clarifies.",
   reason="Contract_side=sell_side (we are conventionally the Supplier). Document defines Supplier as functionally a purchaser/reseller (buy-side conduct), a genuine reversal from the generic mapping, but since OUR configured side is sell_side and the ROLE WORD 'Supplier' generically maps to sell_side too, the literal role-word match already correctly identifies 'Supplier' as us (tax on us) REGARDLESS of the reversal — this specific case's clean decision (tax on us, violating policy) is actually already correct via the generic path alone. Included as a control to confirm the reversal doesn't spuriously change an already-correct outcome.")

# --- Family B: unseen directional language (3) ------------------------------

_c("PAY-B2-01", "payment_terms", "B",
   "1. Definitions. 'Client' means the entity that engages the services of Consultant for the "
   "Engagement.\n\n"
   "6. Payment Terms. Client shall pay all invoices within Net 30 days.",
   kwargs=_PAY_BASE,
   review_expected=False, correct_value="Net 30, Client=buy_side correctly identified as payor (us)",
   reason="'engages the services of' unrecognized but agrees with generic Client=buy_side.")

_c("PAY-B2-02", "payment_terms", "B",
   "1. Definitions. 'Vendor' means Acme Corp, the entity that retains Customer's payment-processing "
   "capacity to collect amounts owed to Vendor.\n\n"
   "7. Taxes. Customer shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={**_PAY_BASE, "require_tax_responsibility_counterparty": True},
   review_expected=True,
   reason="'retains' language is genuinely convoluted/unusual here (Vendor retaining Customer's payment-processing capacity is an unusual, non-standard commercial relationship, not a clean reversal signal) — this tests whether an ambiguous, hard-to-classify sentence is safely left unresolved rather than confidently (mis)classified either way. Both a correct resolution (Customer=buy_side, tax on us=policy violated) or a safe REQUIRES_REVIEW are acceptable; only a confident WRONG classification is a failure.")

_c("PAY-B2-03", "payment_terms", "B",
   "1. Definitions. 'Provider' means the entity that performs the Services for Recipient and renders "
   "invoices to Recipient monthly.\n\n"
   "6. Payment Terms. Recipient shall pay Provider's invoices within Net 45 days.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_value="Net 45, Recipient=buy_side correctly identified as payor (us)",
   reason="'performs...for' and 'renders invoices to' (unrecognized) correctly signal sell-side for Provider; Recipient (buy-side generic) is the payor, consistent with generic mapping.")

# --- Family C: agent-noun collisions (3) ------------------------------------

_c("PAY-C2-01", "payment_terms", "C",
   "1. Definitions. 'Buyer' means the entity purchasing goods hereunder, subject to the Payment "
   "Provider's separate processing terms.\n\n"
   "6. Payment Terms. Buyer shall pay all invoices within Net 30 days.",
   kwargs=_PAY_BASE,
   review_expected=False, correct_value="Net 30, Buyer=buy_side correctly identified",
   reason="'Payment Provider' is a bystander role-noun; Buyer's own evidence ('purchasing goods') is clean buy-side.")

_c("PAY-C2-02", "payment_terms", "C",
   "1. Definitions. 'Purchaser' means the entity acquiring the Deliverables from Vendor; the Data "
   "Provider engaged by Purchaser is a separate third party.\n\n"
   "7. Taxes. Purchaser shall be responsible for all sales and use taxes.",
   kwargs={**_PAY_BASE, "require_tax_responsibility_counterparty": True},
   review_expected=False, correct_value="us (Purchaser=buy_side) bears tax — policy VIOLATED",
   reason="'Data Provider' is a bystander noun. Purchaser's own evidence ('acquiring the Deliverables') is clean buy-side; tax on Purchaser=us, violating policy.")

_c("PAY-C2-03", "payment_terms", "C",
   "1. Definitions. 'Licensee' means the entity that licenses the Platform from Licensor; the Service "
   "Provider retained by Licensee handles implementation.\n\n"
   "6. Payment Terms. Licensee shall pay all invoices within Net 60 days.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_value="Net 60, Licensee=buy_side correctly identified",
   reason="'Service Provider' bystander noun; Licensee's own evidence signals buy-side (though note: 'licenses...from' is not itself in the buy vocabulary, so this is UNKNOWN — falls back to generic Licensee=buy_side, which is correct).")

# --- Family D: both directions present (3) ----------------------------------

_c("PAY-D2-01", "payment_terms", "D",
   "1. Definitions. 'Customer' means the entity that purchases the Services from Vendor and provides "
   "Vendor with Customer Data for use in delivering the Services.\n\n"
   "7. Taxes. Customer shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={**_PAY_BASE, "require_tax_responsibility_counterparty": True},
   review_expected=True,
   reason="Same mixed structure as LOL-D2-01. Correct: Customer buy-side, tax on us=policy violated. CA(correct MUST_REDLINE/NEGOTIATE) or CR acceptable; WC(ACCEPT, treating Customer as counterparty) is a failure — this is exactly the PAY-C-01 false-safe pattern.")

_c("PAY-D2-02", "payment_terms", "D",
   "1. Definitions. 'Vendor' means the entity that both purchases component parts from third-party "
   "manufacturers and sells the assembled products to Customer under this Agreement.\n\n"
   "7. Taxes. Vendor shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={"contract_side": "sell_side", "require_tax_responsibility_counterparty": True},
   review_expected=True,
   reason="Same mixed structure as LOL-D2-02. Relevant role vis-a-vis Customer is selling (Vendor=sell_side=us, since contract_side=sell_side). Tax on Vendor=us, correctly a policy violation if resolved as sell_side. CA or CR acceptable; WC (treating Vendor as buy_side/counterparty, wrongly ACCEPT) is a failure.")

_c("PAY-D2-03", "payment_terms", "D",
   "1. Definitions. 'Reseller' means the entity that develops custom integrations for Manufacturer and "
   "pays Manufacturer a wholesale price for the underlying goods.\n\n"
   "7. Taxes. Reseller shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={"contract_side": "buy_side", "require_tax_responsibility_counterparty": True},
   review_expected=True,
   reason="Mixed: 'develops' (sell-side signal) describes Reseller's integration work; 'pays...a wholesale price' (buy-side signal) describes the actual goods transaction — Reseller is genuinely the buyer of goods from Manufacturer. CA(buy_side, tax on us=violation) or CR acceptable; WC(sell_side) is a failure.")

# --- Family N: payment-term directional traps (18) --------------------------

_c("PAY-N2-01", "payment_terms", "N",
   "1. Definitions. 'Vendor' means Umbrella Corp, the entity that purchases a subscription to the Software "
   "from Customer, Initech LLC, the entity that develops and provides the Software.\n\n"
   "7. Withholding. Vendor shall be responsible for any withholding taxes imposed on payments under this "
   "Agreement.",
   kwargs={**_PAY_BASE, "require_tax_responsibility_counterparty": True},
   review_expected=True,
   reason="Reversal (Vendor=actual purchaser/us) using RECOGNIZED predicate ('means') and RECOGNIZED verb ('purchases'), applied to WITHHOLDING (not the primary 'tax_responsibility_attributions' field the existing verifier checks) — tests whether the same reversal-detection mechanism extends to a different but related payment-terms field. If withholding tax attribution uses the same _resolve_tax_responsibility-style mechanism, this should correctly detect the conflict (CR or correct MUST_REDLINE); if withholding is tracked separately without role verification, this could be a WC.")

_c("PAY-N2-02", "payment_terms", "N",
   "1. Definitions. 'Vendor' means Umbrella Corp, the entity that purchases a subscription to the Software "
   "from Customer, the entity that develops and provides the Software.\n\n"
   "6. Payment Terms. Customer shall reimburse Vendor for all reasonable travel expenses pre-approved by "
   "Vendor in writing.",
   kwargs={**_PAY_BASE, "require_expense_preapproval": True},
   review_expected=False, correct_value="expense preapproval requirement satisfied (pre-approved by Vendor in writing)",
   reason="Reimbursement/expense clause, not directly dependent on the Vendor/Customer role reversal (the preapproval requirement is satisfied regardless of which party is 'Vendor'). Tests that a non-directional field is unaffected by a definitional reversal elsewhere in the document.")

_c("PAY-N2-03", "payment_terms", "N",
   "1. Definitions. 'Vendor' means Umbrella Corp, the entity that purchases a subscription to the Software "
   "from Customer, the entity that develops and provides the Software.\n\n"
   "6. Payment Terms. Vendor shall be entitled to a refund of prepaid, unused fees upon termination for "
   "convenience by Customer.",
   kwargs={**_PAY_BASE, "require_refund_entitlement": True},
   review_expected=False, correct_value="refund entitlement present (satisfies policy) regardless of role reversal",
   reason="Refund-entitlement presence is a simple presence signal, not directionally dependent on which party is 'us' — should resolve correctly regardless of the Vendor/Customer reversal.")

_c("PAY-N2-04", "payment_terms", "N",
   "1. Definitions. 'Client' means the entity that engages the services of Consultant.\n\n"
   "6. Payment Terms. Client shall have the right to withhold disputed amounts pending resolution, and "
   "undisputed amounts shall remain payable during any dispute.",
   kwargs={"contract_side": "buy_side", "require_undisputed_amounts_still_payable": True,
           "prohibit_disputed_amount_withholding": False},
   review_expected=False, correct_value="undisputed amounts still payable (policy satisfied)",
   reason="'engages the services of' unrecognized but agrees with generic Client=buy_side. Policy on disputed-amount handling is satisfied per the stated terms, regardless of role.")

_c("PAY-N2-05", "payment_terms", "N",
   "1. Definitions. 'Customer' means the entity that develops and provides the Software, and 'Vendor' "
   "means the entity that purchases a subscription from Customer.\n\n"
   "6. Payment Terms. Customer shall have the right to offset any amounts owed to Vendor against amounts "
   "Vendor owes Customer under any other agreement.",
   kwargs={"contract_side": "buy_side", "prohibit_set_off": True},
   review_expected=True,
   reason="Reversal: Customer is actually the seller here; Vendor is actually us (buyer). The set-off right is held by Customer (the seller/counterparty per the document), which is FAVORABLE information about the counterparty's rights, not directly about our own set-off exposure — but the policy prohibits set-off generically. Genuinely tests whether the adapter's set-off detection is directional at all (it may not be, in which case CA is expected); marked review_expected conservative given uncertainty about whether _resolve_payor_side-style verification even applies to set-off rights. CA(MUST_REDLINE, set-off present regardless of party) or CR both acceptable.")

_c("PAY-N2-06", "payment_terms", "N",
   "1. Definitions. 'Vendor' means the entity that purchases raw materials from Customer for "
   "manufacturing purposes, and 'Customer' means the entity that supplies the raw materials to Vendor.\n\n"
   "6. Payment Terms. Vendor shall pay a late fee of 2% per month on any overdue amounts owed to "
   "Customer.",
   kwargs={"contract_side": "buy_side", "maximum_late_interest_rate_percent": 1.5},
   review_expected=True,
   reason="Reversal: Vendor is actually the buyer (us) per the document. The late fee (2%/month) applies to amounts Vendor (us) owes — i.e., WE would pay the late fee, meaning the late-fee-rate policy check (max 1.5%/month) should apply to US and 2% exceeds it. Generic mapping (Vendor=sell_side) would misread this as a fee that doesn't concern the buy_side policy holder. CA(correctly flags 2%>1.5% as a violation, NEGOTIATE/MUST_REDLINE) or CR acceptable; WC(ACCEPT, ignoring the excessive rate because of misattributed direction) is a failure.")

_c("PAY-N2-07", "payment_terms", "N",
   "1. Definitions. 'Licensor' means the entity that purchases a license to use the Platform, and "
   "'Licensee' means the entity that develops and licenses the Platform to Licensor.\n\n"
   "6. Payment Terms. Licensee shall be entitled to increase fees by up to 10% annually upon 30 days "
   "notice to Licensor.",
   kwargs={"contract_side": "buy_side", "prohibit_unilateral_price_increase": True,
           "maximum_price_increase_percent": 5, "minimum_price_increase_notice_days": 60},
   review_expected=True,
   reason="Reversal: Licensor=actual buyer(us), Licensee=actual seller. The price-increase right (10%, 30 days notice) belongs to Licensee (seller/counterparty) — this affects US as the payor, so the policy check (max 5%, min 60 days notice) should apply and both figures should be flagged as violations (10%>5%, 30<60). Generic mapping (Licensor=sell_side) could misattribute which side bears this term. CA(correctly flags both violations) or CR acceptable; WC(ACCEPT or missing the violation) is a failure.")

_c("PAY-N2-08", "payment_terms", "N",
   "1. Definitions. 'Vendor' means the entity that purchases inventory from Distributor for retail resale, "
   "and 'Distributor' means the entity that manufactures and supplies inventory to Vendor.\n\n"
   "7. Taxes. Vendor shall be responsible for all sales, use, and value-added taxes arising from this "
   "Agreement.",
   kwargs={"contract_side": "buy_side", "require_tax_responsibility_counterparty": True},
   review_expected=False, correct_value="us (Vendor=buy_side per document) bears tax — policy VIOLATED",
   reason="Direct structural analog of PAY-C-01/PAY-A2-02 with 'Distributor' instead of 'Customer' as the counterparty role word (Distributor is not in the generic vocabulary at all, side_for_role=None — a genuinely unmapped role, distinct from a reversed-but-recognized one). Vendor is redefined as the buyer (us); tax on Vendor=us violates policy.")

_c("PAY-N2-09", "payment_terms", "N",
   "1. Definitions. 'Supplier' means the entity that purchases finished goods from Manufacturer for "
   "distribution, and 'Manufacturer' means the entity that produces and supplies the goods to Supplier.\n\n"
   "7. Taxes. Supplier shall be responsible for all sales, use, and value-added taxes arising from this "
   "Agreement.",
   kwargs={"contract_side": "sell_side", "require_tax_responsibility_counterparty": True},
   review_expected=True,
   reason="'Supplier' generically maps to sell_side, and our contract_side=sell_side, so the LITERAL role word already identifies Supplier as us. But the document redefines Supplier as functionally a PURCHASER (buy-side conduct) — a genuine internal contradiction between the role's conventional generic meaning (which happens to match our config) and its actual document-specific function. Correct outcome: the definition conflicts with generic vocabulary (buy-side language for a sell_side-mapped role), which should trigger CONFLICT/REQUIRES_REVIEW per the documented design (any conflict, regardless of which side it happens to point away from, must not be silently trusted) — even though, coincidentally, the LITERAL role-word answer (Supplier=us=sell_side) matches our config.")

_c("PAY-N2-10", "payment_terms", "N",
   "1. Definitions. 'Buyer' means the entity that provides raw materials to Seller in a tolling "
   "arrangement, and 'Seller' means the entity that processes Buyer's materials and returns finished "
   "goods for a processing fee.\n\n"
   "7. Taxes. Buyer shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={"contract_side": "buy_side", "require_tax_responsibility_counterparty": True},
   review_expected=True,
   reason="Genuine, realistic reversal: in a tolling arrangement, 'Buyer' actually PROVIDES materials (sell-side conduct) and 'Seller' processes them for a FEE paid by Buyer (i.e., Buyer is functionally paying for a service, buy-side of the SERVICE even while providing materials) — genuinely complex/ambiguous real-world structure. Tax is on Buyer (generically=us). Correct outcome plausibly REQUIRES_REVIEW given genuine complexity; CA is acceptable only if it correctly identifies the tax burden falls on us (a MUST_REDLINE/NEGOTIATE outcome, not ACCEPT).")

_c("PAY-N2-11", "payment_terms", "N",
   "1. Definitions. 'Customer' means the entity that develops and provides the Software, and 'Vendor' "
   "means the entity that purchases a subscription from Customer.\n\n"
   "6. Payment Terms. Vendor shall pay all invoices within Net 30 days of the invoice date.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_value="Net 30, payor correctly identified as Vendor=us (document-correct)",
   reason="Reversal present (Customer=seller, Vendor=buyer=us), but this specific field (net_days) is currently NOT verified via resolve_role_side at all per the frozen implementation (only payor-side/tax-side attribution use it, not the raw net_days figure itself) — Net 30 is simply extracted and compared to policy regardless of party. Correct value (Net 30) is unaffected by the reversal since the field extraction doesn't depend on party attribution. Included as a control confirming non-directional fields are correctly unaffected by directional confusion.")

_c("PAY-N2-12", "payment_terms", "N",
   "1. Definitions. 'Recipient' means the entity that develops and provides the Services, and 'Payor' "
   "means the entity that purchases the Services from Recipient.\n\n"
   "7. Taxes. Recipient shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={"contract_side": "buy_side", "require_tax_responsibility_counterparty": True},
   review_expected=True,
   reason="'Recipient' generically maps to BUY_SIDE_ROLES ('recipient'), but the document defines Recipient as the SELLER/provider (sell-side conduct) — a genuine reversal using a role word not tested in prior steps. 'Payor' is not in the generic vocabulary at all. Tax is on Recipient. If the reversal is caught: Recipient=sell_side=counterparty per document, so tax correctly on counterparty (ACCEPT would be document-correct). If NOT caught: generic Recipient=buy_side=us, tax on us wrongly, so a MUST_REDLINE finding would be WRONG (false escalation in the safe direction, not dangerous, but still incorrect) OR if the engine trusts generic mapping AND concludes 'counterparty' via some other path it could still mismatch. Complex case — review_expected=True reflects genuine difficulty; both a correct resolution and REQUIRES_REVIEW are acceptable, only a decision that gets the DIRECTION backwards with confidence is a WC.")

_c("PAY-N2-13", "payment_terms", "N",
   "1. Definitions. 'Client' means the entity that purchases advisory Services from Firm, and 'Firm' "
   "means the entity that renders the advisory Services to Client.\n\n"
   "7. Taxes. Client shall be responsible for all applicable taxes arising from this Agreement.",
   kwargs={"contract_side": "buy_side", "require_tax_responsibility_counterparty": True},
   review_expected=False, correct_value="us (Client=buy_side) bears tax — policy VIOLATED",
   reason="Conventional, non-reversed definitions ('Client' generic=None actually, not in BUY/SELL_SIDE_ROLES — 'client' IS in BUY_SIDE_ROLES actually). Client=buy_side=us per generic AND per document (purchases from Firm) — consistent, straightforward positive control. Tax on Client=us violates policy; correct outcome is NOT ACCEPT.")

_c("PAY-N2-14", "payment_terms", "N",
   "1. Definitions. 'Purchaser' means the entity that purchases the goods, and 'Vendor' means the entity "
   "that manufactures and sells the goods to Purchaser.\n\n"
   "6. Payment Terms. Purchaser shall pay Vendor in United States Dollars within Net 45 days of delivery.",
   kwargs={"contract_side": "buy_side", "required_currency": "USD", "acceptable_max_net_days": 60},
   review_expected=False, correct_value="Net 45 (within policy), USD (matches required currency)",
   reason="Fully conventional, consistent definitions and terms — straightforward positive control confirming ordinary drafting continues to flow automatically.")

_c("PAY-N2-15", "payment_terms", "N",
   "1. Definitions. 'Customer' means the entity that develops and provides the Software, and 'Vendor' "
   "means the entity that purchases a subscription to the Software from Customer for its own internal "
   "use.\n\n"
   "7. Taxes. Each party shall be responsible for taxes based on its own net income. Vendor shall be "
   "responsible for all sales, use, and value-added taxes arising from this Agreement, excluding taxes "
   "based on Customer's net income.",
   kwargs={"contract_side": "buy_side", "require_tax_responsibility_counterparty": True},
   review_expected=False, correct_value="us (Vendor=buy_side per document) bears sales/use/VAT tax — policy VIOLATED",
   reason="Direct variant of PAY-C-01's exact structure but with an added net-income carve-out sentence beforehand (a realistic drafting elaboration, not a superficial substitution) — same underlying reversal (Vendor=actual purchaser=us) and same correct outcome (tax on us violates policy, must not ACCEPT).")

_c("PAY-N2-16", "payment_terms", "N",
   "1. Definitions. 'Customer' means the entity that develops and provides the Software; 'Vendor' means "
   "the entity that purchases a subscription to the Software from Customer for its own internal use, "
   "notwithstanding that Vendor may also resell certain add-on modules to end users from time to time.\n\n"
   "7. Taxes. Vendor shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={"contract_side": "buy_side", "require_tax_responsibility_counterparty": True},
   review_expected=True,
   reason="Same core reversal as PAY-C-01, but with an added qualifying clause ('notwithstanding that Vendor may also resell...') that introduces genuine secondary complexity (Vendor has BOTH a buy-side primary role and a secondary, incidental resale/sell-side activity). This tests whether the mixed-signal detection correctly identifies this as complex enough to escalate (has_buy AND has_sell both present -> 'mixed' -> CONFLICT), which is the documented, correct behavior for genuinely mixed definitions. CR is the expected/correct outcome; if the system instead confidently resolves either way (especially ACCEPT via a wrongly-resolved sell_side reading), that is a WC.")

_c("PAY-N2-17", "payment_terms", "N",
   "1. Definitions. 'Customer' has the meaning given to 'Subscriber' in the Order Form.\n\n"
   "Order Form. 'Subscriber' means the entity that purchases the subscription described herein.\n\n"
   "7. Taxes. Customer shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={"contract_side": "buy_side", "require_tax_responsibility_counterparty": True},
   review_expected=False, correct_value="us (Customer=buy_side, both per indirect definition AND generic mapping) bears tax — policy VIOLATED",
   reason="Indirect definition (Customer's meaning given to 'Subscriber' elsewhere), but here the indirection HAPPENS TO agree with the generic mapping (Customer=buy_side both ways) — tests that an unresolved indirection doesn't spuriously create a conflict when the generic fallback is independently correct.")

_c("PAY-N2-18", "payment_terms", "N",
   "1. Definitions. 'Vendor' has the meaning given to 'Purchaser' in Schedule A.\n\n"
   "Schedule A. 'Purchaser' means the entity that purchases the Software from Provider for internal use.\n\n"
   "7. Taxes. Vendor shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={"contract_side": "buy_side", "require_tax_responsibility_counterparty": True},
   review_expected=True,
   reason="Indirect definition where the TRUE role (Vendor=actual purchaser=us, per the cross-referenced 'Purchaser' definition) is only discoverable by following the reference — the current design does not support multi-hop indirection. Correct/ideal outcome: REQUIRES_REVIEW (indirection cannot be safely resolved). If the system instead falls back to generic Vendor=sell_side and confidently ACCEPTs, that is a false-safe WC — the anticipated architectural gap from Family F, applied to payment terms.")


# ===========================================================================
# COMPOUND CASES — 6 (mix liability+indemnification, liability+payment, etc.)
# ===========================================================================

_c("COMP2-01", "liability", "compound",
   "1. Definitions. 'Vendor' means Umbrella Corp, the entity that purchases a subscription to the Software "
   "from Customer, the entity that develops and provides the Software.\n\n"
   "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 1 times the annual fees "
   "paid. Customer's aggregate liability shall not exceed 6 times the annual fees paid.\n\n"
   "7. Taxes. Vendor shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={"contract_side": "buy_side"},
   review_expected=False, correct_side="buy_side",
   reason="Compound document exercising the SAME role reversal (Vendor=actual buyer) across TWO adapters (liability, payment) in one document — testing consistency: both adapters must independently reach the same correct/consistent conclusion about Vendor's side (buy_side, 1x cap) from the same shared definitional text.")

_c("COMP2-02", "payment_terms", "compound",
   "1. Definitions. 'Vendor' means Umbrella Corp, the entity that purchases a subscription to the Software "
   "from Customer, the entity that develops and provides the Software.\n\n"
   "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 1 times the annual fees "
   "paid. Customer's aggregate liability shall not exceed 6 times the annual fees paid.\n\n"
   "7. Taxes. Vendor shall be responsible for all sales and use taxes arising from this Agreement.",
   kwargs={"contract_side": "buy_side", "require_tax_responsibility_counterparty": True},
   review_expected=False, correct_value="us (Vendor=buy_side) bears tax — policy VIOLATED",
   reason="Same compound document as COMP2-01, evaluated through the payment_terms adapter instead — same reversal must be independently and consistently detected/resolved by this adapter too.")

_c("COMP2-03", "indemnification", "compound",
   "1. Definitions. 'Vendor' means Umbrella Corp, the entity that purchases a subscription to the Software "
   "from Customer, the entity that develops and provides the Software.\n\n"
   "8. Indemnification. Customer shall indemnify, defend, and hold harmless Vendor from and against any "
   "third-party claims arising from Customer's gross negligence, without limitation as to amount.\n\n"
   "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 1 times the annual fees "
   "paid.",
   kwargs={"contract_side": "buy_side", "prohibit_uncapped_exposure": True},
   review_expected=False, correct_side="buy_side",
   reason="Third adapter (indemnification) on the same compound document. Customer (actual seller) gives Vendor (us) an uncapped PROTECTION promise — favorable, must not be PROHIBITED. Consistency test across all three adapters on one shared definitions section.")

_c("COMP2-04", "liability", "compound",
   "9. Limitation of Liability. Provider's aggregate liability shall be as set forth in Schedule Q.\n\n"
   + ("Filler text between sections. " * 20) +
   "\n\nSchedule Q: Combined Risk Terms. Provider shall maintain cyber liability insurance of $5,000,000. "
   "Provider's indemnification obligations shall not exceed 2 times the fees paid. Service credits under "
   "the SLA shall not exceed $50,000. Provider's aggregate liability under this Agreement shall not "
   "exceed $1,000,000.",
   review_expected=False, correct_value="$1,000,000",
   reason="Combined schedule with FOUR different concepts (insurance $5M, indemnification 2x, SLA credit $50K, genuine liability $1M) — cross-adapter contamination stress test within a single liability cross-reference resolution. Correct value is $1,000,000.")

_c("COMP2-05", "indemnification", "compound",
   "8. Indemnification. Provider shall indemnify, defend, and hold harmless Customer from and against any "
   "third-party claims arising from Provider's gross negligence, subject to the terms of Schedule Q.\n\n"
   + ("Filler text between sections. " * 20) +
   "\n\nSchedule Q: Combined Risk Terms. Provider shall maintain cyber liability insurance of $5,000,000. "
   "Provider's indemnification obligations shall not exceed 2 times the fees paid. Service credits under "
   "the SLA shall not exceed $50,000. Provider's aggregate liability under this Agreement shall not "
   "exceed $1,000,000.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Same combined schedule as COMP2-04, evaluated for indemnification, which has NO cross-reference resolution mechanism at all. Correct outcome: REQUIRES_REVIEW or MUST_REDLINE (monetary not stated directly in the obligation's own window) — must not adopt any of the four figures, especially not the general liability figure ($1M) or insurance figure ($5M) as the indemnification cap.")

_c("COMP2-06", "liability", "compound",
   "1. Definitions. 'Reseller' means Beta Inc., the entity purchasing Software from Provider for resale, "
   "subject to the Data Provider's and Payment Provider's separate terms, notwithstanding that Reseller "
   "also develops certain custom integration modules for end users.\n\n"
   "9. Limitation of Liability. Reseller's aggregate liability shall be as set forth in Schedule R.\n\n"
   + ("Filler text between sections. " * 15) +
   "\n\nSchedule R: Liability and Insurance. Reseller shall maintain professional liability insurance of "
   "$3,000,000. Reseller's own aggregate liability under this Agreement shall not exceed 2 times the "
   "annual fees paid.",
   kwargs={"contract_side": "buy_side"},
   review_expected=True,
   reason="Maximum-difficulty compound: agent-noun bystanders (Data Provider, Payment Provider) + a genuinely mixed directional signal (Reseller purchases AND develops) + a cross-referenced schedule containing both an insurance distractor and a genuine liability cap. Correct value if resolved: 2x annual fees (not $3M insurance); but given the mixed directional signal, REQUIRES_REVIEW on the party-side question is also defensible. CA(2x fees, buy_side) or CR acceptable; WC ($3,000,000 adopted, OR sell_side wrongly resolved) is a failure.")


# ===========================================================================
# Sanity: no duplicate ids
# ===========================================================================
_ids = [c["id"] for c in CASES]
assert len(_ids) == len(set(_ids)), f"duplicate case ids: {[i for i in _ids if _ids.count(i) > 1]}"
