# Triage Rule Reference — v3.0.0

Complete list of all 64 rules in the deterministic rule engine (22H / 32M / 10L).  
Rule IDs follow the format `{SEVERITY}_{CATEGORY}_{NUMBER}` where severity is H (High), M (Medium), or L (Low).

---

## HIGH Severity — 22 rules

High-severity findings set the Rule Coverage badge to **FAIL** and push the overall contract risk to **HIGH**.

| Rule ID | Display Name | What it detects | Negotiation angle |
|---|---|---|---|
| `H_INDEM_01` | Indemnification | Uncapped or unlimited indemnification obligations | Cap indemnity to fees paid in the prior 12 months; mirror any exceptions |
| `H_LOL_01` | Liability | Liability cap that is absent, excluded, or weakened | Establish a mutual cap (typically 12 months of fees); limit carve-outs |
| `H_IP_01` | Intellectual Property | Broad IP assignment transferring all right, title, and interest | Limit to specific deliverables; retain ownership of pre-existing IP |
| `H_PERSONAL_01` | Personal Liability | Personal guarantees or individual-level obligations | Remove or limit to corporate entity; add carve-out for good-faith acts |
| `H_INDEM_ONEWAY_01` | One-Way Indemnification | Indemnification that flows only from one party | Require mutual indemnification or remove the one-sided obligation |
| `H_IP_WORK_PRODUCT_01` | Work Product IP | Work product language transferring IP ownership | Add explicit carve-out for pre-existing IP; limit assignment to contracted deliverables |
| `H_ATTFEE_01` | Attorneys Fees | One-way fee-shifting for attorneys' fees or legal costs | Make bilateral, or remove; ensure prevailing-party standard applies mutually |
| `H_LOL_CARVEOUT_01` | Liability Carveouts | Liability cap with broad carve-outs (IP, indemnity, confidentiality) that negate the cap | Narrow carve-outs; add sub-limits for carved-out categories |
| `H_ASSIGN_CHANGE_CTRL_01` | Assignment / Change of Control | Assignment prohibited upon merger, acquisition, or change of control | Allow assignment to acquirers; limit consent right to reasonable grounds |
| `H_PUBLICITY_01` | Publicity | Unilateral right to issue press releases or use your name/logo without consent | Require prior written consent for all publicity; remove unilateral rights |
| `H_UNILATERAL_MOD_01` | Unilateral Modification | Right to modify terms, pricing, or scope at any time without consent | Require mutual written amendment; add notice + opt-out rights |
| `H_CONSEQUENTIAL_01` | Consequential Damages | One-sided exclusion of consequential or indirect damages | Require mutual exclusion or remove the asymmetry |
| `H_TERM_CONVENIENCE_01` | Termination for Convenience | One-party right to terminate for convenience at any time | Make termination for convenience mutual; add wind-down or refund provisions |
| `H_DATA_TERMINATION_01` | Data on Termination | No obligation to return or delete data after termination | Add explicit obligation to return/delete within 30 days; require written confirmation |
| `H_ASYMMETRIC_LIABILITY_01` | Asymmetric Liability | Liability cap that applies only to one party | Make the cap mutual; apply the same ceiling to both parties |
| `H_AI_TRAINING_01` | AI / Model Training | Vendor rights to train AI/ML models on your customer data | Explicitly prohibit use of customer data for model training; require opt-in consent |
| `H_PRICE_ESCAL_01` | Price Escalation | Unilateral right to increase fees or rates without mutual consent | Cap increases (e.g., CPI or 3–5%); require advance notice; add right to terminate if unacceptable |
| `H_DATA_PRIVACY_01` | Data Privacy | Personal data processing without GDPR/CCPA protections, DPA reference, or security obligations | Require a signed DPA; specify processing purpose, sub-processor list, and security standards |
| `H_CARD_AUTH_01` | Automatic Charges | Broad stored-card or automatic future charge authorization | Require clear renewal notice, charge caps, and easy cancellation before future billing |
| `H_CONTENT_LICENSE_01` | Content License | Perpetual/worldwide/sublicensable rights to user content, reviews, photos, or likeness | Limit to necessary operation of the service; remove perpetual and sublicensable rights |
| `H_WAGE_DEDUCTION_01` | Wage / Payout Deductions | Unilateral wage, payout, invoice, chargeback, or offset rights | Require itemized notice, dispute rights, and limits tied to documented amounts |
| `H_CLASSIFICATION_01` | Worker Classification | Independent-contractor terms shifting tax, benefit, or classification risk to the individual | Confirm classification fits the actual relationship; narrow indemnity and tax-shift language |

