# Rule Categories

Rules are organized by severity level: HIGH, MEDIUM, and LOW. Each category represents different levels of potential risk exposure.

## HIGH Risk Rules

High-risk rules detect clauses that may create **material financial or legal exposure**.

### H_INDEM_01: Unlimited Indemnification

**What it detects**: Indemnification obligations without caps or limits.

**Pattern**: Indemnification language combined with "unlimited", "without limit", "no limit", or language that carves out limitation of liability.

**Why it matters**: Uncapped indemnification can expose companies to costs far exceeding contract value.

**Example matches**:
- "Party shall indemnify without limit..."
- "Indemnification obligations notwithstanding any limitation of liability..."

### H_INDEM_ONEWAY_01: One-Way Indemnification

**What it detects**: Indemnification obligations that apply to only one party.

**Pattern**: Indemnification language where only receiving party or only disclosing party has obligations.

**Why it matters**: Even capped indemnity is dangerous if one-sided, creating asymmetric risk.

**Example matches**:
- "Receiving party shall indemnify disclosing party..."
- "Shall indemnify disclosing party against all claims..."

### H_LOL_01: Liability Uncapped or Weakened

**What it detects**: Missing or weakened liability caps.

**Pattern**: Limitation of liability language that excludes key categories or has no cap.

**Why it matters**: If liability is not capped, downside risk can exceed expected exposure.

**Example matches**:
- "No event shall be limited by limitation of liability..."
- "Liability shall not be limited for..."

### H_IP_01: Broad IP Assignment

**What it detects**: Language that assigns all rights, title, and interest in IP.

**Pattern**: Assignment or transfer language combined with "all rights, title, and interest".

**Why it matters**: May transfer ownership of work product rather than granting limited license.

**Example matches**:
- "Assigns all right, title, and interest..."
- "Transfers all rights in intellectual property..."

### H_IP_WORK_PRODUCT_01: IP Ownership via Work Product

**What it detects**: Work product or deliverables language that transfers ownership.

**Pattern**: "Work product" or "deliverables" combined with "owned by" or "shall be the property of".

**Why it matters**: Work product ownership language can effectively transfer IP even if assignment wording is indirect.

**Example matches**:
- "Work product shall be owned by..."
- "Deliverables shall be the property of..."

### H_PERSONAL_01: Personal Liability Exposure

**What it detects**: Language creating personal guarantees or individual responsibility.

**Pattern**: "Personally", "guarantee", or "guarantor" combined with obligation or liability language.

**Why it matters**: May create obligations extending beyond the company to individual founders.

**Example matches**:
- "You personally guarantee..."
- "Officer shall be personally liable..."

## MEDIUM Risk Rules

Medium-risk rules detect clauses that are **commonly negotiated** and may create operational or business constraints.

### M_CONF_01: Indefinite Confidentiality

**What it detects**: Confidentiality obligations that are perpetual or indefinite.

**Pattern**: Confidentiality or non-disclosure language combined with "perpetual", "indefinite", or "no expiration".

**Why it matters**: Indefinite confidentiality can create long-term compliance burden.

**Example matches**:
- "Confidentiality obligations shall survive in perpetuity..."
- "Non-disclosure obligations are indefinite..."

### M_CONF_SCOPE_01: Confidentiality Scope Overbroad

**What it detects**: Confidentiality obligations that lack standard carve-outs.

**Pattern**: Confidential language combined with "without regard to" or "regardless of" or missing public information exclusions.

**Why it matters**: May apply too broadly, including public or independently developed information.

**Example matches**:
- "Confidential information without regard to..."
- "Confidential regardless of public availability..."

### M_RENEW_01: Auto-Renewal

**What it detects**: Automatic renewal terms with notice requirements.

**Pattern**: "Auto-renewal" or "automatically renew" combined with "unless notice" or "prior written notice".

**Why it matters**: May require notice within specific window to avoid renewal.

**Example matches**:
- "Automatically renews unless terminated with 30 days notice..."
- "Auto-renewal unless prior written notice..."

### M_NONCOMP_01: Non-Compete / Non-Solicit

**What it detects**: Restrictive covenants limiting competition or solicitation.

**Pattern**: "Non-compete", "non-solicit", or restrictive language about competitors.

**Why it matters**: Can limit future business activity; enforceability varies.

**Example matches**:
- "Non-compete provision..."
- "Restricted from competing with..."

### M_DEV_RESTRICT_01: Development Restriction

**What it detects**: Restrictions on developing competing products based on confidential information.

**Pattern**: "Not to develop" or "shall not develop" combined with "compete" or "substantially similar" and "based on" or "derived from".

**Why it matters**: Can limit future work even when tied to confidential information.

**Example matches**:
- "Not to develop products that compete with those based on confidential information..."
- "Shall not develop substantially similar products derived from..."

### M_RESIDUALS_01: No Residuals Clause

**What it detects**: Absence of residuals/knowledge carve-out.

**Pattern**: "Shall not use" combined with "knowledge" and "retained".

**Why it matters**: May restrict use of general knowledge gained during discussions.

**Example matches**:
- "Shall not use knowledge retained in memory..."
- "Prohibited from using retained general knowledge..."

### M_INJUNCT_01: Broad Injunctive Relief

**What it detects**: Broad injunctive or equitable relief language.

**Pattern**: "Injunctive relief" or "equitable relief".

**Why it matters**: Can bypass standard dispute resolution safeguards.

**Example matches**:
- "Injunctive relief available..."
- "Equitable relief without limitation..."

## LOW Risk Rules

Low-risk rules detect clauses that are **minor concerns** or provide **contextual information**.

### L_LATEFEE_01: Late Fees / High Interest

**What it detects**: Penalty terms with high rates.

**Pattern**: "Late fee" or "interest" combined with percentage (≥10%).

**Why it matters**: Penalty terms can increase costs if payment timing slips.

**Example matches**:
- "Late fee of 15%..."
- "Interest rate of 18% per annum..."

### L_BROADDEF_01: Broad Definitions

**What it detects**: Overly broad defined terms.

**Pattern**: "Means" or "defined as" combined with "including" or "without limitation".

**Why it matters**: Can expand confidentiality or scope beyond expectations.

**Example matches**:
- "Confidential information means, including without limitation..."
- "Defined as including all information..."

### L_GOVLAW_01: Governing Law / Venue

**What it detects**: Specific governing law or exclusive jurisdiction clauses.

**Pattern**: "Governed by" with "laws" or "exclusive jurisdiction".

**Why it matters**: Can affect enforcement cost and strategy.

**Example matches**:
- "Governed by the laws of California..."
- "Exclusive jurisdiction in New York courts..."

## Severity Logic

Overall risk level is determined by:
- **HIGH**: Any HIGH severity finding → overall = HIGH
- **MEDIUM**: ≥2 MEDIUM findings → overall = MEDIUM
- **LOW**: Otherwise → overall = LOW

This conservative approach ensures high-risk contracts are always flagged.
