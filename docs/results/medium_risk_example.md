# Medium Risk Example

## Sample Contract

**Type**: NDA with some problematic clauses

**Characteristics**:
- Indefinite confidentiality obligations
- Development restrictions tied to confidential information
- Auto-renewal clause
- 2+ medium-risk patterns

## Expected Analysis Results

### Deterministic Findings

**Findings Count**: 2-3

**Rule Counts**:
- High: 0
- Medium: 2-3
- Low: 0-1

**Overall Risk**: MEDIUM

### Example Findings

**Finding 1**:
- **Rule ID**: `M_CONF_01`
- **Title**: Confidentiality may be perpetual / indefinite
- **Severity**: MEDIUM
- **Matched Excerpt**: "...confidentiality obligations shall survive in perpetuity..."
- **Clause Number**: "3.2" (if detected)
- **Matched Keywords**: ["confidentiality", "perpetuity"]

**Finding 2**:
- **Rule ID**: `M_DEV_RESTRICT_01`
- **Title**: Development restriction tied to confidential information
- **Severity**: MEDIUM
- **Matched Excerpt**: "...not to develop products that compete with those based on Confidential Information..."
- **Clause Number**: "4.1" (if detected)
- **Matched Keywords**: ["not to develop", "compete", "based on"]

### LLM Explanation

**Summary Bullets**:
- "Medium-level: multiple negotiable risk patterns were detected"
- "Indefinite confidentiality may create long-term compliance burden"
- "Development restrictions may limit future work opportunities"
- "Review the highlighted clauses with legal counsel"

**Top Issues**:

**Issue 1**:
- **Title**: Confidentiality may be perpetual / indefinite
- **Severity**: MEDIUM
- **Why This May Matter**: "Indefinite confidentiality obligations can create long-term compliance burden and uncertainty around retention and disclosure. You may need to maintain confidentiality indefinitely, which can limit future business activities."
- **Negotiation Consideration**: "This is commonly negotiated. Consider requesting a time limit (e.g., 2-5 years) or standard carve-outs for public information."

**Issue 2**:
- **Title**: Development restriction tied to confidential information
- **Severity**: MEDIUM
- **Why This May Matter**: "Restrictions on developing competing products, even when tied to confidential information, can limit future work opportunities. This may prevent you from entering related markets."
- **Negotiation Consideration**: "This is commonly negotiated. Consider clarifying that restrictions apply only to products directly derived from confidential information, not general market knowledge."

**Possible Missing Sections**:
- "Termination rights (confirm notice windows and renewal terms)"
- "Residuals clause (confirm general knowledge can be used)"
- "Dispute resolution (confirm arbitration vs. litigation)"
- "Data protection (if applicable)"

### Results Page Display

**Risk Badge**: Yellow (MEDIUM RISK INDICATORS DETECTED)

**Executive Summary**: 
- Multiple negotiable risk patterns detected
- Review highlighted clauses

**Detected Risk Indicators**: 
- 2-3 medium-severity issues with explanations

**Statistics**:
- Total Findings: 2-3
- High Risk: 0
- Medium Risk: 2-3
- Low Risk: 0-1

**Rule Engine Version**: 1.0.3

## Interpretation

### What This Means

- **Medium risk**: Contract has some problematic clauses
- **Negotiable issues**: Clauses are commonly negotiated
- **Review needed**: Should get legal review before signing

### What to Do

1. **Review findings**: Understand each detected risk
2. **Legal review**: Get legal review, focus on flagged clauses
3. **Negotiate**: Use findings to guide negotiation discussions
4. **Decide**: After legal review, decide if risks are acceptable

## Important Notes

- **Not a deal-breaker**: Medium risk doesn't mean "don't sign"
- **Negotiable**: These clauses are commonly negotiated
- **Context matters**: Risk level depends on your specific situation
- **Legal review essential**: Always get legal review for medium-risk contracts

This example demonstrates what users should expect from a medium-risk contract analysis.
