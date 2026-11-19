"""Forecast-evaluation metrics (Phase 7): point metrics and the Diebold-Mariano test with the
Harvey-Leybourne-Newbold (1997) small-sample correction.

Tested in tests/test_metrics.py against R's forecast::dm.test (forecast 9.0.2).
"""
from __future__ import annotations

import numpy as np
from scipy import stats


def point_metrics(y_true, y_pred) -> dict:
    """MSE, RMSE, MAE and MAPE (in %) of a forecast. MAPE divides by y_true, so it must be computed on a series
    that never gets close to 0 — prices / index levels, not returns (a return near 0 makes MAPE explode)."""
    y, f = np.asarray(y_true, float), np.asarray(y_pred, float)
    e = y - f
    return {"MSE": float(np.mean(e ** 2)), "RMSE": float(np.sqrt(np.mean(e ** 2))),
            "MAE": float(np.mean(np.abs(e))), "MAPE_%": float(np.mean(np.abs(e / y)) * 100)}


def dm_test(loss1, loss2, h: int = 1, nw_lags: int | None = None) -> dict:
    """Diebold-Mariano test of equal predictive accuracy, with the HLN small-sample correction.

    Parameters
    ----------
    loss1, loss2 : array-like
        Losses of model 1 and model 2 on the SAME targets, in time order (e.g. squared errors e², or QLIKE).
    h : int
        Forecast horizon. h-step forecasts made every day overlap, so the loss differential is
        autocorrelated up to lag h - 1; the long-run variance includes those h - 1 autocovariances.
    nw_lags : int, optional
        Robustness option: Newey-West (Bartlett-weighted) long-run variance with this many lags instead of
        the standard h - 1. Useful when the loss differential is persistent beyond h - 1 (e.g. two slowly
        moving volatility forecasts), where the standard variance is too small and DM too large.

    Returns
    -------
    dict with
        DM      : HLN-corrected statistic. DM > 0 means model 1 has the LARGER loss (model 2 is better).
        p_value : two-sided, from a Student t with n - 1 degrees of freedom (HLN recommendation).
        mean_d  : average loss differential mean(loss1 - loss2).
        n, h, variance : sample size, horizon and which long-run variance estimator was used.

    Notes
    -----
    H0: E[loss1 - loss2] = 0 (equal accuracy). Statistic: DM = mean(d) / sqrt(V / n), with
    V = gamma_0 + 2 * sum_{k=1}^{h-1} gamma_k (autocovariances with divisor n, as R's acf()).
    HLN correction: DM* = DM * sqrt((n + 1 - 2h + h(h - 1) / n) / n).
    If V <= 0 (possible with the rectangular window), Bartlett weights (1 - k/h) are used instead.
    """
    d = np.asarray(loss1, float) - np.asarray(loss2, float)
    n = d.size
    if n < 3 or np.allclose(d, 0):
        raise ValueError("loss differential is empty or identically zero: the two forecasts are the same")
    dc = d - d.mean()
    L = h if nw_lags is None else nw_lags + 1
    gam = np.array([np.sum(dc[k:] * dc[: n - k]) / n for k in range(L)])
    if nw_lags is not None:
        v = gam[0] + 2 * sum((1 - k / (nw_lags + 1)) * gam[k] for k in range(1, L))
        used = f"Newey-West ({nw_lags} lags)"
    else:
        v = gam[0] + 2 * gam[1:].sum()
        used = "rectangular (h-1 lags)"
    if v <= 0:
        v = gam[0] + 2 * sum((1 - k / h) * gam[k] for k in range(1, h))
        used = "Bartlett (fallback)"
    dm = d.mean() / np.sqrt(v / n)
    k = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    stat = dm * k
    p = 2 * stats.t.sf(abs(stat), df=n - 1)
    return {"DM": float(stat), "p_value": float(p), "mean_d": float(d.mean()), "n": n, "h": h, "variance": used}
