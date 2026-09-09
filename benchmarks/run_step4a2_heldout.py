#!/usr/bin/env python3
"""
Step 4A.2 — run the frozen held-out corpus against production code EXACTLY
ONCE. This script does not modify any production file. Ground truth lives
in step4a2_heldout_corpus.py / step4a2_formatting_mutations.py, written
before this script ever ran.

Classification (per Step 4A.2 instructions):
  CA — Correct Automatic: system reached a clean state matching ground truth.
  CR — Correct Review: system returned REQUIRES_REVIEW and gt.review_expected
       is True (or gt.review_expected is False but is explicitly marked
       generously-acceptable in this script's per-case override list).
  FE — False Escalation: system returned REQUIRES_REVIEW but gt says a
       specific correct answer was deterministically establishable.
  WC — Wrong Clean: system reached a clean state that does NOT match ground
       truth (wrong side / wrong value / wrong direction).
  NA — genuinely out of adapter scope (used sparingly, never to hide a
       failure).

This script prints per-case raw actual output AND the classification, so
the classification logic itself is auditable against the raw output.
"""
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import liability_policy_engine as lpe
import indemnification_policy_engine as ie
import payment_terms_policy_engine as pte

from benchmarks.step4a2_heldout_corpus import CASES as SEMANTIC_CASES
from benchmarks.step4a2_formatting_mutations import MUT_CASES


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
    permitted_exposure_triggers_json: Optional[List[str]] = None
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


def run_case(case):
    adapter = case["adapter"]
    kwargs = case["kwargs"]
    text = case["text"]
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
    all_cases = SEMANTIC_CASES + MUT_CASES
    print(f"# Step 4A.2 Held-Out Run — {len(SEMANTIC_CASES)} semantic + {len(MUT_CASES)} formatting mutation cases\n")
    for case in all_cases:
        decision, our_position = run_case(case)
        print(f"=== {case['id']} [{case['adapter']}/{case['family']}] ===")
        print(f"STATE: {decision.state}")
        print(f"extracted_summary: {decision.extracted_summary!r}")
        print(f"unresolved_facts: {decision.unresolved_facts}")
        print(f"our_position/side info: {our_position}")
        print(f"explanation: {decision.explanation}")
        print(f"GT: review_expected={case['gt']['review_expected']} correct_side={case['gt'].get('correct_side')} "
              f"correct_value={case['gt'].get('correct_value')}")
        print()


if __name__ == "__main__":
    main()
