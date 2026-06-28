"""
LinkedIn Partner Prospector for Triage AI

Uses Apollo.io API to find potential commission partners who can refer
clients to Triage AI. Apollo.io is a compliant B2B data provider —
no LinkedIn scraping involved.

Setup:
    1. Sign up at apollo.io (free tier: 10,000 credits/month)
    2. Get your API key from Settings > Integrations > API
    3. Set APOLLO_API_KEY environment variable
    4. pip install requests python-dotenv
    5. python linkedin_prospector.py

Output:
    - CSV file with partner leads (name, title, company, LinkedIn URL, email)
    - Console summary of leads found per segment
"""

import csv
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
APOLLO_BASE_URL = "https://api.apollo.io/v1"

COMMISSION_RATE = 0.25
UNLIMITED_YEARLY_PRICE = 249 * 12  # $2,988
COMMISSION_PER_REFERRAL = UNLIMITED_YEARLY_PRICE * COMMISSION_RATE  # $747


@dataclass
class PartnerSegment:
    name: str
    titles: list[str]
    industries: list[str] = field(default_factory=list)
    employee_ranges: list[str] = field(default_factory=lambda: ["1,10"])
    locations: list[str] = field(default_factory=lambda: ["United States"])
    seniority: list[str] = field(default_factory=list)
    reason: str = ""


SEGMENTS = [
    PartnerSegment(
        name="Fractional GCs & Legal Consultants",
        titles=[
            "Fractional General Counsel",
            "Legal Consultant",
            "Contract Advisor",
            "Fractional CLO",
            "Outside General Counsel",
        ],
        industries=["legal services", "law practice", "business consulting"],
        employee_ranges=["1,10", "11,20"],
        reason="They advise multiple startups/SMBs on legal ops. Each serves 5-15 clients.",
    ),
    PartnerSegment(
        name="Startup Advisors & Fractional COOs",
        titles=[
            "Fractional COO",
            "Startup Advisor",
            "Operations Consultant",
            "Fractional CTO",
            "Startup Consultant",
        ],
        industries=["information technology and services", "management consulting"],
        employee_ranges=["1,10", "11,50"],
        reason="Help startups build operational processes including contract review.",
    ),
    PartnerSegment(
        name="Legal Tech Influencers",
        titles=[
            "Legal Tech",
            "LegalOps",
            "Legal Innovation",
            "Legal Technology Director",
            "Head of Legal Operations",
        ],
        seniority=["director", "vp", "c_suite"],
        reason="One post from these people = many inbound leads.",
    ),
    PartnerSegment(
        name="Accelerator & Incubator Leaders",
        titles=[
            "Accelerator Manager",
            "Incubator Director",
            "Portfolio Manager",
            "Entrepreneur in Residence",
            "Program Director",
        ],
        industries=["venture capital & private equity", "startup"],
        reason="Can recommend Triage to entire portfolios (20-50 startups per cohort).",
    ),
    PartnerSegment(
        name="M&A Advisors & Business Brokers",
        titles=[
            "Business Broker",
            "M&A Advisor",
            "Deal Advisory",
            "Transaction Advisory",
            "Due Diligence Manager",
        ],
        industries=["financial services", "investment banking"],
        reason="Every deal involves a data room full of contracts.",
    ),
    PartnerSegment(
        name="Procurement Consultants",
        titles=[
            "Procurement Consultant",
            "Supply Chain Advisor",
            "Vendor Management Consultant",
            "Strategic Sourcing Consultant",
        ],
        industries=["management consulting", "business consulting"],
        reason="Help companies set up vendor onboarding — contract triage is part of that.",
    ),
    PartnerSegment(
        name="Fractional CFOs & Accountants",
        titles=[
            "Fractional CFO",
            "CFO Services",
            "Virtual CFO",
            "CPA",
            "Financial Advisor for Startups",
        ],
        industries=["accounting", "financial services"],
        employee_ranges=["1,10", "11,20"],
        reason="They see every contract their clients sign for financial terms.",
    ),
]


