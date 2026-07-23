"""
FULL MIGRATION — Reviewer 1 (Framework Author) Migration.

Every one of the 117 rules in rules_engine.py, scored against Severity
Framework v1.0 (docs/rules_engine/severity_architecture.md) by a single
reviewer (the framework's author). This is Phase 2 of the architecture
doc's migration (§12), NOT Phase 2+3 combined -- it is explicitly a
single-reviewer pass, not the full §10 workflow, which additionally
requires:
  (a) a second contributor blind-re-scoring each vector from only the
      rule's rationale and clause text, and
  (b) a subject-matter/licensed-attorney sign-off.
Neither (a) nor (b) has happened yet. This file's factor vectors are a
real, defensible, individually-justified first pass -- not a rubber stamp
and not analogy-based classification -- but they are one person's
judgment, not independently validated. Treat every row's `legacy_severity`
comparison as a hypothesis for Phase 3 review, not a final answer.

Scoring discipline followed for all 117 rules:
  - Every factor was read against the rule's own title/rationale/detection
    pattern (anchors/nearby/pattern), never against how a similar-looking
    rule elsewhere in this file was scored. Similar clause types often
    produce similar vectors because the underlying legal facts really are
    similar -- that is a deterministic rubric converging on consistent
    answers, not analogy-based classification (the thing this framework
    replaces). Anywhere a vector was chosen "because it matches a sibling
    rule," that reasoning is stated explicitly in the comment, and it is
    always grounded in *why* the fact pattern is the same, not merely
    "this looks like that."
  - No factor was inflated or deflated to make the computed tier match
    `legacy_severity`. Divergences are frequent, expected, and logged
    honestly in scripts/generate_full_migration_report.py's output
    rather than smoothed over here.
  - Zero-level factors get a short "not implicated" justification to
    satisfy the schema (FactorScore requires non-empty justification on
    every factor, not just non-zero ones) -- these are NOT the
    "justification for every non-zero factor" the task asked for; the
    real, reasoned justifications are on the non-zero factors, commented
    inline in this file for traceability back to the specific clause
    language that drove each score.

Genuine issues surfaced by doing all 117 (not just the 18-rule sample) are
logged in FINDINGS at the bottom of this file, not silently absorbed.
"""

from rules_engine import RuleEngine, Severity
from severity_scoring import Factor, FactorScore, FactorVector, ScoredRule

_engine = RuleEngine()
_LIVE_RULES = {r.rule_id: r for r in _engine.rules}

_NOT_IMPLICATED = "not implicated by this clause's own text"


def _vec(**nonzero_with_reason):
    """Build a full 11-factor vector. Keys are factor names mapped to
    (level, justification) for the factors actually scored non-zero;
    every other factor is filled with level=0 and a boilerplate
    'not implicated' justification (required by the schema, not a real
    per-factor justification -- see module docstring)."""
    scores = {}
    for f in Factor:
        if f.value in nonzero_with_reason:
            level, reason = nonzero_with_reason[f.value]
            scores[f] = FactorScore(level=level, justification=reason)
        else:
            scores[f] = FactorScore(level=0, justification=_NOT_IMPLICATED)
    return FactorVector(scores=scores)


# rule_id -> (clause_category, affected_party_role, vector)
# Grouped by the same batches used during scoring for traceability.
_SCORES = {}


def _add(rule_id, clause_category, party_role, vector):
    _SCORES[rule_id] = (clause_category, party_role, vector)


# ---------------------------------------------------------------------
# Batch 1 -- core indemnity / liability / IP / personal-liability HIGH+
# ---------------------------------------------------------------------

_add("H_INDEM_01", "Indemnification", "Vendor", _vec(
    FB=(3, "Anchors/nearby require 'no limit'/'without limit'/'unlimited'/'not be limited' co-occurring with indemnify -- indemnity as detected is structurally uncapped."),
    REV=(1, "A cash indemnity payout is compensable in principle but not easily clawed back once paid."),
))

_add("H_LOL_01", "LiabilityCap", "Vendor", _vec(
    FB=(3, "Detects liability language explicitly not limited / without limitation / with limitation excluded -- structurally uncapped as drafted."),
    REV=(1, "Ordinary monetary harm, difficult to fully recover after the fact."),
))

_add("H_IP_01", "IPAssignment", "Assignor", _vec(
    AT=(3, "Pattern requires 'assigns/transfers ... all right, title, and interest' -- unconditional, broad transfer with no retained-rights language required by the pattern."),
    REV=(3, "Once assigned, title has moved; recovering it requires a separate repurchase/negotiation, not a remedy under this contract -- structurally irreversible."),
))

_add("H_PERSONAL_01", "PersonalGuaranty", "Individual", _vec(
    PE=(3, "Pattern fires on 'personally'/'guarantee'/'guarantor' near obligation/liability/responsible with no cap-qualifier required -- read as drafted, this detects unqualified personal obligation language."),
    REV=(1, "Personal financial exposure, difficult to unwind once incurred."),
))

_add("H_INDEM_ONEWAY_01", "Indemnification", "ReceivingParty", _vec(
    REV=(1, "Ordinary monetary/legal-cost harm from bearing indemnity obligations alone."),
))
# FINDING: this rule detects ASYMMETRY of an indemnity obligation (only one
# party indemnifies), not magnitude/boundedness -- magnitude is already
# separately covered by H_INDEM_01/H_LOL_01. None of the 11 factors
# measure "is this obligation one-sided" as a standalone fact (UD measures
# discretion over a term, not asymmetric allocation of an existing
# obligation). Scores LOW; see FINDINGS at end of file.

_add("H_IP_WORK_PRODUCT_01", "IPAssignment", "Assignor", _vec(
    AT=(1, "Pattern is scoped to 'work product/deliverables ... owned by/property of' -- textually narrower than H_IP_01's 'all right, title, and interest' sweep; per the AT rubric, transfer 'limited to specifically enumerated, narrow deliverables' is AT=1, not AT=3."),
    REV=(1, "Ownership of a defined deliverable set, once vested, is not automatically irreversible the way a company-wide IP sweep would be."),
))

_add("H_ATTFEE_01", "FeeShifting", "LosingParty", _vec(
    RW=(1, "One-way attorneys'-fee shifting reallocates litigation COST, not access to a forum or adjudicative process itself -- a negotiable procedural convenience, not an elimination of process (per the RW rubric's narrow forum/process-rights scope)."),
    REV=(1, "Legal-cost exposure, ordinarily compensable/negotiable."),
))

_add("H_LOL_CARVEOUT_01", "LiabilityCap", "Vendor", _vec(
    FB=(2, "Detects an EXISTING liability cap with an explicit carve-out excluding indemnity/confidentiality/IP claims from that cap -- textbook match for FB level 2 ('a cap exists elsewhere, but this clause's own carve-out removes it from that cap's coverage')."),
    REV=(1, "The carved-out claim categories become effectively uncapped, but the underlying harm (money owed) is still an ordinary damages fact."),
))

_add("H_ASSIGN_CHANGE_CTRL_01", "AssignmentRestriction", "Company", _vec(
    UD=(2, "Consent-to-assign requirement blocks a transaction (merger/acquisition/reorg) but does not touch price or the existence of THIS agreement -- a single non-existential constraint, matching the UD=2 rubric level."),
    REV=(1, "A blocked/delayed transaction is a real but not structurally irreversible harm -- consent can still be negotiated or litigated."),
))

_add("H_PUBLICITY_01", "PublicityRights", "Mutual", _vec(
    SC=(3, "Detects 'press release'/'public announcement' language -- by the clause's own text this reaches an unbounded public audience, not just the two contracting parties."),
    REV=(2, "Once a press release or public use of name/logo occurs, the disclosure itself cannot be recalled -- partially irreversible."),
))
# FINDING: publicity/brand-control risk isn't cleanly covered by the 11
# factors (it's not a financial, ownership, personal, or forum-rights
# fact) -- SC/REV are the closest fit but under-weight it relative to
# legacy HIGH. See FINDINGS.

