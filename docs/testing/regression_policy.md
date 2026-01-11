# Regression Policy

## Policy Statement

**No deployment shall proceed if golden fixture tests fail.**

This ensures system consistency and prevents unintended regressions.

## Pre-Deployment Checklist

### 1. Run Golden Fixtures

**Requirement**: All golden fixtures must pass

**Process**:
```bash
# Run golden fixture tests
python -m pytest tests/golden_fixtures/

# Verify all pass
# If any fail, investigate and fix before deployment
```

**Failure Handling**: 
- **Block deployment**: Do not deploy if tests fail
- **Investigate**: Determine cause of failure
- **Fix or document**: Fix regression or update expected if intentional

### 2. Run Unit Tests

**Requirement**: All unit tests must pass

**Process**:
```bash
# Run unit tests
python -m pytest tests/unit/

# Verify all pass
```

**Failure Handling**: Fix failing tests before deployment

### 3. Run Integration Tests

**Requirement**: All integration tests must pass

**Process**:
```bash
# Run integration tests
python -m pytest tests/integration/

# Verify all pass
```

**Failure Handling**: Fix failing tests before deployment

### 4. Check Logs

**Requirement**: No unexpected warnings or errors

**Process**:
- Review test logs
- Check for unexpected warnings
- Verify error handling works

**Failure Handling**: Investigate and fix unexpected issues

## Post-Deployment Monitoring

### 1. Monitor Error Rates

**Metric**: 400/500 error rates

**Threshold**: < 1% error rate

**Action**: If exceeded, investigate and fix

### 2. Monitor Fallback Rate

**Metric**: LLM fallback usage

**Threshold**: < 10% fallback rate

**Action**: If exceeded, investigate API issues

### 3. Monitor Finding Counts

**Metric**: Average findings per contract

**Threshold**: Consistent with historical averages

**Action**: If changed, investigate rule changes

### 4. User Feedback

**Metric**: Reported issues

**Threshold**: Track and respond to all reports

**Action**: Investigate and fix reported issues

## Version Change Policy

### Rule Engine Version Changes

When rule engine version changes:

1. **Document changes**: What rules changed, why
2. **Update golden fixtures**: Expected outputs may change
3. **Run regression suite**: Verify no unintended changes
4. **Update documentation**: Reflect new behavior
5. **Communicate**: Inform users of version change

### Breaking Changes

**Definition**: Changes that affect existing rule IDs or behavior

**Policy**: 
- **Avoid**: Don't change existing rule IDs
- **If necessary**: Create new rule_id, deprecate old one
- **Document**: Clearly document breaking changes
- **Version**: Increment MAJOR version

## Rollback Procedure

If regression detected in production:

1. **Identify issue**: What broke, when
2. **Assess impact**: How many users affected
3. **Rollback decision**: Determine if rollback needed
4. **Execute rollback**: Revert to previous version
5. **Fix issue**: Resolve regression in development
6. **Re-deploy**: Deploy fixed version

## Test Coverage Requirements

### Minimum Coverage

- **Rules**: 100% of rules tested
- **Error paths**: All error scenarios tested
- **Integration**: Full flow tested
- **Golden fixtures**: All fixtures tested

### Coverage Goals

- **Unit tests**: > 90% code coverage
- **Integration tests**: All critical paths
- **Regression tests**: All golden fixtures
- **Error tests**: All error scenarios

## Continuous Improvement

### Regular Reviews

- **Monthly**: Review test coverage
- **Quarterly**: Review golden fixtures
- **Annually**: Review regression policy

### Test Improvements

- **Add tests**: For new features
- **Update tests**: For changed features
- **Remove tests**: For deprecated features
- **Improve tests**: Better coverage, clearer assertions

This policy ensures system reliability and prevents regressions.
