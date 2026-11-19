"""Exploratory-analysis helpers (Phase 2): stationarity tests, STL, outliers, pivot-date evidence.

Every function returns a plain DataFrame / Series so notebooks only display and comment.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import adfuller, coint, kpss
from statsmodels.tools.sm_exceptions import InterpolationWarning

ALPHA = 0.05


# --------------------------------------------------------------------------- stationarity
def adf_kpss(x: pd.Series, regression: str = "c") -> dict:
    """ADF (H0: unit root) and KPSS (H0: stationary) on one series, plus the joint verdict.

    Why both: their null hypotheses are opposite, so agreement gives a firm conclusion
    and disagreement flags a borderline case (brief §2).
    ADF lag length chosen by AIC; KPSS bandwidth by the data-driven 'auto' rule.
    """
    x = x.dropna()
    adf_stat, adf_p, adf_lag, *_ = adfuller(x, regression=regression, autolag="AIC", result_object=False)
    with warnings.catch_warnings():
        # KPSS p-values are interpolated in a table bounded at 0.01 / 0.10; the bound is reported as is.
        warnings.simplefilter("ignore", InterpolationWarning)
        kpss_stat, kpss_p, kpss_lag, _ = kpss(x, regression=regression, nlags="auto", result_object=False)
    adf_stationary = adf_p < ALPHA
    kpss_stationary = kpss_p >= ALPHA
    if adf_stationary and kpss_stationary:
        verdict = "stationary"
    elif not adf_stationary and not kpss_stationary:
        verdict = "non-stationary"
    else:
        verdict = "ambiguous (tests disagree)"
    return {"adf_stat": adf_stat, "adf_p": adf_p, "adf_lags": adf_lag,
            "kpss_stat": kpss_stat, "kpss_p": kpss_p, "kpss_lags": kpss_lag,
            "adf_rejects_unit_root": adf_stationary, "kpss_rejects_stationarity": not kpss_stationary,
            "verdict": verdict}


def stationarity_table(levels: dict[str, pd.Series]) -> pd.DataFrame:
    """ADF + KPSS on each series in level (with trend) and in first difference (constant only).

    Why 'ct' for levels: log prices can drift, so the alternative must allow a deterministic trend;
    differences have no trend, so a constant is enough.
    """
    rows = []
    for name, s in levels.items():
        for form, series, reg in [("level (log price)", s, "ct"), ("difference (log return)", s.diff(), "c")]:
            rows.append({"series": name, "form": form, "regression": reg, **adf_kpss(series, reg)})
    return pd.DataFrame(rows)


def integration_order(table: pd.DataFrame) -> pd.DataFrame:
    """d = 0 if the level is stationary, 1 if only the difference is, otherwise flagged."""
    out = []
    for name, g in table.groupby("series", sort=False):
        lvl, dif = g.iloc[0]["verdict"], g.iloc[1]["verdict"]
        if lvl == "stationary":
            d = "0"
        elif dif == "stationary":
            d = "1"
        else:
            d = "to discuss"
        out.append({"series": name, "level": lvl, "difference": dif, "chosen d": d})
    return pd.DataFrame(out)


# --------------------------------------------------------------------------- decomposition
def stl_shares(x: pd.Series, period: int) -> dict:
    """STL fit + how much variance the seasonal part explains.

    Seasonal strength F_S = max(0, 1 - Var(R) / Var(S + R)) (Hyndman & Athanasopoulos, FPP3 §3.9):
    close to 0 = no seasonality, close to 1 = strong seasonality.
    robust=True so isolated crashes do not leak into the seasonal component.
    """
    xv = x.dropna()
    res = STL(xv.to_numpy(), period=period, robust=True).fit()
    s, r, t = res.seasonal, res.resid, res.trend
    return {
        "period": period,
        "var_share_seasonal": np.var(s) / np.var(xv.to_numpy()),
        "var_share_remainder": np.var(r) / np.var(xv.to_numpy()),
        "seasonal_strength_FS": max(0.0, 1 - np.var(r) / np.var(s + r)),
        "trend_strength_FT": max(0.0, 1 - np.var(r) / np.var(t + r)),
        "seasonal_amplitude": float(np.max(s) - np.min(s)),
        "result": res,
    }


def weekday_effect(r: pd.Series) -> dict:
    """Formal test of weekly seasonality on returns (the series that will actually be modelled).

    ANOVA F (H0: same mean return every weekday) and Kruskal-Wallis (same H0 without
    normality, safer with heavy tails).
    """
    r = r.dropna()
    groups = [g.to_numpy() for _, g in r.groupby(r.index.dayofweek)]
    F, pF = stats.f_oneway(*groups)
    H, pH = stats.kruskal(*groups)
    means = r.groupby(r.index.dayofweek).mean()
    return {"anova_F": F, "anova_p": pF, "kruskal_H": H, "kruskal_p": pH,
            "mean_mon": means[0], "mean_fri": means[4],
            "share_var_explained": float(r.groupby(r.index.dayofweek).transform("mean").var() / r.var())}


# --------------------------------------------------------------------------- outliers
def hampel(x: pd.Series, window: int = 21, n_sigmas: float = 4.0) -> pd.DataFrame:
    """Hampel filter: flag |x - rolling median| > n_sigmas * 1.4826 * rolling MAD.

    Why median/MAD: they are not pulled by the outliers themselves (unlike mean/std).
    Centred window because this is a descriptive diagnostic, not a forecast input.
    """
    med = x.rolling(window, center=True, min_periods=window // 2).median()
    mad = (x - med).abs().rolling(window, center=True, min_periods=window // 2).median()
    scale = 1.4826 * mad
    score = (x - med) / scale
    return pd.DataFrame({"value": x, "median": med, "scale": scale, "score": score,
                         "flag": score.abs() > n_sigmas})


def rolling_iqr(x: pd.Series, window: int = 63, k: float = 3.0) -> pd.DataFrame:
    """Rolling-boxplot rule: flag x outside [Q1 - k*IQR, Q3 + k*IQR] of the trailing window.

    Trailing (past-only) window = what an observer knew that day. k = 3 ('far out' in Tukey's
    terms) instead of 1.5 because daily returns are heavy-tailed and 1.5 flags too many days.
    """
    past = x.shift(1).rolling(window, min_periods=window)
    q1, q3 = past.quantile(0.25), past.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - k * iqr, q3 + k * iqr
    return pd.DataFrame({"value": x, "lower": lo, "upper": hi, "flag": (x < lo) | (x > hi)})


# --------------------------------------------------------------------------- pivot-date evidence
def rolling_corr(a: pd.Series, b: pd.Series, window: int) -> pd.Series:
    """Trailing Pearson correlation (needs a full window)."""
    return a.rolling(window, min_periods=window).corr(b)


def rolling_engle_granger(y: pd.Series, x: pd.Series, window: int, step: int = 5) -> pd.Series:
    """Engle-Granger cointegration p-value on a trailing window, recomputed every `step` days.

    H0 of each test: no cointegration between y and x on that window.
    Why a step: ~200 tests instead of ~1,000, same picture, much faster.
    """
    idx = range(window, len(y) + 1, step)
    out = {}
    for end in idx:
        yy, xx = y.iloc[end - window:end], x.iloc[end - window:end]
        out[y.index[end - 1]] = coint(yy, xx, trend="c", autolag="AIC")[1]
    return pd.Series(out, name="eg_pvalue")


def ols_ssr(y: np.ndarray, X: np.ndarray) -> float:
    """Sum of squared residuals of an OLS fit."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    return float(e @ e)


