# Data Privacy

## Privacy-First Design

The Contract Risk Triage Tool is designed with privacy as a core principle. The system minimizes data collection, storage, and retention.

## Data Collection

### What We Collect

**Contract Text**:
- Collected: Yes (required for analysis)
- Stored: Temporarily in memory (24-hour TTL)
- Shared: Never shared with third parties
- Logged: No (full text never logged)

**File Metadata**:
- Collected: Yes (filename, file size)
- Stored: Temporarily in memory (24-hour TTL)
- Shared: Never shared with third parties
- Logged: Yes (filename only, for debugging)

**Analysis Results**:
- Collected: Yes (findings, risk level)
- Stored: Not persisted (ephemeral)
- Shared: Never shared with third parties
- Logged: Yes (findings summary, not full text)

### What We Do NOT Collect

- **User identifying information**: No accounts, no emails, no names
- **Payment card details**: Handled by Stripe, never stored
- **IP addresses**: Not logged or stored
- **Browser information**: Not collected
- **Location data**: Not collected

## Data Storage

### In-Memory Only

**Storage Type**: In-memory (RAM)

**Structure**:
```python
{
    "app_session_id": {
        "paid": bool,
        "text": str,           # Contract text
        "filename": str,
        "stripe_session_id": str,
        "expires_at": datetime
    }
}
```

**Characteristics**:
- **Ephemeral**: Data exists only in server memory
- **No persistence**: No database, no file storage
- **Automatic expiration**: 24-hour TTL
- **Server restart**: All data lost on restart

### No Database

**Design Decision**: No database by design

**Benefits**:
- **Privacy**: No persistent storage of sensitive data
- **Simplicity**: No database to secure or maintain
- **Compliance**: Easier to meet data retention requirements

**Trade-offs**:
- **No history**: Users cannot access past analyses
- **Session loss**: Server restart loses active sessions
- **No analytics**: Cannot track usage patterns

## Data Retention

### Automatic Expiration

**TTL**: 24 hours from session creation

**Process**:
- Session created on file upload
- Expires 24 hours later
- Automatically cleaned up on each request

**Result**: Contract text deleted within 24 hours, maximum

### No Manual Deletion

**Design**: No manual deletion needed

**Reason**: Automatic expiration ensures data is deleted

**Exception**: Server restart immediately deletes all data

## Data Sharing

### No Third-Party Sharing

**Policy**: Contract text never shared with third parties

**Exceptions**:
- **OpenAI API**: Receives findings only (not contract text)
- **Stripe**: Receives payment information (not contract text)

**Verification**: 
- LLM input logged (first 2000 chars) shows only findings
- No contract text in logs
- No contract text in API calls

### API Usage

**OpenAI API**:
- **What's sent**: Deterministic findings only
- **What's NOT sent**: Full contract text
- **Purpose**: Generate explanations
- **Retention**: Subject to OpenAI's privacy policy

**Stripe API**:
- **What's sent**: Payment information
- **What's NOT sent**: Contract text
- **Purpose**: Process payments
- **Retention**: Subject to Stripe's privacy policy

## Data Security

### Transmission Security

**HTTPS**: All communications encrypted in transit

**Recommendation**: Use HTTPS in production

### Storage Security

**In-Memory**: Data stored only in server RAM

**Access Control**: No user accounts, no authentication needed

**Server Security**: Depends on hosting provider security

### No Data Export

**Policy**: No data export functionality

**Reason**: Privacy-first design, no persistent storage

**Exception**: Users can download their own results page (HTML)

## Compliance Considerations

### GDPR

**Applicability**: May apply if processing EU data

**Compliance Measures**:
- **Minimal data**: Only necessary data collected
- **Short retention**: 24-hour maximum retention
- **No sharing**: Contract text never shared
- **User control**: Users can choose not to use system

**Note**: Consult legal counsel for full GDPR compliance assessment

### CCPA

**Applicability**: May apply if processing California resident data

**Compliance Measures**:
- **No sale**: Data never sold
- **Minimal collection**: Only necessary data
- **Short retention**: 24-hour maximum

**Note**: Consult legal counsel for full CCPA compliance assessment

### HIPAA

**Not Applicable**: System does not process health information

**Note**: Do not use for healthcare-related contracts

## User Rights

### Right to Access

**Current**: No persistent storage, so no data to access

**Future**: If storage added, users would have right to access their data

### Right to Deletion

**Current**: Automatic deletion after 24 hours

**Future**: If storage added, users would have right to immediate deletion

### Right to Portability

**Current**: No persistent storage, so no data to export

**Future**: If storage added, users would have right to export their data

## Breach Response

### If Data Breach Occurs

**Immediate Actions**:
1. **Assess scope**: Determine what data was accessed
2. **Notify users**: If user data affected (if identifiable)
3. **Secure system**: Fix security vulnerability
4. **Document**: Record breach and response

**Note**: With no user accounts and ephemeral storage, breach impact is limited

## Best Practices

### For Users

1. **Understand privacy**: Know that data is ephemeral
2. **Don't upload sensitive data**: If extremely sensitive, consider alternatives
3. **Review results immediately**: Data expires in 24 hours
4. **Use HTTPS**: Ensure secure connection

### For Operators

1. **Use HTTPS**: Encrypt all communications
2. **Secure server**: Follow hosting provider security best practices
3. **Monitor access**: Log access attempts
4. **Update regularly**: Keep dependencies updated

## Privacy Policy Updates

**Policy Version**: 1.0

**Updates**: Privacy policy may be updated over time

**Notification**: Users should review privacy documentation periodically

This privacy-first design minimizes data collection and retention while maintaining system functionality.
