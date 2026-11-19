"""Unit tests for src/metrics.py. Run from the project root: python -m pytest tests -q

Reference values come from R, forecast 9.0.2:
    t <- 1:60; e1 <- sin(t) + 0.3*cos(3*t); e2 <- 0.8*sin(t + 0.5) + 0.1*t/60
    dm.test(e1, e2, h = 1, power = 2)  -> DM = 3.2369586900, p = 0.0019837267
    dm.test(e1, e2, h = 5, power = 2)  -> DM = 6.2008494419, p = 0.0000000599
    dm.test(e1, e2, h = 1, power = 1)  -> DM = 3.0490292128, p = 0.0034343033
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.metrics import dm_test, point_metrics  # noqa: E402

t = np.arange(1, 61)
E1 = np.sin(t) + 0.3 * np.cos(3 * t)
E2 = 0.8 * np.sin(t + 0.5) + 0.1 * t / 60


@pytest.mark.parametrize("h, power, dm_ref, p_ref", [
    (1, 2, 3.2369586900, 0.0019837267),
    (5, 2, 6.2008494419, 0.0000000599),
    (1, 1, 3.0490292128, 0.0034343033),
])
def test_dm_matches_r_forecast(h, power, dm_ref, p_ref):
    r = dm_test(np.abs(E1) ** power, np.abs(E2) ** power, h=h)
    assert r["DM"] == pytest.approx(dm_ref, abs=1e-8)
    assert r["p_value"] == pytest.approx(p_ref, abs=1e-8)


def test_dm_is_antisymmetric():
    a, b = dm_test(E1 ** 2, E2 ** 2, h=3), dm_test(E2 ** 2, E1 ** 2, h=3)
    assert a["DM"] == pytest.approx(-b["DM"])
    assert a["p_value"] == pytest.approx(b["p_value"])


def test_dm_rejects_identical_forecasts():
    with pytest.raises(ValueError):
        dm_test(E1 ** 2, E1 ** 2, h=1)


def test_newey_west_option_matches_manual_formula():
    d = E1 ** 2 - E2 ** 2
    n, L = d.size, 4
    dc = d - d.mean()
    gam = [np.sum(dc[k:] * dc[: n - k]) / n for k in range(L + 1)]
    v = gam[0] + 2 * sum((1 - k / (L + 1)) * gam[k] for k in range(1, L + 1))
    expected = d.mean() / np.sqrt(v / n) * np.sqrt((n + 1 - 2 + 0) / n)   # h = 1 correction
    r = dm_test(E1 ** 2, E2 ** 2, h=1, nw_lags=L)
    assert r["DM"] == pytest.approx(expected)
    assert r["variance"] == "Newey-West (4 lags)"


def test_point_metrics_simple_case():
    m = point_metrics([100, 200], [90, 220])
    assert m["MSE"] == pytest.approx(250.0)
    assert m["RMSE"] == pytest.approx(np.sqrt(250.0))
    assert m["MAE"] == pytest.approx(15.0)
    assert m["MAPE_%"] == pytest.approx(10.0)