_add("H_UNILATERAL_MOD_01", "UnilateralDiscretion", "Vendor", _vec(
    UD=(3, "Pattern's own rationale is 'modify terms, PRICING, or scope' at any time/sole discretion/without consent -- unbounded discretion touching a fundamental economic term, matching UD=3."),
    OC=(2, "Every branch of the pattern is either 'without notice' or silent on notice ('sole discretion', 'at any time') -- no branch requires a stated notice period."),
    REV=(1, "Ordinary contract-terms harm, generally negotiable/curable."),
))

_add("H_CONSEQUENTIAL_01", "DamagesLimitation", "NonWaivingParty", _vec(
    FB=(2, "A one-sided waiver of consequential/indirect/special/punitive damages categorically reduces what the non-waiving party can ever recover for those harm types -- functionally the same structural fact as a cap carve-out (FB=2: a category of recovery is excluded), just phrased as a damages-type exclusion rather than a liability-cap exclusion."),
    REV=(1, "Reduced recovery for a specific damages category; the underlying harm is still an ordinary (if under-compensated) monetary loss."),
))

_add("H_TERM_CONVENIENCE_01", "Termination", "Vendor", _vec(
    UD=(3, "Detects 'may terminate' near 'for convenience'/'without cause'/'for any/no reason'/'sole discretion' -- unbounded discretion touching the existence of the relationship itself."),
    OC=(2, "The pattern also matches on 'at any time' and bare 'sole discretion' with no notice qualifier required -- the detection does not distinguish a properly-noticed exit from an immediate one; scored as the worse case since the rule's own title ('termination for convenience') carries no notice qualifier. FINDING: this rule should be split -- see FINDINGS."),
    REV=(1, "Loss of a commercial relationship, ordinarily a recoverable/renegotiable harm."),
))

_add("H_DATA_TERMINATION_01", "DataRetention", "Vendor", _vec(
    DUR=(2, "Absence of a return/delete obligation on termination means retention continues with no stated end point -- functionally perpetual by omission."),
    REV=(2, "Data retained indefinitely with no deletion right creates compounding exposure (later breach, competitive use) that grows harder to reverse the longer it continues."),
))

_add("H_ASYMMETRIC_LIABILITY_01", "LiabilityCap", "Customer", _vec(
    FB=(3, "From the disadvantaged party's own perspective, THEIR liability is structurally uncapped (the cap in the clause protects only the counterparty) -- matches FB=3 on the exposed party's own exposure."),
    REV=(1, "Ordinary monetary exposure."),
))
# FINDING: legacy elevated this to CRITICAL in the v5.0 pass. Under the
# frozen v1.0 ceiling rules, FB==3 alone floors at HIGH, not CRITICAL --
# CRITICAL requires PE==3, RW==3, CR==2, or FB==3 AND PE==2 specifically.
# Pure asymmetric-but-entity-level exposure, with no personal/rights-
# waiver/criminal fact, does not qualify under the frozen invariant. See
# FINDINGS -- this is part of a systematic pattern, not a one-off.

_add("H_LOL_NO_CARVEOUT_01", "LiabilityCap", "NonCappedParty", _vec(
    FB=(2, "A cap with NO exceptions even for indemnity/gross negligence/willful misconduct/fraud caps the non-capped party's recovery for an unusually broad set of high-severity claim types -- a structural reduction of recoverable damages (FB=2), though a cap still nominally exists (not FB=3's 'no cap referenced anywhere')."),
    REV=(2, "Harm from fraud or gross negligence is generally harder to make whole via ordinary capped damages than a routine breach."),
))
# FINDING: legacy CRITICAL, framework LOW -- another instance of the
# systematic CRITICAL-tier disagreement (see H_ASYMMETRIC_LIABILITY_01
# and FINDINGS). This is the single largest gap between legacy and
# framework of any rule in the ruleset.

_add("H_INDEM_SCOPE_NARROW_01", "Indemnification", "NonIndemnifiedParty", _vec(
    REV=(1, "Narrower indemnification scope leaves some harm types uncovered, but the covered harms are still ordinary compensable damages."),
))
# FINDING: "narrowness of scope" (which harm TYPES are covered) is a
# different fact from "boundedness of amount" (FB) -- no clean factor
# fit; see FINDINGS.

# ---------------------------------------------------------------------
# Batch 2 -- absence-type data/privacy/compliance procedural gaps (MEDIUM)
# ---------------------------------------------------------------------

_add("M_DPA_MISSING_01", "DataProtectionProcedural", "DataProcessor", _vec(
    RS=(2, "GDPR/Data Controller-Processor concepts are named, and the clause's own gap (no DPA execution requirement) omits a substantive compliance obligation under that regime."),
    REV=(1, "A missing formal DPA is a procedural/contractual gap, not itself an active data-protection violation."),
))

_add("M_BAA_MISSING_01", "DataProtectionProcedural", "BusinessAssociate", _vec(
    RS=(2, "HIPAA/PHI are named, and the clause's own gap (no BAA requirement) omits HIPAA's specific breach-notification/safeguard obligations."),
    REV=(1, "Procedural gap, not itself an active HIPAA violation."),
))

_add("M_SUBPROCESSOR_MISSING_01", "DataProtectionProcedural", "Vendor", _vec(
    RS=(1, "Personal-data/GDPR context is present generically but the pattern does not require a specifically-named enforcement-carrying regime for this exact gap."),
    SC=(1, "Subprocessors are a defined-but-open class (unnamed downstream vendors), not the two contracting parties alone."),
    REV=(1, "Lack of visibility into subprocessors is a procedural gap, not itself a realized harm."),
))

_add("M_AUDIT_RIGHTS_CUSTOMER_01", "DataProtectionProcedural", "Customer", _vec(
    RS=(1, "Anchors on 'security measures'/'Data Processor' -- data-protection-adjacent but no specifically named enforcement regime required by the pattern."),
    REV=(1, "No audit right is a visibility gap, not itself a realized breach."),
))

_add("M_DELETION_CERT_MISSING_01", "DataProtectionProcedural", "Vendor", _vec(
    RS=(1, "Data deletion/disposal context, data-protection-adjacent."),
    REV=(1, "Lack of a certification is an evidentiary gap, not itself proof data was retained improperly."),
    DUR=(1, "Without certification, true completion of deletion is unverifiable and open-ended in practice."),
))

_add("M_SLA_REMEDY_EXCLUSIVITY_01", "ServiceCommitment", "Customer", _vec(
    REV=(1, "Undefined remedy exclusivity risks being locked into inadequate credits, but the underlying harm (degraded service) is an ordinary operational/commercial fact."),
))

_add("M_INSURANCE_MINIMUM_MISSING_01", "InsuranceBackstop", "NonInsuredParty", _vec(
    FB=(1, "An insurance requirement with no stated minimum is a weak, but not literally unbounded, financial backstop gap -- it affects the COUNTERPARTY's insurance adequacy, not this party's own uncapped obligation."),
    REV=(1, "A weak insurance backstop is a risk-of-shortfall fact, not itself a realized loss."),
))

_add("M_REG_RESPONSIBILITY_UNALLOCATED_01", "RegulatoryAllocation", "Customer", _vec(
    RS=(2, "Regulatory obligations explicitly named and retained by default 'except to the extent expressly transferred' under an unattached SOW -- a real, named compliance-allocation gap."),
    REV=(1, "Default regulatory retention is a compliance-allocation fact, not itself a violation."),
))

_add("M_DATA_RETURN_CONDITIONAL_01", "DataRetention", "Vendor", _vec(
    DUR=(1, "Return/deletion is conditioned on customer-initiated written instructions with no stated default -- retention continues by inaction, but is not stated as literally perpetual the way H_DATA_TERMINATION_01's gap is."),
    REV=(1, "Retention-by-inaction is a procedural gap, not itself a realized harm."),
))

# ---------------------------------------------------------------------
# Batch 3 -- consumer/creator/worker protection HIGH rules
# ---------------------------------------------------------------------

_add("H_CARD_AUTH_01", "PaymentAuthorization", "Vendor", _vec(
    UD=(2, "Vendor controls WHEN/how future charges occur ('automatically', 'recurring', 'from time to time') -- unilateral discretion over a single term (charge timing), not the existence of the relationship itself."),
    OC=(2, "Pattern explicitly includes 'without further notice or authorization'."),
    REV=(1, "An unexpected charge is an ordinary, disputable/reversible financial harm (chargeback, refund)."),
))
# Note: PE is NOT scored here even though the affected party is often an
# individual consumer -- PE specifically measures a natural person bearing
# an OBLIGATION BEYOND their own (guaranty-style personal liability), not
# an individual paying for their own subscription. That is a different
# fact and PE=0 is the textually correct application of the rubric.

