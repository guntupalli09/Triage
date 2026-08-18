#!/usr/bin/env python3
"""
Step 4A.4 — FIRST AND ONLY frozen held-out execution. Run once against the
frozen Step 4A.3 implementation (commit fc51fa4e). Does not modify any
production file. Prints raw actual output (state, extracted_summary,
unresolved_facts, our_position) plus the locked label/expected/reason for
every case, so classification is auditable against the raw output — same
methodology as benchmarks/run_step4a2_heldout.py.
"""
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import liability_policy_engine as lpe
import indemnification_policy_engine as ie
import payment_terms_policy_engine as pte
from benchmarks.step4a4_corpus import ALL_CASES
from benchmarks.step4a4_formatting_mutations import MUT_CASES

KWARGS_BY_ID = {c["id"]: c["kwargs"] for c in ALL_CASES}
TEXT_BY_ID = {c["id"]: c["text"] for c in ALL_CASES}


@dataclass
class LolPolicy:
    preferred_multiplier: Optional[float] = 1.0
    acceptable_max_multiplier: Optional[float] = 2.0
    negotiate_max_multiplier: Optional[float] = 3.0
    prohibit_unlimited: bool = True
    required_exceptions_json: Optional[List[str]] = None
    fallback_text: Optional[str] = "fallback"
    escalation_approval_authority: Optional[str] = "Legal Director"
    contract_side: str = "mutual"
    require_consequential_damages_exclusion: bool = False
    required_consequential_carveouts_json: Optional[List[str]] = None


@dataclass
class IndemPolicy:
    contract_side: str = "mutual"
    escalation_approval_authority: Optional[str] = "Legal Director"
    fallback_text: Optional[str] = "fallback"
    required_protection_triggers_json: Optional[List[str]] = None
    prohibited_exposure_triggers_json: Optional[List[str]] = None
    require_exposure_third_party_only: bool = False
    require_defense_control_for_exposure: bool = False
    require_notice_and_cooperation_for_exposure: bool = False
    prohibit_uncapped_exposure: bool = True
    exposure_preferred_multiplier: Optional[float] = 1.0
    exposure_acceptable_max_multiplier: Optional[float] = 2.0
    exposure_negotiate_max_multiplier: Optional[float] = 3.0


@dataclass
class PayPolicy:
    contract_side: str = "buy_side"
    escalation_approval_authority: Optional[str] = "Legal Director"
    fallback_text: Optional[str] = "fallback"
    require_counterparty_is_payor: bool = False
    preferred_net_days: Optional[float] = None
    acceptable_max_net_days: Optional[float] = None
    required_payment_trigger: Optional[str] = None
    require_undisputed_amounts_still_payable: bool = False
    prohibit_disputed_amount_withholding: bool = False
    minimum_dispute_notice_days: Optional[float] = None
    prohibit_set_off: bool = False
    maximum_late_interest_rate_percent: Optional[float] = None
    prohibit_unilateral_price_increase: bool = False
    maximum_price_increase_percent: Optional[float] = None
    minimum_price_increase_notice_days: Optional[float] = None
    require_expense_preapproval: bool = False
    require_tax_responsibility_counterparty: bool = False
    required_currency: Optional[str] = None
    require_refund_entitlement: bool = False


def run_case(adapter, text, kwargs):
    if adapter == "liability":
        policy = LolPolicy(**kwargs)
        facts = lpe.extract_liability_facts(text)
        decision = lpe.evaluate_liability_policy(facts, policy)
        our_position = decision.our_position
    elif adapter == "indemnification":
        policy = IndemPolicy(**kwargs)
        facts = ie.extract_indemnification_facts(text)
        decision = ie.evaluate_indemnification_policy(facts, policy)
        our_position = None
        if facts is not None:
            exposure, protection, _ = ie._resolve_obligations_for_side(facts.obligations, policy.contract_side)
            our_position = {"exposure": exposure.indemnifying_role if exposure else None,
                             "protection": protection.indemnified_role if protection else None}
    elif adapter == "payment_terms":
        policy = PayPolicy(**kwargs)
        facts = pte.extract_payment_facts(text)
        decision = pte.evaluate_payment_policy(facts, policy)
        our_position = None
        if facts is not None:
            payor_side, _ = pte._resolve_payor_side(facts, policy.contract_side)
            tax_side, _ = pte._resolve_tax_responsibility(facts, policy.contract_side)
            our_position = {"payor_side": payor_side, "tax_side": tax_side}
    else:
        raise ValueError(adapter)
    return decision, our_position


def main():
    print(f"# Step 4A.4 Held-Out Run — {len(ALL_CASES)} semantic + {len(MUT_CASES)} formatting mutation cases\n")
    for case in ALL_CASES:
        decision, our_position = run_case(case["adapter"], case["text"], case["kwargs"])
        print(f"=== {case['id']} [{case['adapter']}/{case['family']}] label={case['label']} ===")
        print(f"STATE: {decision.state}")
        print(f"extracted_summary: {decision.extracted_summary!r}")
        print(f"unresolved_facts: {decision.unresolved_facts}")
        print(f"our_position: {our_position}")
        print(f"explanation: {decision.explanation}")
        print(f"EXPECTED: {case['expected']}")
        print(f"REASON: {case['reason']}")
        print()

    for mid, base_id, text, label, expected in MUT_CASES:
        adapter = next(c["adapter"] for c in ALL_CASES if c["id"] == base_id)
        kwargs = KWARGS_BY_ID[base_id]
        decision, our_position = run_case(adapter, text, kwargs)
        print(f"=== {mid} [base={base_id}] label={label} ===")
        print(f"STATE: {decision.state}")
        print(f"extracted_summary: {decision.extracted_summary!r}")
        print(f"unresolved_facts: {decision.unresolved_facts}")
        print(f"our_position: {our_position}")
        print(f"EXPECTED: {expected}")
        print()


if __name__ == "__main__":
    main()
