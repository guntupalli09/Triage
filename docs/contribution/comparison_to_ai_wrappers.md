# Comparison to AI Wrappers

## What Is an AI Wrapper?

An AI wrapper is a system that:
- Takes user input
- Sends it to an LLM API
- Returns LLM output
- Adds minimal processing or UI

**Characteristics**:
- No original logic
- No deterministic guarantees
- No auditability
- No technical contribution

## Our System vs. AI Wrappers

### AI Wrapper Approach

```
User Input → LLM API → Output
```

**What it does**:
- Passes contract to LLM
- Returns LLM analysis
- Minimal processing

**Problems**:
- Hallucination
- Inconsistency
- No auditability
- No technical contribution

### Our Neural-Symbolic Approach

```
Contract → Rule Engine → Findings → LLM → Explanations
```

**What it does**:
- Deterministic detection (original logic)
- Bounded LLM explanation (architectural innovation)
- Full auditability (every claim traceable)
- Hard boundaries (prevents hallucination)

**Advantages**:
- Deterministic guarantees
- Consistency
- Full auditability
- Original technical contribution

## Key Differences

### 1. Detection Logic

**AI Wrapper**: LLM detects risks (no original logic)

**Our System**: Rule engine detects risks (original deterministic logic)

**Difference**: We have original detection logic; wrappers don't

### 2. Architectural Boundaries

**AI Wrapper**: No boundaries, LLM sees everything

**Our System**: Hard boundaries, LLM only sees findings

**Difference**: We enforce architectural limits; wrappers don't

### 3. Auditability

**AI Wrapper**: Cannot trace why risks were flagged

**Our System**: Every risk traceable to rule_id

**Difference**: We provide full auditability; wrappers don't

### 4. Consistency

**AI Wrapper**: Same contract may produce different results

**Our System**: Same contract always produces same findings

**Difference**: We guarantee consistency; wrappers don't

### 5. Hallucination Prevention

**AI Wrapper**: LLM can invent risks

**Our System**: LLM cannot invent risks (architecturally impossible)

**Difference**: We prevent hallucination; wrappers don't

## Technical Depth Comparison

### AI Wrapper Technical Stack

```
Frontend → API Gateway → LLM API → Response
```

**Complexity**: Low (mostly API integration)

**Original Logic**: None

**Technical Contribution**: Minimal

### Our System Technical Stack

```
Frontend → Text Extraction → Rule Engine → LLM Evaluator → Results Synthesis
```

**Complexity**: High (multiple components, original logic)

**Original Logic**: 
- Rule engine (deterministic detection)
- Architectural boundaries (hallucination prevention)
- Output validation (safety guarantees)

**Technical Contribution**: Significant

## Code Comparison

### AI Wrapper Code (Hypothetical)

```python
def analyze_contract(text):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Analyze this contract: {text}"}]
    )
    return response.choices[0].message.content
```

**Lines of code**: ~10
**Original logic**: None
**Technical depth**: Minimal

### Our System Code

**Rule Engine**: ~500 lines of original detection logic
**LLM Evaluator**: ~300 lines of bounded explanation logic
**Main Application**: ~400 lines of orchestration
**Total**: ~1200 lines of original, systematic code

**Original logic**: Significant
**Technical depth**: High

## Innovation Comparison

### AI Wrapper Innovation

**Innovation**: None (standard API integration)

**Novelty**: Low (many similar systems exist)

**Technical contribution**: Minimal

### Our System Innovation

**Innovation**: 
- Neural-symbolic architecture for legal-tech
- Hard architectural boundaries
- Deterministic detection with AI explanation
- Full auditability

**Novelty**: High (novel application)

**Technical contribution**: Significant

## Use Case Comparison

### AI Wrapper Use Cases

- **Chatbots**: Simple Q&A
- **Content generation**: Text creation
- **Translation**: Language conversion

**Limitation**: Cannot be used where auditability or consistency is required

### Our System Use Cases

- **Legal contract triage**: Requires auditability
- **Regulatory compliance**: Requires deterministic behavior
- **Enterprise workflows**: Requires consistency

**Advantage**: Can be used in contexts requiring trust and verification

## Regulatory Comparison

### AI Wrapper Regulatory Status

**Auditability**: No (black box)
**Determinism**: No (non-deterministic)
**Compliance**: Difficult (cannot verify claims)

**Result**: Limited regulatory applicability

### Our System Regulatory Status

**Auditability**: Yes (full traceability)
**Determinism**: Yes (deterministic detection)
**Compliance**: Easier (can verify all claims)

**Result**: Suitable for regulatory contexts

## Conclusion

### AI Wrappers Are

- Simple API integrations
- No original logic
- No technical contribution
- Limited applicability

### Our System Is

- Original neural-symbolic architecture
- Significant original logic
- Substantial technical contribution
- Broad applicability (including regulatory)

**Key Distinction**: We built a **system**, not a wrapper. The rule engine, architectural boundaries, and auditability mechanisms represent original technical work that goes far beyond simple API integration.

This distinction is critical for:
- Technical contribution claims (O-1, EB-1A)
- Regulatory compliance
- Enterprise adoption
- Legal use cases
