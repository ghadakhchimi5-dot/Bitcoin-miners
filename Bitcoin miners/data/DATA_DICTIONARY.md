# Data dictionary

## Source

| Item | Value |
|---|---|
| Provider | Yahoo Finance, accessed with the Python package `yfinance` 1.8.0 |
| Download date | 2026-11-09 (UTC timestamps per ticker in `data/raw/_download_log.json`) |
| Download call | `yf.download(ticker, start="2021-01-01", end="2026-11-01", auto_adjust=False, actions=True)` |
| Frequency | Daily |
| Study period | **2021-12-14 → 2026-10-30** (the frozen end date 2026-10-31 is a Saturday; the last stock session is 2026-10-30) |
| Observations | **1,225 trading days** × 100 columns |
| Produced by | `notebooks/python/01_data.ipynb` using `src/data.py` |

## Assets

| Column prefix | Yahoo symbol | Company / asset | Group |
|---|---|---|---|
| `IREN` | IREN | IREN Ltd (ex-Iris Energy) | AI converts |
| `CIFR` | CIFR | Cipher Mining | AI converts |
| `WULF` | WULF | TeraWulf | AI converts |
| `MARA` | MARA | MARA Holdings | Pure miners |
| `CLSK` | CLSK | CleanSpark | Pure miners |
| `RIOT` | RIOT | Riot Platforms | Pure miners |
| `BTC` | BTC-USD | Bitcoin in US dollars | Reference (Bitcoin factor) |
| `NVDA` | NVDA | NVIDIA | Reference (AI factor) |

## Files

| File | Content |
|---|---|
| `data/raw/<PREFIX>.csv` | Untouched Yahoo download, 2021-01-01 → 2026-10-31: `Date, Open, High, Low, Close, Adj Close, Volume, Dividends, Stock Splits` |
| `data/raw/_download_log.json` | Download timestamp, yfinance version, rows, first/last date per ticker |
| `data/processed/panel.csv` | Aligned panel (dates `YYYY-MM-DD`, full float precision). Read by R and Python |
| `data/processed/panel.parquet` | Same content, typed (Python) |

Load it in Python with `src.data.load_panel()` (it restores the trading-day frequency) and in R with `load_panel()` from `R/load_data.R` (returns `xts`).

## Columns of `panel.csv`

Index: `Date`, a US stock trading day. Python declares a `CustomBusinessDay` frequency: Monday–Friday minus the 49 weekdays without trading in the window (exchange holidays and special closures).

### Per asset (`<P>` = IREN, CIFR, WULF, MARA, CLSK, RIOT, BTC, NVDA): 11 columns × 8 = 88

| Column | Definition | Unit |
|---|---|---|
| `<P>_open`, `<P>_high`, `<P>_low` | Session open / high / low, adjusted for splits | USD |
| `<P>_close` | Close, adjusted for **splits only** (Yahoo `Close`) | USD |
| `<P>_adj_close` | Close adjusted for **splits and dividends** (Yahoo `Adj Close`). **Used by every analysis** | USD |
| `<P>_volume` | Shares traded (BTC: USD volume reported by Yahoo) | shares (BTC: USD) |
| `<P>_log_price` | ln(`adj_close`) | log USD |
| `<P>_log_return` | ln(adj_close_t / adj_close_{t-1}); NaN on the first day | decimal (0.01 = 1 %) |
| `<P>_rv20` | Realised volatility: 20-day rolling standard deviation of `log_return` × √252 | annualised decimal (0.80 = 80 %) |
| `<P>_ma20`, `<P>_ma50` | 20- and 50-day simple moving averages of `adj_close` | USD |

### Group indices (`<I>` = CONVERTS, PURE): 6 columns × 2 = 12

