# Auditability

## What Is Auditability?

Auditability means that every claim made by the system can be traced back to its source. For the Contract Risk Triage Tool, this means:

- **Every risk finding** maps to a specific rule with a unique ID
- **Every rule** is defined in source code
- **Every analysis** includes the rule engine version used
- **Every decision** is traceable to deterministic logic

## Why Auditability Matters

### For Legal Professionals

- **Verifiable claims**: Lawyers can verify why risks were flagged
- **Credible evidence**: Findings can be used in legal strategy
- **Workflow integration**: Deterministic results enable process integration

### For Regulatory Bodies

- **Compliance**: Deterministic systems meet auditability requirements
- **Transparency**: Full traceability enables regulatory review
- **Trust**: Auditable systems build regulatory confidence

### For Technical Reviewers (O-1, EB-1A)

- **Original contribution**: Demonstrates technical innovation
- **Verifiable system**: Can trace every claim to source code
- **Deterministic behavior**: Consistent, reproducible results

### For Enterprise Adoption

- **Process standardization**: Consistent results enable workflows
- **Compliance requirements**: Auditable systems meet enterprise standards
- **Risk management**: Traceable findings enable risk assessment

## How Auditability Is Achieved

### 1. Rule-Based Detection

**Every finding has**:
- `rule_id`: Unique identifier (e.g., "H_INDEM_01")
- `rule_name`: Machine-friendly name
- `title`: Human-readable title
- `matched_excerpt`: Text that triggered the rule

**Traceability**: Can look up rule_id in source code to see exact detection logic

### 2. Rule Engine Versioning

**Every analysis includes**:
- Rule engine version (currently "1.0.3")
- Version constant in source code
- Version history documented

**Traceability**: Can identify exact rule set used for any analysis

### 3. Source Code Availability

**All rules defined in**:
- `rules_engine.py`: Rule definitions
- `evaluator.py`: LLM explanation logic
- `main.py`: System orchestration

**Traceability**: Can review source code to understand system behavior

### 4. Logging

**What's logged**:
- Deterministic findings (rule_id, severity, title)
- LLM input (findings summary)
- LLM output (top issues)
- Errors and warnings

**Traceability**: Logs show exactly what was detected and how

### 5. No Black Box

**System is transparent**:
- No hidden ML models
- No proprietary algorithms
- No unexplained behavior
- All logic is explicit and reviewable

**Traceability**: Everything is inspectable

## Audit Trail Example

### Analysis Request

**Input**: Contract file uploaded
**Timestamp**: 2026-01-11 10:00:00
**Rule Engine Version**: 1.0.3

### Detection Phase

**Logs show**:
```
Deterministic findings count=3, overall_risk=medium
RULE HIT: M_CONF_01 | medium | Confidentiality may be perpetual / indefinite
RULE HIT: M_DEV_RESTRICT_01 | medium | Development restriction tied to confidential information
RULE HIT: L_GOVLAW_01 | low | Specific governing law or venue
```

**Traceability**: Can look up each rule_id in `rules_engine.py`

### Explanation Phase

**Logs show**:
```
LLM INPUT (deterministic findings only, first 2000 chars): {...}
LLM CALL → model=gpt-4o-mini, temperature=0.2
LLM OUTPUT: 3 top_issues, 4 summary bullets
```

**Traceability**: Can verify LLM received only findings, not contract text

### Results Phase

**Output includes**:
- Rule engine version: 1.0.3
- Finding details with rule_ids
- LLM explanations mapped to findings

**Traceability**: Every claim in results can be traced to source

## Verification Process

### For Legal Professionals

1. **Review findings**: Check rule_ids in results
2. **Look up rules**: Find rule definitions in source code
3. **Verify logic**: Confirm rule logic matches finding
4. **Check version**: Verify rule engine version
5. **Validate explanations**: Confirm LLM explanations map to findings

### For Technical Reviewers

1. **Review architecture**: Understand neural-symbolic design
2. **Examine rules**: Review rule definitions and logic
3. **Trace findings**: Follow finding from detection to explanation
4. **Verify boundaries**: Confirm LLM cannot invent risks
5. **Check versioning**: Verify rule engine versioning strategy

### For Regulatory Bodies

1. **Review documentation**: Understand system design
2. **Examine code**: Review source code for compliance
3. **Test system**: Run known contracts, verify results
4. **Check logs**: Review audit trails
5. **Verify claims**: Confirm all claims are traceable

## Auditability Guarantees

### 1. Deterministic Detection

**Guarantee**: Same contract → same findings

**Verification**: Run contract multiple times, verify identical results

### 2. Traceable Findings

**Guarantee**: Every finding maps to a rule_id

**Verification**: Check results, verify all findings have rule_ids

### 3. Version Tracking

**Guarantee**: Every analysis includes rule engine version

**Verification**: Check results footer, verify version displayed

### 4. No Hallucination

**Guarantee**: LLM cannot invent risks

**Verification**: Review architecture, confirm LLM never sees contract text

### 5. Full Transparency

**Guarantee**: All logic is explicit and reviewable

**Verification**: Review source code, confirm no black boxes

## Limitations of Auditability

### What Can Be Audited

- **Detection logic**: All rules are explicit
- **Finding traceability**: Every finding maps to a rule
- **System behavior**: All logic is reviewable

### What Cannot Be Audited

- **LLM internal reasoning**: Cannot audit how LLM generates explanations
- **Future rule changes**: Cannot audit rules that don't exist yet
- **User decisions**: Cannot audit how users interpret findings

### Acceptable Limitations

These limitations are acceptable because:
- **LLM reasoning**: Not critical (LLM only explains, doesn't detect)
- **Future changes**: Will be versioned and documented
- **User decisions**: Outside system scope

## Best Practices for Auditors

1. **Review source code**: Understand system implementation
2. **Test with known contracts**: Verify system behavior
3. **Check logs**: Review audit trails
4. **Verify versioning**: Confirm rule engine versioning
5. **Test boundaries**: Verify LLM cannot invent risks

## Audit Documentation

For audits, provide:
- **Source code**: Full codebase
- **Rule definitions**: All rules documented
- **Version history**: Rule engine version changes
- **Test results**: Golden fixture test results
- **Architecture docs**: System design documentation

This auditability enables trust and regulatory compliance.
