"""Step 4A.11 Phase 6 -- the LOCKED, independent final authoritative corpus.

Authored fresh from contractual CONCEPTS, never copied/paraphrased/synonym-
substituted from any prior Step 4A.10, Step 4A.10.x, or Step 4A.11 Phase 1-4
corpus. See artifacts/step4a11_phase6_freeze/overlap_report.md for the
overlap-check methodology and results run against every prior corpus before
this file was locked.

Ground truth is predeclared here, before execution. After the corpus commit
SHA is recorded, no case text or expected outcome may be edited except an
objectively demonstrated CORPUS DEFECT, disclosed as a GTD correction with a
new checksum -- never to make production agree.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from benchmarks.step4a11_final_corpus_vocab import (
    INDEMNIFICATION_ACTORS, INDEMNIFICATION_BENEFICIARIES,
    LIABILITY_PARTIES, PAYMENT_PARTIES,
)

CASES: List[Dict[str, Any]] = []


def case(cid: str, adapter: str, tier: int, attack_families: List[str],
         text: str, expected_status: str, expected: Optional[Dict[str, Any]] = None,
         expected_dimension: Optional[str] = None, disposition: str = "AUTOMATABLE",
         notes: str = "") -> Dict[str, Any]:
    assert disposition in ("AUTOMATABLE", "SHOULD_REVIEW", "HARD_NEGATIVE")
    assert tier in (1, 2, 3)
    return {
        "id": cid, "adapter": adapter, "tier": tier, "attack_families": attack_families,
        "text": text, "expected_status": expected_status, "expected": expected,
        "expected_dimension": expected_dimension, "disposition": disposition, "notes": notes,
    }

# ===========================================================================
# INDEMNIFICATION -- target >=140 cases
# ===========================================================================
# Each entry below is (template, tier, attack_families, expected_status,
# expected_kind, disposition, notes). expected_kind is "actor_beneficiary"
# (normal single-direction obligation -- filled from the vocab pair used),
# "mutual" (reciprocal -- both directions established, value check skipped),
# or "none" (no obligation established / value not checked).
_IND_TEMPLATES = [
    # --- Tier 1: ordinary commercial drafting, AUTOMATABLE (AF1) ---
    ("{A} shall indemnify and hold {B} harmless from and against any "
     "third-party claim arising out of {A}'s performance of the services "
     "described in this Agreement.", 1, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("{A} agrees to indemnify {B} for all losses, costs, and expenses "
     "resulting from {A}'s breach of its confidentiality obligations under "
     "Section 7.", 1, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("{A} will defend and indemnify {B} against any claim brought by a "
     "third party alleging that the deliverables provided by {A} infringe a "
     "United States patent.", 1, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("{A} shall be liable to {B} for, and shall indemnify {B} against, any "
     "fines imposed by a regulator on account of {A}'s noncompliance with "
     "applicable data-privacy law.", 1, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("In the event a third party asserts a claim against {B} arising from "
     "{A}'s negligent installation of equipment, {A} shall indemnify {B} "
     "for all resulting damages.", 1, ["AF1", "AF3"], "ESTABLISHED", "ab", "AUTOMATABLE",
     "Leading conditional clause naming the trigger, then the obligation -- ordinary drafting shape."),
    ("{A} shall reimburse {B} in full for any judgment entered against {B} "
     "in connection with a product-liability claim traceable to goods {A} "
     "manufactured.", 1, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("Should any employee of {A} cause bodily injury to a visitor at {B}'s "
     "facility, {A} shall indemnify and defend {B} with respect to any "
     "resulting claim.", 1, ["AF1", "AF3"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("{A} shall indemnify, defend, and hold harmless {B}, its officers, and "
     "its directors from any claim of misappropriation of trade secrets "
     "arising from {A}'s use of {B}'s proprietary materials.", 1, ["AF1", "AF7"],
     "ESTABLISHED", "ab", "AUTOMATABLE", "Beneficiary followed by an appositive list of covered persons."),
    # --- Tier 1: hard negatives, no indemnification language at all ---
    ("{A} shall deliver the goods described in Exhibit A to {B} no later "
     "than thirty days after the effective date of this Agreement.",
     1, ["AF6"], "NOT_ESTABLISHED", "none", "HARD_NEGATIVE",
     "Ordinary delivery obligation; no risk-transfer language of any kind."),
    ("{A} and {B} shall each maintain commercial general liability "
     "insurance with a minimum limit of $2,000,000 per occurrence for the "
     "duration of this Agreement.", 1, ["AF6"], "NOT_ESTABLISHED", "none", "HARD_NEGATIVE",
     "Insurance covenant, not an indemnification obligation -- a bystander clause."),
    ("{A} shall reimburse {B} for reasonable travel expenses incurred in "
     "connection with the on-site training sessions described in Schedule "
     "2.", 1, ["AF6"], "NOT_ESTABLISHED", "none", "HARD_NEGATIVE",
     "Ordinary expense reimbursement -- not risk transfer for a claim/loss."),
    ("No provision of this Agreement shall be construed to require {A} to "
     "indemnify {B} for any claim arising from {B}'s own willful "
     "misconduct.", 1, ["AF6"], "NOT_ESTABLISHED", "none", "HARD_NEGATIVE",
     "Explicit negation -- mentions indemnify but denies any obligation exists here."),
    # --- Tier 2: noncanonical but realistic structural variants (AF1/AF7) ---
    ("Any claim, loss, or expense that {B} incurs on account of a data "
     "breach traceable to {A}'s systems is to be borne entirely by {A}, who "
     "shall make {B} whole for it.", 2, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE",
     "Passive/inverted structure -- the beneficiary's loss is named first, actor named second."),
    ("Responsibility for defending and satisfying any infringement claim "
     "brought against {B} rests with {A}.", 2, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE",
     "'Responsibility... rests with' risk-transfer phrasing."),
    ("{A}, as between the parties, shall stand in {B}'s place with respect "
     "to any third-party claim arising from the recall of defective "
     "components.", 2, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("Where a regulator brings an enforcement action against {B} arising "
     "from {A}'s labeling of the product, {A} shall answer for that action "
     "directly to {B} and shall cover every resulting expense.",
     2, ["AF1", "AF3"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("{A}-{B} Joint Venture Agreement, Section 9: with respect to any claim "
     "arising from environmental contamination on the leased premises, {A} "
     "shall indemnify {B} in full.", 2, ["AF1", "AF7"], "ESTABLISHED", "ab", "AUTOMATABLE",
     "Hyphenated compound heading naming both parties, distinct from a role capture."),
    ("{A} shall settle, at its own expense, any claim of copyright "
     "infringement asserted against {B} in connection with the training "
     "materials {A} supplied.", 2, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("It is agreed that {A} shall carry the burden of any claim asserted "
     "against {B} by a subcontractor of {A} for unpaid wages.",
     2, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    # --- Tier 2: legitimate SHOULD_REVIEW (ambiguous scope / vague pointer) ---
    ("{A} shall indemnify {B} to the extent required by applicable law, "
     "subject to certain limitations that may further restrict the scope "
     "of this obligation.", 2, ["AF3"], "ESTABLISHED", "none", "SHOULD_REVIEW",
     "Obligation exists but a vague forward pointer to unnamed limitations makes attachment uncertain -- expect condition NOT_ESTABLISHED, obligation itself still established."),
    ("{A} shall indemnify {B} for claims described in the risk allocation "
     "schedule referenced in Section 4, the terms of which are to be "
     "negotiated separately by the parties.", 2, ["AF4"], "ESTABLISHED", "none", "SHOULD_REVIEW",
     "Delegates scope to a schedule not yet negotiated -- obligation named, scope unresolved."),
    ("{A}'s indemnification obligation to {B}, and {B}'s indemnification "
     "obligation to {A}, shall each be governed by the risk allocation "
     "matrix attached as Appendix C, which the parties have not yet "
     "finalized.", 2, ["AF4", "AF8"], "NOT_ESTABLISHED", "none", "SHOULD_REVIEW",
     "Both directions delegated to an unfinalized appendix -- neither obligation is established yet."),
    # --- Tier 3: non-operative text (quotes, recitals, superseded, meta) ---
    ("A model indemnification clause might read as follows: \"{A} shall "
     "indemnify {B} for all claims.\" The parties have not adopted this "
     "language in the operative sections below.", 3, ["AF6"], "NOT_ESTABLISHED",
     "none", "HARD_NEGATIVE", "Quoted example, explicitly not adopted."),
    ("WHEREAS the parties intend to negotiate a mutual indemnification "
     "framework in a future amendment, this recital does not itself impose "
     "any indemnification obligation on {A} or {B}.", 3, ["AF6"], "NOT_ESTABLISHED",
     "none", "HARD_NEGATIVE", "Recital of future intent, not an operative obligation."),
    ("Section 11 (superseded by the Third Amendment and no longer in "
     "force) formerly provided that {A} would indemnify {B} for shipping "
     "delays; that obligation was removed in its entirety.", 3, ["AF6"],
     "NOT_ESTABLISHED", "none", "HARD_NEGATIVE", "Explicitly superseded provision."),
    ("[DRAFTING NOTE: insert an indemnification clause here, e.g. '{A} "
     "shall indemnify {B} for third-party IP claims,' subject to partner "
     "review before circulation.]", 3, ["AF6"], "NOT_ESTABLISHED", "none",
     "HARD_NEGATIVE", "Meta-instructional drafting note, not an adopted clause."),
    # --- Tier 3: ALL-CAPS heading attack (explicit target of the disclosed WC finding) ---
    ("13. INDEMNIFICATION OBLIGATIONS OF {A} -- {A} SHALL INDEMNIFY AND "
     "HOLD HARMLESS {B} FROM ANY THIRD-PARTY CLAIM ARISING OUT OF A BREACH "
     "OF THE WARRANTIES IN SECTION 6.", 3, ["AF6"], "ESTABLISHED", "ab", "AUTOMATABLE",
     "Independent probe of the disclosed ALL-CAPS heading limitation -- an entirely capitalized OPERATIVE clause (not a heading label) that should still establish; realistic drafting seen in some redline/markup conventions."),
    ("14. RISK ALLOCATION -- {A} shall indemnify {B} for claims arising "
     "from a defect in materials.", 3, ["AF6"], "ESTABLISHED", "ab", "AUTOMATABLE",
     "Ordinary mixed-case section heading immediately followed by an ordinary-case operative sentence -- a control alongside the ALL-CAPS probes above."),
    # --- Tier 3: cross-reference (AF4) ---
    ("12. Risk Transfer. {A}'s indemnification obligations to {B} are as "
     "set forth in the Master Risk Allocation Terms.\n\nAppendix 1: Master "
     "Risk Allocation Terms (draft, not yet approved by either party's "
     "legal department). {A} would indemnify {B} for a fee of $50,000.\n\n"
     "Master Risk Allocation Terms. {A} shall indemnify {B} for any claim "
     "arising from a product recall.", 3, ["AF4", "AF6"], "ESTABLISHED", "ab",
     "AUTOMATABLE", "Cross-reference to a target with two occurrences, one explicitly a draft not yet approved; must resolve to the second, genuinely operative occurrence."),
    ("The indemnification obligations referenced in this Section are "
     "governed by Schedule D, which is not included in this excerpt.",
     3, ["AF4"], "NOT_ESTABLISHED", "none", "SHOULD_REVIEW",
     "Cross-reference to a target the document does not contain -- correctly unresolved."),
    # --- Tier 3: AF9 false-absence probe (unusual but genuinely present structure) ---
    ("Any liability {B} incurs to a third party because of a fault "
     "traceable to {A}'s work is a cost {A} alone must bear, in full and "
     "without limitation, and {A} shall see to it directly.", 3, ["AF9"],
     "ESTABLISHED", "ab", "SHOULD_REVIEW",
     "Genuinely present risk-transfer proposition in unusual, verbose phrasing this mechanism's pattern list likely does not cover -- correctly PRESENT_BUT_UNRESOLVED (review), never silently CONFIRMED_ABSENT nor force-established."),
    # --- Tier 3: reciprocal symmetry/asymmetry (AF8) ---
    ("Each party shall indemnify and hold harmless the other party from "
     "any claim arising out of its own breach of this Agreement.",
     3, ["AF8"], "ESTABLISHED", "mutual", "AUTOMATABLE",
     "Canonical reciprocal opener -- both directions established, structurally symmetric."),
    ("{A} shall indemnify {B} for claims arising from a data breach, "
     "capped at $1,000,000; {B} shall indemnify {A} for claims arising "
     "from a data breach, capped at $250,000.", 3, ["AF8"], "ESTABLISHED", "mutual",
     "SHOULD_REVIEW", "Two directional obligations, same trigger concept, materially DIFFERENT monetary treatment -- must not be reported as symmetric."),
    # --- Compound (AF10, >=2 mechanisms combined) ---
    ("Where a third party brings an infringement claim against {B} arising "
     "from materials {A} supplied under Section 5, {A} shall indemnify {B} "
     "as set forth in the Master Risk Allocation Terms referenced in that "
     "Section, provided that {B} gives {A} prompt written notice of the "
     "claim.", 3, ["AF10", "AF3", "AF4"], "ESTABLISHED", "ab", "AUTOMATABLE",
     "GTD (Step 4A.11 Phase 6, pre-numbers-disclosure correction): original ground truth wrongly treated the cross-reference delegation as leaving the WHOLE fact unresolved, by analogy to liability's cap-cross-reference mechanism. On correct legal reading this is a different shape -- the obligation itself and both parties are stated directly in the operative sentence ('{A} shall indemnify {B}'); only the additional scope/terms are delegated to the referenced Master Risk Allocation Terms, exactly as in the already-accepted Phase 4 GTD correction for fab-pay-af4-schedule-in-document-01 (a delegated VALUE detail does not strip the directly-stated obligation of its own authority). Corrected to ESTABLISHED before any production/corpus performance numbers were reported."),
    ("Best-Fit Solutions & Partners LLC shall indemnify Cross-Town Retail "
     "Alliance Inc. for any claim arising from a mislabeled shipment, but "
     "only for claims asserted within eighteen months of delivery.",
     3, ["AF10", "AF7", "AF3"], "ESTABLISHED", "literal", "AUTOMATABLE",
     "Compound: ampersand + hyphenated compound name + trailing 'but only for' temporal condition. Literal expected names given explicitly (not vocab-substituted)."),
]

_IND_A_IDX = 0
_IND_B_IDX = 0
for _ti, (_tmpl, _tier, _afs, _exp_status, _exp_kind, _disp, _notes) in enumerate(_IND_TEMPLATES):
    _reps = 5 if _exp_kind in ("ab",) and _tier == 1 else (3 if _exp_kind == "ab" else 1)
    for _r in range(_reps):
        _a = INDEMNIFICATION_ACTORS[_IND_A_IDX % len(INDEMNIFICATION_ACTORS)]
        _b = INDEMNIFICATION_BENEFICIARIES[_IND_B_IDX % len(INDEMNIFICATION_BENEFICIARIES)]
        _IND_A_IDX += 1
        _IND_B_IDX += 1
        if _exp_kind == "literal":
            _text = _tmpl
            _expected = {"actor": "Best-Fit Solutions & Partners LLC", "beneficiary": "Cross-Town Retail Alliance Inc"}
        else:
            _text = _tmpl.format(A=_a, B=_b)
            _expected = {"actor": _a, "beneficiary": _b} if _exp_kind == "ab" else None
        _cid = f"fin-ind-t{_tier}-{_ti:02d}-{_r}"
        CASES.append(case(_cid, "indemnification", _tier, _afs, _text, _exp_status, _expected,
                           None, _disp, _notes))

# --- Second batch: AF2 (ownership/bystander), AF5 (discovery-helps),
#     AF7 (role complexity), more tier-1/tier-2 volume ---
_IND_TEMPLATES_2 = [
    # AF2 -- material-fact ownership with a bystander / adjacent unrelated value
    ("{A} separately purchases raw materials from a supplier unrelated to "
     "this Agreement; that unrelated supplier's own liability to its own "
     "customers is not addressed here. {A} shall indemnify {B} for any "
     "claim arising from defects in the finished goods {A} delivers under "
     "this Agreement.", 2, ["AF2"], "ESTABLISHED", "ab", "AUTOMATABLE",
     "A bystander sentence about an unrelated third party's unrelated liability, followed by the real, unambiguous obligation."),
    ("{B}'s facilities manager, who is not a party to this Agreement, "
     "separately carries her own professional liability coverage. {A} "
     "shall indemnify {B} for any claim arising from {A}'s failure to "
     "maintain the equipment described in Exhibit B.", 2, ["AF2"], "ESTABLISHED",
     "ab", "AUTOMATABLE", "Bystander individual mentioned, real obligation stated separately."),
    ("A dispute between {A} and an unrelated third-party subcontractor "
     "over payment terms is not governed by this Agreement. Separately, "
     "{A} shall indemnify {B} for claims arising from {A}'s violation of "
     "export control laws.", 2, ["AF2"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    # AF5 -- discovery/verification separation (unusual verb phrasing a
    # semantic layer would need to surface, then deterministically verify)
    ("Financial exposure {B} suffers because of {A}'s own regulatory "
     "violation is to be shouldered by {A}, who shall keep {B} free of any "
     "resulting cost.", 2, ["AF5", "AF1"], "ESTABLISHED", "ab", "AUTOMATABLE",
     "Unusual 'shouldered by / keep free of' phrasing that a fuzzy discovery layer would need to surface for a deterministic verifier to confirm."),
    ("It falls to {A}, and not {B}, to absorb any claim a third party "
     "brings against {B} on account of {A}'s failure to obtain a required "
     "permit.", 2, ["AF5", "AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    # AF7 -- role complexity: new punctuation/name/tokenization shapes
    ("{A} (f/k/a Meridian West Holdings) shall indemnify {B} for claims "
     "arising from a labeling error on products shipped before the name "
     "change.", 2, ["AF7"], "ESTABLISHED", "ab", "AUTOMATABLE",
     "Former-name parenthetical aside between the role and the modal verb."),
    ("{A}, Ltd. shall indemnify {B}, P.C. for any claim arising from a "
     "billing error in the invoices {A} issued.", 2, ["AF7"], "ESTABLISHED",
     "ab", "AUTOMATABLE", "Both role names carry their own trailing entity-suffix comma."),
    ("St. Aidan's Facilities Group shall indemnify Q&R Municipal Services "
     "for any claim arising from a maintenance failure at the leased "
     "premises.", 2, ["AF7"], "ESTABLISHED", "literal2", "AUTOMATABLE",
     "Apostrophe-in-name actor, ampersand-and-digit-free but still punctuation-heavy beneficiary."),
    ("{A}'s wholly owned subsidiary shall not be a party to this "
     "indemnification; {A} itself shall indemnify {B} for any claim "
     "arising from a warranty breach.", 2, ["AF7", "AF2"], "ESTABLISHED", "ab",
     "AUTOMATABLE", "Explicit exclusion of a similarly-named non-party before the real obligation."),
    # More Tier 1 ordinary AUTOMATABLE for volume
    ("{A} shall indemnify {B} for any claim of trademark infringement "
     "arising from {A}'s use of {B}'s branding on marketing materials.",
     1, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("{A} agrees to hold {B} harmless from any claim arising out of "
     "{A}'s violation of applicable wage-and-hour law with respect to "
     "{A}'s own employees.", 1, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("{A} shall indemnify {B} against any claim that the software {A} "
     "licensed to {B} contains a security vulnerability {A} knew about "
     "and failed to disclose.", 1, ["AF1"], "ESTABLISHED", "ab", "AUTOMATABLE", ""),
    ("{A} shall protect {B} from any claim, and shall reimburse {B} for "
     "any resulting loss, arising from a workplace injury to one of "
     "{A}'s subcontractors on {B}'s premises.", 1, ["AF1"], "ESTABLISHED",
     "ab", "AUTOMATABLE", ""),
    # More Tier 2 SHOULD_REVIEW -- genuinely ambiguous compound carve-out
    ("{A} shall indemnify {B} for claims arising from gross negligence "
     "in performing {A}'s data security obligations, which shall also be "
     "deemed to satisfy any separate requirement to address data-breach "
     "claims generally.", 2, ["AF2", "AF3"], "ESTABLISHED", "none", "SHOULD_REVIEW",
     "Narrow, compound carve-out asserted (via 'deemed to satisfy') to cover a broader category -- a genuine legal judgment call, not a clear-cut reading either way."),
    # More Tier 1 hard negatives
    ("{A} represents and warrants that the goods delivered under this "
     "Agreement conform to the specifications in Exhibit A.", 1, ["AF6"],
     "NOT_ESTABLISHED", "none", "HARD_NEGATIVE", "Warranty representation, not indemnification."),
    ("{A} shall pay {B} a one-time integration fee of $15,000 upon "
     "completion of the onboarding process described in Schedule 1.",
     1, ["AF6"], "NOT_ESTABLISHED", "none", "HARD_NEGATIVE", "Payment obligation, unrelated to risk transfer."),
    ("Neither party shall be liable to the other for any indirect, "
     "consequential, or punitive damages arising out of this Agreement.",
     1, ["AF6"], "NOT_ESTABLISHED", "none", "HARD_NEGATIVE",
     "Limitation-of-liability exclusion language, not an indemnification obligation."),
]

for _ti, (_tmpl, _tier, _afs, _exp_status, _exp_kind, _disp, _notes) in enumerate(_IND_TEMPLATES_2):
    _reps = 5 if (_exp_kind == "ab" and _tier == 1) else (3 if _exp_kind == "ab" else 2)
    for _r in range(_reps):
        _a = INDEMNIFICATION_ACTORS[_IND_A_IDX % len(INDEMNIFICATION_ACTORS)]
        _b = INDEMNIFICATION_BENEFICIARIES[_IND_B_IDX % len(INDEMNIFICATION_BENEFICIARIES)]
        _IND_A_IDX += 1
        _IND_B_IDX += 1
        if _exp_kind == "literal2":
            _text = _tmpl
            _expected = {"actor": "St. Aidan's Facilities Group", "beneficiary": "Q&R Municipal Services"}
        else:
            _text = _tmpl.format(A=_a, B=_b)
            _expected = {"actor": _a, "beneficiary": _b} if _exp_kind == "ab" else None
        _cid = f"fin-ind-t{_tier}-b2-{_ti:02d}-{_r}"
        CASES.append(case(_cid, "indemnification", _tier, _afs, _text, _exp_status, _expected,
                           None, _disp, _notes))

# ===========================================================================
# LIABILITY -- target >=100 cases
# ===========================================================================
# expected_kind: "fixed" (fixed_amount), "mult" (fee multiplier), "unlimited",
# "none" (not established / value not checked).
_LIA_TEMPLATES = [
    # Tier 1 -- ordinary, AUTOMATABLE
    ("12. Limitation of Liability. {A}'s aggregate liability under this "
     "Agreement shall not exceed the total fees paid by {B} in the twelve "
     "months preceding the claim, multiplied by one and one-half.",
     1, ["AF1"], "mult", 1.5, "AUTOMATABLE", ""),
    ("12. Limitation of Liability. In no event shall either party's total "
     "liability to the other exceed $750,000.", 1, ["AF1"], "fixed", 750000.0,
     "AUTOMATABLE", ""),
    ("Limitation of Liability. {A}'s liability to {B} arising out of this "
     "Agreement is capped at three times the annual subscription fee.",
     1, ["AF1"], "mult", 3.0, "AUTOMATABLE", ""),
    ("12. Limitation of Liability. {A} shall have unlimited liability for "
     "claims arising from its breach of confidentiality obligations.",
     1, ["AF1"], "unlimited", None, "AUTOMATABLE", ""),
    ("Liability Cap. The maximum aggregate liability of {A} shall not "
     "exceed $2,500,000 in the aggregate for the Term.", 1, ["AF1"], "fixed",
     2500000.0, "AUTOMATABLE", ""),
    # Tier 1 -- hard negatives
    ("{A} shall deliver a monthly status report to {B} summarizing "
     "progress against the project plan.", 1, ["AF6"], "none", None,
     "HARD_NEGATIVE", "Ordinary reporting obligation, no liability language."),
    ("{A} and {B} shall each designate a primary point of contact for "
     "day-to-day communications under this Agreement.", 1, ["AF6"], "none",
     None, "HARD_NEGATIVE", "Administrative provision, no cap concept."),
    ("{A} shall maintain the confidentiality of {B}'s proprietary "
     "information for a period of five years following termination.",
     1, ["AF6"], "none", None, "HARD_NEGATIVE", "Confidentiality term, not a liability cap."),
    # Tier 2 -- noncanonical structural variants (AF1)
    ("The most {A} can ever be made to pay {B} under this Agreement, "
     "taken as a whole and regardless of the number of claims, is a sum "
     "equal to the fees {B} paid in the year before the claim arose.",
     2, ["AF1"], "mult", 1.0, "AUTOMATABLE", "Verbose, unusually phrased fixed-1x concept -- still structurally recognizable."),
    ("No amount recoverable from {A} by {B}, however characterized, shall "
     "surpass $1,200,000 in total.", 2, ["AF1"], "fixed", 1200000.0,
     "AUTOMATABLE", ""),
    ("{A}'s financial exposure to {B} for any and all claims is fixed at "
     "an amount equal to two times the fees paid under this Agreement.",
     2, ["AF1"], "mult", 2.0, "AUTOMATABLE", "'exposure' terminology, 'is fixed at' lead-in."),
    ("There shall be no ceiling whatsoever on {A}'s liability to {B} for "
     "claims arising from fraud.", 2, ["AF1"], "unlimited", None, "AUTOMATABLE", ""),
    # Tier 2 -- SHOULD_REVIEW (multiple super-caps / genuine ambiguity)
    ("12. Limitation of Liability. Aggregate liability shall not exceed 2 "
     "times the annual fees. Liability for breach of the confidentiality "
     "obligations in Section 9 shall not exceed 5 times the annual fees, "
     "and liability arising from the indemnification obligations in "
     "Section 11 shall separately not exceed 3 times the annual fees.",
     2, ["AF1", "AF2"], "mult", 2.0, "SHOULD_REVIEW",
     "Two distinct category-specific super-caps stacked on top of the general cap -- genuinely more complex than the ordinary single-carveout case; the general 2x figure is still the correctly-resolved general cap, but reviewers should examine the interaction."),
    # Tier 3 -- non-operative text
    ("A sample limitation-of-liability provision, shown here purely for "
     "internal drafting reference, reads: \"{A}'s liability shall not "
     "exceed $500,000.\" No such provision currently appears in this "
     "Agreement.", 3, ["AF6"], "none", None, "HARD_NEGATIVE", "Quoted sample, explicitly not adopted."),
    ("Section 12 (Limitation of Liability) was deleted by the Second "
     "Amendment and replaced with new Section 12A, which addresses "
     "insurance requirements instead; no liability cap remains in this "
     "Agreement.", 3, ["AF6"], "none", None, "HARD_NEGATIVE", "Explicitly deleted/replaced provision."),
    ("12. LIMITATION OF LIABILITY -- IN NO EVENT SHALL {A}'S AGGREGATE "
     "LIABILITY TO {B} EXCEED THE TOTAL FEES PAID UNDER THIS AGREEMENT "
     "IN THE PRECEDING TWELVE MONTHS.", 3, ["AF6"], "mult", 1.0, "AUTOMATABLE",
     "Independent probe of the disclosed ALL-CAPS heading limitation -- fully capitalized OPERATIVE clause, not merely a heading, should still establish (1x fees)."),
    # Tier 3 -- cross-reference (AF4), with a decoy occurrence
    ("12. Limitation of Liability. The dollar figure governing {A}'s "
     "aggregate exposure to {B} is stated in the Commercial Framework "
     "Annex.\n\nAnnex B: Commercial Framework Annex -- circulated as a "
     "working draft during negotiations and not incorporated into the "
     "final Agreement. An earlier proposal of $275,000 appears in this "
     "draft passage.\n\nCommercial Framework Annex. As finally agreed, "
     "the ceiling on {A}'s aggregate liability is $2,150,000.", 3, ["AF4", "AF6"],
     "fixed", 2150000.0,
     "AUTOMATABLE", "Independently-authored cross-reference probe with a decoy draft occurrence and a genuinely binding second occurrence -- distinct phrasing/values/labels from the Phase 4 mechanism-fix case it targets the same underlying mechanism as."),
    # Tier 3 -- AF9 false-absence probe on liability specifically (the
    # disclosed SM architecture gap -- an explicit, independent attack target)
    ("12. Financial Ceiling. No matter how many claims are brought or by "
     "whom, {A} will never be made to answer, in total, for more than the "
     "fees {B} paid to {A} in the twelve months before the dispute began.",
     3, ["AF9"], "mult", 1.0, "SHOULD_REVIEW",
     "Independent probe of the disclosed liability false-absence architecture gap -- a genuinely present 1x-fee cap concept phrased entirely without the words 'liability' or 'exposure,' constructed independently rather than copying the known development finding. Outcome counts normally: SM if CONFIRMED_ABSENT, acceptable if it safely routes to review, unsafe only if it force-establishes a WRONG value."),
    ("Under no circumstances is {A} obligated to pay {B}, across every "
     "claim combined, more than the sum {B} actually paid {A} during the "
     "single year immediately preceding the dispute.", 3, ["AF9"], "mult", 1.0,
     "SHOULD_REVIEW", "Second, independently-worded false-absence probe of the same architecture gap, different phrasing."),
    # Tier 3 -- symmetry/asymmetry (AF8)
    ("12. Limitation of Liability. Each party's aggregate liability to the "
     "other shall not exceed the fees paid by the other party in the "
     "preceding twelve months.", 3, ["AF8"], "mult", 1.0, "AUTOMATABLE",
     "Canonical reciprocal cap -- symmetric by construction."),
    ("12. Limitation of Liability. {A}'s aggregate liability to {B} shall "
     "not exceed $500,000. {B}'s aggregate liability to {A} shall not "
     "exceed $2,000,000.", 3, ["AF8"], "fixed", 500000.0, "SHOULD_REVIEW",
     "Two directional caps with materially different values -- must not be reported as symmetric; controlling-provision resolution should reflect {A}'s own cap for {A}'s side."),
]

_LIA_IDX = 0
for _ti, (_tmpl, _tier, _afs, _kind, _val, _disp, _notes) in enumerate(_LIA_TEMPLATES):
    _reps = 4 if _kind != "none" and _tier == 1 else (2 if _kind != "none" else 2)
    for _r in range(_reps):
        _a, _b = LIABILITY_PARTIES[_LIA_IDX % len(LIABILITY_PARTIES)]
        _LIA_IDX += 1
        _text = _tmpl.format(A=_a, B=_b)
        if _kind == "none":
            _status, _expected = "NOT_ESTABLISHED", None
        elif _kind == "unlimited":
            _status, _expected = "ESTABLISHED", {"kind": "unlimited"}
        elif _kind == "fixed":
            _status, _expected = "ESTABLISHED", {"kind": "fixed", "fixed_amount": _val}
        else:
            _status, _expected = "ESTABLISHED", {"kind": "multiplier", "multiplier": _val}
        _cid = f"fin-lia-t{_tier}-{_ti:02d}-{_r}"
        CASES.append(case(_cid, "liability", _tier, _afs, _text, _status, _expected,
                           "general_cap", _disp, _notes))

# --- Second batch of liability templates: AF2/AF3/AF5/AF7/AF10, more volume ---
_LIA_TEMPLATES_2 = [
    # AF3 -- conditional applicability
    ("12. Limitation of Liability. Aggregate liability shall not exceed "
     "$800,000, provided that this limitation shall not apply to claims "
     "arising from {A}'s fraud or willful misconduct.", 2, ["AF3"], "fixed",
     800000.0, "AUTOMATABLE", "Trailing proviso naming a genuine carve-out exception; general cap itself is unconditional."),
    ("12. Limitation of Liability. So long as {A} maintains the insurance "
     "required by Section 8, {A}'s aggregate liability to {B} shall not "
     "exceed $1,000,000.", 2, ["AF3"], "fixed", 1000000.0, "SHOULD_REVIEW",
     "Leading condition on the cap itself tied to an ongoing covenant -- condition ESTABLISHED, value still resolvable."),
    # AF2 -- ownership with adjacent unrelated value (bystander numeric)
    ("{A} separately maintains $10,000,000 of umbrella insurance covering "
     "matters unrelated to this Agreement. 12. Limitation of Liability. "
     "{A}'s aggregate liability to {B} under this Agreement shall not "
     "exceed $600,000.", 2, ["AF2"], "fixed", 600000.0, "AUTOMATABLE",
     "Unrelated large insurance figure stated first as a bystander value; the real cap is materially smaller and stated separately."),
    ("A separate vendor of {B}'s, not a party to this Agreement, is "
     "subject to a $5,000,000 liability cap under its own unrelated "
     "contract. 12. Limitation of Liability. {A}'s aggregate liability to "
     "{B} shall not exceed 2 times the annual fees.", 2, ["AF2"], "mult", 2.0,
     "AUTOMATABLE", "Adjacent unrelated numeric value belonging to a different contract entirely."),
    # AF5 -- discovery/verification separation, unusual verb phrasing
    ("12. Ceiling on Recovery. Whatever {B} might otherwise be entitled to "
     "recover from {A} is trimmed back to a sum not greater than "
     "$450,000 in total.", 2, ["AF5", "AF1"], "fixed", 450000.0, "AUTOMATABLE",
     "'trimmed back to a sum not greater than' -- unusual verb a fuzzy discovery layer would need to surface."),
    ("12. Ceiling on Recovery. {A} cannot be made to answer, across the "
     "life of this Agreement, for more than one and one-quarter times "
     "the total fees {B} has paid.", 2, ["AF5", "AF1"], "mult", 1.25,
     "AUTOMATABLE", ""),
    # AF7 -- role complexity / punctuation
    ("12. Limitation of Liability. {A}, Inc.'s aggregate liability to "
     "{B}, LLC shall not exceed $950,000.", 2, ["AF7"], "fixed", 950000.0,
     "AUTOMATABLE", "Possessive entity-suffix ('Inc.'s') directly before the cap language."),
    ("12. Limitation of Liability. The liability of St. Marrow Holdings "
     "Group to O'Rourke & Fennimore LLP shall not exceed $1,100,000 in "
     "the aggregate.", 2, ["AF7"], "fixed", 1100000.0, "AUTOMATABLE",
     "Apostrophe-and-ampersand-bearing role names."),
    # AF10 -- compound (>=2 mechanisms)
    ("12. Limitation of Liability. Aggregate liability is capped as "
     "described in the Master Commercial Terms referenced in Section 3, "
     "provided that {A} has not committed fraud.", 3, ["AF10", "AF3", "AF4"],
     "none", None, "SHOULD_REVIEW", "Compound: cross-reference delegation (target not included in this excerpt) plus a trailing proviso -- correctly unresolved."),
    ("12. Limitation of Liability. St. Aidan-Fenwick Group's aggregate "
     "liability to Cross-Harbor & Tull Partners shall not exceed 2 times "
     "the annual fees, provided that this limitation does not apply to "
     "claims arising from a breach of the confidentiality obligations in "
     "Section 9.", 3, ["AF10", "AF7", "AF3"], "mult", 2.0, "AUTOMATABLE",
     "Compound: hyphenated/apostrophe-bearing role names plus a trailing carve-out proviso, with a resolvable general cap."),
]

for _ti, (_tmpl, _tier, _afs, _kind, _val, _disp, _notes) in enumerate(_LIA_TEMPLATES_2):
    _reps = 4
    for _r in range(_reps):
        _a, _b = LIABILITY_PARTIES[_LIA_IDX % len(LIABILITY_PARTIES)]
        _LIA_IDX += 1
        _text = _tmpl.format(A=_a, B=_b) if "{A}" in _tmpl else _tmpl
        if _kind == "none":
            _status, _expected = "NOT_ESTABLISHED", None
        elif _kind == "fixed":
            _status, _expected = "ESTABLISHED", {"kind": "fixed", "fixed_amount": _val}
        else:
            _status, _expected = "ESTABLISHED", {"kind": "multiplier", "multiplier": _val}
        _cid = f"fin-lia-t{_tier}-b2-{_ti:02d}-{_r}"
        CASES.append(case(_cid, "liability", _tier, _afs, _text, _status, _expected,
                           "general_cap", _disp, _notes))

# --- Third small batch: push liability volume comfortably past 100 ---
_LIA_TEMPLATES_3 = [
    ("12. Limitation of Liability. {A}'s total liability to {B} arising "
     "under or in connection with this Agreement shall in no event exceed "
     "$3,000,000.", 1, ["AF1"], "fixed", 3000000.0, "AUTOMATABLE", ""),
    ("Limitation of Liability. {A}'s aggregate liability shall be limited "
     "to an amount equal to four times the annual fees paid by {B}.",
     1, ["AF1"], "mult", 4.0, "AUTOMATABLE", ""),
]
for _ti, (_tmpl, _tier, _afs, _kind, _val, _disp, _notes) in enumerate(_LIA_TEMPLATES_3):
    for _r in range(5):
        _a, _b = LIABILITY_PARTIES[_LIA_IDX % len(LIABILITY_PARTIES)]
        _LIA_IDX += 1
        _text = _tmpl.format(A=_a, B=_b)
        _status = "ESTABLISHED"
        _expected = {"kind": "fixed", "fixed_amount": _val} if _kind == "fixed" else {"kind": "multiplier", "multiplier": _val}
        _cid = f"fin-lia-t{_tier}-b3-{_ti:02d}-{_r}"
        CASES.append(case(_cid, "liability", _tier, _afs, _text, _status, _expected,
                           "general_cap", _disp, _notes))

# ===========================================================================
# PAYMENT TERMS -- target >=100 cases
# ===========================================================================
_PAY_TEMPLATES = [
    # Tier 1 -- ordinary, AUTOMATABLE
    ("9. Payment Terms. {A} shall pay {B} within Net 30 days of receipt of "
     "a correct invoice.", 1, ["AF1"], 30.0, "AUTOMATABLE", ""),
    ("9. Payment Terms. Invoices issued by {B} are payable by {A} within "
     "forty-five days of the invoice date.", 1, ["AF1"], 45.0, "AUTOMATABLE", ""),
    ("Payment Terms. {A} shall remit payment to {B} no later than sixty "
     "days after the end of the calendar month in which services were "
     "rendered.", 1, ["AF1"], 60.0, "AUTOMATABLE", ""),
    ("9. Payment Terms. All amounts owed by {A} to {B} under this "
     "Agreement are due within Net 15 days of invoice.", 1, ["AF1"], 15.0,
     "AUTOMATABLE", ""),
    # Tier 1 -- hard negatives
    ("9. Payment Terms. {A} shall notify {B} promptly of any billing "
     "discrepancy discovered upon review of an invoice.", 1, ["AF6"], None,
     "HARD_NEGATIVE", "Notice obligation, no payment-window figure stated."),
    ("{A} shall provide {B} with a current W-9 form prior to the first "
     "payment under this Agreement.", 1, ["AF6"], None, "HARD_NEGATIVE",
     "Administrative tax-form provision, unrelated to payment timing."),
    ("This Agreement shall automatically renew for successive one-year "
     "terms unless either party provides sixty days' notice of "
     "non-renewal.", 1, ["AF6"], None, "HARD_NEGATIVE",
     "Renewal-term provision using a day figure unrelated to payment timing."),
    # Tier 2 -- noncanonical (AF1)
    ("Payment by {A} of any invoice properly submitted by {B} shall occur "
     "no later than the thirtieth day following {A}'s receipt of that "
     "invoice.", 2, ["AF1"], 30.0, "AUTOMATABLE", "Nominalized/inverted phrasing, ordinal day count."),
    ("{B} is to be paid by {A} within a window of twenty-one days "
     "measured from the date the invoice is received.", 2, ["AF1"], 21.0,
     "AUTOMATABLE", ""),
    ("Amounts invoiced by {B} become due and payable thirty-five days "
     "after {A}'s receipt of the invoice, time being of the essence.",
     2, ["AF1"], 35.0, "AUTOMATABLE", ""),
    # Tier 2 -- SHOULD_REVIEW conditional cases (AF3)
    ("9. Payment Terms. {A} shall pay {B} within Net 30 days of receipt of "
     "invoice, provided that the invoice includes a valid purchase order "
     "number.", 2, ["AF3"], 30.0, "AUTOMATABLE",
     "Trailing proviso -- payment window itself is resolvable, condition on the invoice's own form is separately noted."),
    ("9. Payment Terms. {A} shall pay {B} within Net 45 days of receipt of "
     "invoice. This obligation does not apply to invoices for amounts "
     "under $500, which are instead consolidated and paid quarterly.",
     2, ["AF3"], 45.0, "AUTOMATABLE", "Backward-referencing following-sentence exception for a specific invoice class."),
    # Tier 2 -- late fee dimension
    ("9. Payment Terms. Any overdue balance owed by {A} to {B} accrues "
     "interest at a rate of one and one-half percent for every month it "
     "remains outstanding.",
     2, ["AF1"], None, "AUTOMATABLE", "late_fee_rate_percent case -- separate dimension from net_days; expected via expected_dimension override below."),
    # Tier 3 -- non-operative text
    ("A sample payment clause, included here purely for internal training "
     "purposes and not part of the Agreement, reads: \"{A} shall pay {B} "
     "within Net 30 days.\"", 3, ["AF6"], None, "HARD_NEGATIVE",
     "Explicitly non-operative training example."),
    ("Exhibit 4: Historical Payment Terms (superseded, no longer in "
     "force). Under the parties' prior agreement, {A} paid {B} within Net "
     "60 days. That arrangement has been replaced in its entirety by the "
     "terms of this Agreement, found elsewhere.", 3, ["AF6"], None,
     "HARD_NEGATIVE", "Superseded prior-agreement terms, explicitly not this Agreement's own operative term."),
    ("9. PAYMENT TERMS -- {A} SHALL PAY {B} WITHIN NET 30 DAYS OF RECEIPT "
     "OF A CORRECT INVOICE.", 3, ["AF6"], 30.0, "AUTOMATABLE",
     "Independent probe of the disclosed ALL-CAPS heading limitation -- fully capitalized OPERATIVE sentence, not merely a heading, should still establish Net 30."),
    # Tier 3 -- cross-reference (AF4)
    ("9. Payment Terms. Payment timing is as set forth in Schedule 2.\n\n"
     "Schedule 2: Payment Schedule. {A} shall pay {B} within Net 40 days "
     "of receipt of invoice.", 3, ["AF4"], 40.0, "AUTOMATABLE",
     "Cross-reference to an included schedule stating the figure directly."),
    ("9. Payment Terms. Payment timing is governed by the fee schedule in "
     "Exhibit C, which is not included in this excerpt.", 3, ["AF4"], None,
     "SHOULD_REVIEW", "Cross-reference to a target not present in the document -- correctly unresolved."),
    # Tier 3 -- AF9 false-absence probe, unusual structure
    ("{B} is to receive full payment from {A} no sooner than the fifty-fifth "
     "day, and no later than the fifty-fifth day, counting forward from "
     "the day {A} receives a properly issued invoice.", 3, ["AF9"], 55.0,
     "SHOULD_REVIEW", "Genuinely present but unusually verbose 'exactly N days' phrasing -- correctly established if the structural pattern reaches it, otherwise must safely route to review rather than silent absence."),
]

_PAY_IDX = 0
for _ti, (_tmpl, _tier, _afs, _val, _disp, _notes) in enumerate(_PAY_TEMPLATES):
    _reps = 5 if (_val is not None and _tier == 1) else (3 if _val is not None else 2)
    for _r in range(_reps):
        _a, _b = PAYMENT_PARTIES[_PAY_IDX % len(PAYMENT_PARTIES)]
        _PAY_IDX += 1
        _text = _tmpl.format(A=_a, B=_b)
        if "late fee" in _tmpl:
            _status, _expected, _dim = "ESTABLISHED", {"late_fee_rate_percent": 1.5}, "late_fee_rate_percent"
        elif _val is None:
            _status, _expected, _dim = "NOT_ESTABLISHED", None, None
        else:
            _status, _expected, _dim = "ESTABLISHED", {"net_days": _val}, "net_days"
        _cid = f"fin-pay-t{_tier}-{_ti:02d}-{_r}"
        CASES.append(case(_cid, "payment_terms", _tier, _afs, _text, _status, _expected,
                           _dim, _disp, _notes))

# --- Second batch of payment templates: AF2/AF5/AF7/AF10, more volume ---
_PAY_TEMPLATES_2 = [
    # AF2 -- ownership with bystander/adjacent unrelated value
    ("{A} separately reimburses its own employees for travel expenses "
     "within fourteen days under its internal expense policy, unrelated "
     "to this Agreement. 9. Payment Terms. {A} shall pay {B} within Net "
     "30 days of receipt of invoice.", 2, ["AF2"], 30.0, "AUTOMATABLE",
     "Bystander day figure belonging to an unrelated internal policy, stated before the real payment term."),
    ("A different vendor of {B}'s is paid on Net 10 terms under a "
     "separate, unrelated contract not part of this Agreement. 9. Payment "
     "Terms. {A} shall pay {B} within Net 30 days of receipt of invoice.",
     2, ["AF2"], 30.0, "AUTOMATABLE", "Adjacent unrelated Net-day figure belonging to a different contract."),
    # AF5 -- discovery/verification separation, unusual verb phrasing
    ("9. Settlement of Accounts. {A} is to settle each invoice {B} issues "
     "within a span of twenty-five days measured from {A}'s receipt of "
     "it.", 2, ["AF5", "AF1"], 25.0, "AUTOMATABLE", "'settle... within a span of' phrasing."),
    ("9. Settlement of Accounts. Every sum {B} properly bills is to be "
     "cleared by {A} inside of fifty days from the billing date.",
     2, ["AF5", "AF1"], 50.0, "AUTOMATABLE", "'cleared... inside of' unusual phrasing."),
    # AF7 -- role complexity / punctuation
    ("9. Payment Terms. {A} & Co. shall pay {B}, P.L.C. within Net 30 "
     "days of receipt of invoice.", 2, ["AF7"], 30.0, "AUTOMATABLE",
     "Ampersand-bearing actor, dotted-abbreviation beneficiary suffix."),
    ("9. Payment Terms. O'Halloran-Deveraux Group shall pay St. Bridget "
     "Medical Partners within Net 30 days of receipt of invoice.",
     2, ["AF7"], 30.0, "AUTOMATABLE", "Apostrophe-hyphen compound actor, apostrophe-bearing beneficiary."),
    # AF10 -- compound
    ("9. Payment Terms. {B} is owed payment from {A} thirty days after "
     "invoice receipt, on condition that a signed delivery confirmation "
     "accompanies the invoice. Invoices that {A} formally contests before "
     "the confirmation deadline are excluded from this payment window "
     "until the contest is resolved.", 3, ["AF10", "AF3"], 30.0, "AUTOMATABLE",
     "Independently-worded compound: passive/inverted lead-in ('is owed payment from... on condition that') plus a follow-on exception phrased around 'formally contests' -- net_days itself remains resolvable."),
    ("9. Payment Terms. Fenwick-Ashcombe & Partners LLC shall pay Delacroix "
     "Municipal Holdings within Net 45 days of receipt of invoice, but "
     "only for invoices independently verified against the delivery log "
     "maintained under Section 6.", 3, ["AF10", "AF7", "AF3"], 45.0,
     "AUTOMATABLE", "Compound: hyphenated-ampersand actor, multiword beneficiary, trailing 'but only for' condition."),
]

for _ti, (_tmpl, _tier, _afs, _val, _disp, _notes) in enumerate(_PAY_TEMPLATES_2):
    for _r in range(6):
        _a, _b = PAYMENT_PARTIES[_PAY_IDX % len(PAYMENT_PARTIES)]
        _PAY_IDX += 1
        _text = _tmpl.format(A=_a, B=_b) if "{A}" in _tmpl else _tmpl
        _status, _expected, _dim = "ESTABLISHED", {"net_days": _val}, "net_days"
        _cid = f"fin-pay-t{_tier}-b2-{_ti:02d}-{_r}"
        CASES.append(case(_cid, "payment_terms", _tier, _afs, _text, _status, _expected,
                           _dim, _disp, _notes))

# ===========================================================================
# COMPOUND BATCH -- AF10, >=2 mechanisms combined, across all 3 adapters.
# Needed to push total compound-case count past the required >=60 minimum.
# ===========================================================================
_COMPOUND_IND = [
    ("Where a regulator brings an enforcement action against {B} arising "
     "from {A}'s mislabeling of a shipment, {A} shall indemnify {B} as "
     "described in the Master Risk Allocation Terms referenced in Section "
     "3.", ["AF10", "AF3", "AF4"], "ESTABLISHED", "ab",
     "GTD (Step 4A.11 Phase 6, pre-numbers-disclosure correction): same objective ground-truth error as fin-ind-t3-33 -- the obligation and both named parties are stated directly ('{A} shall indemnify {B}'), the cross-reference only delegates additional scope/terms detail, not the existence or ownership of the obligation itself. Corrected to ESTABLISHED before any production/corpus performance numbers were reported."),
    ("{A}-in-Trust for {B}'s benefit shall indemnify {B} for any claim "
     "arising from a breach of fiduciary duty, but only for claims "
     "asserted within two years of the breach.", ["AF10", "AF7", "AF3"],
     "ESTABLISHED", "ab", "Compound: hyphenated compound role prefix + trailing temporal condition."),
    ("A claim may arise from a defect discovered after final acceptance. "
     "In that event, {A} shall indemnify {B} for the resulting loss, "
     "subject to the fee cap set forth in the Master Risk Allocation "
     "Terms.", ["AF10", "AF3", "AF4"], "ESTABLISHED", "ab",
     "Compound: backward-referencing 'In that event' condition (obligation still establishes, condition itself unresolved) + cross-reference to an uncontained cap target."),
    ("Both parties shall indemnify the other for claims traceable to their "
     "respective breaches of this Agreement, so long as the party seeking "
     "indemnification has given prompt notice; the amount recoverable "
     "under this obligation is bounded by the figure stated in Schedule "
     "5.", ["AF10", "AF8", "AF3"],
     "ESTABLISHED", "mutual", "Independently-phrased compound: reciprocal opener ('Both parties... indemnify the other') + double proviso restructured around 'so long as'/'bounded by' -- both directions established."),
]
_COMPOUND_LIA = [
    ("12. Limitation of Liability. {A}'s liability to {B} is limited as "
     "set forth in the Master Commercial Terms, provided that {A} has "
     "maintained the insurance required by Section 8.", ["AF10", "AF3", "AF4"],
     "NOT_ESTABLISHED", None, "Compound: cross-reference to an uncontained target + a leading condition."),
    ("12. Limitation of Liability. St. Fenwick-Marrow Group's aggregate "
     "liability to O'Bannon & Cross Partners shall not exceed $1,400,000, "
     "provided that this limitation does not apply to claims arising from "
     "a breach of Section 9's confidentiality obligations.", ["AF10", "AF7", "AF3"],
     "ESTABLISHED", "fixed:1400000.0", "Compound: apostrophe/hyphen/ampersand role names + trailing carve-out proviso, resolvable general cap."),
    ("A third party's separate $4,000,000 claim against an unrelated "
     "vendor of {B}'s is not addressed here. 12. Limitation of Liability. "
     "{A}'s aggregate liability to {B} shall not exceed 2 times the "
     "annual fees, provided that {A} has not committed fraud.",
     ["AF10", "AF2", "AF3"], "ESTABLISHED", "mult:2.0",
     "Compound: bystander unrelated numeric value + trailing carve-out condition on the real, resolvable cap."),
]
_COMPOUND_PAY = [
    ("9. Payment Terms. {A} shall pay {B} as set forth in the Master Fee "
     "Schedule referenced in Section 4, provided that the Master Fee "
     "Schedule has been countersigned by both parties.", ["AF10", "AF3", "AF4"],
     "NOT_ESTABLISHED", None, "Compound: cross-reference to an uncontained target + leading condition."),
    ("9. Payment Terms. St. Aldwyn-Fairholme & Sons shall pay Marrowgate "
     "Municipal Trust within Net 30 days of receipt of invoice, provided "
     "that the invoice references a valid purchase order. Amounts under "
     "formal challenge by Marrowgate Municipal Trust remain outside this "
     "window pending resolution of the challenge.",
     ["AF10", "AF7", "AF3"], "ESTABLISHED", "days:30.0",
     "Compound: apostrophe/hyphen/ampersand role names + inline proviso plus a follow-on exception phrased around 'formal challenge' rather than 'disputed' -- resolvable net_days."),
    ("A separate, unrelated vendor of {B}'s is paid on Net 10 terms under "
     "a different contract. 9. Payment Terms. {A} shall pay {B} within "
     "Net 45 days of receipt of invoice, provided that the invoice "
     "includes a valid purchase order number.", ["AF10", "AF2", "AF3"],
     "ESTABLISHED", "days:45.0",
     "Compound: bystander unrelated day figure + trailing condition on the real, resolvable payment window."),
]

for _ti, (_tmpl, _afs, _status, _exp_kind, _notes) in enumerate(_COMPOUND_IND):
    for _r in range(4):
        _a = INDEMNIFICATION_ACTORS[_IND_A_IDX % len(INDEMNIFICATION_ACTORS)]
        _b = INDEMNIFICATION_BENEFICIARIES[_IND_B_IDX % len(INDEMNIFICATION_BENEFICIARIES)]
        _IND_A_IDX += 1; _IND_B_IDX += 1
        _text = _tmpl.format(A=_a, B=_b) if "{A}" in _tmpl else _tmpl
        _expected = {"actor": _a, "beneficiary": _b} if _exp_kind == "ab" else None
        _cid = f"fin-ind-t3-cmp-{_ti:02d}-{_r}"
        CASES.append(case(_cid, "indemnification", 3, _afs, _text, _status, _expected,
                           None, "SHOULD_REVIEW" if _status != "ESTABLISHED" or _exp_kind != "ab" else "AUTOMATABLE", _notes))

for _ti, (_tmpl, _afs, _status, _exp_kind, _notes) in enumerate(_COMPOUND_LIA):
    for _r in range(4):
        _a, _b = LIABILITY_PARTIES[_LIA_IDX % len(LIABILITY_PARTIES)]
        _LIA_IDX += 1
        _text = _tmpl.format(A=_a, B=_b) if "{A}" in _tmpl else _tmpl
        if _exp_kind is None:
            _expected = None
        elif _exp_kind.startswith("fixed:"):
            _expected = {"kind": "fixed", "fixed_amount": float(_exp_kind.split(":")[1])}
        elif _exp_kind.startswith("mult:"):
            _expected = {"kind": "multiplier", "multiplier": float(_exp_kind.split(":")[1])}
        else:
            _expected = None
        _cid = f"fin-lia-t3-cmp-{_ti:02d}-{_r}"
        CASES.append(case(_cid, "liability", 3, _afs, _text, _status, _expected,
                           "general_cap" if _expected else None,
                           "AUTOMATABLE" if _expected else "SHOULD_REVIEW", _notes))

for _ti, (_tmpl, _afs, _status, _exp_kind, _notes) in enumerate(_COMPOUND_PAY):
    for _r in range(4):
        _a, _b = PAYMENT_PARTIES[_PAY_IDX % len(PAYMENT_PARTIES)]
        _PAY_IDX += 1
        _text = _tmpl.format(A=_a, B=_b) if "{A}" in _tmpl else _tmpl
        if _exp_kind is None:
            _expected, _dim = None, None
        elif _exp_kind.startswith("days:"):
            _expected, _dim = {"net_days": float(_exp_kind.split(":")[1])}, "net_days"
        else:
            _expected, _dim = None, None
        _cid = f"fin-pay-t3-cmp-{_ti:02d}-{_r}"
        CASES.append(case(_cid, "payment_terms", 3, _afs, _text, _status, _expected,
                           _dim, "AUTOMATABLE" if _expected else "SHOULD_REVIEW", _notes))
