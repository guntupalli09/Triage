"""Step 4A.7.3 — fresh development adversarial battery.

Built AFTER known unsafe WC reached zero (Step 4A.7.2), per the explicit
sequencing rule. Not copied, lightly paraphrased, or mechanically mutated
from any prior corpus (4A.2, 4A.4, 4A.5, 4A.6, 4A.7, 4A.7.1, 4A.7.2's own
mechanism benchmarks). New domains, new entity names, new constructions.

Schema: dict(id, family, adapter, tier, text, kwargs, label, expected_result,
concept, reason). label in {AUTOMATABLE, SHOULD_REVIEW}. Manual
classification (CA/CR/FE/WC/SM + severity) happens after a single held-out
execution — see run_step4a7_3_fresh_adversarial_battery.py and the final
report.
"""

CASES = []


def _c(id_, family, adapter, tier, text, kwargs, label, expected_result, concept, reason):
    CASES.append(dict(id=id_, family=family, adapter=adapter, tier=tier, text=text,
                       kwargs=kwargs, label=label, expected_result=expected_result,
                       concept=concept, reason=reason))


# ===========================================================================
# 1. LIABILITY (20)
# ===========================================================================
_c("F3-L-01", "liability", "liability", 1,
   "9. Limitation of Liability. Brightwater Aquaponics Systems' aggregate liability shall not "
   "exceed 1 times the annual cultivation fees paid.",
   {}, "AUTOMATABLE", "ACCEPT", "ordinary multiplier, new basis noun",
   "Tests whether the basis-modifier fix generalizes to a fresh domain noun not in any prior corpus.")
_c("F3-L-02", "liability", "liability", 1,
   "9. Limitation of Liability. Coldstream Ice Sculpture Rentals' aggregate liability shall not "
   "exceed 2 times the annual rental commission paid.",
   {}, "AUTOMATABLE", "NEGOTIATE (2x)", "ordinary multiplier at threshold boundary",
   "2x is exactly acceptable_max_multiplier; tests correct NEGOTIATE (not ACCEPT, not ESCALATE).")
_c("F3-L-03", "liability", "liability", 2,
   "9. Limitation of Liability. Marrowbone Custom Taxidermy Studio's aggregate liability shall "
   "not exceed 3 times the annual preservation-service fees paid.",
   {}, "AUTOMATABLE", "NEGOTIATE (3x)", "ordinary multiplier with a two-word modifier before fees",
   "'preservation-service fees' — a hyphenated two-word modifier, distinct shape from any prior "
   "hyphen case (which fused into the basis word itself, not preceding it).")
_c("F3-L-04", "liability", "liability", 2,
   "9. Limitation of Liability. Thistlewood Bespoke Millinery's aggregate liability shall not "
   "exceed the greater of $40,000 or 2 times the annual millinery-commission fees paid.",
   {}, "AUTOMATABLE", "ACCEPT (greater-of structure, both components extractable)",
   "greater-of with a fresh basis phrase",
   "Fresh domain test of the existing greater-of mechanism combined with the modifier-tolerant basis extractor.")
_c("F3-L-05", "liability", "liability", 3,
   "9. Limitation of Liability. Silverfen Wetland Restoration Consultants shall have no liability "
   "whatsoever to Client for claims arising under this Agreement, except that claims arising from "
   "willful misconduct shall remain subject to the Restoration Damages Cap, which the parties "
   "agree, subject to annual CPI adjustment, is $250,000.",
   {}, "AUTOMATABLE", "ESCALATE or ACCEPT depending on config (fixed-dollar, unlimited-elsewhere edge phrasing)",
   "unlimited + defined-term delegation with an interposed CPI-adjustment clause",
   "Fresh variant of the interposed-clause defined-term-delegation fix (Step 4A.7.1), with a "
   "DIFFERENT interposing phrase ('subject to annual CPI adjustment') than the one the fix was built against.")
_c("F3-L-06", "liability", "liability", 2,
   "9. Limitation of Liability. Duskglow Neon Fabrication Corp's aggregate liability shall not "
   "exceed the amount specified in the fabrication-cost schedule referenced in Section 5, it being "
   "acknowledged that no such schedule has yet been finalized.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "self-flagged unresolved delegation, fresh phrasing",
   "'it being acknowledged that no such [X] has yet been finalized' — a fresh variant of the "
   "self-flagged-unresolved family, testing generalization beyond the six phrases the fix covers.")
_c("F3-L-07", "liability", "liability", 3,
   "9. Limitation of Liability. Emberlynn Kiln Works' aggregate liability shall not exceed the "
   "Kiln Damage Cap. 'Kiln Damage Cap' means, for purposes of Section 9, 1 times the annual firing "
   "fees paid, and means, for purposes of Schedule C (Insurance Coordination), 5 times the annual "
   "firing fees paid.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "conflicting defined term, fresh domain and target label",
   "Same shape as the Step 4A.7.1 fix (means...for purposes of Section X...and means...for "
   "purposes of Section Y) but referencing a Schedule instead of a Section as the second scope — "
   "tests whether the fix generalizes beyond 'Section' specifically.")
_c("F3-L-08", "liability", "liability", 2,
   "9. Limitation of Liability. Northcairn Distillery Equipment Corp's aggregate liability to "
   "Client shall not exceed 1 times the annual equipment-lease fees paid.",
   {}, "AUTOMATABLE", "ACCEPT", "ordinary named-role pair, both generic vocabulary",
   "Fresh two-word hyphenless modifier ('equipment-lease' is hyphenated, tests the OTHER hyphen "
   "direction — modifier hyphenated internally, not fused to the basis word).")
_c("F3-L-09", "liability", "liability", 3,
   "9. Limitation of Liability. Vantagepoint Aerial Cinematography's aggregate liability to "
   "Producer shall not exceed 2 times the annual production-support fees paid, PROVIDED THAT the "
   "foregoing multiplier applies only if Producer has maintained continuous production insurance "
   "throughout the Term, a condition not yet verified as of this excerpt.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "conditional multiplier with an unverified precondition",
   "A genuinely new mechanism not covered by any existing fix: the multiplier's APPLICABILITY "
   "(not its value or basis) is conditioned on an unverified fact.")
_c("F3-L-10", "liability", "liability", 1,
   "9. Limitation of Liability. Copperlark Bespoke Jewelry Manufacturing's aggregate liability "
   "shall not exceed 1 times the annual craftsmanship fees paid.",
   {}, "AUTOMATABLE", "ACCEPT", "ordinary multiplier, clean",
   "Plain Tier-1 control, no distractor at all.")
_c("F3-L-11", "liability", "liability", 2,
   "9. Limitation of Liability. Ashfield Meadery & Cidery's aggregate liability shall not exceed "
   "the lesser of $80,000 or 1 times the annual production fees paid, excluding claims arising "
   "from product contamination, which shall be governed by the Contamination Liability Rider "
   "(Exhibit F, not included in this excerpt).",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "lesser-of general cap with a category delegated externally",
   "Tests whether a category-specific delegation to an unincluded exhibit correctly leaves the "
   "GENERAL cap resolvable while the excluded category remains unresolved (category-scoped, not "
   "general-cap chained delegation).")
_c("F3-L-12", "liability", "liability", 2,
   "9. Limitation of Liability. Palisade Rock-Climbing Gym Partners' aggregate liability shall "
   "not exceed 1 times the annual membership-processing fees paid.",
   {}, "AUTOMATABLE", "ACCEPT", "three-word compound modifier before fees",
   "'membership-processing fees' tests a longer compound modifier than any prior basis-fix test case.")
_c("F3-L-13", "liability", "liability", 3,
   "9. Limitation of Liability. Ironvale Blacksmithing Collective's aggregate liability shall not "
   "exceed 1 times the annual forging fees paid, it being unclear whether 'forging fees' includes "
   "raw-material surcharges billed separately under Section 11.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "self-flagged basis-value ambiguity, fresh phrasing",
   "'it being unclear whether [basis] includes [X]' — a fresh construction of the existing "
   "self-flagged-ambiguity family, phrased around the BASIS specifically rather than the whole cap.")
_c("F3-L-14", "liability", "liability", 1,
   "9. Limitation of Liability. Thornfield Beekeeping Cooperative's aggregate liability shall not "
   "exceed 2 times the annual honey-sales commission paid.",
   {}, "AUTOMATABLE", "NEGOTIATE (2x)", "ordinary multiplier at threshold, fresh basis",
   "Another 2x-exactly-at-threshold control, different domain from F3-L-02.")
_c("F3-L-15", "liability", "liability", 2,
   "9. Limitation of Liability. Quillfeather Falconry Exhibitions' aggregate liability shall not "
   "exceed 1 times the annual exhibition fees paid. Separately, Quillfeather Falconry Exhibitions "
   "maintains avian-mortality insurance of $500,000, which is unrelated to this Section.",
   {}, "AUTOMATABLE", "ACCEPT", "clean cap with an explicitly-disclaimed insurance distractor",
   "Insurance distractor that EXPLICITLY disclaims relevance ('which is unrelated to this "
   "Section') — must not be misassociated as the cap value, and the explicit disclaimer must not "
   "itself trigger unnecessary review.")
