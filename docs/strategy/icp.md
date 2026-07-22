# Ideal Customer Profile (ICP)

**Status**: Locked
**Decided**: 2026-07-22
**Owner**: Santhosh Guntupalli

## The ICP

**Small and mid-sized law firms** — roughly solo practitioners up through firms in the tens of attorneys, without an in-house tooling/IT budget or a dedicated legal ops function.

This is the primary segment the product, pricing, messaging, and roadmap are built around going forward. It is a lock, not a preference: features, copy, and prioritization calls should default to "does this serve a small/mid-sized law firm workflow?" rather than trying to serve every adjacent buyer equally.

## Why this segment

- **Volume without headcount**: These firms review a steady stream of NDAs, MSAs, vendor and employment agreements but can't staff a first-pass triage function the way a large firm or in-house team can.
- **Price-sensitive but not price-only**: $9–$199/month plans (see `templates/pricing.html`) are real budget for a solo/small firm, unlike enterprise legal, where a tool this size reads as a rounding error and enterprise procurement/security review dominates the sales cycle instead.
- **Malpractice-aware, not compliance-aware**: Small/mid firms care about auditability and reproducibility (see `docs/architecture/FUTURE_ROADMAP.md`, "Legal Defensibility") because a wrong call is a malpractice/reputation risk to *them personally*, not an abstract compliance checkbox — that maps directly onto TriageCounsel's deterministic, rule-anchored architecture.
- **Referral-driven distribution**: The existing Referral Partner Program (`templates/partners.html`) already lists "Law Firms," "Solo Attorneys," and "Fractional General Counsel" as eligible partners — this ICP formalizes what was already the de facto go-to-market motion.
- **Product fit**: Playbook comparison, batch upload, and client-ready PDF reports (Professional/Team tiers) map directly onto how a small/mid firm actually works — one attorney handling many similar contracts against a standard set of firm playbooks.

## What this explicitly deprioritizes

- **Solo founders/freelancers reviewing their own contracts** (`docs/use_cases/founders.md`, `freelancers.md`) remain supported as secondary/adjacent use cases — the tool still works for them — but copy, feature requests, and roadmap tradeoffs should not be optimized around them at the expense of the law firm ICP.
- **Enterprise / large-firm legal ops**, which needs SSO, custom procurement, and integration work this product does not currently offer, and whose review needs (complex M&A, heavily negotiated bespoke terms) sit outside the deterministic rule engine's sweet spot per `docs/use_cases/enterprise_review.md`.
- **Consumer-facing use cases** (reviewing a lease, a ToS, etc.) — out of scope entirely.

## What "locked" changes in practice

1. **Messaging**: Marketing surfaces (README, home/pricing/about/FAQ pages) should name "small and mid-sized law firms" as the primary audience rather than the previous generic "founders, executives, and legal teams" framing.
2. **Roadmap prioritization**: When two roadmap items are otherwise similar in cost/value, prefer the one that serves a small/mid law firm's actual workflow (multi-client playbooks, batch/volume handling, client-ready reporting, audit trail for malpractice defensibility) over generic breadth (e.g., new contract-type coverage aimed at consumer/marketplace terms).
3. **New use-case doc**: `docs/use_cases/law_firms.md` is now the primary use-case document; `founders.md` and `freelancers.md` stay as secondary references.

## Revisiting this lock

This is a business decision, not an architectural constraint — nothing about the deterministic rule engine prevents serving other segments later. If this ICP is revisited, update this file and the roadmap prioritization note in `docs/architecture/FUTURE_ROADMAP.md` in the same change so they don't drift out of sync.