def search_apollo(segment: PartnerSegment, page: int = 1, per_page: int = 25) -> dict:
    """Search Apollo.io for people matching the segment criteria."""
    if not APOLLO_API_KEY:
        return {"error": "APOLLO_API_KEY not set"}

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }

    payload = {
        "api_key": APOLLO_API_KEY,
        "q_person_title": " OR ".join(segment.titles),
        "page": page,
        "per_page": per_page,
    }

    if segment.locations:
        payload["person_locations"] = segment.locations

    if segment.seniority:
        payload["person_seniorities"] = segment.seniority

    if segment.industries:
        payload["q_organization_industry_tag_ids"] = segment.industries

    try:
        resp = requests.post(
            f"{APOLLO_BASE_URL}/mixed_people/search",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def extract_leads(api_response: dict) -> list[dict]:
    """Extract clean lead data from Apollo API response."""
    leads = []
    people = api_response.get("people", [])

    for person in people:
        lead = {
            "name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
            "first_name": person.get("first_name", ""),
            "last_name": person.get("last_name", ""),
            "title": person.get("title", ""),
            "company": person.get("organization", {}).get("name", "") if person.get("organization") else "",
            "linkedin_url": person.get("linkedin_url", ""),
            "email": person.get("email", ""),
            "city": person.get("city", ""),
            "state": person.get("state", ""),
            "country": person.get("country", ""),
            "company_size": person.get("organization", {}).get("estimated_num_employees", "") if person.get("organization") else "",
            "company_industry": person.get("organization", {}).get("industry", "") if person.get("organization") else "",
        }
        leads.append(lead)

    return leads


def run_prospector(dry_run: bool = False) -> dict[str, list[dict]]:
    """Run the prospector across all segments."""
    all_leads: dict[str, list[dict]] = {}
    total = 0

    print("=" * 60)
    print("  Triage AI — LinkedIn Partner Prospector")
    print(f"  Commission: 25% of ${UNLIMITED_YEARLY_PRICE:,}/yr = ${COMMISSION_PER_REFERRAL:,.0f}/referral")
    print("=" * 60)

    if dry_run or not APOLLO_API_KEY:
        if not APOLLO_API_KEY:
            print("\n  [DRY RUN] APOLLO_API_KEY not set — showing search criteria only\n")
        else:
            print("\n  [DRY RUN] Showing search criteria without making API calls\n")

        for segment in SEGMENTS:
            print(f"\n--- {segment.name} ---")
            print(f"  Titles: {', '.join(segment.titles)}")
            print(f"  Industries: {', '.join(segment.industries) if segment.industries else 'Any'}")
            print(f"  Company size: {', '.join(segment.employee_ranges)}")
            print(f"  Locations: {', '.join(segment.locations)}")
            print(f"  Seniority: {', '.join(segment.seniority) if segment.seniority else 'Any'}")
            print(f"  Why: {segment.reason}")
            all_leads[segment.name] = []

        print("\n" + "=" * 60)
        print("  To run for real: set APOLLO_API_KEY and run without --dry-run")
        print("  Sign up free: https://app.apollo.io/")
        print("=" * 60)
        return all_leads

    for segment in SEGMENTS:
        print(f"\nSearching: {segment.name}...")
        result = search_apollo(segment)

        if "error" in result:
            print(f"  Error: {result['error']}")
            all_leads[segment.name] = []
            continue

        leads = extract_leads(result)
        all_leads[segment.name] = leads
        total += len(leads)
        pagination = result.get("pagination", {})
        total_available = pagination.get("total_entries", len(leads))

        print(f"  Found {len(leads)} leads (of {total_available} total available)")
        print(f"  Reason: {segment.reason}")

        time.sleep(1)

    print(f"\n{'=' * 60}")
    print(f"  Total leads found: {total}")
    print(f"  Potential commission value: ${total * COMMISSION_PER_REFERRAL:,.0f}/year")
    print(f"  (if each partner refers just 1 client)")
    print(f"{'=' * 60}")

    return all_leads


def export_csv(all_leads: dict[str, list[dict]], output_dir: str = "partners/output"):
    """Export leads to CSV files."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    all_rows = []
    for segment_name, leads in all_leads.items():
        for lead in leads:
            lead["segment"] = segment_name
            all_rows.append(lead)

    if not all_rows:
        print("No leads to export.")
        return

    filename = f"{output_dir}/partner_leads_{timestamp}.csv"
    fieldnames = [
        "segment", "name", "first_name", "last_name", "title",
        "company", "linkedin_url", "email", "city", "state",
        "country", "company_size", "company_industry",
    ]

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nExported {len(all_rows)} leads to {filename}")


def export_outreach_csv(all_leads: dict[str, list[dict]], output_dir: str = "partners/output"):
    """Export a mail-merge-ready CSV for cold outreach."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    rows = []
    for segment_name, leads in all_leads.items():
        for lead in leads:
            if not lead.get("email"):
                continue
            rows.append({
                "email": lead["email"],
                "first_name": lead["first_name"],
                "last_name": lead["last_name"],
                "title": lead["title"],
                "company": lead["company"],
                "linkedin_url": lead["linkedin_url"],
                "segment": segment_name,
                "commission_value": f"${COMMISSION_PER_REFERRAL:,.0f}/year per referral",
            })

    if not rows:
        print("No leads with emails to export for outreach.")
        return

    filename = f"{output_dir}/outreach_ready_{timestamp}.csv"
    fieldnames = list(rows[0].keys())

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} outreach-ready leads to {filename}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or not APOLLO_API_KEY

    leads = run_prospector(dry_run=dry_run)

    if not dry_run:
        export_csv(leads)
        export_outreach_csv(leads)