_c("F3-L-16", "liability", "liability", 3,
   "9. Limitation of Liability. Graywolf Tactical Training Academy's aggregate liability to "
   "Client shall not exceed 1 times the annual training fees paid, or such higher amount as "
   "Client may separately negotiate for extended engagements, no such separate negotiation having "
   "occurred as of the Effective Date.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "open-ended future-negotiation qualifier, fresh phrasing",
   "'no such separate negotiation having occurred' — a fresh variant of the self-flagged-"
   "unresolved family, different grammatical construction (absolute participial clause) than any "
   "case the fix was built against.")
_c("F3-L-17", "liability", "liability", 2,
   "9. Limitation of Liability. Bellhaven Antique Clock Restoration's aggregate liability shall "
   "not exceed 1 times the annual restoration fees paid.",
   {}, "AUTOMATABLE", "ACCEPT", "plain control",
   "Second plain Tier-2 control for baseline comparison.")
_c("F3-L-18", "liability", "liability", 3,
   "9. Limitation of Liability. Wrenfield Custom Saddlery Corp's liability to Rider shall not "
   "exceed 1 times the annual tack-fitting fees paid, calculated per the definition of "
   "'tack-fitting fees' in Appendix 2, which Appendix 2 in turn incorporates the fee schedule "
   "attached to the separately-executed Service Order (not included).",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "chained delegation via Appendix rather than Schedule/Exhibit",
   "Fresh variant of the Step 4A.7.1 chained-delegation fix using 'Appendix' + 'Service Order' "
   "instead of 'Schedule'/'Exhibit' — tests whether the fix's specific document-type wording "
   "generalizes.")
_c("F3-L-19", "liability", "liability", 2,
   "9. Limitation of Liability. Redshank Wildlife Rehabilitation Trust's aggregate liability "
   "shall not exceed 1 times the annual rehabilitation-program fees paid.",
   {}, "AUTOMATABLE", "ACCEPT", "plain control, trust-adjacent entity name",
   "Third plain control, entity name uses 'Trust' suffix to test entity-name-fragment capture "
   "doesn't misfire on the word 'Trust'.")
_c("F3-L-20", "liability", "liability", 1,
   "9. Limitation of Liability. Marlowe & Finch Custom Bookbinding's aggregate liability shall "
   "not exceed 1 times the annual bindery fees paid.",
   {}, "AUTOMATABLE", "ACCEPT", "ampersand in entity name",
   "Entity name contains '&' — tests whether the multi-word name capture tolerates a non-letter "
   "connector without breaking (similar risk class to the earlier hyphen-in-name issue).")

# ===========================================================================
# 2. INDEMNIFICATION (20)
# ===========================================================================
_c("F3-I-01", "indemnification", "indemnification", 1,
   "8. Indemnification. Hollowreach Cave Tour Operators shall indemnify, defend, and hold "
   "harmless Guest from third-party claims arising from Hollowreach Cave Tour Operators' own "
   "negligence, up to a cap of 1 times the annual tour fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT", "ordinary clean obligation",
   "Plain control, fresh domain.")
_c("F3-I-02", "indemnification", "indemnification", 2,
   "8. Indemnification. Pinnacle Ridge Search & Rescue Training shall indemnify, defend, and hold "
   "harmless Trainee, and Trainee shall indemnify, defend, and hold harmless Pinnacle Ridge "
   "Search & Rescue Training, in each case from third-party claims arising from the indemnifying "
   "party's own negligence, up to a cap of 1 times the annual training fees paid, except that "
   "Trainee's obligation excludes claims arising from equipment malfunction.",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "reciprocal with a fresh differentiated exclusion category",
   "'excludes claims arising from equipment malfunction' — tests the fraud-trigger-style fix "
   "generalizes to a novel exclusion category not itself a tracked trigger keyword at all (a "
   "genuinely new category, unlike 'fraud' which was added as a category).")
_c("F3-I-03", "indemnification", "indemnification", 2,
   "8. Indemnification. Thistlebrook Organic Seed Bank shall indemnify, defend, and hold harmless "
   "Distributor, and Distributor shall indemnify, defend, and hold harmless Thistlebrook Organic "
   "Seed Bank, in each case from third-party claims arising from the indemnifying party's own "
   "negligence, up to a cap of 1 times the annual seed-licensing fees paid, and Thistlebrook "
   "Organic Seed Bank's indemnification obligation is subject to a causation standard of "
   "'direct and proximate cause,' whereas Distributor's indemnification obligation is subject to "
   "a 'but-for cause' standard.",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "causation-standard differentiation, fresh standard names",
   "Fresh causation-standard pair ('direct and proximate cause' vs. 'but-for cause') neither of "
   "which appeared in any prior corpus — tests generalization of the causation-standard "
   "comparison beyond its original 'sole and proximate'/'contributing cause' pair.")
_c("F3-I-04", "indemnification", "indemnification", 3,
   "8. Indemnification. Larkspur Custom Perfumery Corp shall indemnify, defend, and hold harmless "
   "Retailer, and Retailer shall indemnify, defend, and hold harmless Larkspur Custom Perfumery "
   "Corp, in each case from third-party claims arising from the indemnifying party's own "
   "negligence, up to a cap of 1 times the annual fragrance-licensing fees paid, except that "
   "Larkspur Custom Perfumery Corp's obligation does not extend to claims arising from allergic "
   "reaction, whereas Retailer's indemnification obligation is subject to a 'contributing cause' "
   "standard.",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: exception-clause + causation-standard differentiation, fresh domain",
   "Same compound shape as S4B-COMP-05/07 (the two cases the Step 4A.7.1 cross-mechanism fix "
   "targeted) but with entirely fresh entity names, exclusion category, and causation standard — "
   "the most direct generalization test of that specific fix.")
_c("F3-I-05", "indemnification", "indemnification", 1,
   "8. Indemnification. Copperfield Vintage Motorcycle Restoration shall indemnify, defend, and "
   "hold harmless Consignor from third-party claims arising from Copperfield Vintage Motorcycle "
   "Restoration's own gross negligence, up to a cap of 2 times the annual restoration fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT", "ordinary clean obligation",
   "Plain control at the 2x threshold.")
_c("F3-I-06", "indemnification", "indemnification", 2,
   "8. Indemnification. Fenwick Artisanal Cheese Affinage shall indemnify, defend, and hold "
   "harmless Buyer from third-party claims arising from Fenwick Artisanal Cheese Affinage's own "
   "negligence, up to a cap of 1 times the annual affinage fees paid, PROVIDED THAT if the claim "
   "arises from a defect in cheese aged by Fenwick Artisanal Cheese Affinage's Vermont facility "
   "specifically (as opposed to its other facilities), the cap for that specific claim shall "
   "instead be 3 times the annual affinage fees paid.",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "conditional monetary escalation tied to a facility, not a second named party",
   "A NEW variant of the exception-clause differentiation family: the escalation condition names "
   "a FACILITY (a sub-entity of the SAME party), not a different named party — tests whether the "
   "general exception-clause detector over-fires (there's technically no 'second party' at all "
   "here, just a scope qualifier on the same party's own obligation) or correctly still catches it.")
_c("F3-I-07", "indemnification", "indemnification", 1,
   "8. Indemnification. Moonvale Herbal Apothecary shall indemnify, defend, and hold harmless "
   "Wholesaler from third-party claims arising from Moonvale Herbal Apothecary's own negligence, "
   "up to a cap of 1 times the annual apothecary fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT", "plain control",
   "Second plain control.")
_c("F3-I-08", "indemnification", "indemnification", 2,
   "8. Indemnification. Windmere Pipe Organ Restoration Guild shall indemnify, defend, and hold "
   "harmless Cathedral, and Cathedral shall indemnify, defend, and hold harmless Windmere Pipe "
   "Organ Restoration Guild, in each case from third-party claims arising from the indemnifying "
   "party's own negligence, up to a cap of 1 times the annual restoration fees paid, and each "
   "party's indemnification obligations shall additionally require forty-five (45) days' prior "
   "written notice before any claim may be asserted against it.",
   {"contract_side": "buy_side"}, "AUTOMATABLE", "ACCEPT",
   "genuinely symmetric procedural term, fresh domain",
   "'each party's' generic placeholder — true symmetric control, must not escalate.")
_c("F3-I-09", "indemnification", "indemnification", 3,
   "8. Indemnification. Thackeray & Vance Rare Book Appraisers shall indemnify, defend, and hold "
   "harmless Auction House from third-party claims arising from Thackeray & Vance Rare Book "
   "Appraisers' own negligence, up to a cap of the Appraisal Liability Cap. 'Appraisal Liability "
   "Cap' means, for purposes of Section 8.1, 1 times the annual appraisal fees paid, and means, "
   "for purposes of Section 24 (Insurance Coordination), 3 times the annual appraisal fees paid.",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "conflicting defined term on the indemnification side, fresh domain",
   "Tests whether the Step 4A.7.1 conflicting-defined-term fix (built for liability's monetary "
   "regex and independently for payment-terms) generalizes to indemnification's SEPARATE monetary "
   "extraction regex, which was never itself given this specific fix.")
_c("F3-I-10", "indemnification", "indemnification", 1,
   "8. Indemnification. Somerled Highland Cattle Ranch shall indemnify, defend, and hold harmless "
   "Buyer from third-party claims arising from Somerled Highland Cattle Ranch's own negligence, "
   "up to a cap of 1 times the annual herd-management fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT", "plain control",
   "Third plain control, compound basis modifier.")
