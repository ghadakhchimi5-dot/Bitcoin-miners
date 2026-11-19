"""Multivariate helpers (Phase 4): VAR, Granger, Johansen, Engle-Granger, VECM, VAR/VECM forecasts.

Forecasts use the common format of src/arima.py (levels in index points, rolling origins, fixed parameters).
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import coint
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen

from .arima import FORECAST_COLUMNS, arch_lm

ALPHA = 0.05


def period_slices(index: pd.DatetimeIndex, pivot) -> dict:
    """Full sample, pre-pivot (strictly before), post-pivot (from the pivot day on)."""
    piv = pd.Timestamp(pivot)
    return {"full": index, "pre-pivot": index[index < piv], "post-pivot": index[index >= piv]}


# --------------------------------------------------------------------------- VAR
def lag_table(df: pd.DataFrame, maxlags: int = 10) -> tuple[pd.DataFrame, dict]:
    """AIC / BIC / HQ / FPE for p = 0..maxlags on the same estimation sample (comparable values)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sel = VAR(df).select_order(maxlags)
    t = pd.DataFrame({k.upper(): v for k, v in sel.ics.items()})
    t.index.name = "p"
    return t, {k.upper(): int(v) for k, v in sel.selected_orders.items()}


def fit_var(df: pd.DataFrame, p: int):
    return VAR(df).fit(p)


def var_diagnostics(res, nlags: int = 10) -> pd.DataFrame:
    """Stability, Portmanteau (whiteness), Jarque-Bera (multivariate) and per-equation ARCH-LM, with verdicts."""
    rows = []
    max_mod = float(np.max(np.abs(np.linalg.eigvals(_companion(res.coefs))))) if res.k_ar else 0.0
    rows.append(("stability", "max |eigenvalue| of the companion matrix", "—", max_mod, np.nan,
                 "stable (< 1)" if max_mod < 1 else "UNSTABLE"))
    w = res.test_whiteness(nlags=nlags, adjusted=True)
    rows.append(("adjusted Portmanteau", f"lag {nlags}", "no joint residual autocorrelation", float(w.test_statistic), float(w.pvalue), _v(w.pvalue)))
    n = res.test_normality()
    rows.append(("multivariate Jarque-Bera", "", "normal residuals", float(n.test_statistic), float(n.pvalue), _v(n.pvalue)))
    for j, name in enumerate(res.names):
        lm, p = arch_lm(res.resid.iloc[:, j] if hasattr(res.resid, "iloc") else res.resid[:, j], 5)
        rows.append((f"ARCH-LM equation {name}", "lag 5", "no ARCH effect", lm, p, _v(p)))
    return pd.DataFrame(rows, columns=["test", "parameter", "H0", "statistic", "p_value", "conclusion (5%)"])


def _companion(coefs: np.ndarray) -> np.ndarray:
    p, k, _ = coefs.shape
    top = np.concatenate(list(coefs), axis=1)
    if p == 1:
        return top
    bottom = np.eye(k * (p - 1), k * p)
    return np.vstack([top, bottom])


def _v(p: float) -> str:
    return "reject H0" if p < ALPHA else "H0 not rejected"


def granger_pairs(res, refs=("BTC", "NVDA"), groups=("CONVERTS", "PURE")) -> pd.DataFrame:
    """Pairwise Granger tests inside the VAR (F version). H0: the lags of `cause` do not help predict `effect`."""
    rows = []
    for x in refs:
        for g in groups:
            for cause, effect in [(x, g), (g, x)]:
                t = res.test_causality(effect, cause, kind="f")
                rows.append({"cause": cause, "effect": effect, "H0": f"{cause} does not Granger-cause {effect}",
                             "F": float(t.test_statistic), "df": f"({t.df[0]}, {t.df[1]})", "p_value": float(t.pvalue),
                             "conclusion (5%)": _v(t.pvalue)})
    return pd.DataFrame(rows)


def impact_responses(res, shocks=("BTC", "NVDA"), targets=("CONVERTS", "PURE"), periods: int = 10) -> pd.DataFrame:
    """Orthogonalised IRF (Cholesky in the column order) with 95 % asymptotic bands, for h = 0..periods."""
    irf = res.irf(periods)
    se = irf.stderr(orth=True)
    names = list(res.names)
    rows = []
    for s in shocks:
        for t in targets:
            i, j = names.index(t), names.index(s)
            for h in range(periods + 1):
                v, e = irf.orth_irfs[h, i, j], se[h, i, j]
                rows.append({"shock": s, "response": t, "h": h, "irf": v, "lower": v - 1.96 * e, "upper": v + 1.96 * e})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- cointegration
def johansen_pair(y: pd.DataFrame, k_ar_diff: int = 1, det_order: int = 0) -> dict:
    """Johansen trace and max-eigenvalue tests for a pair; rank = number of 5 % rejections in sequence.

    det_order = 0: constant term (Johansen 'case 3', unrestricted constant). Why: log prices drift
    (BTC, NVDA trend up), so the levels need a drift, and a constant must be allowed in the relation.
    """
    j = coint_johansen(y.to_numpy(), det_order=det_order, k_ar_diff=k_ar_diff)
    r_tr = next((r for r in range(2) if j.lr1[r] < j.cvt[r, 1]), 2)
    r_me = next((r for r in range(2) if j.lr2[r] < j.cvm[r, 1]), 2)
    return {"trace_r0": j.lr1[0], "cv95_trace_r0": j.cvt[0, 1], "trace_r1": j.lr1[1], "cv95_trace_r1": j.cvt[1, 1],
            "maxeig_r0": j.lr2[0], "cv95_maxeig_r0": j.cvm[0, 1], "rank_trace": r_tr, "rank_maxeig": r_me}