_add("H_CONTENT_LICENSE_01", "ContentLicense", "Platform", _vec(
    DUR=(2, "Perpetual/no-expiration license language."),
    SC=(3, "'Worldwide' and 'sublicensable' -- by the clause's own text, reaches an unbounded onward-distribution class, not just the two contracting parties."),
    REV=(3, "Once broadly distributed/sublicensed, the content's spread cannot be recalled -- structurally irreversible, the same category as H_AI_TRAINING_01's data-ingestion fact."),
))
# FINDING: no title transfer occurs (a license, however broad, is AT=0 by
# the rubric's own text -- 'license/use-right language only, no title
# transfer' -- even an irrevocable worldwide sublicensable one). The real
# concern here (loss of control over one's identity/likeness) is a
# dignitary/privacy-adjacent interest not cleanly covered by the current
# 11 factors. See FINDINGS -- candidate for a v2 factor, not fixed here.

_add("H_WAGE_DEDUCTION_01", "PaymentContingency", "Worker", _vec(
    FB=(3, "Unilateral deduction/offset/withhold/chargeback rights over wages, payouts, and earnings mean the worker's actual payment amount is not bounded or certain -- structurally the same fact pattern as pay-if-paid (payment subject to the paying party's own unilateral determination)."),
    UD=(3, "The paying party's unilateral discretion over deductions touches whether the worker is actually paid the earned amount -- a fundamental economic term, unbounded."),
    REV=(1, "A wrongful deduction is ordinarily disputable/recoverable."),
))

_add("H_CLASSIFICATION_01", "WorkerClassification", "IndividualContractor", _vec(
    PE=(1, "Where the pattern's indemnification branch fires (indemnify tied to employee/employment/tax), the individual may bear downstream costs of a misclassification dispute -- a real but bounded (tied to classification/tax consequences specifically, not an unqualified 'any and all') personal exposure."),
    RS=(2, "Worker classification is squarely a named regulatory/tax-law regime, and the clause creates a substantive compliance-obligation shift onto the individual."),
    REV=(1, "Classification disputes are ordinarily litigable/correctable, if costly."),
))

# ---------------------------------------------------------------------
# Batch 4 -- consumer-protection MEDIUM/LOW
# ---------------------------------------------------------------------

_add("M_REFUND_01", "RemedyElimination", "Consumer", _vec(
    REV=(2, "Money already paid, with no refund mechanism, is a real and largely irreversible loss for that specific payment."),
))

_add("M_CANCEL_FEE_01", "FeeStructure", "Consumer", _vec(
    FB=(1, "A cancellation fee is a real but bounded, stated cost."),
    REV=(1, "Ordinary, recoverable-in-principle financial harm."),
))

_add("M_ACCOUNT_SUSPEND_01", "UnilateralDiscretion", "Platform", _vec(
    UD=(3, "Sole discretion to suspend/disable/deactivate account or service access -- unbounded discretion touching continuation of the individual's practical access to the service, which is what the relationship actually delivers."),
    OC=(2, "Pattern explicitly includes 'without notice' and 'for any reason'."),
    REV=(1, "Suspension is ordinarily reversible (reinstatement, dispute) rather than a structurally permanent loss."),
))
# FINDING: this computes to HIGH (UD==3 and OC==2 ceiling), ABOVE legacy's
# MEDIUM -- an upgrade recommendation per the literal factor definitions
# (loss of practical service access reads as UD=3's 'continuation of the
# relationship itself' under a strict textual application), not a
# downgrade. Flagged for Phase 3 review since it is a larger jump than
# most disagreements in this migration.

_add("M_PRIVACY_SHARING_01", "DataSharing", "DataSubject", _vec(
    RS=(1, "PII/personal-information concepts are present generically; no single specifically-named enforcement-carrying statute is required by the pattern."),
    SC=(3, "'Third parties'/'marketing partners' -- an unbounded/undefined third-party class by the clause's own text."),
    REV=(1, "Sharing already occurred; the specific disclosure cannot be recalled, but this is bounded to information-level (not structurally catastrophic) harm."),
))

_add("M_NONDISPARAGE_01", "SpeechRestriction", "Mutual", _vec(
    REV=(1, "A silenced reviewer/employee loses a diffuse, hard-to-quantify but not existentially severe ability to warn others."),
))
# FINDING: general speech/review restrictions are not a forum/process
# right (RW is intentionally narrow to court/arbitration/jury/class), nor
# financial, ownership, or personal -- another factor-coverage gap.

_add("M_PHOTO_RELEASE_01", "ContentLicense", "Individual", _vec(
    SC=(2, "'Marketing'/'promotional'/'advertising' reach a role-bounded (not fully unbounded) audience -- narrower than H_CONTENT_LICENSE_01's explicit 'worldwide, sublicensable' language."),
    REV=(2, "Once used in marketing materials, use is hard to fully retract."),
))

_add("L_ELECTRONIC_NOTICE_01", "NoticeMechanics", "Mutual", _vec(
    REV=(1, "A missed deadline from a notice technicality is ordinarily curable (grace periods, actual-notice arguments)."),
))

_add("L_COMMUNICATION_CONSENT_01", "MarketingConsent", "Consumer", _vec(
    RS=(1, "TCPA is named in the detection pattern -- a real named regime, though the clause itself is a consent/disclosure mechanism, not a violation."),
    REV=(1, "Unwanted communications are an ordinary, stoppable-by-opt-out harm."),
))

# ---------------------------------------------------------------------
# Batch 5 -- confidentiality / restrictive-covenant family (MEDIUM)
# ---------------------------------------------------------------------

_add("M_CONF_01", "ConfidentialityDuration", "Mutual", _vec(
    DUR=(2, "Pattern requires 'perpetual'/'in perpetuity'/'indefinite'/'no expiration' co-occurring with confidentiality -- textbook DUR=2."),
))

_add("M_RENEW_01", "AutoRenewal", "Mutual", _vec())
# All-zero: the rule's own detection requires 'unless notice'/'prior
# written notice'/'unless terminated' co-occurring with the auto-renewal
# language -- i.e., it only fires on the DISCLOSED, notice-based variant.
# No factor is implicated by a disclosed, mutual, notice-governed renewal.

_add("M_NONCOMP_01", "RestrictiveCovenant", "RestrictedParty", _vec(
    RS=(1, "Non-compete/non-solicit enforceability is doctrinally regime-dependent (state-by-state restraint-of-trade law), named generically here."),
    REV=(1, "A restrictive covenant limits future activity but is ordinarily negotiable/litigable, not structurally irreversible."),
    DUR=(1, "Restrictive covenants are typically time-bounded (even if the bound is long), not perpetual."),
))

_add("M_DEV_RESTRICT_01", "RestrictiveCovenant", "RestrictedParty", _vec(
    RS=(1, "Restraint-of-trade doctrine implicated generically, same family as non-compete."),
    REV=(1, "Limits future product development but is negotiable, not structurally irreversible."),
    DUR=(1, "Typically tied to the confidentiality period, not perpetual."),
))

_add("M_CONF_SCOPE_01", "ConfidentialityScope", "Mutual", _vec(
    REV=(1, "Overbroad scope (missing public-information carve-out) is a drafting-clarity risk, not itself a realized disclosure harm."),
))

_add("M_RESIDUALS_01", "RestrictiveCovenant", "ReceivingParty", _vec(
    REV=(1, "Restricting use of retained general knowledge limits future work, ordinarily negotiable."),
    DUR=(1, "Open-ended in practice (no residuals carve-out means no stated end to the restriction's practical effect)."),
))

_add("M_INJUNCT_01", "RemedyExpansion", "RestrainedParty", _vec(
    REV=(1, "Broad injunctive-relief availability affects speed of remedy, not the ultimate reversibility of the underlying harm."),
))
# FINDING: expanded injunctive-relief rights for one party functionally
# reduce the restrained party's practical ability to contest quickly --
# adjacent to RW's spirit but RW is scoped to the RESTRAINED party's OWN
# waiver of forum rights, not the counterparty's expanded remedy access.
# Coverage gap; see FINDINGS.