_c("F3-I-11", "indemnification", "indemnification", 2,
   "8. Indemnification. Thornapple Cider Press Cooperative undertakes to make Retailer whole for, "
   "and to assume the defense of, any third-party claims arising from Thornapple Cider Press "
   "Cooperative's own negligence, up to a cap of 1 times the annual pressing fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT",
   "closed synonym-idiom family, fresh domain",
   "Tests the EXISTING 'undertakes to make...whole for, and to assume the defense of' synonym "
   "regex (not modified this session) against a fresh domain, confirming it still generalizes.")
_c("F3-I-12", "indemnification", "indemnification", 3,
   "8. Indemnification. Ashgrove Community Solar Cooperative shall indemnify, defend, and hold "
   "harmless Member, and Member shall indemnify, defend, and hold harmless Ashgrove Community "
   "Solar Cooperative, in each case from third-party claims arising from the indemnifying party's "
   "own negligence, up to a cap of 1 times the annual membership fees paid, except that claims "
   "involving equipment theft attributable to Ashgrove Community Solar Cooperative shall survive "
   "for six (6) years instead of the otherwise-applicable period.",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "survival-period differentiation via 'attributable to', fresh category",
   "Same shape as A6-I-18 (the survival-period fix target) with a fresh trigger category "
   "('equipment theft', not 'data-breach') — direct generalization test.")
_c("F3-I-13", "indemnification", "indemnification", 1,
   "8. Indemnification. Featherstone Falconry Supply Co. shall indemnify, defend, and hold "
   "harmless Buyer from third-party claims arising from Featherstone Falconry Supply Co.'s own "
   "negligence, up to a cap of 1 times the annual supply fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT", "plain control",
   "Fourth plain control.")
_c("F3-I-14", "indemnification", "indemnification", 2,
   "8. Indemnification. Redcliff Canyon Zipline Adventures agrees to hold Guest harmless from and "
   "defend Guest against any and all third-party claims arising from Redcliff Canyon Zipline "
   "Adventures' own gross negligence, up to a cap of 1 times the annual adventure fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT",
   "closed synonym-idiom family (hold-harmless variant), fresh domain",
   "Tests the 'hold X harmless from and defend X against' synonym regex on a fresh domain.")
_c("F3-I-15", "indemnification", "indemnification", 3,
   "8. Indemnification. Marchbanks Custom Violin Makers shall indemnify, defend, and hold "
   "harmless Conservatory from third-party claims arising from Marchbanks Custom Violin Makers' "
   "own negligence, up to a cap of the Instrument Liability Amount, which the parties agree, "
   "subject to periodic revaluation by an independent appraiser, is $150,000.",
   {"contract_side": "sell_side"}, "AUTOMATABLE",
   "ESCALATE or ACCEPT depending on config (fixed-dollar, interposed-clause defined-term delegation)",
   "defined-term monetary delegation with interposed clause, indemnification side",
   "Tests whether liability's interposed-clause defined-term-delegation fix (Step 4A.7.1) has any "
   "counterpart need on indemnification's separate monetary regex — indemnification's "
   "_MONETARY_FIXED_RE was never examined for this specific gap.")
_c("F3-I-16", "indemnification", "indemnification", 1,
   "8. Indemnification. Willowmere Antique Map Dealers shall indemnify, defend, and hold harmless "
   "Buyer from third-party claims arising from Willowmere Antique Map Dealers' own negligence, up "
   "to a cap of 1 times the annual dealership fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT", "plain control",
   "Fifth plain control.")
_c("F3-I-17", "indemnification", "indemnification", 2,
   "8. Indemnification. Nightjar Astronomical Observatory Tours shall indemnify, defend, and hold "
   "harmless Guest, and Guest shall indemnify, defend, and hold harmless Nightjar Astronomical "
   "Observatory Tours, in each case from third-party claims arising from the indemnifying party's "
   "own negligence, up to a cap of 1 times the annual tour fees paid, and both parties' "
   "indemnification obligations are subject to the identical thirty (30) day notice requirement "
   "described in Section 15.",
   {"contract_side": "buy_side"}, "AUTOMATABLE", "ACCEPT",
   "symmetric cross-referenced notice requirement, fresh domain",
   "'both parties'' generic placeholder plus a shared cross-reference — must resolve automatically.")
_c("F3-I-18", "indemnification", "indemnification", 3,
   "8. Indemnification. Thistledown Wool & Fiber Guild shall indemnify, defend, and hold harmless "
   "Spinner, and Spinner shall indemnify, defend, and hold harmless Thistledown Wool & Fiber "
   "Guild, in each case from third-party claims arising from the indemnifying party's own "
   "negligence, up to a cap of 1 times the annual guild fees paid, except that Spinner's "
   "obligation does not extend to claims arising from allergic reaction to raw fiber, a fact that "
   "does not affect either party's indemnification obligations under this Section beyond the "
   "stated exclusion.",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "genuine exclusion immediately followed by a partial self-negation phrase",
   "A deliberately adversarial near-miss: contains the self-negation phrase ('does not affect "
   "either party's...obligations') that the A6-I-37 fix is designed to make the detector SKIP, "
   "but here the self-negation is qualified ('...beyond the stated exclusion') so the exclusion "
   "is REAL, not a bystander aside — tests whether the self-negation check over-fires on a "
   "genuine exception that merely uses similar words.")
_c("F3-I-19", "indemnification", "indemnification", 1,
   "8. Indemnification. Hallowmere Antique Silver Restoration shall indemnify, defend, and hold "
   "harmless Buyer from third-party claims arising from Hallowmere Antique Silver Restoration's "
   "own negligence, up to a cap of 1 times the annual restoration fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT", "plain control",
   "Sixth plain control.")
_c("F3-I-20", "indemnification", "indemnification", 2,
   "8. Indemnification. Crestfall Timber Framing Guild shall bear full responsibility for "
   "defending and satisfying any claim on Homeowner's behalf, arising from Crestfall Timber "
   "Framing Guild's own negligence, up to a cap of 1 times the annual framing fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT",
   "closed synonym-idiom family (bear-responsibility variant), fresh domain",
   "Tests the 'shall bear full responsibility for defending and satisfying...on X's behalf' "
   "synonym regex on a fresh domain.")

# ===========================================================================
# 3. PAYMENT TERMS (20)
# ===========================================================================
_c("F3-P-01", "payment_terms", "payment_terms", 1,
   "6. Payment Terms. Invoices under this Agreement are due Net 45 from the date of invoice.",
   {}, "AUTOMATABLE", "ACCEPT", "ordinary net-days", "Plain control.")
_c("F3-P-02", "payment_terms", "payment_terms", 2,
   "6. Payment Terms. Client shall remit payment within 30 days of receiving Vendor's invoice, "
   "and Client shall be permitted to recoup from any future payment due to Vendor any amount that "
   "Vendor is independently required to pay Client under the separate quality-rebate program "
   "described in Exhibit Q.",
   {"prohibit_set_off": True}, "AUTOMATABLE", "MUST_REDLINE",
   "set-off via cross-referenced exhibit, fresh 'required to pay' phrasing",
   "Tests the bounded 'obligated/required to remit/pay' synonym extension (Step 4A.7 Phase G) "
   "with 'required to pay' specifically (the fix's phrasing was 'obligated to remit'/'required to "
   "pay' — this exercises the second alternative directly).")
_c("F3-P-03", "payment_terms", "payment_terms", 3,
   "6. Payment Terms. Rather than each party paying the other in full each month, the parties "
   "shall settle only the net shortfall between what Licensor is due from Licensee and what "
   "Licensee is due from Licensor under this and all related license agreements, with that net "
   "shortfall payable within 15 days of each month's close.",
   {"prohibit_set_off": True}, "AUTOMATABLE", "MUST_REDLINE",
   "structural net-settlement, 'net shortfall' instead of 'net difference'",
   "Tests the _NET_SETTLEMENT_STRUCTURAL_RE fix's generalization: 'net shortfall' is a different "
   "noun than the fix's own 'net difference'/'resulting balance' alternatives — if this fails, "
   "it demonstrates the fix is a narrower vocabulary patch than the general shape it claims to be.")
_c("F3-P-04", "payment_terms", "payment_terms", 1,
   "6. Payment Terms. Client shall pay all undisputed invoiced amounts within 30 days; amounts in "
   "good-faith dispute may be withheld pending resolution.",
   {}, "AUTOMATABLE", "ACCEPT", "ordinary dispute-right clause", "Plain control.")
_c("F3-P-05", "payment_terms", "payment_terms", 2,
   "6. Payment Terms. The parties acknowledge that final pricing terms remain subject to "
   "completion of the ongoing rate study and agree to formalize them in a subsequent Pricing "
   "Addendum; no invoice shall issue until such Addendum is executed.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "deferred payment terms, fresh phrasing",
   "'no invoice shall issue until such Addendum is executed' — a fresh construction of the "
   "self-flagged-unresolved-payment-terms family (the fix's own phrase was 'no payment obligation "
   "arises until'; this uses a functionally identical but textually different construction).")
_c("F3-P-06", "payment_terms", "payment_terms", 3,
   "6. Payment Terms. Payment is due Net 30. For purposes of Section 6.2 (Early Payment Discount), "
   "'Net 30' shall mean thirty calendar days from invoice date, and for purposes of Section 6.5 "
   "(Late Fee Calculation), 'Net 30' shall instead mean thirty business days from invoice date.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "conflicting Net-30 definition, reordered clause structure",
   "Same underlying concept as A6-P-48 but with the 'for purposes of Section N' clause placed "
   "BEFORE the quoted term instead of after — tests whether the fix's regex, which assumed a "
   "specific clause order, is sensitive to this reordering.")
