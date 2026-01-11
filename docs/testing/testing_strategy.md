# Testing Strategy

## Testing Philosophy

The Contract Risk Triage Tool uses a **deterministic-first testing approach** that emphasizes:
- **Reproducibility**: Same input → same output
- **Regression prevention**: Changes don't break existing functionality
- **Golden fixtures**: Known contracts with expected outputs
- **Rule validation**: Each rule tested independently

## Test Categories

### 1. Unit Tests (Rules Engine)

**Scope**: Individual rule testing

**Approach**:
- Test each rule with known positive cases
- Test each rule with known negative cases
- Verify rule fires correctly
- Verify rule doesn't fire on false positives

**Example**:
```python
def test_unlimited_indemnification_rule():
    text = "Party shall indemnify without limit against all claims"
    findings = rule_engine.analyze(text)
    assert any(f.rule_id == "H_INDEM_01" for f in findings)
```

### 2. Integration Tests (End-to-End)

**Scope**: Full system flow

**Approach**:
- Upload known contract
- Verify deterministic findings
- Verify LLM explanation (if available)
- Verify results page renders

**Example**:
```python
def test_full_analysis_flow():
    # Upload golden NDA
    # Verify findings match expected
    # Verify LLM output (or fallback)
    # Verify results page
```

### 3. Golden Fixture Tests

**Scope**: Regression prevention

**Approach**:
- Maintain library of known contracts
- Expected findings documented
- Run before each deployment
- Verify no regressions

**See**: [Golden Fixtures](golden_fixtures.md)

### 4. Negative Tests

**Scope**: Error handling

**Approach**:
- Test invalid file types
- Test empty files
- Test malformed PDFs
- Test API failures
- Test session expiration

**Goal**: System handles errors gracefully

## Test Data

### Golden NDAs

**Location**: `/tests/golden_ndas/` (future)

**Contents**:
- `low_risk_nda.pdf`: Standard NDA, expected low risk
- `medium_risk_nda.pdf`: NDA with 2+ medium risks
- `high_risk_nda.pdf`: NDA with high-risk clauses

**Purpose**: Regression testing

### Test Contracts

**Types**:
- Clean contracts (no risks)
- Single-risk contracts (one rule fires)
- Multi-risk contracts (multiple rules fire)
- Edge cases (malformed text, special characters)

**Purpose**: Rule validation

## Regression Policy

### Before Deployment

1. **Run golden fixtures**: Verify expected outputs
2. **Run unit tests**: Verify all rules work
3. **Run integration tests**: Verify full flow
4. **Check logs**: Verify no unexpected warnings

### After Deployment

1. **Monitor error rates**: Track 400/500 errors
2. **Monitor fallback rate**: Track LLM failures
3. **Monitor finding counts**: Verify consistency
4. **User feedback**: Track reported issues

### Version Changes

When rule engine version changes:
1. **Document changes**: What rules changed
2. **Update golden fixtures**: Expected outputs may change
3. **Run regression suite**: Verify no unintended changes
4. **Update documentation**: Reflect new behavior

## Known Limitations

See [Known Limitations](known_limitations.md) for detailed list.

## Test Coverage Goals

- **Rules**: 100% of rules tested
- **Error paths**: All error scenarios tested
- **Integration**: Full flow tested
- **Regression**: Golden fixtures tested

## Continuous Testing

### Development

- **Pre-commit**: Run unit tests
- **Pre-push**: Run integration tests
- **CI/CD**: Run full test suite

### Production

- **Monitoring**: Track error rates
- **Logging**: Monitor warnings
- **User feedback**: Track issues

## Test Maintenance

### Regular Updates

- **New rules**: Add tests for new rules
- **Rule changes**: Update tests for changed rules
- **Golden fixtures**: Update expected outputs
- **Error cases**: Add tests for new error scenarios

### Test Documentation

- **Test purpose**: Why each test exists
- **Expected behavior**: What should happen
- **Known issues**: What doesn't work yet
- **Future improvements**: What to test next

This testing strategy ensures system reliability and prevents regressions.