_add("M_EQUIT_NOBOND_01", "RemedyExpansion", "RestrainedParty", _vec(
    FB=(1, "Absence of a bond requirement removes a standard financial safeguard against a wrongfully-sought injunction -- a real but bounded/moderate financial-protection gap, not an unbounded exposure."),
    REV=(1, "A wrongful injunction without a bond is harder to be made whole for, but is not structurally permanent."),
))

_add("M_AUDIT_01", "AuditRights", "AuditedParty", _vec(
    REV=(1, "Audit access is an operational burden; the pattern itself fires even on reasonable-notice audit language, so the detected fact is generic, not extreme."),
))

_add("M_TERM_NOTICE_01", "NoticeMechanics", "Mutual", _vec(
    REV=(1, "A short (but stated) notice window creates a real risk of missed deadlines, ordinarily manageable with calendaring."),
))
# FINDING: the OC factor is defined as '0: a specific notice period ...
# is stated' -- a short-but-DEFINED window (e.g. 5 days) literally
# satisfies OC's level-0 criterion since a period IS stated, even though
# it's short. OC does not graduate for 'notice present but too short.'
# Scored OC=0 (not scored at all above) per the literal rubric text; see
# FINDINGS -- a real rubric granularity gap.

_add("M_SURVIVAL_SCOPE_01", "ObligationScope", "Mutual", _vec(
    DUR=(2, "Pattern requires broad survival language ('all obligations', 'including but not limited to') -- obligations extending indefinitely/broadly past termination."),
    REV=(1, "Extended post-termination obligations are a compliance burden, not a structurally irreversible harm on their own."),
))

_add("M_WAIVER_DEFENSE_01", "RightsWaiver", "WaivingParty", _vec(
    FB=(3, "'Waives any defenses ... regardless of fault ... without limitation' functionally removes all avenues to limit the waiving party's liability -- structurally uncapped, the same underlying fact pattern as an unlimited-liability clause, just phrased as a defense waiver rather than a cap statement."),
    REV=(1, "Ordinary monetary/legal exposure once the waiver is invoked."),
))
# FINDING: computes HIGH (FB==3 ceiling) vs legacy MEDIUM -- an upgrade
# recommendation. A broad, unqualified defense waiver is functionally
# equivalent to an uncapped-liability clause and legacy under-rated it.

_add("M_ARBITRATION_01", "RightsWaiver", "WaivingParty", _vec(
    RW=(2, "Mandatory/binding arbitration replaces court with a different (not eliminated) adjudicative forum -- RW=2, a neutral alternative process, not a full elimination of adversarial process."),
    REV=(1, "Ordinary dispute-resolution-cost harm."),
))

_add("M_WARRANTY_DISCLAIM_01", "RemedyElimination", "Buyer", _vec(
    FB=(2, "A blanket 'AS IS'/disclaim-all-warranties clause categorically zeroes the buyer's quality-defect remedy -- the same structural fact as a damages-category carve-out (FB=2)."),
    REV=(1, "Reduced remedy for defects, an ordinary (if under-compensated) commercial harm."),
))

_add("M_BREACH_NOTIFY_01", "DataProtectionProcedural", "DataSubject", _vec(
    RS=(2, "Breach-notification obligations are squarely a named data-protection-law concept (state breach-notification statutes, GDPR); the clause's own gap creates a compliance omission."),
    REV=(2, "Delayed knowledge of a breach meaningfully worsens the ability to mitigate resulting harm."),
    SC=(2, "Affects data subjects, a role-bounded (not fully unbounded) class."),
))
# FINDING: legacy raised this to HIGH specifically in the v5.0 pass;
# framework computes LOW via band scoring (RS=2 falls short of the
# RS==3-and-SC==3 ceiling). Consistent with the broader pattern that
# required_section/absence-type findings trend lower under intrinsic
# scoring (Refinement Log #6) -- this is now the fourth rule in this
# migration exhibiting exactly that pattern.

_add("M_INSURANCE_01", "InsuranceBackstop", "NonInsuredParty", _vec(
    FB=(1, "Same structural fact as M_INSURANCE_MINIMUM_MISSING_01: a weak, not unbounded, financial-backstop gap."),
    REV=(1, "Risk-of-shortfall fact, not a realized loss."),
))
# FINDING: near-duplicate of M_INSURANCE_MINIMUM_MISSING_01 -- both detect
# 'no minimum insurance amount stated' with nearly identical rationale.
# Flagged for the duplicate-detection validator (architecture doc §9.3,
# not yet implemented -- see severity_implementation.md §6).

_add("M_FORCE_MAJEURE_01", "RemedyElimination", "NonExcusedParty", _vec(
    FB=(1, "Broad force majeure excuses performance for qualifying events, reducing recourse, but is still bounded to actual triggering events even under a broad definition."),
    REV=(1, "Excused performance is an ordinary commercial-risk-allocation fact."),
))

_add("M_SLA_01", "ServiceCommitment", "Customer", _vec(
    REV=(1, "No SLA commitment means no contractual recourse for downtime -- an operational, not existential, gap."),
))

_add("M_MFN_01", "CommercialTerm", "Vendor", _vec())
# All-zero: a pure pricing-mechanics/commercial term with no personal,
# financial-boundedness, ownership, rights-waiver, or regulatory fact.

_add("L_LATEFEE_01", "FeeStructure", "PayingParty", _vec(
    FB=(1, "A stated percentage rate, however high, is a defined and calculable figure -- bounded by FB's own definition even at a punitive rate."),
    REV=(1, "Ordinary, calculable financial harm."),
))

_add("L_BROADDEF_01", "DefinitionalScope", "Mutual", _vec(
    REV=(1, "Overbroad definitions are a drafting-clarity risk, not a realized harm on their own."),
))

_add("L_GOVLAW_01", "Boilerplate", "Mutual", _vec())

_add("L_COMPLIANCE_01", "RegulatoryCompliance", "CompliantParty", _vec(
    CR=(1, "FCPA/anti-bribery references are compliance-representation language, indirect exposure -- the clause itself doesn't create new criminal exposure beyond the statute's own background application."),
    RS=(2, "FCPA/export-control/sanctions are specifically named regimes."),
    REV=(1, "Ordinary compliance-obligation fact."),
))

_add("L_ESCROW_01", "OperationalContinuity", "Licensee", _vec(
    REV=(1, "Escrow terms are a continuity safeguard mechanism, procedural in nature."),
))

_add("L_SUBCONTRACT_01", "UnilateralDiscretion", "Contractor", _vec(
    UD=(2, "Discretion to subcontract without consent touches WHO performs the work, a single non-existential term, not price or the existence of the agreement."),
    REV=(1, "Quality/security risk from an unknown subcontractor is ordinarily manageable/correctable."),
))

# ---------------------------------------------------------------------
# Batch 6 -- v2.1/v3.0/v4.0 broad-ICP rules (AI, pricing, data, worker, etc)
# ---------------------------------------------------------------------

_add("H_AI_TRAINING_01", "DataUsageRights", "Vendor", _vec(
    RS=(3, "Personal/customer data used for AI/ML training implicates data-protection regimes directly and structurally (no consent/opt-out required by the pattern)."),
    AT=(3, "Training data into a model is an unconditional, broad appropriation of the data for a new purpose with no license-back/opt-out required by the pattern -- functionally an ownership-like taking of the data asset."),
    UD=(2, "Vendor decides unilaterally, but this touches data-use SCOPE, not the existence of the customer relationship itself."),
    REV=(3, "A model that has ingested data during training cannot be made to 'un-learn' it -- a well-established, structurally irreversible technical fact, not a probabilistic estimate."),
    SC=(3, "'Customer data'/'your data'/'user content' reaches the customer's own end users/data subjects, an unbounded class by the clause's own scope."),
))
# FINDING: legacy raised this to CRITICAL specifically in the v5.0 pass.
# Framework computes HIGH (AT==3-and-REV==3 ceiling fires; the frozen
# ceiling rules never reach CRITICAL through AT/REV or RS/SC alone -- only
# PE==3, RW==3, CR==2, or FB==3-and-PE==2 reach CRITICAL). This is the
# single most important disagreement in the entire migration -- see
# FINDINGS for the systemic pattern it belongs to.