_c("F3-P-07", "payment_terms", "payment_terms", 1,
   "6. Payment Terms. Client shall pay Vendor within 60 days of the later of invoice date or "
   "delivery date.",
   {}, "AUTOMATABLE", "ACCEPT", "ordinary trigger clause", "Plain control.")
_c("F3-P-08", "payment_terms", "payment_terms", 2,
   "6. Payment Terms. Vendor shall be entitled to deduct from any amount otherwise payable to "
   "Client the value of any nonconforming goods Client has rejected under Section 4, as measured "
   "by the rejected goods' invoiced price.",
   {"prohibit_set_off": True}, "AUTOMATABLE", "ACCEPT",
   "rejected-goods price deduction — hard negative, not mutual debt netting",
   "A self-help deduction tied to Client's OWN performance failure (rejected goods), not a debt "
   "Client independently owes Vendor — must NOT trigger the set-off detector, testing precision "
   "on a fresh hard-negative shape.")
_c("F3-P-09", "payment_terms", "payment_terms", 3,
   "6. Payment Terms. Distributor shall remit payment to Manufacturer within 30 days, PROVIDED "
   "THAT for shipments under the Coastal Region Program specifically, payment shall instead be "
   "due within 45 days, it not yet being determined which shipments qualify for the Coastal "
   "Region Program as of this excerpt.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "conditional payment-period conflict with unresolved qualifier",
   "A genuinely new mechanism: two DIFFERENT net-day values (30 vs. 45) exist, but which applies "
   "depends on an unresolved classification (\"which shipments qualify\") rather than a simple "
   "stated conflict — tests generalization of net_days_conflict detection to a conditional shape.")
_c("F3-P-10", "payment_terms", "payment_terms", 1,
   "6. Payment Terms. Client shall pay Vendor's invoices within 30 days; late payments accrue "
   "interest at 1.5% per month.",
   {}, "AUTOMATABLE", "ACCEPT", "ordinary late-fee clause", "Plain control.")
_c("F3-P-11", "payment_terms", "payment_terms", 2,
   "6. Payment Terms. Rather than remitting duplicate payments, the parties agree that only the "
   "true-up amount determined at each quarter's close, reflecting the difference between "
   "Franchisor's royalty entitlement and Franchisee's marketing-fund credit, shall be transferred "
   "between the parties.",
   {"prohibit_set_off": True}, "AUTOMATABLE", "MUST_REDLINE",
   "'true-up amount...shall be transferred' — structural netting without 'only the net/balance'",
   "A THIRD structural phrasing of net settlement, using 'true-up amount' as the subject rather "
   "than 'net difference'/'net shortfall' — a harder generalization test since it doesn't even "
   "use the word 'net' at all.")
_c("F3-P-12", "payment_terms", "payment_terms", 3,
   "6. Payment Terms. Retailer shall pay Wholesaler within 30 days of invoice, and Wholesaler "
   "shall be entitled to withhold shipment of future orders (but not to withhold or reduce any "
   "payment already invoiced) if Retailer's account becomes more than 60 days past due.",
   {"prohibit_set_off": True}, "AUTOMATABLE", "ACCEPT",
   "withhold-shipment-not-payment — hard negative, explicit carve-out",
   "Explicitly and self-consciously distinguishes withholding SHIPMENT from withholding PAYMENT — "
   "must not trigger the set-off detector despite using 'withhold' near a payment context.")
_c("F3-P-13", "payment_terms", "payment_terms", 1,
   "6. Payment Terms. Client shall pay all amounts due within 45 days of invoice date, in U.S. "
   "Dollars.",
   {}, "AUTOMATABLE", "ACCEPT", "ordinary currency clause", "Plain control.")
_c("F3-P-14", "payment_terms", "payment_terms", 2,
   "6. Payment Terms. Buyer shall pay Seller within 30 days, and Seller shall self-assess and "
   "remit any applicable goods-and-services tax directly to the taxing authority, with Buyer "
   "bearing no responsibility for such remittance.",
   {"require_tax_responsibility_counterparty": True}, "AUTOMATABLE", "MUST_REDLINE",
   "tax-on-us via self-assessment language, fresh phrasing",
   "'self-assess and remit...with Buyer bearing no responsibility' — tests generalization of tax-"
   "responsibility attribution to a self-assessment construction rather than a direct "
   "'responsible for' statement.")
_c("F3-P-15", "payment_terms", "payment_terms", 3,
   "6. Payment Terms. Licensee shall pay royalties within 30 days of each quarter's close, "
   "calculated per the royalty rate set forth in Schedule R, which Schedule R itself "
   "cross-references the then-current Rate Card maintained by Licensor's finance department (not "
   "included in this excerpt).",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "chained delegation, payment-terms side",
   "Payment-terms counterpart of the F3-L-18/A6-RB-07 chained-delegation shape — tests whether "
   "payment_terms_policy_engine.py needs (or already has) an equivalent chained-delegation "
   "detector; none was built for this adapter in any prior step.")
_c("F3-P-16", "payment_terms", "payment_terms", 1,
   "6. Payment Terms. Client shall pay Vendor within 30 days of invoice date; invoices shall be "
   "submitted monthly.",
   {}, "AUTOMATABLE", "ACCEPT", "ordinary invoice-frequency clause", "Plain control.")
_c("F3-P-17", "payment_terms", "payment_terms", 2,
   "6. Payment Terms. Distributor shall be entitled to apply any credit memo issued by "
   "Manufacturer against Distributor's next invoice.",
   {"prohibit_set_off": True}, "AUTOMATABLE", "ACCEPT",
   "credit-memo application — hard negative",
   "Ordinary credit-memo application is a routine accounting mechanic, not mutual debt netting — "
   "must not trigger the set-off detector.")
_c("F3-P-18", "payment_terms", "payment_terms", 3,
   "6. Payment Terms. Franchisee shall remit royalties within 30 days, it remaining under "
   "negotiation whether the royalty base includes online sales originating outside the "
   "Franchisee's designated territory.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "self-flagged basis ambiguity, payment-terms side",
   "Payment-terms counterpart of F3-L-13's self-flagged basis-value ambiguity — tests whether the "
   "self-flagged-unresolved fix (built primarily around deferred/unexecuted-instrument phrasing) "
   "also generalizes to a basis-scope ambiguity specifically.")
_c("F3-P-19", "payment_terms", "payment_terms", 1,
   "6. Payment Terms. Client shall pay Vendor within 30 days; disputed amounts remain payable "
   "pending resolution unless withholding is expressly authorized elsewhere in this Agreement.",
   {}, "AUTOMATABLE", "ACCEPT", "ordinary undisputed-still-payable clause", "Plain control.")
_c("F3-P-20", "payment_terms", "payment_terms", 2,
   "6. Payment Terms. Wholesaler shall pay Grower within 15 days of delivery, and Grower shall "
   "be entitled to net any quality-rejection credits against Wholesaler's next scheduled payment, "
   "where such credits reflect amounts Wholesaler independently owes Grower under the separate "
   "cooperative marketing agreement.",
   {"prohibit_set_off": True}, "AUTOMATABLE", "MUST_REDLINE",
   "true set-off dressed as a 'quality-rejection credit', cross-referenced independent debt",
   "A deliberately adversarial near-miss to F3-P-08/F3-P-17 (which are legitimate hard negatives) "
   "— this one uses similar 'credit'/'rejection' vocabulary but the credits are explicitly tied "
   "to an INDEPENDENT debt Wholesaler owes Grower under a separate agreement, which is genuine "
   "mutual-debt netting, not an ordinary accounting adjustment.")

# ===========================================================================
# 4. RECIPROCAL / ROLE CASES (20)
# ===========================================================================
_c("F3-R-01", "reciprocal_role", "indemnification", 2,
   "8. Indemnification. Each party shall indemnify the other party from third-party claims "
   "arising from its own negligence, up to a cap of 1 times the fees paid, except that "
   "Northwind Aerial Survey Corp (but not any subcontracted pilot) shall be solely responsible "
   "for defending claims arising from FAA regulatory violations.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "reciprocal + party-specific exclusive-defense grant",
   "Same shape as A6-I-12 (the 'but not [subgroup]' fix target) with a fresh subgroup phrase "
   "('subcontracted pilot') and a fresh claim category (FAA violations).")
_c("F3-R-02", "reciprocal_role", "indemnification", 1,
   "8. Indemnification. Each party shall indemnify the other party from third-party claims "
   "arising from its own negligence, up to a cap of 1 times the fees paid.",
   {}, "AUTOMATABLE", "ACCEPT", "plain reciprocal control", "Plain control.")
_c("F3-R-03", "reciprocal_role", "liability", 3,
   "9. Limitation of Liability. Custodian's aggregate liability to Beneficiary shall not exceed "
   "1 times the annual custodial fees paid.",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "unmapped role pair, fresh vocabulary, directional contract_side",
   "Direct generalization test of the Step 4A.7.2 role-attribution fix: 'Custodian'/'Beneficiary' "
   "(trust/custody vocabulary) is a fresh unmapped pair not used in that fix's own benchmark.")
