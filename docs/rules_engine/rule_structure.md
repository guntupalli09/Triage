# Rule Structure

## Rule Definition

Each rule is defined as a `Rule` dataclass with the following fields:

```python
@dataclass(frozen=True)
class Rule:
    rule_id: str              # Unique identifier (e.g., "H_INDEM_01")
    rule_name: str            # Machine-friendly name (e.g., "unlimited_indemnification")
    title: str                # Human-readable title
    severity: Severity        # HIGH, MEDIUM, or LOW
    rationale: str            # Why this rule matters
    
    # Detection method (one of):
    pattern: Optional[str] = None           # Direct regex pattern
    anchors: Optional[List[str]] = None    # Anchor patterns (for proximity)
    nearby: Optional[List[str]] = None     # Nearby patterns (for proximity)
    window: int = 350                       # Proximity window (characters)
    
    # LLM validation
    aliases: List[str] = None              # Alternative names for validation
```

## Rule ID Format

Rule IDs follow the pattern: `{SEVERITY}_{CATEGORY}_{NUMBER}`

- **Severity**: `H` (high), `M` (medium), `L` (low)
- **Category**: Abbreviation (e.g., `INDEM`, `IP`, `CONF`)
- **Number**: Sequential (e.g., `01`, `02`)

Examples:
- `H_INDEM_01`: High-risk indemnification rule #1
- `M_CONF_01`: Medium-risk confidentiality rule #1
- `L_GOVLAW_01`: Low-risk governing law rule #1

## Detection Methods

### Method 1: Pattern-Based

Direct regex pattern matching:

```python
Rule(
    rule_id="H_IP_01",
    rule_name="broad_ip_assignment",
    title="Broad IP assignment / ownership transfer language",
    severity=Severity.HIGH,
    rationale="Assignment language may transfer ownership...",
    pattern=r"\b(assigns?|transfer(s|red)?|hereby\s+assigns?)\b.*?\ball\s+right[s]?,\s*title,\s*and\s+interest\b",
)
```

**How it works**:
1. Search entire text for pattern matches
2. For each match, create a finding
3. Extract matched text as excerpt

**Use when**: Risk can be detected with a single pattern.

### Method 2: Proximity-Based

Anchor + nearby pattern matching:

```python
Rule(
    rule_id="H_INDEM_01",
    rule_name="unlimited_indemnification",
    title="Potentially unlimited indemnification",
    severity=Severity.HIGH,
    rationale="Indemnity obligations may be uncapped...",
    anchors=[r"\bindemnif\w+\b", r"\bhold\s+harmless\b"],
    nearby=[
        r"\bno\s+limit\b",
        r"\bwithout\s+limit\b",
        r"\bunlimited\b",
    ],
    window=400,
)
```

**How it works**:
1. Find all anchor pattern matches
2. For each anchor, check ±window characters for nearby patterns
3. If nearby pattern found, create finding at anchor location

**Use when**: Risk requires two patterns to be close but not adjacent.

## Alias Support

Rules can define explicit aliases for LLM output validation:

```python
Rule(
    rule_id="L_GOVLAW_01",
    rule_name="governing_law_venue",
    title="Specific governing law or venue",
    aliases=["governing_law_and_venue"],
)
```

**Purpose**: Prevents false warnings when LLM uses alternative phrasing.

**How it works**:
- Aliases are normalized (lowercase, no punctuation, underscores)
- LLM output titles are normalized the same way
- Validation checks rule_name, title, and aliases

## Finding Creation

When a rule matches, a `Finding` object is created:

```python
@dataclass
class Finding:
    rule_id: str
    rule_name: str
    title: str
    severity: Severity
    rationale: str
    matched_excerpt: str      # Text that triggered the rule
    position: int              # Character position in text
    context: str               # Context around match
    clause_number: Optional[str] = None      # Detected clause ref
    matched_keywords: List[str] = None       # Key phrases
    aliases: List[str] = None                # Rule aliases
```

## Deduplication

Findings are deduplicated by `rule_id`:
- Only first occurrence of each rule is kept
- Prevents inflated counts from multiple matches
- Ensures one finding per risk type per contract

## Rule Versioning

Rules are versioned as part of the rule engine:
- Current version: `1.0.3`
- Version included in all analysis results
- Changes to rules increment version number

## Adding New Rules

To add a new rule:

1. **Choose severity**: HIGH, MEDIUM, or LOW
2. **Generate rule_id**: Follow format `{SEVERITY}_{CATEGORY}_{NUMBER}`
3. **Define detection**: Pattern-based or proximity-based
4. **Write rationale**: Explain why this matters
5. **Add aliases** (optional): For LLM validation
6. **Test**: Verify rule fires on test cases
7. **Update version**: Increment rule engine version

## Rule Maintenance

Rules should be:
- **Specific**: Target specific risk patterns
- **Conservative**: Prefer false positives over false negatives
- **Documented**: Rationale explains why it matters
- **Tested**: Verified against known contracts
- **Versioned**: Changes tracked in version number

## Best Practices

1. **Use proximity rules** when patterns may be separated
2. **Add aliases** for common LLM phrasings
3. **Keep patterns specific** to avoid false positives
4. **Document rationale** clearly
5. **Test thoroughly** before deployment
