# High Risk Example

## Sample Contract

**Type**: MSA with problematic clauses

**Characteristics**:
- Unlimited indemnification
- Broad IP assignment
- One-way obligations
- 1+ high-risk patterns

## Expected Analysis Results

### Deterministic Findings

**Findings Count**: 1-3

**Rule Counts**:
- High: 1-2
- Medium: 0-1
- Low: 0-1

**Overall Risk**: HIGH

### Example Findings

**Finding 1**:
- **Rule ID**: `H_INDEM_01`
- **Title**: Potentially unlimited indemnification
- **Severity**: HIGH
- **Matched Excerpt**: "...Party A shall indemnify Party B against all claims, without limit, arising from..."
- **Clause Number**: "8.3" (if detected)
- **Matched Keywords**: ["indemnify", "without limit"]

**Finding 2** (if present):
- **Rule ID**: `H_IP_01`
- **Title**: Broad IP assignment / ownership transfer language
- **Severity**: HIGH
- **Matched Excerpt**: "...Developer hereby assigns to Company all right, title, and interest in the Work Product..."
- **Clause Number**: "6.1" (if detected)
- **Matched Keywords**: ["assigns", "all right title and interest"]

### LLM Explanation

**Summary Bullets**:
- "High-level: the deterministic engine flagged one or more high-risk patterns that may materially increase exposure"
- "Unlimited indemnification can expose you to costs far beyond the contract value"
- "Broad IP assignment may transfer ownership of your work product"
- "Exercise caution and consult legal counsel before signing"

**Top Issues**:

**Issue 1**:
- **Title**: Potentially unlimited indemnification
- **Severity**: HIGH
- **Why This May Matter**: "Unlimited indemnification obligations can expose you to costs far exceeding the contract value. If a claim arises, you may be responsible for all damages, legal fees, and related costs without any cap."
- **Negotiation Consideration**: "This is commonly negotiated. Consider requesting a cap tied to contract value (e.g., 1-2x annual fees) or mutual indemnification with reasonable limits."

**Issue 2** (if present):
- **Title**: Broad IP assignment / ownership transfer language
- **Severity**: HIGH
- **Why This May Matter**: "Broad IP assignment language may transfer ownership of your work product to the other party. This could mean you lose rights to work you created, even if it's not directly related to the contract."
- **Negotiation Consideration**: "This is commonly negotiated. Consider requesting a limited license instead of full assignment, or clarifying that assignment applies only to work specifically created for the contract."

**Possible Missing Sections**:
- "Limitation of liability (confirm it exists and covers key categories)"
- "Termination rights (confirm notice windows and renewal terms)"
- "Dispute resolution (confirm arbitration vs. litigation)"
- "Data protection (if applicable)"

### Results Page Display

**Risk Badge**: Red (HIGH RISK INDICATORS DETECTED)

**Executive Summary**: 
- High-risk patterns detected
- Exercise caution and review carefully

**Detected Risk Indicators**: 
- 1-2 high-severity issues with detailed explanations

**Statistics**:
- Total Findings: 1-3
- High Risk: 1-2
- Medium Risk: 0-1
- Low Risk: 0-1

**Rule Engine Version**: 1.0.3

## Interpretation

### What This Means

- **High risk**: Contract has material risk exposure
- **Serious issues**: Clauses may create significant liability
- **Urgent review**: Should get legal review immediately

### What to Do

1. **Do not sign**: Do not sign without legal review
2. **Legal review**: Get full legal review immediately
3. **Negotiate**: Use findings to guide negotiation
4. **Consider alternatives**: May need to walk away if risks unacceptable

## Important Notes

- **Not safe to sign**: High risk means significant exposure
- **Legal review essential**: Always get legal review for high-risk contracts
- **Negotiation critical**: These clauses should be negotiated
- **Context matters**: Risk level depends on your specific situation

This example demonstrates what users should expect from a high-risk contract analysis.
