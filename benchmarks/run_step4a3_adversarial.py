#!/usr/bin/env python3
"""Runs the Step 4A.3 40-case fresh adversarial corpus. This is a
first-pass, same-session sanity check against the post-4A.3 code — NOT a
frozen held-out corpus and NOT a substitute for Step 4A.4."""
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import liability_policy_engine as lpe
import indemnification_policy_engine as ie
import payment_terms_policy_engine as pte
from benchmarks.step4a3_adversarial_corpus import (
    ROLE_CASES, PAYMENT_CASES, LIABILITY_OWNERSHIP_CASES, INDEMNIFICATION_ASYMMETRY_CASES,
)


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


def run_role_group():
    print("## Group A: role-definition / fallback (10)\n")
    print("| id | adapter | expect | state | extracted | ok |")
    print("|---|---|---|---|---|---|")
    n_ok = 0
    for case_id, adapter, text, kwargs, expect in ROLE_CASES:
        if adapter == "liability":
            policy = LolPolicy(**kwargs)
            facts = lpe.extract_liability_facts(text)
            decision = lpe.evaluate_liability_policy(facts, policy)
        elif adapter == "indemnification":
            policy = IndemPolicy(**kwargs)
            facts = ie.extract_indemnification_facts(text)
            decision = ie.evaluate_indemnification_policy(facts, policy)
        else:
            policy = PayPolicy(**kwargs)
            facts = pte.extract_payment_facts(text)
            decision = pte.evaluate_payment_policy(facts, policy)
        if expect == "escalate":
            ok = decision.state == "REQUIRES_REVIEW"
        else:
            _, sub = expect.split(":", 1)
            ok = decision.state != "REQUIRES_REVIEW" and sub in decision.extracted_summary
        n_ok += ok
        print(f"| {case_id} | {adapter} | {expect} | {decision.state} | {decision.extracted_summary!r} | {'OK' if ok else 'FAIL'} |")
    print(f"\nGroup A: {n_ok}/{len(ROLE_CASES)} correct\n")
    return n_ok


def run_payment_group():
    print("## Group B: Payment Terms recognition (10)\n")
    print("| id | expect | recognized | note |")
    print("|---|---|---|---|")
    n_ok = n_scored = 0
    for case_id, text, expect in PAYMENT_CASES:
        facts = pte.extract_payment_facts(text)
        recognized = facts is not None and facts.clause_found
        if expect == "no_engage_known_gap":
            note = "informational (documented gap)"
        else:
            n_scored += 1
            ok = recognized == (expect == "engage")
            n_ok += ok
            note = "OK" if ok else "FAIL"
        print(f"| {case_id} | {expect} | {recognized} | {note} |")
    print(f"\nGroup B: {n_ok}/{n_scored} scored correct\n")
    return n_ok, n_scored


def run_liability_ownership_group():
    print("## Group C: Liability candidate-ownership (10)\n")
    print("| id | expect | got | ok |")
    print("|---|---|---|---|")
    n_ok = 0
    for case_id, text, expect in LIABILITY_OWNERSHIP_CASES:
        facts = lpe.extract_liability_facts(text)
        cp = facts.controlling_provision if facts else None
        cap = cp.general_cap_expression if cp else None
        reviewed = cap is None or bool(cap.unresolved_reason or not cap.components)
        value = cap.raw_excerpt if (cap and not reviewed) else None
        if expect == "escalate":
            ok = reviewed
        else:
            _, sub = expect.split(":", 1)
            ok = (not reviewed) and sub in (value or "")
        n_ok += ok
        display_value = repr(value) if not reviewed else "REVIEW"
        print(f"| {case_id} | {expect} | {display_value} | {'OK' if ok else 'FAIL'} |")
    print(f"\nGroup C: {n_ok}/{len(LIABILITY_OWNERSHIP_CASES)} correct\n")
    return n_ok


def run_indemnification_asymmetry_group():
    print("## Group D: Indemnification reciprocal asymmetry (10)\n")
    print("| id | expect | detected | ok/informational |")
    print("|---|---|---|---|")
    n_ok = n_scored = 0
    for case_id, text, expect in INDEMNIFICATION_ASYMMETRY_CASES:
        facts = ie.extract_indemnification_facts(text)
        reciprocal = [o for o in (facts.obligations if facts else []) if o.is_mutual_reciprocal]
        detected = bool(reciprocal and reciprocal[0].asymmetry_reasons)
        if expect is None:
            note = "informational"
        else:
            n_scored += 1
            ok = detected == expect
            n_ok += ok
            note = "OK" if ok else "FAIL"
        print(f"| {case_id} | {expect} | {detected} | {note} |")
    print(f"\nGroup D: {n_ok}/{n_scored} scored correct\n")
    return n_ok, n_scored


def main():
    a = run_role_group()
    b, b_scored = run_payment_group()
    c = run_liability_ownership_group()
    d, d_scored = run_indemnification_asymmetry_group()
    total_scored = 10 + b_scored + 10 + d_scored
    total_ok = a + b + c + d
    print(f"## TOTAL: {total_ok}/{total_scored} scored correct across all 40 fresh adversarial cases")


if __name__ == "__main__":
    main()
