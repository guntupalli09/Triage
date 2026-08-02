"""
The real, end-to-end customer journey, executed entirely over HTTP against a
deployed TriageCounsel instance: signup -> login -> upload -> wait for
analysis -> open Review -> read findings -> decide on every finding (accept
/ reject / edit / flag / comment) -> verify persistence survives a refresh
-> Verify -> Finalize -> generate the Negotiation Package -> download the
ZIP -> validate the DOCX independently -> logout.

Every step is a real HTTP call through http_client.LiveSession — see that
module and triagebench_live/__init__.py for why no engine module is ever
imported here. A single contract's failure never raises past this module:
like triagebench/pipeline.py, every step is wrapped so the run can continue
to the next contract, and the record captures exactly what failed and where.
"""
from __future__ import annotations

import io
import time
import traceback
import zipfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import docx_validate
from .corpus_source import UploadPayload, unique_test_email
from .http_client import LiveSession

REDLINE_ACTIONS = {"accepted", "edited", "rejected"}
NO_REDLINE_ACTIONS = {"flagged", "dismissed"}


@dataclass
class StepResult:
    name: str
    status: str = "pending"  # ok | fail | error | skipped
    ms: float = 0.0
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "status": self.status, "ms": round(self.ms, 3), "error": self.error, **self.data}


class _Timer:
    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.ms = (time.perf_counter() - self._t0) * 1000.0


def _run_step(name: str, fn, *args, **kwargs) -> StepResult:
    r = StepResult(name=name)
    try:
        with _Timer() as t:
            data = fn(*args, **kwargs) or {}
        r.status = "ok"
        r.ms = t.ms
        r.data = data
    except AssertionError as exc:
        r.status = "fail"
        r.error = str(exc)
    except Exception as exc:  # noqa: BLE001
        r.status = "error"
        r.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=6)}"
    return r


@dataclass
class ContractWorkflowResult:
    contract_id_hint: str
    category: str
    company_name: str
    filename: str
    test_email: str
    live_contract_id: Optional[int] = None
    steps: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    overall_status: str = "pass"
    failures: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "contract_id_hint": self.contract_id_hint,
            "category": self.category,
            "company_name": self.company_name,
            "filename": self.filename,
            "test_email": self.test_email,
            "live_contract_id": self.live_contract_id,
            "steps": self.steps,
            "metrics": self.metrics,
            "overall_status": self.overall_status,
            "failures": self.failures,
        }


def _auto_decide(finding: Dict[str, Any], index: int) -> Dict[str, Any]:
    """The base policy is the same fixed, documented CI review policy
    triagebench/pipeline.py uses for the in-process benchmark (accept every
    finding with an authored redline, flag everything else) — kept
    identical on purpose so a coverage/decision-count discrepancy between
    the two suites is a real signal, not an artifact of two different
    auto-reviewers disagreeing.

    review_workflow.validate_decision (production's own rule, confirmed by
    a live 400 response during development of this suite) constrains which
    actions are even legal for a given finding: "rejected"/"edited" require
    an authored redline to reject/edit; "flagged"/"dismissed" require that
    none exists. A fixed subset of *within-policy* findings are varied to
    reject-with-reason (has-redline findings) or dismiss (no-redline
    findings) instead of the default, so the workflow genuinely exercises
    every decision action against the real endpoints — not just accept/flag
    — without ever sending a combination the app itself would reject."""
    has_redline = bool(finding.get("redline"))
    if has_redline:
        if index % 5 == 4:
            return {"action": "edited", "edited_text": (finding["redline"].get("suggested_redline") or "Reviewed and revised by TriageBench Live.") + " [benchmark-edited]"}
        if index % 7 == 6:
            return {"action": "rejected", "reason": "TriageBench Live: reviewed and declined — synthetic benchmark decision."}
        return {"action": "accepted"}
    if index % 6 == 5:
        return {"action": "dismissed"}
    return {"action": "flagged"}


