# Step 4A.10 Phase 2 — Fresh Read-Only Authority-Boundary Audit

Traced directly from source at frozen SHA `5afbda9` (re-read in full this
session, not assumed from prior reports).

## Full path: semantic API response -> policy decision

```
semantic_discovery_real.discover_candidate_spans_real(text, concept)
  -> HTTP POST to api.anthropic.com/v1/messages
  -> payload["content"] text blocks concatenated -> raw_text
  -> _extract_json(raw_text) -> parsed dict (or exception/None on malformre)
  -> parsed["candidates"]: list of {"quote": str, ...other keys ignored...}
  -> for each item: ONLY item["quote"] is read. ANY other key present
     (policy_result, cap_amount, compliant, our_side, etc.) is never
     accessed by this code — Python dict access is by explicit key name
     only; there is no wildcard/spread that could smuggle extra keys in.
  -> start = document_text.find(quote)  [OUR code's own exact search,
     never the model's own offset claim -- the model is never even asked
     for offsets]
  -> if start == -1: candidate discarded (hallucination)
  -> else: DiscoveryCandidate(concept, evidence_span=quote, start_offset,
     end_offset, source="SEMANTIC_REAL", discovery_metadata={...}).
     DiscoveryCandidate is a FROZEN dataclass with exactly 6 fields
     (semantic_discovery.py) -- no field exists to hold a party, side,
     cap, multiplier, or policy outcome even if the model had supplied one.
  -> indemnification_policy_engine._run_semantic_discovery wraps this in
     try/except; any exception/None/non-list result -> ([], error_string),
     never raises into extract_indemnification_facts.
  -> extract_indemnification_facts: candidates deduped against regex-
     discovered spans (_spans_overlap, >50% overlap threshold), then each
     survivor passed to _verify_semantic_candidate.
  -> _verify_semantic_candidate:
       1. RE-CHECKS text[start_offset:end_offset] == evidence_span
          (redundant with the module-level check, defense in depth).
       2. Runs the window through _OBLIGATION_RE and every entry in
          _SYNONYM_OBLIGATION_RES -- the IDENTICAL deterministic regex
          objects the pure-regex discovery path uses. indemnifying_role/
          indemnified_role/indemnifying_side/indemnified_side/monetary/
          scope/defense_control/causation/asymmetry_reasons/self_flagged
          are ALL computed by these regex matches and the existing
          resolve_role_side/_classify_* functions -- NONE of them read
          candidate.discovery_metadata or any text the model wrote beyond
          the verbatim quote itself.
       3. If no structuring regex matches: falls to
          _risk_transfer_signal_present(candidate.evidence_span) (also a
          plain regex over the VERIFIED VERBATIM text, not model output)
          -> UNRESOLVED (safe, non-authoritative) or REJECTED.
  -> Only a "VERIFIED" IndemnityObligation is appended to
     IndemnificationFacts.obligations; UNRESOLVED/REJECTED never are.
  -> evaluate_indemnification_policy consumes IndemnificationFacts ONLY
     (never touches the raw semantic response, ever) to emit
     ACCEPT/ACCEPT_WITH_NOTE/MUST_REDLINE/PROHIBITED/ESCALATE/
     REQUIRES_REVIEW/NOT_APPLICABLE.
```

## Explicit checks required by Phase 2

1. **Semantic actor labels cannot become authoritative actor labels.**
   CONFIRMED — `indemnifying_role`/`indemnified_role` come from
   `structuring_re.search(window).group(1)/(2)`, i.e. the deterministic
   regex's own capture groups applied to the verified verbatim text, never
   from any field the model returned.
2. **Semantic interpretation cannot establish directionality.**
   CONFIRMED — directionality is which regex alternative matched and in
   which group order; identical code path to pure-regex discovery.
3. **Semantic monetary values cannot become authoritative values.**
   CONFIRMED — `monetary=_classify_monetary(window, ...)`, same function,
   same regex set (`_MONETARY_MULTIPLIER_RE` etc.) as the regex-only path.
4. **Semantic policy recommendations are ignored.** CONFIRMED — the model
   is never asked for one (system prompt explicitly forbids it), and even
   if a response smuggled one in extra JSON keys, no code path reads them
   (see trace above).
5. **Non-verbatim evidence cannot pass.** CONFIRMED — two independent
   exact-match checks (module-level `find()` + `_verify_semantic_
   candidate`'s redundant slice comparison).
6. **Invalid offsets cannot pass.** CONFIRMED — offsets are computed by
   `document_text.find()`, never accepted from the model; a `-1` result
   is discarded before a `DiscoveryCandidate` is even constructed.
7. **Unsupported metadata cannot populate policy facts.**
   CONFIRMED — `discovery_metadata` is stored on `DiscoveryCandidate` but
   never read by `_verify_semantic_candidate` or any downstream function;
   grep confirms zero reads of `.discovery_metadata` outside diagnostic
   printing in test/report scripts.
8. **Semantic absence cannot become confirmed absence.**
   CONFIRMED — `CONFIRMED_ABSENT` (the `return None` path) requires BOTH
   `regex_found_nothing` AND `not semantic_candidates` AND
   `semantic_error is None` (i.e., the provider ran and affirmatively
   found nothing) — see `extract_indemnification_facts` lines ~1384-1397.
9. **Provider outage cannot become confirmed absence.**
   CONFIRMED — same branch: `semantic_error is not None` routes to
   `RECOGNITION_UNCERTAIN`, explicitly bypassing `CONFIRMED_ABSENT`.
10. **Candidate confidence/probability cannot bypass deterministic
    verification.** CONFIRMED — no confidence field is even solicited from
    the model (the schema instructs quote-only output), and
    `_verify_semantic_candidate` has no confidence-based shortcut; every
    candidate goes through the same regex gauntlet regardless of any
    metadata.

## Verdict

No direct semantic -> policy-authority path exists. All 10 checks
CONFIRMED. Phase 2: **PASS.**
