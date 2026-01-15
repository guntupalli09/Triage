# Deterministic–LLM Hybrid Architectures for Auditable Contract Risk Triage

# **Abstract**

Large Language Models (LLMs) have demonstrated strong performance in natural language understanding tasks, including contract analysis. However, their deployment in high-risk domains such as legal document review remains constrained by hallucination risk, non-determinism, and lack of auditability. This paper presents a deterministic–LLM hybrid architecture for contract risk triage that explicitly separates risk detection from contextual explanation. In the proposed system, a rule-based deterministic engine performs clause-level risk identification using versioned linguistic patterns, while an LLM is constrained to synthesizing executive-level explanations solely from pre-validated findings. This design ensures reproducibility, traceability, and safety while preserving the usability benefits of LLM-generated summaries. We describe the system architecture, rule versioning strategy, clause anchoring mechanism, and LLM lockdown constraints, and analyze the resulting guarantees around auditability and hallucination prevention. The proposed approach demonstrates a practical neural-symbolic pattern for deploying LLMs in legally sensitive workflows without exposing users to unbounded model behavior.

# **I. Introduction**

The adoption of Large Language Models (LLMs) for document analysis has accelerated rapidly across legal, financial, and compliance domains. Recent systems have shown promising results in summarizing contracts, extracting obligations, and identifying potential risks in agreements such as Non-Disclosure Agreements (NDAs) and Master Service Agreements (MSAs). Despite these advances, the direct application of LLM-only systems to legal documents introduces critical challenges related to reliability, explainability, and safety.

Legal contracts represent a uniquely high-risk input space. Minor linguistic variations can materially alter obligations, and incorrect interpretation may result in financial exposure, regulatory violations, or litigation. In this context, LLM behaviors such as hallucination, probabilistic inference, and non-deterministic outputs are not merely undesirable—they are unacceptable. A system that invents a risk clause or overlooks a critical provision cannot be meaningfully trusted by legal or executive stakeholders.

Existing approaches to contract analysis typically fall into two categories. Rule-based systems offer deterministic behavior and auditability but lack flexibility and require substantial manual engineering. LLM-based systems offer expressive language understanding but operate as opaque black boxes, often without reproducibility guarantees or verifiable reasoning paths. Hybrid approaches have been proposed, yet many still rely on LLMs to both detect and interpret legal risk, leaving the core safety problem unresolved.

This paper argues that effective deployment of AI in legal contract triage requires a strict separation of responsibilities between deterministic and probabilistic components. We present a deterministic–LLM hybrid architecture in which all risk detection is performed by a versioned, rule-based engine, while the LLM is constrained to contextual explanation and synthesis. The LLM is never permitted to discover new risks, access raw contract text, or override deterministic findings.

Our contributions are as follows:

- We propose a neural-symbolic contract triage architecture that eliminates LLM hallucination at the detection layer.
- We introduce a rule-set versioning and output hashing mechanism to ensure reproducibility and auditability of results.
- We describe a clause-anchoring strategy that ties each finding to a precise textual excerpt.
- We demonstrate how LLMs can be safely leveraged for executive-level explanations without compromising legal defensibility.

While the implementation described focuses on commercial NDAs and MSAs, the architectural principles generalize to other high-risk document analysis domains where deterministic guarantees are required.

**II. System Architecture**

The proposed contract risk triage system is designed around a strict separation of concerns between deterministic risk detection and probabilistic language generation. The architecture enforces a unidirectional flow of information, ensuring that non-deterministic components cannot influence the identification of legal risk. Figure 1 conceptually illustrates the pipeline.

**A. Architectural Overview**

The system consists of four primary components:

1. Document Ingestion and Normalization
2. Deterministic Rule Engine
3. LLM-Constrained Explanation Layer
4. Result Synthesis and Reporting

The pipeline is stateless and session-scoped: no user accounts or persistent document storage are required. Each analysis is executed independently, ensuring that identical inputs and rule configurations yield identical outputs.

**B. Document Ingestion and Normalization**

Uploaded contracts are accepted in standard formats (PDF and DOCX) and converted into normalized plain text. During this stage, the system removes non-semantic formatting artifacts such as excessive whitespace, line breaks, and pagination headers while preserving clause order and structural cues.

Normalization is intentionally conservative: no semantic rewriting or summarization is performed prior to deterministic analysis. This ensures that downstream pattern matching operates on content that faithfully reflects the original contractual language.

**C. Deterministic Rule Engine**

The deterministic rule engine is the foundational component of the system. Its sole responsibility is to identify predefined linguistic patterns that may indicate contractual risk. The engine operates without probabilistic inference, statistical weighting, or machine-learned parameters.

Each rule is defined by the following attributes:

- Rule Identifier: A stable, versioned identifier (e.g., H_INDEM_ONEWAY_01)
- Severity Level: High, Medium, or Low
- Pattern Definition: Regular expressions augmented with proximity and lookaround logic
- Rationale: A conservative explanation of why the pattern may indicate risk
- Aliases: Canonical and alternative semantic labels for downstream validation

Rules are grouped by severity class and evaluated sequentially against the normalized contract text. Matches are anchored using character offsets, enabling precise extraction of clause-level context.

To ensure reproducibility, the engine enforces:

- Rule-set immutability per version
- Deterministic execution order
- Deduplication of findings by rule identifier and clause position

The rule engine does not attempt to interpret intent, enforceability, or jurisdictional validity. Its output is strictly limited to the presence of linguistic constructs that commonly warrant legal review.

**D. Rule-Set Versioning and Reproducibility**

All deterministic rules are versioned using an explicit rule-set manifest. Each analysis embeds the active rule-set version in its output, along with a deterministic hash computed over the normalized document text and rule-set version identifier.

This mechanism ensures that:

- The same document analyzed under the same rule-set always produces identical findings
- Changes in output can be traced to specific rule modifications
- Historical analyses remain auditable even as the rule-set evolves

Such guarantees are essential in legal and compliance contexts, where stakeholders may need to explain or defend past system outputs.

**E. Clause Anchoring and Context Preservation**

Each deterministic finding includes:

- Start and end character indices
- An exact textual excerpt surrounding the match
- Optional clause numbering when detectable

By anchoring findings directly to the source text, the system enables reviewers to independently verify each risk indicator without relying on model-generated interpretation. This design choice reduces reviewer friction and supports side-by-side human validation.

**F. LLM-Constrained Explanation Layer**

The LLM component operates under strict constraints. It is never granted access to the full contract text. Instead, it receives only the structured output of the deterministic engine, including rule identifiers, severity levels, rationales, and matched excerpts.

The LLM’s role is limited to:

- Synthesizing executive-level summaries
- Grouping related findings
- Explaining why identified patterns may matter in business terms

The LLM is explicitly instructed not to:

- Discover new risks
- Reclassify severity
- Interpret legal enforceability
- Reference clauses beyond those provided

This constraint-based design eliminates hallucination at the detection layer while preserving the communicative strengths of LLMs.

**G. Result Synthesis and Reporting**

The final output merges deterministic findings with LLM-generated explanations into a structured report. Severity scoring is computed exclusively from deterministic results. Human-readable summaries are visually distinguished from raw findings to reinforce the system’s non-advisory nature.

All outputs include explicit disclaimers clarifying that the system performs automated pattern analysis and does not provide legal advice.

**III. Related Work**

Research on automated contract analysis spans multiple paradigms, including rule-based legal expert systems, statistical natural language processing, and, more recently, Large Language Model (LLM)–driven approaches. Each paradigm offers distinct advantages and limitations when applied to legally sensitive documents.

**A. Rule-Based and Expert Systems**

Early contract analysis systems relied heavily on manually engineered rules and legal ontologies to identify obligations, prohibitions, and risks. These approaches provided strong determinism and transparency, making them suitable for compliance-driven environments. However, their rigidity limited coverage, required extensive domain expertise to maintain, and struggled to adapt to linguistic variability across contracts.

Despite these limitations, deterministic systems remain attractive in legal contexts due to their reproducibility and auditability. Several commercial tools continue to employ rule-based engines for narrow tasks such as clause classification or obligation extraction. However, such systems typically lack natural language explanation capabilities, reducing accessibility for non-legal stakeholders.

**B. Statistical and Machine Learning Approaches**

Subsequent work introduced supervised and unsupervised machine learning techniques for contract classification, clause detection, and risk scoring. These approaches improved flexibility but introduced probabilistic uncertainty and training-data dependency. In legal domains, where annotated datasets are scarce and labeling consistency is difficult to guarantee, these methods face challenges related to generalization and explainability.

Furthermore, statistical models often require retraining when contract structures or language distributions shift, limiting their suitability for environments that demand stable, versioned behavior over time.

**C. LLM-Based Contract Analysis**

Recent advances in LLMs have enabled end-to-end contract review systems capable of summarization, risk identification, and recommendation generation. These systems benefit from strong language understanding and minimal feature engineering. However, multiple studies and industry reports have documented LLM failure modes, including hallucinated clauses, inconsistent outputs across runs, and sensitivity to prompt phrasing.

In legal and compliance contexts, these behaviors undermine trust. Systems that rely on LLMs to directly identify legal risk effectively conflate detection and interpretation, making it difficult to audit or reproduce results. Even when guardrails are applied, the probabilistic nature of LLM inference remains a fundamental limitation.

**D. Hybrid and Neural-Symbolic Approaches**