def run_contract_workflow(base_url: str, payload: UploadPayload, timeout_s: int = 60) -> ContractWorkflowResult:
    email = unique_test_email()
    password = "TriageBenchLive!2026"
    result = ContractWorkflowResult(
        contract_id_hint=payload.contract_id_hint, category=payload.category,
        company_name=payload.company_name, filename=payload.filename, test_email=email,
    )
    steps = result.steps
    session = LiveSession(base_url, timeout_s=timeout_s)

    # 1. Signup
    s = _run_step("signup", _step_signup, session, email, password)
    steps["signup"] = s.as_dict()
    if s.status != "ok":
        result.overall_status = "error"
        result.failures.append("signup")
        return result

    # 2. Login (a fresh session, proving the credentials just created actually work)
    s = _run_step("login", _step_login, base_url, timeout_s, email, password)
    steps["login"] = s.as_dict()
    if s.status != "ok":
        result.overall_status = "error"
        result.failures.append("login")
        return result
    session = s.data["session"]  # the freshly-logged-in session replaces the signup one

    # 3. Upload + wait for (synchronous) analysis
    s = _run_step("upload_and_analysis", _step_upload, session, payload)
    steps["upload_and_analysis"] = s.as_dict()
    if s.status != "ok":
        result.overall_status = "error"
        result.failures.append("upload_and_analysis")
        return result
    contract_id = s.data["contract_id"]
    result.live_contract_id = contract_id

    # 4. Open report page, verify analysis completed
    s = _run_step("analysis_verification", _step_verify_analysis, session, contract_id)
    steps["analysis_verification"] = s.as_dict()
    if s.status != "ok":
        result.failures.append("analysis_verification")
        result.overall_status = "error" if s.status == "error" else "fail"

    # 5. Open Review page, verify findings loaded
    s = _run_step("review_page_load", _step_review_load, session, contract_id)
    steps["review_page_load"] = s.as_dict()
    if s.status != "ok":
        result.overall_status = "error"
        result.failures.append("review_page_load")
        return result
    findings = s.data["findings"]
    result.metrics["findings_count"] = len(findings)

    # 6. Execute automated review policy: accept/reject/edit/flag + a comment
    s = _run_step("review_decisions", _step_apply_decisions, session, contract_id, findings)
    steps["review_decisions"] = s.as_dict()
    if s.status != "ok":
        result.overall_status = "error" if s.status == "error" else "fail"
        result.failures.append("review_decisions")
    decisions_sent = s.data.get("decisions_sent", {})
    result.metrics.update({
        "accepted": s.data.get("counts", {}).get("accepted", 0),
        "rejected": s.data.get("counts", {}).get("rejected", 0),
        "edited": s.data.get("counts", {}).get("edited", 0),
        "flagged": s.data.get("counts", {}).get("flagged", 0),
        "commented": s.data.get("counts", {}).get("commented", 0),
    })

    # 7. Refresh: verify persistence survived a full page reload (new GET,
    # same session — exactly what hitting F5 does).
    s = _run_step("persistence_after_refresh", _step_verify_persistence, session, contract_id, decisions_sent)
    steps["persistence_after_refresh"] = s.as_dict()
    if s.status != "ok":
        result.overall_status = "error" if s.status == "error" else "fail"
        result.failures.append("persistence_after_refresh")

    # 8. Verify (deterministic replay) — every finding, not just one
    s = _run_step("verify", _step_verify_findings, session, contract_id, findings)
    steps["verify"] = s.as_dict()
    if s.status != "ok" or not s.data.get("all_verified", False):
        result.overall_status = "error" if s.status == "error" else "fail"
        result.failures.append("verify")

    # 9. Finalize
    s = _run_step("finalize", _step_finalize, session, contract_id)
    steps["finalize"] = s.as_dict()
    if s.status != "ok":
        result.overall_status = "error"
        result.failures.append("finalize")
        return result

    # 10. Negotiation Package: generate, download, validate ZIP + DOCX
    #     (native Track Changes, comments, audit report) independently.
    s = _run_step("negotiation_package", _step_package, session, contract_id, decisions_sent)
    steps["negotiation_package"] = s.as_dict()
    if s.status != "ok" or not s.data.get("all_validators_agree", False):
        result.overall_status = "error" if s.status == "error" else "fail"
        result.failures.append("negotiation_package")

    # 11. Logout, then verify the session is actually dead
    s = _run_step("logout", _step_logout, session)
    steps["logout"] = s.as_dict()
    if s.status != "ok":
        result.failures.append("logout")
        result.overall_status = "fail" if result.overall_status == "pass" else result.overall_status

    if not result.failures:
        result.overall_status = "pass"
    return result


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------

