"""
Two-session concurrency tests: the same real account, two independent
LiveSessions (independent cookie jars, standing in for two browser tabs or
two different browsers signed into the same account), racing real HTTP
requests against the same contract. This is the part of "no shortcuts" that
matters most here — an in-process benchmark cannot produce a real race
condition between two separate database transactions; only two real,
concurrent HTTP requests against the real server can.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .corpus_source import unique_test_email
from .http_client import LiveSession

SAMPLE_TEXT = (
    b"This Agreement is entered into by Acme and Jane Roe. Consultant shall indemnify, "
    b"defend and hold harmless the Company from any and all claims in an uncapped amount. "
    b"IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR CONSEQUENTIAL DAMAGES."
)


@dataclass
class ConcurrencyResult:
    name: str
    passed: bool
    severity: str
    detail: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "severity": self.severity,
                "detail": self.detail, **{f"evidence_{k}": v for k, v in self.evidence.items()}}


def run_concurrency_suite(base_url: str, timeout_s: int = 30) -> List[ConcurrencyResult]:
    results: List[ConcurrencyResult] = []

    email, password = unique_test_email(), "TriageBenchLive!2026"
    primary = LiveSession(base_url, timeout_s=timeout_s)
    t, _ = primary.register(email, password)
    if not t.ok:
        return [ConcurrencyResult("setup", False, "critical", "could not create shared test account for concurrency suite")]

    t2, _, contract_id = primary.upload("concurrency.txt", SAMPLE_TEXT)
    if contract_id is None:
        return [ConcurrencyResult("setup", False, "critical", "could not upload shared contract for concurrency suite")]

    # Second "tab" for the SAME account: independent LiveSession, but log in
    # again with the same credentials rather than sharing the cookie jar —
    # this is exactly what opening the review page in a second real browser
    # tab / second real browser does (a distinct session token, same user).
    secondary = LiveSession(base_url, timeout_s=timeout_s)
    tl, _ = secondary.login(email, password)
    if not tl.ok:
        return [ConcurrencyResult("setup", False, "critical", "second tab's login failed")]

    # --- Both tabs load the review page before either decides anything ---
    _, _, findings_a, _ = primary.get_review_page(contract_id)
    _, _, findings_b, _ = secondary.get_review_page(contract_id)
    results.append(ConcurrencyResult(
        name="both_tabs_see_same_findings",
        passed=findings_a is not None and findings_b is not None and len(findings_a) == len(findings_b),
        severity="high" if not (findings_a and findings_b and len(findings_a) == len(findings_b)) else "info",
        detail=f"tab A sees {len(findings_a or [])} findings, tab B sees {len(findings_b or [])}",
        evidence={"tab_a_count": len(findings_a or []), "tab_b_count": len(findings_b or [])},
    ))

    if not findings_a:
        return results

    # --- Race: both tabs decide on the SAME finding simultaneously with
    # DIFFERENT actions. There is no "correct" winner — the test is whether
    # the server ends up in a single consistent state (last-write-wins is
    # fine; a torn/corrupted decision record is not). ---
    idx = 0
    has_redline = bool(findings_a[idx].get("redline"))
    # Both actions must be independently legal for this finding (per
    # review_workflow.validate_decision — accepted/edited/rejected require a
    # redline, flagged/dismissed require none) so a 400 on one side reflects
    # a genuine server-side conflict-resolution choice, not an invalid
    # request of TriageBench Live's own making.
    action_a = "accepted" if has_redline else "flagged"
    action_b = "edited" if has_redline else "dismissed"
    extra_b = {"edited_text": "Concurrent-tab edit from TriageBench Live."} if action_b == "edited" else {}

    def _decide(sess, action, extra=None):
        t, resp = sess.post_decision(contract_id, idx, action, **(extra or {}))
        return resp.status_code, action

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_a = pool.submit(_decide, primary, action_a)
        fut_b = pool.submit(_decide, secondary, action_b, extra_b)
        status_a, sent_a = fut_a.result()
        status_b, sent_b = fut_b.result()

    _, _, _, decisions_after = primary.get_review_page(contract_id)
    final_action = None
    if decisions_after:
        # match by rule_id#index using the finding's own rule_id — the same
        # key scheme production uses, without importing review_workflow.
        key = f"{findings_a[idx]['rule_id']}#{idx}"
        final_action = (decisions_after.get(key) or {}).get("action")

    both_accepted = status_a == 200 and status_b == 200
    consistent = final_action in (sent_a, sent_b)
    results.append(ConcurrencyResult(
        name="simultaneous_conflicting_decisions_resolve_consistently",
        passed=both_accepted and consistent,
        severity="critical" if not consistent else "info",
        detail=f"tab A sent '{sent_a}' ({status_a}), tab B sent '{sent_b}' ({status_b}) on the same finding "
               f"simultaneously; server's final recorded action: '{final_action}' "
               f"({'one of the two writes won cleanly' if consistent else 'final state matches NEITHER write — torn/corrupted state'})",
        evidence={"sent_a": sent_a, "sent_b": sent_b, "final_action": final_action, "status_a": status_a, "status_b": status_b},
    ))

    # --- Race: both tabs finalize simultaneously. Must not error, must not
    # double-finalize into an inconsistent state. ---
    for i, f in enumerate(findings_a):
        if i == idx:
            continue
        action = "accepted" if f.get("redline") else "flagged"
        primary.post_decision(contract_id, i, action)

    def _finalize(sess):
        t, resp = sess.post_finalize(contract_id)
        return resp.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_a = pool.submit(_finalize, primary)
        fut_b = pool.submit(_finalize, secondary)
        fin_a, fin_b = fut_a.result(), fut_b.result()

    results.append(ConcurrencyResult(
        name="simultaneous_finalize_no_error",
        passed=fin_a == 200 and fin_b == 200,
        severity="high" if not (fin_a == 200 and fin_b == 200) else "info",
        detail=f"both tabs called finalize simultaneously -> {fin_a}, {fin_b} (both should succeed idempotently)",
        evidence={"status_a": fin_a, "status_b": fin_b},
    ))

    # --- Race: both tabs request the negotiation package simultaneously
    # after finalize — must both get a valid, identical package, not a
    # partial/corrupt one from a race in file/zip construction. ---
    def _package(sess):
        t, resp = sess.get_package(contract_id)
        return resp.status_code, len(resp.content)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_a = pool.submit(_package, primary)
        fut_b = pool.submit(_package, secondary)
        (status_pa, size_a), (status_pb, size_b) = fut_a.result(), fut_b.result()

    # A few bytes of difference is expected and benign: python-docx/OOXML
    # stamp a `dcterms:modified` wall-clock timestamp into docProps/core.xml
    # on every save, so two generations a second apart can legitimately
    # differ by a handful of bytes without either being corrupt. A large
    # delta (content-sized, not timestamp-sized) is the real signal of a
    # race in file/zip construction.
    size_delta = abs(size_a - size_b)
    consistent = status_pa == 200 and status_pb == 200 and size_delta <= 16
    results.append(ConcurrencyResult(
        name="simultaneous_package_generation_consistent",
        passed=consistent,
        severity="high" if not consistent else "info",
        detail=f"both tabs downloaded the package simultaneously -> statuses ({status_pa},{status_pb}), "
               f"sizes ({size_a},{size_b}), delta={size_delta} bytes "
               f"(<=16 bytes tolerated as timestamp jitter in docProps/core.xml)",
        evidence={"status_a": status_pa, "status_b": status_pb, "size_a": size_a, "size_b": size_b, "size_delta": size_delta},
    ))

    return results
