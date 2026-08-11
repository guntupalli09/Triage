# TriageCounsel Playbook — UX Observation Report

**Persona:** Sarah Chen, Commercial Counsel, Acme Software, Inc.
**Test Playbook:** Acme Customer MSA Playbook (Seller/Vendor side, all six supported clause types configured and Active)
**Test Contract:** Northstar Enterprise Master Services Agreement (`northstar_msa_test_contract.txt`)
**Environment:** Local instance, DEV_MODE=true, SQLite, no OpenAI key configured, `POLICY_ENFORCEMENT_MODE=cutover` (see Finding P0-2 below — this was changed from the shipped default to make the Playbook system enforce at all)

This report is critical by design. Functioning is not the same as good, and several things below function exactly as coded while still being bad for a lawyer using this under time pressure.

---

## Screenshot-by-screenshot notes

### A. Entry / landing experience

**01-dashboard.png**
- Trying to do: Get oriented after login.
- Immediately clear: Plan, usage counter, three primary actions (Upload / Batch / Manage Playbooks), empty state.
- Hesitation: None major. "This Month 0/3" (Free plan) sits next to an "Upgrade" pill with no visible price — a first-time user can't tell what upgrading costs from here.
- Primary CTA obvious: YES (Upload Contract, both header and body).
- Misleading info: None.
- Unnecessary info: None.
- Severity: None.

**02-playbooks-list.png**
- Trying to do: Find/create a Playbook.
- Immediately clear: Empty state, single CTA.
- Hesitation: On the Free plan this screen offers no Playbook creation at all ("Upgrade your plan to create one") — a lawyer who wants to try Playbooks hits a paywall with zero preview of what a Playbook even looks like. There is no sample/demo Playbook to inspect before paying.
- Primary CTA obvious: YES, but it is a paywall, not a create action, on Free.
- Misleading info: None.
- Unnecessary info: None.
- Severity: P2 (reasonable business gating, but zero preview value is a lost-trial opportunity).

**03-create-playbook.png**
- Trying to do: Start a new Playbook.
- Immediately clear: Name, contract type, description.
- Hesitation: **The "Upload Standard Template" box is functionally required** (`<input ... required>`) even though nothing on screen marks it with an asterisk the way "Playbook Name" is marked, and the copy "Upload a file or drag and drop" reads as optional. Submitting without a file silently fails via native HTML5 validation with no visible error — in our first attempt via automation the form just re-rendered blank with no explanation. A lawyer without a template file in hand (which is the entire point of "Manual"/"Build it yourself" setup two screens later) is stuck.
- Primary CTA obvious: YES ("Create Playbook") but it doesn't work without a file the copy implies is optional.
- Misleading info: YES — file upload silently mandatory.
- Unnecessary info: None.
- Severity: **P1** — this blocks the "manual" path the product markets one click later.

**04-setup-method.png**
- Trying to do: Choose how to populate the Playbook.
- Immediately clear: Excellent copy. Each of the three cards states in one sentence what it does, whether it uses AI, and what leaves the server. "Every path below builds the same thing... you can combine paths later" is the single best piece of orientation copy in the whole product.
- Hesitation: None. A first-time lawyer would understand these choices.
- Primary CTA obvious: YES, three clear equal options.
- Misleading info: None found (AI path correctly says "with your explicit consent"; Deterministic path correctly says "never sent to an AI model" — both true, verified against code).
- Unnecessary info: None.
- Severity: None. This is the strongest screen in the product (see Q3 below).

### B. Manual Playbook creation

**05-workbench-empty.png**
- Trying to do: Understand what's left to configure.
- Immediately clear: Coverage 0.0%, 6 "Not configured" cards, "High-impact gaps" chips, one CTA per card.
- Hesitation: None.
- Primary CTA obvious: YES ("Configure →" on every card).
- Misleading info: None.
- Unnecessary info: None.
- Severity: None.

**06/07-liability-authoring-top/bottom.png**
- Trying to do: Encode Acme's liability position.
- Immediately clear: Every numeric field has a plain-English question above it and a one-line explanation below it ("Leave any of these blank if not yet decided — nothing is guessed on your behalf"). This is genuinely good, trustworthy copy.
- Hesitation: The distinction between "Carve-outs that must stay uncapped" (paired with the general cap) and "Required carve-outs from that exclusion" (paired with the consequential-damages exclusion) is subtle — two visually near-identical checkbox rows a few inches apart, easy to fill in the wrong one under time pressure.
- Primary CTA obvious: NO — there are three actions at the bottom of the page (Save draft / Submit for review / Test this policy) with **no visual hierarchy at all**: all three render as plain text-weight links except "Save draft," which is a real button. A lawyer scanning quickly could easily click "Submit for review" thinking it saves their work.
- Misleading info: **YES, seriously** — see Finding P0-1 below. Clicking "Submit for review" without first clicking "Save draft" discards every field you just filled in with no warning, no dirty-state check, and no confirmation dialog.
- Unnecessary info: None.
- Severity: **P0** (see Finding P0-1).