_add("H_PRICE_ESCAL_01", "UnilateralDiscretion", "Vendor", _vec(
    UD=(3, "'May increase/adjust ... price/fee/rate/charge' at the vendor's option -- unbounded discretion over a fundamental economic term."),
    FB=(2, "The pattern requires no cap/formula qualifier -- the increase is undermined-if-any-cap-exists, matching FB=2's 'cap exists elsewhere but undermined' or simply absent."),
    REV=(1, "A price increase is an ordinary, renegotiable/terminable commercial harm."),
))

_add("H_DATA_PRIVACY_01", "DataProtectionProcedural", "DataSubject", _vec(
    RS=(3, "Detects personal data/PII processing with literally ZERO privacy-law reference anywhere -- the clearest possible case of structural non-compliance with a named regime (no controller/processor allocation, no security measures, no purpose limitation)."),
    SC=(3, "Pattern requires 'without restriction'/'for any purpose' co-occurring -- by the clause's own text, use/onward-sharing is unconstrained, reaching an effectively unbounded class."),
    REV=(2, "Personal data processed with no protections creates compounding, hard-to-fully-remediate exposure once it occurs."),
))
# FINDING: legacy CRITICAL, framework HIGH (RS==3-and-SC==3 ceiling) --
# same systemic pattern as H_AI_TRAINING_01. The two together account for
# 2 of the 5 rules legacy specifically elevated to CRITICAL in the v5.0
# pass; both land at HIGH, not CRITICAL, under the frozen v1.0 ceilings.
# See FINDINGS.

_add("M_DATA_PORTABILITY_01", "DataRetention", "Customer", _vec(
    REV=(2, "Data trapped in a non-portable format on exit is a real, meaningfully hard-to-reverse loss of usable access."),
))

_add("M_DATA_DELETION_01", "DataRetention", "Vendor", _vec(
    DUR=(2, "No deletion/return obligation on termination -- retention continues indefinitely by omission."),
    REV=(1, "Indefinite retention creates ongoing but not immediately catastrophic exposure."),
))
# FINDING: near-duplicate of H_DATA_TERMINATION_01 (same underlying fact:
# no data return/deletion on termination) at a different legacy severity
# (HIGH vs MEDIUM) and different rule_class (required_section vs
# presence_risk) for what reads as the same clause pattern. Flagged for
# the duplicate-detection validator.

_add("M_CROSS_BORDER_01", "DataProtectionProcedural", "DataSubject", _vec(
    RS=(2, "Cross-border transfer without SCCs/adequacy is a named GDPR-family compliance gap."),
    SC=(1, "Affects the data being transferred, generally still the same defined class of data subjects as the underlying processing."),
    REV=(1, "A compliance gap, not itself a realized harm."),
))

_add("M_RENEWAL_PRICE_01", "UnilateralDiscretion", "Vendor", _vec(
    UD=(2, "Discretion over renewal-term pricing is gated by a predictable future event (the renewal date itself), unlike price-escalation-at-any-time -- a single, timing-bounded economic term, matching UD=2."),
    FB=(2, "'Uncapped fee increases' per the rationale -- no formula/index required."),
    REV=(1, "A renewal price increase is renegotiable/terminable, an ordinary commercial harm."),
))

_add("M_MIN_COMMIT_01", "PaymentObligation", "Buyer", _vec(
    FB=(1, "A minimum-commitment/take-or-pay obligation is a real but bounded, stated financial figure."),
    REV=(1, "An ordinary, calculable financial obligation."),
))

_add("M_BENCHMARKING_01", "RestrictiveCovenant", "RestrictedParty", _vec(
    REV=(1, "Restricted ability to benchmark limits negotiating leverage, an ordinary commercial (not existential) harm."),
))

_add("M_USE_RESTRICT_01", "RestrictiveCovenant", "Licensee", _vec(
    REV=(1, "Narrow permitted-use language creates breach exposure for otherwise-routine activity, ordinarily curable via amendment."),
))

_add("L_EXPORT_CTRL_01", "RegulatoryCompliance", "CompliantParty", _vec(
    RS=(2, "EAR/ITAR are specifically named export-control regimes."),
    REV=(1, "Ordinary compliance-obligation fact."),
))

_add("L_PAYMENT_TERMS_01", "PaymentObligation", "PayingParty", _vec(
    REV=(1, "Short payment windows create cash-flow pressure, an ordinary and manageable commercial fact."),
))

# ---------------------------------------------------------------------
# Batch 7 -- contract-to-cash correctness rules (all v4.0, mostly MEDIUM,
# all required_section/document-consistency facts)
# ---------------------------------------------------------------------

_add("M_PAYMENT_TRIGGER_01", "DocumentConsistency", "Mutual", _vec(
    REV=(1, "An undefined invoicing trigger (TBD) is an administrative/drafting gap, correctable before execution or by amendment."),
))

_add("M_CURRENCY_AMBIGUOUS_01", "DocumentConsistency", "Mutual", _vec(
    REV=(1, "Currency ambiguity is an administrative reconciliation gap."),
))

_add("M_BILLING_FREQUENCY_01", "DocumentConsistency", "Mutual", _vec(
    REV=(1, "Billing-frequency ambiguity is an administrative configuration gap."),
))

_add("M_PRICE_EXHIBIT_MISSING_01", "DocumentConsistency", "Mutual", _vec(
    REV=(1, "A missing pricing exhibit is a document-completeness gap, correctable by attaching the exhibit."),
))

_add("M_EXPENSE_APPROVAL_01", "PaymentObligation", "ReimbursingParty", _vec(
    FB=(1, "Unbounded reimbursable expenses (no cap/pre-approval) create real but typically modest, catchable-in-practice cost exposure."),
    REV=(1, "Ordinary, auditable financial exposure."),
))

_add("M_USAGE_MEASUREMENT_01", "PaymentObligation", "PayingParty", _vec(
    FB=(1, "An undefined usage-measurement method creates billing uncertainty, a real but bounded-in-practice dispute risk."),
    REV=(1, "A billing dispute is ordinarily resolvable."),
))

_add("M_DISCOUNT_EXPIRY_01", "DocumentConsistency", "Mutual", _vec(
    REV=(1, "Ambiguous discount duration is a billing-configuration gap."),
))

_add("M_AUTHORITY_REP_01", "ExecutionDefect", "Mutual", _vec(
    REV=(1, "An execution defect (no stated signatory title) is ordinarily curable via ratification or a corrected signature page."),
))

_add("M_EFFECTIVE_DATE_MISSING_01", "ExecutionDefect", "Mutual", _vec(
    REV=(1, "A blank Effective Date is an administrative execution gap, correctable before/at signing."),
))

_add("M_EXHIBIT_MISSING_01", "DocumentConsistency", "Mutual", _vec(
    REV=(1, "A missing exhibit is a document-completeness gap, correctable by attaching it."),
))

_add("L_COUNTERPARTS_ESIGN_01", "Boilerplate", "Mutual", _vec())

_add("H_PAYMENT_ACCELERATION_01", "PaymentContingency", "PayingParty", _vec(
    FB=(1, "The accelerated amount is 'all remaining fees' -- a calculable, defined figure (the known remaining contract value), not an unbounded one; this is a TIMING risk (immediate lump sum) more than a magnitude risk."),
    OC=(2, "Acceleration triggers automatically upon termination/breach with no separate notice period for the acceleration itself."),
    REV=(1, "A liquidity-timing harm, ordinarily manageable/negotiable."),
))
# FINDING: legacy HIGH, framework LOW -- a defined, calculable acceleration
# amount is intrinsically less severe under strict FB scoring than a
# genuinely unbounded exposure; the real-world severity here is largely a
# function of the specific dollar amount at stake (an extrinsic,
# deal-size-dependent fact §3 excludes on purpose, same category as the
# H_ASSIGN_CHANGE_CTRL_01 tension already documented in the architecture
# doc).

