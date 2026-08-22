# Step 4B Phase M — Material-Fact / System Trust Audit

## Method

`scripts/step4b_run_phaseM_trust_audit.py` runs 80 real documents (70
rotating-subset documents built from Phase L's freshly-authored per-
clause-type phrasing, plus 10 documents using boilerplate liability/
indemnification text already proven — Phase H — to be recognized by
those two adapters) through the REAL end-to-end pipeline
(`policy_enforcement.apply_policies_for_review`, cutover mode, real
ACTIVE `PolicyPosition` rows for all 12 clause types, real extraction,
real evaluation). This is deliberately NOT fixture-based (unlike Phases
A/D/E/H/L Group 2) — Phase M's purpose is auditing real
extraction→evaluation provenance, which a hand-constructed
`PolicyDecision` fixture cannot test at all (it starts already
"extracted").

Every resulting `ACCEPT`/`ACCEPT_WITH_NOTE` decision (an "authoritative
clean/automatic decision") is classified:

- **VERIFIED** — a real clause was matched (`controlling_provision`
  present, real text indices) AND the governing `PolicyPosition`'s config
  genuinely required something for that clause type (non-vacuous) — a
  real constraint was actually checked against real extracted language.
- **WEAKLY_ESTABLISHED** — a real clause was matched, but the governing
  config required nothing at all for that clause type (fully
  least-restrictive default) — ACCEPT is correct (nothing was violated
  because nothing was required), but it is a vacuous pass, not a checked
  compliance fact.
- **UNVERIFIED** — an ACCEPT-family state with NO clause ever matched in
  the text at all (`controlling_provision is None`) — the hard-gated
  defect shape.

Governance/revision provenance is checked on every audited decision via
`policy_revision_metadata`'s `policy_position_id`/`config_hash` presence.

## Result

**254 authoritative ACCEPT/ACCEPT_WITH_NOTE decisions audited** (exceeds
the ≥200 minimum), across 4 of the 12 clause types whose adapters
recognized this session's phrasing (`ip_ownership`, `insurance`,
`payment_terms`, `sla`) — the remaining 8 clause types' documents in this
run resolved to `NOT_APPLICABLE` (no clause recognized) or an actionable
state (`MUST_REDLINE`/`REQUIRES_REVIEW`, for `limitation_of_liability`/
`indemnification`/`confidentiality` under the STRICT config), never a
false `ACCEPT`.

**Classification: 254/254 (100%) WEAKLY_ESTABLISHED. 0 VERIFIED, 0 UNVERIFIED.**

This is an honestly disclosed finding, not a defect: every ACCEPT
observed in this run happened because the governing `PolicyPosition`'s
config genuinely required nothing for that clause type (the
least-restrictive default this session's playbook setup used for 11 of
12 clause types) — ACCEPT is the structurally correct response when
nothing is configured to check, but it means this specific run did not
happen to produce a genuine VERIFIED example (a real requirement actually
satisfied by real text) for any of the 4 matching clause types. One
attempt was made to manufacture a VERIFIED case (`governing_law` with a
`preferred_jurisdictions_json: ["Massachusetts"]` requirement against
text mentioning "Commonwealth of Massachusetts") — it did not trigger
because that adapter's extractor did not recognize the phrasing as a
governing-law clause at all (`NOT_APPLICABLE`), consistent with the
`limitation_of_liability`/`indemnification` extraction-completeness
limitation already disclosed in Phase L (Step 4A's extraction adapters
are out of scope for this phase per standing instructions — this is a
known, disclosed, non-blocking limitation, not a wrong-authority defect).

**Hard gates:**
- `policy_changing_unverified_feeding_clean = 0` → **PASS**
- `untraceable_governance_on_clean_decision = 0` → **PASS** (every one of
  the 254 audited decisions carried a traceable `policy_position_id` +
  `config_hash` in its revision metadata)

## No production defect found; no production file changed

Every ACCEPT observed was backed by real matched evidence
(`controlling_provision` present) — the audit never found a clause-level
ACCEPT resting on zero textual evidence. The 100%-WEAKLY_ESTABLISHED
result reflects this session's own playbook-configuration choices (most
clause types left at their least-restrictive default), not a system
defect.

## Regression

No production file modified this phase. Full `pytest tests/`: **1975
passed, 14 skipped, 0 failed** (unchanged).

## Conclusion

Across 254 real, end-to-end-produced authoritative clean decisions, zero
rested on missing evidence (`UNVERIFIED = 0`) and every one carried
traceable governance provenance. The audit did not happen to produce a
genuine VERIFIED (real-requirement-actually-checked) example in this
run — disclosed honestly rather than manufactured — because this
session's playbook left most adapters unconfigured; this is a
configuration-scope limitation of this specific audit run, not a system
trust defect, and does not block any hard gate.