Hybrid systems combining symbolic reasoning with neural models have been proposed as a means to balance flexibility and control. Prior work in neural-symbolic reasoning demonstrates that constraining neural components with symbolic structures can improve reliability and interpretability. However, many hybrid legal AI systems still permit LLMs to influence risk detection or classification decisions, thereby reintroducing non-determinism into the core analytical pipeline.

In contrast, the architecture presented in this paper enforces a strict division: symbolic components are solely responsible for risk detection, while neural components are restricted to post-detection explanation. This design aligns with emerging best practices for deploying AI in high-risk domains, where safety and auditability are prioritized over generative breadth.

**E. Positioning of This Work**

This work differs from prior approaches by formalizing a deterministic-first contract analysis pipeline in which LLMs are treated as constrained explanatory agents rather than decision-makers. By combining versioned rule-sets, clause-level anchoring, and LLM lockdown mechanisms, the system achieves reproducibility and transparency without sacrificing usability.

The proposed architecture contributes a practical blueprint for integrating LLMs into legally sensitive workflows while preserving deterministic guarantees, addressing a gap between purely symbolic systems and unconstrained generative models.

**IV. LLM Lockdown and Safety Guarantees**

The integration of Large Language Models into legal workflows introduces unique safety challenges. While LLMs offer strong capabilities in summarization and natural language explanation, their probabilistic nature makes them unsuitable as primary decision-makers in high-risk domains. This section describes the constraint mechanisms used to ensure that LLM behavior in the proposed system remains bounded, auditable, and non-authoritative.

**A. Separation of Detection and Explanation**

A foundational design principle of the system is the strict separation between risk detection and risk explanation. All detection is performed exclusively by the deterministic rule engine. The LLM is never invoked to identify clauses, assess severity, or determine whether a contractual risk exists.

This separation prevents the LLM from:

- Inferring risks not explicitly detected by deterministic rules
- Overriding or reclassifying deterministic severity levels
- Introducing variability into core analytical outcomes

As a result, the system’s risk profile is entirely governed by a transparent and versioned rule-set.

**B. Restricted LLM Input Interface**

To further constrain model behavior, the LLM is provided with a minimal, structured input consisting solely of:

- Rule identifiers
- Severity classifications
- Deterministic rationales
- Clause-anchored textual excerpts

The LLM is explicitly denied access to:

- The full contract text
- Undetected clauses
- Prior or historical analyses
- External knowledge sources

This input restriction ensures that the LLM cannot infer context beyond what has been deterministically validated, effectively eliminating hallucination at the detection layer.

**C. Instructional Constraints and Prompt Design**

The LLM prompt is designed to reinforce its limited role. It instructs the model to:

- Summarize detected findings for executive audiences
- Use conservative, non-advisory language
- Avoid speculative or normative statements

The prompt explicitly prohibits:

- Legal recommendations
- Risk discovery
- Jurisdictional interpretation
- Severity reassessment

By constraining both input and instruction, the system enforces a predictable and explainable LLM behavior profile.

**D. Deterministic Output Enforcement**

All final risk scores and classifications are computed independently of the LLM. Even if the LLM output were malformed or unavailable, the deterministic findings remain intact and actionable.

In practice, this allows:

- Safe degradation in the event of LLM failure
- Consistent outputs across repeated analyses
- Clear attribution of responsibility between symbolic and neural components

This design ensures that LLM outputs enhance usability without becoming a single point of failure.

**E. Auditability and Traceability Guarantees**

Each analysis output includes:

- The active rule-set version
- Clause-level anchors
- Deterministic analysis hash

These artifacts enable post-hoc auditing and independent verification of results. Reviewers can trace each reported risk directly back to a specific rule and text excerpt, without reliance on model reasoning chains.

Such traceability is essential for enterprise and legal stakeholders, who must often justify decisions based on automated analysis.

**F. Safety Implications**

By enforcing LLM lockdown, the system avoids common failure modes observed in LLM-only legal tools, including:

- Hallucinated contractual obligations
- Inconsistent results across runs
- Overconfident or advisory language

The resulting architecture provides a practical example of how LLMs can be safely deployed in legally sensitive environments without compromising determinism or accountability.

**V. Evaluation and System Properties**

The proposed system is evaluated along qualitative and structural dimensions aligned with its intended use as a contract risk triage tool. Rather than optimizing for prediction accuracy against labeled datasets, the evaluation focuses on properties essential to legal and compliance workflows: determinism, reproducibility, auditability, and robustness against hallucination.

**A. Determinism and Reproducibility**

A primary requirement of the system is that identical inputs analyzed under the same rule-set produce identical outputs. This property is enforced through:

- Deterministic rule execution order
- Immutable rule-set versions
- Normalized document preprocessing
- Analysis hashing based on document text and rule-set version

Repeated analyses of the same contract consistently yield identical findings, severity classifications, and clause anchors. This reproducibility enables stakeholders to rely on outputs over time and supports post-hoc review of prior analyses.