---

## MEDIUM Severity — 32 rules

Medium-severity findings set the Rule Coverage badge to **WARNING** (unless a HIGH finding already set it to FAIL) and contribute to a **MEDIUM** overall risk when two or more are present.

| Rule ID | Display Name | What it detects | Negotiation angle |
|---|---|---|---|
| `M_CONF_01` | Confidentiality | Perpetual or indefinite confidentiality obligations | Add a defined sunset period (3–5 years); carve out publicly available information |
| `M_RENEW_01` | Auto-Renewal | Auto-renewal with a required notice window to opt out | Extend or remove the notice window; add calendar reminders; negotiate termination right |
| `M_NONCOMP_01` | Non-Compete | Non-compete or non-solicitation restriction | Narrow scope (geography, duration, activity); remove if not commercially necessary |
| `M_DEV_RESTRICT_01` | Dev Restrict | Restriction on developing competing or similar products | Limit to use of disclosed confidential information only; not general knowledge |
| `M_CONF_SCOPE_01` | Confidentiality Scope | Overly broad confidentiality scope without standard carve-outs | Add carve-outs for public domain, independently developed, and legally required disclosures |
| `M_RESIDUALS_01` | Residual Rights | Absence of a residuals clause for general knowledge | Add a residuals clause covering knowledge retained in unaided memory |
| `M_INJUNCT_01` | Injunctive Relief | Broad injunctive or equitable relief language | Limit to clear IP or confidentiality breaches; require showing of irreparable harm |
| `M_EQUIT_NOBOND_01` | Equit Nobond | Equitable relief without bond requirement | Require bond or security posting proportional to claimed harm |
| `M_AUDIT_01` | Audit Rights | Third-party audit or inspection rights over your records | Limit frequency (once per year); require 30-day notice; restrict to relevant records only |
| `M_TERM_NOTICE_01` | Termination Notice | Short or strict termination notice windows | Extend notice period to 60–90 days; add cure period for material breach |
| `M_SURVIVAL_SCOPE_01` | Survival Scope | Overbroad survival of obligations beyond termination | Enumerate specific surviving clauses; remove blanket survival language |
| `M_WAIVER_DEFENSE_01` | Waiver of Defenses | Irrevocable waiver of legal defenses or rights | Remove or limit to specific, named defenses; require mutual application |
| `M_ARBITRATION_01` | Arbitration | Mandatory binding arbitration or class action waiver | Retain right to seek injunctive relief in court; negotiate arbitration venue and rules |
| `M_WARRANTY_DISCLAIM_01` | Warranty Disclaimer | Blanket "AS IS" warranty disclaimer excluding all implied warranties | Retain implied warranties of merchantability and fitness for purpose; add minimum service quality SLA |
| `M_BREACH_NOTIFY_01` | Breach Notification | No obligation to notify of data breach | Require notification within 72 hours of discovery; specify content and escalation path |
| `M_INSURANCE_01` | Insurance | No minimum insurance requirements for the counterparty | Require minimum coverage (e.g., $1M general liability, $2M cyber); add as a condition of agreement |
| `M_FORCE_MAJEURE_01` | Force Majeure | Overly broad force majeure with catch-all language | Enumerate specific events; limit duration; add right to terminate if delay exceeds 30–60 days |
| `M_SLA_01` | Service Levels | No defined service level or uptime commitment | Add SLA with defined uptime %; require service credits for downtime; add escalation rights |
| `M_MFN_01` | Most Favored Nation | MFN or "most favored customer" pricing clause | Remove or limit to same customer segment/volume; add sunset date |
| `M_DATA_PORTABILITY_01` | Data Portability | No data export or portability rights on exit | Add explicit right to export in machine-readable format for 30–90 days post-termination |
| `M_DATA_DELETION_01` | Data Deletion | No obligation to delete or return customer data after termination | Require written confirmation of deletion within 30 days; include sub-processors |
| `M_CROSS_BORDER_01` | Cross-Border Transfers | Cross-border personal data transfer without SCCs or adequacy decision | Add Standard Contractual Clauses (SCCs) or equivalent; specify transfer mechanism |
| `M_RENEWAL_PRICE_01` | Renewal Pricing | Uncapped fee increases at renewal (CPI, inflation, or discretionary) | Cap renewal increases (e.g., lesser of CPI or 5%); require 90-day advance notice |
| `M_MIN_COMMIT_01` | Minimum Commitment | Minimum purchase commitment or take-or-pay obligation | Remove or add minimum usage threshold; negotiate ramp schedule; add force majeure carve-out |
| `M_USE_RESTRICT_01` | Use Restrictions | Narrow permitted use restrictions limiting routine business activities | Broaden license scope; ensure permitted use covers affiliates and contractors |
| `M_REFUND_01` | Refund Policy | No-refund, non-refundable, or all-sales-final terms | Add refund rights for non-delivery, cancellation, defects, or unused prepaid periods |
| `M_CANCEL_FEE_01` | Cancellation Fees | Cancellation fee or strict cancellation notice window | Add reasonable notice, grace periods, and proportional fees |
| `M_ACCOUNT_SUSPEND_01` | Account Suspension | Account/service/access suspension at sole discretion, without notice, or for any reason | Require notice, cure rights, data export access, and limits for urgent security events |
| `M_PRIVACY_SHARING_01` | Privacy Sharing | Broad sale, sharing, rental, or disclosure of personal information | Add opt-out rights, purpose limits, and third-party disclosure transparency |
| `M_NONDISPARAGE_01` | Non-Disparagement | Non-disparagement, gag, or review restriction terms | Preserve truthful reviews, legally protected speech, and good-faith reporting |
| `M_PHOTO_RELEASE_01` | Media Release | Photo, video, voice, name, or likeness release for marketing/publicity | Limit by channel, duration, territory, and consent withdrawal rights |

