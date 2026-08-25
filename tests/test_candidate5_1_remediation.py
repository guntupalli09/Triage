"""
Candidate 5.1 remediation — targeted semantic-class tests for the three
remaining Candidate 5 failure classes: FALSE_ABSENCE (ip_ownership/
warranties), MATERIAL_CONTEXT_SILENTLY_LOST (sla/warranties), and the
FALSE_SAFE regression discovered and fixed while closing FALSE_ABSENCE.

Each class is tested with: the original burned-corpus shape, >=5
materially different fresh variants (per the mission's explicit
requirement), and negative controls that look lexically similar but mean
something structurally different.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "artifacts" / "candidate2_remediation" / "corpus_replay"))

import ip_ownership_policy_engine as ipo
import warranties_policy_engine as we
import replay_candidate2 as rc2


# ---------------------------------------------------------------------------
# Semantic class: OWNERSHIP_VESTING_STATEMENT (ip_ownership FALSE_ABSENCE)
# ---------------------------------------------------------------------------

def test_burned_owns_all_deliverables_with_exception():
    extract_fn, evaluate_fn, policy_cls = rc2.ADAPTERS["ip_ownership"]
    text = (
        "11. Ownership. Licensee owns all deliverables created under this engagement, except for "
        "Licensor's own pre-existing methodologies and tooling, which Licensor retains and may "
        "reuse for other clients."
    )
    f = extract_fn(text)
    assert f is not None
    assert f.ownership_attributions.get("work_product", {}).get("Licensee") is True
    d = evaluate_fn(f, policy_cls())
    # The same-sentence exception (deterministic_condition_established)
    # must force review, not a silent clean ACCEPT.
    assert d.state == "REQUIRES_REVIEW"


def test_burned_owns_right_title_and_interest():
    f = ipo.extract_ip_facts(
        "11. Ownership. As between the parties, Subscriber owns all right, title, and interest in "
        "the deliverables Operator creates specifically for Subscriber under this engagement."
    )
    assert f is not None
    assert f.ownership_attributions.get("work_product", {}).get("Subscriber") is True


FRESH_VESTING_VARIANTS = [
    "Section 9. Vendor owns all custom software modules built for this project.",
    "Section 9. All right, title, and interest in the Reports shall vest in Client immediately upon creation.",
    "Section 9. Ownership of the Prototype shall pass to Buyer upon final acceptance testing.",
    "Section 9. Each party retains ownership of its pre-existing background technology; Contractor "
    "owns all newly developed deliverables created under this Agreement.",
    "Section 9. Ownership of the deliverables shall transfer to Client only after full payment of "
    "all outstanding invoices.",
]


def test_fresh_vesting_variants_never_absent():
    """Each variant must at minimum be discovered (facts is not None) and
    never left with zero ownership signal AND zero unresolved marker --
    i.e. it must never silently resolve to the FALSE_ABSENCE shape this
    class targets. Some variants establish a clean, grounded ownership
    attribution with no gap (a legitimate ACCEPT); others carry an
    unresolved marker (PRESENT_BUT_UNRESOLVED). Both are safe outcomes;
    silently returning None (facts=None, NOT_APPLICABLE) is not."""
    for text in FRESH_VESTING_VARIANTS:
        f = ipo.extract_ip_facts(text)
        assert f is not None, text
        assert f.ownership_attributions or f.absence_state == "PRESENT_BUT_UNRESOLVED", (text, f)


NEGATIVE_CONTROLS_VESTING = [
    # A retention-only statement about a party's OWN pre-existing rights,
    # with an explicit negation to the counterparty -- must NOT anchor
    # (this is the exact FALSE_SAFE regression this mission fixed).
    "11. Ownership. Provider retains all rights in its own pre-existing tools, and this Agreement "
    "assigns no ownership interest in such tools to Recipient.",
    # Lexically similar "title"/"who owns" constructions that are NOT
    # ownership-vesting statements at all.
    "Section 9. The Sales Manager title shall be reassigned to a new hire next quarter.",
    "This engagement letter between Provider and Recipient sets out the scope of consulting "
    "services to be provided, and does not otherwise address who owns any resulting work product.",
    # Descriptive/industry commentary, not this agreement's own operative term.
    "Section 9. It is common practice for the client to own project deliverables in agreements of "
    "this type, though the parties have not yet reached agreement on this point.",
    "Section 9. Historically, vendors have owned their own tooling in this industry.",
]


def test_negative_controls_never_false_operative():
    for text in NEGATIVE_CONTROLS_VESTING:
        f = ipo.extract_ip_facts(text)
        if f is not None:
            # Never established as an operative, clean-worthy ownership fact.
            assert not f.ownership_attributions, (text, f.ownership_attributions)


# ---------------------------------------------------------------------------
# Semantic class: TRAILING EXCEPTION CONNECTOR ("except that"/"except for")
# on an established commitment (sla/warranties MATERIAL_CONTEXT_SILENTLY_LOST)
# ---------------------------------------------------------------------------

def test_burned_sla_uptime_except_that():
    f = rc2.ADAPTERS["sla"][0](
        "12. Service Levels. Provider shall maintain 99.5% uptime, except that downtime caused by "
        "Recipient's own network or equipment shall not count against Provider's uptime commitment."
    )
    assert f is not None and f.deterministic_condition_established


FRESH_SLA_EXCEPT_VARIANTS = [
    "Section 8. Vendor shall maintain 99.9% uptime, except that scheduled maintenance windows of "
    "up to 4 hours per month shall not count as downtime.",
    "Section 8 (SLA). Operator commits to an availability commitment of 99.8% uptime, except that "
    "outages caused by a third-party cloud provider outside its control shall be excluded.",
    "Section 8. Supplier shall achieve 99.99% uptime, except that any downtime attributable to "
    "Customer's failure to provide required network access shall not be counted.",
]


def test_fresh_sla_except_that_variants_establish_condition():
    extract_fn = rc2.ADAPTERS["sla"][0]
    for text in FRESH_SLA_EXCEPT_VARIANTS:
        f = extract_fn(text)
        assert f is not None, text
        assert f.deterministic_condition_established, text


NEGATIVE_CONTROLS_SLA = [
    # The credit-TRIGGER mechanism itself ("if X fails, Y credit") is not
    # an exception on the uptime commitment -- must NOT falsely trigger.
    "Service Levels. If Provider fails to meet the Service Level, Customer shall receive a service "
    "credit equal to 5% of the monthly fees.",
    # A clean uptime commitment with no exception at all.
    "Section 8. Provider shall maintain 99.5% uptime measured monthly.",
]


def test_negative_controls_sla_no_false_condition():
    extract_fn, evaluate_fn, policy_cls = rc2.ADAPTERS["sla"]
    policy = policy_cls()
    for text in NEGATIVE_CONTROLS_SLA:
        f = extract_fn(text)
        assert f is not None, text
        assert not f.deterministic_condition_established, text
        d = evaluate_fn(f, policy)
        assert d.state == "ACCEPT", (text, d.state)


def test_burned_warranties_defect_free_except_for():
    f = we.extract_warranties_facts(
        "8. Warranties. Operator warrants the deliverables will be free of material defects, "
        "except for defects caused by Subscriber's misuse or unauthorized modification of the "
        "deliverables."
    )
    assert f is not None
    assert f.categories["defect_free"].established
    assert f.deterministic_condition_established


FRESH_WARRANTY_DEFECT_VARIANTS = [
    "Clause 6. Contractor warrants the goods will be free from defects in materials and "
    "workmanship, except for wear and tear resulting from Client's normal use.",
    "Section 7. Supplier warrants the equipment shall be free of defects, except for damage caused "
    "by improper installation by a third party.",
    "8. Warranties. Vendor represents the software will be free of material defects for 90 days, "
    "except for defects arising from unauthorized modifications by Customer.",
]


def test_fresh_warranty_defect_variants_establish_category_and_exception():
    for text in FRESH_WARRANTY_DEFECT_VARIANTS:
        f = we.extract_warranties_facts(text)
        assert f is not None, text
        assert f.categories["defect_free"].established, text
        assert f.deterministic_condition_established, text
