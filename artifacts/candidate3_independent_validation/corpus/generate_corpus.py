#!/usr/bin/env python3
"""Generates the genuinely new, independent Candidate 3 validation corpus.

CONTAMINATION DISCIPLINE: every sentence in every template below was
freshly authored for this corpus. None is copied or paraphrased from the
burned 74-case corpus, the burned 240-case corpus, any adapter unit-test
fixture, any prior repeatability fixture, ip_ownership-080, or any other
previously-used development/regression case. This file was written
without inspecting any Candidate 3 failure log, burned-corpus case text,
or repeatability result file for content ideas -- only the EXPECTED-LABEL
VOCABULARY (YES_OPERATIVE / NO_NOT_OPERATIVE / YES_BUT_CONDITIONAL /
YES_BUT_EXCEPTION / AMBIGUOUS / CROSS_REFERENCE_DEPENDENT /
DEFINITION_DEPENDENT / MISSING_CLAUSE) and the established-signal/grading
methodology from replay_final_gap_closure.py were reused, since that is a
scoring RUBRIC, not corpus content, and reusing a validated grading
methodology on genuinely new content is the correct, sound approach
(rebuilding an equally-audited grading rubric from scratch would not make
the corpus any more independent -- the corpus's cases and texts are what
must be unseen, not the arithmetic used to score them).

Six distinct party-name pairs are used throughout (never "Vendor"/
"Customer" alone, to avoid even superficial resemblance to the most
common burned-corpus party pair) to ensure genuine textual diversity
beyond parameter substitution: (Provider, Recipient), (Contractor,
Client), (Licensor, Licensee), (Supplier, Buyer), (Operator, Subscriber),
(Company, Counterparty).
"""
import json
import hashlib

PARTY_PAIRS = [
    ("Provider", "Recipient"),
    ("Contractor", "Client"),
    ("Licensor", "Licensee"),
    ("Supplier", "Buyer"),
    ("Operator", "Subscriber"),
    ("Company", "Counterparty"),
]

CASES = []
_seq = {"n": 0}


def add(adapter, family, expected, text, policy=None, notes=""):
    _seq["n"] += 1
    CASES.append({
        "id": f"iv-{adapter}-{_seq['n']:04d}",
        "adapter": adapter,
        "family": family,
        "expected": expected,
        "text": text,
        "policy": policy or {},
        "notes": notes,
    })


# ===========================================================================
# 01. limitation_of_liability
# ===========================================================================
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    mult = [2, 3, 1.5, 4, 2.5, 5][i]
    add("limitation_of_liability", "operative",
        "YES_OPERATIVE",
        f"14. Cap on Damages. {p1}'s total liability arising out of this engagement shall not "
        f"exceed {mult} times the fees paid by {p2} during the preceding twelve months.")
    add("limitation_of_liability", "descriptive",
        "NO_NOT_OPERATIVE",
        f"Preamble. Agreements of this type in the {['software','logistics','consulting','marketing','staffing','manufacturing'][i]} "
        f"industry typically include a liability cap, although the parties have not yet settled on specific terms for this engagement.")
    add("limitation_of_liability", "negated",
        "NO_NOT_OPERATIVE",
        f"14. Liability. {p1} shall not be obligated to accept any cap or limitation on its liability under this engagement.")
    add("limitation_of_liability", "conditional",
        "YES_BUT_CONDITIONAL",
        f"14. Cap on Damages. {p1}'s liability shall be capped at {mult} times fees paid, provided that {p2} has given "
        f"written notice of the claim within {[30,45,60,90,15,20][i]} days of discovery.")
    add("limitation_of_liability", "exception",
        "YES_BUT_EXCEPTION",
        f"14. Cap on Damages. {p1}'s aggregate liability shall not exceed {mult} times the annual fees, except that "
        f"this limitation shall not apply to claims arising from {p1}'s fraud or willful misconduct.")
    add("limitation_of_liability", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"14. Cap on Damages. {p1}'s liability under this engagement is capped as set forth in Exhibit "
        f"{['C','D','E','F','G','H'][i]}, attached hereto.")
    add("limitation_of_liability", "definition",
        "DEFINITION_DEPENDENT",
        f"14. Cap on Damages. {p1}'s liability for any Covered Loss shall not exceed the Annual Cap Amount, each as "
        f"defined in this Agreement.")
    add("limitation_of_liability", "ambiguous",
        "AMBIGUOUS",
        f"14. Cap on Damages. {p1}'s liability shall not exceed {mult} times fees paid. Section 22 separately states "
        f"that {p1}'s liability for direct damages shall not exceed the total contract value, without indicating "
        f"which of these two limitations governs.")
    add("limitation_of_liability", "missing",
        "MISSING_CLAUSE",
        f"This Agreement between {p1} and {p2} covers the provision of services described in Exhibit A, "
        f"including delivery timelines and acceptance criteria, but contains no separate discussion of damages.")

