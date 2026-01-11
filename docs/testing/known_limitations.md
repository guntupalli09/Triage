# Known Limitations

This document explicitly lists known limitations of the Contract Risk Triage Tool. This transparency is essential for trust and proper use.

## Detection Limitations

### 1. False Positives

**Issue**: System may flag standard clauses as risky

**Example**: Standard limitation of liability clause may be flagged if wording is unusual

**Impact**: Users may waste time reviewing non-issues

**Mitigation**: 
- Conservative language ("may indicate risk")
- Clear disclaimers
- Recommendation to consult lawyers

**Acceptable**: False positives are safer than false negatives

### 2. Pattern-Based Only

**Issue**: System uses regex patterns, not semantic understanding

**Example**: May miss risks expressed in unusual wording

**Impact**: Some risks may not be detected

**Mitigation**:
- Broad pattern coverage
- Proximity-based rules for flexibility
- Regular rule updates

**Acceptable**: System is a triage tool, not comprehensive analysis

### 3. Language Limitations

**Issue**: Optimized for English commercial contracts

**Example**: May not work well for non-English contracts

**Impact**: Limited applicability to English-only contracts

**Mitigation**: Clear scope documentation

**Acceptable**: Scope is explicitly limited

### 4. Contract Type Limitations

**Issue**: Optimized for NDAs and MSAs

**Example**: May not detect risks in employment contracts, leases, etc.

**Impact**: Limited applicability to target contract types

**Mitigation**: Clear scope documentation

**Acceptable**: Scope is explicitly limited

## Explanation Limitations

### 1. LLM Dependency

**Issue**: LLM explanations depend on API availability

**Example**: If OpenAI API fails, fallback explanations are generic

**Impact**: Reduced explanation quality when API unavailable

**Mitigation**: Automatic fallback to rule-engine-only results

**Acceptable**: System works without LLM, just with reduced functionality

### 2. Explanation Quality

**Issue**: LLM explanations may vary in quality

**Example**: Some explanations may be less clear than others

**Impact**: Users may not understand all explanations equally well

**Mitigation**: 
- Conservative prompts
- Output validation
- Fallback available

**Acceptable**: Explanations are helpful but not perfect

### 3. Missing Sections Suggestions

**Issue**: LLM suggests missing sections, but these are not detected risks

**Example**: May suggest "termination rights" even if contract has them

**Impact**: Users may think sections are missing when they're not

**Mitigation**: Clear labeling as "possible missing sections" (suggestions)

**Acceptable**: Suggestions are helpful but not definitive

## Technical Limitations

### 1. File Format Support

**Issue**: Only supports PDF, DOCX, and TXT

**Example**: Cannot process scanned PDFs or images

**Impact**: Some contracts cannot be analyzed

**Mitigation**: Clear file format requirements

**Acceptable**: Covers majority of use cases

### 2. Text Extraction Quality

**Issue**: Text extraction may be imperfect

**Example**: Complex PDF layouts may extract poorly

**Impact**: Some contracts may not be fully analyzed

**Mitigation**: 
- Multiple extraction libraries
- Error handling
- Clear error messages

**Acceptable**: Works for standard contract formats

### 3. Session Storage

**Issue**: In-memory storage, lost on server restart

**Example**: Server restart loses all active sessions

**Impact**: Users may lose access to results

**Mitigation**: 
- 24-hour TTL
- Clear expiration messaging
- Results can be re-generated

**Acceptable**: Ephemeral storage is by design (privacy)

## Scope Limitations

### 1. Commercial Contracts Only

**Issue**: Optimized for commercial NDAs and MSAs

**Example**: May not work well for employment, real estate, M&A contracts

**Impact**: Limited applicability

**Mitigation**: Clear scope documentation

**Acceptable**: Scope is explicitly limited

### 2. Risk Patterns Only

**Issue**: Detects predefined risk patterns, not all possible risks

**Example**: May miss novel risk patterns

**Impact**: Some risks may not be detected

**Mitigation**: 
- Regular rule updates
- User feedback
- Rule expansion

**Acceptable**: System is a triage tool, not comprehensive

### 3. No Legal Analysis

**Issue**: Does not provide legal analysis or advice

**Example**: Cannot determine enforceability or legality

**Impact**: Users must consult lawyers for legal questions

**Mitigation**: Clear disclaimers and limitations

**Acceptable**: This is by design (not legal advice)

## Performance Limitations

### 1. Analysis Time

**Issue**: Analysis takes 3-6 seconds (with LLM)

**Example**: Large contracts may take longer

**Impact**: Users must wait for results

**Mitigation**: 
- Efficient text processing
- Optimized LLM calls
- Fallback is faster (~200ms)

**Acceptable**: Reasonable for analysis quality

### 2. Concurrent Requests

**Issue**: In-memory storage limits concurrent users

**Example**: High traffic may exhaust memory

**Impact**: System may need horizontal scaling

**Mitigation**: 
- Session expiration
- Memory monitoring
- Horizontal scaling possible

**Acceptable**: Can scale horizontally if needed

## Why These Limitations Are Acceptable

### 1. Triage Tool, Not Final Analysis

The system is designed as a **first-pass screening tool**, not comprehensive legal analysis. Limitations are acceptable because:
- Users should consult lawyers for final decisions
- System helps prioritize legal review
- False positives are safer than false negatives

### 2. Explicit Scope

Limitations are **explicitly documented**:
- Users know what system does and does not do
- Clear disclaimers prevent misuse
- Scope is intentionally limited

### 3. Safety First

Limitations prioritize **safety**:
- Conservative language prevents legal claims
- Explicit limitations build trust
- Fail-safe design ensures system always works

### 4. Continuous Improvement

Limitations are **acknowledged and addressed**:
- Regular rule updates
- User feedback incorporation
- System evolution over time

## How to Work Within Limitations

### For Users

1. **Understand scope**: Know what system does and does not do
2. **Use for triage**: Quick assessment before legal review
3. **Consult lawyers**: Always get legal review for high-risk contracts
4. **Provide feedback**: Help improve system over time

### For Developers

1. **Document limitations**: Keep this list updated
2. **Address limitations**: Prioritize improvements
3. **Test edge cases**: Verify system handles limitations gracefully
4. **Communicate clearly**: Ensure users understand limitations

This transparency builds trust and enables proper use of the system.
