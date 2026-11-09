"""Download, align and feature-engineer the project dataset.

Pipeline: download_raw -> load_raw -> align_prices -> build_features -> build_indices
-> set_trading_freq -> save_panel. Every later notebook only calls load_panel().
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .config import ROOT, load_config, path

RAW_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"]
PRICE_FIELDS = {"Open": "open", "High": "high", "Low": "low", "Close": "close",
                "Adj Close": "adj_close", "Volume": "volume"}


# --------------------------------------------------------------------------- download
def download_raw(force: bool = False) -> pd.DataFrame:
    """Download one CSV per ticker into data/raw/ (skipped if the file already exists).

    auto_adjust=False on purpose: we keep BOTH the split-adjusted `Close` and the
    split+dividend-adjusted `Adj Close` so the provider adjustment stays visible.
    """
    import yfinance as yf

    cfg = load_config()
    raw_dir = path("raw")
    # yfinance's `end` is exclusive -> add one day so the frozen end date is included.
    end_excl = (pd.Timestamp(cfg["dates"]["end"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    log_file = raw_dir / "_download_log.json"
    log = json.loads(log_file.read_text()) if log_file.exists() else {}

    rows = []
    for a in cfg["assets"]:
        f = raw_dir / f"{a['column']}.csv"
        if f.exists() and not force:
            rows.append({"ticker": a["ticker"], "file": f.name, "status": "cached"})
            continue
        df = yf.download(a["ticker"], start=cfg["dates"]["download_start"], end=end_excl,
                         auto_adjust=False, actions=True, progress=False,
                         multi_level_index=False)
        if df.empty:
            raise RuntimeError(f"No data returned for {a['ticker']}")
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        df.index.name = "Date"
        df = df.reindex(columns=RAW_COLUMNS)
        df.to_csv(f, float_format="%.10g")
        log[a["ticker"]] = {"file": f.name,
                            "downloaded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                            "yfinance": yf.__version__, "rows": len(df),
                            "first": str(df.index.min().date()), "last": str(df.index.max().date())}
        rows.append({"ticker": a["ticker"], "file": f.name, "status": "downloaded"})
    log_file.write_text(json.dumps(log, indent=2))
    return pd.DataFrame(rows)


def load_raw() -> dict[str, pd.DataFrame]:
    """Read every raw CSV (the only source of truth after the download)."""
    cfg = load_config()
    raw_dir = path("raw")
    out = {}
    for a in cfg["assets"]:
        df = pd.read_csv(raw_dir / f"{a['column']}.csv", index_col="Date", parse_dates=True)
        out[a["column"]] = df.sort_index()
    return out


def raw_overview(raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per ticker: coverage, data-quality flags and provider actions inside the study window."""
    cfg = load_config()
    start, end = pd.Timestamp(cfg["dates"]["start"]), pd.Timestamp(cfg["dates"]["end"])
    rows = []
    for col, df in raw.items():
        w = df.loc[start:end]
        rows.append({
            "asset": col,
            "raw_first": df.index.min().date(), "raw_last": df.index.max().date(),
            "raw_rows": len(df), "window_rows": len(w),
            "duplicate_dates": int(df.index.duplicated().sum()),
            "nan_adj_close": int(w["Adj Close"].isna().sum()),
            "non_positive_price": int((w[["Open", "High", "Low", "Close", "Adj Close"]] <= 0).any(axis=1).sum()),
            "zero_volume_days": int((w["Volume"] == 0).sum()),
            "dividend_events": int((w["Dividends"].fillna(0) != 0).sum()),
            "split_events": int((w["Stock Splits"].fillna(0) != 0).sum()),
        })
    return pd.DataFrame(rows).set_index("asset")


