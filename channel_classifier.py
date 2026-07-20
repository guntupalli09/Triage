"""
Acquisition channel classification.

Turns a (referring domain, UTM params, ad click IDs) triple into one of a
fixed set of human-readable acquisition channels. This is intentionally a
pure function over plain strings — no I/O, no DB — so it's trivial to unit
test and to re-run retroactively if the classification rules improve.

`acquisition_channel` is stored as a plain VARCHAR (not a Postgres ENUM)
specifically so new channels can be added here without a migration.
"""
from __future__ import annotations

import re
from typing import Mapping, Optional
from urllib.parse import urlparse

# The set the product spec asked for, plus two additions (Bing Ads, TikTok)
# that are only reachable via their own dedicated click-ID params (msclkid,
# ttclid) — those columns are captured but had no home in the base list.
CHANNELS = (
    "Direct", "Google Organic", "Google Ads", "Bing Organic", "Bing Ads",
    "LinkedIn Organic", "LinkedIn Ads", "Twitter/X", "TikTok", "Facebook",
    "Instagram", "Reddit", "Discord", "Slack", "GitHub", "Product Hunt",
    "Hacker News", "Email", "Referral", "Unknown",
)

_PAID_MEDIUMS = {"cpc", "ppc", "paid", "paidsearch", "paid-search", "paidsocial", "paid-social", "display", "ads"}

# (regex over the utm_source value, channel-if-organic, channel-if-paid)
_UTM_SOURCE_RULES: tuple[tuple[re.Pattern, str, str], ...] = (
    (re.compile(r"^google$", re.I), "Google Organic", "Google Ads"),
    (re.compile(r"^bing$", re.I), "Bing Organic", "Bing Ads"),
    (re.compile(r"^linkedin$", re.I), "LinkedIn Organic", "LinkedIn Ads"),
    (re.compile(r"^(twitter|x)$", re.I), "Twitter/X", "Twitter/X"),
    (re.compile(r"^tiktok$", re.I), "TikTok", "TikTok"),
    (re.compile(r"^(facebook|fb)$", re.I), "Facebook", "Facebook"),
    (re.compile(r"^instagram$", re.I), "Instagram", "Instagram"),
    (re.compile(r"^reddit$", re.I), "Reddit", "Reddit"),
    (re.compile(r"^discord$", re.I), "Discord", "Discord"),
    (re.compile(r"^slack$", re.I), "Slack", "Slack"),
    (re.compile(r"^github$", re.I), "GitHub", "GitHub"),
    (re.compile(r"^product ?hunt$", re.I), "Product Hunt", "Product Hunt"),
    (re.compile(r"^(hn|hacker ?news)$", re.I), "Hacker News", "Hacker News"),
)

# (substring found in the referring domain) -> channel
_DOMAIN_RULES: tuple[tuple[str, str], ...] = (
    ("google.", "Google Organic"),
    ("bing.", "Bing Organic"),
    ("linkedin.com", "LinkedIn Organic"),
    ("lnkd.in", "LinkedIn Organic"),
    ("t.co", "Twitter/X"),
    ("twitter.com", "Twitter/X"),
    ("x.com", "Twitter/X"),
    ("tiktok.com", "TikTok"),
    ("facebook.com", "Facebook"),
    ("fb.com", "Facebook"),
    ("instagram.com", "Instagram"),
    ("reddit.com", "Reddit"),
    ("discord.com", "Discord"),
    ("discord.gg", "Discord"),
    ("slack.com", "Slack"),
    ("github.com", "GitHub"),
    ("producthunt.com", "Product Hunt"),
    ("news.ycombinator.com", "Hacker News"),
)

_CLICK_ID_RULES: tuple[tuple[str, str], ...] = (
    ("gclid", "Google Ads"),
    ("msclkid", "Bing Ads"),
    ("li_fat_id", "LinkedIn Ads"),
    ("ttclid", "TikTok"),
    ("fbclid", "Facebook"),
)


def _extract_domain(referring_domain: Optional[str]) -> str:
    if not referring_domain:
        return ""
    if "//" in referring_domain:
        return (urlparse(referring_domain).netloc or "").lower()
    return referring_domain.lower()


def classify_channel(
    referring_domain: Optional[str],
    utm: Optional[Mapping[str, Optional[str]]] = None,
    click_ids: Optional[Mapping[str, Optional[str]]] = None,
) -> str:
    """Classify traffic into one of the CHANNELS values. Never raises."""
    try:
        utm = utm or {}
        click_ids = click_ids or {}

        utm_source = (utm.get("utm_source") or "").strip()
        utm_medium = (utm.get("utm_medium") or "").strip().lower()
        domain = _extract_domain(referring_domain)
        is_paid = utm_medium in _PAID_MEDIUMS or bool(click_ids.get("gclid") or click_ids.get("msclkid") or click_ids.get("li_fat_id"))

        if utm_medium == "email":
            return "Email"

        # Click IDs are the strongest paid-traffic signal — they can only be
        # present because an ad network appended them to the landing URL.
        for param, channel in _CLICK_ID_RULES:
            if click_ids.get(param):
                return channel

        if utm_source:
            for pattern, organic_channel, paid_channel in _UTM_SOURCE_RULES:
                if pattern.match(utm_source):
                    return paid_channel if is_paid else organic_channel
            # Unrecognized utm_source but present — treat as a named referral.
            return "Referral"

        if not domain:
            return "Direct"

        for substring, channel in _DOMAIN_RULES:
            if substring in domain:
                return channel

        return "Referral"
    except Exception:
        return "Unknown"
