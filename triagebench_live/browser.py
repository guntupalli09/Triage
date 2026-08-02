"""
Real-browser validation via Playwright — the layer HTTP-level testing
(workflow.py, security.py, etc.) cannot cover: does a real browser actually
render the page, submit the real HTML forms, persist the session cookie
across a real navigation/reload, and behave correctly with two real,
independent browser tabs open on the same account.

Every action here drives the real DOM: `page.fill()` into the real named
form inputs (`templates/register.html`, `login.html`, `upload.html`),
`page.set_input_files()` into the real `<input type="file">`,
`page.click()` on the real `.mark` / `.pop-btn[data-act=...]` elements
`templates/review.html`'s own JS renders — never a direct fetch/XHR from
Playwright bypassing the UI (that would just be http_client.py again,
wearing a browser as a costume).

Browser matrix: Chromium ships pre-installed in this environment; Firefox,
WebKit, and a real Edge channel do not, and this suite never fabricates a
result for a browser it did not actually launch — an unavailable browser is
recorded as `skipped`, with the reason, not silently omitted or guessed at.
"""
from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .corpus_source import unique_test_email

SAMPLE_TEXT = (
    "This Agreement is entered into by Acme and Jane Roe. Consultant shall indemnify, "
    "defend and hold harmless the Company from any and all claims in an uncapped amount. "
    "IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR CONSEQUENTIAL DAMAGES."
)

# Pinned to the browser binary actually pre-installed in this environment
# (see repo-level environment notes) — playwright's own bundled version
# metadata does not match it, so `executable_path` is required rather than
# the default `p.chromium.launch()`. In a normal CI image with
# `playwright install` run, CHROMIUM_PATH would simply not exist and the
# default launch path is used instead.
CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


@dataclass
class BrowserStepResult:
    name: str
    status: str  # ok | fail | error | skipped
    detail: str = ""
    ms: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "status": self.status, "detail": self.detail, "ms": round(self.ms, 3)}


@dataclass
class BrowserRunResult:
    browser: str
    available: bool
    steps: List[Dict[str, Any]] = field(default_factory=list)
    overall_status: str = "skipped"

    def as_dict(self) -> Dict[str, Any]:
        return {"browser": self.browser, "available": self.available,
                "steps": self.steps, "overall_status": self.overall_status}


def _launch_kwargs(playwright, browser_name: str) -> Optional[Dict[str, Any]]:
    """Returns launch kwargs if this browser can actually be started in this
    environment, else None (never guessed — actually attempted)."""
    if browser_name == "chromium" and os.path.exists(CHROMIUM_PATH):
        return {"executable_path": CHROMIUM_PATH, "headless": True}
    if browser_name == "chromium":
        return {"headless": True}  # let Playwright try its own bundled path
    if browser_name == "msedge":
        return {"channel": "msedge", "headless": True}
    if browser_name in ("firefox", "webkit"):
        return {"headless": True}
    return None


def _get_launcher(playwright, browser_name: str):
    return {"chromium": playwright.chromium, "msedge": playwright.chromium,
            "firefox": playwright.firefox, "webkit": playwright.webkit}.get(browser_name)


def run_browser_suite(base_url: str, browsers: List[str], timeout_s: int = 30) -> List[BrowserRunResult]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [BrowserRunResult(browser=b, available=False, overall_status="skipped",
                                  steps=[{"name": "playwright_not_installed", "status": "skipped",
                                          "detail": "playwright package is not installed in this environment"}])
                for b in browsers]

    results = []
    with sync_playwright() as p:
        for browser_name in browsers:
            launch_kwargs = _launch_kwargs(p, browser_name)
            launcher = _get_launcher(p, browser_name)
            if launch_kwargs is None or launcher is None:
                results.append(BrowserRunResult(
                    browser=browser_name, available=False, overall_status="skipped",
                    steps=[{"name": "launch", "status": "skipped",
                            "detail": f"{browser_name} is not configured for this environment"}],
                ))
                continue
            try:
                browser = launcher.launch(**launch_kwargs)
            except Exception as exc:  # noqa: BLE001
                results.append(BrowserRunResult(
                    browser=browser_name, available=False, overall_status="skipped",
                    steps=[{"name": "launch", "status": "skipped",
                            "detail": f"{browser_name} could not be launched in this environment: {exc}"}],
                ))
                continue
            try:
                results.append(_run_one_browser(browser, browser_name, base_url, timeout_s))
            finally:
                browser.close()
    return results


def _step(name, fn) -> BrowserStepResult:
    t0 = time.perf_counter()
    try:
        detail = fn() or ""
        return BrowserStepResult(name=name, status="ok", detail=detail, ms=(time.perf_counter() - t0) * 1000)
    except AssertionError as exc:
        return BrowserStepResult(name=name, status="fail", detail=str(exc), ms=(time.perf_counter() - t0) * 1000)
    except Exception as exc:  # noqa: BLE001
        return BrowserStepResult(name=name, status="error", detail=f"{type(exc).__name__}: {exc}",
                                  ms=(time.perf_counter() - t0) * 1000)


