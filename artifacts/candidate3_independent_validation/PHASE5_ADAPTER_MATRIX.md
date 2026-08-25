PHASE 5 — 12-ADAPTER COVERAGE MATRIX (one-shot execution, no hidden aggregate numbers)

| Adapter | Cases | Correct | False Safe | False Absence | False Operative→Clean | Silent Context Loss | Unresolved Dependency→Clean | False Escalation | Final Gate |
|---|---|---|---|---|---|---|---|---|---|
| 01. Limitation of Liability | 56 | 50 | 0 | 0 | 0 | 0 | 0 | 11 | **PASS** |
| 02. Indemnification | 55 | 49 | 0 | 0 | 0 | 0 | 0 | 12 | **PASS** |
| 03. Termination | 56 | 43 | 0 | 0 | 0 | 1 | 0 | 12 | **FAIL** |
| 04. Confidentiality | 55 | 36 | 0 | 0 | 0 | 0 | 0 | 12 | **PASS** |
| 05. Assignment | 54 | 41 | 0 | 0 | 0 | 1 | 0 | 12 | **FAIL** |
| 06. Governing Law | 54 | 42 | 0 | 0 | 0 | 0 | 0 | 6 | **PASS** |
| 07. Data Protection & Security | 55 | 36 | 0 | 0 | 0 | 0 | 1 | 6 | **FAIL** |
| 08. IP Ownership & Licensing | 55 | 35 | 0 | 6 | 0 | 0 | 8 | 0 | **FAIL** |
| 09. Insurance | 55 | 19 | 0 | 0 | 0 | 0 | 12 | 0 | **FAIL** |
| 10. Payment Terms | 56 | 54 | 0 | 0 | 0 | 0 | 0 | 9 | **PASS** |
| 11. Warranties | 54 | 37 | 0 | 3 | 0 | 0 | 5 | 0 | **FAIL** |
| 12. SLA / Service Levels | 55 | 48 | 0 | 0 | 0 | 1 | 0 | 0 | **FAIL** |

**5 of 12 adapters (Liability, Indemnification, Confidentiality, Governing Law, Payment Terms)
pass with zero hard-gate violations. 7 of 12 (Termination, Assignment, Data Security, IP
Ownership, Insurance, Warranties, SLA) have at least one confirmed hard-gate violation.**

No FALSE_SAFE and no FALSE_OPERATIVE→CLEAN was found in any adapter — the two most severe gate
categories (a confidently-wrong finding, and a genuinely-non-operative clause being
misclassified as clean-and-operative) are clean across all 12 adapters. The violations found are
concentrated in FALSE_ABSENCE (IP Ownership, Warranties) and UNRESOLVED DEPENDENCY→CLEAN
(Insurance, IP Ownership, Warranties, Data Security) plus isolated SILENT CONTEXT LOSS instances
(Termination, Assignment, SLA) — see `PHASE4_HARD_SAFETY_GATES.md` for root-cause detail on each
category.

Every adapter executed with real AI discovery, real verification, and real deterministic
grounding under `FACT_ADMISSION_MODE=enforced` — no adapter was skipped or excluded from this
run.
