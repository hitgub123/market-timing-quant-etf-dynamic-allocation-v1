import pandas as pd
import pytest

from market_timing_quant.walk_forward import expanding_calendar_year_folds, require_selection_constraints, select_calmar_candidate


def test_expanding_folds_match_frozen_calendar_year_contract():
    sessions = pd.bdate_range("2006-06-21", "2014-06-30")
    folds = expanding_calendar_year_folds(sessions)
    assert [fold.test_year for fold in folds] == [2013, 2014]
    assert folds[0].train_start == pd.Timestamp("2006-06-21")
    assert folds[0].train_end == pd.Timestamp("2012-12-31")
    assert folds[1].train_end == pd.Timestamp("2013-12-31")
    assert folds[1].test_end == pd.Timestamp("2014-06-30")


def test_parameter_selection_fails_closed_without_frozen_constraints():
    with pytest.raises(ValueError, match="minimum CAGR"):
        require_selection_constraints(None, None)
    require_selection_constraints(.10, .45)


def test_selection_returns_no_parameter_when_frozen_gate_has_no_eligible_candidate():
    candidates = pd.DataFrame([
        {"ma_days": 200, "cagr": .149, "max_drawdown": -.40, "calmar": .37, "annual_turnover": 1.0},
        {"ma_days": 225, "cagr": .20, "max_drawdown": -.451, "calmar": .44, "annual_turnover": .8},
    ])
    selected, evaluated = select_calmar_candidate(candidates)
    assert selected is None
    assert not evaluated.eligible.any()


def test_selection_uses_frozen_tie_breaks_inside_five_percent_calmar_band():
    candidates = pd.DataFrame([
        {"ma_days": 200, "momentum_days": 252, "low_vol_quantile": .33,
         "cagr": .20, "max_drawdown": -.40, "calmar": .500, "annual_turnover": 1.0},
        {"ma_days": 225, "momentum_days": 252, "low_vol_quantile": .33,
         "cagr": .19, "max_drawdown": -.38, "calmar": .480, "annual_turnover": 1.2},
        {"ma_days": 250, "momentum_days": 252, "low_vol_quantile": .33,
         "cagr": .19, "max_drawdown": -.37, "calmar": .470, "annual_turnover": .5},
    ])
    selected, evaluated = select_calmar_candidate(candidates)
    assert selected.ma_days == 225
    assert evaluated.within_5pct_of_best_calmar.tolist() == [True, True, False]


def test_selection_prefers_longer_parameters_then_quantile_nearest_point_33():
    common = {"cagr": .20, "max_drawdown": -.40, "calmar": .50, "annual_turnover": 1.0}
    candidates = pd.DataFrame([
        {**common, "ma_days": 225, "momentum_days": 252, "low_vol_quantile": .40},
        {**common, "ma_days": 250, "momentum_days": 189, "low_vol_quantile": .33},
        {**common, "ma_days": 250, "momentum_days": 252, "low_vol_quantile": .40},
        {**common, "ma_days": 250, "momentum_days": 252, "low_vol_quantile": .33},
    ])
    selected, _ = select_calmar_candidate(candidates)
    assert selected.ma_days == 250
    assert selected.momentum_days == 252
    assert selected.low_vol_quantile == pytest.approx(.33)
