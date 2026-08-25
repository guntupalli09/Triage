# AUTHORITY_BOUNDARY

The core rule this whole mission exists to enforce:

**AI may discover, interpret, challenge, or verify candidate evidence.
AI must never determine ACCEPT / ACCEPT_WITH_NOTE / NEGOTIATE /
MUST_REDLINE / PROHIBITED / policy compliance / document risk / final
document state / interaction outcome.**

## Where this is enforced, mechanically, not by convention

1. **`fact_admission.CandidateMaterialFact` has no policy field.**
   `_FORBIDDEN_FIELD_NAMES` (fact_admission.py) plus
   `assert_authority_boundary_intact()` raise if the dataclass schema ever
   grows a field like `policy_state`, `compliant`, `decision`. Same
   pattern as the pre-existing `semantic_discovery.DiscoveryCandidate`
   guard, applied to the new shared schema.

2. **The only output vocabulary this module has is fact-admission states
   (`ESTABLISHED`/`NOT_ESTABLISHED`/`AMBIGUOUS`/`INSUFFICIENT_CONTEXT`/
   `CONFLICTING`/`DEPENDENCY_UNRESOLVED`/`VERIFICATION_ERROR`) plus
   `ADMITTED`/`NOT_ADMITTED`.** None of these strings are
   `policy_engine_core` decision states. `evaluate_admission()` cannot,
   structurally, produce `ACCEPT`/`NEGOTIATE`/etc. — it isn't in its
   vocabulary.

3. **An admitted candidate is not a decision — it is permission to enter
   the SAME deterministic structuring any regex-found anchor already goes
   through.** In `liability_policy_engine.py`, a semantically-admitted
   candidate's `start_offset` seeds `_extract_provision()`, the identical
   function a deterministic `_ANCHOR_RE` match seeds. If that deterministic
   structuring can't build a comparable cap expression, the result is
   `REQUIRES_REVIEW` regardless of how the anchor was found. The AI never
   supplies a cap number, a party role, or a policy verdict — only "look
   here."

4. **Grounding is independent of the verifier's own claim.**
   `ground_evidence_quote()` re-locates the verifier's cited evidence via
   exact substring search against the untouched source text. A verifier
   claiming `ESTABLISHED` with a fabricated or paraphrased quote fails
   grounding and is `NOT_ADMITTED` regardless of its claimed status
   (`test_verify_and_ground_end_to_end_fabricated_evidence_not_admitted`).

5. **Fail-closed is structural, not a convention followers might forget.**
   `verify_candidate_proposition()` converts every provider failure mode
   (missing key, network error, malformed JSON, empty response, invalid
   enum, contradictory ESTABLISHED-with-no-evidence) into
   `VERIFICATION_ERROR` — a member of `_UNSAFE_VERIFICATION_STATES`, which
   `evaluate_admission()` checks before anything else. There is no code
   path from a provider exception to `ADMITTED`.

6. **Adapters map `NOT_ADMITTED` to a pre-existing safe deterministic
   state, never invent a new one.** `liability_policy_engine.py` maps
   `RECOGNITION_UNCERTAIN` to `REQUIRES_REVIEW` — a state
   `interaction_engine_core._UNSAFE_PARTICIPANT_STATES` and
   `document_aggregation._POLICY_REVIEW_STATES` already treat as
   unsafe-to-treat-as-clean. No new document-level or interaction-level
   state was introduced by this change — the existing fail-closed
   machinery (§4/§7 of PRE_IMPLEMENTATION_MAP.md, already correct) absorbs
   it without modification.

## What this buys, concretely

A prompt-injection attempt embedded in contract text, or a model that
hallucinates a favorable clause, cannot reach a policy decision: at worst
it produces a candidate that fails grounding (discarded before
verification) or a verifier output that fails the admission gate
(`NOT_ADMITTED` -> `REQUIRES_REVIEW`). The worst outcome an adversarial or
malfunctioning AI call can cause is an unnecessary escalation to human
review — never a false ACCEPT, and never a fabricated MUST_REDLINE (the
adapter's own deterministic evaluator, unchanged, still owns that
decision, over facts extracted through its own unchanged structuring
logic).
