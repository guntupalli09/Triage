# Step 4A.4 Final Report — Independent Frozen Held-Out Validation

## A. Frozen-code integrity

- Commit/hash at start: `fc51fa4e2b318762049c74fde801f8852e9e9507`, working tree clean.
- Corpus checksum (locked before first execution): `54ebad4bfef6c1a60d5dec72f0acebe91c3478709a37561fae54e1f04b4c346c` (`step4a4_corpus.py`), `2962a9994a501fe4672ced47abad3a710c09f9a14510bde40dc5ba8ec1c86d64` (`step4a4_formatting_mutations.py`).
- Label checksum: locked jointly with corpus (labels are fields inside the same locked file — see `artifacts/step4a4/01_locked_checksums.txt`).
- Production file hashes, PRE and POST (identical):

| File | SHA-256 |
|---|---|
| `policy_engine_core.py` | `1ade60893e3b0da19df305e9c88bc6e591210d09b367f3f9959c23cf55648233` |
| `liability_policy_engine.py` | `eb9252ec6ae7089b7e3333c8825d28754bb3bb7ee4fe122af0bf878312b41a3e` |
| `indemnification_policy_engine.py` | `1ee54e6024d094eeecfb42e522f10a32315fd3ac12c5c1847206c824da8a1a11` |
| `payment_terms_policy_engine.py` | `1169925fc71de96ae994bd0441dcd5cdcd9556ae82329ae80dfe997622e1aa8a` |
| `interaction_enforcement.py` / `interaction_engine_core.py` / `interaction_rules.py` | unchanged (not touched, not in scope) |

**Contaminated? NO.** Only new files were created (`benchmarks/step4a4_*.py`, `artifacts/step4a4/*`); no production file was modified at any point in this step. Verified by direct hash comparison and `git status --short`.

---

## B. Corpus composition

| Adapter | AUTOMATABLE | SHOULD_REVIEW | Semantic total |
|---|---|---|---|
| Liability | 57 | 14 | 71 |
| Indemnification | 35 | 16 | 51 |
| Payment Terms | 40 | 10 | 50 |
| **Total** | **132** | **40** | **172** |

Formatting mutations: 20 (reported separately, Section L; not counted in the 172).

| Attack family | Cases | Adapter mix |
|---|---|---|
| A — unusual but clear role definitions | 15 | Liability 8, Indemnification 7 |
| B — conventional roles, irrelevant definitions | 11 | Liability 4, Indemnification 3, Payment 4 |
| C — genuine liability caps + distractors | 21 | Liability 21 |
| D — unusual but clear liability structures | 15 | Liability 15 |
| E — genuinely reciprocal indemnification | 15 | Indemnification 15 |
| F — payment recognition, unambiguous | 20 | Payment 20 |
| G — unresolved definitions (SHOULD_REVIEW) | 10 | Liability 4, Indemnification 4, Payment 2 |
| H — candidate ownership ambiguity (SHOULD_REVIEW) | 10 | Liability 10 |
| I — payment directional traps (mixed) | 15 | Payment 15 |
| J — indemnification asymmetry traps (mixed) | 15 | Indemnification 15 |
| K — recognition-failure attempts | 15 | Liability 5, Indemnification 4, Payment 6 |
| Compound / cross-policy | 10 | Liability 4, Indemnification 3, Payment 3 |

No case is copied or paraphrased from the Step 4A.2 corpus or the Step 4A.3 40-case adversarial corpus — new entity names and ten new business domains (logistics, media licensing, staffing, construction, SaaS/subscription, agriculture, telecom, healthcare services, energy, events, marine charter, reinsurance, franchising, customs brokerage) not previously exercised.

---

## C. Overall outcomes

| Outcome | Count | Rate (of 172) |
|---|---|---|
| CA | 81 | 47.1% |
| CR | 26 | 15.1% |
| FE | 39 | 22.7% |
| WC | 12 | 7.0% |
| SM | 12 | 7.0% |
| GTD | 2 | 1.2% |
| **Total** | **172** | 100% |

**Valid cases** (172 − 2 GTD) = **170**. Both GTD cases were labeled SHOULD_REVIEW (not AUTOMATABLE), so the AUTOMATABLE denominator used for Automation Recall and FE-among-AUTOMATABLE below is unaffected: **132**.