**B. Rule Coverage and Severity Distribution**

The deterministic engine evaluates contracts against a curated set of risk rules spanning high, medium, and low severity categories. These rules are designed to capture commonly negotiated or reviewed clauses in commercial NDAs and MSAs, such as indemnification scope, liability limitations, intellectual property assignment, confidentiality duration, and development restrictions.

Severity scoring is computed exclusively from deterministic findings:

- Any high-severity finding yields an overall high-risk classification
- Multiple medium-severity findings yield a medium-risk classification
- Otherwise, the contract is classified as low risk

This transparent scoring mechanism avoids opaque weighting schemes and allows users to understand exactly how an overall assessment is derived.

**C. Clause-Level Anchoring Accuracy**

Each deterministic finding is anchored to a specific textual excerpt, including start and end character indices and surrounding context. This anchoring enables reviewers to rapidly locate the relevant language within the original document.

In practice, clause anchoring reduces review time by allowing users to validate findings without manually scanning entire agreements. It also supports downstream integrations such as PDF report generation and side-by-side human review.

**D. LLM Behavior Validation**

The LLM component was evaluated qualitatively to confirm adherence to its constrained role. Across repeated analyses:

- The LLM did not introduce risks not present in deterministic findings
- Severity levels remained unchanged by LLM output
- Generated summaries consistently referenced only provided excerpts

When the LLM component was intentionally disabled or unavailable, the system continued to produce complete deterministic outputs, demonstrating safe degradation.

These observations confirm that the LLM functions as an explanatory layer rather than a decision-making component.

**E. False Positive Control**

Deterministic rule matching is inherently conservative and may overfire in ambiguous contexts. To mitigate this, the system incorporates suppression logic based on local textual qualifiers (e.g., carve-outs, conditional language, or limiting phrases). Suppression reduces noise without removing transparency, as suppressed matches remain traceable for internal debugging.

This balance prioritizes trust over recall, reflecting the preferences of legal reviewers who favor fewer, higher-confidence findings.

**F. Computational Efficiency**

Because deterministic rules operate via regular expression matching and the LLM processes only structured findings rather than full documents, the system remains computationally efficient. This design reduces inference costs and latency, enabling near-real-time analysis even for multi-page agreements.

**G. Summary of Evaluated Properties**

The evaluation demonstrates that the system satisfies key non-functional requirements for legal triage tools:

- Deterministic outputs
- Reproducibility across runs
- Clause-level traceability
- LLM hallucination prevention
- Cost-efficient inference

These properties collectively distinguish the system from unconstrained LLM-based contract analysis tools.

# **VI. Limitations and Scope Boundaries**

While the proposed deterministic–LLM hybrid architecture provides strong guarantees around auditability and hallucination prevention, it is intentionally scoped to serve as a triage system, not a substitute for legal review. Several limitations are acknowledged.

First, the deterministic rule engine is limited by the coverage of its rule-set. Although the rules capture common high-impact contractual risk patterns, the absence of a match does not imply the absence of legal risk. Contracts may contain novel or highly customized language that falls outside predefined patterns.

Second, the system does not assess enforceability, jurisdiction-specific validity, or business appropriateness of contractual terms. Legal interpretation remains inherently contextual and dependent on factors beyond textual analysis, including governing law, regulatory environment, and factual circumstances.

Third, suppression logic and severity classification reflect conservative design choices intended to reduce false positives. While this improves trustworthiness, it may reduce recall for marginal or highly nuanced risk cases.

Finally, the system is currently evaluated on commercial NDAs and MSAs. While the architectural principles generalize to other document types, additional rule engineering and validation would be required to extend coverage to employment agreements, leases, or regulatory filings.

These limitations are deliberate and aligned with the system’s role as an early-stage risk visibility tool rather than a decision-making authority.

# **VII. Conclusion**

This paper presented a deterministic–LLM hybrid architecture for auditable contract risk triage that addresses fundamental limitations of LLM-only legal analysis systems. By enforcing a strict separation between deterministic risk detection and probabilistic explanation, the proposed approach eliminates hallucination at the detection layer while preserving the communicative advantages of LLM-generated summaries.

Key contributions include a versioned deterministic rule engine, clause-level anchoring for traceability, constrained LLM interaction, and reproducible output guarantees. Together, these components form a practical neural-symbolic blueprint for deploying LLMs safely in legally sensitive workflows.

While implemented in the context of commercial NDAs and MSAs, the architectural principles described in this work are broadly applicable to other high-risk document analysis domains. Future work may explore expanded rule coverage, domain adaptation, and formal user studies measuring trust and review efficiency.

The system demonstrates that LLMs can be integrated into legal workflows responsibly—provided they are constrained, auditable, and positioned as explanatory tools rather than autonomous decision-makers.