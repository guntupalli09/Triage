"""
Regression tests for the five P0 production blockers found by the Playbook
UX walkthrough (artifacts/playbook_ux_walkthrough/ux_walkthrough_report.md).

Each class below reproduces one P0 at the route/service level first, then
asserts the fixed behavior:

  P0-1  Submit for review must persist the currently displayed form state
        atomically, not silently discard it in favor of the last-saved row.
  P0-2  "Policy status: Active" (lifecycle) must never be presented as
        "this policy is governing this review" while POLICY_ENFORCEMENT_MODE
        is shadow/legacy, and the operational surface must show how long the
        deployment has been in its current enforcement mode.
  P0-3  The Liability engine must discover a limitation-of-liability
        provision from ordinary commercial cap drafting, not only from the
        literal phrases "limitation of liability"/"liability cap".
  P0-4  Playbook comparison output must be JSON-serializable (Deviation
        dataclasses crossing the persistence boundary caused a 500).
  P0-5  "Request exception" (and every other departure from an authoritative
        policy recommendation) must be rejected server-side without a
        non-empty, non-whitespace reason.
"""
import io
import json
import os
import re

os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi.testclient import TestClient

import liability_policy_engine as lpe
import main
import playbook_engine
import policy_enforcement
import policy_readiness
import rate_limit
import review_workflow
from database import SessionLocal
from models import Contract, Playbook, PolicyPosition, User

TEMPLATE_BYTES = b"This is a template contract. Governing Law: Delaware."


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    rate_limit._memory_counters.clear()
    yield
    rate_limit._memory_counters.clear()


@pytest.fixture(autouse=True)
def _shadow_mode_default(monkeypatch):
    """Tests must not inherit a developer's local .env cutover setting."""
    monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "shadow")
    yield


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _register(client, email) -> str:
    email = email.lower()
    r = client.get("/register")
    token = r.cookies.get("csrf_token")
    client.post("/register", data={
        "email": email, "password": "Str0ngP@ssw0rd!", "confirm_password": "Str0ngP@ssw0rd!",
        "name": "Sarah Chen", "company": "", "csrf_token": token,
    })
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user.plan = "professional"
        db.commit()
    finally:
        db.close()
    return token


def _create_playbook(client, token, name="P0 Playbook", template_bytes=TEMPLATE_BYTES) -> int:
    files = {"file": ("template.txt", io.BytesIO(template_bytes), "text/plain")}
    r = client.post("/playbooks/new", data={
        "name": name, "contract_type": "", "description": "", "lol_enabled": "", "csrf_token": token,
    }, files=files, follow_redirects=False)
    assert r.status_code == 302, r.text
    db = SessionLocal()
    try:
        pb = db.query(Playbook).filter(Playbook.name == name).order_by(Playbook.id.desc()).first()
        return pb.id
    finally:
        db.close()


LIABILITY_FORM = {
    "preferred_multiplier": "1.0", "acceptable_max_multiplier": "2.0", "negotiate_max_multiplier": "3.0",
    "prohibit_unlimited": "yes",
    "required_exceptions_json": ["fraud", "confidentiality"],
    "require_consequential_damages_exclusion": "no",
    "contract_side": "sell_side", "escalation_approval_authority": "General Counsel",
    "fallback_text": "Approved fallback language.",
}


def _position(pb_id, clause_type="limitation_of_liability"):
    db = SessionLocal()
    try:
        return (
            db.query(PolicyPosition)
            .filter(PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == clause_type)
            .order_by(PolicyPosition.id.desc())
            .first()
        )
    finally:
        db.close()


def _lawyer_visible_text(html: str) -> str:
    """Page text with <style>/<script> blocks and class attributes removed —
    what a lawyer actually reads. CSS utility names like `shadow-sm` are not
    product copy and must not be confused with the enforcement-mode word."""
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r'class="[^"]*"', " ", html)
    return html


def _comparable(position) -> dict:
    """Everything about a persisted position that constitutes the policy
    configuration — deliberately excludes ids/timestamps/status."""
    return {
        "config_json": dict(position.config_json or {}),
        "contract_side": position.contract_side,
        "escalation_approval_authority": position.escalation_approval_authority,
        "fallback_text": position.fallback_text,
    }


