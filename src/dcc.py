"""DCC(1,1)-GARCH, two-step estimation (Engle, 2002), for a PAIR of series (Phase 7 extension).

Step 1: a univariate GARCH(1,1)-t per series (src/garch.py) gives standardised residuals z_t.
Step 2: the correlation dynamics
    Q_t = (1 - a - b) Q̄ + a z_{t-1} z_{t-1}' + b Q_{t-1},   R_t = diag(Q_t)^-1/2 Q_t diag(Q_t)^-1/2
are estimated by maximising the Gaussian correlation log-likelihood -1/2 Σ [ln|R_t| + z_t' R_t^-1 z_t - z_t' z_t].
a measures how fast the correlation reacts to joint shocks, b its persistence (a + b < 1).
Cross-checked against R rmgarch::dccfit in notebooks/r/07_dcc.Rmd.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def _ab(x):
    """Map two free reals to a, b > 0 with a + b < 1 (softmax-style), so the optimiser needs no constraints."""
    e = np.exp(x)
    s = 1 + e.sum()
    return e[0] / s, e[1] / s


def _filter(z: np.ndarray, a: float, b: float):
    n = len(z)
    Qbar = np.cov(z.T, bias=True)
    Q = Qbar.copy()
    rho = np.empty(n)
    ll = 0.0
    for t in range(n):
        if t > 0:
            Q = (1 - a - b) * Qbar + a * np.outer(z[t - 1], z[t - 1]) + b * Q
        d = np.sqrt(np.diag(Q))
        R = Q / np.outer(d, d)
        r = R[0, 1]
        rho[t] = r
        det = 1 - r ** 2
        x, y = z[t]
        quad = (x ** 2 - 2 * r * x * y + y ** 2) / det
        ll += -0.5 * (np.log(det) + quad - (x ** 2 + y ** 2))
    return ll, rho


def fit_dcc(z: pd.DataFrame) -> dict:
    """Fit DCC(1,1) on a (n, 2) frame of standardised residuals. Returns a, b, log-likelihood, rho_t (Series)."""
    zz = z.to_numpy()
    best = None
    for x0 in ([-3.0, 2.0], [-4.0, 3.0], [-2.0, 1.0]):          # a few starts: the likelihood surface can be flat
        r = minimize(lambda x: -_filter(zz, *_ab(x))[0], np.array(x0), method="Nelder-Mead",
                     options={"xatol": 1e-8, "fatol": 1e-8, "maxiter": 4000})
        if best is None or r.fun < best.fun:
            best = r
    a, b = _ab(best.x)
    ll, rho = _filter(zz, a, b)
    return {"a": float(a), "b": float(b), "a+b": float(a + b), "loglik": float(ll), "converged": bool(best.success),
            "rho": pd.Series(rho, index=z.index)}
