# Neural-Symbolic Design

## What Is Neural-Symbolic Architecture?

Neural-symbolic systems combine:
- **Symbolic components**: Rule-based, deterministic, auditable
- **Neural components**: AI-powered, flexible, contextual

The key is **strict separation** with **hard boundaries** between components.

## Our Implementation

### Symbolic Layer (Deterministic)

**Component**: `rules_engine.py`

**Characteristics**:
- Pure algorithmic detection
- Explicit rule definitions
- Regex pattern matching
- Proximity-based logic
- Version-controlled rules
- Fully auditable

**Output**: Structured findings with:
- Unique rule identifiers
- Severity classifications
- Matched text excerpts
- Clause numbers (when detected)
- Matched keywords

**Guarantees**:
- Same input → same output (deterministic)
- Every finding is traceable (auditable)
- No interpretation (algorithmic)
- No hallucination (impossible by design)

### Neural Layer (AI-Assisted)

**Component**: `evaluator.py`

**Characteristics**:
- Receives only deterministic findings
- Never sees full contract text
- Explains pre-identified risks
- Suggests missing sections
- Generates executive summaries

**Output**: Business-friendly explanations

**Guarantees**:
- Cannot invent new risks (architecturally bounded)
- Output validated against input findings
- Fallback available if API fails
- Conservative language enforced

## The Boundary

### Hard Architectural Limits

1. **Rule Engine → LLM**: Only findings are passed
   ```python
   # ✅ CORRECT: Findings only
   llm_evaluator.evaluate(findings=findings_dict, overall_risk=overall_risk)
   
   # ❌ IMPOSSIBLE: Contract text never passed
   # llm_evaluator.evaluate(contract_text=text)  # This doesn't exist
   ```

2. **LLM → Results**: Output is validated
   ```python
   # Every LLM issue must map to a deterministic finding
   _verify_output_maps_to_findings(llm_output, input_findings)
   ```

3. **Zero Findings**: LLM never called
   ```python
   if not findings:
       return self.create_fallback_response([], overall_risk)
   ```

### Why This Works

**Problem**: Pure LLM systems hallucinate risks.

**Solution**: Separate detection (deterministic) from explanation (AI).

**Result**: 
- Detection is reliable (deterministic)
- Explanation is helpful (AI-powered)
- No hallucination (architecturally impossible)

## Comparison to Pure LLM Systems

### Pure LLM Approach

```
Contract Text → LLM → Risk Analysis
```

**Problems**:
- LLM invents risks
- Inconsistent results
- No auditability
- Cannot verify claims

### Our Neural-Symbolic Approach

```
Contract Text → Rule Engine → Findings → LLM → Explanations
```

**Benefits**:
- Rule engine detects risks (deterministic)
- LLM explains risks (bounded)
- Full auditability (every risk traceable)
- Consistent results

## Technical Contribution

This architecture solves the **legal hallucination problem** by:

1. **Separating concerns**: Detection vs. explanation
2. **Enforcing boundaries**: Hard limits prevent AI from inventing risks
3. **Ensuring auditability**: Every claim is traceable to source code
4. **Maintaining consistency**: Deterministic detection guarantees reproducibility

This is a **novel application** of neural-symbolic architecture to legal-tech, providing:
- Deterministic risk detection (symbolic)
- Business-friendly explanations (neural)
- Zero hallucination guarantee (architectural)

## Why This Matters

For **technical reviewers** (O-1, EB-1A):
- Demonstrates original technical contribution
- Shows deterministic, auditable system design
- Provides verifiable innovation

For **legal professionals**:
- Findings are traceable and verifiable
- No hallucinated risks to waste time on
- Consistent results enable workflow integration

For **enterprise adoption**:
- Auditable systems meet compliance requirements
- Deterministic behavior enables process standardization
- Clear boundaries enable risk assessment

## Future Enhancements

Potential improvements (not implemented):
- Rule learning from expert feedback
- Multi-jurisdiction rule sets
- Contract type specialization
- Integration with legal databases

These would maintain the neural-symbolic boundary while expanding capabilities.