_c("F3-R-04", "reciprocal_role", "liability", 2,
   "9. Limitation of Liability. Trustee's aggregate liability to Grantor shall not exceed 1 "
   "times the annual trustee fees paid.",
   {}, "AUTOMATABLE", "ACCEPT", "unmapped role pair, MUTUAL contract_side",
   "Same unmapped-vocabulary shape as F3-R-03 but mutual contract_side (kwargs empty) — must NOT "
   "escalate, direct generalization test of the contract_side gate.")
_c("F3-R-05", "reciprocal_role", "indemnification", 2,
   "8. Indemnification. Harborview Ferry Operators shall indemnify, defend, and hold harmless "
   "Passenger, and Passenger shall indemnify, defend, and hold harmless Harborview Ferry "
   "Operators, in each case from third-party claims arising from the indemnifying party's own "
   "negligence, up to a cap of 1 times the annual fare revenue paid, and Harborview Ferry "
   "Operators' indemnification obligations shall survive termination for four (4) years, whereas "
   "Passenger's indemnification obligations shall survive termination for four (4) years as "
   "well.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT",
   "identical-value near-miss control, fresh domain",
   "Two named roles with IDENTICAL survival values (4 years each) — must resolve automatically, "
   "not be mistaken for differentiation (same shape as the asym-19 permanent regression case).")
_c("F3-R-06", "reciprocal_role", "indemnification", 3,
   "8. Indemnification. Blackthorn Fencing & Ironwork shall indemnify, defend, and hold harmless "
   "Client, and Client shall indemnify, defend, and hold harmless Blackthorn Fencing & Ironwork, "
   "in each case from third-party claims arising from the indemnifying party's own negligence, up "
   "to a cap of 1 times the fees paid, and Blackthorn Fencing & Ironwork's obligation is subject "
   "to a causation standard of 'sole cause,' whereas Client's obligation is subject to the "
   "identical 'sole cause' standard.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT",
   "identical causation-standard near-miss control",
   "Both parties explicitly stated to have the SAME causation standard ('sole cause' for both) — "
   "must not be misread as a differentiation merely because two attributions exist.")
_c("F3-R-07", "reciprocal_role", "liability", 2,
   "9. Limitation of Liability. Depositor's aggregate liability to Warehouseman shall not exceed "
   "1 times the annual storage fees paid.",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "unmapped role pair, warehousing vocabulary",
   "Another fresh unmapped pair ('Depositor'/'Warehouseman') with a directional contract_side.")
_c("F3-R-08", "reciprocal_role", "indemnification", 2,
   "8. Indemnification. Silverpine Timber Cooperative shall indemnify, defend, and hold harmless "
   "Mill, and Mill shall indemnify, defend, and hold harmless Silverpine Timber Cooperative, in "
   "each case from third-party claims arising from the indemnifying party's own negligence, up to "
   "a cap of 1 times the fees paid, except that Silverpine Timber Cooperative's obligation does "
   "not extend to claims arising from wildfire.",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "single-role exception-clause differentiation, fresh category",
   "Direct generalization test of the general exception-clause detector on a fresh category "
   "('wildfire') and fresh entity names.")
_c("F3-R-09", "reciprocal_role", "liability", 1,
   "9. Limitation of Liability. Bailee's aggregate liability to Bailor shall not exceed 1 times "
   "the annual bailment fees paid.",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "unmapped role pair, bailment vocabulary, Tier 1 phrasing",
   "Tests the role-attribution fix at Tier 1 (ordinary, non-adversarial phrasing) rather than "
   "Tier 2/3 — confirms the fix isn't accidentally scoped to only complex sentences.")
_c("F3-R-10", "reciprocal_role", "indemnification", 1,
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Client, and Client "
   "shall indemnify, defend, and hold harmless Vendor, in each case from third-party claims "
   "arising from the indemnifying party's own negligence, up to a cap of 1 times the fees paid.",
   {"contract_side": "buy_side"}, "AUTOMATABLE", "ACCEPT",
   "plain named-pair reciprocal control, generic vocabulary",
   "Plain control confirming the named-pair (not 'each party') symmetric path still works "
   "cleanly with ordinary vocabulary.")
_c("F3-R-11", "reciprocal_role", "indemnification", 3,
   "8. Indemnification. Nightshade Apothecary Guild shall indemnify, defend, and hold harmless "
   "Buyer, and Buyer shall indemnify, defend, and hold harmless Nightshade Apothecary Guild, in "
   "each case from third-party claims arising from the indemnifying party's own negligence, up to "
   "a cap of 1 times the fees paid, and Nightshade Apothecary Guild's indemnification obligation "
   "is subject to a causation standard of 'proximate cause,' whereas Buyer's indemnification "
   "obligation is subject to a materially different 'sole and exclusive cause' standard.",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "causation-standard differentiation, named-pair (not reciprocal-opener) shape",
   "Same causation-standard concept as F3-I-03 but using the STRICTLY-NAMED PAIR shape (two "
   "separate 'X shall indemnify Y' sentences) rather than the 'each party' reciprocal opener — "
   "tests the OTHER code path (same_pair equality check) rather than _detect_reciprocal_asymmetry.")
_c("F3-R-12", "reciprocal_role", "liability", 2,
   "9. Limitation of Liability. Consignor's aggregate liability to Consignee shall not exceed 1 "
   "times the annual consignment-handling fees paid.",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "unmapped role pair with a compound-modifier basis",
   "Combines the role-attribution fix and the basis-modifier fix in the SAME sentence — tests "
   "that the role-attribution check still fires even though the basis extracts cleanly.")
_c("F3-R-13", "reciprocal_role", "indemnification", 2,
   "8. Indemnification. Redshank Falconry Supply shall indemnify, defend, and hold harmless "
   "Buyer, and Buyer shall indemnify, defend, and hold harmless Redshank Falconry Supply, in each "
   "case from third-party claims arising from the indemnifying party's own negligence, up to a "
   "cap of 1 times the fees paid, and Redshank Falconry Supply's indemnification obligation "
   "requires fifteen (15) days' prior written notice, whereas Buyer's indemnification obligation "
   "requires the identical fifteen (15) days' prior written notice.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT",
   "identical notice-requirement near-miss, named-pair shape",
   "Named-pair (not reciprocal-opener) identical-value control — tests the same_pair equality "
   "check's notice_required comparison specifically.")
_c("F3-R-14", "reciprocal_role", "liability", 3,
   "9. Limitation of Liability. Escrow Agent's aggregate liability to Principal shall not exceed "
   "1 times the annual escrow fees paid, it being acknowledged that 'Escrow Agent' and 'Principal' "
   "are not otherwise defined in this excerpt.",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "unmapped role pair with an explicit self-acknowledgment of no definition",
   "Combines the role-attribution gap with an explicit self-flagged-absence-of-definition "
   "statement — tests whether either or both mechanisms correctly escalate (should not conflict "
   "or double-fire incorrectly).")
_c("F3-R-15", "reciprocal_role", "indemnification", 1,
   "8. Indemnification. Supplier shall indemnify, defend, and hold harmless Buyer, and Buyer "
   "shall indemnify, defend, and hold harmless Supplier, in each case from third-party claims "
   "arising from the indemnifying party's own negligence, up to a cap of 1 times the fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT", "plain control", "Plain control.")
_c("F3-R-16", "reciprocal_role", "indemnification", 2,
   "8. Indemnification. Thistlebury Antique Instrument Restorers shall indemnify, defend, and "
   "hold harmless Museum, and Museum shall indemnify, defend, and hold harmless Thistlebury "
   "Antique Instrument Restorers, in each case from third-party claims arising from the "
   "indemnifying party's own negligence, up to a cap of 1 times the fees paid, except that "
   "Museum's obligation does not extend to claims arising from provenance disputes.",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "single-role exclusion attached to the OTHER party (beneficiary, not the obligor tested so far)",
   "Most prior exception-clause tests named the FIRST-mentioned party; this one differentiates "
   "the SECOND-mentioned party ('Museum') — tests the detector isn't order-dependent.")
_c("F3-R-17", "reciprocal_role", "liability", 2,
   "9. Limitation of Liability. Licensor's aggregate liability to Sublicensee shall not exceed 1 "
   "times the annual sublicense fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT",
   "one mapped role, one unmapped role, directional contract_side",
   "'Licensor' resolves (sell_side) but 'Sublicensee' does not — tests that the fix correctly "
   "requires BOTH roles unmapped, not just one, before escalating (by design, per the A6-L-52 "
   "root-cause: only fire when NEITHER role has a mapping).")
_c("F3-R-18", "reciprocal_role", "indemnification", 3,
   "8. Indemnification. Each party shall indemnify the other party from third-party claims "
   "arising from its own negligence, up to a cap of 1 times the fees paid, except that Coastal "
   "Ridge Vineyard Management (but not any seasonal harvest contractor) shall be solely "
   "responsible for defending claims arising from pesticide drift, and Client's indemnification "
   "obligation is subject to a 'contributing cause' standard.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: reciprocal-opener exception-clause + causation-standard, fresh names",
   "A THIRD instance of the compound cross-mechanism shape (reciprocal opener this time, not "
   "named-pair like F3-I-04) — broadens the generalization test of the Step 4A.7.2... actually "
   "Step 4A.7.1 cross-mechanism fix to the reciprocal-opener code path specifically.")
_c("F3-R-19", "reciprocal_role", "liability", 1,
   "9. Limitation of Liability. Chargee's aggregate liability to Chargor shall not exceed 1 "
   "times the annual facility fees paid.",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "unmapped role pair, UK secured-lending vocabulary",
   "'Chargee'/'Chargor' (English secured-lending terminology) — another fresh unmapped pair, "
   "tests generalization to non-US legal vocabulary.")
