#!/usr/bin/env python3
"""
P0 remediation recheck — a DELTA walkthrough, not a re-run of the original
50-screenshot pass. Drives the same Northstar/Acme scenario end to end
against a live server and captures replacement screenshots for exactly the
five failure points from artifacts/playbook_ux_walkthrough/
ux_walkthrough_report.md.

The test contract is used verbatim from
artifacts/playbook_ux_walkthrough/northstar_msa_test_contract.txt.
"""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path("/home/user/Triage")
OUT = REPO / "artifacts/playbook_ux_walkthrough/p0_remediation_recheck"
CONTRACT = REPO / "artifacts/playbook_ux_walkthrough/northstar_msa_test_contract.txt"
BASE = "http://127.0.0.1:8099"
EMAIL = f"sarah.chen.recheck{int(time.time())}@acme.example.com"
PASSWORD = "Str0ngP@ssw0rd!"

OUT.mkdir(parents=True, exist_ok=True)


def shot(page, name, full_page=True):
    page.wait_for_timeout(350)
    if not full_page:
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(200)
    page.screenshot(path=str(OUT / name), full_page=full_page)
    print("captured", name)


def start_server(mode):
    env = dict(os.environ)
    env["DEV_MODE"] = "true"
    env["POLICY_ENFORCEMENT_MODE"] = mode
    env["DATABASE_URL"] = f"sqlite:///{RECHECK_DB}"
    env["SECURE_COOKIES"] = "false"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8099"],
        cwd=str(REPO), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    import urllib.request
    for _ in range(120):
        try:
            urllib.request.urlopen(BASE + "/", timeout=2)
            return proc
        except Exception:
            time.sleep(0.5)
    proc.kill()
    raise RuntimeError("server did not start")


RECHECK_DB = "/tmp/claude-0/-home-user-Triage/4965a3c1-c3c5-5e7d-8443-b516169bbb9b/scratchpad/recheck.db"


def upgrade_plan(email):
    code = (
        "import os,sys;sys.path.insert(0,'.');"
        "from database import SessionLocal;from models import User;import analytics_models;"
        "db=SessionLocal();u=db.query(User).filter(User.email=='%s').first();"
        "u.plan='professional';db.commit();print('plan ok')" % email
    )
    env = dict(os.environ, DEV_MODE="true", DATABASE_URL=f"sqlite:///{RECHECK_DB}")
    r = subprocess.run([sys.executable, "-c", code], cwd=str(REPO), env=env,
                       capture_output=True, text=True)
    print("upgrade_plan:", r.stdout.strip(), r.stderr.strip()[-400:])


LIABILITY_FIELDS = {
    "preferred_multiplier": "1",
    "acceptable_max_multiplier": "2",
    "negotiate_max_multiplier": "3",
}


