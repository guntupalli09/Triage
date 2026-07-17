# TriageCounsel — Enterprise UX & Product Audit (July 2026)

**Method.** The full customer journey was exercised in a real Chromium browser against this exact codebase running locally (`DEV_MODE=true`, SQLite, no OpenAI key): registration → dashboard → every nav item → NDA upload (the provided sample, three times) → full results review → export/share → history/search/filters → reopen → billing/settings/account → error states, over-limit states, 404s, refresh, back/forward, keyboard, and mobile (390px). The live site (triagecounsel.com) was unreachable from this environment's network policy, so the audit ran against the same code the site deploys; behavior that differs in production (working Stripe, working LLM explanations) is called out below.

**Product readiness score: 7.5 / 10** (was ~5.5 before the fixes in this branch). The core loop — upload, analyze, read an evidence-backed report — is genuinely good and now presents honestly. The remaining gap to "confidently sell to enterprise legal" is account recovery, async processing feedback, and payment-flow verification on live.

---

## What was fixed in this branch (verified in-browser after each fix)

### Critical
1. **History mislabeled every contract as "Low" risk.** `history.html` read `contract.risk_level`; the model field is `overall_risk`, so the Jinja fallback branch always rendered the Low badge. A lawyer triaging from this list would have been actively misled — the NDA showing "HIGH RISK" in its report showed "Low" in history. Fixed and verified (badge now "High").
2. **Invalid uploads dead-ended on raw JSON.** Uploading a wrong file type / empty / oversized / unparseable file via the browser form returned `{"detail":"Only PDF, DOCX, or TXT"}` as the whole page — no branding, no way back. Single and batch upload now re-render their page with a friendly inline error (and an Upgrade CTA for quota errors). Verified for bad type and over-limit on both single and batch.
3. **Schema initialization only ran under gunicorn.** `init_db()` lived solely in `gunicorn.conf.py`; uvicorn/serverless boots crashed with `no such table: users` on first registration. Now runs in the FastAPI startup hook (create_all is idempotent).
4. **False security claim.** Footers stated "Documents Never Stored" while the product stores full contract text to power History/reopen — a claim any diligence review would flag. Replaced with "Your Documents Stay Private".

