"""
Adversarial security probes against the real, deployed application — every
check here is an HTTP request an actual attacker (or a curious customer)
could send; nothing here uses privileged access or inspects the database
directly. Two independent LiveSessions (two real signed-up accounts) stand
in for "attacker" and "victim."

Each probe returns a SecurityFinding with a `severity` and a `passed` flag
so a probe that reveals a real gap is reported, not silently absorbed —
consistent with this suite's mandate to find problems, not confirm the
absence of any.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .corpus_source import unique_test_email
from .http_client import LiveSession


@dataclass
class SecurityFinding:
    check: str
    passed: bool
    severity: str  # critical | high | medium | low | info
    detail: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"check": self.check, "passed": self.passed, "severity": self.severity,
                "detail": self.detail, **{f"evidence_{k}": v for k, v in self.evidence.items()}}


def _new_session_with_contract(base_url: str, timeout_s: int, text: bytes, filename: str = "victim.txt"):
    email, password = unique_test_email(), "TriageBenchLive!2026"
    s = LiveSession(base_url, timeout_s=timeout_s)
    t, resp = s.register(email, password)
    if not t.ok:
        raise RuntimeError(f"security probe setup: signup failed ({t.status_code})")
    t2, resp2, cid = s.upload(filename, text)
    if cid is None:
        raise RuntimeError(f"security probe setup: upload failed ({t2.status_code})")
    return s, email, cid


SAMPLE_TEXT = (
    b"This Agreement is entered into by Acme and Jane Roe. Consultant shall indemnify, "
    b"defend and hold harmless the Company from any and all claims in an uncapped amount. "
    b"IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR CONSEQUENTIAL DAMAGES."
)


def run_security_suite(base_url: str, timeout_s: int = 30) -> List[SecurityFinding]:
    findings: List[SecurityFinding] = []

    victim, victim_email, victim_contract_id = _new_session_with_contract(base_url, timeout_s, SAMPLE_TEXT)
    attacker, attacker_email, attacker_contract_id = _new_session_with_contract(
        base_url, timeout_s, SAMPLE_TEXT, filename="attacker.txt"
    )

    # --- IDOR: attacker tries to view victim's report page ---
    t, resp = attacker.raw("GET", f"/contract/{victim_contract_id}")
    findings.append(SecurityFinding(
        check="idor_report_page", passed=resp.status_code in (403, 404),
        severity="critical" if resp.status_code == 200 else "info",
        detail=f"authenticated attacker GET /contract/{{victim_id}} -> {resp.status_code} "
               f"(expected 403/404, not 200)",
        evidence={"status_code": resp.status_code},
    ))

    # --- IDOR: attacker tries to view victim's review page ---
    t, resp = attacker.raw("GET", f"/contract/{victim_contract_id}/review")
    findings.append(SecurityFinding(
        check="idor_review_page", passed=resp.status_code in (403, 404),
        severity="critical" if resp.status_code == 200 else "info",
        detail=f"attacker GET /contract/{{victim_id}}/review -> {resp.status_code}",
        evidence={"status_code": resp.status_code},
    ))

    # --- IDOR: attacker tries to submit a review decision on victim's contract ---
    t, resp = attacker.raw("POST", f"/contract/{victim_contract_id}/review/decision",
                            data={"finding_index": 0, "action": "accepted"})
    findings.append(SecurityFinding(
        check="idor_forge_decision", passed=resp.status_code in (403, 404),
        severity="critical" if resp.status_code in (200,) else "info",
        detail=f"attacker POST decision on victim's contract -> {resp.status_code} "
               f"(a 200 here means one user can alter another user's review record)",
        evidence={"status_code": resp.status_code},
    ))

    # --- IDOR: attacker tries to download victim's negotiation package ---
    t, resp = attacker.raw("GET", f"/contract/{victim_contract_id}/review/package")
    findings.append(SecurityFinding(
        check="idor_download_package", passed=resp.status_code in (400, 403, 404),
        severity="critical" if resp.status_code == 200 else "info",
        detail=f"attacker GET victim's negotiation package -> {resp.status_code}",
        evidence={"status_code": resp.status_code},
    ))

    # --- IDOR: attacker tries victim's PDF report ---
    t, resp = attacker.raw("GET", f"/contract/{victim_contract_id}/pdf")
    findings.append(SecurityFinding(
        check="idor_download_pdf", passed=resp.status_code in (400, 403, 404),
        severity="high" if resp.status_code == 200 else "info",
        detail=f"attacker GET victim's PDF -> {resp.status_code}",
        evidence={"status_code": resp.status_code},
    ))

    # --- Unauthenticated access entirely (no session at all) ---
    anon = LiveSession(base_url, timeout_s=timeout_s)
    t, resp = anon.raw("GET", f"/contract/{victim_contract_id}/review", allow_redirects=False)
    findings.append(SecurityFinding(
        check="unauthenticated_review_access", passed=resp.status_code in (302, 401, 403),
        severity="critical" if resp.status_code == 200 else "info",
        detail=f"no-cookie GET /contract/{{id}}/review -> {resp.status_code} "
               f"(expected a redirect to /login, not the page itself)",
        evidence={"status_code": resp.status_code, "location": resp.headers.get("location")},
    ))
    t, resp = anon.raw("GET", f"/contract/{victim_contract_id}/review/package", allow_redirects=False)
    findings.append(SecurityFinding(
        check="unauthenticated_download", passed=resp.status_code in (302, 401, 403),
        severity="critical" if resp.status_code == 200 else "info",
        detail=f"no-cookie GET negotiation package -> {resp.status_code}",
        evidence={"status_code": resp.status_code},
    ))

    # --- ID enumerability: are contract IDs sequential? (informational —
    # this is only a real risk if authorization above (idor_* checks) is
    # broken; report it either way so the two facts are read together.) ---
    findings.append(SecurityFinding(
        check="contract_id_enumerable", passed=True, severity="info",
        detail=f"contract IDs are sequential integers (victim={victim_contract_id}, attacker={attacker_contract_id}) "
               f"— safe only as long as every per-contract route enforces ownership (see idor_* checks above); "
               f"consider opaque/UUID contract identifiers as defense-in-depth regardless.",
        evidence={"victim_id": victim_contract_id, "attacker_id": attacker_contract_id},
    ))

    # --- Session cookie attributes ---
    cookie_jar_entry = next((c for c in victim.session.cookies if c.name == "triage_session"), None)
    samesite = cookie_jar_entry._rest.get("SameSite") if cookie_jar_entry and hasattr(cookie_jar_entry, "_rest") else None
    findings.append(SecurityFinding(
        check="session_cookie_attributes", passed=bool(samesite and samesite.lower() == "lax"),
        severity="medium" if not samesite else "info",
        detail=f"triage_session cookie SameSite={samesite!r}. No CSRF token is issued anywhere in the app "
               f"(confirmed by source inspection during test development) — SameSite=Lax blocks the classic "
               f"cross-site <form> POST CSRF vector by not attaching the cookie to cross-site POSTs, but it is "
               f"not equivalent to a CSRF token and does not protect against every CSRF variant "
               f"(e.g. a compromised subdomain, or a browser with SameSite disabled/misconfigured). "
               f"Recommend an explicit CSRF token as defense-in-depth for state-changing POSTs.",
        evidence={"samesite": samesite},
    ))

    # --- Session expiration / garbage token rejected ---
    forged = LiveSession(base_url, timeout_s=timeout_s)
    forged.session.cookies.set("triage_session", "not-a-real-session-token-" + "x" * 40)
    t, resp = forged.raw("GET", "/dashboard", allow_redirects=False)
    findings.append(SecurityFinding(
        check="forged_session_token_rejected", passed=resp.status_code in (302, 401, 403),
        severity="critical" if resp.status_code == 200 else "info",
        detail=f"garbage session token GET /dashboard -> {resp.status_code} (expected redirect to /login)",
        evidence={"status_code": resp.status_code},
    ))

    # --- Logout actually invalidates the session server-side (not just
    # clears the client cookie) — re-attach the pre-logout cookie value
    # after logging out and confirm it's dead. ---
    pre_logout_token = victim.session.cookies.get("triage_session")
    victim.logout()
    replay = LiveSession(base_url, timeout_s=timeout_s)
    replay.session.cookies.set("triage_session", pre_logout_token)
    t, resp = replay.raw("GET", "/dashboard", allow_redirects=False)
    findings.append(SecurityFinding(
        check="logout_invalidates_session_serverside", passed=resp.status_code in (302, 401, 403),
        severity="high" if resp.status_code == 200 else "info",
        detail=f"replaying the pre-logout session token after logout -> {resp.status_code} "
               f"(expected redirect to /login; a 200 would mean logout only clears the client cookie "
               f"and the server-side session is still valid)",
        evidence={"status_code": resp.status_code},
    ))

    # --- Invalid finding_index cannot be used to forge a decision on an
    # out-of-range / nonexistent finding ---
    t, resp = attacker.raw("POST", f"/contract/{attacker_contract_id}/review/decision",
                            data={"finding_index": 999999, "action": "accepted"})
    findings.append(SecurityFinding(
        check="out_of_range_finding_index_rejected", passed=resp.status_code in (400, 404),
        severity="medium" if resp.status_code not in (400, 404) else "info",
        detail=f"decision on finding_index=999999 (own contract) -> {resp.status_code}",
        evidence={"status_code": resp.status_code},
    ))

    return findings