def chow_test(y: pd.Series, X: pd.DataFrame, break_date) -> dict:
    """Chow test for a break in ALL coefficients at a given date.

    H0: same coefficients before and after the date. F = [(SSR_p - SSR_1 - SSR_2)/k] / [(SSR_1+SSR_2)/(n-2k)].
    """
    yv, Xv = y.to_numpy(), X.to_numpy()
    n, k = Xv.shape
    cut = int(np.searchsorted(y.index, pd.Timestamp(break_date)))
    ssr_p = ols_ssr(yv, Xv)
    ssr1, ssr2 = ols_ssr(yv[:cut], Xv[:cut]), ols_ssr(yv[cut:], Xv[cut:])
    F = ((ssr_p - ssr1 - ssr2) / k) / ((ssr1 + ssr2) / (n - 2 * k))
    return {"date": y.index[cut], "n_before": cut, "n_after": n - cut, "F": F,
            "p_value": float(stats.f.sf(F, k, n - 2 * k))}


def chow_scan(y: pd.Series, X: pd.DataFrame, trim: float = 0.15) -> pd.Series:
    """Chow F statistic at every candidate date in the central (1 - 2*trim) of the sample (Quandt / sup-F scan).

    The argmax is the data's best single break date. Its p-value from chow_test is too
    optimistic (the date was chosen by looking), so it is read as a location, not as a test.
    """
    yv, Xv = y.to_numpy(), X.to_numpy()
    n, k = Xv.shape
    ssr_p = ols_ssr(yv, Xv)
    out = {}
    for cut in range(int(n * trim), int(n * (1 - trim))):
        ssr1, ssr2 = ols_ssr(yv[:cut], Xv[:cut]), ols_ssr(yv[cut:], Xv[cut:])
        out[y.index[cut]] = ((ssr_p - ssr1 - ssr2) / k) / ((ssr1 + ssr2) / (n - 2 * k))
    return pd.Series(out, name="chow_F")


