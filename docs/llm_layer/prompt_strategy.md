# Prompt Strategy

## Prompt Design Principles

1. **Explicit constraints**: Clear boundaries on what LLM can and cannot do
2. **Structured input**: Deterministic findings provided in structured format
3. **Output format**: Strict JSON schema enforced
4. **Conservative language**: Constraints on phrasing
5. **No contract text**: Only findings, never full contract

## Prompt Structure

### System Message

```
You are a risk triage assistant for founders/CEOs.
Output only valid JSON.
```

**Purpose**: Define role and enforce JSON output.

### User Message

The user message contains:

1. **Role definition**: What the LLM is and is not
2. **Deterministic findings**: Structured list of detected risks
3. **Task definition**: What to produce
4. **Constraints**: What not to do
5. **Output format**: JSON schema

## Example Prompt

```
You are a contract risk triage assistant for founders/CEOs.

IMPORTANT:
- The deterministic engine has ALREADY detected the risks.
- Your job is NOT to find new risks.
- Your job is to explain why the provided findings may matter and synthesize a concise executive summary.

Deterministic Overall Risk (already computed): medium

DETECTED FINDINGS (deterministic):
Rule: indefinite_confidentiality
Title: Confidentiality may be perpetual / indefinite
Severity: medium
Rationale: Indefinite confidentiality can create long-term compliance burden and uncertainty around retention and disclosure.
- Excerpt: "...confidentiality obligations shall survive in perpetuity..."

Rule: dev_restriction_confidential
Title: Development restriction tied to confidential information
Severity: medium
Rationale: Restrictions on developing competing or similar products, even when tied to confidential information, can limit future work and are commonly negotiated.
- Excerpt: "...not to develop products that compete with those based on confidential information..."

TASK:
1) Provide a 3–5 bullet executive summary (plain English, business impact, not legal analysis)
2) Produce "top_issues" based ONLY on the detected findings (choose the most important 3–6)
3) Suggest POSSIBLE missing sections commonly negotiated in NDAs/MSAs (max 6). Phrase as suggestions (e.g., "You may want to confirm whether...")

CRITICAL CONSTRAINTS:
- Do NOT invent new risks.
- Do NOT declare legality, enforceability, or safety.
- Do NOT use: "safe to sign", "illegal", "enforceable", "you should"
- Prefer: "may indicate", "can increase risk", "commonly negotiated", "you may want to confirm"

OUTPUT FORMAT: JSON ONLY with this schema:
{
  "overall_risk": "low | medium | high",
  "summary_bullets": ["..."],
  "top_issues": [
    {
      "title": "",
      "severity": "high | medium | low",
      "why_it_matters": "",
      "negotiation_consideration": ""
    }
  ],
  "possible_missing_sections": ["..."],
  "disclaimer": "This is automated risk triage, not legal advice."
}
```

## Key Design Elements

### 1. Explicit Role Definition

**What LLM is**:
- Risk triage assistant
- Explanation provider
- Synthesis tool

**What LLM is NOT**:
- Risk detector
- Legal advisor
- Contract interpreter

### 2. Structured Findings Input

Findings are grouped by rule and include:
- Rule name
- Title
- Severity
- Rationale
- Excerpts (up to 2 per rule)

**Purpose**: Provide context without full contract text.

### 3. Task Clarity

Tasks are explicitly defined:
1. Executive summary (3-5 bullets)
2. Top issues (3-6 most important)
3. Missing sections (max 6 suggestions)

**Purpose**: Constrain output scope.

### 4. Language Constraints

Explicit constraints on phrasing:
- ❌ Forbidden: "safe to sign", "illegal", "enforceable", "you should"
- ✅ Preferred: "may indicate", "can increase risk", "commonly negotiated"

**Purpose**: Ensure conservative, non-advice language.

### 5. Output Schema

Strict JSON schema enforced:
- Required keys
- Type constraints
- Value constraints (e.g., severity must match input)

**Purpose**: Ensure structured, parseable output.

## Prompt Optimization

### Finding Grouping

Findings are grouped by `rule_name` to reduce repetition:
- Multiple matches of same rule → single entry
- Up to 2 excerpts per rule shown
- Reduces prompt size

### Truncation

If findings are too numerous:
- Limit to most severe findings
- Group similar findings
- Prioritize HIGH severity

### Temperature Setting

**Temperature**: `0.2` (low)

**Purpose**: 
- Reduce randomness
- Increase consistency
- Produce more deterministic output

## Response Format

### JSON Mode

OpenAI API called with:
```python
response_format={"type": "json_object"}
```

**Purpose**: Enforce JSON output, reduce parsing errors.

### Validation

Response is validated:
1. **JSON parsing**: Must be valid JSON
2. **Structure**: Required keys present
3. **Types**: Correct data types
4. **Mapping**: Output maps to input findings
5. **Language**: Conservative language enforced

## Error Handling

### Invalid JSON

**Handling**: Fallback to rule-engine-only response

**Logging**: Error logged, user sees fallback

### Missing Keys

**Handling**: Validation fails, fallback triggered

**Logging**: Validation error logged

### Mapping Failure

**Handling**: Warning logged, but response accepted if structure valid

**Logging**: Warning about unmapped issues

## Prompt Evolution

Prompts are versioned with the system:
- Changes tracked in code
- Tested against golden fixtures
- Validated for language constraints

**Current version**: Aligned with rule engine v1.0.3

## Best Practices

1. **Be explicit**: Clear constraints prevent misuse
2. **Structure input**: Organized findings improve output
3. **Enforce format**: JSON mode reduces errors
4. **Validate output**: Ensure quality and safety
5. **Test thoroughly**: Verify against known contracts

These practices ensure reliable, safe LLM explanations.