_add("H_POST_TERMINATION_BILLING_01", "PaymentContingency", "PayingParty", _vec(
    FB=(1, "Continued post-termination billing is a calculable, defined-fee-amount fact, not an unbounded one."),
    REV=(1, "Erroneous continued billing is ordinarily disputable/reversible via credit or refund."),
))

_add("M_PREPAID_FEES_REFUND_01", "PaymentContingency", "PayingParty", _vec(
    FB=(1, "Non-refundable prepaid fees are bounded to the stated prepaid amount, a calculable figure."),
    REV=(2, "Money already paid with no refund mechanism is a real, largely irreversible loss for that specific payment."),
))

_add("M_FINAL_INVOICE_01", "DocumentConsistency", "Mutual", _vec(
    REV=(1, "Undefined final-invoice timing is an administrative close-out gap."),
))

_add("M_EARLY_TERMINATION_FEE_01", "FeeStructure", "TerminatingParty", _vec(
    FB=(1, "An early-termination fee is a real but bounded, stated cost."),
    REV=(1, "Ordinary, calculable financial harm."),
))

# ---------------------------------------------------------------------
# Batch 8 -- v6.0 law-firm-expansion rules (lease/loan/employment/
# franchise/M&A/partnership/settlement/construction)
# ---------------------------------------------------------------------

_add("H_LEASE_PERSONAL_GUARANTY_01", "PersonalGuaranty", "Individual", _vec(
    PE=(3, "Same fact pattern and same rubric application as H_PERSONAL_01: 'personally guarantee'/'guarantor' with no cap-qualifier required by the pattern -- read as drafted, unqualified personal obligation for the tenant entity's lease obligations."),
    REV=(1, "Personal financial exposure, difficult to unwind once incurred."),
))
# FINDING: legacy scored this HIGH, while H_PERSONAL_01 (the generic
# version of the identical underlying fact -- unconditional personal
# guaranty) and H_LOAN_GUARANTY_WAIVER_01 were both scored CRITICAL. This
# is a genuine, pre-existing INCONSISTENCY in the legacy ruleset --
# functionally identical fact patterns given different severities purely
# because one is phrased as lease-specific and the others generic/
# loan-specific. The v1.0 framework's PE==3 ceiling applies uniformly
# regardless of practice area and computes CRITICAL here, exposing the
# inconsistency. This is exactly the kind of cross-rule inconsistency the
# framework's monotonicity principle is designed to catch -- see FINDINGS.

_add("H_LEASE_ASSIGN_SUBLET_01", "AssignmentRestriction", "Tenant", _vec(
    UD=(2, "Landlord consent-to-assign/sublet, unconstrained by a reasonableness standard, blocks a sale/downsize but does not end the tenancy itself -- a single non-existential constraint, matching UD=2 (the same level as H_ASSIGN_CHANGE_CTRL_01's structurally identical consent-blocking fact)."),
    REV=(1, "A blocked assignment/sublet is negotiable/litigable, not structurally irreversible."),
))

_add("H_LEASE_HOLDOVER_01", "FeeStructure", "Tenant", _vec(
    FB=(1, "A holdover penalty of a stated multiple (150-200%) is a defined, calculable figure -- bounded by FB's own definition even at a harsh rate, the same structural fact as L_LATEFEE_01's high-but-stated percentage."),
    REV=(1, "A calculable holdover cost, ordinarily manageable/negotiable."),
))

_add("H_LEASE_RELOCATION_01", "UnilateralDiscretion", "Landlord", _vec(
    UD=(2, "Relocation within the landlord's building/complex is the rubric's own canonical UD=2 example ('relocation within the same building') -- a single non-existential term, not the existence of the tenancy itself."),
    REV=(1, "Operational disruption from relocation is negotiable/compensable, not structurally irreversible."),
))
# FINDING (documentation inconsistency discovered during this migration):
# the architecture doc's Refinement Log #2/#4 narrative claims lease
# relocation was one of the motivating examples that "correctly return[s]
# HIGH" after the UD/mutuality fixes. That claim does not hold under the
# doc's OWN factor-level rubric: architecture doc §2 explicitly cites
# "relocation within the same building" as the canonical UD=2 example --
# and UD=2 can never reach the UD==3-gated ceiling rule. Scored here as
# UD=2 (LOW) per the literal, frozen factor definition, not UD=3 (which
# would match the Refinement Log's narrative but contradict the rubric
# text). This is a real inconsistency in the architecture doc itself,
# surfaced only by actually running all 117 rules through the frozen
# rubric rather than re-reading the doc's prose -- recorded as a finding,
# not silently resolved either direction, since the framework is frozen.

_add("M_LEASE_CAM_UNCAPPED_01", "FeeCap", "Tenant", _vec(
    FB=(3, "No cap referenced anywhere for CAM charges -- structurally uncapped, textbook FB=3."),
    UD=(2, "Landlord's sole discretion over CAM amounts, a single non-existential term."),
    REV=(1, "A calculable-in-hindsight but structurally uncapped cost."),
))

_add("M_LEASE_ESCALATION_UNCAPPED_01", "FeeCap", "Tenant", _vec(
    FB=(3, "No stated maximum percentage increase -- structurally uncapped rent escalation, textbook FB=3."),
    REV=(1, "A compounding but ordinary cost-increase fact."),
))

_add("H_LOAN_CONFESSION_JUDGMENT_01", "RightsWaiver", "Borrower", _vec(
    RW=(3, "Confession of judgment/cognovit eliminates any hearing or notice before judgment is entered -- textbook RW=3, elimination of adversarial process entirely."),
    REV=(3, "An entered judgment is the paradigm case of structural irreversibility under the REV rubric."),
))

_add("H_LOAN_GUARANTY_WAIVER_01", "PersonalGuaranty", "Guarantor", _vec(
    PE=(3, "'Absolute and unconditional' guaranty waiving notice/demand/presentment/suretyship defenses -- unqualified personal obligation, textbook PE=3."),
    REV=(1, "Personal financial exposure, difficult to unwind once incurred."),
))

_add("M_LOAN_CROSS_DEFAULT_01", "PaymentContingency", "Borrower", _vec(
    FB=(1, "Cross-default broadens the TRIGGER for default but the resulting obligation (the loan balance) is still a calculable, defined figure."),
    REV=(1, "An accelerated-by-cross-default obligation is an ordinary, calculable financial fact."),
))

_add("M_LOAN_PREPAY_PENALTY_01", "FeeStructure", "Borrower", _vec(
    FB=(1, "A prepayment penalty is a real but bounded, stated cost."),
    REV=(1, "Ordinary, calculable financial harm."),
))

_add("M_LOAN_RATE_DISCRETION_01", "UnilateralDiscretion", "Lender", _vec(
    UD=(2, "Lender discretion over the interest RATE affects the cost of an existing obligation, not whether repayment happens at all -- a single economic term, not existential, matching UD=2."),
    FB=(2, "'Without a defined index, formula, or cap' -- undermined/absent capping mechanism on the rate itself."),
    REV=(1, "An unpredictable rate is an ordinary, renegotiable financial fact."),
))

_add("H_EMPLOY_ATWILL_WAIVER_01", "ImpliedContractFormation", "Employer", _vec(
    DUR=(1, "Promised continued employment tied to 'satisfactory performance' implies an ongoing (though not literally perpetual) commitment beyond pure at-will."),
    REV=(1, "An inadvertent implied-contract claim is litigable/correctable, not structurally irreversible."),
))
# FINDING: this rule flags unintended CONTRACT FORMATION (the employer
# accidentally created job security it didn't intend), which isn't a
# clean fit for any of the 11 factors -- it's not a risk-transfer fact in
# the way the other rules are. Another factor-coverage gap; see FINDINGS.

_add("H_EMPLOY_IP_ASSIGN_OVERBROAD_01", "IPAssignment", "Employee", _vec(
    AT=(3, "Broad 'assigns all inventions' with no own-time carve-out required by the pattern -- unconditional, broad transfer, same structural fact as H_IP_01."),
    REV=(3, "Once assigned, invention ownership has moved; the same structural irreversibility as H_IP_01."),
))

