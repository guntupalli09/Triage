from __future__ import annotations

from enum import Enum


class FeeBasis(str, Enum):
    FEES_PAID = "FEES_PAID"
    FEES_PAYABLE = "FEES_PAYABLE"
    FEES_PAID_OR_PAYABLE = "FEES_PAID_OR_PAYABLE"
    CONTRACT_FEES = "CONTRACT_FEES"
    UNRESOLVED = "UNRESOLVED"


class FeeScope(str, Enum):
    AGREEMENT = "AGREEMENT"
    ORDER_FORM = "ORDER_FORM"
    CLAIM_RELATED_SERVICES = "CLAIM_RELATED_SERVICES"
    UNRESOLVED = "UNRESOLVED"


def fee_bases_compatible(a: FeeBasis, b: FeeBasis) -> bool:
    """Two fee bases are symbolically comparable when neither is UNRESOLVED
    and they refer to the same fee concept or a known-compatible pair."""
    if a == FeeBasis.UNRESOLVED or b == FeeBasis.UNRESOLVED:
        return False
    if a == b:
        return True
    compatible_pairs = {
        frozenset({FeeBasis.FEES_PAID_OR_PAYABLE, FeeBasis.FEES_PAID}),
        frozenset({FeeBasis.FEES_PAID_OR_PAYABLE, FeeBasis.FEES_PAYABLE}),
        frozenset({FeeBasis.FEES_PAID_OR_PAYABLE, FeeBasis.CONTRACT_FEES}),
        frozenset({FeeBasis.CONTRACT_FEES, FeeBasis.FEES_PAID}),
        frozenset({FeeBasis.CONTRACT_FEES, FeeBasis.FEES_PAYABLE}),
    }
    return frozenset({a, b}) in compatible_pairs


def fee_scopes_compatible(a: FeeScope, b: FeeScope) -> bool:
    if a == FeeScope.UNRESOLVED or b == FeeScope.UNRESOLVED:
        return False
    return a == b