# ===========================================================================
# 02. indemnification
# ===========================================================================
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    mult = [1, 2, 3, 1.5, 2.5, 4][i]
    add("indemnification", "operative",
        "YES_OPERATIVE",
        f"9. Indemnification. {p1} shall indemnify, defend, and hold {p2} harmless from third-party claims arising "
        f"out of {p1}'s breach of its obligations under this Agreement.")
    add("indemnification", "descriptive",
        "NO_NOT_OPERATIVE",
        f"Historically, agreements between parties in this sector have included mutual indemnification provisions, "
        f"though such language does not appear elsewhere in this document.")
    add("indemnification", "negated",
        "NO_NOT_OPERATIVE",
        f"9. Indemnification. Neither party shall have any obligation to indemnify the other under this Agreement.")
    add("indemnification", "conditional",
        "YES_BUT_CONDITIONAL",
        f"9. Indemnification. {p1} shall indemnify {p2} against third-party claims, provided that {p2} promptly "
        f"notifies {p1} in writing of any such claim and tenders sole control of its defense.")
    add("indemnification", "exception",
        "YES_BUT_EXCEPTION",
        f"9. Indemnification. {p1} shall indemnify {p2} from third-party claims arising from {p1}'s products, "
        f"except that this obligation shall not apply to claims arising from {p2}'s modification of those products.")
    add("indemnification", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"9. Indemnification. The scope of {p1}'s indemnification obligation to {p2} is as set forth in Schedule "
        f"{['1','2','3','4','5','6'][i]} to this Agreement.")
    add("indemnification", "definition",
        "DEFINITION_DEPENDENT",
        f"9. Indemnification. {p1} shall indemnify {p2} against any Excluded Liability, as that term is defined "
        f"in this Agreement.")
    add("indemnification", "ambiguous",
        "AMBIGUOUS",
        f"9. Indemnification. {p1} shall indemnify {p2} for all third-party claims. Elsewhere, Section 19 states "
        f"that {p1}'s indemnification duty is limited to claims arising from gross negligence only, without "
        f"reconciling the two provisions.")
    add("indemnification", "missing",
        "MISSING_CLAUSE",
        f"This engagement letter between {p1} and {p2} addresses scope of work, fees, and term, but does not "
        f"otherwise discuss responsibility for third-party claims.")

# ===========================================================================
# 03. confidentiality
# ===========================================================================
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    yrs = [2, 3, 5, 1, 4, 3][i]
    add("confidentiality", "operative",
        "YES_OPERATIVE",
        f"7. Confidentiality. Each of {p1} and {p2} shall protect the other's Confidential Information using at "
        f"least a reasonable degree of care, and shall not disclose it to any third party without prior consent.")
    add("confidentiality", "descriptive",
        "NO_NOT_OPERATIVE",
        f"Best practice in commercial contracting generally calls for confidentiality obligations between "
        f"contracting parties, a topic the drafters have flagged for later discussion.")
    add("confidentiality", "negated",
        "NO_NOT_OPERATIVE",
        f"7. Confidentiality. Neither {p1} nor {p2} shall be under any duty of confidentiality with respect to "
        f"information exchanged under this Agreement.")
    add("confidentiality", "conditional",
        "YES_BUT_CONDITIONAL",
        f"7. Confidentiality. {p1} shall keep {p2}'s Confidential Information confidential for {yrs} years, "
        f"provided that {p2} has conspicuously marked such information as confidential at the time of disclosure.")
    add("confidentiality", "exception",
        "YES_BUT_EXCEPTION",
        f"7. Confidentiality. {p1} shall not disclose {p2}'s Confidential Information, except information that "
        f"{p1} is compelled to disclose by a valid court order or governmental subpoena.")
    add("confidentiality", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"7. Confidentiality. The parties' confidentiality obligations to one another are governed by the terms "
        f"of the separate Non-Disclosure Agreement referenced in Recital {['B','C','D','E','F','G'][i]}.")
    add("confidentiality", "definition",
        "DEFINITION_DEPENDENT",
        f"7. Confidentiality. {p1} shall not disclose any Proprietary Materials belonging to {p2}, as that term "
        f"is defined in this Agreement.")
    add("confidentiality", "ambiguous",
        "AMBIGUOUS",
        f"7. Confidentiality. {p1} shall keep {p2}'s information confidential indefinitely. Section 14 separately "
        f"states the confidentiality term expires {yrs} years after termination, without resolving which controls.")
    add("confidentiality", "missing",
        "MISSING_CLAUSE",
        f"This purchase order between {p1} and {p2} specifies quantities, unit prices, and delivery dates, and "
        f"does not otherwise address the treatment of confidential information.")

