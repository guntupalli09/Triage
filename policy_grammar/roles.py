from __future__ import annotations

from enum import Enum


class NormalizedRole(str, Enum):
    CUSTOMER = "customer"
    VENDOR = "vendor"
    LICENSOR = "licensor"
    LICENSEE = "licensee"
    SERVICE_PROVIDER = "service_provider"
    CLIENT = "client"
    COUNTERPARTY = "counterparty"
    MUTUAL = "mutual"


class TransactionOrientation(str, Enum):
    BUY_SIDE = "buy_side"
    SELL_SIDE = "sell_side"
    MUTUAL = "mutual"
