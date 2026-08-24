# Candidate 2 — Cross-Adapter Adversarial Sweep

Scope: all 12 fact-admission adapters (liability, indemnification,
confidentiality, payment_terms, ip_ownership, insurance, data_security,
governing_law, termination, warranties, sla, assignment). Purpose: confirm
the 6 fixed root causes did not leave the SAME failure class alive,
unaddressed, in an adapter that did not happen to appear in the 74-case
frozen corpus, and confirm no adapter regressed on dimensions the fix
touched only indirectly (the shared `policy_engine_core` primitives).

Each row is evidence-backed: either a fresh ad-hoc probe run against the
adapter's real `extract_*` function during this sweep (shown inline), or a
pointer to the adapter's own permanent regression suite already covering
that dimension. "N/A" is used only where the dimension genuinely does not
exist for that adapter's semantics, with the reason stated.

## Dimension: descriptive vs. operative (defect #4/#5's root cause class)

The two fixed adapters (insurance, sla) plus the three pre-existing callers
of `is_operative_context` (liability, indemnification, payment_terms) are
directly protected by the shared primitive. The 7 adapters that do NOT call
`is_operative_context` were probed directly with the same adversarial
shape that broke insurance/sla ("industry-norm descriptive framing +
explicit not-yet-agreed language"), adapted to each adapter's own subject
matter:

| Adapter | Wired to `is_operative_context`? | Probe result |
|---|---|---|
| liability | Yes (pre-existing) | Regression suite (`test_liability_fact_admission.py`) already exercises this family. |
| indemnification | Yes (pre-existing) | Regression suite (`test_indemnification_reconciliation.py`, `test_candidate2_indemnification_backward_reference.py`) already exercises this family. |
| payment_terms | Yes (pre-existing) | Regression suite (`test_payment_terms_fact_admission.py`) already exercises this family. |
| insurance | Yes (Candidate 2 fix) | `test_candidate2_operative_context_shared_fix.py` — descriptive background never establishes coverage; operative clause still does. |
| sla | Yes (Candidate 2 fix) | `test_candidate2_operative_context_shared_fix.py` — descriptive background never establishes uptime; operative clause still does. |
| confidentiality | No | Probed: `"It is common practice for a vendor to protect a customer's confidential information for five years, although the specific duration for this engagement remains to be negotiated."` → `obligations=[]`, `absence_state=CONFIRMED_ABSENT`. **Not exposed** — the adapter's own obligation-attribution regex requires an explicit `shall protect`/`shall hold in confidence`-shaped commitment verb tied to a named party, which this descriptive sentence never supplies. |
| ip_ownership | No | Probed: `"Technology agreements typically assign all work product IP to the customer, although ownership terms for this engagement have not yet been agreed."` → `ownership_attributions={}` (empty). **Not exposed** — same reason: no `shall`/`is owned by`-shaped attribution verb present. |
| data_security | No | Probed: `"Vendors in this industry usually notify customers of a personal data breach within 72 hours, although the specific notification period for this engagement remains to be negotiated."` → `breach_notification_hours=None`. **Not exposed** — the hour/day-window extractor requires an obligation verb (`shall notify`/`must notify`) directly governing the anchor, absent here. |
| governing_law | No | Probed: `"Technology agreements of this type typically designate Delaware law as governing, although the governing law for this engagement has not yet been agreed."` → `jurisdiction=None`. **Not exposed** — the jurisdiction extractor requires a direct `governed by the laws of <state>`-shaped clause, not a third-person descriptive mention. |
| termination | No | Probed: `"It is common practice for a vendor agreement to allow termination for convenience with 60 days notice, although the termination terms for this engagement remain to be negotiated."` → `rights=[]`. **Not exposed** — same reason: no first-person `either party may terminate`-shaped grant present. |
| warranties | No | Probed: `"Vendors typically warrant that services will be performed in a professional and workmanlike manner, although the specific warranty terms for this engagement have not yet been agreed."` → `facts is None` (the adapter's own `found_anything` negative-control gate already rejects a bare descriptive mention with nothing structured — this is the same defensive pattern the mission asked insurance/sla to adopt, already present here). |
| assignment | No | Probed: `"It is common practice for a vendor agreement to prohibit assignment without consent, although the assignment terms for this engagement remain to be negotiated."` → `restrictions=[]`, `absence_state=CONFIRMED_ABSENT`. **Not exposed** — no first-person restriction-granting verb present. |

**Finding:** none of the 7 not-yet-wired adapters are exposed to this exact
failure shape today, because each one's own extraction gate independently
requires a first-person, obligation-verb-bearing commitment before
attributing any fact — the insurance/sla defect was specifically that their
coverage/uptime-percent regexes matched on a bare NUMBER+UNIT anchor without
that same requirement. This is a narrower gate than "call
`is_operative_context`," not evidence the primitive is unnecessary there:
a descriptive sentence that DID happen to contain a first-person obligation
verb (e.g. "It is typical for agreements of this type to have the vendor
warrant services shall be performed in a professional manner, though this
is not yet agreed") could still slip through the same class of gap in these
7 adapters. This residual risk is recorded in `ROOT_CAUSE_MAP.md` and is
NOT fixed in this mission (wiring 7 more adapters to a primitive with no
corpus evidence of an actual failure there would violate the "no
unrequested scope" and "no regression on adapters not in scope" discipline
this mission set) — it is flagged as follow-up scope for whoever builds
Candidate 2's independent corpus.

## Dimension: negated vs. affirmative

| Adapter | Result |
|---|---|
| liability, indemnification, confidentiality, payment_terms, ip_ownership, insurance, data_security, sla | Each has a `TestNoClause`/equivalent negative-control case in its own `test_*_fact_admission.py` or `test_*_policy_engine.py` suite (e.g. indemnification's `test_negated_mention_is_not_applicable_not_a_false_clause`) — all pass. |
| governing_law, termination, warranties, assignment | Freshly probed in this sweep with a `"No <clause> is included in this Agreement"` construction for each: governing_law and (previously) data_security/ip_ownership correctly resolve to `CONFIRMED_ABSENT`; confidentiality, termination, warranties, and assignment correctly return `None`/no clause_found rather than fabricating an obligation from the negated mention. No false extraction in any of the 12. |

## Dimension: condition preservation / exception preservation

Applicable to: liability, indemnification, confidentiality, payment_terms,
data_security, insurance, sla (adapters whose obligations can be
conditioned or carved out). Each has dedicated condition/exception tests in
its own suite; indemnification additionally gained the new
`detect_backward_referenced_qualifier` coverage in this mission
(`test_candidate2_indemnification_backward_reference.py`, 9 tests). Not
independently re-verified for termination/warranties/assignment/ip_ownership/
governing_law in this sweep beyond their own existing suites, since none of
the 6 fixed defects touched a shared condition/exception primitive those
adapters call — `_merge_condition_evidence` and `ConditionEvidence` were not
modified by any Candidate 2 fix.

## Dimension: cross-sentence / cross-section modifiers

Directly exercised by the defect #1 (confidentiality, cross-sentence
asymmetry) and defect #6 (indemnification, cross-section backward
reference) regression families, both of which include multi-paragraph/
multi-section variants
(`test_multi_paragraph_form_still_caught`,
`test_multi_section_form_forward_reference_wording_still_caught`). No other
adapter's fixed code touches cross-section reasoning in this mission.

## Dimension: definitions / cross-references

`sow_cross_reference` (ip_ownership), `dpa_cross_reference`/
`liability_cross_reference` (data_security), and the Section-N backward
reference machinery (indemnification, liability, payment_terms) are each
covered by their own adapters' existing suites. No Candidate 2 fix altered
definition-resolution code; only indemnification's cross-reference
detection (defect #6) was in scope, and it is covered above.

## Dimension: competing readings

N/A for this mission's 6 defects — none of the fixes touched
`resolve_competing_readings`-shaped logic (that machinery is exercised by
each adapter's own existing "competing reading" test cases per
`EXECUTABLE_ARCHITECTURE.md` from the Mission A validation, unchanged here).

## Dimension: AI provider failure / grounding disagreement / hallucinated evidence / missed modifier

N/A for source-code-level fixes: all 6 Candidate 2 fixes are deterministic,
regex/structural-primitive changes in the extraction and evaluation layers.
None of them touch the AI-discovery layer (`fact_admission.py`'s provider
call, grounding, or reconciliation code), so this dimension is unaffected
by Candidate 2 and is separately covered by the AI PROVIDER CONFIGURATION
section of `CANDIDATE2_REPORT.md` (fail-closed behavior when no provider is
configured — the production default — rather than a live-provider sweep,
per the same credential/budget constraint honored in Mission A).

## Summary

No adapter outside the 6 targeted defects regressed. No adapter shares an
ACTIVE (corpus-demonstrated) instance of the fixed failure classes. One
residual, narrower-than-original risk is documented (7 adapters not wired
to `is_operative_context` could theoretically be fooled by a descriptive
sentence that also contains a first-person obligation verb) and explicitly
deferred as out-of-scope follow-up, not silently closed.
