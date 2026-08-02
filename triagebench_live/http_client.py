"""
The only way TriageBench Live talks to the application: a real HTTP client
with a real cookie jar, exactly like a browser's fetch/form-submit layer.
No route in this module is ever called with knowledge of the server's
internals — every payload is exactly what the real login/upload/review
forms send, every response is parsed the way a browser-side script would
parse it (regex over embedded JSON in the rendered HTML, same as
review.html's own inline `<script>` does with `{{ findings | tojson }}`).

Timing is captured on every call (`LiveSession.timings`) because "how long
did this actually take for a real customer's browser" is itself one of the
things this suite exists to measure — see config.py's performance goals.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import List, Optional

import requests

FINDINGS_RE = re.compile(r"const FINDINGS = (\[.*?\]);\s*\n", re.DOTALL)
DECISIONS_RE = re.compile(r"let DECISIONS = (\{.*?\});\s*\n", re.DOTALL)
CLAUSE_QUALITY_RE = re.compile(r"const CLAUSE_QUALITY = (\{.*?\});\s*\n", re.DOTALL)
OVERALL_RISK_RE = re.compile(r">\s*([A-Z]+)\s*RISK\s*<")
CONTRACT_ID_RE = re.compile(r"/contract/(\d+)")


class LiveError(Exception):
    """Raised for a hard, unexpected HTTP-layer failure (not a validation
    finding — validation findings are recorded on the result record and the
    workflow keeps going; a LiveError means the HTTP call itself couldn't be
    made sense of, e.g. the server is unreachable)."""


@dataclass
class Timed:
    name: str
    ms: float
    status_code: Optional[int] = None
    ok: bool = True


class LiveSession:
    """One customer's browser session: cookie jar + timing log. Each
    LiveSession is independent (its own requests.Session / cookie jar) —
    concurrency.py and security.py rely on that isolation to simulate
    separate real users or separate tabs of the same user."""

    def __init__(self, base_url: str, timeout_s: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.session = requests.Session()
        self.timings: List[Timed] = []
        self.user_email: Optional[str] = None

    def _timed(self, name: str, fn):
        t0 = time.perf_counter()
        resp = fn()
        ms = (time.perf_counter() - t0) * 1000.0
        self.timings.append(Timed(name=name, ms=ms, status_code=getattr(resp, "status_code", None)))
        return resp, ms

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # -- Auth ---------------------------------------------------------

    def register(self, email: str, password: str, name: str = "TriageBench Live", company: str = "TriageBench") -> Timed:
        resp, ms = self._timed("register", lambda: self.session.post(
            self._url("/register"),
            data={"email": email, "password": password, "confirm_password": password,
                  "name": name, "company": company},
            timeout=self.timeout_s, allow_redirects=True,
        ))
        self.user_email = email
        t = Timed("register", ms, resp.status_code, ok=resp.status_code == 200 and "/dashboard" in resp.url)
        return t, resp

    def login(self, email: str, password: str):
        resp, ms = self._timed("login", lambda: self.session.post(
            self._url("/login"), data={"email": email, "password": password},
            timeout=self.timeout_s, allow_redirects=True,
        ))
        self.user_email = email
        t = Timed("login", ms, resp.status_code, ok=resp.status_code == 200 and "/dashboard" in resp.url)
        return t, resp

    def logout(self):
        resp, ms = self._timed("logout", lambda: self.session.get(
            self._url("/logout"), timeout=self.timeout_s, allow_redirects=True,
        ))
        t = Timed("logout", ms, resp.status_code, ok=resp.status_code == 200)
        return t, resp

    def is_authenticated(self) -> bool:
        resp = self.session.get(self._url("/dashboard"), timeout=self.timeout_s, allow_redirects=False)
        return resp.status_code == 200

    # -- Upload / analysis ---------------------------------------------

    def upload(self, filename: str, content: bytes, content_type: str = "text/plain"):
        resp, ms = self._timed("upload", lambda: self.session.post(
            self._url("/upload"), files={"file": (filename, content, content_type)},
            timeout=self.timeout_s, allow_redirects=True,
        ))
        contract_id = None
        m = CONTRACT_ID_RE.search(resp.url)
        if m:
            contract_id = int(m.group(1))
        t = Timed("upload", ms, resp.status_code, ok=contract_id is not None)
        return t, resp, contract_id

    def get_report(self, contract_id: int):
        resp, ms = self._timed("report_page", lambda: self.session.get(
            self._url(f"/contract/{contract_id}"), timeout=self.timeout_s,
        ))
        overall_risk = None
        m = OVERALL_RISK_RE.search(resp.text)
        if m:
            overall_risk = m.group(1).lower()
        t = Timed("report_page", ms, resp.status_code, ok=resp.status_code == 200 and overall_risk is not None)
        return t, resp, overall_risk

    # -- Review workflow -------------------------------------------------

    def get_review_page(self, contract_id: int):
        resp, ms = self._timed("review_page", lambda: self.session.get(
            self._url(f"/contract/{contract_id}/review"), timeout=self.timeout_s,
        ))
        findings, decisions = None, None
        if resp.status_code == 200:
            fm = FINDINGS_RE.search(resp.text)
            dm = DECISIONS_RE.search(resp.text)
            if fm:
                import json
                findings = json.loads(fm.group(1))
            if dm:
                import json
                decisions = json.loads(dm.group(1))
        t = Timed("review_page", ms, resp.status_code, ok=findings is not None)
        return t, resp, findings, decisions

    def post_decision(self, contract_id: int, finding_index: int, action: str,
                       reason: str = "", edited_text: str = ""):
        resp, ms = self._timed("review_decision", lambda: self.session.post(
            self._url(f"/contract/{contract_id}/review/decision"),
            data={"finding_index": finding_index, "action": action, "reason": reason, "edited_text": edited_text},
            timeout=self.timeout_s,
        ))
        t = Timed("review_decision", ms, resp.status_code, ok=resp.status_code == 200)
        return t, resp

    def post_comment(self, contract_id: int, finding_index: int, comment: str):
        resp, ms = self._timed("review_comment", lambda: self.session.post(
            self._url(f"/contract/{contract_id}/review/comment"),
            data={"finding_index": finding_index, "comment": comment}, timeout=self.timeout_s,
        ))
        t = Timed("review_comment", ms, resp.status_code, ok=resp.status_code == 200)
        return t, resp

    def post_verify(self, contract_id: int, finding_index: int):
        resp, ms = self._timed("review_verify", lambda: self.session.post(
            self._url(f"/contract/{contract_id}/review/verify"),
            data={"finding_index": finding_index}, timeout=self.timeout_s,
        ))
        t = Timed("review_verify", ms, resp.status_code, ok=resp.status_code == 200)
        return t, resp

    def post_finalize(self, contract_id: int):
        resp, ms = self._timed("review_finalize", lambda: self.session.post(
            self._url(f"/contract/{contract_id}/review/finalize"), timeout=self.timeout_s,
        ))
        t = Timed("review_finalize", ms, resp.status_code, ok=resp.status_code == 200)
        return t, resp

    def get_package(self, contract_id: int):
        resp, ms = self._timed("review_package", lambda: self.session.get(
            self._url(f"/contract/{contract_id}/review/package"), timeout=self.timeout_s,
        ))
        t = Timed("review_package", ms, resp.status_code, ok=resp.status_code == 200 and resp.headers.get("content-type") == "application/zip")
        return t, resp

    # -- Raw escape hatch for security/failure tests --------------------

    def raw(self, method: str, path: str, **kwargs):
        resp, ms = self._timed(f"raw_{method.lower()}_{path}", lambda: self.session.request(
            method, self._url(path), timeout=self.timeout_s, **kwargs
        ))
        return Timed(f"{method} {path}", ms, resp.status_code), resp
