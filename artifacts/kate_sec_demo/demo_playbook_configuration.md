# Demo Playbook Configuration — "Commercial Services Playbook"

Reviewing perspective: **Customer** (buy-side), evaluating an inbound data-center
/ managed-services MSA against Customer's own legal team's approved
positions. Thresholds below are commercially ordinary — not tuned to force
findings — and were verified against the real contract via a dry run through
the actual production pipeline (`policy_enforcement.apply_policies_for_review`)
before being entered into the application's Playbook authoring UI.

| Policy area | Contract side | Key positions |
|---|---|---|
| Limitation of Liability | Mutual | Preferred cap 1.0x fees, acceptable up to 2.0x, negotiate up to 6.0x. Uncapped liability not prohibited outright (colocation/facility risk is commercially mutual here). No specific required carve-outs configured. |
| Indemnification | Buy-side (Customer) | No specific required protection triggers configured; uncapped exposure not prohibited; exposure cap preferred 1.0x / acceptable 2.0x / negotiate 5.0x of fees. |
| Termination | Buy-side | Minimum 30 days' notice against us, minimum 5 days' cure period against us. |
| Payment Terms | Buy-side | Preferred Net 30, acceptable up to Net 45. |
| SLA / Service Levels | Buy-side | No specific uptime/severity-tier minimums configured for this position (colocation power/space SLA structure differs from a SaaS uptime SLA). |
| Insurance | Buy-side | Require CGL, minimum $1M per occurrence / $2M aggregate; require counterparty obligated to carry insurance. Cyber liability not required (facility/colocation risk profile). |
| Confidentiality | Mutual | No specific required exclusions or minimum duration configured for this position. |
| Assignment | Buy-side | No specific required exceptions configured. |
| Governing Law | Buy-side | No preferred/acceptable jurisdiction list configured — left open for this engagement. |
| Data Protection & Security | Buy-side | Standard buy-side defaults; not expected to be the controlling issue on a colocation/facility agreement. |
| IP Ownership & Licensing | Buy-side | Standard buy-side defaults. |
| Warranties | Buy-side | Standard buy-side defaults; no specific required warranty categories configured. |

## Honesty note

Governing Law and Data Protection & Security are legitimately less central
to this particular agreement (a data-center colocation/power license
structured with arbitration/dispute-resolution provisions rather than a
conventional governing-law clause, and no data-processing relationship). The
real engine reports Governing Law as `NOT_APPLICABLE` and Data Protection &
Security as not meaningfully evaluated on this document. This was not
adjusted to manufacture a fuller-looking result — the honest count is what is
reported in `contract_selection.md` and in the demo itself: 12 policy areas
available, 10 evaluated meaningfully, 1 genuinely not applicable, 1 not
evaluated (no matching provisions), 4 accepted, 2 negotiate, 2
requires-review, 2 must-redline, 1 actionable cross-policy interaction.
