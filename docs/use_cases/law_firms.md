# Use Case: Small and Mid-Sized Law Firms

**This is the primary ICP.** See `docs/strategy/icp.md` for the full rationale. Other use-case docs (`founders.md`, `freelancers.md`, `enterprise_review.md`) describe supported but secondary audiences.

## Target User

Attorneys and paralegals at solo practices and small/mid-sized firms (roughly solo up through a few dozen attorneys) who handle a steady volume of client contracts — NDAs, MSAs, vendor agreements, employment agreements — without the headcount or budget for a dedicated first-pass review function.

## The Problem

Small and mid-sized firms sit in an awkward middle:
- **No spare associate capacity**: Every contract review competes with billable client work; there's no junior-associate pool to absorb first-pass triage the way a large firm has.
- **Client price sensitivity**: Clients (especially startup and SMB clients) push back on paying attorney rates for a first read of a boilerplate NDA or vendor MSA.
- **Consistency across attorneys**: A 5-15 attorney firm needs contracts reviewed the same way regardless of which attorney picks it up — hard to guarantee with ad hoc review.
- **Malpractice exposure is personal**: Unlike an in-house team, a missed risk at a small firm is a professional liability and reputational issue for the specific attorney of record, not an abstract compliance gap.

## How This Tool Helps

### 1. First-Pass Triage Before Billable Review

**Before**: Attorney reads the full contract cold, or delegates to an associate at full billable rate, just to find out what actually needs attention.

**After**: Upload the contract, get a ruleset-versioned, clause-anchored risk report in seconds, then spend billable time only on what's flagged.

### 2. Firm-Standard Playbooks

The Playbook feature lets a firm encode its own standard positions (e.g., acceptable liability caps, required indemnification carve-outs) once, then compare every incoming contract against that standard automatically — so review quality doesn't depend on which attorney is handling a given matter.

### 3. Volume Without Adding Headcount

Batch upload (Team plan — up to 50 files) and per-plan monthly review caps (`templates/pricing.html`) are sized around a small/mid firm's actual contract volume: enough to cover a busy transactional or employment practice without enterprise-scale pricing.

### 4. Client-Ready, Defensible Output

Every finding is anchored to an exact clause, ruleset version, and evidence snippet (`docs/architecture/FUTURE_ROADMAP.md`, "Legal Defensibility"). That reproducibility matters specifically to a small firm attorney who may need to show *why* a contract was flagged (or wasn't) months later — the professional-liability angle that a generic enterprise compliance tool doesn't need to optimize for.

## Example Workflow

### Scenario: Small Firm Handling Multiple Client NDAs

1. **Upload**: Associate uploads an incoming NDA from a client's counterparty.
2. **Playbook comparison**: Tool compares it against the firm's standard NDA playbook.
3. **Findings**: Two deviations flagged — indefinite confidentiality term, one-sided assignment restriction — each with clause-level evidence and severity.
4. **Decision**: Associate handles the routine deviation directly; escalates the higher-severity one to the supervising partner with the report attached.
5. **Client deliverable**: Firm generates a client-ready PDF summary instead of a billed memo for a low-risk review.

## What Firms Should Know

### What the Tool Does
- Deterministic, versioned first-pass risk detection across NDAs, MSAs, vendor, and employment agreements
- Firm-specific playbook comparison
- Batch handling for deal rooms or high-volume periods
- Auditable, reproducible output suitable for the firm's own file

### What the Tool Does NOT Do
- Replace attorney judgment or sign-off
- Provide legal advice to the firm's clients
- Handle complex bespoke M&A or heavily negotiated custom terms (see `docs/use_cases/enterprise_review.md` for where the tool's coverage tapers off)
- Guarantee contract enforceability

## Best Practices for Firms

1. **Standardize with playbooks first** — the tool's value compounds once a firm's own positions are encoded, not just out-of-the-box rule coverage.
2. **Use it as triage, not the final word** — route flagged contracts to attorney review; use low-risk findings to skip unnecessary billable time, not to skip attorney sign-off entirely.
3. **Keep the report on file** — the clause-anchored, versioned output is useful contemporaneous documentation of what was reviewed and why.