def bai_perron_ruptures(y: pd.Series, X: pd.DataFrame, max_breaks: int = 5,
                        min_size: int = 60) -> pd.DataFrame:
    """Multiple breaks in the regression y = X b (Bai-Perron style, exact dynamic programming).

    Number of breaks chosen by BIC: n*log(SSR/n) + (m+1)*k*log(n) + m*log(n).
    min_size = 60 trading days (~3 months) so each regime has enough data to estimate b.
    """
    import ruptures as rpt

    yv, Xv = y.to_numpy(), X.to_numpy()
    n, k = Xv.shape
    algo = rpt.Dynp(model="linear", min_size=min_size, jump=1).fit(np.column_stack([yv, Xv]))
    rows = []
    for m in range(0, max_breaks + 1):
        bkps = [n] if m == 0 else algo.predict(n_bkps=m)
        edges = [0, *bkps]
        ssr = sum(ols_ssr(yv[a:b], Xv[a:b]) for a, b in zip(edges[:-1], edges[1:]))
        bic = n * np.log(ssr / n) + (m + 1) * k * np.log(n) + m * np.log(n)
        rows.append({"n_breaks": m, "SSR": ssr, "BIC": bic,
                     "break_dates": [str(y.index[b].date()) for b in bkps[:-1]]})
    return pd.DataFrame(rows)


def regime_betas(y: pd.Series, X: pd.DataFrame, dates: list) -> pd.DataFrame:
    """OLS coefficients and R² in each regime delimited by `dates` (to read what changed)."""
    edges = [y.index[0], *[pd.Timestamp(d) for d in dates], y.index[-1] + pd.Timedelta(days=1)]
    rows = []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (y.index >= a) & (y.index < b)
        yv, Xv = y[m].to_numpy(), X[m].to_numpy()
        beta, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
        e = yv - Xv @ beta
        r2 = 1 - (e @ e) / np.sum((yv - yv.mean()) ** 2)
        rows.append({"start": y.index[m][0].date(), "end": y.index[m][-1].date(), "n": int(m.sum()),
                     **{f"beta_{c}": v for c, v in zip(X.columns, beta)}, "R2": r2})
    return pd.DataFrame(rows)