_c("F3-R-20", "reciprocal_role", "indemnification", 2,
   "8. Indemnification. Bramblewood Orchard Cooperative shall indemnify, defend, and hold "
   "harmless Packer, and Packer shall indemnify, defend, and hold harmless Bramblewood Orchard "
   "Cooperative, in each case from third-party claims arising from the indemnifying party's own "
   "negligence, up to a cap of 1 times the fees paid, and both parties shall each control the "
   "defense of any claim for which each is respectively the indemnifying party.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT",
   "symmetric defense-control grant near-miss, fresh domain",
   "Same shape as the A6-I-15 permanent control (symmetric 'each...respectively' defense-control "
   "grant) — must resolve automatically, not be mistaken for asymmetric differentiation.")

# ===========================================================================
# 5. CROSS-REFERENCE / DEFINITION / AMBIGUITY (20)
# ===========================================================================
_c("F3-D-01", "cross_ref_definition_ambiguity", "liability", 2,
   "9. Limitation of Liability. Aggregate liability shall not exceed the Ceiling Amount. "
   "'Ceiling Amount' is defined in Section 9.2 as $200,000, and separately in Section 31 "
   "(Warranty Interaction) as $500,000.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "conflicting defined term, ORIGINAL fixed-phrase shape",
   "Uses the EXACT phrase shape ('is defined in Section X as..., and separately in Section Y "
   "as...') the original Step 4A.5 fix targeted — a control confirming that mechanism still works "
   "after all subsequent generalizations, not just the newer 'means...for purposes of' shape.")
_c("F3-D-02", "cross_ref_definition_ambiguity", "liability", 1,
   "9. Limitation of Liability. Aggregate liability shall not exceed the Ceiling Amount. "
   "'Ceiling Amount' means $300,000, as further described in Section 12 for reference purposes "
   "only.",
   {}, "AUTOMATABLE", "ACCEPT", "single consistent definition with a harmless cross-reference",
   "A near-miss control: only ONE definition exists, with a bystander reference to another "
   "Section that does NOT restate or conflict — must resolve automatically, not be mistaken for "
   "the conflicting-definition shape.")
_c("F3-D-03", "cross_ref_definition_ambiguity", "payment_terms", 2,
   "6. Payment Terms. Payment is due Net 30. 'Net 30' means thirty days from invoice date, as "
   "also confirmed in Section 19.",
   {}, "AUTOMATABLE", "ACCEPT", "single consistent definition with harmless cross-reference, payment side",
   "Payment-terms counterpart of F3-D-02 — single definition, bystander confirming cross-"
   "reference, must not escalate.")
_c("F3-D-04", "cross_ref_definition_ambiguity", "liability", 3,
   "9. Limitation of Liability. Aggregate liability shall not exceed 1 times the annual fees "
   "paid, calculated per the fee schedule in Exhibit A, which Exhibit A itself references the "
   "master rate table maintained in Exhibit B (not included in this excerpt).",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "chained delegation via Exhibit-to-Exhibit, fresh phrasing",
   "Chained delegation using 'Exhibit' for BOTH levels (the fix's own test case used 'Section' "
   "then 'Schedule') — tests whether same-document-type chaining is still caught.")
_c("F3-D-05", "cross_ref_definition_ambiguity", "liability", 1,
   "9. Limitation of Liability. Aggregate liability shall not exceed 1 times the annual fees "
   "paid, calculated per the fee schedule in Exhibit A.",
   {}, "AUTOMATABLE", "ACCEPT", "single-level cross-reference, no chain",
   "A near-miss control: ONE level of delegation only (no 'which Exhibit A itself references...'"
   " second hop) — the existing single-level cross-reference handling should resolve this "
   "automatically without needing the chained-delegation escalation.")
_c("F3-D-06", "cross_ref_definition_ambiguity", "indemnification", 2,
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Client from claims "
   "described in the Indemnification Schedule, which Indemnification Schedule itself "
   "incorporates by reference the risk-allocation matrix attached to the Master Services "
   "Agreement (not included in this excerpt).",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "chained delegation, indemnification side",
   "Indemnification counterpart of the chained-delegation family — no equivalent detector was "
   "built for this adapter in any prior step (only liability got the Section-4/Schedule-B fix); "
   "tests whether this is a genuine, disclosed gap.")
_c("F3-D-07", "cross_ref_definition_ambiguity", "liability", 2,
   "9. Limitation of Liability. Aggregate liability shall not exceed 1 times the annual fees "
   "paid, it being unclear whether 'fees' as used in this Section includes pass-through expenses "
   "billed separately.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "original 'unclear whether' phrasing, basis-scoped",
   "Uses the EXACT original 'unclear whether' phrase (the fix's starting point before "
   "generalization) but scoped to the BASIS specifically rather than the whole cap — confirms "
   "the original mechanism still works after the family was widened.")
_c("F3-D-08", "cross_ref_definition_ambiguity", "liability", 1,
   "9. Limitation of Liability. Aggregate liability shall not exceed 1 times the annual fees "
   "paid, which fees are defined in Section 4 as all amounts invoiced under this Agreement.",
   {}, "AUTOMATABLE", "ACCEPT", "single clean definition, no conflict, no chain",
   "A near-miss control: a definition exists and is referenced, but there's no second "
   "conflicting definition and no further chain — must resolve automatically.")
_c("F3-D-09", "cross_ref_definition_ambiguity", "payment_terms", 3,
   "6. Payment Terms. Payment is due within the period stated in the Rate Sheet most recently "
   "issued by Vendor, it being noted that Vendor issues updated Rate Sheets quarterly and this "
   "excerpt does not specify which quarter's Rate Sheet governs.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "ambiguous-most-recent-instrument, fresh phrasing",
   "Same underlying concept as A6-RB-10 (ambiguous which of several instruments is 'most "
   "recent') but a fresh construction ('issues updated...quarterly and this excerpt does not "
   "specify which quarter's') rather than the fix's own 'does not indicate which is the most "
   "recent' phrase.")
_c("F3-D-10", "cross_ref_definition_ambiguity", "liability", 2,
   "9. Limitation of Liability. Aggregate liability shall not exceed either (a) 1 times the "
   "annual fees paid, or (b) $50,000, whichever is greater, as determined at the time a claim is "
   "asserted.",
   {}, "AUTOMATABLE", "NEGOTIATE or ESCALATE (greater-of, resolvable structure, value comparison needed)",
   "greater-of with an explicit resolution mechanism ('as determined at the time a claim is "
   "asserted')",
   "A near-miss control to the either/or-ambiguity family (A6-RB-09): this ALSO uses "
   "either/or language but explicitly states HOW and WHEN it resolves (greater-of, at claim "
   "time) rather than leaving the selection criterion genuinely undetermined — must be treated "
   "as the resolvable greater-of structure the system already handles, not escalated as ambiguous.")
_c("F3-D-11", "cross_ref_definition_ambiguity", "liability", 3,
   "9. Limitation of Liability. Aggregate liability shall not exceed either (a) 1 times the "
   "annual fees paid, or (b) the replacement cost of the damaged equipment, whichever the "
   "parties later determine to be more appropriate given the nature of the loss, no such "
   "determination having yet been made.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "either/or ambiguity, fresh domain",
   "Direct generalization test of the A6-RB-09 either/or-ambiguity fix on a fresh domain "
   "(equipment replacement cost vs. artwork fair market value).")
_c("F3-D-12", "cross_ref_definition_ambiguity", "indemnification", 2,
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Client from claims "
   "arising under this Agreement, the parties acknowledging that the precise scope of covered "
   "claims remains a matter not yet finally resolved and intended to be clarified in a future "
   "amendment.",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "self-flagged unresolved scope, indemnification side",
   "Direct generalization test of the self-flagged-unresolved fix on indemnification (the "
   "liability-side fix's exact phrase family, tested on the OTHER adapter that received an "
   "independent implementation of the same concept).")
_c("F3-D-13", "cross_ref_definition_ambiguity", "liability", 1,
   "9. Limitation of Liability. Aggregate liability shall not exceed 1 times the annual fees "
   "paid.",
   {}, "AUTOMATABLE", "ACCEPT", "plain control, no ambiguity of any kind", "Plain control.")
_c("F3-D-14", "cross_ref_definition_ambiguity", "liability", 2,
   "9. Limitation of Liability. Aggregate liability shall not exceed the Warranty Cap Amount. "
   "'Warranty Cap Amount' means $75,000 and 'Warranty Cap Amount' is restated for convenience in "
   "Section 40 as $75,000.",
   {}, "AUTOMATABLE", "ACCEPT",
   "restated-but-identical defined term, explicit 'for convenience' framing",
   "A near-miss control: the term is defined TWICE but the drafter explicitly frames the second "
   "instance as a convenience restatement with an IDENTICAL value — must not be mistaken for a "
   "genuine conflict.")
_c("F3-D-15", "cross_ref_definition_ambiguity", "payment_terms", 2,
   "6. Payment Terms. Late payments accrue interest at the Default Rate. 'Default Rate' means, "
   "for purposes of Section 6.8, 1.5% per month, and means, for purposes of Section 22 "
   "(Acceleration), 2.5% per month.",
   {"maximum_late_interest_rate_percent": 2.0}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "conflicting defined term, late-interest-rate concept",
   "A fresh application of the conflicting-defined-term shape to a late-fee RATE rather than a "
   "monetary cap or net-days value — tests generalization to a third policy-fact type.")
