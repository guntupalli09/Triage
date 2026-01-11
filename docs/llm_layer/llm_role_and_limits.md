# LLM Role and Limits

## Core Principle

**The LLM does NOT detect risks. It only explains risks that the deterministic engine has already identified.**

This is a hard architectural boundary that prevents hallucination.

## What the LLM Does

### 1. Explains Detected Risks

The LLM receives deterministic findings and provides:
- **Business-friendly explanations**: Why each risk may matter to a founder/CEO
- **Negotiation considerations**: What is commonly negotiated for each risk type
- **Executive summaries**: 3-5 bullet points synthesizing all findings

### 2. Suggests Missing Sections

The LLM suggests sections that are commonly included in commercial contracts:
- Limitation of liability
- Termination rights
- Dispute resolution
- Data protection
- IP ownership
- Payment terms

**Important**: These are suggestions only, not detected risks.

### 3. Synthesizes Findings

The LLM creates a cohesive narrative from multiple findings:
- Groups related findings
- Prioritizes high-severity issues
- Provides context for business impact

## What the LLM Does NOT Do

### ❌ Does NOT Detect Risks

The LLM never:
- Scans contract text for risks
- Identifies new risk patterns
- Interprets contract language
- Makes legal determinations

### ❌ Does NOT See Full Contract

The LLM receives:
- ✅ Deterministic findings (rule_id, title, severity, rationale, excerpt)
- ❌ Full contract text (never sent)

This architectural boundary ensures the LLM cannot invent risks.

### ❌ Does NOT Override Risk Levels

The LLM cannot change:
- Overall risk level (deterministic calculation)
- Individual finding severities (from rule definitions)
- Rule counts (from deterministic detection)

The LLM's `overall_risk` output is ignored; the deterministic value is used.

## Input to LLM

The LLM receives a structured prompt containing:

1. **System instructions**: Role definition and constraints
2. **Deterministic overall risk**: Pre-calculated risk level
3. **Detected findings**: Grouped by rule, with excerpts
4. **Task definition**: What the LLM should produce
5. **Constraints**: Language restrictions and output format

**Example prompt structure**:
```
You are a risk triage assistant for commercial contracts.

Deterministic Overall Risk: medium

DETECTED FINDINGS:
Rule: indefinite_confidentiality
Title: Confidentiality may be perpetual / indefinite
Severity: medium
Rationale: Indefinite confidentiality can create long-term compliance burden.
- Excerpt: "...confidentiality obligations shall survive in perpetuity..."

TASK:
1) Provide 3-5 bullet executive summary
2) Produce top_issues based ONLY on detected findings
3) Suggest possible missing sections

CRITICAL CONSTRAINTS:
- Do NOT invent new risks
- Do NOT declare legality or enforceability
- Use conservative language: "may indicate", "can increase risk"
```

## Output Validation

The LLM output is validated against input findings:

1. **Structure validation**: Required keys present, correct types
2. **Mapping validation**: Every `top_issue` must map to a deterministic finding
3. **Language validation**: Disclaimer enforced, conservative language checked

If validation fails → fallback to rule-engine-only response.

## Fallback Behavior

When LLM is unavailable or fails:

1. **API key missing**: Automatic fallback
2. **API timeout**: Automatic fallback
3. **Invalid response**: Automatic fallback
4. **Validation failure**: Automatic fallback

**Fallback response**:
- Uses rule rationale for explanations
- Provides generic summary based on risk level
- Suggests standard missing sections
- Includes disclaimer

**User experience**: Results page shows rule-engine findings with note that LLM explanation unavailable.

## Cost Control

### Token Management

- **Input truncation**: Contract text never sent (only findings)
- **Finding limits**: Up to 2 excerpts per rule in prompt
- **Output limits**: Max 5 summary bullets, max 6 missing sections
- **Model selection**: Uses `gpt-4o-mini` (cost-effective)

### Estimated Costs

- **Per analysis**: ~500-1000 input tokens, ~300-500 output tokens
- **Cost per analysis**: ~$0.001-0.002 (at current OpenAI pricing)
- **Fallback rate**: ~5-10% (when API unavailable)

## Safety Guarantees

### Architectural Boundaries

1. **No contract text**: LLM never receives full contract
2. **Zero findings check**: LLM never called with zero findings
3. **Output validation**: LLM output validated against input
4. **Fallback available**: System works without LLM

### Language Constraints

The LLM is constrained to use:
- ✅ "may indicate risk"
- ✅ "can increase exposure"
- ✅ "commonly negotiated"
- ❌ "safe to sign"
- ❌ "illegal"
- ❌ "enforceable"
- ❌ "you should"

These constraints are enforced in the prompt and validated in output.

## Why This Design

### Problem: Legal Hallucination

Pure LLM systems hallucinate risks because:
- They interpret contract language
- They make legal judgments
- They invent patterns that don't exist

### Solution: Bounded LLM

Our design prevents hallucination by:
- Separating detection (deterministic) from explanation (AI)
- Hard architectural boundaries
- Output validation
- Fallback mechanisms

### Result: Trustworthy System

Users can trust the system because:
- All risks are traceable to deterministic rules
- LLM cannot invent new risks
- System works even if LLM fails
- Language is conservative and non-advice

## Technical Implementation

See [Prompt Strategy](prompt_strategy.md) for prompt design details.

See [Hallucination Prevention](hallucination_prevention.md) for validation mechanisms.

See [Cost Control](cost_control.md) for token management.
