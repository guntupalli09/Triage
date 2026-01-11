# Hallucination Prevention

## The Problem

LLMs can "hallucinate" by:
- Inventing risks that don't exist
- Misinterpreting contract language
- Making legal judgments
- Providing inconsistent results

This is unacceptable for legal-tech systems.

## Our Solution: Architectural Boundaries

We prevent hallucination through **hard architectural boundaries** that make it impossible for the LLM to invent risks.

### Boundary 1: No Contract Text

**Constraint**: LLM never receives full contract text.

**Implementation**:
```python
# ✅ CORRECT: Only findings passed
llm_evaluator.evaluate(findings=findings_dict, overall_risk=overall_risk)

# ❌ IMPOSSIBLE: Contract text never passed
# llm_evaluator.evaluate(contract_text=text)  # This method doesn't exist
```

**Result**: LLM cannot scan contract for risks it wasn't told about.

### Boundary 2: Zero Findings Check

**Constraint**: LLM never called with zero findings.

**Implementation**:
```python
if not findings:
    logger.warning("LLM evaluate() called with zero findings - using fallback instead")
    return self.create_fallback_response(findings=[], overall_risk=overall_risk)
```

**Result**: LLM cannot invent risks when none are detected.

### Boundary 3: Output Validation

**Constraint**: LLM output validated against input findings.

**Implementation**:
```python
def _verify_output_maps_to_findings(self, llm_output: Dict, input_findings: List[Dict]):
    # Check that every top_issue maps to a deterministic finding
    # Uses normalized title matching and explicit aliases
```

**Result**: LLM cannot output risks not in input findings.

## Validation Mechanisms

### 1. Structure Validation

**Checks**:
- Required keys present
- Correct data types
- Value constraints (e.g., severity matches input)

**Failure**: Fallback triggered

### 2. Mapping Validation

**Checks**:
- Every `top_issue.title` maps to a deterministic finding
- Uses normalized matching (rule_name, title, aliases)
- Warns on unmapped issues

**Failure**: Warning logged, but response accepted if structure valid

### 3. Language Validation

**Checks**:
- Disclaimer present and correct
- No forbidden phrases ("safe to sign", "illegal", etc.)
- Conservative language used

**Failure**: Disclaimer enforced, warnings logged

## Normalized Matching

To prevent false warnings, we use normalized matching:

1. **Normalize titles**: Lowercase, remove punctuation, underscores
2. **Check rule names**: Match against normalized rule_name
3. **Check titles**: Match against normalized title
4. **Check aliases**: Match against normalized aliases

**Example**:
- LLM output: "Indefinite Confidentiality"
- Normalized: "indefinite_confidentiality"
- Matches rule: `indefinite_confidentiality` ✅

## Explicit Aliases

Rules define explicit aliases for common LLM phrasings:

```python
Rule(
    rule_id="L_GOVLAW_01",
    rule_name="governing_law_venue",
    aliases=["governing_law_and_venue"],
)
```

**Purpose**: Prevents false warnings when LLM uses alternative phrasing.

## Fallback Safety

When validation fails, system falls back to rule-engine-only response:

- Uses rule rationale for explanations
- Provides generic summary
- Suggests standard missing sections
- Includes disclaimer

**Result**: System always produces valid output, even if LLM fails.

## Logging and Monitoring

### What Gets Logged

- **LLM input**: First 2000 chars of findings (for debugging)
- **LLM output**: Top issues count and titles
- **Validation warnings**: Unmapped issues
- **Fallback triggers**: When and why fallback used

### What Doesn't Get Logged

- Full contract text (privacy)
- Complete LLM prompts (token efficiency)
- User identifying information

## Testing Hallucination Prevention

The system is tested for:

1. **Zero findings**: LLM not called
2. **Invalid output**: Fallback triggered
3. **Unmapped issues**: Warnings logged
4. **Language violations**: Disclaimer enforced

## Why This Works

### Architectural Guarantees

1. **Impossible to invent risks**: LLM never sees contract text
2. **Impossible to call with zero findings**: Hard check prevents it
3. **Impossible to output unmapped risks**: Validation enforces mapping

### Verification

Every risk in LLM output can be traced to:
- A deterministic finding (rule_id)
- A specific rule definition
- Source code

This provides **full auditability**.

## Comparison to Pure LLM Systems

### Pure LLM Approach

```
Contract Text → LLM → Risk Analysis
```

**Problems**:
- LLM invents risks
- No auditability
- Inconsistent results

### Our Approach

```
Contract Text → Rule Engine → Findings → LLM → Explanations
```

**Benefits**:
- LLM cannot invent risks (architecturally bounded)
- Full auditability (every risk traceable)
- Consistent results (deterministic detection)

## Success Metrics

Hallucination prevention is successful if:

1. **Zero invented risks**: All risks traceable to rules
2. **Consistent validation**: Mapping validation works reliably
3. **Safe fallback**: System works when LLM fails
4. **Clear warnings**: Unmapped issues logged for review

## Future Enhancements

Potential improvements:
- **Stricter validation**: Reject responses with unmapped issues
- **Enhanced logging**: More detailed validation traces
- **A/B testing**: Test prompt variations
- **Rule learning**: Learn aliases from LLM output

These would maintain safety while improving quality.