GTD detail: `A4-H-04` and `A4-H-05` were labeled SHOULD_REVIEW on the theory that an amendment "signaling intent to modify" or a numerically-identical carve-out creates genuine ambiguity. On reflection against the system's actual (defensible) output — `A4-H-04`: the amendment states no new figure, so the original cap continuing to govern is the more legally correct reading, not an ambiguity; `A4-H-05`: a carve-out cap numerically identical to the general cap is ordinary redundant drafting, not a genuine stacking ambiguity — both original labels were objectively too aggressive. Reclassified GTD per the task's explicit instruction rather than silently counted as WC or quietly relabeled CA.

---

## D. Safety metrics

| Metric | Value |
|---|---|
| WCDR (WC / automatic decisions [CA+WC=93]) | 12.9% |
| Unsafe Case Rate (WC / valid) | 7.1% |
| Silent Miss Rate (SM / valid) | 7.1% |
| S4 count | **0** |
| SM-CRITICAL count | **1** (`A4-K-07`) |

No WC reached a false-safe (ACCEPT/clean-clear on a clause that actually violates policy) or a PROHIBITED-cleared state. `A4-K-07` is SM-CRITICAL: a set-off clause phrased without the words "set-off"/"offset" ("withhold...an amount equal to any sums...owes") returns `NOT_APPLICABLE` — the clause never reaches the `prohibit_set_off` check at all, silently clearing a policy-violating term from review entirely, not merely failing to automate it.

---

## E. Automation/selectivity metrics (mandatory section)

| Metric | Value |
|---|---|
| CADR (CA / valid) | 47.6% |
| Automatic Decision Rate ((CA+WC) / valid) | 54.7% |
| **Automation Recall (CA / AUTOMATABLE)** | **61.4%** (81/132) |
| FE rate overall (FE / valid) | 22.9% |
| **FE rate among AUTOMATABLE (FE / AUTOMATABLE)** | **29.5%** (39/132) |

Automation Recall of 61.4% means that on drafting a human would consider objectively clear, the system reaches the correct automatic decision well under two-thirds of the time — the remainder mostly escalates unnecessarily (FE=29.5% of AUTOMATABLE cases) rather than getting it wrong (WC is a smaller fraction of AUTOMATABLE misses, concentrated in indemnification — see Section F). This is the central finding of Objective 2: **the system bought its Step 4A.3 safety gains at a real, measurable automation cost**, and that cost is systematic, not incidental (Section G).

---

## F. Per-adapter results

Both GTD cases (`A4-H-04`, `A4-H-05`) are liability-family-H (SHOULD_REVIEW), so they subtract from liability's valid/CR count only, not from any adapter's AUTOMATABLE count.

| Adapter | Valid | AUTOMATABLE | CA | CR | FE | WC | SM | WCDR | Automation Recall |
|---|---|---|---|---|---|---|---|---|---|
| Liability | 69 | 57 | 37 | 8 | 16 | 4 | 4 | 9.8% (4/41) | **64.9%** (37/57) |
| Indemnification | 51 | 35 | 13 | 8 | 18 | 8 | 4 | **38.1%** (8/21) | **37.1%** (13/35) |
| Payment Terms | 50 | 40 | 31 | 10 | 5 | 0 | 4 | **0.0%** (0/31) | **77.5%** (31/40) |
| **Total** | **170** | **132** | **81** | **26** | **39** | **12** | **12** | 12.9% | 61.4% |

