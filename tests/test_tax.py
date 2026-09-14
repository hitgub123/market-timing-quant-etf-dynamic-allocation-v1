import pytest

from market_timing_quant.tax import SimplifiedJapanTax


def test_loss_pool_offsets_future_gain():
    tax = SimplifiedJapanTax()
    assert tax.realize(1000) == pytest.approx(203.15)
    assert tax.realize(-400) == 0
    assert tax.loss_pool == 400
    assert tax.realize(500) == pytest.approx(20.315)
    assert tax.loss_pool == 0
    assert tax.tax_paid == pytest.approx(223.465)

