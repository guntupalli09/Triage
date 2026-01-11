# Golden Fixtures

## Purpose

Golden fixtures are known contracts with documented expected outputs. They serve as regression tests to ensure the system produces consistent results over time.

## Fixture Structure

### Low Risk NDA

**File**: `low_risk_nda.pdf` (example)

**Characteristics**:
- Standard confidentiality terms
- Mutual obligations
- Reasonable time limits
- Standard carve-outs

**Expected Output**:
- **Findings**: 0-1 LOW severity findings
- **Overall Risk**: LOW
- **Rule Counts**: {"high": 0, "medium": 0, "low": 0-1}

**Use Case**: Verify system doesn't over-flag standard contracts

### Medium Risk NDA

**File**: `medium_risk_nda.pdf` (example)

**Characteristics**:
- Indefinite confidentiality
- Auto-renewal clause
- Development restrictions
- 2+ medium-risk patterns

**Expected Output**:
- **Findings**: 2-3 MEDIUM severity findings
- **Overall Risk**: MEDIUM
- **Rule Counts**: {"high": 0, "medium": 2-3, "low": 0-1}

**Use Case**: Verify medium-risk detection works

### High Risk MSA

**File**: `high_risk_msa.pdf` (example)

**Characteristics**:
- Unlimited indemnification
- Broad IP assignment
- One-way obligations
- 1+ high-risk patterns

**Expected Output**:
- **Findings**: 1+ HIGH severity findings
- **Overall Risk**: HIGH
- **Rule Counts**: {"high": 1+, "medium": 0-2, "low": 0-1}

**Use Case**: Verify high-risk detection works

## Expected Findings

Each fixture has documented expected findings:

### Low Risk NDA Expected Findings

```
Rule ID: L_GOVLAW_01 (if governing law clause present)
Severity: LOW
Title: Specific governing law or venue
```

### Medium Risk NDA Expected Findings

```
Rule ID: M_CONF_01
Severity: MEDIUM
Title: Confidentiality may be perpetual / indefinite

Rule ID: M_DEV_RESTRICT_01
Severity: MEDIUM
Title: Development restriction tied to confidential information
```

### High Risk MSA Expected Findings

```
Rule ID: H_INDEM_01
Severity: HIGH
Title: Potentially unlimited indemnification

Rule ID: H_IP_01
Severity: HIGH
Title: Broad IP assignment / ownership transfer language
```

## Regression Testing

### Process

1. **Load fixture**: Load known contract
2. **Run analysis**: Execute rule engine
3. **Compare results**: Verify findings match expected
4. **Check counts**: Verify rule counts match
5. **Verify risk level**: Verify overall risk matches

### Success Criteria

- **Exact match**: Findings match expected (rule_id, severity)
- **Count match**: Rule counts match expected
- **Risk match**: Overall risk level matches expected

### Failure Handling

If results don't match:
1. **Investigate**: Check what changed
2. **Document**: Record the difference
3. **Decide**: Is change intentional or regression?
4. **Fix or update**: Fix regression or update expected results

## Fixture Maintenance

### Adding New Fixtures

1. **Select contract**: Choose representative contract
2. **Run analysis**: Get initial results
3. **Document expected**: Record expected findings
4. **Add to suite**: Include in regression tests
5. **Version control**: Commit with expected outputs

### Updating Fixtures

When rules change:
1. **Re-run fixtures**: Get new results
2. **Compare**: See what changed
3. **Update expected**: Update expected outputs if intentional
4. **Document**: Record why expected changed

## Version Compatibility

### Rule Engine Versions

Each fixture documents:
- **Rule engine version**: Which version produced expected results
- **Test date**: When fixture was last validated
- **Expected changes**: What to expect if version changes

### Migration

When rule engine version changes:
1. **Re-run all fixtures**: Get new results
2. **Compare to expected**: Identify changes
3. **Update expected**: Update if changes are intentional
4. **Document migration**: Record version change and impact

## Future Enhancements

Potential improvements:
- **Automated regression**: CI/CD integration
- **Fixture library**: Expanded set of test contracts
- **Performance benchmarks**: Track analysis time
- **Coverage metrics**: Track which rules are tested

These would improve test reliability and coverage.
