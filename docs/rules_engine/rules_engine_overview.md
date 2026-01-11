# Rules Engine Overview

## Purpose

The rules engine is the **deterministic detection layer** of the Contract Risk Triage Tool. It uses algorithmic pattern matching to identify risk indicators in commercial contracts without any AI or interpretation.

## Core Principle

**All risk detection is deterministic and auditable.**

Every finding is:
- Traceable to a specific rule with a unique `rule_id`
- Reproducible (same input → same output)
- Verifiable (can inspect the rule that triggered)
- Version-controlled (rule engine version included in results)

## How It Works

### 1. Text Normalization

Contract text is normalized before processing:
- Multiple whitespace collapsed to single space
- Newlines normalized
- Excessive newlines removed (max 2 consecutive)

**Purpose**: Ensure consistent pattern matching regardless of formatting.

### 2. Text Chunking

Text is chunked to preserve structure:
- Prefer chunking on blank lines (section boundaries)
- Fallback to fixed-size chunks if no blank lines
- Chunk size: ~3000 characters

**Purpose**: Maintain context while processing large documents.

### 3. Rule Application

Two types of rules:

#### Pattern-Based Rules

Direct regex pattern matching:
```python
pattern = r"\bindemnif\w+\b.*?\bunlimited\b"
```

**Process**:
1. Search text for pattern matches
2. Extract matched text excerpt
3. Create finding with rule metadata

#### Proximity-Based Rules

Anchor + nearby pattern matching:
```python
anchors = [r"\bindemnif\w+\b"]
nearby = [r"\bno\s+limit\b", r"\bwithout\s+limit\b"]
window = 400  # characters
```

**Process**:
1. Find anchor matches
2. Check for nearby patterns within window
3. If found, create finding

**Purpose**: Detect risks where patterns are close but not adjacent.

### 4. Finding Creation

Each match creates a `Finding` object:
- `rule_id`: Unique identifier (e.g., "H_INDEM_01")
- `rule_name`: Machine-friendly name (e.g., "unlimited_indemnification")
- `title`: Human-readable title
- `severity`: HIGH, MEDIUM, or LOW
- `matched_excerpt`: Text that triggered the rule
- `clause_number`: Detected clause reference (if found)
- `matched_keywords`: Key phrases that triggered detection

### 5. Deduplication

Findings are deduplicated by `rule_id`:
- Only first occurrence of each rule is kept
- Prevents inflated counts from multiple matches
- Ensures one finding per risk type

### 6. Severity Aggregation

Overall risk level determined by:
- **HIGH**: If any HIGH severity finding exists
- **MEDIUM**: If ≥2 MEDIUM severity findings exist
- **LOW**: Otherwise

## Rule Categories

See [Rule Categories](rule_categories.md) for detailed breakdown.

## Rule Structure

See [Rule Structure](rule_structure.md) for technical details.

## Example Rules

See [Example Rules](example_rules.md) for concrete examples.

## Versioning

See [Versioning Strategy](versioning_strategy.md) for how rules are versioned.

## Why Determinism Matters

1. **Auditability**: Every finding is traceable
2. **Consistency**: Same contract → same findings
3. **Trust**: Users can verify why risks were flagged
4. **No Hallucination**: Impossible by design
5. **Regulatory Compliance**: Deterministic systems meet auditability requirements

## Performance

- **Speed**: Processes ~10,000 words in ~50-200ms
- **Accuracy**: High precision (may have false positives, but no false negatives by design)
- **Scalability**: Linear time complexity with text length

## Limitations

- **False Positives**: May flag standard clauses as risky (acceptable trade-off)
- **Language**: Optimized for English commercial contracts
- **Scope**: Designed for NDAs and MSAs, not all contract types
- **Pattern Matching**: Cannot understand context or intent

These limitations are acceptable because:
- The system is a triage tool, not final analysis
- False positives are safer than false negatives
- All findings should be reviewed by legal counsel
