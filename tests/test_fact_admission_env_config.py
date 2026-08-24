"""Tests for fact_admission.semantic_discovery_enabled() — the Phase 12
env-var-driven configuration this branch adds (see
artifacts/final_architecture/PRE_IMPLEMENTATION_MAP.md's "no
FACT_ADMISSION_MODE env var exists" finding). Each of the 11 adapters'
own <ADAPTER>_SEMANTIC_DISCOVERY_ENABLED module constants is initialized
by calling this function at import time — this file tests the function
directly rather than re-importing every adapter module (which would only
pick up the environment as it existed at interpreter start).
"""
import fact_admission as fa


def test_defaults_to_disabled_with_no_env_vars(monkeypatch):
    monkeypatch.delenv("LIABILITY_SEMANTIC_DISCOVERY_ENABLED", raising=False)
    monkeypatch.delenv("FACT_ADMISSION_MODE", raising=False)
    assert fa.semantic_discovery_enabled("LIABILITY_SEMANTIC_DISCOVERY_ENABLED") is False


def test_adapter_specific_env_var_enables_it(monkeypatch):
    monkeypatch.delenv("FACT_ADMISSION_MODE", raising=False)
    monkeypatch.setenv("LIABILITY_SEMANTIC_DISCOVERY_ENABLED", "true")
    assert fa.semantic_discovery_enabled("LIABILITY_SEMANTIC_DISCOVERY_ENABLED") is True


def test_global_fact_admission_mode_enforced_enables_every_adapter(monkeypatch):
    monkeypatch.delenv("LIABILITY_SEMANTIC_DISCOVERY_ENABLED", raising=False)
    monkeypatch.delenv("CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED", raising=False)
    monkeypatch.setenv("FACT_ADMISSION_MODE", "enforced")
    assert fa.semantic_discovery_enabled("LIABILITY_SEMANTIC_DISCOVERY_ENABLED") is True
    assert fa.semantic_discovery_enabled("CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED") is True


def test_adapter_specific_false_overrides_global_enforced(monkeypatch):
    """An operator can enable everything globally except one adapter they
    are not ready to turn on."""
    monkeypatch.setenv("FACT_ADMISSION_MODE", "enforced")
    monkeypatch.setenv("LIABILITY_SEMANTIC_DISCOVERY_ENABLED", "false")
    assert fa.semantic_discovery_enabled("LIABILITY_SEMANTIC_DISCOVERY_ENABLED") is False
    assert fa.semantic_discovery_enabled("CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED") is True


def test_global_mode_not_enforced_leaves_adapters_disabled(monkeypatch):
    monkeypatch.delenv("LIABILITY_SEMANTIC_DISCOVERY_ENABLED", raising=False)
    monkeypatch.setenv("FACT_ADMISSION_MODE", "shadow")
    assert fa.semantic_discovery_enabled("LIABILITY_SEMANTIC_DISCOVERY_ENABLED") is False


def test_case_and_whitespace_insensitive(monkeypatch):
    monkeypatch.delenv("LIABILITY_SEMANTIC_DISCOVERY_ENABLED", raising=False)
    monkeypatch.setenv("FACT_ADMISSION_MODE", "  ENFORCED  ")
    assert fa.semantic_discovery_enabled("LIABILITY_SEMANTIC_DISCOVERY_ENABLED") is True


def test_all_eleven_adapter_flags_are_actually_wired_to_this_function():
    """Confirms every adapter file that should call semantic_discovery_
    enabled() at import time actually does -- guards against a future
    adapter integration copy-pasting the old hardcoded-False pattern
    instead of the env-driven one."""
    import ast
    adapters = [
        "liability_policy_engine.py", "confidentiality_policy_engine.py",
        "data_security_policy_engine.py", "ip_ownership_policy_engine.py",
        "insurance_policy_engine.py", "payment_terms_policy_engine.py",
        "termination_policy_engine.py", "warranties_policy_engine.py",
        "sla_policy_engine.py", "governing_law_policy_engine.py",
        "assignment_policy_engine.py",
    ]
    for path in adapters:
        with open(path) as f:
            source = f.read()
        assert "semantic_discovery_enabled(" in source, f"{path} does not call semantic_discovery_enabled()"