# ===========================================================================
# 04. payment_terms
# ===========================================================================
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    days = [30, 45, 60, 15, 90, 20][i]
    add("payment_terms", "operative",
        "YES_OPERATIVE",
        f"5. Payment. {p2} shall pay all undisputed invoices issued by {p1} within {days} days of the invoice date.")
    add("payment_terms", "descriptive",
        "NO_NOT_OPERATIVE",
        f"Vendors in this industry commonly invoice on {days}-day terms, though the parties here have not yet "
        f"agreed on a specific payment schedule.")
    add("payment_terms", "negated",
        "NO_NOT_OPERATIVE",
        f"5. Payment. {p2} shall have no obligation to pay any amount to {p1} except as the parties may separately "
        f"agree in writing from time to time.")
    add("payment_terms", "conditional",
        "YES_BUT_CONDITIONAL",
        f"5. Payment. {p2} shall pay {p1}'s invoices within {days} days, provided that {p1} has delivered a "
        f"correctly formatted invoice referencing the applicable purchase order number.")
    add("payment_terms", "exception",
        "YES_BUT_EXCEPTION",
        f"5. Payment. {p2} shall pay all invoices within {days} days, except that {p2} may withhold payment of any "
        f"portion of an invoice that {p2} disputes in good faith by written notice.")
    add("payment_terms", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"5. Payment. Payment terms, including due dates and applicable currency, are as set forth in the pricing "
        f"schedule attached as Appendix {['I','II','III','IV','V','VI'][i]}.")
    add("payment_terms", "definition",
        "DEFINITION_DEPENDENT",
        f"5. Payment. {p2} shall pay all Recurring Charges within {days} days, as that term is defined elsewhere "
        f"in this Agreement.")
    add("payment_terms", "ambiguous",
        "AMBIGUOUS",
        f"5. Payment. {p2} shall pay invoices within {days} days. Section 11 separately states payment is due "
        f"within 10 days of receipt, without indicating which period governs.")
    add("payment_terms", "missing",
        "MISSING_CLAUSE",
        f"This statement of work between {p1} and {p2} describes deliverables and milestones only, and does not "
        f"otherwise address invoicing or payment.")

# ===========================================================================
# 05. ip_ownership (deliberately NOT reusing ip_ownership-080's phrasing:
# no "shall be owned exclusively by X upon Y" construction is used anywhere)
# ===========================================================================
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    add("ip_ownership", "operative",
        "YES_OPERATIVE",
        f"11. Ownership. As between the parties, {p2} owns all right, title, and interest in the deliverables "
        f"{p1} creates specifically for {p2} under this engagement.")
    add("ip_ownership", "descriptive",
        "NO_NOT_OPERATIVE",
        f"It is common in professional-services engagements for the client to retain ownership of bespoke "
        f"deliverables, though ownership has not yet been addressed for this particular engagement.")
    add("ip_ownership", "negated",
        "NO_NOT_OPERATIVE",
        f"11. Ownership. {p1} retains all rights in its own pre-existing tools, and this Agreement assigns no "
        f"ownership interest in such tools to {p2}.")
    add("ip_ownership", "conditional",
        "YES_BUT_CONDITIONAL",
        f"11. Ownership. Title to the deliverables shall transfer to {p2} upon {p2}'s receipt of {p1}'s final "
        f"invoice for the applicable milestone and confirmation that the invoice has been paid in full.")
    add("ip_ownership", "exception",
        "YES_BUT_EXCEPTION",
        f"11. Ownership. {p2} owns all deliverables created under this engagement, except for {p1}'s own "
        f"pre-existing methodologies and tooling, which {p1} retains and may reuse for other clients.")
    add("ip_ownership", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"11. Ownership. Ownership of intellectual property created under this engagement is allocated between "
        f"the parties as set forth in the IP Allocation Table in Exhibit {['J','K','L','M','N','O'][i]}.")
    add("ip_ownership", "definition",
        "DEFINITION_DEPENDENT",
        f"11. Ownership. {p2} owns all Custom Work Product, as defined in this Agreement, created under this "
        f"engagement.")
    add("ip_ownership", "ambiguous",
        "AMBIGUOUS",
        f"11. Ownership. {p2} owns all deliverables created under this engagement. Section 18 separately states "
        f"that {p1} retains ownership of all work product until final payment, without reconciling the two "
        f"statements.")
    add("ip_ownership", "missing",
        "MISSING_CLAUSE",
        f"This engagement letter between {p1} and {p2} sets out the scope of consulting services to be provided, "
        f"and does not otherwise address who owns any resulting work product.")

