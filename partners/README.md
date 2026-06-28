# Partner Prospecting Tools

Find and recruit commission partners for Triage AI.

## Files

- `ICP_AND_PARTNER_STRATEGY.md` — Full ICP definition, partner profiles, commission structure, and outreach playbook
- `linkedin_prospector.py` — Script to find partner leads via Apollo.io API
- `output/` — Generated CSV files with leads (gitignored)

## Quick Start

```bash
# Install dependencies
pip install requests python-dotenv

# Set your Apollo.io API key
export APOLLO_API_KEY=your_key_here

# Dry run (see search criteria without API calls)
python partners/linkedin_prospector.py --dry-run

# Real run (queries Apollo.io, exports CSVs)
python partners/linkedin_prospector.py
```

## Recommended Tool Stack

| Tool | Purpose | Cost |
|---|---|---|
| Apollo.io | Find leads with emails | Free tier / $49/mo |
| LinkedIn Sales Navigator | Advanced LinkedIn search | ~$99/mo |
| Instantly.ai | Cold email sequences | ~$30/mo |
| Rewardful | Partner program management (Stripe integration) | Free–$49/mo |
