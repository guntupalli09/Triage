"""
SQLAlchemy models for first-party acquisition & product analytics.

Four tables, each with a distinct purpose so the schema stays normalized
and query-efficient at scale instead of a wide, ever-growing `users` table:

- UserAcquisition: one row per user, written once at signup, never
  mutated afterwards. "How did this user find us."
- UserSession: one row per browsing session (anonymous or authenticated).
  "When did they show up, and from where."
- UserEvent: append-only product-analytics event stream. "What did they
  do." Designed for very high write volume.
- ContractEvent: one row per contract upload, carrying upload-specific
  technical facts (hash, size, processing time) that don't belong on the
  general event stream.

Notes on scale-oriented choices:
- Event tables use BigInteger primary keys (Integer would wrap around
  well before 100M+ rows). Parent tables keep their existing Integer PKs;
  FK columns match the parent type.
- `user_events.session_id` / `contract_events.session_id` are plain
  indexed strings, not enforced foreign keys to `user_sessions`. At
  high ingest volume, decoupling the event write path from another
  table's row-existence lock is a deliberate tradeoff (standard for
  event/analytics tables) — correlation is done at query time.
- `acquisition_channel` is a plain VARCHAR, not a Postgres ENUM, so new
  channels (see channel_classifier.py) never require a migration.
- All new columns/tables are additive — no existing table is altered by
  this module, so init_db()'s `create_all` covers them with zero
  downtime and zero data loss on existing deployments.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from database import Base

# JSONB on Postgres, plain JSON everywhere else (e.g. local SQLite dev).
_JSONType = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")
# INET on Postgres (indexable, CIDR-aware), plain VARCHAR everywhere else.
_IPType = String(45).with_variant(INET(), "postgresql")
# BIGINT/bigserial on Postgres for real headroom past 2.1B rows. On SQLite,
# only a column whose *declared* type is exactly INTEGER becomes the
# ROWID-aliased autoincrementing primary key — BigInteger's SQLite affinity
# (BIGINT) loses that behavior and leaves new rows with a NULL id. Since
# SQLite is dev-only here, downgrading the PK affinity there is safe.
_BigPK = BigInteger().with_variant(Integer(), "sqlite")


class UserAcquisition(Base):
    """Immutable first-touch/signup snapshot. One-to-one with users."""

    __tablename__ = "user_acquisition"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    signup_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    signup_ip = Column(_IPType, nullable=True)
    signup_ipv6 = Column(_IPType, nullable=True)

    signup_country = Column(String(2), nullable=True)
    signup_region = Column(String(120), nullable=True)
    signup_city = Column(String(120), nullable=True)
    signup_timezone = Column(String(64), nullable=True)

    signup_latitude = Column(Float, nullable=True)
    signup_longitude = Column(Float, nullable=True)

    signup_user_agent = Column(Text, nullable=True)

    browser = Column(String(60), nullable=True)
    browser_version = Column(String(30), nullable=True)

    os = Column(String(60), nullable=True)
    os_version = Column(String(30), nullable=True)

    device_type = Column(String(20), nullable=True)
    device_brand = Column(String(60), nullable=True)
    device_model = Column(String(100), nullable=True)

    is_mobile = Column(Boolean, nullable=False, default=False)
    is_tablet = Column(Boolean, nullable=False, default=False)
    is_desktop = Column(Boolean, nullable=False, default=False)

    language = Column(String(35), nullable=True)
    screen_resolution = Column(String(20), nullable=True)
    viewport = Column(String(20), nullable=True)

    signup_referrer = Column(Text, nullable=True)
    signup_referring_domain = Column(String(255), nullable=True)
    landing_page = Column(Text, nullable=True)
    query_string = Column(Text, nullable=True)

    utm_source = Column(String(255), nullable=True)
    utm_medium = Column(String(255), nullable=True)
    utm_campaign = Column(String(255), nullable=True)
    utm_term = Column(String(255), nullable=True)
    utm_content = Column(String(255), nullable=True)

    gclid = Column(String(512), nullable=True)
    fbclid = Column(String(512), nullable=True)
    msclkid = Column(String(512), nullable=True)
    ttclid = Column(String(512), nullable=True)
    li_fat_id = Column(String(512), nullable=True)

    session_id = Column(String(64), nullable=True)
    first_request_id = Column(String(64), nullable=True)

    x_forwarded_for = Column(Text, nullable=True)
    # Raw header capture for audit/debugging — deliberately *not* INET typed
    # (unlike signup_ip/signup_ipv6) since it stores whatever the proxy
    # sent verbatim, which may not always be a single valid address.
    x_real_ip = Column(String(255), nullable=True)

    asn = Column(String(20), nullable=True)
    isp = Column(String(255), nullable=True)

    acquisition_channel = Column(String(40), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="acquisition")

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_acquisition_user_id"),
        Index("ix_user_acquisition_channel", "acquisition_channel"),
        Index("ix_user_acquisition_utm_campaign", "utm_source", "utm_campaign"),
        Index("ix_user_acquisition_country", "signup_country"),
        Index("ix_user_acquisition_signup_ts", "signup_timestamp"),
    )


class UserSession(Base):
    """One row per browsing session (anonymous or authenticated)."""

    __tablename__ = "user_sessions"

    id = Column(_BigPK, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    session_id = Column(String(64), nullable=False)

    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    ip = Column(_IPType, nullable=True)
    country = Column(String(2), nullable=True)

    browser = Column(String(60), nullable=True)
    os = Column(String(60), nullable=True)
    device = Column(String(20), nullable=True)
    user_agent = Column(Text, nullable=True)

    landing_page = Column(Text, nullable=True)
    referrer = Column(Text, nullable=True)

    is_authenticated = Column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        UniqueConstraint("session_id", name="uq_user_sessions_session_id"),
        Index("ix_user_sessions_user_started", "user_id", "started_at"),
        Index("ix_user_sessions_started_at", "started_at"),
    )


class UserEvent(Base):
    """Append-only product-analytics event stream. High write volume."""

    __tablename__ = "user_events"

    id = Column(_BigPK, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_id = Column(String(64), nullable=True)

    event_type = Column(String(60), nullable=False)
    event_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    page = Column(Text, nullable=True)
    ip = Column(_IPType, nullable=True)
    country = Column(String(2), nullable=True)
    referrer = Column(Text, nullable=True)

    # DB column is literally named "metadata" per spec; the Python
    # attribute can't be called that — `metadata` is reserved on every
    # SQLAlchemy declarative class (it's the schema MetaData collection).
    event_metadata = Column("metadata", _JSONType, nullable=True)

    user = relationship("User", back_populates="events")

    __table_args__ = (
        Index("ix_user_events_type_ts", "event_type", "event_timestamp"),
        Index("ix_user_events_user_ts", "user_id", "event_timestamp"),
        Index("ix_user_events_session", "session_id"),
        Index("ix_user_events_ts", "event_timestamp"),
        Index("ix_user_events_metadata_gin", "metadata", postgresql_using="gin"),
    )


class ContractEvent(Base):
    """One row per contract upload attempt — upload-specific technical facts."""

    __tablename__ = "contract_events"

    id = Column(_BigPK, primary_key=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_id = Column(String(64), nullable=True)

    event_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    upload_ip = Column(_IPType, nullable=True)
    country = Column(String(2), nullable=True)
    browser = Column(String(60), nullable=True)
    device = Column(String(20), nullable=True)
    user_agent = Column(Text, nullable=True)

    filename = Column(String(255), nullable=True)
    sha256 = Column(String(64), nullable=True)
    filesize = Column(Integer, nullable=True)
    processing_time = Column(Float, nullable=True)
    status = Column(String(20), nullable=True)  # processing | completed | failed

    contract = relationship("Contract", back_populates="events")

    __table_args__ = (
        Index("ix_contract_events_contract_ts", "contract_id", "event_timestamp"),
        Index("ix_contract_events_sha256", "sha256"),
        Index("ix_contract_events_status_ts", "status", "event_timestamp"),
        Index("ix_contract_events_user_ts", "user_id", "event_timestamp"),
    )