# ===========================================================================
# 06. insurance
# ===========================================================================
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    amt = [1, 2, 3, 5, 1.5, 2.5][i]
    add("insurance", "operative",
        "YES_OPERATIVE",
        f"13. Insurance. {p1} shall maintain commercial general liability insurance with limits of not less than "
        f"${amt} million per occurrence throughout the term of this Agreement.")
    add("insurance", "descriptive",
        "NO_NOT_OPERATIVE",
        f"Service providers of this kind typically carry commercial general liability coverage, though specific "
        f"minimum limits for this engagement remain to be negotiated.")
    add("insurance", "negated",
        "NO_NOT_OPERATIVE",
        f"13. Insurance. {p1} shall have no obligation under this Agreement to obtain or maintain any insurance "
        f"coverage.")
    add("insurance", "conditional",
        "YES_BUT_CONDITIONAL",
        f"13. Insurance. {p1} shall maintain liability coverage of at least ${amt} million, provided that such "
        f"coverage shall only be required for the duration of any on-site work performed at {p2}'s facilities.")
    add("insurance", "exception",
        "YES_BUT_EXCEPTION",
        f"13. Insurance. {p1} shall maintain liability coverage of at least ${amt} million, except that this "
        f"requirement shall not apply once {p1} has completed all deliverables and this Agreement has expired.")
    add("insurance", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"13. Insurance. {p1}'s required insurance coverage types and minimum limits are set forth in the "
        f"Insurance Requirements Schedule attached as Exhibit {['P','Q','R','S','T','U'][i]}.")
    add("insurance", "definition",
        "DEFINITION_DEPENDENT",
        f"13. Insurance. {p1} shall maintain the Required Coverage, as defined in this Agreement, throughout the "
        f"term.")
    add("insurance", "ambiguous",
        "AMBIGUOUS",
        f"13. Insurance. {p1} shall maintain liability coverage of ${amt} million. Section 21 separately requires "
        f"coverage of $10 million, without indicating which limit governs.")
    add("insurance", "missing",
        "MISSING_CLAUSE",
        f"This subcontract between {p1} and {p2} addresses scope, schedule, and price, and does not otherwise "
        f"address insurance coverage.")

# ===========================================================================
# 07. data_security
# ===========================================================================
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    hrs = [24, 48, 72, 12, 96, 36][i]
    add("data_security", "operative",
        "YES_OPERATIVE",
        f"10. Data Security. If {p1} becomes aware of unauthorized access to {p2}'s personal data, {p1} shall "
        f"notify {p2} within {hrs} hours of discovery.")
    add("data_security", "descriptive",
        "NO_NOT_OPERATIVE",
        f"Regulatory guidance in this sector generally recommends breach notification within a short window, "
        f"though the parties have not yet fixed a specific notification period for this engagement.")
    add("data_security", "negated",
        "NO_NOT_OPERATIVE",
        f"10. Data Security. {p1} shall have no obligation to notify {p2} of any security incident under this "
        f"Agreement.")
    add("data_security", "conditional",
        "YES_BUT_CONDITIONAL",
        f"10. Data Security. {p1} shall notify {p2} of a data breach within {hrs} hours, provided that {p1} has "
        f"first confirmed, through its own internal investigation, that personal data was actually affected.")
    add("data_security", "exception",
        "YES_BUT_EXCEPTION",
        f"10. Data Security. {p1} shall notify {p2} of any breach within {hrs} hours, except where a law "
        f"enforcement agency has directed {p1} in writing to delay notification pending an active investigation.")
    add("data_security", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"10. Data Security. {p1}'s breach notification obligations to {p2} are set forth in the Data Processing "
        f"Addendum referenced in Section {['3.2','4.1','5.3','6.2','7.1','8.4'][i]}.")
    add("data_security", "definition",
        "DEFINITION_DEPENDENT",
        f"10. Data Security. {p1} shall notify {p2} of any Security Incident, as that term is defined in this "
        f"Agreement, within {hrs} hours.")
    add("data_security", "ambiguous",
        "AMBIGUOUS",
        f"10. Data Security. {p1} shall notify {p2} within {hrs} hours of a breach. Section 16 separately requires "
        f"notification within 5 business days, without reconciling the two time periods.")
    add("data_security", "missing",
        "MISSING_CLAUSE",
        f"This data-processing order form between {p1} and {p2} specifies the categories of data processed and "
        f"processing purposes, and does not otherwise address breach notification.")

