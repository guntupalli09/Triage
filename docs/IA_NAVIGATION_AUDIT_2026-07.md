# TriageCounsel — Information Architecture & Navigation Audit (July 2026)

Scope: navigation, information architecture, and workflows only. Conducted as a returning paying customer over multiple sessions (fresh logins, repeated core loops) in a real browser, with an instrumented crawl of every page's links, buttons, breadcrumbs, and header chrome. Technical bugs assumed fixed (this branch).

---

## Scores

| Dimension | Score | Rationale |
|---|---|---|
| Navigation | **7.5/10** | Persistent 3-item app nav + avatar menu covers 90% of intent; report page has conflicting exits; two pages break chrome. |
| Workflow | **6.5/10** | Core loop (login → upload → report → history) is 1–2 clicks and excellent. Playbook creation is a silent dead loop on the default plan; no mistake recovery for reviews. |
| Discoverability | **6/10** | Batch upload, help/FAQ, and share-link controls (password, revoke) are hidden or absent; rows aren't clickable so "View" is the only, small, target. |
| Consistency | **7/10** | App shell is consistent across app pages; `/pricing`, `/contact`, `/faq` switch to marketing chrome mid-task; `/demo` mixes both (shows "Log in" to a logged-in user); "New Review" vs "Upload Contract" name the same action. |
| First-time user | **7.5/10** | Login lands on a dashboard that answers "what do I do" (stats → Upload Contract → empty-state CTA). Playbooks invite an action the free plan forbids. |
| Long-term daily use | **6/10** | Fast re-entry and reopen, but no review deletion/rename, no comparison, no bulk export, no share-link management, filename search only — the workspace doesn't scale with a real caseload. |

**Overall: the skeleton is right** (flat 3-section IA + object pages + avatar menu is exactly the mature-SaaS pattern). What's missing is the object lifecycle around a review (manage, compare, revoke, delete) and three broken/ambiguous edges documented below.

---

## Navigation map (as-built)

```
Marketing chrome (logged-in state shows: … | Dashboard | Logout)
  / (home) ── How It Works · Research · Security · Pricing · Partners · FAQ · About · Contact
  /pricing ─ plan CTAs → POST /subscribe/{plan} (Stripe)
  /demo ──── sample Verification Report (⚠ mixed chrome when logged in)
  /login ⇄ /register ── → /dashboard

App chrome (logo→/dashboard · Dashboard · Reviews · Playbooks ‖ Upgrade→/pricing · +New Review→/upload-page · Avatar▾)
  Avatar▾: Account · Billing · Settings · Support(mailto) · Sign out
  /dashboard ── stats(4) · [Upload Contract][Batch Upload][Manage Playbooks]
  │             Recent Contracts → View→/contract/{id} · PDF · Share ·· "View all"→/history
  /history ──── search · risk filter pills · rows: View · PDF · Share · pagination
  /upload-page ─ file → POST /upload → /contract/{id} ·· "Batch upload →" ·· usage meter → /pricing
  /batch-upload ─ files → POST /batch-upload → /batch/{id} results → download-all zip
  /playbooks ── "Create New Playbook" → /playbooks/new (⚠ silently 302s back when plan gate hit)
  │             [playbook] → edit / delete
  /contract/{id} ─ crumbs: Dashboard / Contract(self ⚠) / Report
  │             top: ‹Dashboard · Export PDF · Share(modal)   bottom: ‹Back to Reviews (⚠ different exit)
  /account ──── profile · change password        (from Avatar or Settings hub)
  /billing ──── plan · usage · View Plans→/pricing · cancel
  /settings ─── hub → Account, Billing · Delete Account (⚠ redundant layer)
Anonymous:
  /shared/{token} ─ read-only report (no revoke/expiry ⚠; password support exists in API, no UI)
```

---

## Hesitation log (each moment I paused = a usability issue)

