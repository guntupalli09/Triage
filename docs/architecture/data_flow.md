# Data Flow

## End-to-End Flow

### Stage 1: File Upload

**Input**: User uploads PDF, DOCX, or TXT file

**Processing**:
1. File size validation (max 10MB)
2. File type validation (PDF, DOCX, or TXT only)
3. Text extraction using appropriate library:
   - PDF: PyPDF2
   - DOCX: python-docx
   - TXT: UTF-8 decode

**Output**: Plain text string

**Error Handling**: 
- Invalid file type → 400 error
- File too large → 400 error
- Extraction failure → 400 error with clear message

### Stage 2: Payment Processing

**Input**: Extracted contract text

**Processing**:
1. Create Stripe Checkout session
2. Store contract text in memory with signed session token
3. Redirect user to Stripe payment page

**Output**: Stripe Checkout URL

**Error Handling**:
- Stripe API failure → 500 error
- Missing Stripe config → 500 error

### Stage 3: Payment Confirmation

**Input**: Stripe webhook event (`checkout.session.completed`)

**Processing**:
1. Verify webhook signature
2. Extract `client_reference_id` (app session ID)
3. Mark session as paid in memory store

**Output**: Session marked as paid

**Error Handling**:
- Invalid signature → 400 error
- Unknown session → Warning logged

### Stage 4: Deterministic Detection

**Input**: Contract text (from paid session)

**Processing**:
1. Normalize whitespace
2. Chunk text (preserve structure)
3. Apply all rules:
   - Pattern-based rules: Direct regex matching
   - Proximity rules: Anchor + nearby pattern matching
4. Extract clause numbers (if found)
5. Extract matched keywords
6. Deduplicate by rule_id (keep first occurrence)
7. Calculate severity counts
8. Determine overall risk level

**Output**: 
```python
{
    "findings": [Finding, ...],
    "overall_risk": "high" | "medium" | "low",
    "rule_counts": {"high": int, "medium": int, "low": int},
    "version": "1.0.3"
}
```

**Error Handling**:
- Empty text → Returns empty findings, low risk
- Malformed text → Processes what it can

### Stage 5: LLM Explanation (Optional)

**Input**: Deterministic findings (NOT contract text)

**Processing**:
1. Validate findings exist (zero findings → fallback)
2. Build prompt with findings only
3. Call OpenAI API (temperature=0.2, JSON mode)
4. Validate response structure
5. Verify output maps to input findings
6. Enforce disclaimer

**Output**:
```json
{
    "overall_risk": "high" | "medium" | "low",
    "summary_bullets": ["...", ...],
    "top_issues": [
        {
            "title": "...",
            "severity": "...",
            "why_it_matters": "...",
            "negotiation_consideration": "..."
        }
    ],
    "possible_missing_sections": ["...", ...],
    "disclaimer": "..."
}
```

**Error Handling**:
- API failure → Fallback to rule-engine-only response
- Invalid JSON → Fallback
- Validation failure → Fallback

### Stage 6: Results Synthesis

**Input**: Deterministic findings + LLM explanation (or fallback)

**Processing**:
1. Map LLM issues to deterministic findings (for clause numbers/keywords)
2. Calculate statistics (finding counts, severity breakdown)
3. Render HTML template with:
   - Overall risk badge
   - Executive summary
   - Detected risk indicators
   - Possible missing sections
   - Negative guarantees
   - Rule engine version

**Output**: HTML page

**Error Handling**:
- Missing data → Graceful degradation
- Template error → 500 error

## Data Storage

### In-Memory Session Store

**Structure**:
```python
{
    "app_session_id": {
        "paid": bool,
        "text": str,
        "filename": str,
        "stripe_session_id": str,
        "expires_at": datetime
    }
}
```

**Lifecycle**:
- Created: On file upload
- Updated: On payment confirmation
- Expires: 24 hours after creation
- Cleanup: Automatic on each request

**Security**:
- Session IDs are signed with HMAC
- Tokens verified before access
- No database persistence

## Data Privacy

- **No Database**: All data stored in memory
- **No Accounts**: No user identification
- **Ephemeral Storage**: Data expires after 24 hours
- **No Logging of Contract Text**: Only findings are logged
- **No Third-Party Sharing**: Contract text never leaves the server

## Logging

### What Is Logged

- Deterministic findings (rule_id, severity, title)
- LLM input (findings summary, first 2000 chars)
- LLM output (top issues count)
- Payment confirmations
- Errors and warnings

### What Is NOT Logged

- Full contract text
- User identifying information
- Payment card details
- Stripe session IDs (only app session IDs)

## Performance Characteristics

- **Text Extraction**: ~100-500ms (depends on file size)
- **Rule Engine**: ~50-200ms (depends on text length)
- **LLM Call**: ~2-5 seconds (depends on API latency)
- **Total Analysis**: ~3-6 seconds (with LLM) or ~200ms (fallback only)

## Scalability Considerations

- **Stateless Design**: Each request is independent
- **In-Memory Storage**: Limited by server RAM
- **No Database**: No I/O bottlenecks
- **Horizontal Scaling**: Can run multiple instances
- **Session Cleanup**: Automatic expiration prevents memory leaks