# ---------------------------------------------------------------------------
# P0-1 — Submit for review must not discard unsaved authoring input
# ---------------------------------------------------------------------------

class TestP0_1SubmitForReviewPersistsFormState:
    def test_submit_for_review_without_prior_save_persists_the_form(self, client):
        token = _register(client, "p0-1-nosave@example.com")
        pb_id = _create_playbook(client, token, name="P0-1 no save")

        # Open the authoring page (creates the DRAFT row), then submit the
        # form straight to submit-for-review WITHOUT clicking Save draft.
        assert client.get(f"/playbooks/{pb_id}/positions/limitation_of_liability/edit").status_code == 200
        data = dict(LIABILITY_FORM)
        data["csrf_token"] = token
        data["authoring_form"] = "1"
        r = client.post(
            f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review",
            data=data, follow_redirects=False,
        )
        assert r.status_code == 302, r.text

        position = _position(pb_id)
        assert position.status == "NEEDS_REVIEW"
        # Before the fix, config_json was {} here: the route read the
        # last-persisted row and never looked at the submitted form.
        assert position.config_json.get("preferred_multiplier") == 1.0
        assert position.config_json.get("acceptable_max_multiplier") == 2.0
        assert position.config_json.get("negotiate_max_multiplier") == 3.0
        assert position.config_json.get("prohibit_unlimited") is True
        assert position.contract_side == "sell_side"
        assert position.escalation_approval_authority == "General Counsel"
        assert position.fallback_text == "Approved fallback language."

    def test_edit_then_submit_equals_edit_then_save_then_submit(self, client):
        token_a = _register(client, "p0-1-direct@example.com")
        pb_a = _create_playbook(client, token_a, name="P0-1 direct")
        client.get(f"/playbooks/{pb_a}/positions/limitation_of_liability/edit")
        direct = dict(LIABILITY_FORM, csrf_token=token_a, authoring_form="1")
        assert client.post(
            f"/playbooks/{pb_a}/positions/limitation_of_liability/submit-for-review",
            data=direct, follow_redirects=False,
        ).status_code == 302

        with TestClient(main.app) as client_b:
            token_b = _register(client_b, "p0-1-saved@example.com")
            pb_b = _create_playbook(client_b, token_b, name="P0-1 saved")
            client_b.get(f"/playbooks/{pb_b}/positions/limitation_of_liability/edit")
            saved = dict(LIABILITY_FORM, csrf_token=token_b, authoring_form="1")
            assert client_b.post(
                f"/playbooks/{pb_b}/positions/limitation_of_liability/save",
                data=saved, follow_redirects=False,
            ).status_code == 302
            assert client_b.post(
                f"/playbooks/{pb_b}/positions/limitation_of_liability/submit-for-review",
                data=dict(saved), follow_redirects=False,
            ).status_code == 302

        pos_a, pos_b = _position(pb_a), _position(pb_b)
        assert pos_a.status == pos_b.status == "NEEDS_REVIEW"
        assert _comparable(pos_a) == _comparable(pos_b)

    def test_invalid_form_keeps_values_shows_error_and_does_not_transition(self, client):
        token = _register(client, "p0-1-invalid@example.com")
        pb_id = _create_playbook(client, token, name="P0-1 invalid")
        client.get(f"/playbooks/{pb_id}/positions/limitation_of_liability/edit")

        bad = dict(LIABILITY_FORM, csrf_token=token, authoring_form="1")
        bad["acceptable_max_multiplier"] = "not-a-number"
        r = client.post(
            f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review",
            data=bad, follow_redirects=False,
        )
        assert r.status_code == 400
        assert "number" in r.text.lower()
        # Entered values survive the re-render...
        assert "General Counsel" in r.text
        assert "Approved fallback language." in r.text
        # ...and no lifecycle transition happened.
        assert _position(pb_id).status == "DRAFT"

    def test_bare_transition_post_without_form_still_works(self, client):
        """Backwards compatibility: a submit-for-review post that carries no
        authoring payload (no authoring_form marker) must still transition
        the already-saved row rather than blanking it."""
        token = _register(client, "p0-1-bare@example.com")
        pb_id = _create_playbook(client, token, name="P0-1 bare")
        saved = dict(LIABILITY_FORM, csrf_token=token)
        assert client.post(
            f"/playbooks/{pb_id}/positions/limitation_of_liability/save",
            data=saved, follow_redirects=False,
        ).status_code == 302
        assert client.post(
            f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review",
            data={"csrf_token": token}, follow_redirects=False,
        ).status_code == 302
        position = _position(pb_id)
        assert position.status == "NEEDS_REVIEW"
        assert position.config_json.get("preferred_multiplier") == 1.0

    def test_authoring_form_posts_submit_for_review_within_the_same_form(self):
        """The template must submit the real field values with the
        Submit-for-review action (formaction on the authoring form), not
        from a second, empty form."""
        html = open("templates/playbook_position_edit_base.html").read()
        assert 'name="authoring_form"' in html
        assert "formaction=" in html
        assert "submit-for-review" in html