# ===========================================================================
# 08. governing_law
# ===========================================================================
STATES = ["Delaware", "New York", "California", "Texas", "Illinois", "Massachusetts"]
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    st = STATES[i]
    add("governing_law", "operative",
        "YES_OPERATIVE",
        f"20. Governing Law. This Agreement shall be governed by and construed in accordance with the laws of "
        f"the State of {st}, without regard to its conflict-of-laws principles.")
    add("governing_law", "descriptive",
        "NO_NOT_OPERATIVE",
        f"Agreements between parties headquartered in different states commonly designate a governing-law "
        f"provision, a topic the parties intend to finalize before execution.")
    add("governing_law", "negated",
        "NO_NOT_OPERATIVE",
        f"20. Governing Law. The parties expressly decline to designate a governing law for this Agreement at "
        f"this time.")
    add("governing_law", "conditional",
        "YES_BUT_CONDITIONAL",
        f"20. Governing Law. This Agreement shall be governed by the laws of {st}, provided that if {p1} "
        f"relocates its principal place of business to another state during the term, the law of that new state "
        f"shall govern from the date of relocation.")
    add("governing_law", "exception",
        "YES_BUT_EXCEPTION",
        f"20. Governing Law. This Agreement is governed by the laws of {st}, except that any dispute concerning "
        f"intellectual property ownership shall instead be governed by federal law.")
    add("governing_law", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"20. Governing Law. The governing law and venue applicable to this Agreement are as designated in the "
        f"Master Framework Agreement referenced in Recital {['A','B','C','D','E','F'][i]}.")
    add("governing_law", "definition",
        "DEFINITION_DEPENDENT",
        f"20. Governing Law. This Agreement is governed by the laws of the Designated Jurisdiction, as that term "
        f"is defined in this Agreement.")
    add("governing_law", "ambiguous",
        "AMBIGUOUS",
        f"20. Governing Law. This Agreement is governed by the laws of {st}. Section 27 separately designates "
        f"the laws of Nevada as governing, without resolving which state's law applies.")
    add("governing_law", "missing",
        "MISSING_CLAUSE",
        f"This short-form order between {p1} and {p2} covers pricing and delivery only, and does not otherwise "
        f"designate a governing law.")

# ===========================================================================
# 09. termination
# ===========================================================================
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    days = [30, 60, 90, 45, 15, 20][i]
    add("termination", "operative",
        "YES_OPERATIVE",
        f"17. Termination. Either party may terminate this Agreement for convenience upon {days} days' prior "
        f"written notice to the other party.")
    add("termination", "descriptive",
        "NO_NOT_OPERATIVE",
        f"Commercial agreements of this length commonly include a termination-for-convenience right, a point the "
        f"parties intend to address in a later amendment.")
    add("termination", "negated",
        "NO_NOT_OPERATIVE",
        f"17. Termination. Neither party shall have any right to terminate this Agreement prior to the end of "
        f"the stated term.")
    add("termination", "conditional",
        "YES_BUT_CONDITIONAL",
        f"17. Termination. {p2} may terminate this Agreement for convenience upon {days} days' notice, provided "
        f"that {p2} has first paid all outstanding invoices in full.")
    add("termination", "exception",
        "YES_BUT_EXCEPTION",
        f"17. Termination. Either party may terminate for convenience upon {days} days' notice, except that "
        f"{p1} may not exercise this right during the first six months of the term.")
    add("termination", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"17. Termination. The parties' termination rights are as set forth in the Master Terms referenced in "
        f"Section {['2.1','3.4','4.2','5.1','6.3','7.2'][i]}.")
    add("termination", "definition",
        "DEFINITION_DEPENDENT",
        f"17. Termination. Either party may terminate this Agreement upon the occurrence of a Material Breach, "
        f"as that term is defined in this Agreement.")
    add("termination", "ambiguous",
        "AMBIGUOUS",
        f"17. Termination. Either party may terminate for convenience upon {days} days' notice. Section 23 "
        f"separately requires 10 days' notice for termination, without indicating which period applies.")
    add("termination", "missing",
        "MISSING_CLAUSE",
        f"This one-time services order between {p1} and {p2} addresses scope and price only, and does not "
        f"otherwise address termination rights.")

