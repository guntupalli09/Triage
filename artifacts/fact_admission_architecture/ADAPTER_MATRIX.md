# ADAPTER_MATRIX

## Reconciliation (12/12, resolving the "1/12 vs 10/12" ambiguity)

The previous session's summary conflated two different things under
"integrated." This table separates them:

- **Architecturally protected** = has SOME absence-state-aware,
  fail-closed-on-uncertainty protection today (whether via the new shared
  `fact_admission.py` or indemnification's own pre-existing, separately
  frozen equivalent).
- **Integrated with shared framework** = specifically uses
  `fact_admission.py`'s discover/verify/ground/admit functions.

| # | Adapter | Architecturally protected before this branch | Shared `fact_admission.py` integration | Production enabled | Targeted tests | Regression |
|---|---|---|---|---|---|---|
| 1 | limitation_of_liability | No | **YES** (prior session) | No (`LIABILITY_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 85/85 pass |
| 2 | indemnification | **YES** — own pre-existing `semantic_discovery_real.py` + 4-way `absence_state`, frozen/validated Step 4B | Not migrated (deliberate — see ARCHITECTURE.md) | Partial (`SEMANTIC_PROVIDER` hardcoded `SIMULATED`) | pre-existing suite | pre-existing suite passes |
| 3 | confidentiality | No | **YES** | No (`CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 36/36 pass |
| 4 | payment_terms | No | **YES** | No (`PAYMENT_TERMS_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 8/8 pass |
| 5 | ip_ownership | No | **YES** | No (`IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 4/4 pass |
| 6 | insurance | No | **YES** | No (`INSURANCE_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 11/11 pass |
| 7 | data_security | No | **YES** | No (`DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 4/4 pass |
| 8 | governing_law | No | pending this session | — | — | — |
| 9 | termination | No | **YES** | No (`TERMINATION_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 50/50 pass |
| 10 | warranties | No | **YES** | No (`WARRANTIES_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 4/4 pass |
| 11 | sla | No | pending this session | — | — | — |
| 12 | assignment | No | pending this session | — | — | — |

Accounting for all 12: **1 integrated with the shared framework
(liability)**, **1 architecturally protected by a separate, pre-existing
mechanism (indemnification)**, **10 with no semantic protection at all
before this session** (rows 3-12, being closed in this session below,
one at a time, updating this table after each).



Integration status of the shared `fact_admission.py` framework across all
12 production adapters (confirmed list, see PRE_IMPLEMENTATION_MAP.md §1).

| # | Adapter | Fact-admission integration | Existing AI pathway |
|---|---|---|---|
| 1 | limitation_of_liability | **DONE (reference implementation)** — see below | none prior to this change |
| 2 | indemnification | Not migrated — has its own separately frozen, already-validated (Step 4B) semantic-discovery pathway (`semantic_discovery_real.py`) with an equivalent absence-state model. See ARCHITECTURE.md for why this is left as-is. | `semantic_discovery_real.py` (Anthropic, discovery only, deterministic structural verification) |
| 3 | confidentiality | Not yet integrated | none |
| 4 | payment_terms | Not yet integrated | none |
| 5 | ip_ownership | Not yet integrated | none |
| 6 | insurance | Not yet integrated | none |
| 7 | data_security | Not yet integrated | none |
| 8 | governing_law | Not yet integrated | none |
| 9 | termination | Not yet integrated | none |
| 10 | warranties | Not yet integrated | none |
| 11 | sla | Not yet integrated | none |
| 12 | assignment | Not yet integrated | none |

**Only 1 of 12 adapters (liability) has been integrated with the new
shared framework in this pass**, per explicit user direction to prove the
pattern end-to-end on one adapter before rolling out to the rest (see
conversation record — this was a deliberate, confirmed scope decision, not
an oversight). The remaining 10 are scoped below as a roadmap; each is
real design work (Step 8), not mechanical repetition, because each
adapter's material dimensions differ.

## 1. limitation_of_liability — DONE

Material dimensions already handled by `liability_policy_engine.py`'s
existing deterministic structuring (unchanged by this integration): cap
amount/multiplier, cap basis (fees/purchase price/contract value/fixed/
recurring payment), category carve-outs (data breach, IP infringement,
confidentiality, indemnification, fraud, gross negligence, willful
misconduct), consequential-damages exclusion, cross-referenced cap
definitions, multi-provision reconciliation (amendment/consistent-
duplicate/unreconciled), and directional (asymmetric) party positions.

Fact-admission integration adds a third, additive discovery layer for the
one case the deterministic anchors miss entirely: liability language using
neither `_ANCHOR_RE` nor `_SECONDARY_ANCHOR_RE`'s vocabulary. The semantic
layer never touches cap parsing, basis classification, or category
carve-out logic — a semantically-discovered candidate is only ever a
*where to look* signal into the SAME deterministic `_extract_provision()`
every regex anchor already uses (see AUTHORITY_BOUNDARY.md §3). Gated
behind `LIABILITY_SEMANTIC_DISCOVERY_ENABLED` (default `False`).

## 2-12. Roadmap for the remaining adapters (dimensions, not yet built)

Each row lists the material dimensions a semantic verifier's adversarial
proposition set would need to address for that adapter, drawn from each
engine's own `SEMANTIC MODEL` docstring section
(confirmed present at `confidentiality_policy_engine.py:7`,
`payment_terms_policy_engine.py:18`, `ip_ownership_policy_engine.py:17`,
`insurance_policy_engine.py:15`, `data_security_policy_engine.py:13`,
`governing_law_policy_engine.py:14`, `termination_policy_engine.py:12`,
`warranties_policy_engine.py:6`, `sla_policy_engine.py:8`,
`assignment_policy_engine.py:9` — read in full before writing any
verifier prompt, not assumed from the mission brief's examples alone):

- **confidentiality**: who is obligated to protect whose confidential
  information; definition scope; exclusions (public domain, independently
  developed, rightfully received); use restriction; disclosure exceptions
  (legal compulsion, professional advisors); duration (including
  survival past termination); return/destruction obligations.
- **payment_terms**: payment period; disputed-amount handling; offset/
  setoff rights; tax allocation (gross-up vs. inclusive); late fees/
  interest; price-increase conditions; which of several payment-related
  catalog items are independently present vs. absent.
- **ip_ownership**: background IP vs. work product ownership; license
  grants (scope, exclusivity, field of use); residual-rights carve-outs;
  which party owns what given the two genuinely independent questions
  this adapter's own docstring identifies (see file for the exact two).
- **insurance**: required coverage types; minimum limits; additional-
  insured requirements; certificate/evidence-of-insurance obligations;
  schedule/exhibit cross-references for coverage detail.
- **data_security**: security-standard obligations; breach-notification
  triggers and timelines; subprocessor flow-down requirements; data-use/
  transfer restrictions — four largely independent catalog items per the
  engine's own four anchor regexes (`_SUBPROCESSOR_ANCHOR_RE`,
  `_BREACH_ANCHOR_RE`, `_TRANSFER_ANCHOR_RE`, `_SECURITY_ANCHOR_RE`).
- **governing_law**: governing jurisdiction; forum/venue; mandatory vs.
  permissive forum language; conflict-of-laws qualifiers.
- **termination**: termination for convenience vs. for cause; cure
  periods; notice requirements; survival clauses; post-termination
  obligations — independent catalog items per
  `_SURVIVAL_ANCHOR_RE` existing as its own anchor.
- **warranties**: express warranties made; disclaimers (including
  ALL-CAPS conspicuousness conventions); warranty duration; remedies for
  breach; carve-outs/exceptions to disclaimers.
- **sla**: uptime/service-level commitment; measurement methodology;
  exclusions (scheduled maintenance, force majeure); service credits/
  remedies; sole-remedy language — per the engine's own "three independent
  fact families, deliberately never conflated" docstring framing.
- **assignment**: consent requirements; affiliate/change-of-control
  exceptions; assignment-by-operation-of-law treatment; successor-and-
  assigns binding language.

For each, integration should follow the exact 5-step discipline in
ARCHITECTURE.md's "Rollout discipline" section, in the same order liability
was done: absence_state field -> gated real-provider call -> anchor-only
semantic contribution (never bypassing existing structuring) ->
RECOGNITION_UNCERTAIN routes to REQUIRES_REVIEW -> adapter-specific tests
including the descriptive-language regression family.

This is deliberately not attempted in this pass. Each adapter's
`evaluate_*_policy` structuring logic must be read in full before its
semantic verifier propositions can be written correctly — doing all 10 in
one sitting without that reading would repeat the mission's own warned-
against anti-pattern (benchmark-patching without understanding).
