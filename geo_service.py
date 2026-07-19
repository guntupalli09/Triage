"""
IP geolocation service.

Single place where an IP address is turned into country/region/city/
timezone/lat-long/ISP/ASN facts. Tries progressively more expensive
sources and stops at the first one that returns a country:

    1. Cloudflare geo headers            (free, instant, zero network cost)
    2. Reverse-proxy / nginx geo headers (free, instant, zero network cost)
    3. MaxMind GeoLite2 local database    (fast, local, no network — optional)
    4. ip-api.com HTTP fallback          (network call, short timeout, best-effort)

Design constraint from the product spec: geolocation must **never** block
or fail a signup. Every public function here catches its own exceptions
and degrades to an empty result instead of raising.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Mapping, Optional

logger = logging.getLogger(__name__)

GEOIP_CITY_DB_PATH = os.getenv("GEOIP_CITY_DB_PATH", "").strip()
GEOIP_ASN_DB_PATH = os.getenv("GEOIP_ASN_DB_PATH", "").strip()
IP_API_ENABLED = os.getenv("IP_API_FALLBACK_ENABLED", "true").strip().lower() == "true"
IP_API_TIMEOUT_SECONDS = float(os.getenv("IP_API_TIMEOUT_SECONDS", "1.0"))

_IP_API_CACHE_TTL = 3600  # seconds
_IP_API_CACHE_MAX = 5000
_ip_api_cache: dict[str, tuple[float, "GeoResult"]] = {}


@dataclass(frozen=True)
class GeoResult:
    country: Optional[str] = None       # ISO 3166-1 alpha-2
    region: Optional[str] = None
    city: Optional[str] = None
    timezone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    isp: Optional[str] = None
    asn: Optional[str] = None
    source: str = "none"


_EMPTY = GeoResult()


def _is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast)
    except ValueError:
        return False


def _from_cloudflare(headers: Mapping[str, str]) -> Optional[GeoResult]:
    country = headers.get("cf-ipcountry")
    if not country or country in ("XX", "T1"):  # CF uses XX=unknown, T1=Tor
        return None
    try:
        lat = float(headers["cf-iplatitude"]) if headers.get("cf-iplatitude") else None
        lon = float(headers["cf-iplongitude"]) if headers.get("cf-iplongitude") else None
    except (TypeError, ValueError):
        lat = lon = None
    return GeoResult(
        country=country.upper(),
        region=headers.get("cf-region") or None,
        city=headers.get("cf-ipcity") or None,
        timezone=headers.get("cf-timezone") or None,
        latitude=lat,
        longitude=lon,
        isp=None,
        asn=None,
        source="cloudflare",
    )


def _from_proxy_headers(headers: Mapping[str, str]) -> Optional[GeoResult]:
    """Common reverse-proxy geo header conventions (nginx geoip2 module,
    GCP App Engine, generic edge proxies)."""
    country = (
        headers.get("x-geo-country")
        or headers.get("x-appengine-country")
        or headers.get("x-geoip-country")
    )
    if not country:
        return None
    return GeoResult(
        country=country.upper(),
        region=headers.get("x-geo-region") or headers.get("x-appengine-region") or None,
        city=headers.get("x-geo-city") or headers.get("x-appengine-city") or None,
        timezone=headers.get("x-geo-timezone") or None,
        latitude=None,
        longitude=None,
        isp=None,
        asn=None,
        source="proxy_headers",
    )


_geoip_city_reader = None
_geoip_asn_reader = None
_geoip_load_attempted = False


def _load_geoip_readers() -> None:
    global _geoip_city_reader, _geoip_asn_reader, _geoip_load_attempted
    if _geoip_load_attempted:
        return
    _geoip_load_attempted = True
    if not GEOIP_CITY_DB_PATH and not GEOIP_ASN_DB_PATH:
        return
    try:
        import geoip2.database
    except ImportError:
        logger.info("geoip2 package not installed — MaxMind lookups disabled")
        return
    try:
        if GEOIP_CITY_DB_PATH and os.path.exists(GEOIP_CITY_DB_PATH):
            _geoip_city_reader = geoip2.database.Reader(GEOIP_CITY_DB_PATH)
        if GEOIP_ASN_DB_PATH and os.path.exists(GEOIP_ASN_DB_PATH):
            _geoip_asn_reader = geoip2.database.Reader(GEOIP_ASN_DB_PATH)
    except Exception:
        logger.exception("Failed to open MaxMind GeoLite2 database")


def _from_maxmind(ip: str) -> Optional[GeoResult]:
    _load_geoip_readers()
    if _geoip_city_reader is None:
        return None
    try:
        city_resp = _geoip_city_reader.city(ip)
    except Exception:
        return None

    asn_value = None
    if _geoip_asn_reader is not None:
        try:
            asn_resp = _geoip_asn_reader.asn(ip)
            if asn_resp.autonomous_system_number:
                asn_value = f"AS{asn_resp.autonomous_system_number}"
        except Exception:
            pass

    return GeoResult(
        country=city_resp.country.iso_code,
        region=city_resp.subdivisions.most_specific.name if city_resp.subdivisions else None,
        city=city_resp.city.name,
        timezone=city_resp.location.time_zone,
        latitude=city_resp.location.latitude,
        longitude=city_resp.location.longitude,
        isp=None,
        asn=asn_value,
        source="maxmind",
    )


def _from_ip_api(ip: str) -> Optional[GeoResult]:
    if not IP_API_ENABLED:
        return None

    cached = _ip_api_cache.get(ip)
    if cached and (time.monotonic() - cached[0]) < _IP_API_CACHE_TTL:
        return cached[1]

    url = (
        f"http://ip-api.com/json/{ip}"
        "?fields=status,countryCode,regionName,city,lat,lon,timezone,isp,as"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TriageCounsel-Analytics/1.0"})
        with urllib.request.urlopen(req, timeout=IP_API_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return None

    if data.get("status") != "success":
        return None

    result = GeoResult(
        country=data.get("countryCode"),
        region=data.get("regionName"),
        city=data.get("city"),
        timezone=data.get("timezone"),
        latitude=data.get("lat"),
        longitude=data.get("lon"),
        isp=data.get("isp"),
        asn=(data.get("as") or "").split(" ")[0] or None,
        source="ip-api",
    )

    if len(_ip_api_cache) >= _IP_API_CACHE_MAX:
        _ip_api_cache.clear()
    _ip_api_cache[ip] = (time.monotonic(), result)
    return result


def _normalize(result: GeoResult) -> GeoResult:
    """Country is stored in a VARCHAR(2) column on Postgres, which raises
    (rather than truncating) on overflow. Cloudflare/MaxMind/ip-api are all
    guaranteed-2-letter by their own docs, but the generic proxy-header
    source (`_from_proxy_headers`) has no such guarantee — an operator's
    nginx geoip config could emit a full country name. Normalize once,
    here, so every source is safe regardless of provenance."""
    country = result.country
    if country and (len(country) != 2 or not country.isalpha()):
        country = None
    elif country:
        country = country.upper()
    if country == result.country:
        return result
    from dataclasses import replace
    return replace(result, country=country)


def geolocate(ip: str, headers: Mapping[str, str], allow_network_fallback: bool = True) -> GeoResult:
    """Resolve geo facts for an IP address, trying cheapest sources first.

    `headers` should be a case-insensitive-ish mapping of lowercase header
    names to values (see analytics.extract_headers). Never raises.
    """
    if not ip:
        return _EMPTY

    try:
        if not _is_public_ip(ip):
            return GeoResult(source="private")

        for lookup in (
            lambda: _from_cloudflare(headers),
            lambda: _from_proxy_headers(headers),
            lambda: _from_maxmind(ip),
        ):
            result = lookup()
            if result is not None:
                return _normalize(result)

        if allow_network_fallback:
            result = _from_ip_api(ip)
            if result is not None:
                return _normalize(result)

        return _EMPTY
    except Exception:
        logger.exception("Geolocation failed for ip=%r", ip)
        return _EMPTY
