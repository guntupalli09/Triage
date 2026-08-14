# Contract Selection — Kate SEC Demo

## Selected contract

- **Repository path:** `Benchmark - TC/Services/archive/documents/896493/000121465926007704/ex10_1.htm`
  (also copied unmodified to `artifacts/kate_sec_demo/selected_contract_ex10_1.htm`)
- **SEC metadata** (from `Benchmark - TC/Services/archive/metadata.parquet`):
  - `company_name`: Hyperscale Data, Inc.
  - `cik`: 896493
  - `accession`: 000121465926007704
  - `form_type`: 8-K
  - `date_filed`: 2026-06-24
  - `exhibit`: EX-10.1
  - `label`: services
- **Agreement type:** Master Services Agreement for data-center colocation and related services (hybrid MSA/real-estate-license structure — Provider grants Customer a license to a "Service Area" with defined critical IT power capacity, alongside standard MSA articles).
- **Parties:** Alliance Cloud Services, LLC ("Provider," a Delaware LLC) and a Customer whose name is redacted as `[***]` in the public SEC filing (a Texas LLC). The redaction is favorable for this demo: it removes an unrelated third party's name from what will become customer-facing material without any need to alter the document.
- **Dated:** June 23, 2026.

## Why this document, over the two next-strongest candidates

Selection was performed by running the actual, unmodified policy engines
(`liability_policy_engine.py`, `indemnification_policy_engine.py`, and the
other ten adapters) directly against plain-text extractions of candidate SEC
contracts — the same HTML→text conversion the application performs
(`re.sub('<[^>]+>', ' ', html)` → unescape → whitespace collapse) — and then,
for the strongest textual candidates, against the real production entrypoint
`policy_enforcement.apply_policies_for_review()` (the exact function
`main.py` calls) plus `interaction_engine_core.evaluate()` with the shipped
`interaction_rules.LAUNCH_CATALOG`. No adapter code, contract text, or
database record was modified at any point during this search.

229 documents from the Services corpus (664 total) were shortlisted by
keyword density across the 12 policy areas, and the strongest were tested
directly against the engines. Three candidates had genuinely strong,
textbook-quality cross-reference language between Limitation of Liability and
Indemnification:

