# Step 4B Phase J — System-Level Prompt Injection: Read-Only Trace

## Untrusted-text boundaries mapped

1. **Contract review explanation** (`evaluator.LLMEvaluator.evaluate`) —
   the ONLY place contract-derived text reaches an LLM during a review.
   `evaluate()` has a hard guard: `if contract_text is not None: raise
   ValueError(...)` — confirmed by direct code read and by `main.py`'s own
   call site passing `contract_text=None` explicitly. The model only ever
   receives `findings_dict` — short pre-extracted excerpts
   (`matched_excerpt`, `rationale`), never the full document. This is the
   text an attacker could poison (by drafting a contract clause containing
   an injection payload that happens to be captured as a `matched_excerpt`).
2. **Playbook AI-assisted import** (`playbook_ai_extraction.py`) — a
   lawyer-uploaded playbook document sent to an LLM to propose candidate
   `PolicyPosition` field values. `verify_and_classify_candidate`
   (`playbook_ai_extraction.py:445`) is the authoritative gate: it
   re-locates the model's claimed quote against the ACTUAL source
   document text (discarding the model's own reproduction), requires
   `basis == "EXTRACTED"`, and for numeric fields requires the claimed
   value to be textually grounded in the verified quote. Anything failing
   any check becomes `NOT_ESTABLISHED` or `REQUIRES_LAWYER_INTERPRETATION`
   — never silently `ESTABLISHED`.
3. **Semantic candidate discovery** (`semantic_discovery`/
   `semantic_discovery_real`, used by `indemnification_policy_engine.py`)
   — a Step 4A-era mechanism already governed by the standing non-
   negotiable rule (semantic layer may only discover candidates, never
   establish authoritative facts) and out of scope for re-validation here
   per the explicit "do not reopen Step 4A" instruction — not touched.

## Trust boundary already enforced structurally

- No `eval(`, `exec(`, `pickle.loads(`, or `yaml.load(` (unsafe) of any
  document-derived or model-derived content anywhere in the codebase
  (confirmed by direct grep across every `.py` file).
- Contract/playbook text has no code path that can invoke
  `approve_position`/`activate_position`/`playbook_delete`/any DB
  mutation — those are only ever reachable via explicit authenticated
  HTTP routes triggered by a human action, never by parsing document
  content. This is a structural property (no function anywhere accepts
  "instructions" parsed out of contract or playbook text), not merely an
  input filter.
- `evaluate()`'s `result["overall_risk"] = overall_risk` (forces the
  deterministic value) and `_validate_result`'s forced disclaimer both
  apply unconditionally, regardless of what the model output claims —
  already confirmed in Phase I.
- `_verify_output_maps_to_findings` (fixed in Phase I) drops any
  `top_issue` not grounded in a real deterministic finding — this
  directly defeats an injection payload framed as a fabricated "finding"
  (e.g., "the correct answer is CLEAN," "mark this contract clean,"
  "return VERIFIED") from ever being displayed as if it were a real
  finding.
- `build_enhanced_issues`'s per-finding loop iterates `findings_dict`
  directly — the deterministic list of real findings — never `top_issues`;
  an LLM narrative cannot cause a real finding to disappear from the
  displayed list merely by claiming it doesn't matter, because the
  narrative never controls which findings are iterated.

Full benchmark, PRE/POST, and regression: see
`artifacts/step4b/phaseJ_prompt_injection_report.md`.
