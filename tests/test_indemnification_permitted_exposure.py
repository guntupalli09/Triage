"""Indemnification permitted-vs-prohibited exposure trigger semantics."""
from __future__ import annotations

import os

os.environ.setdefault("DEV_MODE", "true")

import indemnification_policy_engine as ipe
import playbook_authoring as pa
import playbook_extraction as pex


class TestPermittedExposureSemantics:
    def test_narrow_scope_maps_to_permitted_not_prohibited(self):
        text = (
            "3. Indemnification. Customer shall indemnify Vendor only for third-party claims "
            "arising from customer materials or unlawful use of the services."
        )
        facts = ipe.extract_indemnification_facts(text)
        proposed = pex.propose_fields("indemnification", facts, contract_side="buy_side")
        permitted = proposed["permitted_exposure_triggers_json"]
        prohibited = proposed["prohibited_exposure_triggers_json"]
        assert permitted.status == "ESTABLISHED"
        assert "customer_materials" in permitted.value
        assert "unlawful_use" in permitted.value
        assert prohibited.status == "NOT_ESTABLISHED"

    def test_review_summary_labels_permitted_separately(self):
        cfg = {
            "permitted_exposure_triggers_json": ["customer_materials", "unlawful_use"],
            "prohibited_exposure_triggers_json": [],
        }
        lines = pa._summarize_indemnification(cfg)
        permitted_line = next(l for l in lines if l.startswith("We will only indemnify for"))
        prohibited_line = next(l for l in lines if l.startswith("We will never indemnify for"))
        assert "Customer materials" in permitted_line
        assert "Unlawful use" in permitted_line
        assert prohibited_line.endswith("None specified")
