# Progress log

## Phase 1: Architecture + data + README ✅ (2026-11-09)

### Status
- [x] Brief read and mapped to phases (README roadmap)
- [x] Project structure, `config.yaml`, pinned `requirements.txt`, `.gitignore`
- [x] Raw download, 8 tickers → `data/raw/*.csv` (frozen; downloaded 2026-11-09, yfinance 1.8.0)
- [x] Alignment, features, CONVERTS/PURE indices → `data/processed/panel.csv` + `.parquet`
- [x] 90/10 chronological split written into `config.yaml`
- [x] Sanity figures: `figures/fig_01_rebased_prices_by_group.png`, `figures/fig_01_indices_vs_references.png`
- [x] `notebooks/python/01_data.ipynb` runs top-to-bottom from a fresh kernel without errors
- [x] `notebooks/r/01_data.Rmd` knits without errors (R 4.6.2); R and Python statistics match (max relative difference 4.3e-16)
- [x] `data/DATA_DICTIONARY.md`, `README.md`, this file

### Key facts
| | |
|---|---|
| Period | 2021-12-14 → 2026-10-30 (frozen end 2026-10-31 is a Saturday) = 4.88 years |
| Observations | 1,225 US trading days × 100 columns (49 weekday market closures in the window) |
| Train | 1,102 rows, 2021-12-14 → 2026-05-06 |
| Test | 123 rows, 2026-05-07 → 2026-10-30 |
| Index frequency | pandas `CustomBusinessDay` (Mon–Fri minus market closures); R `xts`, daily periodicity |
| Missing values | 0 after alignment; 1 provider placeholder row (CLSK 2024-11-08) forward-filled |

### Data issues found
1. **Shell-company history.** `yfinance` returns WULF data back to 1994 (IKONICS) and CIFR back to 2020 (Good Works SPAC). Excluded: the window starts at TeraWulf's first session (2021-12-14).
2. **Window < 5 years** (4.88 y) because of (1) and IREN's IPO (2021-11-17). Justified in DATA_DICTIONARY.md.
3. **CLSK 2024-11-08**: a Yahoo placeholder row (volume 0, OHLC = previous close). Treated as missing and forward-filled.
4. **WULF $5 "dividend" on 2021-12-14**: the merger cash distribution. It only adjusts pre-window prices, so the panel is unaffected.
5. **NVDA 10:1 split (2024-06-10) and 19 dividends**: absorbed by `Adj Close`.
6. **BTC/stock close timing**: BTC's daily close is 24:00 UTC, stocks close at 20:00–21:00 UTC, about 3–4 h apart. Matters for same-day lead/lag interpretation.

### Decisions and why
| Decision | Why |
|---|---|
| Option A: keep IREN/CIFR/WULF, accept 4.88 years (chosen by the student) | They are the most representative AI converts; swapping them for older tickers (BTBT, HUT) would weaken the research question. 1,225 obs are enough for all methods |
| Stock trading days only; BTC sampled on them | Joint models need simultaneous observations; filling weekends would create fake zero returns |
| `Adj Close` everywhere; `auto_adjust=False` at download | Keeps both the split-only `Close` and the split+dividend `Adj Close`, so the provider adjustment is documented |
| Raw files frozen, download only if missing | Yahoo back-adjusts and revises history; re-downloading would silently change results |
| Equal-weighted indices from log returns, rebased to 100 | Reduces single-stock noise; individual tickers kept for robustness |
| No pre-window data for rolling-feature warm-up | Pre-window rows of WULF/CIFR belong to other companies |
| Split by row count (floor 90 %) | Brief §1.3; dates stored in `config.yaml` so Python and R share the same test set |
| `pivot_date: null` | To be chosen with evidence (EDA / break tests), not imposed in Phase 1 |

### Open questions
- **Deadline.** The brief says 12 Oct 2026, but the data end on 2026-10-31. Confirm the actual submission date with the teacher.
- **"Basket of 2–3 assets"** (brief §1.1). We model 4 series (CONVERTS, PURE, BTC, NVDA). Explain in the report that the indices are the modelled series.
- **Pivot date** for the converts (e.g. first major HPC contract). Needed for the before/after comparison and for break tests.
- **Test window (123 days) vs forecast horizon h = 5–10.** Decide in Phase 7 between a single origin and rolling origins over the test set.

### Environment
Python 3.11.9 (`.venv`, see `requirements.txt`). R 4.6.2 + pandoc 3.13 (installed with winget on 2026-11-09). R packages are listed by `R/install_packages.R`.

---

## Next: Phase 2 — EDA (`notebooks/python/02_eda.ipynb`)
Plots, ACF/PACF (raw and differenced) with a written reading, STL decomposition, outlier detection and treatment, ADF + KPSS, and the differencing order.
