"""Canonical production subprocessor register for public and compliance pages."""
from __future__ import annotations

from typing import List, TypedDict


class Subprocessor(TypedDict):
    name: str
    purpose: str
    location: str
    data_categories: str


# Single source of truth — the public /security/subprocessors table loops over this list.
SUBPROCESSORS: List[Subprocessor] = [
    {
        "name": "Hetzner Online GmbH",
        "purpose": "Infrastructure hosting for the production application and stored customer data",
        "location": "Germany (European Union)",
        "data_categories": (
            "Account information; extracted contract text; analysis results and related "
            "customer content stored to provide the service"
        ),
    },
    {
        "name": "OpenAI, L.L.C.",
        "purpose": (
            "AI-assisted contract analysis, including plain-language explanations and, where enabled, "
            "evidence discovery or playbook-related extraction requested by the customer"
        ),
        "location": "United States and other locations used by OpenAI for API processing (see OpenAI documentation)",
        "data_categories": (
            "Contract content and analysis context as required by the features enabled for the account "
            "or action — which may range from short excerpts to broader passages or full document text "
            "depending on configuration and use"
        ),
    },
    {
        "name": "Stripe, Inc.",
        "purpose": "Payment processing and subscription management",
        "location": "United States and other locations used by Stripe (see Stripe documentation)",
        "data_categories": (
            "Billing contact details and subscription metadata. Payment card details are collected "
            "directly by Stripe; TriageCounsel does not store card numbers"
        ),
    },
    {
        "name": "Google LLC",
        "purpose": "Optional user authentication (Google sign-in), when enabled",
        "location": "United States and other locations used by Google (see Google documentation)",
        "data_categories": "Name, email address, and authentication identifiers. No contract content",
    },
    {
        "name": "SMTP email provider",
        "purpose": "Transactional email delivery via SMTP (password reset and account notifications)",
        "location": "United States and other locations used by the configured SMTP host",
        "data_categories": (
            "Recipient email address and content required to deliver the notification. No contract content"
        ),
    },
]