def _run_one_browser(browser, browser_name: str, base_url: str, timeout_s: int) -> BrowserRunResult:
    result = BrowserRunResult(browser=browser_name, available=True)
    steps = result.steps
    ms_timeout = timeout_s * 1000

    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(ms_timeout)
    email, password = unique_test_email(f"triagebench-live-{browser_name}"), "TriageBenchLive!2026"

    def do_signup():
        page.goto(f"{base_url}/register", wait_until="domcontentloaded")
        page.fill("#name", "TriageBench Live")
        page.fill("#email", email)
        page.fill("#password", password)
        page.fill("#confirm_password", password)
        page.click("form button[type=submit], form input[type=submit]")
        page.wait_for_url("**/dashboard", timeout=ms_timeout, wait_until="domcontentloaded")
        assert "/dashboard" in page.url, f"signup did not land on /dashboard (at {page.url})"
        return page.url

    s = _step("signup", do_signup)
    steps.append(s.as_dict())
    if s.status != "ok":
        result.overall_status = "error"
        return result

    def do_upload():
        page.goto(f"{base_url}/upload-page", wait_until="domcontentloaded")
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(SAMPLE_TEXT)
            tmp_path = f.name
        try:
            page.set_input_files("#file", tmp_path)
            page.click("#uploadForm button[type=submit], #uploadForm input[type=submit]")
            page.wait_for_url("**/contract/*", timeout=ms_timeout, wait_until="domcontentloaded")
        finally:
            os.unlink(tmp_path)
        assert "/contract/" in page.url, f"upload did not land on a contract page (at {page.url})"
        return page.url

    s = _step("upload_via_real_file_input", do_upload)
    steps.append(s.as_dict())
    if s.status != "ok":
        result.overall_status = "error"
        return result

    contract_url = page.url
    contract_id = contract_url.rstrip("/").split("/")[-1]

    def do_open_review_and_decide():
        page.goto(f"{base_url}/contract/{contract_id}/review", wait_until="domcontentloaded")
        page.wait_for_selector(".mark", timeout=ms_timeout)
        marks = page.query_selector_all(".mark")
        assert marks, "no .mark elements rendered — findings did not load into the DOM"
        marks[0].click()
        page.wait_for_selector(".pop-btn", timeout=ms_timeout)
        btn = page.query_selector(".pop-btn[data-act=accepted]") or page.query_selector(".pop-btn[data-act=flagged]")
        assert btn, "no accept/flag button rendered in the decision popover"
        btn.click()
        page.wait_for_timeout(500)  # let the async postForm() + DOM update settle
        return f"clicked {btn.get_attribute('data-act')} on finding 0"

    s = _step("open_review_and_click_decision", do_open_review_and_decide)
    steps.append(s.as_dict())

    def do_refresh_and_check_persistence():
        decisions_before = page.evaluate("() => Object.keys(DECISIONS).length")
        page.reload(timeout=ms_timeout)
        page.wait_for_selector(".mark", timeout=ms_timeout)
        decisions_after = page.evaluate("() => Object.keys(DECISIONS).length")
        assert decisions_after == decisions_before and decisions_after >= 1, (
            f"decision count before reload ({decisions_before}) != after a real page reload ({decisions_after})"
        )
        return f"{decisions_after} decision(s) survived a real browser reload"

    s = _step("real_page_reload_persistence", do_refresh_and_check_persistence)
    steps.append(s.as_dict())

    def do_second_tab_same_session():
        # A second real tab in the SAME browser context = the same cookie
        # jar, exactly like a user opening a new tab (not a new incognito
        # window) to the same site.
        page2 = context.new_page()
        page2.goto(f"{base_url}/contract/{contract_id}/review", wait_until="domcontentloaded")
        page2.wait_for_selector(".mark", timeout=ms_timeout)
        decisions_tab2 = page2.evaluate("() => Object.keys(DECISIONS).length")
        page2.close()
        assert decisions_tab2 >= 1, "second tab (same session) did not see the decision made in the first tab"
        return f"second tab sees {decisions_tab2} decision(s) made in the first tab"

    s = _step("second_tab_same_session_sees_state", do_second_tab_same_session)
    steps.append(s.as_dict())

    def do_logout():
        page.goto(f"{base_url}/logout")
        page.goto(f"{base_url}/dashboard")
        assert "/login" in page.url, f"dashboard reachable after logout (at {page.url})"
        return "logout redirected /dashboard to /login as expected"

    s = _step("logout", do_logout)
    steps.append(s.as_dict())

    context.close()
    failed = [st for st in steps if st["status"] in ("fail", "error")]
    result.overall_status = "pass" if not failed else ("fail" if all(st["status"] == "fail" for st in failed) else "error")
    return result
