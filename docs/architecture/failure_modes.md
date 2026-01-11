# Failure Modes and Safe Degradation

## Design Philosophy

The system is designed to **fail safely** and **degrade gracefully**. When components fail, the system continues operating with reduced functionality rather than crashing.

## Failure Scenarios

### 1. File Upload Failures

**Scenario**: User uploads invalid file

**Handling**:
- File type validation → 400 error with clear message
- File size validation → 400 error with clear message
- Text extraction failure → 400 error with helpful message

**User Experience**: Clear error message, can retry with different file

**System State**: No impact, request rejected before processing

### 2. Payment Processing Failures

**Scenario**: Stripe API unavailable or misconfigured

**Handling**:
- Missing Stripe config → 500 error: "Stripe is not configured"
- API failure → 500 error: "Failed to create payment session"
- Webhook signature failure → 400 error: "Invalid webhook signature"

**User Experience**: Error message, can retry later

**System State**: No session created, no data stored

### 3. Text Extraction Failures

**Scenario**: Malformed PDF or corrupted DOCX

**Handling**:
- PyPDF2 failure → Try to extract what's possible, log warning
- Empty extraction → 400 error: "File appears unreadable or empty"
- Partial extraction → Process available text, log warning

**User Experience**: Clear error or partial results with warning

**System State**: No analysis performed if extraction completely fails

### 4. Rule Engine Failures

**Scenario**: Rule engine encounters unexpected input

**Handling**:
- Empty text → Returns empty findings, low risk
- Malformed text → Processes what it can
- Regex errors → Caught and logged, rule skipped

**User Experience**: Analysis continues with available findings

**System State**: Partial results, system continues

### 5. LLM API Failures

**Scenario**: OpenAI API unavailable, rate limited, or returns error

**Handling**:
- API key missing → Fallback to rule-engine-only results
- API timeout → Fallback to rule-engine-only results
- Invalid JSON response → Fallback to rule-engine-only results
- Validation failure → Fallback to rule-engine-only results

**User Experience**: Results page shows rule-engine findings with note that LLM explanation unavailable

**System State**: Full functionality maintained (deterministic detection works)

**Fallback Response**:
- Uses rule rationale for explanations
- Provides generic summary based on risk level
- Suggests standard missing sections
- Includes disclaimer

### 6. Session Expiration

**Scenario**: User tries to access results after 24 hours

**Handling**:
- Session not found → 404 error: "Session not found or expired"
- Automatic cleanup on each request

**User Experience**: Clear message, can upload new file

**System State**: Expired sessions automatically removed

### 7. Payment Not Confirmed

**Scenario**: User reaches results page before payment confirmed

**Handling**:
- Payment pending → 202 response with "Payment pending" message
- User can refresh page

**User Experience**: Clear message, can refresh to check status

**System State**: Session exists but not marked paid

## Safe Degradation Strategy

### Level 1: Full Functionality

- File upload works
- Payment processed
- Rule engine detects risks
- LLM provides explanations
- Results displayed

### Level 2: Reduced Functionality (LLM Fails)

- File upload works
- Payment processed
- Rule engine detects risks
- LLM unavailable → Fallback explanations
- Results displayed (rule-engine-only)

### Level 3: Minimal Functionality (Payment Fails)

- File upload works
- Payment fails → Error message
- No analysis performed
- User can retry

### Level 4: No Functionality (Upload Fails)

- File upload fails → Error message
- No further processing
- User can retry with different file

## Error Messages

All error messages are:
- **User-friendly**: Clear, actionable language
- **Non-technical**: No stack traces exposed
- **Helpful**: Suggest what user can do
- **Conservative**: Don't reveal system internals

## Logging Strategy

### What Gets Logged

- **Errors**: All exceptions with context
- **Warnings**: Non-fatal issues (LLM fallback, etc.)
- **Info**: Key operations (findings detected, payment confirmed)
- **Debug**: Detailed flow (only in development)

### What Doesn't Get Logged

- Full contract text (privacy)
- User identifying information
- Payment card details
- Sensitive API keys

## Monitoring Recommendations

For production deployment, monitor:

1. **Error Rates**: Track 400/500 errors
2. **LLM Fallback Rate**: How often fallback is used
3. **Payment Success Rate**: Stripe checkout completion
4. **Session Expiration**: How many sessions expire unused
5. **File Processing Time**: Performance metrics

## Recovery Procedures

### LLM API Failure

**Automatic**: System falls back to rule-engine-only results

**Manual**: Check OpenAI API status, verify API key

### Payment Processing Failure

**Automatic**: Error returned to user

**Manual**: Check Stripe dashboard, verify webhook configuration

### Session Storage Full

**Automatic**: Expired sessions cleaned up on each request

**Manual**: Restart server to clear all sessions (if needed)

## Testing Failure Modes

The system is tested for:

- Invalid file uploads
- Payment processing failures
- LLM API failures
- Session expiration
- Malformed contract text
- Empty contracts

All failure modes are handled gracefully without system crashes.
