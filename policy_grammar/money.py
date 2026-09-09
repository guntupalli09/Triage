from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Union


@dataclass(frozen=True)
class MoneyAmount:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("MoneyAmount.amount must be non-negative")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("MoneyAmount.currency must be a 3-letter ISO code")

    @classmethod
    def from_number(cls, amount: Union[int, float, str, Decimal], currency: str = "USD") -> "MoneyAmount":
        try:
            dec = Decimal(str(amount))
        except (InvalidOperation, ValueError) as e:
            raise ValueError(f"invalid money amount: {amount!r}") from e
        return cls(amount=dec, currency=currency.upper())