_c("F3-D-16", "cross_ref_definition_ambiguity", "liability", 3,
   "9. Limitation of Liability. Aggregate liability shall not exceed 1 times the annual fees "
   "paid, calculated per Section 4, which Section 4 cross-references Appendix C, which Appendix "
   "C in turn cross-references the vendor's own published rate card (external, not part of this "
   "Agreement).",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW", "THREE-level chained delegation",
   "A harder variant of the chained-delegation family: THREE levels (Section 4 -> Appendix C -> "
   "external rate card), not two — tests whether the fix (built for exactly two levels) still "
   "catches a deeper chain or requires the specific two-level shape.")
_c("F3-D-17", "cross_ref_definition_ambiguity", "liability", 1,
   "9. Limitation of Liability. Aggregate liability shall not exceed 2 times the annual fees "
   "paid.",
   {}, "AUTOMATABLE", "NEGOTIATE (2x)", "plain control at threshold", "Plain control.")
_c("F3-D-18", "cross_ref_definition_ambiguity", "indemnification", 3,
   "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Client from claims "
   "arising under this Agreement, up to a cap of the Indemnification Ceiling. 'Indemnification "
   "Ceiling' means, for purposes of the general indemnity in Section 8.1, 1 times the fees paid, "
   "and means, for purposes of the data-breach-specific indemnity in Section 8.4, 5 times the "
   "fees paid.",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "conflicting defined term, indemnification monetary side, category-scoped",
   "Combines the conflicting-defined-term shape with category-specific scoping language (general "
   "vs. data-breach-specific) — tests whether the detector still fires when the two 'for purposes "
   "of' clauses reference substantively different categories, not just different Section numbers.")
_c("F3-D-19", "cross_ref_definition_ambiguity", "liability", 2,
   "9. Limitation of Liability. Aggregate liability shall not exceed 1 times the annual fees "
   "paid. For the avoidance of doubt, 'annual fees' has the same meaning throughout this "
   "Agreement.",
   {}, "AUTOMATABLE", "ACCEPT", "explicit consistency assurance, near-miss control",
   "An explicit 'for the avoidance of doubt...has the same meaning throughout' clause — must not "
   "be mistaken for a self-flagged ambiguity signal merely because it discusses definitional "
   "scope.")
_c("F3-D-20", "cross_ref_definition_ambiguity", "payment_terms", 1,
   "6. Payment Terms. Payment is due Net 30 from invoice date, as defined in Section 1.",
   {}, "AUTOMATABLE", "ACCEPT", "plain control with a harmless single-definition cross-reference",
   "Plain control confirming an ordinary, single, non-conflicting cross-reference to a "
   "definitions section does not itself trigger review.")

# ===========================================================================
# 6. COMPOUND CASES (20, each combining 2-4 mechanisms)
# ===========================================================================
_c("F3-CM-01", "compound", "liability", 3,
   "1. Definitions. 'Consignor' means the entity delivering goods for sale, and 'Consignee' "
   "means the entity receiving them for sale on the Consignor's behalf.\n\n"
   "9. Limitation of Liability. Consignor's aggregate liability to Consignee shall not exceed 1 "
   "times the annual consignment-handling fees paid.",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: unmapped role pair + compound-hyphenated basis modifier",
   "Combines role-attribution (Consignor/Consignee unmapped) with a hyphenated basis modifier — "
   "both mechanisms present in one sentence; the role-attribution escalation must govern "
   "regardless of the basis extracting cleanly.")
_c("F3-CM-02", "compound", "liability", 3,
   "9. Limitation of Liability. Aggregate liability shall not exceed the Facility Cap Amount. "
   "'Facility Cap Amount' means, for purposes of Section 9, 1 times the annual usage-tier fees "
   "paid, and means, for purposes of Section 27 (Casualty Coordination), 4 times the annual "
   "usage-tier fees paid.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: conflicting defined term + compound-hyphenated basis modifier",
   "Combines conflicting-defined-term detection with a hyphenated basis modifier inside the "
   "conflicting value itself.")
_c("F3-CM-03", "compound", "indemnification", 3,
   "8. Indemnification. Each party shall indemnify the other party from third-party claims "
   "arising from its own negligence, up to a cap of the Coverage Ceiling. 'Coverage Ceiling' "
   "means, for purposes of Section 8.1, 1 times the fees paid, and means, for purposes of "
   "Section 8.9 (Cyber Incident Rider), 6 times the fees paid, except that Underwriting Partner "
   "(but not any reinsurer) shall be solely responsible for defending claims arising from "
   "regulatory fines.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: conflicting defined term + exception-clause differentiation, THREE mechanisms",
   "Combines conflicting-defined-term detection with a party-specific exception clause in the "
   "SAME provision — either mechanism alone should escalate; tests they don't interfere.")
_c("F3-CM-04", "compound", "payment_terms", 3,
   "6. Payment Terms. Payment is due Net 30. 'Net 30' for purposes of Section 6.1 shall mean "
   "thirty calendar days, and 'Net 30' for purposes of Section 6.9 (Early Termination) shall "
   "instead mean thirty business days, and Vendor shall be entitled to net any amount Client "
   "independently owes Vendor under the separate maintenance agreement against Client's next "
   "invoice.",
   {"prohibit_set_off": True}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: conflicting Net-30 definition + genuine set-off, payment terms",
   "Combines the conflicting-defined-term fix with a genuine set-off violation in the SAME "
   "clause — both are independently sufficient for REQUIRES_REVIEW-or-worse; tests neither "
   "mechanism accidentally suppresses the other (e.g. via an early-return path).")
_c("F3-CM-05", "compound", "liability", 3,
   "9. Limitation of Liability. Bailee's aggregate liability to Bailor shall not exceed 1 times "
   "the annual bailment fees paid, calculated per the fee schedule in Section 4, which Section 4 "
   "itself cross-references Schedule D (a rate table not included in this excerpt).",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: unmapped role pair + chained cross-reference delegation",
   "Combines two independently-sufficient escalation reasons (role attribution AND chained "
   "delegation) in one sentence — either alone should escalate.")
_c("F3-CM-06", "compound", "indemnification", 3,
   "8. Indemnification. Northstar Aerial Mapping Corp shall indemnify, defend, and hold harmless "
   "Client, and Client shall indemnify, defend, and hold harmless Northstar Aerial Mapping Corp, "
   "in each case from third-party claims arising from the indemnifying party's own negligence, up "
   "to a cap of 1 times the fees paid, and Northstar Aerial Mapping Corp's obligation is subject "
   "to a causation standard of 'direct cause,' whereas Client's obligation is subject to a "
   "'contributing cause' standard, except that claims involving FAA violations attributable to "
   "Northstar Aerial Mapping Corp shall survive for seven (7) years instead.",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: causation-standard + survival-period differentiation, THREE mechanisms in one sentence",
   "A harder compound than S4B-COMP-05/07: causation-standard differentiation for the pair PLUS "
   "a survival-period differentiation attributable to just one party — tests whether multiple "
   "SEPARATE differentiation signals (not just two different mechanisms for two different "
   "parties, but two mechanisms possibly both implicating the same party) still resolve to "
   "escalation.")
_c("F3-CM-07", "compound", "liability", 2,
   "9. Limitation of Liability. Aggregate liability shall not exceed 1 times the annual "
   "warehousing-throughput fees paid. Separately, Client maintains cargo insurance of $2,000,000, "
   "which is unrelated to this Section, and a service-level credit of up to 10% of monthly fees "
   "applies for missed delivery windows under Section 14.",
   {}, "AUTOMATABLE", "ACCEPT",
   "compound distractor stack: insurance + SLA credit, both explicitly non-cap",
   "Two DIFFERENT distractor mechanisms (insurance, SLA credit) in one document, testing that "
   "neither is misassociated as the general cap and that stacking distractors doesn't "
   "artificially trigger review.")
_c("F3-CM-08", "compound", "payment_terms", 2,
   "6. Payment Terms. Client shall pay Vendor within 30 days. Vendor shall self-assess and remit "
   "applicable sales tax with Client bearing no responsibility for such remittance, and Vendor "
   "shall be entitled to apply routine credit memos against Client's future invoices.",
   {"require_tax_responsibility_counterparty": True, "prohibit_set_off": True}, "AUTOMATABLE",
   "MUST_REDLINE (tax-on-us) while credit-memo application correctly does NOT separately trigger set-off",
   "compound: genuine tax-on-us violation + hard-negative credit-memo, must not cross-contaminate",
   "Tests that a genuine violation (tax) and a hard negative (credit memo) in the SAME document "
   "are correctly, independently classified rather than one contaminating the other's result.")
_c("F3-CM-09", "compound", "indemnification", 3,
   "8. Indemnification. Thistlemoor Adventure Racing shall indemnify, defend, and hold harmless "
   "Participant, and Participant shall indemnify, defend, and hold harmless Thistlemoor Adventure "
   "Racing, in each case from third-party claims arising from the indemnifying party's own "
   "negligence, up to a cap of the Race Liability Ceiling, which the parties agree, subject to "
   "annual inflation adjustment, is $100,000.",
   {"contract_side": "sell_side"}, "AUTOMATABLE",
   "ESCALATE or ACCEPT depending on config (fixed-dollar defined-term delegation with interposed clause)",
   "compound: reciprocal structure + interposed-clause fixed-dollar delegation",
   "Tests the interposed-clause defined-term-delegation fix on the indemnification side (never "
   "directly tested there before) combined with a reciprocal structure.")
