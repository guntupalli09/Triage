# Adapter Primary-Fact Grounding Matrix (Candidate 3 remediation)

Per Section 3 of the mission: for every adapter, what deterministic evidence is necessary to ground its PRIMARY fact, and how Root Cause 1's fix (`PRESENT_BUT_UNRESOLVED`) applies or doesn't.

| Adapter | Primary fact | Grounding requirement | Root Cause 1 applied? |
|---|---|---|---|
| limitation_of_liability | cap concept + affected party/side + amount/formula/unlimited state + scope | `_extract_provision`'s cap/multiplier parser, run on any anchor (regex- or AI-sourced) | Not needed — an unparseable admitted candidate already routes to `MUST_REDLINE` via the existing "clause present but no numeric general cap stated" branch |
| indemnification | party pair + trigger + monetary treatment + condition | Full deterministic structuring parser (hybrid discovery design, unchanged) | Not needed — structurally avoids the defect by design (Section 11: not replaced) |
| confidentiality | confidentiality obligation + obligated party + protected scope + directionality | `_NAMED_OBLIGATION_RE`/`_MUTUAL_OBLIGATION_RE`, scanning the FULL document unconditionally (not window-scoped to an anchor) | Not needed — the existing blanket "obligations=[] → REQUIRES_REVIEW" branch already safely absorbs any unparseable case |
| payment_terms | payment obligation + deadline/time period + triggering event | `_NET_DAYS_RE`/`_WITHIN_DAYS_PAYMENT_RE` etc., window-scoped to the anchor | **Yes** — `PRESENT_BUT_UNRESOLVED` added |
| ip_ownership | ownership attribution + category (background/work-product) | `_OWNERSHIP_PASSIVE_RE`/`_IP_ASSIGNMENT_RE`, window-scoped | **Yes** — the exact mechanism behind the confirmed `ip_ownership-099` non-determinism |
| insurance | coverage type + limit | `_COVERAGE_RES` (named types only), window-scoped | **Yes** |
| data_security | breach notification window / role / transfer mechanism / etc. | Multiple dimension-specific regexes, window-scoped | **Yes** |
| governing_law | jurisdiction | `_JURISDICTION_RE`, scanning the FULL document unconditionally | Not needed — blanket "jurisdiction is None → REQUIRES_REVIEW" branch already safe |
| termination | termination right + holder + trigger | `_NAMED_RIGHT_RE`/`_MUTUAL_RIGHT_RE`, scanning the FULL document unconditionally | Not needed — blanket "rights=[] → REQUIRES_REVIEW" branch already safe |
| warranties | warranty category + established/negated | Per-category regex + `found_anything` gate, window-scoped | **Yes** — `found_anything` itself did not previously account for an admitted-but-unstructured candidate at all (would return `None` → `NOT_APPLICABLE`, not even reach ACCEPT) |
| sla | uptime percent / service credit / response times | Per-dimension regex + `found_anything` gate, window-scoped | **Yes** — same mechanism as warranties |
| assignment | assignment restriction / unrestricted flag | `_NAMED_RESTRICTION_RE`/`_MUTUAL_RESTRICTION_RE`, scanning the FULL document unconditionally | Not needed — blanket "restrictions=[] and not unrestricted → REQUIRES_REVIEW" branch already safe |

## Pattern observed

The adapters that needed Root Cause 1's fix are exactly the ones whose primary-fact extraction is **window-scoped to a specific anchor position** (insurance, payment_terms, ip_ownership, data_security, warranties, sla) — an admitted-but-unstructured candidate's window simply produces nothing, with no adapter-level fallback distinguishing "nothing in this window" from "nothing anywhere." The adapters whose primary-fact regex **scans the full document unconditionally** (confidentiality, governing_law, termination, assignment) already had an unconditional, blanket "nothing was ever structured → REQUIRES_REVIEW" check, because that check doesn't depend on knowing WHERE to look first. Liability and indemnification are protected by their own, adapter-specific fallback branches (a `MUST_REDLINE`-on-no-cap branch, and a fully re-run deterministic structuring parser, respectively).