# ===========================================================================
# 10. warranties
# ===========================================================================
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    add("warranties", "operative",
        "YES_OPERATIVE",
        f"8. Warranties. {p1} warrants that the services shall be performed in a professional and workmanlike "
        f"manner consistent with generally accepted industry standards.")
    add("warranties", "descriptive",
        "NO_NOT_OPERATIVE",
        f"Service agreements in this field customarily include a professional-standard warranty, though the "
        f"parties have not yet drafted specific warranty language here.")
    add("warranties", "negated",
        "NO_NOT_OPERATIVE",
        f"8. Warranties. {p1} makes no warranty of any kind, express or implied, regarding the services "
        f"performed under this Agreement.")
    add("warranties", "conditional",
        "YES_BUT_CONDITIONAL",
        f"8. Warranties. {p1} warrants the deliverables will conform to the specifications, provided that {p2} "
        f"notifies {p1} of any non-conformity within 30 days of delivery.")
    add("warranties", "exception",
        "YES_BUT_EXCEPTION",
        f"8. Warranties. {p1} warrants the deliverables will be free of material defects, except for defects "
        f"caused by {p2}'s misuse or unauthorized modification of the deliverables.")
    add("warranties", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"8. Warranties. {p1}'s warranty obligations to {p2} are as set forth in the Warranty Schedule attached "
        f"as Exhibit {['W','X','Y','Z','AA','BB'][i]}.")
    add("warranties", "definition",
        "DEFINITION_DEPENDENT",
        f"8. Warranties. {p1} warrants that the Deliverables, as defined in this Agreement, will materially "
        f"conform to the agreed specifications.")
    add("warranties", "ambiguous",
        "AMBIGUOUS",
        f"8. Warranties. {p1} warrants the deliverables for 12 months. Section 15 separately states the warranty "
        f"period is 90 days, without reconciling the two durations.")
    add("warranties", "missing",
        "MISSING_CLAUSE",
        f"This purchase agreement between {p1} and {p2} specifies product quantities and pricing only, and does "
        f"not otherwise address any warranty of quality or performance.")

# ===========================================================================
# 11. sla
# ===========================================================================
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    pct = [99.5, 99.9, 99.0, 99.95, 99.7, 99.99][i]
    add("sla", "operative",
        "YES_OPERATIVE",
        f"12. Service Levels. {p1} shall maintain at least {pct}% uptime for the hosted service, measured "
        f"monthly.")
    add("sla", "descriptive",
        "NO_NOT_OPERATIVE",
        f"Hosted-service providers in this market commonly commit to uptime in the high 99% range, though a "
        f"specific commitment for this engagement has not yet been negotiated.")
    add("sla", "negated",
        "NO_NOT_OPERATIVE",
        f"12. Service Levels. {p1} makes no commitment regarding the uptime or availability of the hosted "
        f"service under this Agreement.")
    add("sla", "conditional",
        "YES_BUT_CONDITIONAL",
        f"12. Service Levels. {p1} shall maintain {pct}% uptime, provided that scheduled maintenance windows of "
        f"which {p2} receives at least 48 hours' notice are excluded from the calculation.")
    add("sla", "exception",
        "YES_BUT_EXCEPTION",
        f"12. Service Levels. {p1} shall maintain {pct}% uptime, except that downtime caused by {p2}'s own "
        f"network or equipment shall not count against {p1}'s uptime commitment.")
    add("sla", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"12. Service Levels. {p1}'s uptime commitment and associated service credits are as set forth in the "
        f"Service Level Schedule attached as Exhibit {['CC','DD','EE','FF','GG','HH'][i]}.")
    add("sla", "definition",
        "DEFINITION_DEPENDENT",
        f"12. Service Levels. {p1} shall maintain the Required Availability, as defined in this Agreement, for "
        f"the hosted service.")
    add("sla", "ambiguous",
        "AMBIGUOUS",
        f"12. Service Levels. {p1} shall maintain {pct}% uptime. Section 20 separately commits to 99.999% uptime, "
        f"without indicating which commitment controls.")
    add("sla", "missing",
        "MISSING_CLAUSE",
        f"This hosting order form between {p1} and {p2} specifies the service tier and monthly fee only, and "
        f"does not otherwise address uptime or service levels.")

