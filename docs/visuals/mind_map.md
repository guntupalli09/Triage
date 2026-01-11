# System Mind Map

## Core Concepts

```
Contract Risk Triage Tool
│
├── Architecture
│   ├── Neural-Symbolic Design
│   │   ├── Symbolic Layer (Deterministic)
│   │   └── Neural Layer (Bounded)
│   ├── Hard Boundaries
│   │   ├── No Contract Text to LLM
│   │   ├── Zero Findings Check
│   │   └── Output Validation
│   └── Fail-Safe Design
│       ├── Fallback Mechanisms
│       └── Graceful Degradation
│
├── Rule Engine
│   ├── Detection Methods
│   │   ├── Pattern-Based
│   │   └── Proximity-Based
│   ├── Rule Categories
│   │   ├── HIGH Risk
│   │   ├── MEDIUM Risk
│   │   └── LOW Risk
│   ├── Features
│   │   ├── Clause Number Detection
│   │   ├── Keyword Extraction
│   │   ├── Deduplication
│   │   └── Versioning
│   └── Guarantees
│       ├── Determinism
│       ├── Auditability
│       └── Consistency
│
├── LLM Layer
│   ├── Role
│   │   ├── Explains Findings
│   │   ├── Generates Summaries
│   │   └── Suggests Missing Sections
│   ├── Constraints
│   │   ├── No Contract Text
│   │   ├── No Risk Detection
│   │   └── Conservative Language
│   ├── Safety
│   │   ├── Output Validation
│   │   ├── Fallback Available
│   │   └── Hallucination Prevention
│   └── Cost Control
│       ├── Token Optimization
│       ├── Model Selection
│       └── Caching (Future)
│
├── Use Cases
│   ├── Founders
│   │   ├── Quick Triage
│   │   ├── Risk Prioritization
│   │   └── Cost Savings
│   ├── Freelancers
│   │   ├── Affordable Assessment
│   │   └── Negotiation Guidance
│   └── Enterprise
│       ├── First-Pass Triage
│       ├── Standardized Screening
│       └── Workflow Integration
│
├── Compliance
│   ├── Legal
│   │   ├── No Legal Advice
│   │   ├── Conservative Language
│   │   └── Explicit Disclaimers
│   ├── Privacy
│   │   ├── Minimal Data Collection
│   │   ├── Ephemeral Storage
│   │   └── No Third-Party Sharing
│   ├── Security
│   │   ├── Input Validation
│   │   ├── Session Security
│   │   └── API Security
│   └── Auditability
│       ├── Rule Versioning
│       ├── Finding Traceability
│       └── Full Transparency
│
└── Technical Contribution
    ├── Innovation
    │   ├── Neural-Symbolic Architecture
    │   ├── Hallucination Prevention
    │   └── Deterministic Guarantees
    ├── Comparison
    │   ├── vs. Pure LLM Systems
    │   ├── vs. AI Wrappers
    │   └── vs. Symbolic Systems
    └── Impact
        ├── Legal-Tech Industry
        ├── Regulatory Compliance
        └── Enterprise Adoption
```

## Key Relationships

- **Architecture → Rule Engine**: Deterministic detection
- **Architecture → LLM Layer**: Bounded explanation
- **Rule Engine → Compliance**: Auditability
- **LLM Layer → Compliance**: Safety guarantees
- **Use Cases → Compliance**: Legal safety
- **Technical Contribution → All**: Original innovation
