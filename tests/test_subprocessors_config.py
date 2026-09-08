"""Tests for the canonical subprocessor register."""
from __future__ import annotations

import subprocessors_config as spc


def test_subprocessor_register_has_unique_names():
    names = [row["name"] for row in spc.SUBPROCESSORS]
    assert len(names) == len(set(names)), f"Duplicate subprocessor names: {names}"


def test_subprocessor_register_expected_count():
    assert len(spc.SUBPROCESSORS) == 5


def test_subprocessor_register_expected_vendors():
    names = {row["name"] for row in spc.SUBPROCESSORS}
    assert names == {
        "Hetzner Online GmbH",
        "OpenAI, L.L.C.",
        "Stripe, Inc.",
        "Google LLC",
        "SMTP email provider",
    }
