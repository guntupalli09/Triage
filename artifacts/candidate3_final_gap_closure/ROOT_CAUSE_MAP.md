# Root Cause Map (Candidate 3 final gap-closure, Section 0)

Re-verified directly against commit `0ee86e2` (frozen input commit for this mission), not trusted from the prior mission's report. Every case below was re-run through the actual current code before any fix was applied.

## Group A — `is_operative_context()` structural-cue gap (Root Cause A)

**Shared mechanism**: `is_operative_context()`'s only non-obvious gate required BOTH `_INDUSTRY_NORM_DESCRIPTIVE_RE` AND `_NOT_YET_AGREED_RE` before suppressing a match as non-operative. Plain descriptive, hypothetical, or directly-negated text that didn't carry both signals (or either signal, for the hypothetical/negation sub-families, which had no signal coverage at all) passed through as `True` (operative), letting a structuring regex establish a "fact" from text that was never the document's real term.

| Case | Adapter | Family | First point of breakage |
|---|---|---|---|
| limitation_of_liability-001 | liability | LEE2 descriptive | `is_operative_context` returns `True` for "Technology services agreements commonly cap..." — no party-specific obligation, pure generic-subject commentary |
| insurance-102 | insurance | LEE3 hypothetical | `_QUOTATION_INTRODUCING_RE`'s "for example" check only fires when a quote-mark span exists; "For example, if Vendor were required to..." has no quote marks, so the hypothetical framing is invisible |
| data_security-130 | data_security | NEGATED | **Re-verified and corrected, not a Root Cause A instance** — `data_security_policy_engine.py` never calls `is_operative_context` at all; it has its own dedicated `_BREACH_NOTIFICATION_NEGATION_RE` (added in Candidate 2), which ALREADY correctly matches this exact text (`established=True`, `breach_notification_explicitly_disclaimed=True`, directly re-confirmed). The burned-corpus grading harness's `_established_signal` proxy treats `established=True` on a `NO_NOT_OPERATIVE`-labeled case as automatically wrong regardless of WHY it was established; this specific case's test policy config is `{}` (no breach-notification requirement configured at all), so `ACCEPT` is the policy-correct outcome given that empty config, independent of whether the negation was recognized (it was). This is a harness-grading/test-configuration artifact exposed by this mission's re-verification, not a code defect reachable by any of the three chartered fix classes — no code change applied for this case. See `ADAPTER_SAFETY_MATRIX.md`. |
| sla-201 | sla | LEE2 descriptive | Same as limitation_of_liability-001 |
| sla-202 | sla | LEE3 hypothetical | Same as insurance-102 |
| sla-203 | sla | LEE4 negotiation/draft | `_NOT_YET_AGREED_RE` alone fires but the AND-gate required `_INDUSTRY_NORM_DESCRIPTIVE_RE` too, which this sentence lacks |
| sla-204 | sla | LEE5 quoted external | "attached for reference only, not incorporated" not covered by the existing reference-only phrase list |
| sla-210 | sla | NEGATED | Same direct-negation gap as data_security-130 |

Root cause: **one shared classifier, one shared gap** — not 8 independent adapter bugs. Fix scope: `policy_engine_core.py` only.

## Group B — cross-reference / definition detection vocabulary gap (Root Cause B)

**Shared mechanism**: 6 independently-authored regexes (`insurance_policy_engine._SCHEDULE_CROSSREF_RE`, `payment_terms_policy_engine._SCHEDULE_CROSSREF_RE`, `sla_policy_engine._SCHEDULE_CROSSREF_RE`, `warranties_policy_engine._SCHEDULE_CROSSREF_RE`, `ip_ownership_policy_engine._SOW_CROSSREF_RE`, `data_security_policy_engine._DPA_CROSSREF_RE`) all independently required the literal word "the" before Schedule/Exhibit/DPA, and none had any detector at all for a defined term whose definition is delegated to an external, explicitly-not-attached document.

| Case | Adapter | Text shape | First point of breakage |
|---|---|---|---|
| sla-208 | sla | "as set forth in Exhibit C" | No "the" before "Exhibit C" — regex doesn't match, `established_signal=False` yet decision reaches non-REQUIRES_REVIEW |
| ip_ownership-088 | ip_ownership | "as set forth in Schedule G" | Same "the" gap |
| data_security-128 | data_security | "as set forth in the Data Processing **Addendum**" | Regex only knew "Data Processing Agreement"/"DPA", not "Addendum" |
| insurance-108 | insurance | "as set forth in Exhibit D" | Same "the" gap |
| insurance-109 | insurance | "'Required Coverage.' ... defined in the Master Services Agreement, which is not attached" | No detector at all for external-definition-not-attached |
| data_security-129 | data_security | "'Personal Data Breach' as defined in the Data Processing Addendum, which is not attached" | Same — plus the Addendum vocabulary gap |
| ip_ownership-089 | ip_ownership | "'Pre-Existing Materials.' ... defined in the Statement of Work, which is not attached" | Same — plus: even after detecting it, an already-established ownership statement in the same sentence swallowed the signal (see below) |

Root cause: **narrow, independently-reinvented regex vocabulary with no shared primitive**, plus (for ip_ownership-089 specifically) no separate signal for "a defined term used inside an established fact is itself unresolved" as distinct from "nothing else was established."

## Group C — clean-state provider variance (Root Cause C)

**Mechanism** (re-traced from `REAL_PROVIDER_REPEATABILITY.md`, confirmed against current code): `ip_ownership_policy_engine._OWNERSHIP_PASSIVE_RE` matched `"shall be (solely )?owned by <Party>"` but not `"shall be owned exclusively by <Party>"` (adverb between "owned" and "by"). Deterministic ownership attribution therefore NEVER established for this phrasing, making the case's outcome depend entirely on whether the AI's per-run discovery+verification succeeded — 4/5 runs correctly reached `REQUIRES_REVIEW` via Root Cause 1's `PRESENT_BUT_UNRESOLVED` net, 1/5 runs reached `ACCEPT`.

A prior fix attempt (Candidate 3 remediation mission) broadened the regex correctly but exposed a SECOND, independent bug: `_categorize`'s nearest-keyword heuristic picked a subordinate "including any pre-existing intellectual property embodied therein" mention over the sentence's real subject ("Work Product") purely because it sat textually closer to the ownership verb, misattributing `benchmarks/ip_ownership_corpus.py`'s `conflict-02` case to `background_ip` instead of `work_product`. The fix was reverted rather than trade one bug for another.

Root cause: **two independent, compounding regex/heuristic gaps** — a word-order gap in the ownership-passive-voice regex, and a "nearest raw-distance keyword" category-attribution heuristic with no concept of subordinate/qualifying clauses.

## Fix scope declared before implementation

- Group A: `policy_engine_core.py` only (`classify_operative_context`, three new signal regexes, one broadened regex).
- Group B: one new shared primitive in `policy_engine_core.py` (`EXTERNAL_DEFINITION_NOT_ATTACHED_RE`) plus a one-line broadening of each adapter's own existing cross-reference regex (no new schema, no adapter-specific reinvention); `ip_ownership_policy_engine.py` gets one new dataclass field (`definition_dependency_unresolved`) to keep the "already-established fact, but a used term is separately unresolved" case distinct from "nothing established."
- Group C: `ip_ownership_policy_engine.py` only (`_OWNERSHIP_PASSIVE_RE`, `_nearest_category`, new `_SUBORDINATE_QUALIFIER_SPAN_RE`).

No other adapter code touched. No adapter's authority boundary (AI discovers, deterministic code decides) touched — every fix here operates entirely within the deterministic layer.
