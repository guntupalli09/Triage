# Problem Statement

## The Legal Hallucination Problem

Traditional AI-powered contract analysis tools face a fundamental challenge: **legal hallucination**. When large language models (LLMs) analyze contracts end-to-end, they can:

1. **Invent risks that don't exist**: The model may flag clauses as problematic when they are standard and acceptable
2. **Miss real risks**: The model may fail to detect actual problematic language
3. **Provide inconsistent results**: The same contract analyzed twice may produce different findings
4. **Lack auditability**: It's impossible to trace why a risk was flagged—was it a real pattern or model hallucination?

This creates a **trust problem**: users cannot rely on the system's output because they cannot verify its claims.

## Why This Matters

For founders signing NDAs and MSAs:

- **False positives** waste legal budget on non-issues
- **False negatives** expose companies to real risk
- **Inconsistency** undermines confidence in the tool
- **Lack of auditability** prevents legal review of the tool's findings

For legal professionals:

- **Unverifiable claims** cannot be used in legal strategy
- **Hallucinated risks** damage credibility with clients
- **Non-deterministic behavior** prevents integration into legal workflows

For regulatory and immigration contexts (O-1, EB-1A):

- **Auditability requirements** demand traceable, deterministic systems
- **Technical contribution claims** require verifiable innovation
- **Reliability standards** necessitate consistent, reproducible results

## The Solution: Neural-Symbolic Architecture

The Contract Risk Triage Tool solves this by separating **detection** (deterministic) from **explanation** (AI-assisted):

1. **Deterministic Rule Engine**: Uses explicit regex patterns and proximity logic to detect risk indicators. Every finding is traceable to a specific rule with a unique ID.

2. **Bounded LLM Layer**: AI only explains pre-identified risks. It never sees the full contract and cannot invent new risks.

This architecture provides:
- **Auditability**: Every risk claim maps to a specific rule
- **Consistency**: Same contract always produces same findings
- **Trust**: Users can verify why risks were flagged
- **Safety**: Hard architectural boundaries prevent hallucination

## What This Enables

With deterministic detection and bounded AI explanation:

- Founders can quickly triage contracts before expensive legal review
- Legal teams can use the tool as a first-pass screening mechanism
- Organizations can build consistent contract review processes
- Technical systems can claim deterministic, auditable behavior for regulatory purposes

The system does not replace legal counsel, but it provides a reliable, auditable foundation for contract risk assessment.
