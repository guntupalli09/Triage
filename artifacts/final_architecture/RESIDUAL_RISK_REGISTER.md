# RESIDUAL_RISK_REGISTER — Final Trust Architecture

## Closed this session

1. **Phase 0 re-verification**, surfacing two findings the prior branch's
   artifacts did not state sharply: (a) the entire modern 12-adapter
   engine + interaction engine only runs in `POLICY_ENFORCEMENT_MODE=cutover`,
   which defaults to `"shadow"`; (b) no environment-variable-driven
   configuration existed for the semantic-discovery layer.
2. **Phase 12 (partial)**: `fact_admission.semantic_discovery_enabled()`
   makes all 11 newly-integrated adapters' flags environment-configurable,
   plus a global `FACT_ADMISSION_MODE=enforced` switch. 7 new tests, 0
   regressions (1266 passed total, up from 1259).

## Open, ranked by materiality

1. **Unknown production enforcement mode.** This session cannot determine
   whether triagecounsel.com's actual deployment has
   `POLICY_ENFORCEMENT_MODE=cutover` set. This single fact determines
   whether everything in `artifacts/fact_admission_architecture/` and
   this session's work has ever been live for a real user. Must be
   checked against actual deployment configuration before any further
   claim is made either way.
2. **No live-model validation exists for 11 of 12 adapters.** Every
   targeted test mocks the provider. Indemnification alone has real
   200-call evidence, from before either session.
3. **AI-identified qualifiers (conditions/provisos/exceptions/cross-
   references) are not preserved onto `CandidateMaterialFact`.** The
   schema has the fields; no adapter populates them from the semantic
   layer's own contextual read. Only the pre-existing regex-based
   condition detectors run over semantically-discovered text.
4. **No canonical, structured context package (Phase 1).** The full
   document text is sent as context, which is a defensible interim
   choice but not the mission's asked-for bounded, source-coordinate-
   preserving package with separated heading/definition/party fields.
5. **No version provenance for the semantic layer** in
   `policy_revision_metadata_json`.
6. **Fresh frozen 600-case corpus**: not created (no live provider
   budget/authorization).
7. **Live triagecounsel.com validation**: not performed (no deployment/
   browser access; even if performed, would show no new behavior given
   #1 and the fact every flag defaults off).
8. **45 test files environment-blocked** in this sandbox (missing
   `fastapi`/`python-docx`/`cryptography`) — any regression reachable
   only through those paths, including the review-page HTTP route added
   in the prior branch, is unverified by execution in this sandbox.
9. **Adversarial test family breadth** (Phase 6) is narrower than the
   mission's full specification — one NOT_ESTABLISHED family per adapter,
   not ~10 distinct named categories (hypothetical, quoted, recital,
   etc.) per adapter (see ADVERSARIAL_TEST_MATRIX.md).
10. **No automated detection of a misconfiguration risk**: an operator
    believing 12-adapter coverage is active while `POLICY_ENFORCEMENT_MODE`
    silently defaults to `"shadow"` receives no warning anywhere in the
    product (AUTHORITY_BOUNDARY.md).

## What was deliberately NOT done, and why that is correct restraint

- **`POLICY_ENFORCEMENT_MODE` was not changed and no adapter flag was
  enabled.** Doing so would be a live production activation decision
  gated behind Phase 15's hard release gates (items 2, 13, 14 of which
  cannot be satisfied this session). Making that change anyway would be
  exactly the "declare success because implementation is complete"
  failure mode this mission opens by prohibiting.
- **No frozen corpus was fabricated**, and no live screenshots were
  fabricated or substituted with localhost evidence. Both are explicitly
  forbidden by this mission, and reporting FAIL honestly on unfinished
  gates is the correct outcome per the mission's own stated rule ("If you
  cannot finish all gates, verdict = FAIL / NOT RELEASE-READY").
- **Indemnification was not migrated onto the shared framework.**
  Migrating a separately frozen, already-validated system for no safety
  benefit would introduce risk without a corresponding gain.