### High
5. **"Upload Contract" led signed-in users to the marketing homepage.** `/upload-page` rendered the full landing page (hero, research stats, ICCS badges) with a different header than the app shell; the upload widget sat mid-page under a "Start Free Review" button (wrong for a signed-in customer). Replaced with a dedicated **New Review** page: app shell, breadcrumbs, drag-and-drop (the old page advertised drag-and-drop but had no handlers — it silently didn't work), usage meter ("1 of 3 reviews used this month"), upgrade link, batch-upload cross-link.
6. **Tailwind Play CDN in production.** All pages loaded `cdn.tailwindcss.com` (a browser-side JIT compiler; Tailwind explicitly warns against production use — FOUC, third-party uptime/CSP risk). Replaced with a compiled, minified `static/tailwind.css` (~30KB) scanned from all templates. Regenerate after template changes with:
   `npx tailwindcss@3.4 -c tailwind.config.js -i tw-in.css -o static/tailwind.css --minify` (config: `content: ['templates/**/*.html','static/**/*.js']`, default theme).
7. **Report content read as fake when LLM explanations were unavailable.** Every finding repeated the identical "Analysis" (copy of Reason) and the identical "Negotiation Recommendation" ("Commonly negotiated; consider clarifying scope, caps, and mutuality.") — on an assignment clause and a damages waiver alike. The Execution Pipeline claimed "LLM Explanation Layer — DONE" even when it never ran. Now: duplicated analysis suppressed, canned recommendation removed from the fallback path, pipeline shows **SKIPPED — explanations unavailable** honestly, and "Recommended Manual Review" no longer lists near-duplicates (baseline topics suppressed when a rule-triggered recommendation covers them).
8. **Share used `alert()`/`prompt()`.** Replaced with an accessible modal (read-only URL field, Copy button with "Copied!" feedback, explanation that the link is public read-only, Escape/backdrop close), shared by results and history.

### Medium
9. **Brand fragmentation.** Titles/footers mixed *TriageCounsel AI*, *TRIAGE*, *Triage Counsel*, *TriageCounsel*. Titles standardized on **Triage Counsel**.
10. **Marketing claimed "40 deterministic rules"; the engine ships 64.** Updated everywhere (an understated capability claim is still an inconsistency a buyer will notice next to "Rules Loaded: 64" in the report).
11. **Results page hierarchy.** The 64-cell PASS/FAIL Rule Coverage grid sat *above* the findings, pushing the product's core value below the fold. Findings now lead; Rule Coverage is a collapsed `<details>` below them with a PASS/WARNING/FAIL legend (the semantics were previously unexplained). "Verification Status: HIGH RISK" relabeled **Overall Risk Assessment**; "Missing Sections" → "Provisions Not Detected"; misleading "Rule Coverage 72%" health stat → "Rules Passed 46/64"; decorative fake checkboxes → warning icons.
12. **Terminology drift: nav "Reviews" → page "Contract History".** Page retitled **Reviews**; empty states now end with a CTA (Upload Contract, or Clear search when filtered).
13. **Billing showed "Status: Inactive" on the Free plan** — alarming for a brand-new paying-curious user. Free plan now reads "Free plan — no billing required". Pricing page now mentions the Free tier (3 reviews/month), which previously existed nowhere on the pricing page.
14. **Footer dead links** (Documentation `#`, Blog `#`) removed/redirected.
15. **Auth polish.** Login gained "Forgot password?" (points to contact/support until a real reset ships — see blockers); register states the 8-character minimum and enforces `minlength`.

All 105 existing tests pass. Fixes were each re-verified in the browser (screenshots in session log).

---

## Remaining blockers before I would sell this to enterprise legal teams

1. **No password reset (Critical).** There is no reset flow at all; a locked-out customer is locked out forever. Requires an email provider decision (Resend/Postmark/SES). Implementation sketch: `password_resets` table (user_id, token hash, expires_at), `POST /forgot-password` issuing a 30-min single-use token, email with link, `GET/POST /reset-password/{token}`, invalidate sessions on success. The login page's "Forgot password?" link should then point at it.
2. **Synchronous processing (High).** `/upload` blocks for the full analysis (~5–20s with LLM). The button shows "Analyzing…" with a shimmer, but a slow LLM call risks proxy timeouts and double-submits, and batch "progress" is a simulated timer, not real status. Recommended: create the Contract row in `processing` state, run analysis in a background task, redirect immediately to `/contract/{id}` which polls (or SSE) until complete — this also makes the report page a real loading state.
3. **Live payment flow unverified (High).** Stripe checkout/webhooks couldn't be exercised from this environment. Before launch: run a live-mode test purchase of each plan, confirm plan/limit updates, cancel flow, and webhook signature handling (see STRIPE_* docs in repo).
4. **LLM-path content QA (Medium).** With a working `OPENAI_API_KEY`, confirm per-finding "Analysis"/"Negotiation Recommendation" are genuinely per-finding on the live site, and that the pipeline shows DONE. The fallback path is now honest; the happy path should be spot-checked for quality.
5. **Admin email in source (Low).** `ADMIN_EMAIL` is hardcoded in `main.py`; move to an env var.

## Should fix soon
- **Async/batch results page** polish: batch results table shows per-file risk, but the batch progress bar is cosmetic (see blocker 2).
- **Playbook onboarding**: "Create your first playbook" empty state could link a sample template; the create form is bare.
- **Search** matches filename only; lawyers will expect party names / clause text. Consider indexing contract_text.
- **Report PDF** is plain (Helvetica, no branding); bring it visually in line with the web report — it's the artifact partners forward.
- **Session security**: consider session expiry display, "sign out other sessions", and rate limiting on login.
- **Duplicate uploads** are silently allowed (same file analyzed twice consumes quota). Consider a soft warning ("You reviewed a79a9d79-NDA.docx 5 minutes ago — view that report instead?").

## Nice to have
- Compare two reviews side by side (the data model supports it).
- Self-hosted Inter font files (Google Fonts is still a runtime third-party dependency).
- Per-finding permalink anchors + a sticky in-page nav on long reports.
- Keyboard shortcut (U) for New Review; skip-to-content link.

---

## Area notes (post-fix state)

- **Landing/marketing**: strong, credible, consistent CTAs; research framing is a real differentiator. ✅
- **Onboarding**: register → dashboard works without guidance; dashboard empty state directs to upload. First-run could add a one-time "how it works" strip, but not blocking.
- **Dashboard**: stats, primary actions, recent contracts with correct badges. ✅
- **Upload**: dedicated app page, drag-and-drop works, inline errors, quota meter. ✅ (async processing pending)
- **Results**: leads with risk + findings; evidence (matched text, rule IDs, clause numbers, keywords) is genuinely auditable; honest pipeline; collapsed coverage. ✅
- **History/search/filters**: correct badges, working risk filters (`?risk=high`), search, pagination, empty states with CTAs. ✅
- **Sharing/exports**: PDF exports verified (application/pdf); share modal + anonymous read-only page with disclaimers verified. ✅
- **Billing/settings/account**: coherent; free plan no longer reads as broken. Stripe live flow unverified (blocker 3).
- **Navigation**: no dead ends found post-fix; breadcrumbs consistent; 404 page offers Home/Dashboard/Support. ✅
- **Accessibility**: focus states visible, keyboard nav works across header/nav/table links, share modal closes on Escape; contrast is generally strong (slate palette). Deeper screen-reader pass not performed.
- **Mobile (390px)**: hamburger drawer, stacked report meta, usable upload page. ✅
