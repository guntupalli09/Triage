"""
Policy enforcement engine — the firm's deterministic legal operating system.

Replaces "compare this contract to a template document" with "evaluate this
contract against the firm's authored legal positions," organized in an
inheritable Firm -> Organization -> Practice Group -> Client -> Matter
hierarchy and bound to the existing deterministic rule engine
(rules_engine.py) by policy topic, not by document identity.

Submodules (see docs/architecture plan for the full design):
    db_models          SQLAlchemy models for the hierarchy + policy tables
    repository          Firm-scoped CRUD for hierarchy entities and policy sets
    inheritance          Inheritance Resolver — merges PolicySets across levels
    topic_binding        Finding <-> PolicyRule matching key
    policy_engine         Deterministic 6-status classifier
    decision_engine       Orchestrator: Finding -> PolicyDecision
    override_manager      Attorney overrides (append-only, never mutates policy)
    version_manager        Clone/publish/rollback/compare/archive/import/export
    audit_engine           Single write/read path for the firm audit trail
    compliance_reporter     Deterministic aggregate reporting
    migration               One-time backfill of legacy Playbook rows
    api / schemas            JSON API surface
"""
