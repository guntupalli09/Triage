# System Goals

## Primary Goals

### 1. Deterministic Risk Detection

The system must detect risk indicators using purely algorithmic methods:
- Regex pattern matching
- Proximity-based logic (anchors + nearby patterns)
- Explicit rule definitions with unique identifiers
- No AI in the detection path

**Success Criteria**: Every risk finding is traceable to a specific rule_id.

### 2. Bounded AI Explanation

The system must use AI only for explanation, never for detection:
- LLM receives only deterministic findings, not full contract text
- LLM cannot invent new risks
- LLM output is validated against deterministic findings
- Fallback to rule-engine-only results if LLM fails

**Success Criteria**: Zero hallucinated risks in production.

### 3. Conservative Language

The system must use legally conservative language:
- "may indicate risk" (not "is risky")
- "commonly negotiated" (not "you should negotiate")
- "can increase exposure" (not "will cause problems")
- Never declares terms "safe to sign" or "illegal"

**Success Criteria**: Language passes legal review for non-advice disclaimer.

### 4. Auditability

The system must be fully auditable:
- Rule engine versioning
- Every finding maps to a rule_id
- Logs show deterministic detection before LLM explanation
- Results include rule engine version

**Success Criteria**: Technical reviewers can trace every claim to source code.

## Secondary Goals

### 5. Executive-Friendly Output

The system must present findings in business language:
- Executive summaries (3-5 bullets)
- Business impact explanations (not legal analysis)
- Negotiation considerations (not legal advice)

**Success Criteria**: Non-legal users can understand and act on findings.

### 6. Pay-Per-Use Model

The system must support one-time payments:
- No user accounts required
- No subscriptions
- Stripe Checkout integration
- In-memory session storage with TTL

**Success Criteria**: Users can analyze contracts without account creation.

### 7. Commercial Contract Focus

The system must focus on commercial NDAs and MSAs:
- Rules optimized for these contract types
- Not designed for employment agreements, leases, etc.
- Clear scope limitations

**Success Criteria**: System performs well on target contract types.

## Non-Goals

The system explicitly does NOT aim to:

- Replace legal counsel
- Determine enforceability
- Provide legal advice
- Support all contract types
- Build a general-purpose contract analyzer
- Create a contract redlining tool
- Generate contract templates

## Success Metrics

The system is successful if:

1. **Zero hallucinated risks** in production (all risks traceable to rules)
2. **Consistent results** for the same contract (deterministic behavior)
3. **Legal disclaimers** are respected (no legal advice claims)
4. **Users understand limitations** (tool is not a replacement for counsel)
5. **Technical reviewers** can audit the system (full traceability)

## Design Principles

1. **Determinism First**: Detection must be algorithmic and auditable
2. **Safety Boundaries**: Hard architectural limits prevent AI from inventing risks
3. **Conservative Language**: Err on the side of caution in all communications
4. **Transparency**: System clearly states what it does and does not do
5. **Fail-Safe**: System degrades gracefully when components fail

These goals and principles guide all system design decisions.