_add("M_EMPLOY_SEVERANCE_RELEASE_01", "RightsWaiver", "Employee", _vec(
    RW=(2, "A broad release attempting to waive statutory claims (EEOC, whistleblower) -- these specific rights are non-waivable by law regardless of the clause's text, so this is an attempted overbroad waiver (RW=2: a significant but not fully forum-eliminating attempt), not RW=3."),
    RS=(1, "EEOC/OWBPA/unemployment-benefit regimes are named generically."),
    REV=(2, "A signed release is hard to unwind once executed."),
))

_add("M_EMPLOY_NONSOLICIT_EMPLOYEE_01", "RestrictiveCovenant", "RestrictedParty", _vec(
    RS=(1, "No-hire covenant enforceability is restraint-of-trade-doctrine-dependent, same family as non-compete."),
    REV=(1, "Restricts future hiring, ordinarily negotiable."),
    DUR=(1, "Typically time-bounded (e.g. 24 months), not perpetual."),
))

_add("H_FRANCHISE_TERMINATION_CAUSE_01", "Termination", "Franchisor", _vec(
    UD=(3, "'Sole discretion'/'without cause'/'immediately upon notice' -- unbounded discretion touching the existence of the franchise relationship itself, the franchisee's core investment."),
    OC=(2, "Pattern explicitly includes 'without an opportunity to cure'."),
    REV=(1, "Loss of the franchise relationship is a severe but ordinarily litigable/compensable harm, not structurally irreversible in the REV sense."),
))

_add("M_FRANCHISE_TERRITORY_01", "OwnershipDilution", "Franchisee", _vec(
    REV=(1, "Diluted territory value is a diffuse commercial harm, ordinarily negotiable at renewal."),
))
# FINDING: absence-type again trending low; territory dilution's real
# severity is deal-value-dependent (extrinsic, excluded by §3).

_add("H_MA_INDEM_BASKET_MISSING_01", "Indemnification", "Seller", _vec(
    FB=(2, "No basket/deductible/threshold means first-dollar indemnification risk on every claim -- a structural reduction of the practical protection a basket would provide, matching FB=2's 'cap exists (implicitly, via the indemnity scope) but undermined by the absence of a floor.'"),
    REV=(1, "First-dollar indemnity exposure is an ordinary, calculable-per-claim financial fact."),
))

_add("M_MA_EARNOUT_DISCRETION_01", "UnilateralDiscretion", "Buyer", _vec(
    UD=(3, "Earn-out metrics/payment determination left entirely to buyer discretion with no objective formula -- unbounded discretion touching whether the seller is ever paid at all, an existential economic term."),
    FB=(2, "No formula stated -- the payment amount/certainty is structurally undermined, matching FB=2."),
    REV=(2, "Once a buyer's discretionary determination is made and disputed, unwinding it is difficult."),
))

_add("M_PARTNERSHIP_DEADLOCK_01", "GovernanceGap", "EquallyHeldOwner", _vec(
    REV=(1, "A frozen company from deadlock is remediable via judicial dissolution, though slow."),
    DUR=(2, "No stated resolution mechanism means paralysis, if it occurs, is open-ended."),
))

_add("M_PARTNERSHIP_CAPITAL_CALL_01", "OwnershipDilution", "DefaultingPartner", _vec(
    AT=(3, "An uncapped dilution penalty is, in substance, a forced transfer of the defaulting partner's equity value to the other partners with no retained-rights/buy-back stated -- unconditional, broad transfer of an ownership interest."),
    UD=(3, "The dilution mechanism operates automatically upon the partner's default with no negotiated ceiling -- unconstrained, touching the existence of that partner's ownership stake."),
    REV=(3, "Dilution, once executed, is not reversible without a separate buy-back transaction -- structurally irreversible."),
))

_add("H_SETTLEMENT_RELEASE_OVERBROAD_01", "RemedyElimination", "Releasor", _vec(
    REV=(3, "A release of claims 'known and unknown' waives future claims the releasor doesn't yet know about -- the paradigm case of structural irreversibility (an executed release, per the REV rubric's own example)."),
))
# FINDING: computes LOW (REV=3 alone is only weight x1 = 3 WAS, no ceiling
# fires since AT is not touched) vs legacy HIGH -- a significant
# divergence. The substantive-remedy-reduction pattern (a broad release,
# like a blanket warranty disclaimer or consequential-damages waiver) is
# structurally similar to several other rules in this migration that also
# scored lower than legacy for the same underlying reason: REV alone, at
# weight x1, cannot carry a clause to HIGH without help from a Tier
# A/B factor, and a pure release-of-claims fact doesn't trigger PE, RW
# (narrowly forum-scoped), FB, RS, or AT. See FINDINGS.

_add("M_SETTLEMENT_LIQUIDATED_DAMAGES_01", "FeeStructure", "BreachingParty", _vec(
    FB=(1, "A stated liquidated-damages amount is a defined, calculable figure."),
    REV=(1, "Ordinary, calculable financial harm."),
))

_add("H_CONSTR_PAY_IF_PAID_01", "PaymentContingency", "Subcontractor", _vec(
    FB=(3, "Payment is entirely contingent on the owner's independent, uncontrollable decision to pay the general contractor -- the subcontractor's payment right is not bounded or certain, textbook FB=3."),
    REV=(2, "Non-payment under a pay-if-paid structure is hard to remedy once the owner-GC payment chain fails."),
))

_add("M_CONSTR_LIEN_WAIVER_01", "RightsWaiver", "Subcontractor", _vec(
    RW=(1, "Waiving a statutory lien remedy is a real but narrow, specific right -- not a full elimination of adversarial process, matching RW=1."),
    FB=(2, "Giving up security before payment is received means the subcontractor's payment right is not certain -- undermined, matching FB=2."),
    REV=(2, "Once a lien is waived, reinstating it is difficult."),
))

_add("M_CONSTR_RETAINAGE_01", "PaymentContingency", "Contractor", _vec(
    FB=(2, "Retainage held with no defined release trigger means a portion of earned payment is uncertain/undermined, matching FB=2."),
    REV=(1, "Withheld retainage is ordinarily recoverable once a trigger is eventually met or negotiated."),
    DUR=(2, "No release trigger means the withholding is open-ended in practice."),
))


# ---------------------------------------------------------------------
# Completeness check + ScoredRule construction
# ---------------------------------------------------------------------

_missing = set(_LIVE_RULES) - set(_SCORES)
_extra = set(_SCORES) - set(_LIVE_RULES)
if _missing:
    raise RuntimeError(f"severity_migration_full.py is missing scores for: {sorted(_missing)}")
if _extra:
    raise RuntimeError(f"severity_migration_full.py has scores for unknown rule_ids: {sorted(_extra)}")

FULL_MIGRATION = []
for rule_id, live_rule in _LIVE_RULES.items():
    clause_category, party_role, vector = _SCORES[rule_id]
    FULL_MIGRATION.append(
        ScoredRule(
            rule_id=rule_id,
            clause_category=clause_category,
            affected_party_role=party_role,
            factor_vector=vector,
            legacy_severity=live_rule.severity,
            rationale=live_rule.rationale,
        )
    )

assert len(FULL_MIGRATION) == 117, f"expected 117 scored rules, got {len(FULL_MIGRATION)}"


