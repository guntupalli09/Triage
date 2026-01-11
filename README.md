# Contract Risk Triage Tool

A production-ready system for automated risk triage of commercial contracts (NDAs and MSAs). This tool uses a deterministic rule engine to detect risk indicators, combined with an LLM layer that provides contextual explanations of detected risks. It is designed for founders, CEOs, and legal teams who need rapid, auditable risk assessment before contract review.

## What This System Does

The Contract Risk Triage Tool analyzes uploaded contract documents using a deterministic rule engine that identifies common risk patterns through regex and proximity-based pattern matching. Detected risks are then explained by an LLM layer that provides business-focused context—not legal advice—about why these patterns may matter. The system produces structured reports with severity classifications (high, medium, low), matched excerpts, clause numbers where possible, and suggested negotiation considerations.

## What This System Does NOT Do

This tool does not provide legal advice, determine enforceability, identify jurisdiction-specific legality, or replace qualified legal counsel. It does not declare contracts "safe to sign" or "illegal." It does not use LLMs for risk detection—all risk identification is deterministic and auditable. The system is designed for triage and awareness, not final legal decisions.

## High-Level Architecture

The system follows a **neural-symbolic architecture** that strictly separates deterministic detection from AI-assisted explanation:

1. **Deterministic Rule Engine**: Regex and proximity-based pattern matching identifies risk indicators without any LLM involvement
2. **LLM Explainer Layer**: Receives only the detected findings (never the full contract) and provides business-focused explanations
3. **Strict Boundaries**: Architectural assertions prevent the LLM from inventing risks or seeing contract text
4. **Safe Failure Modes**: If the LLM fails, the system falls back to rule-engine-only results

This architecture solves the "legal hallucination problem" by ensuring all risk detection is deterministic, auditable, and version-controlled.

## Quick Start

### Prerequisites

- Python 3.8+
- Stripe account (for payments)
- OpenAI API key (for explanations, optional)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd Triage

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Running Locally

```bash
# Start the server
uvicorn main:app --reload

# Open browser to http://localhost:8000
```

For development mode (bypassing Stripe), set `DEV_MODE=true` in `.env`.

### Stripe Webhook Testing

```bash
# Install Stripe CLI
# https://stripe.com/docs/stripe-cli

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/stripe-webhook
```

## Safety-First Philosophy

This system is built on three core principles:

1. **Determinism First**: All risk detection is rule-based and auditable. No LLM is used for detection.
2. **Bounded LLM Usage**: LLMs only explain pre-identified risks. They never see full contract text and cannot invent new risks.
3. **Conservative Language**: The system uses phrases like "may indicate risk" and "commonly negotiated," never "safe to sign" or "illegal."

## Documentation

Comprehensive documentation is available in the `/docs` directory:

- **[Architecture Overview](docs/architecture/architecture_overview.md)**: System design and component interactions
- **[Rules Engine](docs/rules_engine/rules_engine_overview.md)**: How deterministic detection works
- **[LLM Layer](docs/llm_layer/llm_role_and_limits.md)**: LLM boundaries and safety guarantees
- **[Testing Strategy](docs/testing/testing_strategy.md)**: How we ensure consistency and accuracy
- **[Original Contribution](docs/contribution/original_technical_contribution.md)**: Technical innovation and differentiation

## Rule Engine Version

Current version: **1.0.3**

All analyses include the rule engine version for auditability and reproducibility.

## License

This is a production MVP. Customize as needed for your use case.

## Support

For technical questions, refer to the documentation in `/docs`. For issues or contributions, please follow standard GitHub workflows.
