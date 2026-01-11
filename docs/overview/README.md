# Overview Documentation

This section provides high-level context about the Contract Risk Triage Tool: what problem it solves, its design goals, and its place in the legal-tech ecosystem.

## Contents

- **[Problem Statement](problem_statement.md)**: The legal hallucination problem and why deterministic-first systems matter
- **[System Goals](system_goals.md)**: What this system aims to achieve and what it deliberately avoids
- **[Architecture Overview](../architecture/architecture_overview.md)**: High-level system design

## Key Concepts

### Deterministic-First Architecture

Unlike pure LLM-based contract analysis tools, this system uses a deterministic rule engine for all risk detection. LLMs are used only for explanation, never for detection. This ensures:

- **Auditability**: Every finding can be traced to a specific rule
- **Reproducibility**: Same contract produces same findings
- **No Hallucination**: LLMs cannot invent risks
- **Version Control**: Rule changes are explicit and trackable

### Neural-Symbolic Hybrid

The system combines:
- **Symbolic Layer**: Deterministic rules (regex, proximity logic)
- **Neural Layer**: LLM explanations (bounded, input-controlled)

This hybrid approach leverages the strengths of both: deterministic accuracy for detection, contextual explanation for understanding.

### Conservative by Design

The system is intentionally conservative:
- Uses language like "may indicate risk" not "is risky"
- Never declares enforceability or legality
- Always recommends legal counsel review
- Admits limitations explicitly
