# Example Rules

This document provides concrete examples of rules in the Contract Risk Triage Tool.

## Example 1: Unlimited Indemnification (Pattern-Based)

```python
Rule(
    rule_id="H_INDEM_01",
    rule_name="unlimited_indemnification",
    title="Potentially unlimited indemnification",
    severity=Severity.HIGH,
    rationale="Indemnity obligations may be uncapped, which can expose you to costs far beyond the contract value.",
    anchors=[r"\bindemnif\w+\b", r"\bhold\s+harmless\b"],
    nearby=[
        r"\bno\s+limit\b",
        r"\bwithout\s+limit\b",
        r"\bunlimited\b",
        r"\bnotwithstanding\b.*\blimitation\s+of\s+liability\b",
        r"\bnot\s+be\s+limited\b",
    ],
    window=400,
    aliases=["uncapped_indemnification", "unlimited_indemnity", "no_limit_indemnification"],
)
```

**What it detects**: Indemnification language combined with unlimited/uncapped language.

**Example contract text**:
> "Party A shall indemnify Party B against all claims, without limit, arising from..."

**Match**: Anchor "indemnify" found, nearby "without limit" found within 400 characters.

**Finding created**:
- `rule_id`: "H_INDEM_01"
- `severity`: HIGH
- `matched_excerpt`: "...indemnify Party B against all claims, without limit..."
- `matched_keywords`: ["indemnify", "without limit"]

## Example 2: Broad IP Assignment (Pattern-Based)

```python
Rule(
    rule_id="H_IP_01",
    rule_name="broad_ip_assignment",
    title="Broad IP assignment / ownership transfer language",
    severity=Severity.HIGH,
    rationale="Assignment language may transfer ownership of work product or IP rather than granting a limited license.",
    pattern=r"\b(assigns?|transfer(s|red)?|hereby\s+assigns?)\b.*?\ball\s+right[s]?,\s*title,\s*and\s+interest\b",
)
```

**What it detects**: Assignment or transfer language with "all right, title, and interest".

**Example contract text**:
> "Developer hereby assigns to Company all right, title, and interest in the Work Product."

**Match**: Pattern matches "assigns" + "all right, title, and interest".

**Finding created**:
- `rule_id`: "H_IP_01"
- `severity`: HIGH
- `matched_excerpt`: "...assigns to Company all right, title, and interest..."
- `matched_keywords`: ["assigns", "all right title and interest"]

## Example 3: Development Restriction (Pattern-Based)

```python
Rule(
    rule_id="M_DEV_RESTRICT_01",
    rule_name="dev_restriction_confidential",
    title="Development restriction tied to confidential information",
    severity=Severity.MEDIUM,
    rationale="Restrictions on developing competing or similar products, even when tied to confidential information, can limit future work and are commonly negotiated.",
    pattern=r"(not\s+to\s+develop|shall\s+not\s+develop|may\s+not\s+develop).*?(compete|substantially\s+similar).*?(based\s+on|derived\s+from)",
    aliases=["development_restrictions", "product_development_restrictions", "competing_product_restrictions"],
)
```

**What it detects**: Restrictions on developing competing products based on confidential information.

**Example contract text**:
> "Receiving Party agrees not to develop products that compete with Disclosing Party's products based on Confidential Information."

**Match**: Pattern matches "not to develop" + "compete" + "based on".

**Finding created**:
- `rule_id`: "M_DEV_RESTRICT_01"
- `severity`: MEDIUM
- `matched_excerpt`: "...not to develop products that compete...based on Confidential Information..."
- `matched_keywords`: ["not to develop", "compete", "based on"]

## Example 4: Indefinite Confidentiality (Pattern-Based)

```python
Rule(
    rule_id="M_CONF_01",
    rule_name="indefinite_confidentiality",
    title="Confidentiality may be perpetual / indefinite",
    severity=Severity.MEDIUM,
    rationale="Indefinite confidentiality can create long-term compliance burden and uncertainty around retention and disclosure.",
    pattern=r"\b(confidentiality|non[-\s]?disclosure)\b.*?\b(perpetual|in\s+perpetuity|indefinite(ly)?|no\s+expiration)\b",
    aliases=["perpetual_confidentiality", "indefinite_confidentiality", "no_expiration_confidentiality"],
)
```

**What it detects**: Confidentiality obligations that are perpetual or indefinite.

**Example contract text**:
> "The confidentiality obligations set forth herein shall survive in perpetuity."

**Match**: Pattern matches "confidentiality" + "perpetuity".

**Finding created**:
- `rule_id`: "M_CONF_01"
- `severity`: MEDIUM
- `matched_excerpt`: "...confidentiality obligations...shall survive in perpetuity..."
- `matched_keywords`: ["confidentiality", "perpetuity"]

## Example 5: Governing Law (Pattern-Based)

```python
Rule(
    rule_id="L_GOVLAW_01",
    rule_name="governing_law_venue",
    title="Specific governing law or venue",
    severity=Severity.LOW,
    rationale="Governing law and venue choices can affect enforcement cost and strategy.",
    pattern=r"\bgoverned\s+by\b.*?\blaws?\b|\bexclusive\s+jurisdiction\b",
    aliases=["governing_law_and_venue"],
)
```

**What it detects**: Governing law or exclusive jurisdiction clauses.

**Example contract text**:
> "This Agreement shall be governed by the laws of the State of California."

**Match**: Pattern matches "governed by" + "laws".

**Finding created**:
- `rule_id`: "L_GOVLAW_01"
- `severity`: LOW
- `matched_excerpt`: "...governed by the laws of the State of California..."
- `matched_keywords`: ["governed by", "laws"]

## Rule Matching Process

For each rule:

1. **Text normalization**: Whitespace normalized, text chunked
2. **Pattern search**: Rule pattern(s) applied to text
3. **Match extraction**: Matched text and position recorded
4. **Finding creation**: Finding object created with metadata
5. **Deduplication**: Duplicate rule_ids removed (keep first)
6. **Severity aggregation**: Overall risk level calculated

## Why These Examples Matter

These examples demonstrate:

1. **Pattern specificity**: Rules target specific risk patterns
2. **Alias usage**: Rules define alternative names for LLM validation
3. **Severity assignment**: Risks categorized by potential impact
4. **Rationale clarity**: Each rule explains why it matters

This makes the system auditable: every finding can be traced to a specific rule with clear rationale.