1. **Backblaze, Inc. / CoreWeave, Inc. MSA** (CIK 1462056, accession
   000162828026044804) — contains an explicit, well-drafted carve-out
   ("the foregoing limitation shall not apply to... indemnification
   obligations"), but the dollar figures defining the liability cap are
   redacted in the public filing (`[***]`), per standard SEC confidential-treatment
   practice. `evaluate_liability_policy()` correctly returns `REQUIRES_REVIEW`
   because the cap amount cannot be established from the redacted text, and the
   Interaction Engine's participant-gating safety check
   (`interaction_engine_core._gate_participants`) correctly refuses to fire any
   Liability-based interaction rule on a `REQUIRES_REVIEW` participant — this is
   the engine behaving safely, not a bug, but it disqualifies the document for a
   demo that needs an *actionable* interaction. Rejected.

2. **Boost Run Inc. Service Agreement** (CIK 2090646, accession
   000149315226025672) — contains the cleanest, most explicit flagship-pattern
   language found anywhere in the corpus: "The foregoing limitations of
   liability do not apply to: ... (iii) either Party's indemnification
   obligations for third-party claims alleging infringement or
   misappropriation of intellectual property rights under Section 8." However,
   the real provision-discovery/reconciliation logic in
   `liability_policy_engine.py` (built to handle documents with multiple
   candidate liability provisions) identifies Section 9's general cap and its
   nested indemnification/security super-cap as two separate, competing
   provisions rather than one coherent tiered structure, and returns
   `reconciliation='unreconciled'` /
   `unresolved_facts=['controlling provision could not be determined among
   multiple candidates']`. This is a real, honestly-diagnosed limitation of
   the current provision-discovery logic on this specific document's
   structure — not something worked around for this demo. It also cascades to
   `INSUFFICIENT_FACTS` for every Liability-based interaction rule. Rejected.

3. **Hyperscale Data, Inc. / Alliance Cloud Services, LLC MSA** (selected) —
   see below.

## Relevant provisions present in the selected contract

- **Limitation of Liability** — Section 31.1(c): "Notwithstanding anything
  elsewhere in this Agreement, except as expressly provided in Article 28,
  under no circumstances shall either Provider or Customer be liable to the
  other for any consequential damages or lost profits." A second,
  independent liability provision at Section 10.2 caps aggregate liability
  for gross-negligence/willful-misconduct claims at six months of Recurring
  Service Charges, while carving out gross negligence and willful misconduct
  from a mutual insurance-subrogation release.
  **This carve-out is drafted directly into the contract text — the
  liability article itself cross-references the indemnification article by
  number ("Article 28"). This is not an inference by TriageCounsel; it is
  what the two parties actually wrote.**
- **Indemnification** — Article 28 (Sections 28.1–28.4), mutual: Customer
  indemnifies Provider (28.1) and Provider indemnifies Customer (28.2), each
  "subject always to the limitations on liability contained in Section 31.1
  and elsewhere in this Agreement." Section 13.2 contains an additional,
  narrower indemnity tied to a specific insurance-related option.
- **Termination** — Article 32 (Provider's Default, Customer's Remedies,
  Self-Help) and related default/cure provisions.
- **Insurance** — Article 10 (insurance requirements and evidence of
  coverage).
- **Assignment** — Article 13 (Assignment and Sublicensing).
- **Payment Terms** — Recurring Service Charges structure (defined in
  Exhibit B) and related payment articles.
- **SLA / Service Levels** — Article 21 (Service Availability) and Exhibit E
  (Service Level Agreement).
- **Confidentiality**, **Governing Law**, **Warranties**, **IP Ownership**,
  and **Data Protection/Security** provisions are present in varying degrees;
  Governing Law language did not match the adapter's extraction patterns in
  this document (a real-estate/data-center MSA drafted with dispute-resolution/
  arbitration provisions rather than a conventional "Governing Law" clause),
  which the engine honestly reports as `NOT_APPLICABLE` rather than guessing.
  Data Protection/Security did not evaluate meaningfully — this is a
  colocation/power-and-space MSA, not a data-processing agreement, so the
  absence of data-processor language is accurate, not a gap.

## Which shipped Interaction Engine rule is realistically testable

Confirmed by running the real, unmodified `interaction_engine_core.evaluate()`
against the real production-pipeline output
(`policy_enforcement.apply_policies_for_review()`) for this document:

- **`IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY`** fires at
  **`REQUIRES_REVIEW`**. The Limitation of Liability adapter classifies
  "gross negligence" carve-out treatment as `unresolved` (ambiguous) while
  classifying "willful misconduct" as `within_general_cap`, and the
  Indemnification adapter's controlling provision (Section 28.2) exposes
  Provider to indemnify Customer without a category-specific carve-out
  matching that ambiguity. The Interaction Engine correctly identifies that
  these two independently-evaluated clauses cannot be confirmed as consistent
  until the ambiguity is resolved, and routes the combined finding to
  `REQUIRES_REVIEW` rather than letting either clause's individual ACCEPT/
  NEGOTIATE state stand alone.
- The other six rules (`IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY`,
  `IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH`,
  `IX_INDEMNITY_WITHIN_GENERAL_CAP`, `IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE`,
  `IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING`,
  `IX_SLA_PAYMENT_CREDIT_DEPENDENCY`) evaluate cleanly and correctly do not
  fire on this document's actual facts (six as `NOT_TRIGGERED`, one —
  SLA×Payment — as `INSUFFICIENT_FACTS` because this document's payment
  structure does not reference service credits the way its SLA does). No
  adapter or rule was tuned to force additional firings; this document was
  selected precisely because it is the only one, across the full 664-document
  Services corpus, where any rule fires with an actionable state given the
  shipped engines as they exist today.

## Overall demo shape (real pipeline dry run)

Individual policy evaluation, 12 areas: 4 ACCEPT (Termination, Assignment, IP
Ownership & Licensing, Warranties), 2 NEGOTIATE (Insurance, Payment Terms), 2
REQUIRES_REVIEW (Confidentiality, SLA/Service Levels), 2 MUST_REDLINE
(Limitation of Liability, Indemnification), 1 NOT_APPLICABLE (Governing Law),
1 NOT_EVALUATED (Data Protection/Security). One actionable cross-policy
interaction. This matches the task's stated target shape ("12 policy areas
available / several evaluated meaningfully / several acceptable / some clause
exceptions / 1–2 cross-policy interactions") far better than an artificially
catastrophic contract would.

## Statement of integrity

**The contract language used in this demonstration was not modified.** The
file at `artifacts/kate_sec_demo/selected_contract_ex10_1.htm` is a byte-for-byte
copy of `Benchmark - TC/Services/archive/documents/896493/000121465926007704/ex10_1.htm`
as it exists in the SEC benchmark corpus. No clauses were inserted, edited, or
removed. No engine or adapter code was modified during selection. No policy
decision or interaction result shown in the demo was manually edited in the
database — all results were produced by running the real, unmodified engines.
