# Step 4B Phase E — ≥3-Policy Compound Interactions

## Corpus

`benchmarks/step4b_phaseE_compound_benchmark.py` — 150 documents (meets
the ≥150 minimum), 3 buckets (50 exactly-3-policy, 50 4-to-6-policy, 50
7-plus-policy up to all 12), built only from combinations supported by the
real 12-adapter catalog and the real 7-rule `interaction_rules.LAUNCH_CATALOG`
— no invented interactions. 104 documents activate ≥1 interaction (exceeds
the ≥75 minimum); 40 activate ≥2 interactions simultaneously (meets the
≥40 minimum, after one recipe was added specifically to close the gap —
disclosed below).

Named-combination families exercised where the actual catalog supports
them: Liability+Indemnification(+Insurance), Termination+Payment Terms,
SLA+Payment(+Liability), plus multi-interaction compositions (one policy
feeding two interactions via a shared `data_breach` category; two
interactions sharing a `payment_terms` participant; two fully independent
interaction pairs firing in the same document; three-plus interactions
firing at once). Every document is run through the real
`interaction_engine_core.evaluate()` + real
`document_aggregation.aggregate_document_state()`, never reimplemented.

## Result

**Document-state: 150/150 (100%) on the first run.** All six hard gates
PASS: `base_finding_suppression`, `interaction_suppression`,
`wrong_participant`, `uncertainty_laundering`, `false_clean_document`,
`wrong_attention_state` — all 0.

**Interaction-count: 149/150 on the first run**, one predeclared-ground-
truth undercount (not a production defect): `7plus-policy-three-plus-interactions`
was predeclared to fire 3 interactions but the real engine correctly fires
4 (IP-uncapped, shared-category, and cyber-insurance all `ESCALATE`, plus
the SLA/payment-credit dependency `REQUIRES_REVIEW` — the fixture
legitimately satisfies all four rules' trigger conditions simultaneously,
which I undercounted when authoring the case). Verified directly against
`interaction_engine_core.evaluate()`'s actual output before correcting;
the document-level state (`HAS_CRITICAL_INTERACTION`) was unaffected by
this ground-truth error, since 3 or 4 ESCALATE-tier firings both resolve
to the same document state. Corrected to 4, disclosed here rather than
silently fixed. Re-run: **150/150 on both metrics.**

## Construction note

An initial draft of this corpus (structurally identical to Phase A's
approach) coupled combo selection and interaction-setup selection to the
same modulo cycle, which meant several intended `elif`-guarded interaction
setups could structurally never fire (their `issubset` guard was always
false given which combo the same index always produced). Caught before
committing by directly measuring `n_interactions_fired >= 1` across the
draft corpus (21/150, far short of the ≥75 target) rather than trusting
the family labels — rewritten with explicit, decoupled per-recipe
combo+setup pairing (`_RECIPES_3POLICY`/`_RECIPES_4_6`/`_RECIPES_7PLUS`)
so every intended interaction setup is guaranteed reachable. This was a
benchmark-construction defect, caught and fixed before any run was
trusted as evidence — not a production issue.

## Conclusion

No production defect found in Phase E; no production file was modified.
The interaction engine and document aggregation function both compose
correctly across realistic ≥3-policy documents, including cases where one
policy feeds two interactions, two interactions share a participant, and
3-4 interactions fire simultaneously in one document.

## Regression

- Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed**.
- No production file changed this phase, so the other benchmark suites
  (Phase A/B/C/D, 104/213/54/18-case suites, Step 4A.11 corpora) are
  unaffected by construction.