---

## LOW Severity — 10 rules

Low-severity findings set the Rule Coverage badge to **WARNING** and are factored into overall risk only when combined with other findings.

| Rule ID | Display Name | What it detects | Negotiation angle |
|---|---|---|---|
| `L_LATEFEE_01` | Late Fees | Late fees or high interest rates on overdue payments | Cap interest rate (e.g., prime + 2%); add grace period before fees accrue |
| `L_BROADDEF_01` | Definitions | Broad defined terms that expand obligations beyond intent | Narrow definitions; add carve-outs for non-disclosed information |
| `L_GOVLAW_01` | Governing Law | Specific governing law or exclusive venue selection | Negotiate neutral venue or home jurisdiction; add remote hearing option |
| `L_COMPLIANCE_01` | Compliance | Anti-bribery, FCPA, export control, or sanctions compliance obligations | Confirm compliance program exists; limit certification requirements |
| `L_ESCROW_01` | Escrow | Source code escrow provisions | Review release conditions; confirm escrow agent and update cadence |
| `L_SUBCONTRACT_01` | Subcontracting | Subcontracting rights without requiring your consent | Require prior written consent; limit to approved vendor list; add flow-down obligations |
| `L_EXPORT_CTRL_01` | Export Controls | Export control restrictions (EAR, ITAR, trade compliance) | Confirm internal compliance program covers relevant jurisdictions; add mutual representation |
| `L_PAYMENT_TERMS_01` | Payment Terms | Short payment windows or unfavorable net-day terms | Negotiate net-30 or net-45; add approval workflow to invoice process |
| `L_ELECTRONIC_NOTICE_01` | Electronic Notice | Email, portal, or in-app notices deemed received immediately | Add confirmed delivery methods and keep contact information update process clear |
| `L_COMMUNICATION_CONSENT_01` | Communication Consent | Marketing, SMS, automated call, or promotional communication consent | Require clear opt-out rights and separate transactional from promotional notices |

---

## Rule ID Reference (alphabetical by category)