def _step_signup(session: LiveSession, email: str, password: str) -> Dict[str, Any]:
    t, resp = session.register(email, password)
    assert t.ok, f"signup did not land on /dashboard (status={t.status_code}, url={resp.url})"
    return {"status_code": t.status_code}


def _step_login(base_url: str, timeout_s: int, email: str, password: str) -> Dict[str, Any]:
    fresh = LiveSession(base_url, timeout_s=timeout_s)
    t, resp = fresh.login(email, password)
    assert t.ok, f"login did not land on /dashboard (status={t.status_code}, url={resp.url})"
    assert fresh.is_authenticated(), "session cookie from login did not authenticate a follow-up request"
    return {"status_code": t.status_code, "session": fresh}


def _step_upload(session: LiveSession, payload: UploadPayload) -> Dict[str, Any]:
    t, resp, contract_id = session.upload(payload.filename, payload.content)
    assert contract_id is not None, f"upload did not redirect to /contract/<id> (status={t.status_code}, url={resp.url})"
    return {"status_code": t.status_code, "contract_id": contract_id}


def _step_verify_analysis(session: LiveSession, contract_id: int) -> Dict[str, Any]:
    t, resp, overall_risk = session.get_report(contract_id)
    assert t.status_code == 200, f"report page returned {t.status_code}"
    assert overall_risk in ("low", "medium", "high", "critical"), f"could not read overall_risk from report page (got {overall_risk!r})"
    return {"overall_risk": overall_risk}


def _step_review_load(session: LiveSession, contract_id: int) -> Dict[str, Any]:
    t, resp, findings, decisions = session.get_review_page(contract_id)
    assert t.status_code == 200, f"review page returned {t.status_code}"
    assert findings is not None, "review page did not embed a FINDINGS array (page markup may have changed)"
    return {"findings": findings, "decisions": decisions or {}}


