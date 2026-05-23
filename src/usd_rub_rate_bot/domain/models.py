"""Domain models for USD/RUB rates."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CommercialRate(BaseModel):
    """A buy/sell quote from a single commercial source.

    ``buy`` is the rate at which the source buys USD from the customer
    (customer sells USD, receives RUB).
    ``sell`` is the rate at which the source sells USD to the customer
    (customer pays RUB, receives USD).
    """

    source: str = Field(min_length=1)
    buy: float = Field(gt=0)
    sell: float = Field(gt=0)


class CentralBankRate(BaseModel):
    """The Central Bank of Russia official rate (single value, not buy/sell)."""

    source: str = Field(min_length=1)
    value: float = Field(gt=0)