def engle_granger(y: pd.Series, x: pd.Series) -> dict:
    """Engle-Granger (H0: no cointegration), y regressed on x with a constant, MacKinnon p-value."""
    stat, p, _ = coint(y, x, trend="c", autolag="AIC")
    return {"EG_stat": stat, "EG_p": p}


def half_life(alpha: float) -> float:
    """Trading days for half of a deviation to vanish: ln(0.5) / ln(1 + alpha) (only if -1 < alpha < 0)."""
    return float(np.log(0.5) / np.log(1 + alpha)) if -1 < alpha < 0 else np.nan


def fit_vecm(y: pd.DataFrame, k_ar_diff: int = 1, rank: int = 1):
    """VECM with an unrestricted constant ('co'), matching the Johansen case used in the tests."""
    return VECM(y, k_ar_diff=k_ar_diff, coint_rank=rank, deterministic="co").fit()


# --------------------------------------------------------------------------- forecasts
def _ma(A: np.ndarray, n: int) -> np.ndarray:
    """MA(∞) coefficients Psi_0..Psi_n of a VAR with coefficient array A (p, k, k)."""
    p, k, _ = A.shape
    psi = np.zeros((n + 1, k, k))
    psi[0] = np.eye(k)
    for i in range(1, n + 1):
        for j in range(1, min(i, p) + 1):
            psi[i] += A[j - 1] @ psi[i - j]
    return psi


def _var_path(hist: np.ndarray, A: np.ndarray, c: np.ndarray, H: int) -> np.ndarray:
    p = A.shape[0]
    buf = list(hist[-p:]) if p else []
    out = []
    for _ in range(H):
        y = c.copy()
        for j in range(p):
            y = y + A[j] @ buf[-1 - j]
        out.append(y)
        buf.append(y)
    return np.array(out)


def var_return_forecasts(res, returns: pd.DataFrame, log_level: pd.Series, target: str, origins, H: int,
                         model: str, level: float = 0.95) -> pd.DataFrame:
    """VAR fitted on RETURNS → forecast of the target's LOG LEVEL = last log level + cumulated forecast returns.

    Interval of the cumulated return: Var = sum_i C_i Σ C_i', C_i = Psi_0 + ... + Psi_i (errors add up over h).
    Parameters are fixed (train estimates); each origin only conditions on the data observed so far.
    """
    from scipy.stats import norm
    z = norm.ppf(0.5 + level / 2)
    A, c, S = res.coefs, res.intercept, res.sigma_u.to_numpy() if hasattr(res.sigma_u, "to_numpy") else res.sigma_u
    k = list(res.names).index(target)
    psi = _ma(A, H)
    C = np.cumsum(psi, axis=0)
    var_cum = np.array([sum(C[i] @ S @ C[i].T for i in range(h))[k, k] for h in range(1, H + 1)])
    R, idx, ly = returns.to_numpy(), returns.index, log_level
    out = []
    for o in origins:
        n_o = idx.get_loc(o) + 1
        steps = min(H, len(idx) - n_o)
        if steps < 1:
            continue
        path = _var_path(R[:n_o], A, c, steps)[:, k]
        mean = ly.loc[o] + np.cumsum(path)
        sd = np.sqrt(var_cum[:steps])
        for h in range(steps):
            d = idx[n_o + h]
            out.append({"date": d, "model": model, "series": target, "origin": o, "horizon": h + 1,
                        "y_true": float(np.exp(ly.loc[d])), "y_pred": float(np.exp(mean[h])),
                        "lower": float(np.exp(mean[h] - z * sd[h])), "upper": float(np.exp(mean[h] + z * sd[h]))})
    return pd.DataFrame(out, columns=FORECAST_COLUMNS)


def vecm_level_forecasts(vres, levels: pd.DataFrame, target: str, origins, H: int, model: str,
                         level: float = 0.95) -> pd.DataFrame:
    """VECM written as a VAR in LOG LEVELS (var_rep) + constant; forecasts and MSE from its MA form."""
    from scipy.stats import norm
    z = norm.ppf(0.5 + level / 2)
    A = vres.var_rep                       # (k_ar_diff + 1, k, k)
    c = np.asarray(vres.det_coef)[:, 0]    # unrestricted constant ('co')
    S = np.asarray(vres.sigma_u)
    k = list(levels.columns).index(target)
    psi = _ma(A, H)
    mse = np.array([sum(psi[i] @ S @ psi[i].T for i in range(h))[k, k] for h in range(1, H + 1)])
    Y, idx = levels.to_numpy(), levels.index
    out = []
    for o in origins:
        n_o = idx.get_loc(o) + 1
        steps = min(H, len(idx) - n_o)
        if steps < 1:
            continue
        mean = _var_path(Y[:n_o], A, c, steps)[:, k]
        sd = np.sqrt(mse[:steps])
        for h in range(steps):
            d = idx[n_o + h]
            out.append({"date": d, "model": model, "series": target, "origin": o, "horizon": h + 1,
                        "y_true": float(np.exp(Y[n_o + h, k])), "y_pred": float(np.exp(mean[h])),
                        "lower": float(np.exp(mean[h] - z * sd[h])), "upper": float(np.exp(mean[h] + z * sd[h]))})
    return pd.DataFrame(out, columns=FORECAST_COLUMNS)