def register(page):
    page.goto(BASE + "/register")
    page.fill('input[name="email"]', EMAIL)
    page.fill('input[name="password"]', PASSWORD)
    page.fill('input[name="confirm_password"]', PASSWORD)
    page.fill('input[name="name"]', "Sarah Chen")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def login(page):
    page.goto(BASE + "/login")
    if "/login" not in page.url:
        return  # registration already established the session
    page.fill('input[name="email"]', EMAIL)
    page.fill('input[name="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


TEMPLATE = (
    "ACME STANDARD CUSTOMER MSA (TEMPLATE)\n\n"
    "1. LIMITATION OF LIABILITY. In no event shall either party's aggregate liability under this "
    "Agreement exceed 1 times the total annual fees paid in the twelve (12) months preceding the "
    "claim.\n\n"
    "2. TERM AND TERMINATION. Either party may terminate this Agreement for convenience upon "
    "thirty (30) (30) days' prior written notice, and for material breach upon thirty (30) days' "
    "notice and a fifteen (15) day cure period.\n\n"
    "3. ASSIGNMENT. Neither party may assign this Agreement without the other party's prior "
    "written consent, which shall not be unreasonably withheld, except to an affiliate or in "
    "connection with a merger or sale of substantially all assets.\n\n"
    "4. INDEMNIFICATION. Each party shall indemnify, defend and hold harmless the other against "
    "third-party claims of intellectual property infringement arising from its own materials.\n\n"
    "5. GOVERNING LAW. This Agreement shall be governed by, and construed in accordance with, the "
    "laws of the State of Delaware.\n"
)


def create_playbook(page):
    page.goto(BASE + "/playbooks/new")
    page.fill('input[name="name"]', "Acme Customer MSA Playbook")
    tmpl = Path("/tmp/claude-0/-home-user-Triage/4965a3c1-c3c5-5e7d-8443-b516169bbb9b/scratchpad/acme_template.txt")
    tmpl.write_text(TEMPLATE)
    page.set_input_files('input[type="file"]', str(tmpl))
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    m = re.search(r"/playbooks/(\d+)", page.url)
    return int(m.group(1))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "shadow"
    proc = start_server(mode)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            register(page)
            upgrade_plan(EMAIL)
            login(page)
            pb = create_playbook(page)
            print("playbook", pb)
            run_checks(page, pb, mode)
            browser.close()
    finally:
        proc.terminate()


def fill_liability_form(page, pb):
    page.goto(f"{BASE}/playbooks/{pb}/positions/limitation_of_liability/edit")
    for name, value in LIABILITY_FIELDS.items():
        page.fill(f'input[name="{name}"]', value)
    page.check('input[name="prohibit_unlimited"][value="yes"]')
    page.check('input[name="require_consequential_damages_exclusion"][value="no"]')
    for cat in ("fraud", "confidentiality"):
        box = page.locator(f'input[name="required_exceptions_json"][value="{cat}"]')
        if box.count():
            box.first.check()
    page.select_option('select[name="contract_side"]', "sell_side")
    page.fill('input[name="escalation_approval_authority"]', "General Counsel")
    page.fill('textarea[name="fallback_text"]',
              "Acme approved fallback: aggregate liability capped at 1x fees paid in the prior 12 months.")


def run_checks(page, pb, mode):
    if os.getenv("P0_2_ONLY"):
        fill_liability_form(page, pb)
        page.click('button:has-text("Submit for review")')
        page.wait_for_load_state("networkidle")
        page.click('button:has-text("Approve")')
        page.wait_for_load_state("networkidle")
        try:
            page.click('button:has-text("Activate")')
            page.wait_for_load_state("networkidle")
        except Exception:
            pass
        page.goto(f"{BASE}/playbooks/{pb}/workbench")
        shot(page, f"p0-2-a-workbench-enforcement-disclosure-{mode}.png", full_page=False)
        page.goto(BASE + "/upload-page")
        page.set_input_files('input[type="file"]', str(CONTRACT))
        sel = page.locator('select[name="playbook_id"]')
        if sel.count():
            sel.select_option(str(pb))
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=120000)
        shot(page, f"p0-2-b-review-enforcement-disclosure-{mode}.png", full_page=False)
        return

    # ---------------- P0-1 -------------------------------------------------
    fill_liability_form(page, pb)
    shot(page, "p0-1-a-authoring-filled-before-submit.png")
    page.click('button:has-text("Submit for review")')
    page.wait_for_load_state("networkidle")
    shot(page, "p0-1-b-review-screen-values-preserved.png")

    # approve + activate so the position is ACTIVE
    page.click('button:has-text("Approve")')
    page.wait_for_load_state("networkidle")
    try:
        page.click('button:has-text("Activate")')
        page.wait_for_load_state("networkidle")
    except Exception:
        pass

    # ---------------- P0-3 : Test Policy on the Northstar clause ----------
    clause = (
        "Except for Customer's payment obligations, Provider's liability shall be unlimited for "
        "breaches of confidentiality, data security obligations, intellectual property "
        "infringement, and indemnification obligations. For all other claims, Provider's "
        "aggregate liability shall not exceed five times the fees paid under this Agreement. "
        "Neither limitation shall apply to Provider's gross negligence, willful misconduct, or "
        "fraud."
    )
    page.goto(f"{BASE}/playbooks/{pb}/positions/limitation_of_liability/preview")
    page.fill('textarea[name="sample_text"]', clause)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    shot(page, "p0-3-northstar-clause-classified.png")

    # ---------------- P0-2 : workbench + review enforcement disclosure ----
    page.goto(f"{BASE}/playbooks/{pb}/workbench")
    shot(page, f"p0-2-a-workbench-enforcement-disclosure-{mode}.png", full_page=False)

    # ---------------- P0-4 : upload against a playbook with template findings
    page.goto(BASE + "/upload-page")
    page.wait_for_load_state("networkidle")
    print("upload page url:", page.url, "| has file input:", page.locator('#file').count())
    open("/tmp/claude-0/-home-user-Triage/4965a3c1-c3c5-5e7d-8443-b516169bbb9b/scratchpad/upload_dump.html","w").write(page.content())
    page.set_input_files('input[type="file"]', str(CONTRACT))
    sel = page.locator('select[name="playbook_id"]')
    if sel.count():
        sel.select_option(str(pb))
    shot(page, "p0-4-a-upload-configured.png")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle", timeout=120000)
    shot(page, "p0-4-b-review-loaded-no-500.png")
    print("review url:", page.url)
    shot(page, f"p0-2-b-review-enforcement-disclosure-{mode}.png", full_page=False)

    # ---------------- P0-5 : exception requires a reason ------------------
    contract_id = re.search(r"/contract/(\d+)", page.url).group(1)
    result = page.evaluate(
        """async () => {
            const csrf = document.querySelector('meta[name="csrf-token"]').content;
            const out = [];
            const govIdx = FINDINGS.findIndex(f => f.finding_type === 'policy_decision'
                && ['PROHIBITED','MUST_REDLINE','ESCALATE'].includes(f.policy_state));
            for (const reason of ["", "   "]) {
                const body = new URLSearchParams({finding_index: govIdx, action: 'flagged',
                                                  reason, csrf_token: csrf});
                const r = await fetch(`/contract/${CONTRACT_ID}/review/decision`,
                    {method: 'POST', body, headers: {'X-CSRF-Token': csrf}});
                out.push({reason, status: r.status, detail: (await r.json()).detail});
            }
            return {govIdx, out};
        }"""
    )
    print("P0-5 raw-post results:", result)
    (OUT / "p0-5-a-server-rejects-reasonless-exception.txt").write_text(
        "Direct POSTs to /contract/%s/review/decision, bypassing the UI entirely\n"
        "(this is the bypass path the old HTML-only check could not stop):\n\n%s\n"
        % (contract_id, "\n".join(
            "  reason=%r -> HTTP %s : %s" % (r["reason"], r["status"], r["detail"]) for r in result["out"]))
    )

    # Now show the UI flow: open the governance finding, click Request exception
    page.evaluate("(i) => openFinding(i)", result["govIdx"])
    page.wait_for_timeout(400)
    shot(page, "p0-5-b-governance-finding-actions.png")
    btn = page.locator('#active-popover [data-act="flagged"], #active-popover [data-act="rejected"]').first
    btn.click()
    page.wait_for_timeout(300)
    shot(page, "p0-5-c-reason-required-before-confirm.png")
    # Try to confirm with an empty reason.
    page.locator("#reject-save").click()
    page.wait_for_timeout(300)
    shot(page, "p0-5-d-empty-reason-rejected.png")
    # Provide a real reason.
    page.fill("#reject-textarea",
              "Deal desk and GC approved a one-off exception for the Northstar renewal; "
              "Northstar refused to move and the ARR justifies the risk.")
    page.locator("#reject-save").click()
    page.wait_for_timeout(900)
    shot(page, "p0-5-e-governance-record-after-exception.png")
    page.reload()
    page.wait_for_load_state("networkidle")
    page.evaluate("(i) => openFinding(i)", result["govIdx"])
    page.wait_for_timeout(600)
    shot(page, "p0-5-f-governance-record-survives-reload.png")


if __name__ == "__main__":
    main()
