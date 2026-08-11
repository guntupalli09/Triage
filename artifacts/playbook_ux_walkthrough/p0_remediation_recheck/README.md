# P0 remediation recheck — delta screenshots

These are **replacement screenshots for the five P0 failure points only**, not a re-run
of the original 50-screenshot walkthrough. The original record in the parent directory
is untouched.

Same scenario as the original pass: persona Sarah Chen / Acme Software, Playbook
"Acme Customer MSA Playbook" (seller side, LoL configured 1x preferred / 2x acceptable /
3x negotiable, unlimited prohibited, escalation authority General Counsel), test contract
`../northstar_msa_test_contract.txt` **used verbatim, unmodified**. Driven end to end
through a real browser against a live `uvicorn main:app` by `recheck_walkthrough.py`
(kept here for reproducibility).

| File | Shows |
|---|---|
| `p0-1-a-authoring-filled-before-submit.png` | Liability authoring form filled in, **not saved** |
| `p0-1-b-review-screen-values-preserved.png` | After clicking *Submit for review* with no prior *Save draft*: every value persisted (1x/2x/3x, prohibited unlimited, carve-outs, General Counsel, fallback text) and the position is in Needs Review. Previously this screen read "Not yet decided" for every field. |
| `p0-2-a-workbench-enforcement-disclosure-shadow.png` | Workbench while enforcement is not authoritative: "Policy enforcement: Checking only — not yet deciding reviews", in plain English (no env-var terminology) |
| `p0-2-b-review-enforcement-disclosure-shadow.png` | Same disclosure on the contract-review page |
| `p0-2-a/b-...-cutover.png` | The same two surfaces when policy **is** authoritative: "Governing contract reviews" |
| `p0-2-c-operator-readiness-report-shadow.txt` | Operator surface (`python -m scripts.phase4_readiness_check`): current mode, whether it is authoritative, and how long the deployment has been in it |
| `p0-3-northstar-clause-classified.png` | Test Policy on the Northstar liability clause **with no heading**: now `ESCALATE` ("5x annual fees … exceeds negotiable range"), previously `NOT APPLICABLE` |
| `p0-4-a-upload-configured.png` / `p0-4-b-review-loaded-no-500.png` | Uploading the Northstar contract against a Playbook whose own template produced findings: review renders, no 500 (`Deviation is not JSON serializable`) |
| `p0-5-a-server-rejects-reasonless-exception.txt` | Raw POSTs to the decision endpoint bypassing the UI entirely — empty and whitespace-only reasons both rejected 400, server-side |
| `p0-5-b/c/d-...` | ESCALATE finding (no fallback text — the state that previously submitted instantly): *Request exception* now opens the reason step, and confirming with an empty reason is refused |
| `p0-5-e/f-governance-record-...` | Resulting governance record — original recommendation, decision, reviewer, timestamp, reason — visible in the finding, and still there after a page reload |