| Column | Definition | Unit |
|---|---|---|
| `<I>_log_return` | Equal-weighted mean of the members' `log_return` (CONVERTS = IREN, CIFR, WULF; PURE = MARA, CLSK, RIOT) | decimal |
| `<I>_level` | 100 × exp(cumulative sum of `<I>_log_return`); equals 100 on 2021-12-14 | index points |
| `<I>_log_price` | ln(`level`) | log points |
| `<I>_rv20`, `<I>_ma20`, `<I>_ma50` | Same definitions as for single assets, applied to `level` | as above |

**Why indices:** a single small-cap miner is dominated by firm-specific news (contracts, equity dilution, outages). Averaging three firms with the same business model reduces that noise, so the comparison "converts vs pure miners" reflects the business model. The individual tickers stay in the panel for robustness checks.

## Provider adjustments (brief §1.3)

* `Adj Close` is Yahoo's split-and-dividend-adjusted price. It is back-adjusted, so its past values can change when a new dividend or split happens. This is why the raw files are frozen and never downloaded again automatically.
* Events inside the study window:
  * **NVDA**: 10-for-1 split on 2024-06-10 and 19 quarterly dividends, all absorbed in `Adj Close` (`open/high/low/close` are split-adjusted too).
  * **WULF**: a $5.00 "dividend" on 2021-12-14. This is the cash distribution to IKONICS shareholders at the reverse merger. Yahoo applies it to prices **before** 2021-12-14 only, i.e. outside the window, so it has no effect on the panel.
  * The other miners: no split or dividend in the window.
* BTC-USD is a 24/7 market. Yahoo's daily BTC bar covers the UTC calendar day, so its "close" is the price at the end of that day (24:00 UTC). US stocks close at 16:00 New York time (20:00–21:00 UTC), so the two closes on the same date are taken about 3–4 hours apart. This non-synchronicity must be kept in mind when interpreting same-day lead/lag effects (Granger, VAR).

## Study window and why it starts on 2021-12-14

The raw files start on 2021-01-01, but the panel starts on 2021-12-14:

* **WULF**: rows before 2021-12-14 are IKONICS Corp. The reverse merger with TeraWulf closed on 2021-12-13, and volume jumps from ~50k to 353k shares on 2021-12-14.
* **CIFR**: rows before late Aug 2021 are the Good Works Acquisition SPAC (trading near $10).
* **IREN**: IPO on 2021-11-17.

The window is therefore **4.88 years**, slightly below the brief's 5 years. Justification: the AI pivot only exists for miners listed from 2021, the two most representative converts cannot have a longer history, and 1,225 daily observations are enough for every method of the brief. *(Decision taken with the student: option A.)*

## Alignment rule

* Calendar = **US stock trading days only** (union of the seven stocks' dates). BTC-USD is sampled on those days, so its weekend prices are dropped.
* Why: joint models (VAR, VECM, Granger, cointegration) need observations taken at the same time. Filling stocks on weekends would create artificial zero returns.
* Consequence: a Monday BTC `log_return` covers Friday → Monday (three calendar days of Bitcoin trading).

## Missing values and anomalies

| Issue | Where | Treatment |
|---|---|---|
| Provider placeholder row (volume = 0, Open = High = Low = Close = previous close) | CLSK, 2024-11-08 (the stock did trade that day) | Treated as missing, then price forward-filled (return 0 that day, the move is booked on 2024-11-11), volume set to 0 |
| Missing price on a trading day | None after alignment (0 for all 8 assets) | The rule would be: forward-fill prices, volume 0, logged in the notebook |
| Duplicated dates, non-positive prices | None | — |
| Rolling-window warm-up | First row of `log_return`; first 19 rows of `ma20`; first 20 of `rv20`; first 49 of `ma50` | Left as NaN on purpose. Pre-window data is not used because for WULF and CIFR it belongs to shell companies |

## Train / test split

Chronological 90 / 10 split on rows (stored in `config.yaml`, written by notebook 01):

| Set | Rows | Start | End |
|---|---|---|---|
| Train | 1,102 | 2021-12-14 | 2026-05-06 |
| Test | 123 | 2026-05-07 | 2026-10-30 |