def _step_apply_decisions(session: LiveSession, contract_id: int, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    decisions_sent: Dict[int, Dict[str, Any]] = {}
    counts = {"accepted": 0, "rejected": 0, "edited": 0, "flagged": 0, "commented": 0}
    failures = []
    for i, f in enumerate(findings):
        decision = _auto_decide(f, i)
        t, resp = session.post_decision(
            contract_id, i, decision["action"],
            reason=decision.get("reason", ""), edited_text=decision.get("edited_text", ""),
        )
        if t.status_code != 200:
            failures.append(f"finding {i}: decision POST returned {t.status_code}")
            continue
        decisions_sent[i] = decision
        counts[decision["action"]] = counts.get(decision["action"], 0) + 1
        if i % 3 == 0:
            ct, cresp = session.post_comment(contract_id, i, f"TriageBench Live automated review note for finding {i}.")
            if ct.status_code == 200:
                counts["commented"] += 1
            else:
                failures.append(f"finding {i}: comment POST returned {ct.status_code}")

    assert not failures, "; ".join(failures[:5])
    return {"decisions_sent": decisions_sent, "counts": counts, "total": len(findings)}


def _step_verify_persistence(session: LiveSession, contract_id: int, decisions_sent: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    t, resp, findings2, decisions2 = session.get_review_page(contract_id)
    assert t.status_code == 200, f"post-refresh review page returned {t.status_code}"
    assert decisions2 is not None, "post-refresh review page had no DECISIONS state"

    # decisions2 keys are opaque server-assigned "{rule_id}#{index}" strings
    # — reconstructing that format would mean depending on review_workflow's
    # exact key scheme, which this HTTP-only package deliberately never
    # imports (see __init__.py). Validate by COUNT
    # and by action-value multiset rather than reconstructing the key format
    # (reconstructing it would require the exact same key-building logic the
    # server uses — out of scope for an HTTP-only test to depend on).
    sent_actions = sorted(d["action"] for d in decisions_sent.values())
    persisted_actions = sorted(d.get("action") for d in decisions2.values())
    assert len(decisions2) == len(decisions_sent), (
        f"decision count after refresh ({len(decisions2)}) != decisions sent ({len(decisions_sent)}) "
        f"— something disappeared or duplicated"
    )
    assert sent_actions == persisted_actions, (
        f"decision actions after refresh do not match what was sent: sent={sent_actions} persisted={persisted_actions}"
    )
    return {"decisions_persisted": len(decisions2), "decisions_sent": len(decisions_sent)}


def _step_verify_findings(session: LiveSession, contract_id: int, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = []
    for i in range(len(findings)):
        t, resp = session.post_verify(contract_id, i)
        ok = t.status_code == 200 and resp.json().get("verified") is True
        results.append({"finding_index": i, "verified": ok, "status_code": t.status_code})
    all_verified = all(r["verified"] for r in results)
    failed = [r["finding_index"] for r in results if not r["verified"]]
    return {"all_verified": all_verified, "verified_count": sum(r["verified"] for r in results),
            "total": len(results), "failed_indices": failed}


def _step_finalize(session: LiveSession, contract_id: int) -> Dict[str, Any]:
    t, resp = session.post_finalize(contract_id)
    assert t.status_code == 200, f"finalize returned {t.status_code}: {resp.text[:300]}"
    body = resp.json()
    assert body.get("progress", {}).get("is_complete"), f"finalize succeeded but progress.is_complete is False: {body}"
    return {"finalized_at": body.get("finalized_at")}


def _step_package(session: LiveSession, contract_id: int, decisions_sent: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    t, resp = session.get_package(contract_id)
    assert t.status_code == 200, f"package download returned {t.status_code}"
    assert resp.headers.get("content-type") == "application/zip", f"unexpected content-type {resp.headers.get('content-type')}"

    zip_check = docx_validate.validate_package_zip(resp.content)
    assert zip_check["ok"], f"negotiation package zip invalid: {zip_check['errors']}"

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    docx_name = next(n for n in zf.namelist() if n.endswith(".docx"))
    docx_bytes = zf.read(docx_name)
    memo_text = zf.read("Cover_Memo.txt").decode("utf-8", errors="replace")
    audit_text = zf.read("Audit_Trail.txt").decode("utf-8", errors="replace")

    expected_redlines = sum(1 for d in decisions_sent.values() if d["action"] in ("accepted", "edited"))
    docx_result = docx_validate.validate_docx(docx_bytes, expected_redline_count=expected_redlines)

    return {
        "package_size_bytes": len(resp.content),
        "docx_size_bytes": len(docx_bytes),
        "zip_check": zip_check,
        "docx_validation": docx_result.as_dict(),
        "all_validators_agree": docx_result.all_validators_agree,
        "memo_has_content": len(memo_text.strip()) > 0,
        "audit_has_content": len(audit_text.strip()) > 0,
        "audit_mentions_unresolved": "UNRESOLVED" in audit_text,
    }


def _step_logout(session: LiveSession) -> Dict[str, Any]:
    t, resp = session.logout()
    assert t.status_code == 200, f"logout returned {t.status_code}"
    still_authenticated = session.is_authenticated()
    assert not still_authenticated, "session remained authenticated after logout"
    return {"session_terminated": True}
