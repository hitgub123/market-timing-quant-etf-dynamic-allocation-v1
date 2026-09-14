from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimplifiedJapanTax:
    rate: float = 0.20315
    loss_pool: float = 0.0
    tax_paid: float = 0.0

    def realize(self, realized_gain: float) -> float:
        if realized_gain < 0:
            self.loss_pool += -realized_gain
            return 0.0
        offset = min(realized_gain, self.loss_pool)
        self.loss_pool -= offset
        tax = (realized_gain - offset) * self.rate
        self.tax_paid += tax
        return tax

    def preview(self, realized_gain: float) -> float:
        if realized_gain <= 0:
            return 0.0
        return max(0.0, realized_gain - self.loss_pool) * self.rate