# ---------------------------------------------------------------------
# FINDINGS -- issues surfaced by scoring all 117, not silently absorbed.
# None of these are framework changes; the frozen v1.0 rubric was applied
# literally throughout. Where a finding suggests the framework itself
# might benefit from a change, it is recorded as a v2 candidate
# observation, not acted on here.
# ---------------------------------------------------------------------
FINDINGS = """
UPDATE (Framework v1.1.0): the headline finding below (#0) was recorded
under the v1.0 absolute band mode and directly motivated the v1.1
relative-mode default now shipped in severity_scoring.py. It is kept
verbatim as the calibration record, not because it still describes
current behavior -- under the current default, MEDIUM is reached by 40
of 117 rules, not 0. See docs/rules_engine/severity_v1_1_release_notes.md
for the current state and docs/rules_engine/severity_migration_report_full_117_v1_0_absolute_archive.md
for the absolute-mode snapshot this analysis describes.

0. HEADLINE FINDING -- MEDIUM is structurally unreachable via aggregation
   across the real ruleset. 93 of 117 rules (79%) changed tier; 86 of 117
   (74%) downgraded. Of the 94 rules scored via the WAS band path (no
   ceiling fired), the WAS values range from 0 to 12 -- EVERY ONE landed
   in the LOW band (<18). Not a single band-scored rule reached MEDIUM
   (18-35) or HIGH (36+) through aggregation alone anywhere in the actual
   117-rule set; every HIGH/CRITICAL result in this migration came from a
   named ceiling rule, never from the weighted sum. This is the single
   most important number in this migration and should be read before any
   individual row: it means the v1.0 threshold table (architecture doc
   §6.3, "18/36" as ~35%/70% of a ~52-point theoretical max) was
   calibrated against a hand-picked 40-clause stress test biased toward
   clauses deliberately chosen to be severe, not against the real
   distribution of how actual deployed rules score. Two live hypotheses,
   deliberately left both live rather than picked between (framework is
   frozen; this is exactly what architecture doc §12 Phase 3 exists to
   resolve with real attorney review, not a unilateral engineering call):
     (a) legacy severity is systematically over-escalated (plausible --
         it was assigned by analogy with no downward pressure, so
         "worth mentioning at all" tended to become "at least MEDIUM"),
         and the framework's much lower distribution is closer to correct; OR
     (b) the WAS thresholds (18 for MEDIUM, 36 for HIGH) are set too high
         relative to how real single/double-factor commercial clauses
         actually score under the weighted formula, and Tier C's weight-1
         contribution in particular is too small to ever move a
         REV/SC/OC/DUR-only fact out of LOW regardless of how many of
         those factors are present.
   Recommend this be the FIRST item reviewed in Phase 3, before any
   individual rule's disagreement -- if the threshold table needs
   adjustment, that is a single governed change (architecture doc §9)
   that would resolve dozens of the individual disagreements below at
   once, rather than reviewing 86 rows independently.

1. SYSTEMIC: the v1.0 CRITICAL tier is narrower than legacy's. Legacy's
   v5.0 pass elevated 5 rules to CRITICAL: H_ASYMMETRIC_LIABILITY_01,
   H_LOL_NO_CARVEOUT_01, H_PERSONAL_01, H_DATA_PRIVACY_01, H_AI_TRAINING_01.
   Under the frozen v1.0 ceiling rules, CRITICAL is reachable ONLY via
   PE==3, RW==3, CR==2, or FB==3-and-PE==2 (architecture doc §6.1's hard
   invariant). Of the 5: H_PERSONAL_01 still computes CRITICAL (PE==3).
   The other 4 -- H_ASYMMETRIC_LIABILITY_01, H_LOL_NO_CARVEOUT_01,
   H_DATA_PRIVACY_01, H_AI_TRAINING_01 -- all compute HIGH, not CRITICAL,
   because their underlying facts (uncapped-but-entity-level liability,
   overbroad cap carve-outs, regulatory/breadth exposure, irreversible
   data ingestion) don't touch personal liability, a forum-rights waiver,
   or criminal exposure. This is the single largest, most consistent
   disagreement pattern in the migration and merits explicit governance
   discussion: is legacy's broader CRITICAL concept (severe + irreversible,
   regardless of personal/rights/criminal facts) correct, and the frozen
   ceiling rules too narrow? Or is the frozen design's insistence that
   CRITICAL be reserved for personal/rights/criminal facts specifically
   correct, and legacy over-escalated these 4? Recorded as the top
   candidate for Phase 3 attorney review and/or a v2.0 ceiling-rule
   discussion -- NOT resolved here.

2. INCONSISTENCY FOUND IN LEGACY: H_LEASE_PERSONAL_GUARANTY_01 (legacy
   HIGH) and H_PERSONAL_01 / H_LOAN_GUARANTY_WAIVER_01 (legacy CRITICAL)
   detect the same underlying fact -- an unconditional personal guaranty
   with no cap qualifier -- but were scored two different legacy tiers.
   The v1.0 framework computes CRITICAL for all three uniformly via the
   PE==3 ceiling, which is applied without regard to practice area by
   design. This is exactly the kind of pre-existing legacy inconsistency
   the framework's uniform, rule-independent ceiling logic is supposed to
   surface -- a positive validation of the architecture, not a defect in
   it.

3. DOCUMENTATION INCONSISTENCY FOUND IN THE ARCHITECTURE DOC ITSELF:
   H_LEASE_RELOCATION_01 was cited in the architecture doc's Refinement
   Log #2/#4 narrative as an example that "correctly return[s] HIGH" after
   the UD factor and mutuality-gate fixes. That is inconsistent with the
   doc's own §2 factor rubric, which explicitly names "relocation within
   the same building" as the canonical UD=2 example -- and UD=2 can never
   reach the UD==3-gated ceiling. Scored here as UD=2 (LOW) per the
   literal, frozen rubric text, contradicting the Refinement Log's prose
   claim. Recorded as a documentation defect for correction alongside any
   future v1.x doc maintenance, not resolved by picking whichever answer
   matches the narrative.

4. RECURRING FACTOR-COVERAGE GAPS (rules that don't cleanly map onto any
   of the 11 factors, each scored conservatively and landing LOW as a
   result): H_INDEM_ONEWAY_01 (asymmetry of an obligation, distinct from
   its magnitude), H_PUBLICITY_01 (brand/reputational control),
   H_CONTENT_LICENSE_01 (loss of control over personal identity/likeness
   -- a license, not a title transfer, so AT=0 by definition),
   H_EMPLOY_ATWILL_WAIVER_01 (unintended contract formation),
   M_NONDISPARAGE_01 (speech restriction, not a forum/process right),
   M_INJUNCT_01 (expanded remedy access for the counterparty, not a
   waiver by the restrained party), H_SETTLEMENT_RELEASE_OVERBROAD_01 and
   several substantive-remedy-reduction rules (M_REFUND_01,
   M_WARRANTY_DISCLAIM_01, H_CONSEQUENTIAL_01, H_LOL_NO_CARVEOUT_01) where
   REV alone (weight x1) cannot carry a clause to HIGH and no other factor
   is cleanly implicated. None of these were patched by inflating a
   factor to "make the math work" -- each is flagged inline above with
   its specific reasoning. Worth a dedicated v2-candidates discussion on
   whether a "substantive remedy reduction" factor, distinct from RW's
   narrow forum-rights scope, belongs in a future version.

5. RUBRIC GRANULARITY GAP: M_TERM_NOTICE_01 revealed that OC's definition
   ("0: a specific notice period ... is stated") does not graduate for a
   notice period that is stated but very short (e.g. 5 days) -- it scores
   identically to a fully adequate notice period. A future version might
   want an intermediate OC level for "notice stated but below a
   commercially reasonable minimum," but that reintroduces exactly the
   kind of judgment-call ambiguity the framework was built to eliminate,
   so this is flagged as a genuine tension, not an obvious fix.

6. LIKELY DUPLICATE RULE PAIRS (flagged for the not-yet-implemented
   duplicate-detection validator, architecture doc §9.3):
   M_INSURANCE_01 / M_INSURANCE_MINIMUM_MISSING_01 (near-identical
   rationale and detection); H_DATA_TERMINATION_01 / M_DATA_DELETION_01
   (same underlying fact -- no data return/deletion on termination -- at
   different legacy severities and rule_class).

7. UPGRADE RECOMMENDATIONS (framework computes HIGHER than legacy, not
   just lower -- listed explicitly so the report isn't read as "the
   framework only downgrades"): M_LEASE_CAM_UNCAPPED_01 (MEDIUM->HIGH),
   M_LEASE_ESCALATION_UNCAPPED_01 (MEDIUM->HIGH),
   M_PARTNERSHIP_CAPITAL_CALL_01 (MEDIUM->HIGH),
   M_MA_EARNOUT_DISCRETION_01 (MEDIUM->HIGH), M_WAIVER_DEFENSE_01
   (MEDIUM->HIGH), M_ACCOUNT_SUSPEND_01 (MEDIUM->HIGH),
   H_LEASE_PERSONAL_GUARANTY_01 (HIGH->CRITICAL, see finding #2).

None of the above were "fixed" in this file -- the frozen rubric was
applied as written in every case, and the resulting disagreement was
recorded rather than smoothed over, per the explicit instruction not to
optimize for matching legacy severity.
"""
