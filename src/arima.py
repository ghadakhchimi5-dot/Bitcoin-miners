"""ARIMA helpers (Phase 3): order search, residual diagnostics, rolling-origin forecasts.

Common forecast format (shared by every model, read by Phase 7):
    date, model, series, origin, horizon, y_true, y_pred, lower, upper
`y_*` are on the PRICE LEVEL (index points), `horizon` = steps ahead (1..H), `origin` = last
date the model has seen. The 7 columns of the brief are all there; `series` and `origin` are added.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.arima.model import ARIMA

ALPHA = 0.05
FORECAST_COLUMNS = ["date", "model", "series", "origin", "horizon", "y_true", "y_pred", "lower", "upper"]


def fit_arima(y: pd.Series, order: tuple, trend: str = "n", seasonal_order=(0, 0, 0, 0)):
    """Fit by exact maximum likelihood (state space); optimiser warnings are kept out of the notebook."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ARIMA(y.to_numpy(), order=order, trend=trend, seasonal_order=seasonal_order).fit()


def order_grid(y: pd.Series, d: int = 1, max_p: int = 3, max_q: int = 3) -> pd.DataFrame:
    """AIC / BIC for every (p, d, q) with p, q <= 3, with and without drift.

    Why a full small grid: it shows how flat the criterion surface is, which a stepwise search hides.
    trend='t' with d=1 is a drift (constant mean of the returns).
    """
    rows = []
    for p in range(max_p + 1):
        for q in range(max_q + 1):
            for trend in ("n", "t"):
                r = fit_arima(y, (p, d, q), trend)
                rows.append({"order": f"({p},{d},{q})", "p": p, "q": q, "drift": trend == "t",
                             "k": len(r.params), "loglik": r.llf, "AIC": r.aic, "BIC": r.bic,
                             "converged": bool(r.mle_retvals.get("converged", True))})
    g = pd.DataFrame(rows)
    g["dAIC"] = g["AIC"] - g["AIC"].min()
    g["dBIC"] = g["BIC"] - g["BIC"].min()
    return g


def arch_lm(e, nlags: int) -> tuple[float, float]:
    """Engle's ARCH-LM test (H0: no ARCH effect). Returns (LM statistic, p-value)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)  # statsmodels announces a return-type change, values are unchanged
        lm, p, *_ = het_arch(np.asarray(e, dtype=float), nlags=nlags)
    return float(lm), float(p)


def residual_diagnostics(resid: np.ndarray, model_df: int = 0, lags=(5, 10, 20)) -> pd.DataFrame:
    """Brief §3.1: independence, normality and ARCH tests, each with H0 and a written verdict.

    The first residual of a d=1 model is the (diffuse) first observation, so callers drop it.
    model_df = p + q corrects the Ljung-Box degrees of freedom for the estimated ARMA terms.
    """
    e = np.asarray(resid, dtype=float)
    rows = []
    lb = acorr_ljungbox(e, lags=list(lags), model_df=model_df)
    for m, r in lb.iterrows():
        rows.append(("Ljung-Box", f"lag {m}", "no autocorrelation up to lag m", r["lb_stat"], r["lb_pvalue"]))
    lb2 = acorr_ljungbox(e ** 2, lags=[10])
    rows.append(("Ljung-Box on e²", "lag 10", "no autocorrelation of squares", lb2["lb_stat"].iloc[0], lb2["lb_pvalue"].iloc[0]))
    lba = acorr_ljungbox(np.abs(e), lags=[10])
    rows.append(("Ljung-Box on |e|", "lag 10", "no autocorrelation of absolute values", lba["lb_stat"].iloc[0], lba["lb_pvalue"].iloc[0]))
    jb = stats.jarque_bera(e)
    rows.append(("Jarque-Bera", "", "normal residuals (skew 0, kurtosis 3)", jb.statistic, jb.pvalue))
    sw = stats.shapiro(e)
    rows.append(("Shapiro-Wilk", "", "normal residuals", sw.statistic, sw.pvalue))
    for m in (5, 10):
        lm, p = arch_lm(e, m)
        rows.append(("ARCH-LM", f"lag {m}", "no ARCH effect (constant conditional variance)", lm, p))
    t = pd.DataFrame(rows, columns=["test", "parameter", "H0", "statistic", "p_value"])
    t["conclusion (5%)"] = np.where(t["p_value"] < ALPHA, "reject H0", "H0 not rejected")
    return t


def rolling_forecasts(res, log_level: pd.Series, origins: pd.DatetimeIndex, H: int,
                      model: str, series: str, level=0.95) -> pd.DataFrame:
    """Forecast 1..H steps from every origin with the TRAIN parameters kept fixed.

    Why fixed parameters (`apply`, no refit): no information from the test period leaks into the
    estimates; the model only sees the new observations as conditioning data, like a forecaster would.
    Log forecasts are mapped back with exp(): exp(mean) is the median of the level forecast, and
    exp() of the log interval bounds is an exact interval for the level.
    """
    out = []
    y = log_level.to_numpy()
    idx = log_level.index
    for o in origins:
        n_o = idx.get_loc(o) + 1
        steps = min(H, len(y) - n_o)
        if steps < 1:
            continue
        r_o = res.apply(y[:n_o])
        f = r_o.get_forecast(steps)
        mean, ci = f.predicted_mean, f.conf_int(alpha=1 - level)
        for h in range(steps):
            out.append({"date": idx[n_o + h], "model": model, "series": series, "origin": o, "horizon": h + 1,
                        "y_true": float(np.exp(y[n_o + h])), "y_pred": float(np.exp(mean[h])),
                        "lower": float(np.exp(ci[h, 0])), "upper": float(np.exp(ci[h, 1]))})
    return pd.DataFrame(out, columns=FORECAST_COLUMNS)


def quick_scores(fc: pd.DataFrame, horizons=(5, 10)) -> pd.DataFrame:
    """RMSE / MAE / MAPE / interval coverage at given horizons (a preview; Phase 7 does the full evaluation)."""
    rows = []
    for (m, s), g in fc.groupby(["model", "series"], sort=False):
        for h in horizons:
            k = g[g["horizon"] == h]
            e = k["y_true"] - k["y_pred"]
            rows.append({"model": m, "series": s, "horizon": h, "n_origins": len(k),
                         "RMSE": float(np.sqrt((e ** 2).mean())), "MAE": float(e.abs().mean()),
                         "MAPE_%": float((e.abs() / k["y_true"]).mean() * 100),
                         "coverage_95%": float(((k["y_true"] >= k["lower"]) & (k["y_true"] <= k["upper"])).mean() * 100)})
    return pd.DataFrame(rows)