# --------------------------------------------------------------------------- alignment
def trading_days(raw: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    """US stock trading days inside the study window = union of the stocks' dates.

    Why the union of stocks (not BTC): BTC trades 7/7, stocks 5/7; the stock calendar
    is the binding one for every joint model (VAR/VECM need simultaneous observations).
    """
    cfg = load_config()
    start, end = pd.Timestamp(cfg["dates"]["start"]), pd.Timestamp(cfg["dates"]["end"])
    stocks = [a["column"] for a in cfg["assets"] if a["ticker"] != "BTC-USD"]
    idx = pd.DatetimeIndex([])
    for c in stocks:
        idx = idx.union(raw[c].dropna(subset=["Adj Close"]).index)
    return idx[(idx >= start) & (idx <= end)]


def align_prices(raw: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Put all assets on the stock trading calendar.

    Returns (wide price panel, missing-value report). Missing prices on a trading day
    are forward-filled (last known price = no trade information), volume set to 0,
    and every fill is counted in the report.
    """
    days = trading_days(raw)
    frames, report = [], []
    for col, df in raw.items():
        sub = df.reindex(days)[list(PRICE_FIELDS)].rename(columns=PRICE_FIELDS)
        # Provider placeholder rows (volume 0 and High == Low) are not real sessions: treat them as missing.
        stale = (sub["volume"] == 0) & (sub["high"] == sub["low"])
        sub.loc[stale, :] = np.nan
        n_missing = int(sub["adj_close"].isna().sum())
        missing_dates = [d.strftime("%Y-%m-%d") for d in sub.index[sub["adj_close"].isna()]]
        price_cols = ["open", "high", "low", "close", "adj_close"]
        sub[price_cols] = sub[price_cols].ffill()
        sub["volume"] = sub["volume"].fillna(0).astype("int64")  # share counts are integers in CSV and Parquet alike
        report.append({"asset": col, "trading_days": len(days), "stale_rows": int(stale.sum()),
                       "missing_before_fill": n_missing,
                       "missing_after_fill": int(sub["adj_close"].isna().sum()),
                       "missing_dates": ", ".join(missing_dates) if missing_dates else ""})
        sub.columns = [f"{col}_{c}" for c in sub.columns]
        frames.append(sub)
    panel = pd.concat(frames, axis=1)
    panel.index.name = "Date"
    return panel, pd.DataFrame(report).set_index("asset")


# --------------------------------------------------------------------------- features
def _add_features(panel: pd.DataFrame, name: str, price: pd.Series, log_ret: pd.Series) -> dict:
    """Derived indicators shared by single assets and indices."""
    f = load_config()["features"]
    out = {
        f"{name}_log_price": np.log(price),
        f"{name}_log_return": log_ret,
        f"{name}_rv{f['vol_window']}": log_ret.rolling(f["vol_window"]).std() * np.sqrt(f["annualisation"]),
    }
    for w in f["ma_windows"]:
        out[f"{name}_ma{w}"] = price.rolling(w).mean()
    return out


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Add log price, log return, realised volatility and moving averages per asset."""
    cols = {}
    for a in load_config()["assets"]:
        price = panel[f"{a['column']}_adj_close"]
        cols.update(_add_features(panel, a["column"], price, np.log(price).diff()))
    return pd.concat([panel, pd.DataFrame(cols, index=panel.index)], axis=1)


def build_indices(panel: pd.DataFrame) -> pd.DataFrame:
    """Equal-weighted group indices from member log returns, rebased to 100 on day 1.

    Index log return = mean of the members' log returns (daily rebalanced, equal weights).
    Level = 100 * exp(cumulative sum of that return).
    """
    cols = {}
    for name, members in load_config()["indices"].items():
        ret = panel[[f"{m}_log_return" for m in members]].mean(axis=1, skipna=False)
        level = 100 * np.exp(ret.fillna(0).cumsum())
        cols[f"{name}_level"] = level
        cols.update(_add_features(panel, name, level, ret))
    return pd.concat([panel, pd.DataFrame(cols, index=panel.index)], axis=1)


# --------------------------------------------------------------------------- frequency & IO
def trading_freq(index: pd.DatetimeIndex) -> pd.offsets.CustomBusinessDay:
    """Business-day frequency whose holidays are the weekdays the market was closed.

    Why: pandas 'B' would invent rows on exchange holidays; this CustomBusinessDay
    declares a regular frequency that matches the trading calendar exactly.
    """
    all_bdays = pd.bdate_range(index.min(), index.max())
    return pd.offsets.CustomBusinessDay(holidays=all_bdays.difference(index))


def set_trading_freq(df: pd.DataFrame) -> pd.DataFrame:
    """Attach the trading-day frequency to the DatetimeIndex (validated by pandas)."""
    df = df.copy()
    df.index = pd.DatetimeIndex(df.index, freq=trading_freq(df.index), name="Date")
    return df


def market_holidays(index: pd.DatetimeIndex) -> list[str]:
    """Weekdays inside the window without trading (exchange holidays and special closures)."""
    return [str(d)[:10] for d in trading_freq(index).holidays]


def save_panel(panel: pd.DataFrame) -> dict:
    """Save CSV (read by R and humans) and Parquet (fast, typed) with identical content."""
    out = path("processed")
    panel.to_csv(out / "panel.csv", date_format="%Y-%m-%d", float_format="%.17g")
    panel.to_parquet(out / "panel.parquet")
    return {"csv": out / "panel.csv", "parquet": out / "panel.parquet"}


def load_panel(fmt: str = "parquet") -> pd.DataFrame:
    """Entry point for every notebook: processed panel with its trading-day frequency."""
    out = path("processed")
    if fmt == "parquet":
        df = pd.read_parquet(out / "panel.parquet")
    else:
        df = pd.read_csv(out / "panel.csv", index_col="Date", parse_dates=True)
    return set_trading_freq(df)


def chrono_split(df: pd.DataFrame, train_frac: float | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chronological (never random) train/test split."""
    frac = load_config()["split"]["train_frac"] if train_frac is None else train_frac
    n_train = int(np.floor(len(df) * frac))
    return df.iloc[:n_train], df.iloc[n_train:]


def summary_stats(panel: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Small numeric fingerprint used to prove Python and R read identical data."""
    s = panel[columns].agg(["count", "mean", "std", "min", "max"]).T
    s.index.name = "column"
    return s
