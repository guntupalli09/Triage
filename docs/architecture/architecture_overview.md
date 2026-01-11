# Architecture Overview

## High-Level Design

The Contract Risk Triage Tool uses a **neural-symbolic architecture** that strictly separates deterministic risk detection from AI-assisted explanation.

```
┌─────────────┐
│   Upload    │
│  (PDF/DOCX) │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Text Extraction│
│  (PyPDF2/docx)  │
└──────┬──────────┘
       │
       ▼
┌─────────────────────┐
│ Deterministic Rule  │
│      Engine         │
│  (rules_engine.py)  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Findings + Risk    │
│     Level           │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  LLM Evaluator      │
│  (evaluator.py)     │
│  (Findings Only)    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Results Synthesis  │
│  (HTML Template)    │
└─────────────────────┘
```

## Core Components

### 1. Text Extraction Layer

**File**: `main.py` → `extract_text_from_file()`

- Supports PDF, DOCX, and TXT formats
- Extracts plain text (no formatting preservation)
- Handles malformed files gracefully
- Maximum file size: 10MB

**Output**: Plain text string

### 2. Deterministic Rule Engine

**File**: `rules_engine.py`

- Pure algorithmic detection (no AI)
- Regex pattern matching
- Proximity-based logic (anchors + nearby patterns)
- Rule versioning (currently v1.0.3)
- Deduplication by rule_id

**Output**: List of `Finding` objects with:
- `rule_id`: Unique identifier
- `rule_name`: Machine-friendly name
- `title`: Human-readable title
- `severity`: HIGH, MEDIUM, or LOW
- `matched_excerpt`: Text that triggered the rule
- `clause_number`: Detected clause reference (if found)
- `matched_keywords`: Key phrases that triggered detection

### 3. LLM Explanation Layer

**File**: `evaluator.py`

- Receives **only** deterministic findings (not contract text)
- Explains why detected risks may matter
- Suggests commonly negotiated sections
- Generates executive summary
- Validates output against deterministic findings

**Output**: Structured JSON with:
- `summary_bullets`: 3-5 executive summary points
- `top_issues`: Detailed explanations of detected risks
- `possible_missing_sections`: Suggestions for review
- `disclaimer`: Legal disclaimer text

### 4. Results Synthesis

**File**: `templates/results.html`

- Combines deterministic findings with LLM explanations
- Displays risk indicators with severity badges
- Shows clause numbers and matched keywords
- Includes negative guarantees section
- Displays rule engine version

## Architectural Boundaries

### Critical Separation

The system enforces hard boundaries between components:

1. **Rule Engine → LLM**: Only findings are passed, never contract text
2. **LLM → Results**: Output is validated against deterministic findings
3. **Zero Findings**: LLM is never called with zero findings (automatic fallback)

### Safety Guarantees

- **No Hallucination**: LLM cannot invent risks (architecturally impossible)
- **Auditability**: Every risk claim maps to a rule_id
- **Consistency**: Same contract produces same findings
- **Fail-Safe**: System degrades gracefully when LLM fails

## Data Flow

1. **Upload**: User uploads contract file
2. **Extraction**: System extracts plain text
3. **Detection**: Rule engine scans text for risk patterns
4. **Deduplication**: Findings deduplicated by rule_id
5. **Severity Calculation**: Overall risk determined (high if any HIGH, else medium if ≥2 MEDIUM, else low)
6. **Explanation**: LLM explains detected findings (if available)
7. **Synthesis**: Results combined and displayed
8. **Cleanup**: Session data expires after 24 hours

## Payment Integration

- **Stripe Checkout**: One-time payment per analysis
- **Webhook Verification**: Payment confirmed before analysis runs
- **In-Memory Storage**: Session data stored temporarily (no database)
- **Signed Tokens**: Session IDs are signed to prevent tampering

## Failure Modes

See [Failure Modes](failure_modes.md) for detailed error handling.

## Why This Architecture

This neural-symbolic design solves the legal hallucination problem by:

1. **Separating concerns**: Detection (deterministic) vs. explanation (AI)
2. **Enforcing boundaries**: Hard limits prevent AI from inventing risks
3. **Ensuring auditability**: Every claim is traceable
4. **Maintaining consistency**: Deterministic detection guarantees reproducibility

This architecture is defensible for:
- Technical contribution claims (O-1, EB-1A)
- Regulatory compliance (auditability requirements)
- Legal use cases (verifiable findings)
- Enterprise adoption (consistent behavior)
