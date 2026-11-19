"""GARCH helpers (Phase 5): model specs, comparison rows, standardised-residual diagnostics, volatility forecasts.

Returns are in PERCENT (100 x log return): the `arch` optimiser is much more stable on that scale.
Volatility forecasts use the common format of src/arima.py with y_true = squared return (a noisy but
unbiased proxy of the true variance) and y_pred = forecast variance, both in %².
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from arch import arch_model
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox

from .arima import FORECAST_COLUMNS, arch_lm

SPECS = {
    "GARCH(1,1)-N": dict(vol="GARCH", p=1, q=1, dist="normal"),
    "GARCH(1,1)-t": dict(vol="GARCH", p=1, q=1, dist="t"),
    "GJR-GARCH(1,1)-t": dict(vol="GARCH", p=1, o=1, q=1, dist="t"),
    "EGARCH(1,1)-t": dict(vol="EGARCH", p=1, o=1, q=1, dist="t"),
}


def fit(y: pd.Series, spec: str, last_obs=None):
    """Constant mean + the chosen variance equation. Why a constant mean: Phase 3 chose ARIMA(0,1,0),
    i.e. returns = constant + white noise, so no AR/MA term is needed in the mean."""
    kw = SPECS[spec] if spec in SPECS else spec
    return arch_model(y, mean="Constant", **kw).fit(disp="off", last_obs=last_obs)


def persistence(res) -> float:
    """How long a variance shock lasts. GARCH: Σα + Σβ; GJR: + γ/2 (symmetric errors); EGARCH: β (log-variance AR coefficient)."""
    p = res.params
    if res.model.volatility.__class__.__name__ == "EGARCH":
        return float(p.filter(like="beta").sum())
    return float(p.filter(like="alpha").sum() + p.filter(like="beta").sum() + 0.5 * p.filter(like="gamma").sum())


def half_life(pers: float) -> float:
    """Days for a variance shock to halve: ln(0.5) / ln(persistence)."""
    return float(np.log(0.5) / np.log(pers)) if 0 < pers < 1 else np.inf


def summary_row(res, name: str) -> dict:
    pers = persistence(res)
    row = {"model": name, "n": int(res.nobs), "loglik": res.loglikelihood, "AIC": res.aic, "BIC": res.bic,
           "persistence": pers, "half-life (d)": half_life(pers)}
    for k, v in res.params.items():
        row[k] = v
        row[f"p({k})"] = res.pvalues[k]
    return row


def std_resid_diagnostics(res) -> pd.DataFrame:
    """Brief §3.3: standardised residuals z should be white noise AND homoscedastic once volatility is modelled."""
    z = res.std_resid.dropna().to_numpy()
    rows = []
    for what, x in [("z", z), ("z²", z ** 2)]:
        lb = acorr_ljungbox(x, lags=[10, 20])
        for m, r in lb.iterrows():
            rows.append((f"Ljung-Box on {what}", f"lag {m}", r["lb_stat"], r["lb_pvalue"]))
    for m in (5, 10):
        lm, p = arch_lm(z, m)
        rows.append(("ARCH-LM on z", f"lag {m}", lm, p))
    dist = res.model.distribution.name
    if "t" in dist.lower() or "student" in dist.lower():
        nu = res.params["nu"]
        ks = stats.kstest(z / np.sqrt(nu / (nu - 2)), "t", args=(nu,))   # z has unit variance; rescale to a standard t
        rows.append(("Kolmogorov-Smirnov vs Student-t(ν)", f"ν = {nu:.1f}", ks.statistic, ks.pvalue))
    else:
        ks = stats.kstest(z, "norm")
        rows.append(("Kolmogorov-Smirnov vs normale", "", ks.statistic, ks.pvalue))
    t = pd.DataFrame(rows, columns=["test", "parameter", "statistic", "p_value"])
    t["conclusion (5%)"] = np.where(t["p_value"] < 0.05, "reject H0", "H0 not rejected")
    return t


def qq_points(res):
    """Theoretical quantiles of the ASSUMED distribution (unit variance) vs sorted standardised residuals."""
    z = np.sort(res.std_resid.dropna().to_numpy())
    q = (np.arange(1, len(z) + 1) - 0.5) / len(z)
    if "nu" in res.params:
        nu = res.params["nu"]
        theo = stats.t.ppf(q, nu) * np.sqrt((nu - 2) / nu)
    else:
        theo = stats.norm.ppf(q)
    return theo, z


def vol_forecasts(y: pd.Series, spec: str, train_end, origins, H: int, model: str, series: str, seed: int) -> pd.DataFrame:
    """Variance forecasts 1..H from every origin, parameters estimated on TRAIN only (`last_obs`), never refitted.

    `arch` conditions each origin's forecast on the data up to that origin. EGARCH has no closed form beyond
    one step, so its multi-step forecast is simulated (fixed seed, 2,000 paths).
    """
    first_test = y.index[y.index.get_loc(train_end) + 1]
    res = fit(y, spec, last_obs=first_test)            # last_obs is exclusive: estimation stops at train_end
    kw = {"method": "simulation", "simulations": 2000, "rng": np.random.default_rng(seed).standard_normal} \
        if "EGARCH" in spec else {}
    f = res.forecast(horizon=H, start=origins[0], reindex=False, **kw).variance
    idx = y.index
    out = []
    for o in origins:
        n_o = idx.get_loc(o) + 1
        for h in range(min(H, len(idx) - n_o)):
            d = idx[n_o + h]
            out.append({"date": d, "model": model, "series": series, "origin": o, "horizon": h + 1,
                        "y_true": float(y.iloc[n_o + h] ** 2), "y_pred": float(f.loc[o].iloc[h]),
                        "lower": np.nan, "upper": np.nan})
    return pd.DataFrame(out, columns=FORECAST_COLUMNS), res


def naive_vol_forecasts(y: pd.Series, train_end, origins, H: int, series: str, window: int = 20) -> pd.DataFrame:
    """Two benchmarks: constant train variance, and the last `window`-day sample variance (a 'random walk' for volatility)."""
    const = float(y.loc[:train_end].var())
    idx = y.index
    out = []
    for o in origins:
        n_o = idx.get_loc(o) + 1
        recent = float(y.iloc[n_o - window:n_o].var())
        for h in range(min(H, len(idx) - n_o)):
            d = idx[n_o + h]
            for m, v in (("const_var", const), (f"hist_var{window}", recent)):
                out.append({"date": d, "model": m, "series": series, "origin": o, "horizon": h + 1,
                            "y_true": float(y.iloc[n_o + h] ** 2), "y_pred": v, "lower": np.nan, "upper": np.nan})
    return pd.DataFrame(out, columns=FORECAST_COLUMNS)


def vol_scores(fc: pd.DataFrame, horizons=(5, 10)) -> pd.DataFrame:
    """MSE on the variance proxy and QLIKE = r²/σ̂² − ln(r²/σ̂²) − 1 (robust to the noise of r², Patton 2011).

    QLIKE uses r² floored at 1e-6 to avoid ln(0) on days with a zero return."""
    rows = []
    for (m, s), g in fc.groupby(["model", "series"], sort=False):
        for h in horizons:
            k = g[g["horizon"] == h]
            r2, v = k["y_true"].clip(lower=1e-6), k["y_pred"]
            rows.append({"model": m, "series": s, "horizon": h, "n": len(k),
                         "MSE_var": float(((k["y_true"] - v) ** 2).mean()),
                         "QLIKE": float((r2 / v - np.log(r2 / v) - 1).mean())})
    return pd.DataFrame(rows)