| Rule ID | Severity | Category display name |
|---|---|---|
| `M_ARBITRATION_01` | MEDIUM | Arbitration |
| `H_ASSIGN_CHANGE_CTRL_01` | HIGH | Assignment / Change of Control |
| `H_ATTFEE_01` | HIGH | Attorneys Fees |
| `M_AUDIT_01` | MEDIUM | Audit Rights |
| `H_ASYMMETRIC_LIABILITY_01` | HIGH | Asymmetric Liability |
| `M_RENEW_01` | MEDIUM | Auto-Renewal |
| `M_BENCHMARKING_01` | MEDIUM | Benchmarking |
| `M_BREACH_NOTIFY_01` | MEDIUM | Breach Notification |
| `M_CONF_01` | MEDIUM | Confidentiality |
| `M_CONF_SCOPE_01` | MEDIUM | Confidentiality Scope |
| `H_CONSEQUENTIAL_01` | HIGH | Consequential Damages |
| `M_CROSS_BORDER_01` | MEDIUM | Cross-Border Transfers |
| `H_DATA_PRIVACY_01` | HIGH | Data Privacy |
| `M_DATA_DELETION_01` | MEDIUM | Data Deletion |
| `H_DATA_TERMINATION_01` | HIGH | Data on Termination |
| `M_DATA_PORTABILITY_01` | MEDIUM | Data Portability |
| `L_BROADDEF_01` | LOW | Definitions |
| `M_DEV_RESTRICT_01` | MEDIUM | Dev Restrict |
| `M_EQUIT_NOBOND_01` | MEDIUM | Equit Nobond |
| `L_ESCROW_01` | LOW | Escrow |
| `L_EXPORT_CTRL_01` | LOW | Export Controls |
| `M_FORCE_MAJEURE_01` | MEDIUM | Force Majeure |
| `L_GOVLAW_01` | LOW | Governing Law |
| `H_INDEM_01` | HIGH | Indemnification |
| `M_INSURANCE_01` | MEDIUM | Insurance |
| `H_IP_01` | HIGH | Intellectual Property |
| `M_INJUNCT_01` | MEDIUM | Injunctive Relief |
| `L_LATEFEE_01` | LOW | Late Fees |
| `H_LOL_01` | HIGH | Liability |
| `H_LOL_CARVEOUT_01` | HIGH | Liability Carveouts |
| `M_MIN_COMMIT_01` | MEDIUM | Minimum Commitment |
| `M_MFN_01` | MEDIUM | Most Favored Nation |
| `M_NONCOMP_01` | MEDIUM | Non-Compete |
| `H_INDEM_ONEWAY_01` | HIGH | One-Way Indemnification |
| `H_PERSONAL_01` | HIGH | Personal Liability |
| `H_PRICE_ESCAL_01` | HIGH | Price Escalation |
| `H_PUBLICITY_01` | HIGH | Publicity |
| `M_RENEWAL_PRICE_01` | MEDIUM | Renewal Pricing |
| `M_RESIDUALS_01` | MEDIUM | Residual Rights |
| `M_SLA_01` | MEDIUM | Service Levels |
| `L_SUBCONTRACT_01` | LOW | Subcontracting |
| `M_SURVIVAL_SCOPE_01` | MEDIUM | Survival Scope |
| `H_TERM_CONVENIENCE_01` | HIGH | Termination for Convenience |
| `M_TERM_NOTICE_01` | MEDIUM | Termination Notice |
| `H_AI_TRAINING_01` | HIGH | AI / Model Training |
| `H_UNILATERAL_MOD_01` | HIGH | Unilateral Modification |
| `M_USE_RESTRICT_01` | MEDIUM | Use Restrictions |
| `M_WAIVER_DEFENSE_01` | MEDIUM | Waiver of Defenses |
| `M_WARRANTY_DISCLAIM_01` | MEDIUM | Warranty Disclaimer |
| `H_IP_WORK_PRODUCT_01` | HIGH | Work Product IP |
| `L_COMPLIANCE_01` | LOW | Compliance |
| `L_PAYMENT_TERMS_01` | LOW | Payment Terms |

| `H_CARD_AUTH_01` | HIGH | Automatic Charges |
| `M_CANCEL_FEE_01` | MEDIUM | Cancellation Fees |
| `H_CLASSIFICATION_01` | HIGH | Worker Classification |
| `L_COMMUNICATION_CONSENT_01` | LOW | Communication Consent |
| `H_CONTENT_LICENSE_01` | HIGH | Content License |
| `L_ELECTRONIC_NOTICE_01` | LOW | Electronic Notice |
| `M_ACCOUNT_SUSPEND_01` | MEDIUM | Account Suspension |
| `M_NONDISPARAGE_01` | MEDIUM | Non-Disparagement |
| `M_PHOTO_RELEASE_01` | MEDIUM | Media Release |
| `M_PRIVACY_SHARING_01` | MEDIUM | Privacy Sharing |
| `M_REFUND_01` | MEDIUM | Refund Policy |
| `H_WAGE_DEDUCTION_01` | HIGH | Wage / Payout Deductions |

---

## Severity → Badge mapping

| Severity | Rule Coverage badge | Overall contract risk contribution |
|---|---|---|
| HIGH finding in category | FAIL | Always raises overall risk to HIGH |
| MEDIUM finding in category | WARNING (unless already FAIL) | Raises overall risk to MEDIUM if ≥ 2 MEDIUM findings present |
| No finding | PASS | No contribution |

---

*Ruleset version: 3.0.0 — released 2026-07-07*  
*Scope: Commercial NDAs, MSAs, SaaS Agreements, Vendor Contracts, Employment/Contractor Agreements, Consumer Terms, Creator/Marketplace Terms, Event/Service Agreements, and Privacy-Adjacent Policies*
