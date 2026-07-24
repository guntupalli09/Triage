# Severity Classification Architecture — v1.0

Status: **proposed specification**, superseding the earlier draft (git
history preserves it as `v0`). The current 117 rules still carry legacy
analogy-assigned severities pending the migration in §12. Until that
migration completes, `Severity` on `Rule` remains the runtime source of
truth and this document is not yet enforced.

This version is not a refinement of v0 — several of v0's factors were
deleted, redefined, or merged after a 40-clause stress test exposed real
double-counting and at least one category error. §1 is a full self-critique
of v0. Nothing from v0 survives here by default; anything that does
survives because it was re-derived and re-tested, not because it was
already written down.

---

## 1. Self-critique of the prior proposal

Reviewed against the specific failure modes requested: overlap, hidden
assumptions, ambiguous definitions, double counting, unintuitive outputs.

**1.1 — PE, RW, and FB double-counted the same fact on personal
guaranties.** v0 scored an unconditional personal guaranty that waives
suretyship defenses as PE=3 *and* RW=3 *and* implicitly drove FB up too —
three factors all reacting to one underlying fact ("this guarantor has no
way out"). That's not three independent risks, it's one risk read three
times. **Fix:** RW is redefined to cover only *forum/process* rights
(the right to notice-and-hearing, a jury, a class, an independent
arbitrator) — not substantive contract defenses. Waiving a suretyship
defense is now scored entirely inside PE (which internally encodes
capped-vs-uncapped), and FB is redefined to apply strictly to the
*entity's* exposure, never the guarantor's. Each fact is now scored in
exactly one place.

**1.2 — CR and RS both listed "loss of a license/authorization."** An
identical example appeared under both Criminal Exposure and Regulatory
Exposure in v0 — a direct overlap the brief specifically asked me to hunt
for. **Fix:** CR is now strictly *penal* exposure (fines payable as
punishment, referral for prosecution, imprisonment exposure). License and
authorization loss lives entirely in RS.

**1.3 — MC (Trigger Conditionality) was a category error, not a severity
factor.** On reflection, "does this fire automatically on signature vs.
require a contingent event" is a *detection-methodology* question — the
engine already models exactly this distinction via `RuleClass`
(`PRESENCE_RISK` vs `REQUIRED_SECTION`). Encoding it a second time as a
severity factor mixed two different layers of the system. **Fix: deleted.**
Not merged, not renamed — removed, because it didn't measure an
independent legal fact at all.

**1.4 — The v0 weighting scheme (Tier A/B/C ×4/×2/×1) was asserted, not
derived, and under-weighted unbounded financial exposure specifically.**
Stress-testing an uncapped vendor-liability clause (`shall not be limited`)
against v0's formula produced a WAS that landed **LOW** — a result that is
flatly wrong by any commercial-lawyer's standard, and wrong in the
*dangerous* direction (a real top-tier risk scored as noise). This is
exactly the "unintuitive result" the brief asked me to hunt for and fix,
and it's the most important thing v0 got wrong. See the Refinement Log
(§4) for how this was fixed — it required promoting unbounded financial
exposure to its own ceiling rule rather than trusting the aggregate.

**1.5 — v0 had no factor for unilateral, unconstrained control over a
fundamental deal term (price, existence, location) short of a rights
waiver or an uncapped dollar figure.** Landlord relocation rights and
franchise termination-without-cure — both correctly HIGH in last session's
rules — scored **LOW** under a naive re-run of v0's formula, because
neither one waives a forum right, transfers ownership, or states an
unbounded dollar amount. The harm is real but doesn't fit any of v0's nine
remaining factors. This surfaced during the stress test, not in the
original design, and required inventing a new factor (§2, UD) rather than
patching an existing one — patching REV or OC to also cover this would have
recreated the overlap problem from §1.1 in a new place.

**1.6 — v0's level definitions used unmeasurable adjectives** ("substantial,"
"broad," "significant") without defining what makes something substantial.
Two reviewers could legitimately disagree on whether $50,000 of exposure is
"substantial." **Fix:** every level in §2 below is now defined by the
presence or absence of specific, enumerable textual markers (e.g., "any and
all," a stated dollar cap, "sole and absolute discretion," a defined notice
period) — the same kind of marker vocabulary the detection regex already
searches for. A reviewer applies the rubric by checking whether specific
words appear, not by judging degree.

