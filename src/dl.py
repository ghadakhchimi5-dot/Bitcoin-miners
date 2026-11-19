"""Deep-learning helpers (Phase 6, PyTorch, Python only): windows, LSTM/GRU, training with early stopping,
walk-forward validation, rolling-origin forecasts in the common format.

Multi-step scheme: DIRECT multi-output. One network outputs the next H returns at once.
Why not recursive: the inputs include BTC and NVDA returns, which are unknown in the future; a recursive
forecast would need a second model for them and would accumulate its own errors.
"""
from __future__ import annotations

import copy
import os
import random

import numpy as np
import pandas as pd
import torch
from torch import nn

from .arima import FORECAST_COLUMNS


def set_torch_seed(seed: int) -> None:
    """Fix every random source and force deterministic kernels (results identical run after run on CPU)."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)   # multi-threaded reductions can change the order of float additions


def make_windows(F: np.ndarray, target: np.ndarray, w: int, H: int, ends: np.ndarray):
    """X[i] = F[e-w+1 .. e] (w days of features), Y[i] = target[e+1 .. e+H] (next H returns), for each window end e."""
    X = np.stack([F[e - w + 1: e + 1] for e in ends]).astype(np.float32)
    Y = np.stack([target[e + 1: e + 1 + H] for e in ends]).astype(np.float32)
    return X, Y


class RNN(nn.Module):
    """One recurrent layer (LSTM or GRU) -> dropout -> linear layer giving H outputs (the next H scaled returns)."""

    def __init__(self, kind: str, n_in: int, hidden: int, H: int, dropout: float, layers: int = 1):
        super().__init__()
        cell = nn.LSTM if kind == "lstm" else nn.GRU
        self.rnn = cell(n_in, hidden, num_layers=layers, batch_first=True, dropout=dropout if layers > 1 else 0.0)
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(hidden, H)

    def forward(self, x):
        out, _ = self.rnn(x)
        return self.head(self.drop(out[:, -1, :]))   # last hidden state summarises the window


def train_model(kind, Xtr, Ytr, Xva, Yva, hidden=32, dropout=0.2, lr=1e-3, batch=64, epochs=150, patience=15, seed=42):
    """Adam + MSE, early stopping on the validation loss (best weights restored). Returns (model, history)."""
    set_torch_seed(seed)
    model = RNN(kind, Xtr.shape[2], hidden, Ytr.shape[1], dropout)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    Xt, Yt, Xv, Yv = map(torch.from_numpy, (Xtr, Ytr, Xva, Yva))
    g = torch.Generator().manual_seed(seed)
    best, best_state, wait, hist = np.inf, None, 0, []
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(len(Xt), generator=g)
        tot = 0.0
        for i in range(0, len(Xt), batch):
            b = perm[i:i + batch]
            opt.zero_grad()
            loss = loss_fn(model(Xt[b]), Yt[b])
            loss.backward()
            opt.step()
            tot += loss.item() * len(b)
        model.eval()
        with torch.no_grad():
            vl = loss_fn(model(Xv), Yv).item()
        hist.append({"epoch": ep + 1, "train_loss": tot / len(Xt), "val_loss": vl})
        if vl < best - 1e-6:
            best, best_state, wait = vl, copy.deepcopy(model.state_dict()), 0
        else:
            wait += 1
            if wait >= patience:
                break
    model.load_state_dict(best_state)
    return model, pd.DataFrame(hist)


def predict(model, X: np.ndarray) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        return model(torch.from_numpy(X.astype(np.float32))).numpy()


def split_train_val(ends: np.ndarray, val_frac: float = 0.15, gap: int = 10):
    """Chronological split of window ends; `gap` samples are dropped between the two parts because their
    10-day targets would overlap the validation period (purging, no look-ahead)."""
    n_val = int(len(ends) * val_frac)
    return ends[: len(ends) - n_val - gap], ends[len(ends) - n_val:]


def cum_errors(Y_true_ret: np.ndarray, Y_pred_ret: np.ndarray) -> np.ndarray:
    """Error on the LOG LEVEL at each horizon = cumulative sum of the return errors (n, H)."""
    return np.cumsum(Y_true_ret, axis=1) - np.cumsum(Y_pred_ret, axis=1)


def rolling_level_forecasts(pred_ret: np.ndarray, log_level: pd.Series, origins, H: int, model: str, series: str,
                            q_lo: np.ndarray, q_hi: np.ndarray) -> pd.DataFrame:
    """Turn predicted returns (one row per origin) into level forecasts in the common format.

    Intervals: empirical 2.5 % / 97.5 % quantiles of the validation log-level errors at each horizon
    (networks give no analytic interval; validation errors are the honest substitute).
    """
    idx, ly = log_level.index, log_level
    out = []
    for i, o in enumerate(origins):
        n_o = idx.get_loc(o) + 1
        path = ly.loc[o] + np.cumsum(pred_ret[i])
        for h in range(min(H, len(idx) - n_o)):
            d = idx[n_o + h]
            out.append({"date": d, "model": model, "series": series, "origin": o, "horizon": h + 1,
                        "y_true": float(np.exp(ly.loc[d])), "y_pred": float(np.exp(path[h])),
                        "lower": float(np.exp(path[h] + q_lo[h])), "upper": float(np.exp(path[h] + q_hi[h]))})
    return pd.DataFrame(out, columns=FORECAST_COLUMNS)
