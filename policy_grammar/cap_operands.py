from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union

from policy_grammar.fee_relative import FeeBasis, FeeScope
from policy_grammar.money import MoneyAmount


class ReferenceTarget(str, Enum):
    GENERAL_CAP = "GENERAL_CAP"


@dataclass(frozen=True)
class FeeRelativeCap:
    months: float
    basis: FeeBasis = FeeBasis.CONTRACT_FEES
    scope: FeeScope = FeeScope.AGREEMENT

    @property
    def operand_type(self) -> str:
        return "fee_period"


@dataclass(frozen=True)
class AnnualFeeMultipleCap:
    multiple: float

    @property
    def operand_type(self) -> str:
        return "annual_fee_multiple"


@dataclass(frozen=True)
class FixedAmountCap:
    money: MoneyAmount

    @property
    def operand_type(self) -> str:
        return "fixed_amount"


@dataclass(frozen=True)
class ReferenceCap:
    ref: ReferenceTarget
    multiplier: float

    @property
    def operand_type(self) -> str:
        return "reference"


@dataclass(frozen=True)
class UnlimitedCap:
    @property
    def operand_type(self) -> str:
        return "unlimited"


CapOperand = Union[FeeRelativeCap, AnnualFeeMultipleCap, FixedAmountCap, ReferenceCap, UnlimitedCap]