# ===========================================================================
# 12. assignment
# ===========================================================================
for i, (p1, p2) in enumerate(PARTY_PAIRS):
    add("assignment", "operative",
        "YES_OPERATIVE",
        f"18. Assignment. Neither party may assign this Agreement without the other party's prior written "
        f"consent, not to be unreasonably withheld.")
    add("assignment", "descriptive",
        "NO_NOT_OPERATIVE",
        f"Commercial agreements typically restrict assignment without consent, a term the parties intend to "
        f"finalize in a later revision of this draft.")
    add("assignment", "negated",
        "NO_NOT_OPERATIVE",
        f"18. Assignment. This Agreement places no restriction whatsoever on either party's ability to assign "
        f"its rights or obligations hereunder.")
    add("assignment", "conditional",
        "YES_BUT_CONDITIONAL",
        f"18. Assignment. {p1} may assign this Agreement to a successor entity, provided that {p1} gives {p2} "
        f"at least 30 days' prior written notice of the assignment.")
    add("assignment", "exception",
        "YES_BUT_EXCEPTION",
        f"18. Assignment. Neither party may assign this Agreement without consent, except that either party may "
        f"assign this Agreement without consent to an entity that acquires substantially all of its assets.")
    add("assignment", "cross_reference",
        "CROSS_REFERENCE_DEPENDENT",
        f"18. Assignment. The parties' rights to assign this Agreement are governed by the Master Framework "
        f"Agreement referenced in Recital {['G','H','I','J','K','L'][i]}.")
    add("assignment", "definition",
        "DEFINITION_DEPENDENT",
        f"18. Assignment. Neither party may assign this Agreement to a Competing Business, as that term is "
        f"defined in this Agreement, without the other's consent.")
    add("assignment", "ambiguous",
        "AMBIGUOUS",
        f"18. Assignment. Neither party may assign this Agreement without consent. Section 25 separately permits "
        f"free assignment by either party, without reconciling the two provisions.")
    add("assignment", "missing",
        "MISSING_CLAUSE",
        f"This short-form purchase order between {p1} and {p2} addresses product and price only, and does not "
        f"otherwise address assignment of the order.")

BASE_COUNT = len(CASES)

# ===========================================================================
# Composite / whole-document cases (interaction scenarios, deliberately
# clean agreements, deliberately unsafe agreements, unusual drafting order,
# role ambiguity, asymmetric obligations) -- hand-authored, not templated.
# ===========================================================================

add("limitation_of_liability", "interaction_uncapped_indemnity",
    "YES_OPERATIVE",
    "16. Limitation of Liability. Operator's aggregate liability under this Agreement shall be unlimited and "
    "shall not be subject to any cap or exclusion of any kind.\n\n17. Indemnification. Operator shall indemnify, "
    "defend, and hold harmless Subscriber from any and all third-party claims, of any kind, without limitation, "
    "arising from Operator's performance under this Agreement.",
    notes="Composite document pairing an unlimited liability clause with an uncapped indemnity -- intended to "
          "exercise IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY under real cutover.")

add("indemnification", "interaction_uncapped_indemnity",
    "YES_OPERATIVE",
    "16. Limitation of Liability. Operator's aggregate liability under this Agreement shall be unlimited and "
    "shall not be subject to any cap or exclusion of any kind.\n\n17. Indemnification. Operator shall indemnify, "
    "defend, and hold harmless Subscriber from any and all third-party claims, of any kind, without limitation, "
    "arising from Operator's performance under this Agreement.",
    notes="Same composite document, scored from the indemnification adapter's perspective.")

add("termination", "interaction_nonpayment_vs_dispute",
    "YES_BUT_CONDITIONAL",
    "18. Termination. Company may terminate this Agreement immediately upon Counterparty's failure to pay any "
    "invoice within 30 days of its due date.\n\n6. Payment. Counterparty may withhold payment of any invoice, "
    "or portion thereof, that it disputes in good faith by written notice to Company, and such withheld amounts "
    "shall not be deemed overdue for purposes of this Agreement.",
    notes="Composite document pairing a nonpayment-termination trigger with a dispute-withholding right -- "
          "intended to exercise IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING under real cutover.")

add("payment_terms", "interaction_nonpayment_vs_dispute",
    "YES_BUT_EXCEPTION",
    "18. Termination. Company may terminate this Agreement immediately upon Counterparty's failure to pay any "
    "invoice within 30 days of its due date.\n\n6. Payment. Counterparty may withhold payment of any invoice, "
    "or portion thereof, that it disputes in good faith by written notice to Company, and such withheld amounts "
    "shall not be deemed overdue for purposes of this Agreement.",
    notes="Same composite document, scored from the payment_terms adapter's perspective.")

add("sla", "interaction_sla_payment_credit",
    "YES_OPERATIVE",
    "12. Service Levels. Provider shall maintain 99.9% uptime for the hosted service, measured monthly, and "
    "shall issue Recipient a service credit against future fees for any shortfall.\n\n6. Payment. Recipient "
    "shall pay Provider's invoices, net of any service credits owed under Section 12, within 30 days.",
    notes="Composite document pairing an SLA credit mechanism with payment terms -- intended to exercise "
          "IX_SLA_PAYMENT_CREDIT_DEPENDENCY under real cutover.")