_c("F3-CM-10", "compound", "liability", 3,
   "9. Limitation of Liability. Grantee's aggregate liability to Grantor shall not exceed the "
   "Conveyance Liability Cap. 'Conveyance Liability Cap' means, for purposes of Section 9, 1 "
   "times the annual royalty payments made, and means, for purposes of Section 30 (Title "
   "Insurance Coordination), 3 times the annual royalty payments made.",
   {"contract_side": "buy_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: unmapped role pair (Grantee/Grantor again) + conflicting defined term",
   "Directly reuses the A6-L-52 unmapped-role-pair vocabulary but adds a conflicting-defined-"
   "term layer on top — two independently-sufficient reasons, tests neither is required alone "
   "for the case to correctly escalate (i.e., even if role-attribution were somehow bypassed, "
   "the conflicting term alone should still catch it).")
_c("F3-CM-11", "compound", "payment_terms", 2,
   "6. Payment Terms. Distributor shall remit payment within 30 days, and the parties agree that "
   "final freight-surcharge terms remain under negotiation and will be formalized in a subsequent "
   "Freight Addendum; no freight surcharge shall be invoiced until such Addendum is executed.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: clean net-days + self-flagged-unresolved freight-surcharge term",
   "The NET-DAYS fact is clean and resolvable (30 days), but a SEPARATE, deferred sub-term "
   "(freight surcharge) is unresolved — tests whether a genuinely-resolvable primary fact "
   "alongside an unresolved secondary fact still correctly escalates overall, rather than the "
   "clean net-days fact masking the deferred one.")
_c("F3-CM-12", "compound", "indemnification", 2,
   "8. Indemnification. Fernbridge Apiary Cooperative shall indemnify, defend, and hold harmless "
   "Distributor, and Distributor shall indemnify, defend, and hold harmless Fernbridge Apiary "
   "Cooperative, in each case from third-party claims arising from the indemnifying party's own "
   "negligence, up to a cap of 1 times the fees paid, and both parties' indemnification "
   "obligations shall additionally require the identical thirty (30) days' prior written notice, "
   "and each party shall bear its own costs of defense.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT",
   "compound near-miss: TWO simultaneous symmetric-control shapes stacked",
   "Stacks two DIFFERENT genuinely-symmetric control shapes (identical notice + symmetric "
   "cost-bearing) in one sentence — must resolve automatically; tests that stacking multiple "
   "clean symmetric signals doesn't accidentally trip a false-positive threshold.")
_c("F3-CM-13", "compound", "liability", 3,
   "9. Limitation of Liability. Aggregate liability shall not exceed 1 times the annual "
   "crop-insurance-adjusted fees paid, it being unclear whether 'crop-insurance-adjusted fees' "
   "includes government subsidy payments received by Grower.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: triple-hyphenated basis modifier + self-flagged basis ambiguity",
   "A three-word hyphenated-chain modifier ('crop-insurance-adjusted') combined with a "
   "self-flagged ambiguity about the SAME basis phrase — tests the basis-modifier extractor's "
   "tolerance limit alongside the ambiguity detector.")
_c("F3-CM-14", "compound", "payment_terms", 3,
   "6. Payment Terms. Rather than each party paying the other in full, the parties shall settle "
   "only the net amount owed between what Reinsurer owes Cedent and what Cedent owes Reinsurer "
   "under this and all related treaties, it being noted that the treaty schedule governing which "
   "treaties are 'related' has not yet been finalized.",
   {"prohibit_set_off": True}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: structural netting (a genuine violation) + self-flagged scope ambiguity",
   "The netting/set-off violation is clearly present (should MUST_REDLINE on its own), but the "
   "SCOPE of which treaties are covered is separately flagged as unresolved — tests whether a "
   "clear policy violation combined with a separate scope ambiguity resolves to the MORE severe "
   "state (still a redline) or whether the ambiguity signal incorrectly downgrades it to mere "
   "review; either MUST_REDLINE or REQUIRES_REVIEW is defensible here, but silent ACCEPT is not.")
_c("F3-CM-15", "compound", "indemnification", 2,
   "8. Indemnification. Windrose Sailing Charter Co. shall indemnify, defend, and hold harmless "
   "Charterer, and Charterer shall indemnify, defend, and hold harmless Windrose Sailing Charter "
   "Co., in each case from third-party claims arising from the indemnifying party's own "
   "negligence, up to a cap of 1 times the annual charter-booking fees paid.",
   {"contract_side": "sell_side"}, "AUTOMATABLE", "ACCEPT",
   "compound (mild): reciprocal + compound-hyphenated basis, both clean",
   "A LOW-adversarial compound (both mechanisms present but both resolve cleanly) — a positive "
   "control confirming that combining mechanisms doesn't itself manufacture a problem when "
   "nothing is actually wrong.")
_c("F3-CM-16", "compound", "liability", 3,
   "9. Limitation of Liability. Consignor's aggregate liability to Consignee shall not exceed 1 "
   "times the annual consignment fees paid, calculated per Section 4, which Section 4 "
   "cross-references Schedule E (not included in this excerpt), it being acknowledged that "
   "Schedule E has not yet been finalized.",
   {"contract_side": "sell_side"}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: unmapped role pair + chained delegation + self-flagged unresolved, THREE mechanisms",
   "The most heavily-stacked compound case in this battery: role attribution, chained "
   "delegation, and self-flagged ambiguity all present in one sentence. Any ONE should be "
   "sufficient for escalation; the real test is whether the combination causes an unexpected "
   "interaction (e.g. an early-return in one check suppressing evaluation of the others in a way "
   "that matters).")
_c("F3-CM-17", "compound", "payment_terms", 2,
   "6. Payment Terms. Client shall pay Vendor within 30 days, and Vendor shall be entitled to "
   "apply any promotional rebate credited to Client's account against Client's next invoice, and "
   "separately, Vendor shall be entitled to net any amount Client independently owes Vendor under "
   "a separate consulting engagement against Client's next invoice.",
   {"prohibit_set_off": True}, "AUTOMATABLE", "MUST_REDLINE",
   "compound: hard-negative promotional rebate + genuine independent-debt netting, must not cancel out",
   "Stacks a hard negative (promotional rebate — should NOT trigger) with a genuine violation "
   "(independent-debt netting — SHOULD trigger) in the same document — tests that the hard "
   "negative doesn't dilute or suppress detection of the real violation stated separately.")
_c("F3-CM-18", "compound", "indemnification", 3,
   "8. Indemnification. Each party shall indemnify the other party from third-party claims "
   "arising from its own negligence, up to a cap of 1 times the fees paid, except that Meadowlark "
   "Dairy Genetics Cooperative (but not any inseminating technician) shall be solely responsible "
   "for defending claims arising from genetic-defect disputes, a fact that does not affect either "
   "party's indemnification obligations under this Section for any OTHER claim category.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: genuine exception + partially-scoped self-negation phrase",
   "Same adversarial shape as F3-I-18 (a genuine exception followed by a QUALIFIED self-negation "
   "that doesn't actually negate the exception itself, only clarifies its scope) — a second "
   "instance to confirm the finding isn't a one-off.")
_c("F3-CM-19", "compound", "liability", 2,
   "9. Limitation of Liability. Aggregate liability shall not exceed 1 times the annual "
   "membership-tier fees paid. 'Membership-tier fees' means $500,000 and is restated for "
   "convenience in Section 19 as $500,000.",
   {}, "AUTOMATABLE", "ACCEPT",
   "compound (mild): hyphenated basis modifier + restated-identical defined term",
   "Combines a clean hyphenated-modifier basis extraction with a restated-but-identical defined "
   "term (the F3-D-14 near-miss shape) — both should resolve cleanly together.")
_c("F3-CM-20", "compound", "payment_terms", 3,
   "6. Payment Terms. Licensee shall pay royalties within 30 days, calculated per the rate in "
   "Schedule R, which Schedule R itself cross-references the then-current Rate Card (not "
   "included), and 'Net 30' for purposes of Section 6.1 shall mean thirty calendar days, and "
   "'Net 30' for purposes of Section 6.9 shall instead mean thirty business days.",
   {}, "SHOULD_REVIEW", "REQUIRES_REVIEW",
   "compound: chained delegation + conflicting Net-30 definition, payment terms, TWO mechanisms",
   "Stacks the (disclosed-as-untested) payment-terms chained-delegation shape with the "
   "conflicting-Net-30-definition fix in one clause — tests whether the conflicting-definition "
   "fix alone is sufficient to catch this even if chained-delegation detection doesn't exist for "
   "this adapter.")

_FAMILY_MINIMUMS = {
    "liability": 20, "indemnification": 20, "payment_terms": 20,
    "reciprocal_role": 20, "cross_ref_definition_ambiguity": 20, "compound": 20,
}


def _validate():
    from collections import Counter
    counts = Counter(c["family"] for c in CASES)
    for fam, minimum in _FAMILY_MINIMUMS.items():
        assert counts[fam] >= minimum, f"{fam}: {counts[fam]} < {minimum}"
    assert len(CASES) >= 120, f"total {len(CASES)} < 120"
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids)), "duplicate case id"


_validate()
