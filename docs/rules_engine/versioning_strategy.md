# Versioning Strategy

## Rule Engine Versioning

The rule engine uses semantic versioning: `MAJOR.MINOR.PATCH`

- **Current version**: `1.0.3`
- **Version constant**: `RULE_ENGINE_VERSION` in `rules_engine.py`
- **Included in results**: All analysis results include the version

## Version Components

### MAJOR Version

Incremented when:
- Breaking changes to rule structure
- Changes that affect existing rule IDs
- Architectural changes to rule engine

**Example**: Changing from pattern-based to ML-based detection would be MAJOR.

### MINOR Version

Incremented when:
- New rules added
- Rule categories expanded
- New detection methods added
- Significant rule logic changes

**Example**: Adding 5 new HIGH risk rules would be MINOR.

### PATCH Version

Incremented when:
- Bug fixes in existing rules
- Alias additions
- Deduplication improvements
- Performance optimizations
- Documentation updates

**Example**: Adding alias to existing rule would be PATCH.

## Version History

### 1.0.3 (Current)

**Changes**:
- Added alias support for rules
- Improved deduplication (by rule_id only)
- Added clause number detection
- Added matched keywords extraction
- Added explicit aliases to governing law rule

### 1.0.2

**Changes**:
- Added development restriction rule (M_DEV_RESTRICT_01)
- Added confidentiality scope rule (M_CONF_SCOPE_01)
- Added residuals clause rule (M_RESIDUALS_01)
- Added injunctive relief rule (M_INJUNCT_01)

### 1.0.1

**Changes**:
- Added one-way indemnity rule (H_INDEM_ONEWAY_01)
- Added work product IP rule (H_IP_WORK_PRODUCT_01)
- Initial rule set

### 1.0.0

**Initial release**:
- Core rule set (HIGH, MEDIUM, LOW categories)
- Pattern-based and proximity-based detection
- Deduplication logic
- Severity aggregation

## Version Display

The rule engine version is displayed:
- In analysis results footer
- In logs (when findings are detected)
- In API responses (if API endpoints added)

**Format**: "Rule Engine Version 1.0.3"

## Why Versioning Matters

### For Users

- **Transparency**: Users know which rule set was used
- **Reproducibility**: Same version → same results
- **Trust**: Versioning shows system maturity

### For Legal Professionals

- **Auditability**: Can reference specific rule engine version
- **Consistency**: Same version produces consistent results
- **Verification**: Can verify findings against rule set version

### For Technical Reviewers

- **Traceability**: Can map findings to specific code version
- **Evolution**: Can track how system improves over time
- **Contribution**: Demonstrates systematic development

## Version Compatibility

### Backward Compatibility

- **Rule IDs**: Never change (immutable)
- **Rule structure**: Maintained across versions
- **Output format**: Consistent across versions

### Migration Strategy

When rules change:
- **New rules**: Added with new rule_ids
- **Deprecated rules**: Marked but not removed
- **Rule updates**: New rule_id created, old one deprecated

## Versioning Best Practices

1. **Increment on changes**: Every rule change increments version
2. **Document changes**: Changelog tracks what changed
3. **Test thoroughly**: New versions tested against golden fixtures
4. **Communicate changes**: Users informed of version updates
5. **Maintain history**: Version history preserved

## Future Versioning

Potential enhancements:
- **Rule-level versioning**: Individual rules could have versions
- **A/B testing**: Test new rules before full deployment
- **Rollback capability**: Revert to previous rule set if needed
- **Version comparison**: Show differences between versions

These would maintain auditability while enabling rule evolution.