add("payment_terms", "interaction_sla_payment_credit",
    "YES_OPERATIVE",
    "12. Service Levels. Provider shall maintain 99.9% uptime for the hosted service, measured monthly, and "
    "shall issue Recipient a service credit against future fees for any shortfall.\n\n6. Payment. Recipient "
    "shall pay Provider's invoices, net of any service credits owed under Section 12, within 30 days.",
    notes="Same composite document, scored from the payment_terms adapter's perspective.")

add("limitation_of_liability", "unusual_drafting_order",
    "YES_OPERATIVE",
    "Notwithstanding anything to the contrary elsewhere in this Agreement, and before any other provision of "
    "this Section is read, the parties agree first and foremost that Licensor's liability arising under or in "
    "connection with this Agreement, however characterized, shall in no circumstance exceed two times the "
    "license fees paid in the preceding year.",
    notes="Deliberately unusual sentence order (qualifier-first, operative clause last) for the same underlying "
          "liability-cap concept.")

add("ip_ownership", "role_ambiguity",
    "AMBIGUOUS",
    "11. Ownership. The party responsible for creating the deliverables under this engagement, whichever party "
    "that ultimately is determined to be given the parties' overlapping staffing arrangement described in "
    "Exhibit A, shall own all resulting work product, without further specifying which named party this refers "
    "to.",
    notes="Role ambiguity -- no named party is clearly the owner; the clause defers to an undetermined "
          "resolution.")

add("insurance", "asymmetric_obligations",
    "YES_OPERATIVE",
    "13. Insurance. Contractor shall maintain commercial general liability insurance of at least $2 million per "
    "occurrence. Client shall maintain commercial general liability insurance of at least $5 million per "
    "occurrence, reflecting Client's larger on-site workforce.",
    notes="Asymmetric obligations -- both parties have real, but different, insurance requirements; a "
          "single-attribution adapter should establish at least one side without collapsing the asymmetry.")

add("confidentiality", "deliberately_clean_agreement",
    "YES_OPERATIVE",
    "MASTER SERVICES AGREEMENT (Excerpt)\n\n7. Confidentiality. Each of Supplier and Buyer shall protect the "
    "other's Confidential Information using at least a reasonable degree of care for five years following "
    "disclosure, and shall not disclose it to any third party without the disclosing party's prior written "
    "consent, except as required by law after providing the disclosing party reasonable advance notice.",
    notes="A deliberately clean, fully-resolved confidentiality clause (operative, has a term, has a lawful "
          "exception) with nothing left ambiguous -- expected to reach a clean ACCEPT-shaped decision.")

add("data_security", "deliberately_unsafe_agreement",
    "YES_OPERATIVE",
    "10. Data Security. Operator shall notify Subscriber of a security incident affecting personal data within "
    "30 days of discovery. Operator may, in its sole discretion, decline to notify Subscriber of any incident "
    "Operator determines, in its own judgment, not to be material, and Operator's determination of materiality "
    "shall be final and not subject to review or challenge by Subscriber.",
    notes="Deliberately unsafe drafting -- a nominal notification obligation is effectively hollowed out by an "
          "unreviewable unilateral materiality carve-out; expected to at least establish the clause as operative, "
          "testing whether the adapter recognizes the underlying obligation despite the self-serving carve-out.")

add("termination", "conflicting_provisions",
    "AMBIGUOUS",
    "17. Termination. Either party may terminate this Agreement for convenience upon 60 days' prior written "
    "notice. Section 24, Miscellaneous, separately states that this Agreement may only be terminated for cause "
    "and that no right of termination for convenience exists, without either provision referencing or "
    "reconciling the other.",
    notes="Directly conflicting whole-document provisions (one grants a termination-for-convenience right, "
          "another denies any such right exists) with no cross-reference between them.")

CORPUS_SIZE = len(CASES)
print(f"Generated {CORPUS_SIZE} cases ({BASE_COUNT} templated + {CORPUS_SIZE - BASE_COUNT} composite/hand-authored).")

with open("cases.json", "w") as f:
    json.dump(CASES, f, indent=2)

corpus_bytes = json.dumps(CASES, sort_keys=True).encode("utf-8")
sha256 = hashlib.sha256(corpus_bytes).hexdigest()
print(f"SHA-256: {sha256}")

from collections import Counter
adapter_dist = Counter(c["adapter"] for c in CASES)
family_dist = Counter(c["family"] for c in CASES)
print("Adapter distribution:", dict(adapter_dist))
print("Family distribution:", dict(family_dist))

with open("corpus_sha256.txt", "w") as f:
    f.write(sha256 + "\n")
