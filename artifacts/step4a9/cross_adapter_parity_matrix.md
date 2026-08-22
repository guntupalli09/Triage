# Step 4A.9 — Cross-Adapter Safety-Capability Parity Matrix

| Capability | Liability | Indemnification | Payment Terms |
|---|---|---|---|
| Role verification (escalate on unresolved role/side) | SUPPORTED | SUPPORTED | SUPPORTED |
| Unmapped-role-pair attribution (A6-L-52 family) | SUPPORTED | N/A (uses reciprocal/named-pair term-invariance instead) | N/A (role attribution not cap-bearing in this adapter) |
| Conflicting definitions | SUPPORTED (fixed Step 4A.9: interposed "is...defined") | SUPPORTED (added Step 4A.7.3, category-scoping) | SUPPORTED (added Step 4A.7.4, two shapes) |
| Conditional applicability | SUPPORTED — shared `CONDITIONAL_UNVERIFIED_PRECONDITION_RE` (widened Step 4A.9) | PARTIAL — own `_CONDITIONAL_CAP_ESCALATION_RE` for the bifurcated-cap shape; does not yet use the shared proviso regex | SUPPORTED — shared `CONDITIONAL_UNVERIFIED_PRECONDITION_RE` |
| Self-flagged unresolved scope | SUPPORTED — shared `SELF_FLAGGED_UNRESOLVED_RE` (promoted Step 4A.9) | SUPPORTED — shared `SELF_FLAGGED_UNRESOLVED_RE` (promoted Step 4A.9) | SUPPORTED — shared `SELF_FLAGGED_UNRESOLVED_RE` (promoted Step 4A.9) |
| Chained delegation | SUPPORTED — shared `CHAINED_DELEGATION_RE` (widened Step 4A.9: "defers to") | SUPPORTED — shared `CHAINED_DELEGATION_RE` (added Step 4A.7.3) | SUPPORTED — shared `CHAINED_DELEGATION_RE` + single-hop "(not included...)" variant (added Step 4A.7.3) |
| False-absence protection (discovery failure != absence) | N/A — liability's own anchor/basis extraction was never closed-idiom-based; this was never a liability-specific risk | **SUPPORTED as of Step 4A.9** (was the Step 4A.8 headline finding — closed idiom enumeration collapsed discovery failure into absence) | N/A — payment recognition already used a broad multi-signal anchor set (Step 4A.3), not a closed idiom list |
| Wrong-provision substitution protection | SUPPORTED (Step 4A.8 Family C tested, held) | Not independently tested at this depth in Step 4A.9 | SUPPORTED (security-deposit exclusion, Step 4A.7.3) |
| Spelled-out ("one (1)") multiplier numbers | SUPPORTED (original) | **SUPPORTED as of Step 4A.9** (was 0/97 verified pre-fix; shared `WORD_NUMBERS` primitive) | N/A (no multiplier concept — payment terms are Net-days/rate-based, not multiplier-of-fee-based) |
| Causation-standard comparison | N/A (liability has no causation-standard concept) | SUPPORTED (adverb-tolerant as of Step 4A.7.4) | N/A |
| Reciprocal asymmetry detection | N/A (liability has no reciprocal-obligation concept) | SUPPORTED (0/39+ tested cases show unsafe false-symmetry across Step 4A.8/4A.9) | N/A |
| Material-fact verification (ESTABLISHED vs UNVERIFIED tracking) | SUPPORTED (audited Step 4A.7.5/4A.9, 0 UNVERIFIED-CA) | SUPPORTED (audited Step 4A.9, 0 UNVERIFIED-CA, was 2 pre-fix) | SUPPORTED (audited Step 4A.7.5/4A.9, 0 UNVERIFIED-CA) |
| Broad discovery + independent verification (vs. exact-phrase-only recognition) | PARTIAL — anchor-based discovery is already broader than a phrase enumeration, but has not been redesigned around the explicit discovery/verification separation this step introduced for indemnification | **SUPPORTED as of Step 4A.9** (this step's primary deliverable) | PARTIAL — same as liability |

## What this matrix exposes

The self-flagged-unresolved and chained-delegation rows show the exact
drift pattern Step 4A.8 predicted: three (then two) independently-written
copies of the same concept, missing different phrases in each adapter,
with at least one fix (`determination having yet been made`) added to
liability in Step 4A.7.4 and never propagated. Both are now single shared
primitives in `policy_engine_core.py`; a future fix to either only needs to
be written once.

Indemnification's conditional-applicability row remains PARTIAL — its
`_CONDITIONAL_CAP_ESCALATION_RE` (the bifurcated-cap-tier shape) is a
genuinely different concept from the shared PROVIDED-THAT/UNLESS proviso
regex (an unresolved precondition gating a single stated value) and was
correctly left adapter-local; whether it's ALSO missing the more general
concept is a real open question this step did not fully close (see Section
Y of the final report).
