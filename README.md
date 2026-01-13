# Triage AI — Contract Risk Intelligence

A production-ready system for automated risk triage of commercial contracts (NDAs and MSAs). Uses a deterministic rule engine for risk detection, combined with an LLM layer for contextual explanations. Designed for founders, CEOs, and legal teams who need rapid, auditable risk assessment.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (see Configuration below)
# Run the application
uvicorn main:app --reload
```

## What This System Does

Analyzes uploaded contract documents using deterministic pattern matching to identify common risk indicators. Detected risks are explained by an LLM layer that provides business-focused context—not legal advice. Produces structured reports with severity classifications, matched excerpts, and suggested negotiation considerations.

**See**: [What This Tool Is NOT](docs/use_cases/what_this_tool_is_not.md) for explicit limitations and non-claims.

## System Architecture

**Neural-Symbolic Architecture with Deterministic Control Plane**:
- **Deterministic Rule Engine**: All risk detection is rule-based (no LLM involvement)
- **LLM Explanation Layer**: Only explains pre-identified findings (never sees contract text)
- **Hard Boundaries**: Architectural guards prevent LLM from inventing risks
- **Safe Failure Modes**: System works even if LLM is unavailable

**See**: [Architecture Documentation](docs/architecture/) for detailed system design.

## Testing

**Test Results**: 57/59 tests passing (96.6% pass rate)

```bash
# Run all tests
pytest tests/ -v

# Quick summary
pytest tests/ --tb=no -q
```

**See**: [Test Results & Coverage](docs/testing/test_results.md) for detailed test documentation.

## Documentation

Comprehensive documentation is available in the `/docs` directory:

### Core Documentation
- **[Architecture Overview](docs/architecture/architecture_overview.md)**: System design and component interactions
- **[Neural-Symbolic Design](docs/architecture/neural_symbolic_design.md)**: Deterministic control plane architecture
- **[Data Flow](docs/architecture/data_flow.md)**: How data moves through the system

### Rules Engine
- **[Rules Engine Overview](docs/rules_engine/rules_engine_overview.md)**: How deterministic detection works
- **[Rule Structure](docs/rules_engine/rule_structure.md)**: Rule format and patterns
- **[Rule Categories](docs/rules_engine/rule_categories.md)**: Types of rules and examples
- **[Versioning Strategy](docs/rules_engine/versioning_strategy.md)**: Ruleset versioning and changelog

### LLM Layer
- **[LLM Role & Limits](docs/llm_layer/llm_role_and_limits.md)**: LLM boundaries and safety guarantees
- **[Hallucination Prevention](docs/llm_layer/hallucination_prevention.md)**: How we prevent LLM from inventing risks
- **[Prompt Strategy](docs/llm_layer/prompt_strategy.md)**: LLM prompt design

### Testing & Quality
- **[Testing Strategy](docs/testing/testing_strategy.md)**: Testing philosophy and approach
- **[Test Results](docs/testing/test_results.md)**: Detailed test coverage and results
- **[Regression Policy](docs/testing/regression_policy.md)**: How we prevent breaking changes
- **[Known Limitations](docs/testing/known_limitations.md)**: Current limitations and edge cases

### Safety & Compliance
- **[Auditability](docs/compliance/auditability.md)**: How analyses are auditable
- **[Data Privacy](docs/compliance/data_privacy.md)**: Data handling and privacy
- **[Security Posture](docs/compliance/security_posture.md)**: Security measures
- **[Legal Disclaimer](docs/compliance/legal_disclaimer.md)**: Legal boundaries

### Use Cases
- **[For Founders](docs/use_cases/founders.md)**: How founders can use this tool
- **[For Freelancers](docs/use_cases/freelancers.md)**: Freelancer use cases
- **[Enterprise Review](docs/use_cases/enterprise_review.md)**: Enterprise deployment
- **[What This Tool Is NOT](docs/use_cases/what_this_tool_is_not.md)**: Explicit limitations

### Technical Details
- **[Original Contribution](docs/contribution/original_technical_contribution.md)**: Technical innovation
- **[Why Determinism Matters](docs/contribution/why_determinism_matters.md)**: Design philosophy
- **[Comparison to AI Wrappers](docs/contribution/comparison_to_ai_wrappers.md)**: How this differs

## Configuration

### Runtime Modes (DEV_MODE)

The application supports two runtime modes:

**Demo Mode** (`DEV_MODE=true`):
- Stripe disabled (no payment required)
- OpenAI optional (LLM skipped if key missing)
- Use for demos, testing, development

**Production Mode** (`DEV_MODE=false`):
- Stripe required (payment flow enabled)
- OpenAI required (startup error if missing)
- Use for real customer transactions

Set in environment variables:
```bash
DEV_MODE=true   # Demo mode
DEV_MODE=false  # Production mode
```


**See**: [Architecture Documentation](docs/architecture/) for detailed configuration options.

## Rule Engine

- **Version**: 1.0.3 (see `rules/version.json`)
- **Coverage**: Commercial NDAs and MSAs
- **Detection**: Regex and proximity-based pattern matching
- **Anchoring**: All findings include exact text positions (start_index, end_index, exact_snippet)
- **Suppression**: Deterministic false-positive suppression layer

**See**: [Rules Engine Documentation](docs/rules_engine/) for detailed rule design, structure, and examples.

## Safety & Legal Defensibility

- **Non-Advisory**: Uses "may indicate" language, never "safe to sign" or "illegal"
- **Auditable**: Every finding includes ruleset version, matched excerpts, and position anchors
- **Reproducible**: Same contract + same version = same output
- **LLM Lockdown**: Hard boundaries prevent LLM from seeing contract text or inventing risks

**See**: [Compliance Documentation](docs/compliance/) for detailed safety and legal defensibility measures.

## License

This is a production MVP. Customize as needed for your use case.

## Support

For technical questions, refer to the documentation in `/docs`. For issues or contributions, please follow standard GitHub workflows.