Indemnification has by far the **worst** safety/automation balance: the highest WCDR (38.1% — more than one in three of its automatic decisions is wrong), the highest FE rate among its own AUTOMATABLE cases (18/35 = 51.4%), and the lowest Automation Recall (37.1%) — directly traceable to the multi-word-role-name and unmapped-generic-role systematic gaps (Section G root causes #1, #2, #3). Payment Terms has the **best** balance (Automation Recall 77.5%, WCDR 0.0% — every automatic payment decision observed was correct); its remaining gap is concentrated in recognition-vocabulary misses (Section J) rather than wrong decisions. Liability sits in the middle (Automation Recall 64.9%, WCDR 9.8%), with FE concentrated in a handful of well-isolated structural/basis-word mechanisms (Section G) rather than the broader identity-resolution problem that dominates indemnification.

---

## G. False-escalation analysis

| FE family | Count | Adapter(s) | Root cause | General/systematic? |
|---|---|---|---|---|
| 1. Multi-word ROLE name (the role being classified itself, e.g. "Staffing Agency", "Event Producer", "Home Health Agency", "Import Broker", "Underwriting Agent", "Host Facility"/"Tenant Operator") truncated to its last word by the indemnification obligation-parsing regex, then fails every downstream lookup under the truncated name | 7 | Indemnification | Verifier too weak — the capture group was never designed for multi-word entity/role labels, which are extremely common in real drafting | **Yes, systematic — the single largest FE family** |
| 2. Bystander multi-word CORPORATE NAME inside a definition's own identity boilerplate (e.g. "'Vendor' means Ridgeline Materials Group...") mistaken for a "second party" by `_has_unrecognized_relational_content`, even though the role token itself ("Vendor") is single-word and the sentence has zero transactional content | 7 | Liability, Indemnification, Payment (all Family B) | Verifier too weak — directly contradicts Family B's design goal ("the presence of a definition alone must not trigger review"); the heuristic conflates the entity's own multi-word legal name with a second party whenever ANY other word in the sentence matches the crude verb-suffix pattern (e.g. "successors and permitted **assigns**") | **Yes, systematic** |
| 3. Unmapped generic role name (not in `BUY_SIDE_ROLES`/`SELL_SIDE_ROLES`) with no in-document definition blocks exposure/protection classification even for a fully symmetric, unambiguous two-party exchange (e.g. "Landlord"/"Tenant", "Underwriter"/"Reinsured", "Grower"/"Processor"); `A4-COMP-09`'s closely related mutual/non-mutual configuration mismatch is included here as the same underlying category | 5 | Indemnification | Verifier too weak — this is the exact residual limitation flagged (but not fixed) at the close of Step 4A.3 Section K; Step 4A.4 shows it is not a rare edge case but a **high-volume, systematic** blocker for any domain-specific role-pair outside the hardcoded vocabulary | **Yes, systematic** |
| 4. Same unmapped-generic-role pattern as #3, manifesting in the payment adapter's tax-side resolution | 4 | Payment Terms | Same underlying pattern as #3 | **Yes, systematic** |
| 5. Basis-word extraction fixed in Step 4A.3 (rent/royalties/premiums added to the multiplier regex) but the downstream policy-threshold **comparison** layer (`_classify_basis`) still only recognizes "fee"/"purchase price"/"contract value" and declines to compare a non-fee-basis multiplier against fee-based thresholds | 4 | Liability | The Step 4A.3 basis-word fix was incomplete — it closed the extraction gap but not the comparison gap one layer downstream | **Yes, systematic, and a genuinely new finding about incomplete prior hardening** |
| 6. "Greater of"/"lesser of" structural extraction fails to pull both component values when one is a fixed dollar amount and the other a multiplier | 3 | Liability | Verifier too weak for a very standard drafting structure | Systematic within this structure |
| 7. Carve-out-scoped "uncapped" language for a specific claim category (fraud/willful misconduct) treated as conflicting with the general cap rather than a scoped exception | 2 | Liability | Verifier too weak for an extremely standard, commercially important pattern | **Yes, and commercially important** |
| 8. Well-formed but atypical reciprocal defined-term phrasing (e.g. roles that "rotate" via a defined-term convention) not parsed as an obligation at all | 2 | Indemnification | Verifier too weak for a legitimate structural variant | Plausibly systematic, small sample |
| 9. Per-claim + aggregate distinction extracted but the policy-threshold scope isn't specified/comparable | 1 | Liability | Narrow, single-case gap | Not yet shown to be systematic |
| 10. Disqualifier-to-candidate comma-segment scoping (the Step 4A.3 Family-3 fix) fails when the disqualifier and its target value are separated by a relative clause across a comma boundary ("exclusive of X, which shall not exceed $Y") | 1 | Liability | A genuine, subtle side-effect of the Step 4A.3 fix | Narrow so far, structurally plausible to recur |
| 11. Cross-reference-to-exhibit resolution fails when the exhibit heading falls inside the same provision-extraction window as the reference | 1 | Liability | Possibly influenced by this specific case's document length — flagged with that caveat | Uncertain |
| 12. Cross-sentence discovery only extends into a following sentence for a narrow bare-alias pattern (fixed in Step 4A.3); a descriptive-then-elaboration two-sentence definition ("means the party responsible for X. Owner shall pay...") is not covered, so the directional evidence in the second sentence is never found | 1 | Liability | The Step 4A.3 cross-sentence fix was narrower than this drafting pattern needs | Plausibly systematic, single case observed |
| 13. Genuinely mixed buy/sell vocabulary match where the intended "bystander" clause ("having provided the data...for account-verification purposes") was in fact read as directional — a vocabulary-calibration miss in either direction | 1 | Liability | Ambiguous whether this is a verifier weakness or a defensible conservative read; flagged, not over-claimed | Uncertain |

**Every FE family above is the second kind, not the first: the system is reviewing because our deterministic verifier is too weak, not because the underlying legal fact was genuinely ambiguous** (family 13 excepted, flagged as uncertain). Every other AUTOMATABLE case that produced an FE was, by this report's own construction and manual reconfirmation, objectively resolvable by a competent reviewer from the text alone.

**Did the previous FE increase (6→22) reproduce independently? Answer: PARTIALLY, trending toward YES (Scenario B).** Root causes #3 and #4 (unmapped generic role blocking classification even with unambiguous document evidence) are the *same underlying architectural gap* documented as a residual, unaddressed limitation at the close of Step 4A.3 (Section K of that report) — it was known, not fixed, and now demonstrably recurs at volume in new domains. Root cause #2 (bystander multi-word corporate names) is a new manifestation of the same *category* of problem that drove much of Step 4A.3's original FE growth (the `_has_unrecognized_relational_content` mechanism, introduced in 4A.3 specifically to close Family 1's WC gap, is shown here to over-trigger broadly on ordinary corporate boilerplate it was never validated against). Root cause #1 (multi-word role-name truncation) is a genuinely new finding, not present in 4A.3's own FE causes. Root causes #5–12 are also new, specific to this corpus's domains and structures — a real Scenario A component. **Net: this is not a clean Scenario A ("peculiar to the old corpus") result — a substantial, identifiable share (root causes #2, #3, #4 = 16 of 39 FE cases, 41%) is the same general verifier weakness recurring in new drafting, which the task's own criteria treat as blocking a clean PASS.**

---

## H. Previous (Step 4A.3) FE control — 22 cases, regrouped by root cause

The 22 POST-4A.3 FE cases (original labels **not** changed) were re-examined and grouped:

| Root cause (4A.3 FE cases) | Count | Also appears in Step 4A.4? |
|---|---|---|
| Unrecognized-verb bystander/relational content escalates even when the document's own language would, on close reading, resolve cleanly by a human (the `_has_unrecognized_relational_content` mechanism) | ~14 | **YES** — this is root cause #2 above, now shown to also fire on pure corporate-identity boilerplate with zero transactional content, a strictly broader failure mode than the 4A.3 cases exhibited |
| "References to X are references to" / broad-unrecognized-predicate escalation (deliberate, by design) | ~5 | YES, but this one is an intentional, accepted invariant (Section 4A.3 explicitly required it), not a defect — reproduced in `A4-I-02/03` and `A4-COMP-07` by design, correctly scored CR |
| Multi-provision/amendment reconciliation ambiguity | ~3 | Related but distinct — Step 4A.4's Family D structural gaps (greater-of/lesser-of, per-claim+aggregate, carve-out-scoping) are a different mechanism than 4A.2/4A.3's amendment-reconciliation FE cases |

**Conclusion: the dominant 4A.3 FE root cause (unrecognized-relational-content over-triggering) reproduces independently in Step 4A.4, and in a broader, previously-unobserved form** (firing on definitions with zero transactional content at all, not just unrecognized-but-genuinely-relational text). This is Scenario B for that specific mechanism.

---

## I. Wrong-clean analysis

Every WC, individually verified against actual extracted facts (not the auto-classifier's label alone):

| id | Adapter | Severity | What happened | Root cause |
|---|---|---|---|---|
| A4-G-01 | Liability | S2 | Mixed buy/sell evidence for "Consignee" ("purchases...from" + "resells...to") resolved confidently to buy_side instead of escalating | "resells" does not match the sell-verb regex `\bsell(?:s\|ing)?\b` because the `re-` prefix has no word boundary before "sell" — a real vocabulary/word-boundary gap |
| A4-G-03 | Liability | S2 | Two conflicting definitions of the same role at different document scopes (general vs. Section-14-scoped) — only the first (general) definition is discovered; the scoped, conflicting one is never found | Discovery only ever looks at the FIRST definitional sentence for a role; no mechanism detects a second, later, conflicting definition |
| A4-H-06 | Liability | S2 | Multiplier basis text itself flags an ambiguity ("may refer to...or, if greater, cumulative fees") but the extractor pulls "1x annual fees" without noticing the basis is described as alternative/undetermined | Multiplier extraction doesn't scan for basis-ambiguity language nearby |
| A4-H-08 | Liability | S2 | Contract text explicitly says "it is unclear whether...the same cap...or two independent caps that would stack" — the system still reaches ACCEPT_WITH_NOTE with a single confident value | No mechanism detects self-declared ambiguity language near a cap |
| A4-J-02, A4-J-12, A4-J-15, A4-COMP-06 | Indemnification | S3 | Reciprocal-opener-plus-named-party-exception pattern using a MULTI-WORD role name ("Home Health Agency", "Charter Operator" ×2, "Import Broker") — `_PARTY_SPECIFIC_EXCEPTION_RE`'s single-capitalized-word capture never matches | Same systematic multi-word-name gap as Section G's FE root cause #1 (multi-word role names), here manifesting as a missed asymmetry instead of an over-escalation |
| A4-J-05 | Indemnification | S3 | "Contractor (but not Owner) shall control the defense..." — an explicit, clearly differentiated term using a parenthetical-exclusion structure not covered by any existing detector | No detector exists for "(but not Y)" phrasing at all |
| A4-J-06 | Indemnification | S3 | Explicitly different survival periods per named party (5 years vs. 3 years) | `_compare_indemnity_attribution` tracks monetary/scope/defense_control/triggers only — survival period is not a tracked comparable attribute |
| A4-J-11 | Indemnification | S3 | Two separate sentences give each named party a different claim-timing carve-out, with no "except that/provided that" lead-in phrase at all | `_PARTY_SPECIFIC_EXCEPTION_RE` requires a specific lead-in phrase; this structure has none |
| A4-J-14 | Indemnification | S3 | "except that Grower's...obligations shall additionally require...notice...that does not apply to claims asserted against Processor" — the regex matches, but the comparator doesn't track notice/procedural preconditions as a comparable attribute | Same comparator-attribute gap as A4-J-06, different attribute |

**12 WC total. Zero are S4.** All liability WCs (S2) leave a defensible value in place; all indemnification WCs (S3) understate the true differentiated exposure in a specific carved-out scenario without clearing an outright policy violation.

No claim is made that wrong-clean decisions are impossible outside this set — only that none were observed beyond the 12 listed.

---

## J. Silent misses

All 12, all in the Payment Terms/Liability/Indemnification recognition layer, all confirmed by design (Family K) to describe a real, supported concept:

| id | Adapter | Concept present but missed | SM-CRITICAL? |
|---|---|---|---|
| A4-K-01 | Payment | Net-30 payment timing, no section heading | No |
| A4-K-03 | Indemnification | "hold...harmless from and defend...against" (reordered anchor verbs), no heading | No (favorable/protection clause) |
| A4-K-04 | Payment | Tax responsibility phrased "bear the cost of" | No |
| A4-K-05 | Liability | "Damages" heading, "exposure...restricted to" phrasing | No |
| A4-K-06 | Indemnification | "Risk Allocation" heading, "protect, defend, and reimburse" phrasing | No (favorable/protection clause) |
| A4-K-07 | Payment | Set-off phrased as "withhold...an amount equal to any sums...owes", no "set-off"/"offset" wording | **YES** — clears a `prohibit_set_off` violation from review entirely |
| A4-K-08 | Liability | "is fixed at...and shall not be exceeded" (non-canonical), no heading | No |
| A4-K-10 | Indemnification | "undertakes to make...whole for, and to assume the defense of", no heading | No (favorable/protection clause) |
| A4-K-11 | Payment | "disbursed by" payment-timing phrasing | No |
| A4-K-12 | Liability | "any recovery against...is limited to a sum not to exceed", no heading | No |
| A4-K-14 | Indemnification | "Loss Sharing" heading, conditional obligation phrasing | No (favorable/protection clause) |
| A4-K-15 | Liability | Field:value normalized text, no prose sentence, no heading | No |
| A4-F-20 | Payment | Telecom-specific tax/fee vocabulary not in the recognition vocabulary | No |

No claim is made that silent misses are impossible outside this set.

---

## K. Severity

| Severity | Count |
|---|---|
| S1 | 0 |
| S2 | 4 |
| S3 | 8 |
| S4 | **0** |
| SM-CRITICAL | **1** |

---

## L. Formatting robustness

All 20 formatting mutations were run against the same frozen code. **Zero semantic results changed** relative to their base case's actual (not expected) POST-run outcome — every mutation reproduced the identical `state`/`extracted_summary` as its base case, confirming formatting (capitalization, headings removed, line breaks, compressed paragraphs, semicolons, numbered/bulleted lists, quoted/unquoted terms, table-normalized text, whitespace noise) does not itself change any decision, for better or worse, on the cases tested. (This is a narrower claim than "recognition generalizes" — it only shows the *specific* outcome a case already reached, correct or not, is format-stable.)

---

## M. Existing controls

| Control | Result |
|---|---|
| Liability-125 | PASS — false-safe 0, accuracy 97.6% (unchanged), determinism 100% |
| Indemnification-100 | PASS — false-safe 0, false-escalation 0, determinism 100% |
| Payment-84 | PASS — false-safe 0, false-escalation 0, accuracy 100%, determinism 100% |
| Role-resolution (49 cases) | Precision 100%, Recall 100%, false-conflict 0%, missed-conflict 0% |
| Liability-concept (15 cases) | unchanged |
| Payment recognition (65 cases) | Recall 100%, Precision 95.7% (2 pre-existing FPs, unchanged) |
| Liability ownership (42 cases) | 42/42 (100%), 0 false-safes |
| Indemnification asymmetry (26 cases, 19 scored) | 19/19 (100%), 0 false-safes |

All eight controls hold exactly at their Step 4A.3 closing values. No unexplained regression.

---

## N. Step 4A.2 corpus reproducibility

Reproduced exactly: **CA 57 / CR 29 / FE 22 / WC 0 / SM 0** (108 semantic cases), matching the state recorded at the close of Step 4A.3 precisely.

---

## O. Product interpretation

1. **Is the current system still capable of false certainty on new drafting?** Yes, in a narrow but real sense — 12 WCs were found (7.0% of valid cases), none S4, all traceable to specific, now-documented mechanism gaps (word-boundary vocabulary miss, scoped-redefinition blindness, self-declared-ambiguity blindness, and — the largest cluster — the same multi-word-role-name gap that also drives much of the FE growth). It is not "confidently wrong at scale" — but it is not incapable of false certainty either.

2. **Is the current system systematically over-escalating clear drafting?** **Yes.** FE among AUTOMATABLE cases is 29.5%, traceable to a small number of *named, general* mechanisms (Section G), the largest of which (bystander multi-word proper names in ordinary corporate-identity boilerplate) directly defeats the specific design goal Family B was built to test ("the presence of a definition alone must not trigger review").

3. **Which adapter has the best safety/automation balance?** Payment Terms (Automation Recall 77.5%, WCDR 0.0% — no wrong automatic decisions observed at all; its residual gap is recognition-vocabulary misses, not incorrect decisions).

4. **Which has the worst?** Indemnification, decisively — Automation Recall 37.1% (worst of the three), WCDR 38.1% (more than one in three automatic decisions wrong — also the worst of the three and the main driver of the corpus-wide WCDR), and the highest AUTOMATABLE-FE rate (51.4% of its own AUTOMATABLE cases). Both of indemnification's problems (missed asymmetry, blocked classification) trace to the same handful of systematic mechanism gaps identified in Section G.

5. **Is FE now the dominant engineering problem?** **Yes** for liability and payment terms, where WC/SM are low and controlled and the residual gap is overwhelmingly unnecessary review. For indemnification specifically, **WC is now comparably urgent to FE** — a 38.1% WCDR is not a minor residual; the same underlying mechanism gaps (Section G root causes #1–#3) drive both problems simultaneously in that adapter.

6. **Would the current level of FE materially reduce usefulness for a slim legal team reviewing recurring commercial contracts?** Using the measured numbers rather than theory: Automation Recall of 61.4% overall (and as low as 37.1% for indemnification) means that on drafting a human reviewer would consider unremarkable, the system fails to resolve it automatically more than a third of the time overall — and for indemnification, nearly two-thirds of the time. For a team relying on this system to triage recurring commercial paper, that is a material fraction of ordinary contracts still landing on a human's desk purely because of specific, fixable regex/mechanism gaps (multi-word entity names, unmapped domain-specific role pairs, corporate-boilerplate bystander tokens) rather than genuine legal ambiguity. **Yes, materially reduced**, on this evidence — and for indemnification specifically, the current WCDR (38.1%) is itself a distinct, more urgent problem than automation convenience.

---

## Verdict

**HARDENING REQUIRED**

Justification against the task's own criteria: S4 = 0 and controls remain stable (both PASS-consistent), but this evaluation found (a) a non-zero, non-trivial WC count (12, all non-S4 but real), (b) a critical silent miss (SM-CRITICAL = 1 — a policy-violating set-off clause cleared from review entirely), and (c) clear evidence of a **systematic** general-verifier problem driving FE (29.5% of AUTOMATABLE cases, concentrated in a small number of named, general mechanisms — not scattered noise), with Section H showing the dominant 4A.3 FE mechanism reproducing independently and in a broader form here. Per the task's explicit verdict rules, this combination — meaningful WC, a critical silent miss, and FE revealing a systematic general-verifier problem — points to HARDENING REQUIRED rather than either PASS variant.

This is not a claim that the verify-or-escalate architecture itself is unsound (contra a FAIL verdict) — every identified gap is a specific, nameable mechanism weakness (a regex too narrow, a comparator missing an attribute, a vocabulary gap), not evidence the architecture cannot in principle separate supported facts from unsupported ones.

---

## Step 4B recommendation

- **Safety ready for Step 4B?** **WITH CONDITIONS** — S4=0 and WC is small and non-critical, but the single SM-CRITICAL case (a policy violation silently cleared from review) and the demonstrated recurrence of the multi-word-role-name/unmapped-generic-role gap should be closed first; these are narrow, well-understood fixes, not open research questions.
- **Automation/selectivity ready for Step 4B?** **NO** — Automation Recall (61.4% overall, 37.1% for indemnification) and FE-among-AUTOMATABLE (29.5%) show the system is not yet selective enough to be commercially useful at the rate Step 4A.3's own FE growth (6→22) already signaled as a risk.
- **Overall Step 4B recommendation: BEGIN ONLY AFTER FE HARDENING.**

## Next action

Per the task's explicit instruction, no code was modified during this evaluation. The recommended next step is a **Step 4A.5 — False-Escalation Reduction** pass, targeting (in priority order, by systematic impact): (1) multi-word role/entity name support in the indemnification obligation-parsing and asymmetry-exception regexes; (2) resolving exposure/protection classification when at least one named party's side is confidently known even if the other is an unmapped generic role with no document definition; (3) narrowing the bystander/relational-content heuristic so a definition's own multi-word corporate name is never itself treated as a "second party"; (4) completing the Step 4A.3 basis-word fix through the policy-threshold-comparison layer, not just extraction; (5) the carve-out-scoped-uncapped-language vs. genuine-conflict distinction for fraud/willful-misconduct carve-outs; (6) the SM-CRITICAL set-off vocabulary gap specifically. The invariant for that step: reduce unnecessary review without reintroducing wrong-clean decisions — i.e., re-run this same 172-case corpus (plus the Step 4A.2/4A.3 corpora as regression controls) after the fix and confirm WC does not rise above its current level while Automation Recall rises materially.

Step 4A.5 was **not** performed here. Step 4B was **not** started.