1. **Playbooks: "Create New Playbook" does nothing.** On the default plan (`playbooks_max = 0`) the button 302s straight back to the list — no message, no upgrade prompt — on a page whose empty state says *"Create your first playbook…"*. This is the worst workflow break in the product: it reads as broken software, and the dashboard promotes "Manage Playbooks" as a co-equal primary action. **Fix:** gate visibly — keep the button, intercept with an upgrade sheet ("Playbooks are available on Starter and above"), and label the plan requirement on the empty state and dashboard tile.
2. **Two different exits from the report.** Top-left says "‹ Dashboard", bottom says "‹ Back to Reviews", breadcrumb offers a third mental model — and the middle crumb ("Contract") links to the page itself. **Fix:** one canonical parent (Reviews), same label top and bottom; make the crumb `Dashboard / Reviews / {filename}` with the self-link dropped and the filename as the leaf.
3. **Rows aren't clickable.** In both Recent Contracts and Reviews, the filename — the thing a user's eye lands on — is inert; the only way in is the small "View" link. **Fix:** whole-row click (or filename link) to open the report; keep View/PDF/Share as secondary row actions.
4. **"Where do I change my password — Settings or Account?"** The avatar menu offers Account *and* Billing *and* Settings, where Settings is just a hub that links back to the other two, plus Delete Account. Three destinations for two jobs. **Fix:** collapse to a single Settings page with Profile / Security / Billing / Danger Zone sections (or tabs), one avatar-menu entry plus Billing if desired.
5. **Two support paths that don't match.** Login page: "Forgot password?" → `/contact` (marketing page). App avatar menu: "Support" → `mailto:`. Neither is in-app help; the FAQ exists only in the marketing footer. **Fix:** one Help destination (`/faq` + contact form) linked as "Help & Support" from the avatar menu; keep mailto as a secondary line on that page.
6. **Upgrading throws you into the marketing site.** "Upgrade" (app chrome) → `/pricing` (marketing chrome) where the Starter CTA reads "Start Reviewing Contracts" — signup copy shown to an existing customer. The way back is the small "Dashboard" header link. **Fix (minimum):** logged-in pricing CTAs become "Choose Starter / Upgrade to Professional"; **better:** an in-app plan-selection view under `/billing`.
7. **`/demo` in a logged-in session is chrome soup.** App nav + a "Log in" link + "Upload → /" + "Back to Reviews" all coexist. **Fix:** logged-in visitors to /demo should get the plain app shell and a "This is a sample report" banner with "Start your own review →".
8. **No way to undo a mistake on a review.** Wrong file uploaded? It consumes quota, sits in Reviews forever, and cannot be deleted or renamed (only the whole *account* can be deleted — the one destructive action offered). **Fix:** per-review Delete (with confirm) and ideally rename/matter-label; decide and document whether deletion refunds the monthly count.
9. **Share links are irrevocable and invisible.** Creating a share link is easy; seeing which reviews are shared, revoking a link, or setting the password **that the API already supports** is impossible. For lawyers sharing risk reports externally this is a real governance gap. **Fix:** share modal gains "Anyone with the link · [Set password] · [Revoke link]"; a "Shared" badge in Reviews rows.
10. **No comparison workflow.** "Compare against playbook" exists only as an option at upload time; two completed reviews can never be compared (e.g., v1 vs v2 of the same NDA after redlines). **Fix (roadmap):** multi-select in Reviews → "Compare" view diffing findings by rule ID (the deterministic engine makes this uniquely credible for this product).
11. **Batch upload is semi-hidden and stylistically foreign.** It's reachable only via a dashboard button and a footnote link on New Review — not from the main nav — and its centered hero-style title breaks the left-aligned app pattern. **Fix:** fold it into New Review as a "Single / Batch" toggle (one upload destination), left-align.
12. **Dashboard has no page title.** Every other app page has an H1; the dashboard opens directly with stat cards (breadcrumb reads "Dashboard"). Minor, but it weakens the "where am I" signal that the rest of the app gets right. **Fix:** add a lightweight H1 ("Good morning, Carla" or just "Dashboard").
13. **Same action, two names.** Header says "New Review"; dashboard button and empty states say "Upload Contract"; the object pages are "Reviews" listing "contracts". Pick one noun pair — recommend **Review** (the deliverable) and keep "contract" only for the file — so: "+ New Review" everywhere, "Reviews" list, report titled by filename.
14. **Report repeats its stats three times.** Rules Loaded/Executed/Triggered appear in the meta strip, Executive Summary, and Rule Execution Summary; counts appear again in Document Health. Daily users scroll past the same numbers. **Fix:** meta strip keeps identity fields; Executive Summary owns counts; drop the Rule Execution Summary card (its unique fields — integrity/deterministic status — move to the top banner, which already shows them).

## What already works (keep)

- Login lands on the dashboard, and the dashboard answers "what now" in one glance: usage (1/3), risk stats, Upload Contract, recent items. Re-entry to yesterday's report is two clicks.
- "+ New Review" is persistent and 1 click from every app page — the single most important shortcut in the product.
- Browser back/forward and refresh behave; `/history?risk=high` filter state survives view-and-return.
- Exports are where users look: on the report (top and bottom) and on every row; batch offers a zip.
- The avatar menu contains everything account-ish; mobile drawer has full nav parity; 404 page offers Home / Dashboard / Support.
- Feedback exists where it matters: profile save, password errors, contact confirmation, quota banners with upgrade CTAs, destructive-action confirms.

## Prioritized recommendations

**Now (breaks trust or strands users):** 1 playbook gate (hesitation #1) · 2 single report exit (#2) · 3 clickable rows (#3) · 4 review delete (#8) · 5 share revoke/visibility (#9).
**Next (coherence):** settings consolidation (#4) · one help path (#5) · logged-in pricing CTAs (#6) · demo chrome (#7) · naming pass (#13) · batch merge into New Review (#11).
**Later (daily-use depth):** review comparison (#10) · report stat dedup (#14) · dashboard H1/greeting (#12) · search beyond filename (party names, clause text) · matter/client tags on reviews.
