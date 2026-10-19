"""Estimated trip cost compared with the budget."""

from pydantic import BaseModel


class CostLine(BaseModel):
    label: str
    amount: float
    detail: str = ""


class CostBreakdown(BaseModel):
    currency: str
    lines: list[CostLine]
    total: float
    budget: float | None = None
    remaining: float | None = None
    over_budget: bool = False
    notes: list[str] = []
