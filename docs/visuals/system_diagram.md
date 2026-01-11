# System Diagram

## High-Level Architecture

```mermaid
graph TB
    A[User Uploads Contract] --> B[Text Extraction]
    B --> C[Deterministic Rule Engine]
    C --> D[Findings + Risk Level]
    D --> E{Findings Exist?}
    E -->|Yes| F[LLM Evaluator]
    E -->|No| G[Fallback Response]
    F --> H[Results Synthesis]
    G --> H
    H --> I[Results Page]
    
    style C fill:#e1f5ff
    style F fill:#fff4e1
    style D fill:#e8f5e9
```

## Component Details

### Text Extraction
- PDF: PyPDF2
- DOCX: python-docx
- TXT: UTF-8 decode

### Deterministic Rule Engine
- Pattern-based rules
- Proximity-based rules
- Deduplication
- Severity aggregation

### LLM Evaluator
- Receives findings only
- Generates explanations
- Validates output
- Fallback on failure

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant M as Main App
    participant R as Rule Engine
    participant L as LLM Evaluator
    participant S as Results
    
    U->>M: Upload contract
    M->>M: Extract text
    M->>R: Analyze text
    R->>R: Apply rules
    R->>M: Return findings
    M->>L: Evaluate findings
    L->>L: Generate explanations
    L->>M: Return explanations
    M->>S: Synthesize results
    S->>U: Display results
```

## Boundary Enforcement

```mermaid
graph LR
    A[Contract Text] --> B[Rule Engine]
    B --> C[Findings Only]
    C --> D[LLM]
    D --> E[Explanations]
    
    F[Full Contract] -.->|NEVER SENT| D
    
    style C fill:#e8f5e9
    style F fill:#ffebee
```