**08-liability-review.png**
- Trying to do: Confirm the position before approving it.
- Immediately clear: "This is the legal position you're approving — not a technical field dump" — plain-English summary of exactly what will be enforced.
- Hesitation: None once data is actually saved (see P0-1 — the first time we hit this screen, every line read "Not yet decided" because we hadn't clicked Save draft first, which is confusing and looks like a bug in the *review* screen even though the bug is on the *previous* screen).
- Primary CTA obvious: YES ("Approve this position").
- Misleading info: None on this screen itself.
- Unnecessary info: None.
- Severity: None (screen itself is well designed).

**09-liability-active.png**
- Trying to do: Confirm the position is live.
- Immediately clear: Green "Active" badge, one-line enforcement summary, coverage moved to 16.7%.
- Hesitation: None.
- Primary CTA obvious: YES ("Open →", "Test policy →").
- Misleading info: None.
- Unnecessary info: None.
- Severity: None.

**10–14 (Indemnification / Termination / Confidentiality / Assignment / Governing Law authoring)**
- Trying to do: Configure the remaining five clauses.
- Immediately clear: Same authoring pattern as Liability throughout — consistent and learnable once you've done one.
- Hesitation: Field *support* is uneven and not obvious until you look: e.g. Termination has separate "notice days" and "cure days" inputs but no way to express "no termination fee contemplated" other than leaving three fee-multiplier fields blank, which reads identically to "not yet decided." Governing Law's jurisdiction fields are free-text with no autocomplete/canonicalization — "Delaware," "DE," and "the State of Delaware" are three different strings to the matcher (confirmed against `governing_law_policy_engine.py`).
- Primary CTA obvious: Same Save/Submit/Test hierarchy problem as Liability (P0-1 territory) on every one of these five pages — untested individually but the template (`playbook_position_edit_base.html`-style) is shared, so the risk is systemic, not a one-off.
- Misleading info: None additional beyond the shared risk above.
- Unnecessary info: None.
- Severity: P1 (the field-support opacity), P0 shared with above.

### C. Completed Playbook

**15/16-workbench-complete-top/bottom.png**
- Trying to do: Confirm the Playbook is ready to use.
- Immediately clear: "6 Active / 0 Needs review / 0 Not configured," "All supported clause types are Active," 100.0% coverage, all six cards green.
- Hesitation: None — this is a clean, confidence-inspiring screen.
- Primary CTA obvious: YES (Open / Test policy per card).
- Misleading info: **Indirectly yes** — "100% coverage" and "Active" imply the policy is now live and enforcing. As Finding P0-2 shows, in this environment's *shipped default configuration* (`POLICY_ENFORCEMENT_MODE=shadow`), an Active Playbook like this one enforces **nothing** on real contract review — it is silently evaluated in the background for audit-log comparison only. Nothing on this screen, or anywhere in the six authoring screens, says "this only takes effect once your operator flips a server-side switch."
- Unnecessary info: None.
- Severity: **P0** (see Finding P0-2 — this is the single biggest trust gap in the product).

### D. Test Policy

**17-test-policy-empty.png**
- Trying to do: Sanity-check the Liability position against sample language.
- Immediately clear: "PREVIEW ONLY — nothing here is saved," example placeholder text.
- Hesitation: None.
- Primary CTA obvious: YES.
- Misleading info: None.
- Severity: None.

**18-test-policy-input.png**
- Trying to do: Paste the adverse Northstar liability clause and check it.
- Immediately clear: Text pasted correctly, ready to run.
- Severity: None.

**19-test-policy-result.png**
- Trying to do: See how Acme's policy treats this clause.
- Immediately clear: Result is unambiguous — "NOT APPLICABLE."
- Hesitation: **Major.** The pasted paragraph is, in plain English, exactly the kind of clause the policy exists to catch (unlimited liability for confidentiality/data-security/IP/indemnification breaches). The tool says "No limitation-of-liability clause found... this contract does not address liability caps." A lawyer testing their own policy against the single most adverse clause they're likely to see would reasonably conclude their policy doesn't work, or that the tool is broken. See Finding P0-3.
- Primary CTA obvious: N/A (no action to take on a NOT_APPLICABLE result).
- Misleading info: **YES** — "this contract does not address liability caps" is false; it's the anchor-phrase-matching that's missing, not liability language.
- Unnecessary info: None.
- Severity: **P0** (see Finding P0-3).

(No 20-test-policy-evidence.png — see contact sheet note; there is no evidence section to expand on a NOT_APPLICABLE result.)

### E. Contract upload

**21-contract-upload.png / 22-contract-upload-configured.png**
- Trying to do: Upload the counterparty contract and pick the Playbook to compare against.
- Immediately clear: Both states are simple and correct. "0 of 150 reviews used this month" is accurate once on a paid-equivalent plan.
- Hesitation: None.
- Primary CTA obvious: YES.
- Misleading info: None.
- Severity: None. (This screen also nearly caused a hard **P0 crash** — see Finding P0-4 — which is not visible in these two screenshots but is documented below because a lawyer hitting it would see only a raw 500 error page with no recovery path.)

### F. Processing

**23-processing.png**
- Trying to do: Wait for analysis.
- Immediately clear: There is effectively nothing to see — analysis is fully synchronous server-side and the browser jumps straight from click to the completed review screen. We attempted to capture an intermediate frame at multiple timing offsets (30ms after click, at navigation-commit, and via the button's own "Analyzing…" JS state) and never observed anything other than either the pre-click form or the fully-rendered result.
- Hesitation: For a lawyer, a review that appears "instantly" for a document with 20 findings across a full MSA may itself read as suspicious ("did it actually read the whole thing?") — there is no per-clause progress indicator or even a spinner to signal work happened.
- Primary CTA obvious: N/A.
- Misleading info: None (it isn't hiding a real process — it genuinely is that fast).
- Unnecessary info: None.
- Severity: P3 (cosmetic/trust polish only).

### G. Contract review — MOST IMPORTANT

**24-review-first-impression.png**
- Trying to do: Understand, at a glance, what's wrong with this contract and what needs Sarah's attention first.
- Immediately clear: Six compact policy-exception banners sit directly above the contract text, color-coded and labeled (ESCALATE / MUST REDLINE / PROHIBITED / REQUIRES REVIEW ×3 / ACCEPT), each naming the clause, the counterparty's actual language, and Acme's own policy limit, in one line. This is a genuinely strong "review by exception" first screen.
- Hesitation: The right-hand panel auto-opens an *ordinary* rule-engine finding ("Asymmetric liability cap," MEDIUM confidence) rather than the actual highest-severity item (Termination, PROHIBITED, critical, requires General Counsel). The most urgent thing in the document is not what a lawyer's eye is drawn to on open.
- Primary CTA obvious: NO — with 20 unresolved items and 6 policy exceptions plus a right panel already showing "Accept/Edit/Reject" for something else, it isn't obvious where to start. There's no "start with the most severe item" affordance.
- Misleading info: None.
- Unnecessary info: The colored inline number badges (7,1,4,14,5 etc. — one per matched rule) inside the contract text are dense and, on first look, read like clutter rather than useful anchors, though they do work once explained.
- Severity: P1.

**25-review-exception-queue.png**
- Trying to do: Triage the governance-relevant items specifically.
- Immediately clear: "3 need attention / 3 Prohibited·Must Redline·Escalate / 1 Passed," each row showing Counterparty vs. Your playbook with a one-line rationale and an "Escalate to General Counsel" chip where relevant. This is the best screen in the product for a lawyer under time pressure (see Q3).
- Hesitation: None.
- Primary CTA obvious: YES (each row is clickable).
- Misleading info: None.
- Unnecessary info: None.
- Severity: None.

**26-review-other-findings.png**
- Trying to do: See the non-policy findings.
- Immediately clear: Plain list of titles, no severity color visible in this collapsed list view (severity only shows once opened).
- Hesitation: "Landlord assignment/sublet consent lacks reasonableness standard" is a **lease-specific rule firing on an MSA** — a visibly wrong/mismatched rule for this document type, which undermines confidence in the rest of the "Other Contract Findings" list. See Finding P2-1.
- Primary CTA obvious: YES (clickable rows).
- Misleading info: The lease-rule finding, see above.
- Unnecessary info: Rule taxonomy leakage (a landlord/tenant rule appearing at all) reads as noise.
- Severity: P2.

**27/28-review-passed-collapsed/expanded.png**
- Trying to do: Confirm what's fine so it can be ignored.
- Immediately clear: "▸ 1 policy check passed," expands to "Governing Law: Jurisdiction: Delaware... within policy (Delaware)."
- Hesitation: None functionally, but note this state was **not naturally reachable** with the spec's original adverse-only test contract — see Finding P2-2 (the governing-law extractor needed comma-punctuated boilerplate to parse "governed by, and construed in accordance with, the laws of the State of Delaware" — the more common unpunctuated phrasing, "governed by and construed in accordance with the laws of," failed to parse at all).
- Primary CTA obvious: N/A (informational only).
- Misleading info: None once reached.
- Severity: P2 (extractor brittleness, not this screen's fault).

### H. Severe exception

**29-prohibited-finding.png**
- Trying to do: Understand exactly why Termination is PROHIBITED and what to do.
- Immediately clear: State badge, rule ID, counterparty position vs. Acme's playbook position side by side, "Requires approval from General Counsel" banner, a ready-made redline diff, and four clear actions.
- Hesitation: None — this is a complete, well-organized finding card.
- Primary CTA obvious: YES ("Apply approved redline" is styled primary/green).
- Misleading info: None.
- Unnecessary info: None.
- Severity: None.

**30-why-this-decision.png / 31-contract-evidence.png / 32-playbook-policy.png**
- Trying to do: Audit the reasoning behind the decision (this is the deterministic-evidence promise of the whole product).
- Immediately clear: All three sections are real, all three are populated with real, specific, traceable text — not templated boilerplate. "Contract evidence" literally states "Controlling provision → Termination treatment → Playbook source → Result," in that causal order.
- Hesitation: Minor — the three sections ("Why this decision?", "Contract evidence," "Playbook evidence") overlap somewhat in content (the explanation text is nearly duplicated between "Why" and "Contract evidence"), so a lawyer expanding all three gets some repetition rather than three genuinely distinct layers of information.
- Primary CTA obvious: N/A (these are disclosure toggles, not actions).
- Misleading info: None.
- Unnecessary info: Some duplication as noted above.
- Severity: P3.

(No 33-negotiation-guidance.png — see contact sheet note. There is no separate control; the negotiation ladder lives inside "Playbook evidence.")

### I. Redline

**34-redline-before.png**
- Trying to do: Review the suggested replacement language before accepting it.
- Immediately clear: Struck-through original vs. green replacement text, side by side in a monospace diff box.
- Severity: None.

**35-redline-after.png**
- Trying to do: Confirm the redline was applied.
- Immediately clear: Progress counter moved from "0 of 20" to "1 of 20 resolved."
- Hesitation: **Whether the contract itself visibly changed is only moderately obvious.** The affected clause text in the document body gets a grey strikethrough marker and the resolved-item tick on the margin timeline turns from orange to grey, but the *actual accepted redline text is not inserted into the document body* — only the original is struck through in place; the approved replacement language is visible only inside the (now-closed) finding panel, not inline in the contract view. A lawyer scanning the document after accepting several redlines would see a document full of strikeouts but not the accepted new language, unlike a Word Track Changes view.
- Primary CTA obvious: N/A (post-action state).
- Misleading info: The visual signal ("something changed here") is real but doesn't show *what* it changed to without reopening the finding.
- Severity: P1.

### J. Exception / escalation

**36-request-exception.png**
- Trying to do: Grant an exception on a governance-grade finding.
- Immediately clear: "Request exception" button present and clearly governance-labeled.
- Severity: None.

**37-exception-reason.png**
- Trying to do: Provide a reason before confirming.
- Immediately clear: Reason textarea with a placeholder explicitly stating "goes in the audit record," "Confirm exception" / "Cancel."
- Severity: None — **when this step is reachable at all** (see Finding P0-5, next).
- Important undisclosed fact discovered during testing: **"Request exception" only opens this reason textarea when the underlying policy position has approved fallback/redline text.** For a governance-grade finding whose policy position has *no* `fallback_text` configured — which was true for both our Limitation of Liability (ESCALATE) and Indemnification (MUST_REDLINE) decisions — clicking the identically-labeled "Request exception" button **submits the exception immediately, with zero reason captured, no confirmation, and no undo.** We reproduced this directly: on the Limitation of Liability finding, "Request exception" fired instantly and the queue row shows "✓ Exception requested" with no reason ever entered (visible in 38-exception-approved-row.png, top card). See Finding P0-5.

**38-exception-approved-row.png**
- Trying to do: Confirm the exception was recorded.
- Immediately clear: "✓ Exception granted" badge on Termination (which *did* go through the reason flow) and "✓ Exception requested" badge on Limitation of Liability (which did **not** — no reason was ever entered for it, by design of the current code, not by tester error).
- Misleading info: Both badges look identical in weight/color and give no visual signal that one carries a documented reason and the other carries none.
- Severity: **P0** (see Finding P0-5).

**39-exception-history.png**
- **Not captured as a separate numbered file.** The governance record (original recommendation → decision → reviewer/timestamp → reason) is not a separate "reopen" screen — it renders inline inside the finding's own detail popover as soon as any decision exists (visible at the bottom of 36/38-adjacent panel states). We did not fabricate a distinct "history" screen since none exists separately from the finding detail view already captured in 29/36.

### K. Verify

**40-policy-verify.png**
- Trying to do: Confirm the finding is deterministic and reproducible, not a one-off/LLM artifact.
- Immediately clear: "✓ Re-ran your policy against this contract using the exact approved policy revision. Result: PROHIBITED. Same result, every time." This is exactly the trust-building message the product's "deterministic rule engine" promise needs, and it is real — not a canned string; it re-executes the pinned policy revision.
- Hesitation: None.
- Primary CTA obvious: N/A (confirmatory, not actionable).
- Misleading info: None.
- Severity: None. This is one of the strongest individual interactions in the product.

### L. Finalize / export

**41-finalize-review.png**
- Trying to do: Confirm the review is complete and ready to finalize.
- Immediately clear: Status chip changes to green "Ready to finalize," "Finalize Review" button becomes enabled, "20/20 resolved."
- Severity: None.

**42-export-options.png / 43-review-complete.png**
- Trying to do: Finish the review and get a deliverable to send out.
- Immediately clear: A green checkmark, "Review complete," an estimated-time-saved line, "Run it again — verify determinism," and "Generate Negotiation Package →" (a single ZIP containing a Track-Changes-style DOCX, a cover memo, and an audit trail — genuinely useful, real content, verified by opening the generated file).
- Hesitation: **The "Finalize Review" click does not visually replace the review screen.** The completion banner is appended *below* the entire, still-fully-rendered, still-fully-interactive original review UI (findings panel, "Finalize Review" button still present and clickable, margin map still there) — the CSS class that's supposed to hide the review screen on finalize (`#review-screen`) has no matching stylesheet rule, so nothing actually hides. A lawyer has to scroll past their entire redlined contract again to find the "done" state, and the two screenshots the spec asked for (42 "before submitting"/"export options" and 43 "review complete") are, on the real running app, **the same screen** — there is no separate options/format-picker step; "Generate Negotiation Package" is the only export action and it is a single fixed bundle, not a chooser.
- Primary CTA obvious: Muddled by the above — two "Finalize Review" buttons (topbar, now vestigial, and the completion state) are simultaneously present.
- Misleading info: The still-visible, still-clickable original "Finalize Review" button after finalization is misleading (implies you can finalize again / haven't finished).
- Unnecessary info: The entire redlined document re-displayed above the completion banner is unnecessary at this point.
- Severity: **P1** (functional but confusing/duplicated state; the underlying export itself works and is good).

### M. Deterministic import UX

**44-deterministic-upload.png**
- Trying to do: Understand what deterministic import will and won't do before uploading.
- Immediately clear: "DETERMINISTIC & PRIVATE — no document content is ever sent to an AI model," a plain-English "What extraction can and can't do" explainer with a worked example, and an explicit cross-link to AI-assisted import for prose memos. This is honest, well-written, unusually candid product copy.
- Severity: None.

**45-deterministic-options.png**
- Trying to do: Pick what the uploaded contract should be used for.
- Immediately clear: Two independent checkboxes (deviation baseline / policy extraction) plus a contract-side selector, each with a one-line explanation.
- Severity: None.

**46-deterministic-processing.png**
- Trying to do: Wait for extraction.
- Immediately clear: Nothing — same synchronous-processing gap as contract analysis (F. above); captured a blank transitional frame.
- Severity: P3 (same cosmetic note as Section F).

**47-deterministic-review.png**
- Trying to do: Review what the extractor found before accepting anything.
- Immediately clear: "Every position below is a DRAFT proposal... nothing here is enforced until you review and activate it," per-clause "Directly established" vs. "Needs your input" split.
- Hesitation: Only 3 of the 6 configured clause types (Limitation of Liability, Termination, Governing Law) produced any draft positions at all from the Northstar contract; Confidentiality, Assignment, and Indemnification produced nothing, with **no visible explanation on this screen of why those three are simply absent** (as opposed to present-but-empty). A lawyer would not know whether the extractor tried and found nothing, or didn't try.
- Primary CTA obvious: YES ("Open clause card →").
- Misleading info: The silent omission of 3 of 6 clause types, above.
- Unnecessary info: None.
- Severity: P2.

**48-deterministic-missing-fields.png**
- Trying to do: See what still needs a human decision.
- Immediately clear: "NEEDS YOUR INPUT... These are unanswered — not answered 'no,' not permissive by default." Excellent, unambiguous copy — directly answers "did it guess?" with "no."
- Severity: None.

**49-deterministic-source-evidence.png**
- Trying to do: Verify an extracted value against the actual source text.
- Immediately clear: "View evidence" expands to the literal source excerpt ("five times the fees") the value was derived from.
- Severity: None. This — combined with 40 (Verify) and 31 (Contract evidence) — is the strongest evidence chain in the product (see Q7).

### N. AI-assisted import UX

**50-ai-import-disabled.png**
- Trying to do: Try the AI-assisted path.
- Immediately clear: "AI-assisted import is disabled for this server... An administrator has not enabled this feature. Deterministic/private template import remains fully available and never uses AI," with a direct link back to the working path.
- Hesitation: None — this is a clean, honest, non-broken disabled state (real, unmodified `AI_ASSISTED_IMPORT_ENABLED` env var, left unset).
- Primary CTA obvious: YES.
- Misleading info: None.
- Severity: None.

---

## Critical findings not tied to a single screenshot

**Finding P0-1 — "Submit for review" silently discards unsaved work.**
On every one of the six clause-authoring pages, the bottom of the page presents three actions with equal visual weight: "Save draft" (a real button), "Submit for review" (a plain text link), "Test this policy against sample text" (a plain text link). `Submit for review` is a separate POST endpoint (`/positions/{clause_type}/submit-for-review`) that reads **only the already-persisted database row** — it does not read the form. If a lawyer fills in the entire Liability form and clicks "Submit for review" without first clicking "Save draft," every field reverts to "Not yet decided" / "None specified" with no warning, no confirmation dialog, and no way to recover the typed values. We hit this ourselves on the very first clause we configured. This directly contradicts the reassuring copy elsewhere in the product ("nothing is guessed on your behalf") — here, something worse than guessing happens: real input is silently thrown away.

**Finding P0-2 — Activated Playbooks do not enforce anything by default.**
`policy_enforcement.py` ships with `POLICY_ENFORCEMENT_MODE` defaulting to `"shadow"`. In shadow mode, the six-clause Policy Workbench system this entire product surface is built around — the one Sarah spends an hour configuring across screens 05–16 — has **zero effect on real contract review**. Production's user-visible result comes only from a legacy, single-clause (`limitation_of_liability`-only) `PolicyRule` table that isn't even populated by the "Build it yourself" manual flow used in this walkthrough. We confirmed this directly: with the shipped default, uploading the adverse Northstar contract against a fully-Active, 6/6-configured Playbook produced **zero policy findings** — none of the six "Active" clause cards had any effect on the review at all, despite every card in screens 09/15/16 showing a green "Active" badge and "100% coverage." Nothing in the Workbench UI, the clause-authoring screens, or the "Active" badge itself discloses that server-side enforcement might be off. We set `POLICY_ENFORCEMENT_MODE=cutover` via `.env` purely to be able to complete this walkthrough at all — this is an environment/ops change, not something reachable through the UI by a lawyer, and it is documented here rather than silently worked around.

**Finding P0-3 — The Liability engine's clause detector needs a specific anchor phrase, not liability language.**
`liability_policy_engine.py`'s `_ANCHOR_RE` is `r"limitation\s+of\s+liability|liability\s+cap"` — it will not recognize a clause as being about liability at all unless one of those two literal phrases appears. The adverse paragraph the task spec itself mandates verbatim ("Except for Customer's payment obligations, Provider's liability shall be unlimited for breaches of confidentiality...") contains neither phrase and, tested in isolation via "Test Policy," is reported as "No limitation-of-liability clause found... this contract does not address liability caps" — a materially false statement about a paragraph whose entire content is a liability limitation. In the full contract, this paragraph only worked because we placed it under a "3. LIMITATION OF LIABILITY." heading, which supplied the anchor. A lawyer testing policy language pasted from an actual redline exchange (which frequently omits section headings) would get a false "not applicable" result on genuinely adverse liability language.

**Finding P0-4 — Uploading a contract against a Playbook with a non-empty uploaded "template" crashes with an unhandled 500.**
Every Playbook's *creation* form requires uploading a "Standard Template" file (see 03-create-playbook.png), which is independently run through the rule engine and stored as `template_findings_json`. If that file produces any findings (realistic template contract text virtually always will), then later comparing an uploaded contract against that Playbook triggers `playbook_engine.compare()`, which returns raw Python `Deviation` dataclass instances inside the result dict; `main.py` stores that dict directly into an encrypted JSON column without serializing the dataclasses first, raising `TypeError: Object of type Deviation is not JSON serializable` and returning a raw, unstyled "Server Error" page with no recovery path — the upload is lost, the review never created. We hit this on our very first real upload attempt. We worked around it, without touching application code, by re-uploading a deliberately content-free placeholder file via the Playbook's Edit screen to clear `template_findings_json` back to empty before continuing — a workaround no lawyer would discover on their own, since nothing on the crash page hints at the cause.

**Finding P0-5 — "Request exception" silently skips the reason-capture step for roughly half of governance findings.**
The "Request exception" button is shown identically (same label, same position) for any PROHIBITED/MUST_REDLINE/ESCALATE finding. Under the hood it maps to one of two different `data-act` values depending on whether the underlying policy position has `fallback_text` configured: with fallback text, it opens a required reason textarea ("goes in the audit record") before submitting; without fallback text, it calls `submitDecision` **immediately, with no reason, no confirmation, and no way to add one after the fact.** Two of our three governance-grade decisions (Limitation of Liability/ESCALATE, Indemnification/MUST_REDLINE) had no fallback text configured — not because we skipped a field, but because the underlying engines (`liability_policy_engine.py`, `indemnification_policy_engine.py`) simply don't attach fallback text to those particular states by design. The result: an audit-trail-critical governance action (an exception to blocked contract language) can be taken with literally zero documented justification, through a button that visually promises otherwise.

---

## Additional (lower-severity) findings

**P2-1 — Cross-document-type rule leakage.** A landlord/tenant-specific rule ("Landlord assignment/sublet consent lacks reasonableness standard") fired on an MSA (screenshot 26). The deterministic rule set does not appear to gate rules by contract type, undermining trust in the "Other Contract Findings" list generally.

**P2-2 — Governing-law jurisdiction regex is comma-brittle.** `governing_law_policy_engine.py`'s `_JURISDICTION_RE` only matches "governed by, and construed in accordance with, the laws of the State of X" with commas around the middle clause; the equally common unpunctuated form ("governed by and construed in accordance with the laws of the State of X") does not match, and falls back to REQUIRES_REVIEW even when a jurisdiction is unambiguously stated in ordinary prose.

**P2-3 — Inconsistent fallback-text availability across identical policy_state labels.** `MUST_REDLINE` carries a redline in the Termination engine but not (for our tested position) in the Indemnification engine, and `ESCALATE` never carries one in the Liability engine — yet all three states are presented to a lawyer with the same visual vocabulary, giving no way to predict from the label alone whether suggested language will be offered.

**P3-1 — No visible loading state during (very fast) synchronous processing**, for both contract review (Section F) and deterministic import (Section M) — see notes above.

**P3-2 — Redundant explanation text** between "Why this decision?" and "Contract evidence" panels on a finding (screens 30/31).

---

## Direct answers

**1. Could Sarah complete the entire workflow without instruction?**
**PROBABLY**, with two hard stops she could not resolve unaided: (a) the required-but-unlabeled template file on Playbook creation (P1) would confuse but not permanently block her — trial and error would eventually surface it; (b) losing an entire clause's worth of typed input to the Save-draft/Submit-for-review trap (P0-1) she would very likely not notice immediately (the review screen just looks unusually empty, not obviously "broken"), and would either re-do the work without understanding why, or worse, approve an empty/wrong position. Everything else — the setup chooser, the six-clause authoring pattern once learned, the exception queue, redlining, verify, and export — she could drive entirely on her own; the interaction design there is good enough to not need a manual.

**2. Where is the single biggest moment of confusion?**
The **Liability authoring page (06/07) immediately followed by the Liability review page (08)** — specifically the moment a lawyer clicks "Submit for review" expecting their work to carry forward and instead sees "Not yet decided" across every field. It is confusing precisely because nothing *looks* broken — the review screen renders correctly, just empty — so there's no error to Google, just an inexplicable blank policy.

**3. Where does TriageCounsel feel strongest?**
**The exception queue (25) combined with a finding's evidence stack (29–32, 40).** The combination of "here is exactly what they said, here is exactly what your policy says, here is who has to sign off, here is the suggested fix, and here is proof this is deterministic and repeatable" is a genuinely strong, trustworthy design for the exact audience (in-house/outside counsel under time pressure) this product targets. The setup-method chooser (04) is a close second for pure clarity of copy.

**4. Where does it still feel like an internal engineering tool?**
**The finalize/completion screen (42/43).** A lawyer clicking "Finalize Review" gets a completion banner glued onto the bottom of an unchanged, still fully-interactive review page — the kind of "we forgot to write the CSS rule that hides the old view" gap that reads as an engineering oversight rather than a deliberate UX choice, because it is one (confirmed in the template source — `#review-screen` has no display-toggling CSS rule at all).

**5. Does the contract-review page genuinely feel like review-by-exception?**
**PARTIALLY.** The exception-queue rail (25) and the top-of-page policy banners (24) are a real, well-executed review-by-exception surface for the six governed clause types. But the same page also surfaces 17 ordinary rule-engine findings with no policy backing, in a visually similar "Other Contract Findings" list, one of which is a landlord/tenant rule that doesn't belong in an MSA review at all — so "exception" is diluted by a second, unfiltered stream of findings sitting right next to it with no way to hide or deprioritize it.

**6. Is the recommended redline workflow obvious?**
**PARTIALLY.** Finding → Accept redline → counter increments is obvious and satisfying in the moment. Whether the underlying *document* changed is not obvious afterward — the accepted replacement text is never actually written into the visible contract body, only struck-through markers appear, and the real "after" text lives only inside a finding panel a lawyer would have to reopen.

**7. Is the deterministic evidence chain understandable without explanation?**
**YES.** This is the product's strongest area. "Contract evidence" (31) → "Playbook evidence" (32) → "Verify" (40) → deterministic-import's "View evidence" (49) all use the same causal vocabulary (contract excerpt → detected value → your playbook's stated position → result) consistently across the manual-authoring, contract-review, and import-review surfaces, and every one of them cites real, specific, traceable text rather than templated boilerplate.

**8. Would you put this exact UI in front of a law-firm design partner tomorrow?**
**NO.** Not because the visual design is bad (it's clean, consistent, and the copy is frequently excellent) but because of Findings P0-1 through P0-5: silent data loss on the authoring form, a feature-flagged enforcement mode that makes "Active" policies inert by default with zero on-screen disclosure, a false-negative on the product's own headline test paragraph, an unhandled 500 on a routine upload path, and an exception button that sometimes skips its own audit-trail requirement. Any one of these, hit live in front of a design partner, would be a credibility-ending demo failure; we hit three of the five on our very first pass through the product with no attempt to find edge cases.

**9. Top five UX problems, ranked.**
1. **P0-2** — Activated, "100% coverage" Playbooks silently enforce nothing by default (shadow mode), with zero on-screen disclosure.
2. **P0-1** — "Submit for review" discards unsaved authoring input with no warning, on every clause type.
3. **P0-4** — Routine contract-upload-against-Playbook crashes with an unhandled 500 whenever the Playbook's own template file produced findings (i.e., almost always).
4. **P0-5** — "Request exception" silently skips reason-capture (an audit requirement, per its own placeholder text) for roughly half of governance-grade findings, with an identical-looking button.
5. **P0-3** — The Liability engine's own headline test paragraph returns a false "not applicable" because the anchor-phrase regex is stricter than ordinary liability drafting.

**10. UX scores /10**

| Area | Score | Why |
|---|---|---|
| Dashboard | 7 | Clean, correct, minor plan-clarity gap. |
| Playbook creation | 4 | Silently-required file field, no preview on Free plan. |
| Setup-method chooser | 9 | Best screen in the product; clear, honest, well-written. |
| Empty Workbench | 8 | Clear coverage model, obvious next actions. |
| Manual authoring | 5 | Excellent field copy undercut by P0-1 (silent data loss) and weak action hierarchy. |
| Completed Workbench | 5 | Looks trustworthy; "Active"/"100%" claims are not backed by default server config (P0-2). |
| Test Policy | 4 | Good UI around a real false-negative (P0-3) on the exact adverse language this feature exists to catch. |
| Contract upload | 6 | Simple and correct, but one upload path away from an unhandled crash (P0-4). |
| Processing | 6 | No visible state, but only because it's genuinely fast — not deceptive. |
| Exception queue | 9 | Strongest single screen for the actual review workflow. |
| Finding detail | 8 | Complete, well-organized, minor content duplication. |
| Evidence/trust | 9 | Consistent, specific, real evidence chain across every surface that has one. |
| Redlining | 6 | Accept flow is clear; the document itself doesn't visibly show the new language afterward. |
| Exception/override | 4 | Works well when reachable; silently degrades to no-reason-capture for ~half of governance states (P0-5). |
| Verify | 9 | Does exactly what it claims, clearly communicated. |
| Finalize/export | 5 | Real, useful export bundle; broken/duplicated visual state on finalize. |
| Deterministic import | 7 | Honest, well-explained, some silent clause omissions with no reason shown. |
| AI-assisted import (disabled) | 8 | Clean, honest disabled state — nothing to fault given the feature is off. |
| **Overall** | **5** | A genuinely strong interaction-design foundation (copy, evidence chain, exception queue) undermined by five P0-severity functional/trust gaps that a lawyer would hit within one normal pass through the product, not through adversarial testing. |
