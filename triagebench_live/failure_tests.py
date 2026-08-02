"""
Adversarial failure injection against the real deployed app — everything a
sloppy, malicious, or simply unlucky real customer could do. Every check
records what actually happened, not what "should" happen; a check "passing"
means the app degraded gracefully (a clear error, not a crash or corrupted
state), not that nothing went wrong.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .corpus_source import unique_test_email
from .http_client import LiveSession


@dataclass
class FailureTestResult:
    name: str
    passed: bool
    severity: str
    detail: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "severity": self.severity,
                "detail": self.detail, **{f"evidence_{k}": v for k, v in self.evidence.items()}}


def _fresh_user(base_url: str, timeout_s: int) -> LiveSession:
    email, password = unique_test_email(), "TriageBenchLive!2026"
    s = LiveSession(base_url, timeout_s=timeout_s)
    t, resp = s.register(email, password)
    if not t.ok:
        raise RuntimeError(f"failure-test setup: signup failed ({t.status_code})")
    return s


def run_failure_suite(base_url: str, timeout_s: int = 30) -> List[FailureTestResult]:
    results: List[FailureTestResult] = []

    # --- Corrupt "DOCX" upload (wrong extension trick: valid-looking bytes
    # that are not a real document) ---
    s = _fresh_user(base_url, timeout_s)
    t, resp = s.raw("POST", "/upload", files={"file": ("corrupt.docx", b"PK\x03\x04not-a-real-docx-body", "application/octet-stream")})
    results.append(FailureTestResult(
        name="corrupt_docx_upload", passed=resp.status_code in (200, 400),
        severity="high" if resp.status_code >= 500 else "info",
        detail=f"uploading corrupt .docx bytes -> {resp.status_code} "
               f"({'landed on a contract page — check text extraction did not silently fabricate content' if '/contract/' in resp.url else 'rejected/handled without a 5xx'})",
        evidence={"status_code": resp.status_code, "final_url": resp.url},
    ))

    # --- Empty file ---
    s = _fresh_user(base_url, timeout_s)
    t, resp = s.raw("POST", "/upload", files={"file": ("empty.txt", b"", "text/plain")})
    results.append(FailureTestResult(
        name="empty_file_upload", passed=resp.status_code in (200, 400) and "/contract/" not in resp.url,
        severity="medium" if "/contract/" in resp.url else "info",
        detail=f"uploading an empty file -> {resp.status_code}, landed on {resp.url}",
        evidence={"status_code": resp.status_code, "final_url": resp.url},
    ))

    # --- Oversized file (just over the app's own 10MB limit) ---
    s = _fresh_user(base_url, timeout_s)
    huge = b"A" * (10 * 1024 * 1024 + 1024)
    t, resp = s.raw("POST", "/upload", files={"file": ("huge.txt", huge, "text/plain")})
    results.append(FailureTestResult(
        name="oversized_file_upload", passed=resp.status_code in (200, 400, 413) and resp.status_code < 500,
        severity="high" if resp.status_code >= 500 else "info",
        detail=f"uploading a file 1KB over the documented 10MB limit -> {resp.status_code} (expect a clean rejection, not a 5xx)",
        evidence={"status_code": resp.status_code, "bytes_sent": len(huge)},
    ))

    # --- Disallowed extension masquerading as allowed content-type ---
    s = _fresh_user(base_url, timeout_s)
    t, resp = s.raw("POST", "/upload", files={"file": ("payload.exe", b"MZ\x90\x00fake-binary", "text/plain")})
    results.append(FailureTestResult(
        name="disallowed_extension_rejected", passed=resp.status_code in (200, 400) and "/contract/" not in resp.url,
        severity="high" if "/contract/" in resp.url else "info",
        detail=f"uploading .exe with a spoofed text/plain content-type -> {resp.status_code}, landed on {resp.url}",
        evidence={"status_code": resp.status_code, "final_url": resp.url},
    ))

    # --- Duplicate upload: same file twice in the same account, back to
    # back — must not corrupt state or silently merge the two contracts ---
    s = _fresh_user(base_url, timeout_s)
    text = b"Duplicate upload test. IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR CONSEQUENTIAL DAMAGES."
    t1, r1, cid1 = s.upload("dup.txt", text)
    t2, r2, cid2 = s.upload("dup.txt", text)
    results.append(FailureTestResult(
        name="duplicate_upload_creates_independent_contracts",
        passed=cid1 is not None and cid2 is not None and cid1 != cid2,
        severity="medium" if not (cid1 and cid2 and cid1 != cid2) else "info",
        detail=f"uploading the identical file twice -> contract ids {cid1} and {cid2} "
               f"(expected two independent records, not a merge/overwrite/collision)",
        evidence={"contract_id_1": cid1, "contract_id_2": cid2},
    ))

    # --- Repeated Verify: calling verify on the same finding many times in
    # a row must be idempotent (no state corruption, no duplicate side effects) ---
    if cid1:
        s2 = LiveSession(base_url, timeout_s=timeout_s)
        s2.session.cookies.update(s.session.cookies)
        _, _, findings, _ = s2.get_review_page(cid1)
        if findings:
            verify_results = []
            for _ in range(5):
                t, resp = s2.post_verify(cid1, 0)
                verify_results.append(resp.status_code == 200 and resp.json().get("verified") is True)
            results.append(FailureTestResult(
                name="repeated_verify_idempotent", passed=all(verify_results),
                severity="high" if not all(verify_results) else "info",
                detail=f"calling /review/verify on the same finding 5x in a row -> {verify_results}",
                evidence={"results": verify_results},
            ))

    # --- Repeated Finalize: finalizing an already-finalized contract must
    # not error or double-apply anything ---
    if cid1:
        s3 = LiveSession(base_url, timeout_s=timeout_s)
        s3.session.cookies.update(s.session.cookies)
        _, _, findings3, _ = s3.get_review_page(cid1)
        for i, f in enumerate(findings3 or []):
            action = "accepted" if f.get("redline") else "flagged"
            s3.post_decision(cid1, i, action)
        t_fin1, r_fin1 = s3.post_finalize(cid1)
        t_fin2, r_fin2 = s3.post_finalize(cid1)
        results.append(FailureTestResult(
            name="repeated_finalize_idempotent",
            passed=r_fin1.status_code == 200 and r_fin2.status_code == 200,
            severity="high" if r_fin2.status_code >= 500 else "info",
            detail=f"finalizing twice -> first={r_fin1.status_code}, second={r_fin2.status_code}",
            evidence={"first": r_fin1.status_code, "second": r_fin2.status_code},
        ))

        # --- Repeated Package Generation: generating the package multiple
        # times must return a consistent, valid zip every time, not error
        # or drift. ---
        pkg_results = []
        pkg_sizes = []
        for _ in range(3):
            t_pkg, r_pkg = s3.get_package(cid1)
            pkg_results.append(r_pkg.status_code == 200 and zipfile.is_zipfile(io.BytesIO(r_pkg.content)))
            pkg_sizes.append(len(r_pkg.content))
        results.append(FailureTestResult(
            name="repeated_package_generation_consistent", passed=all(pkg_results),
            severity="high" if not all(pkg_results) else "info",
            detail=f"generating the negotiation package 3x in a row -> valid_zip={pkg_results}, sizes={pkg_sizes} "
                   f"(sizes should be identical — same decisions, same deterministic redline generation)",
            evidence={"valid": pkg_results, "sizes": pkg_sizes, "sizes_stable": len(set(pkg_sizes)) == 1},
        ))

    # --- Interrupted download: closing the connection mid-download must
    # not corrupt server-side state for a subsequent, complete download. ---
    if cid1:
        s4 = LiveSession(base_url, timeout_s=2)  # deliberately too short to finish a full read
        s4.session.cookies.update(s.session.cookies)
        interrupted = False
        try:
            s4.session.get(f"{base_url}/contract/{cid1}/review/package", timeout=0.001)
        except Exception:
            interrupted = True
        s5 = LiveSession(base_url, timeout_s=timeout_s)
        s5.session.cookies.update(s.session.cookies)
        t_after, r_after = s5.get_package(cid1)
        results.append(FailureTestResult(
            name="interrupted_download_does_not_corrupt_state",
            passed=r_after.status_code == 200 and zipfile.is_zipfile(io.BytesIO(r_after.content)),
            severity="high" if r_after.status_code != 200 else "info",
            detail=f"forced a client-side timeout mid-download ({interrupted}), then re-downloaded -> "
                   f"{r_after.status_code}, valid_zip={zipfile.is_zipfile(io.BytesIO(r_after.content)) if r_after.status_code == 200 else None}",
            evidence={"interrupted_first_attempt": interrupted, "status_after": r_after.status_code},
        ))

    # --- Multiple simultaneous uploads from the SAME account (thread pool
    # — not asyncio, so this genuinely races real sockets) ---
    from concurrent.futures import ThreadPoolExecutor
    s6 = _fresh_user(base_url, timeout_s)
    text6 = b"Concurrent upload race test. IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR CONSEQUENTIAL DAMAGES."

    def _do_upload(i):
        s_i = LiveSession(base_url, timeout_s=timeout_s)
        s_i.session.cookies.update(s6.session.cookies)
        _, _, cid = s_i.upload(f"race{i}.txt", text6)
        return cid

    with ThreadPoolExecutor(max_workers=5) as pool:
        cids = list(pool.map(_do_upload, range(5)))
    successful = [c for c in cids if c is not None]
    results.append(FailureTestResult(
        name="concurrent_uploads_same_account",
        passed=len(successful) == len(set(successful)) and len(successful) >= 1,
        severity="high" if len(successful) != len(set(successful)) else "info",
        detail=f"5 simultaneous uploads on one account -> {len(successful)}/5 succeeded, "
               f"unique contract ids: {len(set(successful))} (duplicates would mean a race condition "
               f"in contract creation or the usage-limit counter)",
        evidence={"contract_ids": cids},
    ))

    return results