**1.7 — Mutuality was excluded from v0 entirely, and that was itself a
mistake — but naively re-adding it as a subjective judgment would have been
a worse mistake.** Standard mutual at-will employment ("either party may
terminate at any time") scored as a false positive once UD was introduced
in §1.5's fix, because unconstrained discretion over the relationship's
existence, without a mutuality check, flags completely ordinary boilerplate
as high severity. The fix is not "score mutuality subjectively" — it's
that the engine *already has* a deterministic, jurisdiction-neutral
mutuality classifier (`_classify_party_direction` / `party_direction`,
used today for `ONE_WAY_RULE_IDS`). UD is defined to consume that existing
output as an input, scoring 0 whenever the discretion is held identically
by both parties. This is a legitimate intrinsic fact (derivable from clause
grammar alone) reused from existing deterministic machinery, not a new
subjective axis.

---

## 2. Intrinsic factors (v1.0)

Litmus test, unchanged from v0 and reaffirmed after stress-testing it
against 40 clauses: a factor is legitimate **iff it is determinable from
the clause's text, the contract's own party-direction grammar, and general
legal doctrine — never from the specific parties' identities, the specific
governing law, deal size/stakes, or any probability estimate.**

11 factors (down from v0's 10 — one deleted per §1.3, one added per §1.5),
grouped into three harm tiers. Every entry states what it measures, what it
explicitly does *not* measure, and why it can't be merged into a neighbor —
required by the brief for every factor, not just the ones that changed.

### Tier A — Fundamental rights & personal harm (weight ×4)

**PE — Personal Exposure to a Natural Person**
- 0: no clause language extends any obligation to a named natural person.
- 1: a natural person is named as obligor, and the obligation is capped by
  a stated dollar figure or formula.
- 2: a natural person is named as obligor, uncapped, but limited to a
  closed, enumerated list of obligations (e.g., "guarantees Base Rent
  only").
- 3: a natural person is named as obligor for "any and all"/unqualified
  obligations, no stated cap, no closed list — *including* where the
  clause separately waives defenses to that obligation (per §1.1, that
  waiver is absorbed into this level, not re-scored under RW).
- Does NOT measure: whether the person can contest the claim procedurally
  (RW); the entity's own exposure (FB, by definition excludes personal
  guarantors).
- Cannot merge into RW: a capped personal guaranty (PE=1) with no waiver
  language exists and is common; RW=0 there while PE>0 — the two vary
  independently, proving they measure different things.

**RW — Waiver of Forum/Process Rights**
- 0: no waiver of how a dispute gets resolved.
- 1: waives a negotiable procedural convenience (e.g., objection to venue).
- 2: replaces court with a *neutral* alternative forum (e.g., ordinary
  arbitration with a recognized administrator) — a different process, not
  an eliminated one.
- 3: eliminates any adversarial process before an adverse consequence
  attaches (confession of judgment/cognovit — judgment with no hearing at
  all), **or** stacks jury-trial waiver + class-action waiver + mandatory
  arbitration together, such that no meaningful avenue to contest a claim
  remains (see stress test #13 — three individually-moderate waivers
  compound into something categorically worse than any one alone).
- Does NOT measure: financial exposure size (FB) or whether a natural
  person is exposed (PE) — a purely corporate jury-trial waiver scores RW
  with PE=0.
- Cannot merge into PE: RW fires identically whether the party bound is an
  individual or a corporation (jury-trial waivers appear constantly in
  pure B2B contracts with PE=0 throughout).

**CR — Penal Exposure**
- 0: none.
- 1: clause references compliance with a criminal statute, exposure
  indirect (a representation of compliance only).
- 2: clause text itself creates or fails to prevent direct criminal
  exposure (e.g., a provision requiring backdating, or a
  kickback/structuring arrangement).
- Does NOT measure: loss of a license or regulatory authorization — that
  is entirely RS's job after §1.2's fix.
- Cannot merge into RS: penal liability (fines to the state as punishment,
  imprisonment) is doctrinally distinct from administrative/regulatory
  enforcement (fines to a regulator, license loss) even though both stem
  from statutes — the remedy-holder and the nature of the sanction differ.

### Tier B — Structural financial & legal exposure (weight ×2)

**FB — Financial Boundedness and Certainty (entity-level only)**
- 0: the entity's monetary obligation or payment right is capped by a
  stated amount/formula, *and* is not contingent on a fact outside this
  party's control.
- 1: capped, but by a large/undefined multiple ("greater of $X or Y×
  fees").
- 2: a cap exists elsewhere in the agreement, but this clause's own
  carve-out ("except for," "notwithstanding the cap") removes it from that
  cap's coverage.
- 3: no cap referenced anywhere (structurally uncapped: "unlimited,"
  "without limit," "any and all claims"), **or** the party's right to be
  paid at all is made entirely contingent on a third party's independent,
  uncontrollable decision (e.g., pay-if-paid — see Refinement Log #3,
  which broadened this factor from pure liability-cap language to also
  cover payment-contingency, since both are the same underlying legal
  fact: "is the financial outcome bounded and certain").
- Does NOT measure: a natural person's guaranty exposure (PE, by
  definition).
- Cannot merge into AT: FB concerns the *amount/certainty* of money; AT
  concerns *title* to an asset. A capped liability clause with a separate
  broad IP assignment scores FB=0, AT=3 — fully independent in practice.

**RS — Named Regulatory/Statutory Exposure**
- 0: no named regulatory regime implicated by the clause's own text or its
  clause_category doctrine.
- 1: a regime is named for representation/compliance purposes only, no
  operative obligation tied to it.
- 2: a regime is named and the clause creates or omits a substantive
  compliance obligation under it (e.g., GDPR "Data Controller" language
  with no DPA requirement).
- 3: a regime is named, the clause's own gap makes non-compliance
  structural (e.g., PHI handled, no BAA required), and the regime carries
  direct enforcement authority against a contracting party.
- Does NOT measure: whether *this contract clause* creates new penal
  exposure (CR) — a routine FCA certification clause references a heavy
  statute (RS=3) without itself creating new criminal exposure beyond what
  the statute already imposes by operation of law (see stress test #34,
  an explicit example of this distinction being load-bearing).
- Cannot merge into SC (below): RS is a doctrinal fact ("is a named regime
  implicated"); SC is a headcount fact ("how many people does this reach
  per the clause's own defined terms"). Stress test #25 and #33 show these
  varying independently — a two-party securities representation is RS=3,
  SC=0; a broad marketing data-share with no named regime is RS=0, SC=3.

**AT — Ownership/Title Transfer**
- 0: license/use-right language only, no title transfer.
- 1: transfer limited to specifically enumerated, narrow deliverables.
- 2: broad transfer language ("all right, title and interest") carved back
  by an explicit retained-rights or license-back provision.
- 3: unconditional, broad transfer, no retained rights, no license-back.
- Does NOT measure: whether the transfer, once made, can practically be
  undone (REV) — an AT=3 clause with a contractual repurchase option still
  scores AT=3 (the grant as drafted is unconditional) but would score lower
  on REV.
- Cannot merge into FB: an unconditional IP assignment with zero dollars
  attached scores AT=3, FB=0 (no monetary exposure at all) — the two vary
  fully independently.

**UD — Unilateral Discretion Over a Fundamental Term**
*(new in v1.0 — see Refinement Log #2 for why v0 lacked this and what broke
without it)*
- Scored 0 by definition whenever the same discretion is held identically
  by both parties (sourced from the engine's existing deterministic
  `party_direction` classification — see §1.7). This is not a judgment
  call; it's a lookup against machinery the engine already computes.
- 0: no unconstrained unilateral discretion over price, term/existence,
  scope, or location — changes require mutual agreement or follow an
  objective external standard (e.g., CPI-indexed).
- 1: unilateral discretion exists but is bounded by a stated objective
  formula/ceiling.
- 2: unbounded discretion, but limited to a single non-existential term
  (e.g., relocation within the same building; CAM charges with no cap;
  audit-rights scope).
- 3: unbounded discretion touching the existence/continuation of the
  relationship itself, or an economic term whose absence of any
  procedural *or* financial constraint makes it functionally equivalent
  (termination "for any reason or no reason"; an earnout payable entirely
  at the buyer's discretion with no formula).
- Does NOT measure: whether notice/cure softens the exercise of that
  discretion (OC, scored separately) or whether the dollar amount at stake
  is capped (FB, scored separately) — UD fires on the *existence* of
  unconstrained control; OC and FB determine whether anything constrains
  how it's actually exercised. See Refinement Log #2 and #4 for why UD
  needed to combine with *either* OC *or* FB, not just OC, to correctly
  separate ordinary at-will termination from things like uncapped-earnout
  buyer discretion.
- Cannot merge into RW: RW is about *forum* — how a dispute gets resolved.
  UD is about *deal terms* — who controls what the deal even is. A
  contract can have UD=3 (unilateral termination) with RW=0 (ordinary court
  access preserved), or RW=3 (confession of judgment) with UD=0 (no
  discretion over deal terms at all, just a harsh enforcement mechanism).

### Tier C — Operational & temporal exposure (weight ×1)

**REV — Legal Reversibility of Harm**
- 0: fully compensable by ordinary damages.
- 1: compensable, but only via a difficult-to-prove remedy (e.g., lost
  profits).
- 2: partially irreversible (e.g., a confidential disclosure, once made,
  cannot be undone, though damages may follow).
- 3: structurally irreversible (an entered judgment, an executed release of
  unknown claims, information published to the public domain, equity
  already diluted, a trained model that has ingested the data).
- Does NOT measure: whether an asset's *title* moved (AT) — a broad release
  of claims scores REV=3 with AT=0; the two vary independently (stress
  test #10 vs. #14).

**SC — Structural Breadth of Exposed Persons**
- 0: only the two contracting parties, per the clause's own defined terms.
- 1: contracting parties plus a defined, closed class (e.g., named
  affiliates).
- 2: contracting parties plus an open-but-role-bounded class ("all Company
  employees," "all Subcontractors").
- 3: an unbounded/public class by the clause's own text ("any third
  party," "the general public," undefined "partners").
- Does NOT measure: whether a named regulatory regime is implicated (RS) —
  independence demonstrated in stress test #25/#33.

**OC — Notice/Cure Absence on Adverse Unilateral Action**
- 0: a specific notice and/or cure period is stated (N/A, scored 0 by
  convention, for clauses that don't involve an adverse unilateral action
  at all — this is a textual applicability gate, not a judgment call).
- 1: "reasonable notice" or similarly undefined notice, no cure period.
- 2: "immediately," "without notice," "at any time," or silent on notice
  entirely.
- Does NOT measure: whether the underlying discretion is one-sided (UD) —
  a *mutual* right to terminate immediately without notice scores UD=0
  (per the mutuality gate) but OC=2 independently; OC alone, without UD
  confirming asymmetry, never reaches a ceiling.

**DUR — Temporal Boundedness**
- 0: bounded by the Agreement's term or a stated survival period.
- 1: survives termination, but for a stated, bounded post-termination
  period.
- 2: "perpetual," "in perpetuity," "indefinitely," or silent on survival
  limits for an obligation that logically continues.
- Does NOT measure: whether the ongoing obligation is itself risky in
  substance (that's whatever factor the substance triggers — e.g., a
  perpetual license with unconditional transfer is scored on AT, DUR
  separately notes only that it never ends).

---

## 3. Factors deliberately excluded (reaffirmed after stress-testing)

Unchanged in substance from v0, restated with the stress-test evidence that
confirms each exclusion was correct rather than convenient:

| Excluded factor | Confirmed by |
|---|---|
| Likelihood of litigation/enforcement | Stress test #34 (FCA certification): the statute's real-world enforcement risk is identical regardless of this contract's drafting quality — scoring it would attribute background statutory risk to a specific clause that didn't create it. |
| Bargaining power / ease of negotiation | Never appeared as a necessary input in 40 clauses scored blind to which party had leverage. |
| Estimated dollar damages | FB (§2) is the correct proxy — "is it bounded," not "what would it cost." Stress test #3 shows FB alone correctly identifies uncapped liability as top-tier without ever estimating a number. |
| Deal size / commercial stakes | Stress test #40 (assignment-on-change-of-control) is the clearest case: the same clause is existential for a company mid-acquisition and irrelevant for one that never will be — an extrinsic fact about the deal, not the clause. Flagged in §5 as the single most contestable stress-test disagreement precisely because excluding this factor is uncomfortable but principled. |
| Governing-law enforceability | Modeled entirely in §6 (jurisdiction), confirmed necessary by stress test #17 (non-compete): identical clause text is banned in one state and standard practice in another — conflating that into intrinsic severity would make "severity" silently mean different things depending on which contract you're reading. |

---

## 4. Refinement log (what the stress test actually broke, and how it was fixed)

This is the evidence that the framework was tested to failure and repaired,
not asserted once and left alone.

1. **PE/RW/FB double-counting on personal guaranties** — found while
   scoring stress test #8 against v0's definitions. Fixed by narrowing RW
   to forum/process rights only and making FB entity-only (§1.1, §2).

2. **Landlord relocation and franchise-termination-without-cure scored LOW**
   — found while re-running last session's HIGH-rated lease/franchise
   rules through v0's nine factors; none of them fired. Root cause: no
   factor captured "unconstrained control over a fundamental deal term."
   Fixed by adding UD (§2) — but UD's first version created a **new** false
   positive (see #4 below).

3. **Pay-if-paid scored LOW** (stress test #22) — none of the original
   factors captured payment-contingency risk; it isn't a liability cap,
   an ownership transfer, or a rights waiver, it's a distinct fact about
   whose credit risk a payment obligation rides on. Rather than add a 12th
   factor for one clause type, FB's definition was broadened (§2) to cover
   "boundedness *and certainty*" of a monetary outcome, since both a
   missing cap and an uncontrollable payment contingency are the same
   underlying question: is the financial result of this clause bounded and
   knowable. This also correctly pulled lien-adjacent construction clauses
   into scope without a new factor.

4. **Standard mutual at-will employment scored HIGH** the moment UD was
   added (stress test #16) — an unconstrained-discretion factor with no
   mutuality check flags completely ordinary boilerplate. Fixed by gating
   UD on the engine's existing `party_direction` mutuality classification
   (§1.7): mutual discretion scores UD=0 by definition. Re-run: at-will
   boilerplate correctly returns LOW; one-sided lease relocation and
   franchise termination correctly return HIGH.

5. **Earnout-at-buyer's-discretion scored LOW even after UD existed**
   (stress test #29) — the UD ceiling as first written required pairing
   with OC (no notice/cure), but earnout discretion isn't a
   notice-and-cure situation at all; OC is structurally N/A (scored 0) for
   purely economic discretion clauses, so the ceiling could never fire for
   an entire category of real risk (uncapped pricing/earnout/MFN-adjacent
   discretion). Fixed by widening the ceiling to fire on UD=3 paired with
   **either** OC=2 (procedural: no notice/cure) **or** FB≥2 (substantive:
   no financial constraint) — unconstrained discretion is severe when
   nothing, procedural or financial, bounds how it gets exercised.

6. **A pattern, not a bug: absence-type findings score systematically
   lower than presence-type findings** (stress test #28, deadlock
   mechanism; #35, government flow-down clauses) — both landed LOW under
   pure intrinsic scoring, consistent with each other. This maps cleanly
   onto the engine's existing `FindingType` distinction
   (`ADVERSE_LANGUAGE_DETECTED` vs. `EXPECTED_PROTECTION_NOT_FOUND`), which
   already treats absence-claims as lower-confidence than presence-claims.
   Documented here as an intentional, now-twice-observed property of the
   architecture, not patched away — a missing protective clause is
   definitionally less certain to matter than adverse language that is
   actually present, and the two systems (confidence and severity) agree
   on that independently, which is reassuring rather than coincidental.

**Deferred, not adopted** (explicitly flagged rather than smuggled into
v1.0 without full re-testing): a "compound ceiling escalation" rule — when
two *independently* fired HIGH ceilings coincide on one clause (stress test
#30, AI training-on-data: `AT/REV` and `RS/SC` both fire from different
underlying facts) — could arguably escalate to CRITICAL. Left out of v1.0
because one stress-test observation isn't enough evidence to add a new
compounding rule; candidate for v1.1 after it's tested against more
multi-ceiling clauses.

---

## 5. Stress test — 40 clauses

Factor vector shorthand: `PE·RW·CR·FB·RS·AT·UD·REV·SC·OC·DUR`. WAS =
(PE+RW+CR)×4 + (FB+RS+AT+UD)×2 + (REV+SC+OC+DUR)×1. Ceiling rules (§6)
checked first; WAS/bands (§6) only apply if no ceiling fires.

| # | Type | Clause | Vector | Ceiling | WAS | Tier | Note |
|---|---|---|---|---|---|---|---|
| 1 | NDA | Perpetual confidentiality, mutual, standard exceptions | 0·0·0·0·0·0·0·0·0·0·2 | — | 2 | LOW | Duration alone, nothing else — see §5.1 disagreement with legacy MEDIUM |
| 2 | NDA | Confidential-info definition lacks public/independent-development carve-out | 0·0·0·0·0·0·0·1·0·0·0 | — | 1 | LOW | Drafting-clarity issue, not a rights/financial fact |
| 3 | SaaS | Vendor liability "shall not be limited" | 0·0·0·3·0·0·0·1·0·0·0 | FB=3 | — | **HIGH** | Matches legacy H_LOL_01 |
| 4 | SaaS | Liability capped at 12mo fees, standard carve-outs | 0·0·0·0·0·0·0·1·0·0·0 | — | 1 | LOW | Capped = correctly a non-issue |
| 5 | MSA | Vendor-only termination for convenience, 30-day notice | 0·0·0·0·0·0·3·1·0·0·0 | — | 7 | LOW | One-sided but constrained by notice — see §5.1 |
| 6 | MSA | Vendor-only termination for convenience, immediate, sole discretion | 0·0·0·0·0·0·3·1·0·2·0 | UD=3∧OC=2, one-sided | — | **HIGH** | Same clause type as #5, differs only by notice — a distinction legacy's single flat rule can't make |
| 7 | MSA | Mutual termination for convenience, 30-day notice | 0·0·0·0·0·0·0·1·0·0·0 | — | 1 | LOW | UD=0 via mutuality gate |
| 8 | Loan | Unlimited personal guaranty, "any and all obligations" | 3·0·0·0·0·0·0·1·0·0·0 | PE=3 | — | **CRITICAL** | |
| 9 | Loan | Limited personal guaranty, capped at $50,000 | 1·0·0·0·0·0·0·1·0·0·0 | — | 5 | LOW | Capped personal exposure is a real but modest fact |
| 10 | Loan | Confession of judgment / cognovit | 0·3·0·0·0·0·0·3·0·0·0 | RW=3 | — | **CRITICAL** | |
| 11 | Loan | Mandatory arbitration, neutral administrator, no other waivers | 0·2·0·0·0·0·0·1·0·0·0 | — | 9 | LOW | Plain arbitration alone is not top-tier |
| 12 | Loan | Jury-trial waiver only | 0·1·0·0·0·0·0·1·0·0·0 | — | 5 | LOW | |
| 13 | Loan | Arbitration + jury waiver + class-action waiver, stacked | 0·3·0·0·0·0·0·2·2·0·0 | RW=3 | — | **CRITICAL** | Three moderate waivers compounding into "no meaningful recourse" — RW's level-3 definition earns its keep here |
| 14 | Employment | Broad invention assignment, no own-time carve-out | 0·0·0·0·0·3·0·3·0·0·0 | AT=3∧REV=3 | — | **HIGH** | Matches legacy |
| 15 | Employment | Invention assignment with explicit own-time carve-out | 0·0·0·0·0·1·0·1·0·0·0 | — | 3 | LOW | Carve-out does real work |
| 16 | Employment | Standard mutual at-will disclaimer | 0·0·0·0·0·0·0·0·0·0·0 | — | 0 | LOW | Confirms mutuality gate fix (Refinement #4) |
| 17 | Employment | Non-compete, 2-year radius, no stated consideration | 0·0·0·0·1·0·0·1·0·0·1 | — | 4 | LOW | Enforceability is jurisdiction-dependent, correctly modeled outside intrinsic severity |
| 18 | Employment | Severance release, broad, no EEOC/whistleblower carve-out | 0·2·0·0·1·0·0·2·0·0·0 | — | 12 | LOW (boundary) | Right at the LOW/MEDIUM cut line — flagged for Phase-3 review, not force-resolved |
| 19 | Lease | Personal guaranty of all lease obligations, uncapped, full term | 3·0·0·0·0·0·0·1·0·0·0 | PE=3 | — | **CRITICAL** | |
| 20 | Lease | CAM charges, landlord sole discretion, no cap anywhere | 0·0·0·3·0·0·2·1·0·0·0 | FB=3 | — | **HIGH** | First pass mis-scored this FB=2 (see text below table) — corrected to FB=3, which is a stronger result than legacy's MEDIUM |
| 21 | Lease | Rent escalation capped at 3%/year | 0·0·0·0·0·0·0·0·0·0·0 | — | 0 | LOW | Capped = correctly a non-issue |
| 22 | Construction | Pay-if-paid | 0·0·0·3·0·0·0·2·0·0·0 | FB=3 | — | **HIGH** | Matches legacy after Refinement #3 |
| 23 | Construction | Lien waiver required before payment received | 0·1·0·2·0·0·0·2·0·0·0 | — | 10 | LOW (boundary) | Flagged for Phase-3 review against legacy MEDIUM |
| 24 | Construction | Retainage withheld, no release trigger | 0·0·0·2·0·0·0·1·0·0·2 | — | 7 | LOW | |
| 25 | Procurement | MFN clause | 0·0·0·0·0·0·0·0·0·0·0 | — | 0 | LOW | Correctly a pure commercial term |
| 26 | Procurement | Unlimited customer audit rights, no notice | 0·0·0·0·0·0·2·1·0·2·0 | — | 7 | LOW | |
| 27 | Partnership | Capital call default → uncapped dilution penalty | 0·0·0·0·0·3·3·3·0·0·0 | AT=3∧REV=3 | — | **HIGH** | First pass mis-scored AT=2 (see text below table) — corrected; framework recommends *upgrading* legacy MEDIUM |
| 28 | Partnership | 50/50 ownership, no deadlock mechanism | 0·0·0·0·0·0·0·1·0·0·2 | — | 3 | LOW | Absence-type finding — see Refinement #6 |
| 29 | M&A | Earnout metrics nominally formula-based, but final calculation and payment timing left to buyer's own auditors | 0·0·0·2·0·0·3·2·0·0·0 | UD=3∧FB≥2, one-sided | — | **HIGH** | FB=2 (not 3) deliberately — see erratum below the table: this is the row that actually exercises the UD/FB compound ceiling from Refinement #5, since a plain FB=3 vector would fire the simpler FB==3 ceiling first and never reach it |
| 30 | AI | Model training on customer data, no opt-out, "all data" | 0·0·0·0·3·3·2·3·3·0·0 | AT=3∧REV=3 (also RS=3∧SC=3 independently) | — | **HIGH** | Double-ceiling case — candidate for deferred CRITICAL-escalation rule, see Refinement log |
| 31 | Privacy | Unlimited data retention, no deletion right, regime not named | 0·0·0·0·2·0·0·2·2·0·2 | — | 10 | LOW (boundary) | |
| 32 | Privacy | Same, but clause explicitly names GDPR | 0·0·0·0·3·0·0·2·2·0·2 | — | 12 | LOW | Possible deferred ceiling (RS=3∧DUR=2), not adopted in v1.0 |
| 33 | Healthcare | PHI handling, no BAA execution requirement | 0·0·0·0·3·0·0·2·2·0·0 | — | 16 | LOW (boundary) | Just under the MEDIUM cut — flagged, not force-resolved |
| 34 | Government | FCA certification required, clause itself is routine/ambiguous drafting | 0·0·1·0·3·0·0·2·0·0·0 | — | 12 | LOW | Statutory exposure exists regardless of this clause — see §3 |
| 35 | Government | Mandatory flow-down clauses omitted (absence-type) | 0·0·0·0·2·0·0·1·0·0·0 | — | 5 | LOW | Absence-type, consistent with #28/#35 pattern |
| 36 | Consumer | Auto-renewal, 60-day notice, clearly disclosed | 0·0·0·0·0·0·0·0·0·0·0 | — | 0 | LOW | |
| 37 | Consumer | Auto-renewal, cancel only via certified mail in a 5-day annual window | 0·0·0·0·0·0·2·1·0·0·1 | — | 6 | LOW | Dark pattern, but state auto-renewal statutes are the right layer for this, not intrinsic severity |
| 38 | Boilerplate | Governing law / exclusive jurisdiction | 0·0·0·0·0·0·0·0·0·0·0 | — | 0 | LOW | |
| 39 | Boilerplate | Counterparts / e-signature | 0·0·0·0·0·0·0·0·0·0·0 | — | 0 | LOW | |
| 40 | MSA | Assignment restricted on change of control, no M&A carve-out | 0·0·0·0·0·0·2·1·0·0·0 | — | 5 | LOW | Most contestable disagreement in the set — see §5.1 |

**Erratum (found during implementation, corrected here rather than in a
silent edit):** row 29 originally scored FB=3, which the implementation's
unit tests caught as self-contradictory — a plain FB=3 fires ceiling rule 5
("FB == 3") on its own, before the UD/FB compound rule (rule 8) is ever
reached, so the original vector didn't actually demonstrate Refinement #5
as its note claimed. Corrected to FB=2 (a formula nominally exists but is
undermined by unilateral control over its application), which is the
genuine motivating case for the compound rule. Tier is unchanged (HIGH
either way); only the *reason* it fires was wrong. This is exactly the kind
of inconsistency the regression suite (`tests/test_severity_regression_corpus.py`)
and unit tests (`tests/test_severity_scoring.py`) exist to catch — it was
found by running this document's own vectors through the implemented engine,
not by re-reading prose.

**Implementation addendum (entries 41–43):** when this framework was
implemented as executable code (`severity_scoring.py`) and the table above
was converted into `tests/test_severity_regression_corpus.py`, an
automated coverage check (`test_corpus_exercises_every_ceiling_rule_at_least_once`)
found that 2 of the 8 ceiling rules — `CR == 2` and `FB == 3 and PE == 2`
— were never fired by any of the 40 hand-picked clauses above, and that
`RS == 3 and SC == 3` was *present* in row 30 but never actually
*recorded*, because row 30's `AT == 3 and REV == 3` combination fires
first (rules are checked in order, first match wins). Three entries were
added to close these gaps — a government false-statement clause for
`CR == 2`, a lease with both unlimited entity liability and a
capped-but-personal guaranty for `FB == 3 and PE == 2`, and a
GDPR-controller/broad-third-party-sharing clause with `AT`/`REV` kept
below 3 so `RS == 3 and SC == 3` is the rule that actually fires. All
three are corpus growth (architecture doc §14), not framework changes —
they add test evidence for existing ceiling rules, they don't add, remove,
or reweight anything. See `tests/test_severity_regression_corpus.py` for
the exact vectors.

### 5.1 Disagreements worth naming explicitly

- **#1 (perpetual confidentiality, LOW vs. legacy MEDIUM):** recommend
  **framework wins**. Duration alone, with no personal/financial/rights
  fact attached, is a compliance-burden item, not a legal-risk item. Legacy
  MEDIUM likely reflects "this is inconvenient to comply with," which is a
  different question than "this creates disproportionate exposure."
- **#5/#6 (termination for convenience, notice-dependent split):**
  recommend **framework wins and legacy should split into two rules** — a
  single flat HIGH severity for "termination for convenience" can't
  distinguish a properly-noticed exit right from an immediate,
  sole-discretion one, and the distinction is exactly the kind of thing a
  real negotiator cares about.
- **#20 (uncapped CAM, HIGH vs. legacy MEDIUM) and #27 (capital-call
  dilution, HIGH vs. legacy MEDIUM):** recommend **legacy be upgraded**.
  Both were caught by the framework's ceiling logic once scored correctly,
  and both involve genuinely unbounded exposure that legacy under-rated.
- **#18, #23, #33 (severance release, lien waiver, missing BAA — all LOW,
  legacy MEDIUM, all sitting within a few points of the band boundary):**
  recommend **neither wins outright — send to Phase-3 attorney
  calibration.** These are the honest boundary cases the threshold table
  (§6.3) is not yet confident enough to resolve unilaterally; they're
  exactly what the golden-set calibration pass exists for.
- **#40 (assignment-on-change-of-control, LOW vs. legacy HIGH):** the
  single most contestable result in the set. The framework's answer is
  principled (the clause only imposes a consent requirement; it doesn't
  block the transaction outright, waive a right, or create unbounded
  exposure), but the real-world severity of this clause is famously
  deal-size-dependent, which is precisely the kind of extrinsic fact §3
  excludes on purpose. Flagged for the most scrutiny of any row in Phase 3
  rather than resolved here.

---

## 6. Scoring algorithm

### 6.1 Ceiling rules (checked first, in order; first match wins)

```
1. CR == 2                                    -> CRITICAL
2. PE == 3                                    -> CRITICAL
3. RW == 3                                    -> CRITICAL
4. FB == 3 and PE == 2                        -> CRITICAL
5. FB == 3                                    -> HIGH   (floor)
6. AT == 3 and REV == 3                       -> HIGH   (floor)
7. RS == 3 and SC == 3                        -> HIGH   (floor)
8. UD == 3 and (OC == 2 or FB >= 2) and
   discretion is one-sided (party_direction)  -> HIGH   (floor)
```

**Hard invariant, stated explicitly and preserved from v0:** CRITICAL is
**only** reachable through rules 1–4. It is never reachable by aggregate
score alone. This means every CRITICAL finding has a one-sentence, citable
reason ("this rule fired because PE==3"), never an opaque "the weighted sum
happened to be high" — which is the single property that matters most for
legal defensibility, and stress-testing confirmed it holds (no clause in
the 40-clause set reached CRITICAL-range WAS without a ceiling firing).

### 6.2 Weighted Aggregate Score (WAS)

```
WAS = (PE + RW + CR) × 4  +  (FB + RS + AT + UD) × 2  +  (REV + SC + OC + DUR) × 1
```

### 6.3 Thresholds (derived independently, not fit to legacy — see §7)

Reachable range excluding all ceiling-triggering combinations (PE≤2, RW≤2,
CR≤1, FB≤2, and UD=3 only paired with OC<2 and FB<2): approximate max ≈ 52.

| WAS | Tier |
|---|---|
| Ceiling fired | CRITICAL or HIGH per §6.1 |
| ≥ 36 (≈70%) | HIGH |
| 18–35 (≈35–69%) | MEDIUM |
| 0–17 (< 35%) | LOW |

These are a **first-principles hypothesis**, explicitly not tuned to
reproduce legacy labels (per §7's mandate). The 40-clause test surfaced
four boundary cases (§5.1) sitting within a few points of the LOW/MEDIUM
line — expected, and exactly what the Phase-3 golden-set calibration
(§12) exists to resolve with actual attorney review, not further
first-principles guessing.

---

## 7. Threshold calibration methodology (as mandated: framework first, legacy compared after)

1. **Design independently.** §2–§6 were built and stress-tested (§5)
   entirely from the litmus test in §2, before consulting how any specific
   legacy rule was labeled.
2. **Apply to existing rules.** §5's 40 clauses include 11 direct restatements
   of last-session's rules (guaranty, confession of judgment, CAM,
   pay-if-paid, lien waiver, retainage, capital call, earnout, at-will,
   invention assignment, franchise-adjacent termination) plus several
   pre-v6 rule types (uncapped liability, IP assignment, perpetual
   confidentiality, non-compete, auto-renewal, governing law,
   counterparts).
3. **Compare.** §5.1 lists every disagreement found, in both directions —
   3 recommend the framework's answer over legacy, 2 recommend legacy be
   upgraded, 4 are genuine toss-ups deferred to attorney review, 1
   (assignment-on-change-of-control) is flagged as the most contestable
   result in the entire set rather than resolved by assertion.
4. **Recommendation:** the framework should **not** be re-tuned to make
   these disagreements disappear. Every one of them has a stated,
   defensible reason. The correct next step is Phase 2/3 of the migration
   (§12) — full retroactive scoring of all 117 rules by a
   contributor-plus-attorney pair, using this document's rubric, producing
   a complete disagreement list like §5.1 but exhaustive rather than
   representative. This document demonstrates the *method*; running it
   against all 117 (soon 500+) rules is real review work that shouldn't be
   simulated here.

---

## 8. Rule metadata schema

Unchanged in structure from v0's design, with `factor_vector` updated to
the 11-factor set above and `severity_derivation` updated to record which
of the 8 ceiling rules (or which band) produced the tier:

```python
@dataclass(frozen=True)
class RuleMetadata:
    rule_id: str
    rule_version: str                  # semver of this rule's definition — MANDATORY
                                        # purpose: lets a factor_vector change be diffed
                                        # against a specific prior version during audit.

    legal_domain: LegalDomain          # MANDATORY, controlled vocabulary
                                        # purpose: practice-area filtering/reporting only —
                                        # deliberately NOT used in severity or consistency
                                        # checks (that's clause_category's job, see below).

    clause_category: ClauseCategory    # MANDATORY, controlled vocabulary, cross-cuts domain
                                        # purpose: groups doctrinally-identical clauses
                                        # (e.g. "Indemnification" appears in MSAs, leases,
                                        # M&A alike) — this is what §9's monotonicity check
                                        # groups by, since severity correlates with clause
                                        # doctrine, not practice area.

    affected_party_role: PartyRole     # MANDATORY, controlled vocabulary
                                        # purpose: supports party_direction-aware UD scoring
                                        # (§2) and reporting ("show me every rule that can
                                        # bind a Guarantor").

    affected_asset: AssetType          # MANDATORY, controlled vocabulary
                                        # purpose: reporting/filtering; also a cross-check —
                                        # a rule with affected_asset=IP and AT=0 is a schema
                                        # inconsistency worth flagging (§9.5).

    factor_vector: Dict[str, FactorScore]  # MANDATORY — the actual source of truth
                                        # purpose: {"PE": FactorScore(level=3,
                                        # justification="...")} — every level requires a
                                        # justification string; a bare integer is a schema
                                        # violation. This is what makes blind re-scoring
                                        # (§10.7) checkable at all.

    severity_score: int                # MANDATORY, GENERATED — never hand-set
                                        # purpose: the computed WAS; recomputed by CI on
                                        # every change (§9.1) and must equal severity_tier's
                                        # derivation.

    severity_tier: Severity            # MANDATORY, GENERATED — never hand-set
                                        # purpose: the four-tier public projection (§ "Open
                                        # question" note below on why this stays 4 tiers).

    severity_derivation: SeverityDerivation  # MANDATORY, GENERATED
                                        # purpose: {method: "ceiling"|"band", rule_fired:
                                        # str|None, band: str|None} — the one-line answer
                                        # to "why is this CRITICAL," required by §6.1's
                                        # invariant.

    detection: DetectionSpec           # MANDATORY — unchanged from today's pattern/
                                        # anchors/nearby/topic/protective spec.
                                        # purpose: detection is orthogonal to severity by
                                        # design; kept as its own field so a severity-rubric
                                        # change never requires touching detection regex.

    prerequisite_facts: List[str]      # OPTIONAL (empty list valid)
                                        # purpose: deterministic scope-gating facts
                                        # independent of jurisdiction, e.g. "guarantor is a
                                        # natural person" — decides whether the rule applies
                                        # at all, not how severe it is once it does.

    jurisdiction_profile: List[JurisdictionModifier]  # OPTIONAL, empty by default
                                        # purpose: §11's overlay entries; empty means "no
                                        # jurisdiction-specific data known," a valid and
                                        # common state, not an error.

    rationale: str                     # MANDATORY
                                        # purpose: human-readable explanation, exists today,
                                        # unchanged — the plain-English complement to the
                                        # factor_vector's justifications.

    references: List[str]              # OPTIONAL but STRONGLY RECOMMENDED for Tier-A
                                        # ceiling-triggering rules specifically
                                        # purpose: statute sections/restatement citations —
                                        # required for legal defensibility of any CRITICAL
                                        # finding in particular.

    authored_by: str                   # MANDATORY
    reviewed_by: str                   # MANDATORY — see §10.8 sign-off requirement
    review_date: date                  # MANDATORY
                                        # purpose (all three): governance trail — who wrote
                                        # and who signed off, permanently.

    legacy_severity: Optional[Severity]  # MANDATORY once migration (§12) begins; None
                                        # before then
                                        # purpose: permanent historical record — "what was
                                        # this called before the rearchitecture, and does the
                                        # new tier disagree" — never deleted, per §7.4.

    schema_version: str                 # MANDATORY
                                        # purpose: lets old rule records be forward-migrated
                                        # mechanically when the schema itself changes.

    aliases: List[str]                  # OPTIONAL, unchanged from today.
```

Deliberately **excluded** from this schema, each for a stated reason:

- **Confidence** (evidentiary confidence a regex match is real) — already
  exists (`_score_confidence`) and must stay separate: a CRITICAL rule with
  a medium-confidence match is still CRITICAL if it fires. Merging the two
  would silently downgrade real risks over an unrelated evidentiary
  question.
- **Dispute frequency / telemetry** — a real and useful metric, but for a
  different reporting surface entirely; including it here would reintroduce
  exactly the "how often does this actually bite" factor §3 excludes from
  severity.
- **A raw numeric-only severity field with no tier** — rejected per the
  "Open question" resolution carried over from v0: the four-tier label
  remains the stable public contract for existing consumers
  (`signature_readiness`, `ONE_WAY_RULE_IDS`); `severity_score` is exposed
  alongside it for anyone who wants the finer-grained number, not instead
  of it.

---

## 9. Validation rules (CI-enforced)

1. **Recomputation check.** `severity_tier` must equal
   `compute_severity(factor_vector)` exactly; build fails otherwise.
2. **Cross-rule monotonicity within `clause_category`.** For any two rules
   A, B sharing a `clause_category`: if every factor level in A is ≥ the
   corresponding level in B (at least one strictly greater), then
   `severity(A)` must be ≥ `severity(B)`. Automatic, whole-rulebase version
   of "why is this HIGH when a strictly worse clause is MEDIUM."
3. **Duplicate/near-duplicate detection.** Similarity clustering over
   `rationale` + detection pattern flags candidates for human triage before
   merge.
4. **Ceiling-coverage keyword check.** A maintained keyword list scanned
   against `rationale`; presence of a high-risk term (e.g. "confession of
   judgment," "unlimited," "criminal") with no corresponding ceiling factor
   triggered is flagged for manual review — catches under-scoring.
5. **Schema validation.** Required fields present; every factor level has a
   non-empty justification; `clause_category`/`legal_domain`/
   `affected_asset` in their controlled vocabularies; any
   `jurisdiction_profile` entry carries a real citation.
6. **Golden-set regression.** A frozen set of attorney-confirmed
   `(factor_vector → tier)` examples, seeded from §5's 40 clauses plus the
   Phase-3 (§12) full retroactive pass, must still score correctly after
   any change to the scoring function or thresholds; any flip requires
   explicit sign-off.
7. **Detection-pattern test-coverage lint.** Every `rule_id` maps to at
   least one positive, one negative, and one messy-formatting test.
8. **Mutuality-gate sanity check (new, from Refinement #4).** Any rule
   scoring UD > 0 must have `affected_party_role` set to something other
   than a symmetric/mutual designation, or the PR is blocked — a structural
   backstop against reintroducing the mutual-at-will false positive.

---

## 10. Mandatory rule-authoring workflow

1. **Clause identification.** Assign `clause_category` from the controlled
   taxonomy; propose new categories via a separate taxonomy-governance PR.
2. **Factor scoring.** Score all 11 factors from §2, each with a
   justification string tied to specific clause language.
3. **Automated score computation.** Run `compute_severity()` — the
   contributor never hand-picks the tier.
4. **Derivation record auto-generated.**
5. **Detection pattern authoring.** Unchanged discipline: whitespace/
   line-wrap-tolerant regex, positive/negative/messy-formatting tests.
6. **Prerequisite facts & jurisdiction stub.** Declare `prerequisite_facts`;
   leave `jurisdiction_profile` empty absent a sourced citation.
7. **Blind re-score gate.** A second contributor, given only `rationale`
   and clause text (not the first scorer's vector), independently scores
   all 11 factors. A tier divergence blocks the PR until the *factor
   definitions* — not the tier — are reconciled.
8. **Subject-matter/legal sign-off.** `reviewed_by` recorded permanently.
9. **Automated validation suite passes** (§9).
10. **Documentation generated, not hand-written**, from the metadata store.

---

## 11. Jurisdiction architecture (reviewed, confirmed correct, one hardening added)

The four-stage pipeline from the prior draft survives the stress test
unchanged in structure — §5's non-compete example (#17) is direct evidence
it's necessary: identical clause text is banned in one state and standard
elsewhere, and intrinsic severity correctly stays constant across both
because §2's factors never reference governing law.

```
Rule
  │  (detection + factor_vector + rationale + clause_category)
  ▼
Intrinsic Severity                     <- §6, identical for every document,
  │                                        any governing law, always shown
  ▼
Applicability Layer  (per-document, deterministic)
  - resolve governing_law (extracted or declared)
  - look up JurisdictionModifier for (clause_category, governing_law)
  - absence of an entry is valid ("no jurisdiction-specific data known"),
    never an error and never "not risky"
  ▼
Jurisdiction Modifier Table (keyed by clause_category × jurisdiction,
  never by rule_id — one entry covers every rule in that category)
  - enforceability: valid | void | voidable | restricted | unsettled
  - severity_adjustment: none | -1_tier | +1_tier   (bounded to ±1 band)
  - statutory_citation, note
  ▼
Final Finding
  - intrinsic_severity (always present)
  - jurisdiction_adjusted_severity (present only if governing_law known)
  - enforceability_status
  - jurisdiction_confidence: known | assumed | unknown
```

**One hardening added in v1.0, made explicit rather than merely implied:**
a jurisdiction modifier may change `enforceability_status` and may apply a
bounded ±1-tier `severity_adjustment`, but it may **never** downward-adjust
a finding whose intrinsic severity was produced by a §6.1 ceiling rule.
Confession of judgment in California is `enforceability: void`, but its
`intrinsic_severity` stays CRITICAL — the drafting is still bad, and the
same document could be reformed, assigned, or re-drafted under a different
governing law. A jurisdiction table that could silently turn CRITICAL into
LOW would reintroduce exactly the subjectivity/inconsistency this whole
architecture exists to remove, just one layer downstream.

---

## 12. Migration strategy (unchanged in structure, confirmed by §7 as the right calibration mechanism)

**Phase 0 — Freeze & snapshot.** Tag current ruleset, copy every rule's
`severity` into permanent `legacy_severity`.

**Phase 1 — Additive schema introduction.** Add §8's fields as
optional/nullable; `analyze()` output unchanged; zero behavioral risk.

**Phase 2 — Retroactive factor scoring.** Score all 117 rules against §2
via the §10 workflow (contributor + attorney), producing `computed_severity`
alongside legacy `severity`.

**Phase 3 — Calibration.** Diff `computed_severity` vs. legacy `severity`
for all 117. Every mismatch root-caused per §7's method — most will
confirm legacy was analogy-drift (expected), some may reveal §6.3's
thresholds need adjusting; adjust and freeze, using §5's 40 clauses plus
this pass as the golden set (§9.6).

**Phase 4 — Shadow mode.** Ship `computed_severity` as a secondary field
for one release cycle; verify `overall_risk`, `signature_readiness`, and
`ONE_WAY_RULE_IDS` logic against it before anything user-facing changes.

**Phase 5 — Cutover.** `severity` becomes a generated property of
`computed_severity`; `legacy_severity` stays permanently.

**Phase 6 — Enforcement.** §9's validation suite becomes a hard CI gate;
this document becomes the CONTRIBUTING standard; "classify by analogy" is
removed from any remaining docs/prompts.

**Rollback:** fully additive/reversible through Phase 4; Phase 5 is a
one-line revert since nothing is deleted.

---

## 13. Governance

- This document is versioned (`v1.0` in its title). Changes to §2's factor
  definitions, §6's ceiling rules, or §6.3's thresholds are themselves
  governed changes: they require re-running the golden set (§9.6), and any
  tier flip they cause across existing rules must be individually reviewed
  and approved, not silently absorbed.
- No rule's `severity_tier` may be hand-edited under any circumstance;
  the schema should make the field structurally read-only, with §9.1's CI
  check as the backstop.
- `clause_category` and the jurisdiction taxonomy are separately governed
  vocabularies (their own lightweight PR process) — never extended inline
  inside a rule-adding PR, to keep the grouping stable enough for §9.2's
  monotonicity check to mean anything over time.

---

## 14. Future extensibility guidance

- **New practice areas** (e.g., insurance, IP licensing/patent
  prosecution, environmental) need no new severity machinery — only new
  `clause_category` entries scored against the same 11 factors, per the
  standard §10 workflow.
- **New factors** should be added only after a stress-test failure like
  those in §4 — a factor invented speculatively, without a concrete clause
  that breaks without it, is exactly the kind of ungrounded addition this
  document was written to prevent. Two deferred candidates are already on
  record for the next stress-testing pass: a compound-ceiling escalation
  rule for simultaneous independent ceiling triggers (§4, deferred), and a
  possible RS×DUR ceiling for perpetual-plus-named-regime data clauses
  (§5, row 32).
- **The four-tier public projection** should stay four tiers for human-
  facing surfaces indefinitely; `severity_score` (the raw WAS) is already
  exposed in the schema for any future automated consumer that outgrows
  four buckets — that's a scoped follow-up against the existing field, not
  a reason to revisit this document's core design.