# ---------------------------------------------------------------------------
# P0-2 — ACTIVE lifecycle vs. shadow enforcement conflation
# ---------------------------------------------------------------------------

class TestP0_2EnforcementModeTruthfulness:
    def test_single_canonical_mode_reader(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "shadow")
        assert policy_enforcement.get_enforcement_mode() == "shadow"
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        assert policy_enforcement.get_enforcement_mode() == "cutover"
        assert policy_enforcement.is_policy_authoritative() is True
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "shadow")
        assert policy_enforcement.is_policy_authoritative() is False
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "legacy")
        assert policy_enforcement.is_policy_authoritative() is False

    @pytest.mark.parametrize("mode", ["shadow", "legacy"])
    def test_workbench_qualifies_active_when_not_authoritative(self, client, monkeypatch, mode):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", mode)
        token = _register(client, f"p0-2-wb-{mode}@example.com")
        pb_id = _create_playbook(client, token, name=f"P0-2 workbench {mode[:3]}")
        r = client.get(f"/playbooks/{pb_id}/workbench")
        assert r.status_code == 200
        body = r.text
        # Plain language for lawyers — never raw env-var terminology.
        assert "Checking only" in body
        assert "POLICY_ENFORCEMENT_MODE" not in body
        visible = _lawyer_visible_text(body)
        assert not re.search(r"\bshadow\b", visible, re.I)
        assert not re.search(r"\bcutover\b", visible, re.I)

    def test_workbench_says_governing_when_authoritative(self, client, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        token = _register(client, "p0-2-wb-cutover@example.com")
        pb_id = _create_playbook(client, token, name="P0-2 workbench authoritative")
        r = client.get(f"/playbooks/{pb_id}/workbench")
        assert r.status_code == 200
        assert "Checking only" not in r.text
        assert "Governing contract reviews" in r.text
        assert not re.search(r"\bcutover\b", _lawyer_visible_text(r.text), re.I)

    @pytest.mark.parametrize("mode,expect_qualifier", [("shadow", True), ("legacy", True), ("cutover", False)])
    def test_review_page_qualifies_enforcement(self, client, monkeypatch, mode, expect_qualifier):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", mode)
        token = _register(client, f"p0-2-rev-{mode}@example.com")
        pb_id = _create_playbook(client, token, name=f"P0-2 review {mode[:3]}")
        files = {"file": ("c.txt", io.BytesIO(b"Limitation of Liability. Aggregate liability shall not exceed 5 times the fees paid."), "text/plain")}
        r = client.post("/upload", data={"csrf_token": token, "playbook_id": str(pb_id)}, files=files, follow_redirects=False)
        assert r.status_code in (302, 303), r.text
        contract_id = r.headers["location"].rstrip("/").split("/")[-2]
        r = client.get(f"/contract/{contract_id}/review")
        assert r.status_code == 200
        if expect_qualifier:
            assert "Checking only" in r.text
            assert "Governing contract reviews" not in r.text
        else:
            assert "Governing contract reviews" in r.text
        assert "POLICY_ENFORCEMENT_MODE" not in r.text
        visible = _lawyer_visible_text(r.text)
        assert not re.search(r"\bcutover\b", visible, re.I)
        assert not re.search(r"\bshadow\b", visible, re.I)

    def test_readiness_surface_reports_mode_and_duration(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "shadow")
        db = SessionLocal()
        try:
            policy_enforcement.record_enforcement_mode_observation(db)
            db.commit()
            status = policy_readiness.compute_enforcement_mode_status(db)
            assert status.mode == "shadow"
            assert status.since is not None
            assert status.days_in_mode is not None
            report = policy_readiness.assess_readiness(db, run_benchmarks=False, run_tests=False)
            safe = policy_readiness.report_to_safe_dict(report)
            assert safe["enforcement_mode"]["mode"] == "shadow"
            assert "days_in_mode" in safe["enforcement_mode"]
            assert safe["enforcement_mode"]["since"] is not None
        finally:
            db.close()

    def test_mode_observation_is_recorded_once_per_mode(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "shadow")
        db = SessionLocal()
        try:
            from models import AuditLog
            before = db.query(AuditLog).filter(
                AuditLog.event_type == policy_enforcement.ENFORCEMENT_MODE_EVENT_TYPE
            ).count()
            policy_enforcement.record_enforcement_mode_observation(db)
            policy_enforcement.record_enforcement_mode_observation(db)
            db.commit()
            after = db.query(AuditLog).filter(
                AuditLog.event_type == policy_enforcement.ENFORCEMENT_MODE_EVENT_TYPE
            ).count()
            assert after - before <= 1
        finally:
            db.close()


# ---------------------------------------------------------------------------
# P0-3 — Liability provision discovery
# ---------------------------------------------------------------------------

NORTHSTAR_LIABILITY_CLAUSE = (
    "Except for Customer's payment obligations, Provider's liability shall be unlimited for "
    "breaches of confidentiality, data security obligations, intellectual property infringement, "
    "and indemnification obligations. For all other claims, Provider's aggregate liability shall "
    "not exceed five times the fees paid under this Agreement. Neither limitation shall apply to "
    "Provider's gross negligence, willful misconduct, or fraud."
)


class TestP0_3LiabilityDiscovery:
    def test_northstar_clause_is_discovered_without_a_heading(self):
        facts = lpe.extract_liability_facts(NORTHSTAR_LIABILITY_CLAUSE)
        assert facts is not None, "engine returned NOT_APPLICABLE for a real liability cap clause"
        assert facts.clause_found is True

    @pytest.mark.parametrize("text", [
        "Provider's aggregate liability shall not exceed 2 times the fees paid under this Agreement.",
        "The total liability of either party shall not exceed the fees paid in the preceding 12 months.",
        "Supplier's liability is capped at $500,000.00 in the aggregate.",
        "Vendor's maximum liability under this Agreement shall not exceed 1 times the annual fees paid.",
        "In no event shall Provider's liability exceed the total fees paid under this Agreement.",
        "Each party's liability is limited to the fees paid in the twelve (12) months preceding the claim.",
        "Provider shall have unlimited liability for breaches of its data security obligations.",
    ])
    def test_commercially_standard_cap_language_is_discovered(self, text):
        assert lpe.extract_liability_facts(text) is not None

    @pytest.mark.parametrize("text", [
        # Indemnification clause that merely mentions liabilities.
        "Customer shall indemnify, defend, and hold harmless Provider from and against any and all "
        "third-party claims, damages, liabilities, costs, and expenses (including reasonable "
        "attorneys' fees) arising out of Customer's breach of this Agreement.",
        # Insurance clause with dollar limits and the word liability.
        "Each party shall maintain commercial general liability insurance with limits of not less "
        "than $2,000,000 per occurrence and $5,000,000 in the aggregate.",
        # Joint-and-several liability allocation, not a cap.
        "The obligations of the Customer entities under this Agreement are joint and several, and "
        "each such entity accepts liability for the acts of the others.",
        # Governing-law clause naming liability in passing.
        "Any liability arising under this Agreement shall be determined in accordance with the laws "
        "of the State of Delaware, without regard to its conflict of laws principles.",
    ])
    def test_incidental_liability_language_does_not_over_fire(self, text):
        assert lpe.extract_liability_facts(text) is None

    def test_determinism_of_discovery(self):
        results = {lpe.extract_liability_facts(NORTHSTAR_LIABILITY_CLAUSE).controlling_provision.raw_excerpt
                    for _ in range(10)}
        assert len(results) == 1


# ---------------------------------------------------------------------------
# P0-4 — Deviation JSON serialization
# ---------------------------------------------------------------------------

TEMPLATE_WITH_FINDINGS = (
    b"STANDARD TEMPLATE AGREEMENT\n\n"
    b"1. LIMITATION OF LIABILITY. In no event shall either party's aggregate liability exceed "
    b"1 times the total annual fees paid.\n\n"
    b"2. TERMINATION. Either party may terminate this Agreement for convenience upon thirty (30) "
    b"days' prior written notice.\n\n"
    b"3. ASSIGNMENT. Neither party may assign this Agreement without the other party's prior "
    b"written consent, which shall not be unreasonably withheld.\n\n"
    b"4. INDEMNIFICATION. Each party shall indemnify the other against third-party claims arising "
    b"from its own gross negligence or willful misconduct.\n"
)

INCOMING_CONTRACT = (
    b"NORTHSTAR MASTER SERVICES AGREEMENT\n\n"
    b"3. LIMITATION OF LIABILITY. Provider's liability shall be unlimited for breaches of "
    b"confidentiality. For all other claims, Provider's aggregate liability shall not exceed five "
    b"times the fees paid under this Agreement.\n\n"
    b"6. ASSIGNMENT. Customer may not assign this Agreement without Provider's prior written "
    b"consent, which Provider may withhold in its sole and absolute discretion.\n\n"
    b"7. GOVERNING LAW. This Agreement shall be governed by, and construed in accordance with, the "
    b"laws of the State of Delaware.\n"
)


class TestP0_4DeviationSerialization:
    def test_compare_output_is_json_serializable(self):
        engine = playbook_engine.PlaybookEngine()
        incoming = [{"rule_id": "A", "title": "A risk", "severity": "high", "matched_excerpt": "x"}]
        template = [{"rule_id": "B", "title": "B protection", "severity": "medium", "matched_excerpt": "y"}]
        result = engine.compare(incoming, template)
        # Before the fix this raised: Object of type Deviation is not JSON serializable
        encoded = json.dumps(result)
        decoded = json.loads(encoded)
        assert decoded["deviation_count"] == 2
        assert decoded["added_risks"][0]["rule_id"] == "A"
        assert decoded["added_risks"][0]["deviation_type"] == "added_risk"
        assert decoded["missing_protections"][0]["rule_id"] == "B"
        assert decoded["missing_protections"][0]["deviation_type"] == "missing_protection"

    def test_zero_deviations_serializes(self):
        engine = playbook_engine.PlaybookEngine()
        same = [{"rule_id": "A", "title": "A", "severity": "high", "matched_excerpt": "x"}]
        result = engine.compare(same, same)
        json.dumps(result)
        assert result["deviation_count"] == 0
        assert result["shared_findings"][0]["severity_changed"] is False

    def test_shared_finding_severity_change_serializes(self):
        engine = playbook_engine.PlaybookEngine()
        incoming = [{"rule_id": "A", "title": "A", "severity": "high", "matched_excerpt": "x"}]
        template = [{"rule_id": "A", "title": "A", "severity": "low", "matched_excerpt": "y"}]
        result = engine.compare(incoming, template)
        json.dumps(result)
        assert result["shared_findings"][0]["severity_changed"] is True

    def test_deviation_to_dict_preserves_every_ui_rendered_field(self):
        d = playbook_engine.Deviation(
            rule_id="R", title="T", severity="high", deviation_type="added_risk",
            description="D", incoming_excerpt="I", template_excerpt="E",
        )
        assert d.to_dict() == {
            "rule_id": "R", "title": "T", "severity": "high", "deviation_type": "added_risk",
            "description": "D", "incoming_excerpt": "I", "template_excerpt": "E",
        }

    def test_upload_against_playbook_with_template_findings_does_not_500(self, client):
        token = _register(client, "p0-4-upload@example.com")
        pb_id = _create_playbook(client, token, name="P0-4 playbook", template_bytes=TEMPLATE_WITH_FINDINGS)
        db = SessionLocal()
        try:
            pb = db.query(Playbook).filter(Playbook.id == pb_id).first()
            assert pb.template_findings_json, "test precondition: template must produce findings"
        finally:
            db.close()

        files = {"file": ("northstar.txt", io.BytesIO(INCOMING_CONTRACT), "text/plain")}
        r = client.post("/upload", data={"csrf_token": token, "playbook_id": str(pb_id)},
                        files=files, follow_redirects=False)
        assert r.status_code in (302, 303), r.text
        contract_id = int(r.headers["location"].rstrip("/").split("/")[-2])

        # Round-trip through the encrypted JSON column, then re-render.
        db = SessionLocal()
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            assert contract.deviations_json is not None
            json.dumps(contract.deviations_json)
        finally:
            db.close()
        assert client.get(f"/contract/{contract_id}/review").status_code == 200
        assert client.get(f"/contract/{contract_id}").status_code == 200

    def test_batch_upload_path_serializes_deviations(self, client):
        token = _register(client, "p0-4-batch@example.com")
        pb_id = _create_playbook(client, token, name="P0-4 batch", template_bytes=TEMPLATE_WITH_FINDINGS)
        files = [
            ("files", ("a.txt", io.BytesIO(INCOMING_CONTRACT), "text/plain")),
            ("files", ("b.txt", io.BytesIO(INCOMING_CONTRACT), "text/plain")),
        ]
        r = client.post("/batch-upload", data={"csrf_token": token, "playbook_id": str(pb_id)},
                        files=files, follow_redirects=False)
        assert r.status_code in (302, 303), r.text
        db = SessionLocal()
        try:
            rows = db.query(Contract).filter(Contract.playbook_id == pb_id, Contract.batch_id.isnot(None)).all()
            assert rows, "batch upload produced no contracts"
            for row in rows:
                json.dumps(row.deviations_json)
        finally:
            db.close()


# ---------------------------------------------------------------------------
# P0-5 — Exception requests cannot bypass reason capture
# ---------------------------------------------------------------------------

class TestP0_5ExceptionReasonRequired:
    @pytest.mark.parametrize("policy_state", ["PROHIBITED", "MUST_REDLINE", "ESCALATE"])
    @pytest.mark.parametrize("action", ["flagged", "dismissed"])
    def test_no_redline_governance_action_requires_reason(self, policy_state, action):
        with pytest.raises(review_workflow.DecisionValidationError):
            review_workflow.validate_decision(
                "R#0", action, has_redline=False, reason="", edited_text="",
                policy_state=policy_state, finding_type="policy_decision",
            )
        with pytest.raises(review_workflow.DecisionValidationError):
            review_workflow.validate_decision(
                "R#0", action, has_redline=False, reason="   \t\n ", edited_text="",
                policy_state=policy_state, finding_type="policy_decision",
            )
        # A real reason is accepted.
        review_workflow.validate_decision(
            "R#0", action, has_redline=False, reason="Business signed off.", edited_text="",
            policy_state=policy_state, finding_type="policy_decision",
        )

    def test_accepting_the_recommendation_needs_no_reason(self):
        review_workflow.validate_decision(
            "R#0", "accepted", has_redline=True, reason="", edited_text="",
            policy_state="MUST_REDLINE", finding_type="policy_decision",
        )

    def test_editing_the_approved_redline_requires_a_reason(self):
        with pytest.raises(review_workflow.DecisionValidationError):
            review_workflow.validate_decision(
                "R#0", "edited", has_redline=True, reason="", edited_text="new language",
                policy_state="PROHIBITED", finding_type="policy_decision",
            )

    def test_non_governance_findings_are_unchanged(self):
        review_workflow.validate_decision("R#0", "flagged", has_redline=False, reason="", edited_text="")
        review_workflow.validate_decision("R#0", "dismissed", has_redline=False, reason="", edited_text="")

    def _contract_with_policy_finding(self, client, token, policy_state, with_redline):
        """Creates a real contract row carrying one governance policy_decision
        finding, so the route (not just the validator) is exercised."""
        files = {"file": ("c.txt", io.BytesIO(INCOMING_CONTRACT), "text/plain")}
        r = client.post("/upload", data={"csrf_token": token}, files=files, follow_redirects=False)
        assert r.status_code in (302, 303), r.text
        contract_id = int(r.headers["location"].rstrip("/").split("/")[-2])
        db = SessionLocal()
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            finding = {
                "rule_id": "POLICY_LOL_CAP", "rule_name": "Limitation of Liability Policy",
                "title": f"Limitation of Liability — {policy_state}", "severity": "critical",
                "rationale": "Cap exceeds policy.", "matched_excerpt": "aggregate liability",
                "start_index": 0, "end_index": 10, "exact_snippet": "aggregate",
                "finding_type": "policy_decision", "finding_type_label": "Policy Decision",
                "policy_state": policy_state, "clause_type": "limitation_of_liability",
                "escalate_to": "General Counsel",
                "redline": {"issue": "i", "legal_rationale": "r", "suggested_redline": "s"} if with_redline else None,
            }
            contract.findings_json = [finding]
            contract.policy_revision_metadata_json = {
                "limitation_of_liability": {"policy_position_id": 4242, "config_hash": "abc123"}
            }
            db.commit()
        finally:
            db.close()
        return contract_id

    @pytest.mark.parametrize("policy_state,with_redline,action", [
        ("ESCALATE", False, "flagged"),
        ("MUST_REDLINE", False, "flagged"),
        ("PROHIBITED", False, "dismissed"),
        ("PROHIBITED", True, "rejected"),
    ])
    def test_route_rejects_reasonless_exception(self, client, policy_state, with_redline, action):
        token = _register(client, f"p0-5-{policy_state}-{with_redline}-{action}@example.com")
        contract_id = self._contract_with_policy_finding(client, token, policy_state, with_redline)
        for reason in ("", "   ", "\t\n  "):
            r = client.post(f"/contract/{contract_id}/review/decision", data={
                "finding_index": 0, "action": action, "reason": reason, "csrf_token": token,
            })
            assert r.status_code == 400, f"reason={reason!r} was accepted: {r.text}"
        db = SessionLocal()
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            assert not (contract.review_decisions_json or {}), "a reasonless exception was recorded"
        finally:
            db.close()

    def test_exception_record_preserves_full_governance_record(self, client):
        token = _register(client, "p0-5-record@example.com")
        contract_id = self._contract_with_policy_finding(client, token, "ESCALATE", with_redline=False)
        r = client.post(f"/contract/{contract_id}/review/decision", data={
            "finding_index": 0, "action": "flagged",
            "reason": "Deal desk approved a one-off exception for this renewal.",
            "csrf_token": token,
        })
        assert r.status_code == 200, r.text
        entry = r.json()["entry"]
        assert entry["policy_original_recommendation"] == "ESCALATE"
        assert entry["action"] == "flagged"
        assert entry["reason"] == "Deal desk approved a one-off exception for this renewal."
        assert entry["decided_by"]
        assert entry["decided_at"]
        assert entry["policy_position_id"] == 4242
        assert entry["policy_config_hash"] == "abc123"

        # Survives reload...
        db = SessionLocal()
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            stored = contract.review_decisions_json["POLICY_LOL_CAP#0"]
            assert stored["reason"] == entry["reason"]
            assert stored["policy_original_recommendation"] == "ESCALATE"
            findings = contract.findings_json
            decisions = contract.review_decisions_json
        finally:
            db.close()

        # ...the history view...
        page = client.get(f"/contract/{contract_id}/review")
        assert page.status_code == 200
        assert "Deal desk approved a one-off exception" in page.text

        # ...and the audit export.
        audit = review_workflow.build_audit_trail_text("c.txt", "2.0.0", findings, decisions)
        assert "Deal desk approved a one-off exception" in audit
        assert "Original policy recommendation: ESCALATE" in audit
        assert "Decided by:" in audit
