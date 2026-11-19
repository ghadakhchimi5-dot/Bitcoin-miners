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

## Phase 2: EDA, stationarity, pivot date ✅ (2026-11-12)

### Status
- [x] `notebooks/python/02_eda.ipynb` runs top-to-bottom from a fresh kernel (0 errors); markdown commentary in French
- [x] New helpers: `src/eda.py` (ADF+KPSS, STL strength, weekday test, Hampel, rolling IQR, rolling corr, rolling Engle-Granger, Chow test/scan, Bai-Perron via `ruptures`, regime betas); `config.update_pivot`; `plotting.CORE` colours
- [x] Figures `fig_02_01` … `fig_02_13`; tables `results/02_*.csv` (descriptive stats, Ljung-Box, STL, weekday, outliers, ADF/KPSS, integration order, rolling corr, rolling EG, Bai-Perron, Chow scan, Chow at candidates, regime betas)
- [x] `pivot_date: "2025-01-22"` written to `config.yaml` after the student's OK
- [x] `requirements.txt`: statsmodels 0.15.0, scipy 1.17.1, ruptures 1.1.10

### Key results (all from executed output)
| Topic | Result |
|---|---|
| Scale | daily std of returns: CONVERTS 0.063, PURE 0.058, BTC 0.032, NVDA 0.032 (annualised ≈ 100 % vs ≈ 51 %) |
| Tails | excess kurtosis: BTC 6.51, NVDA 3.93, CONVERTS 0.95, PURE 0.59 (averaging 3 stocks thins the tails) |
| ADF / KPSS | all 4 core series: log price non-stationary (ADF p 0.08–0.61, KPSS p ≤ 0.01), returns stationary (ADF p < 0.001, KPSS p ≥ 0.10) → **d = 1** for all. WULF, RIOT levels "ambiguous" (ADF p 0.037 / 0.034 vs trend-stationary, KPSS rejects) → d = 1 kept |
| ACF returns | no structure; Ljung-Box not rejected for CONVERTS (p 0.37/0.24/0.57 at 5/10/20), PURE, BTC; NVDA rejected only at lag 5 (p 0.0385) → expected ARIMA(0,1,0) for CONVERTS |
| Squared returns | Ljung-Box rejects for PURE (p ≤ 0.0027), BTC (0.0036 at 5), NVDA (0.0128 at 5); **not for CONVERTS** (p 0.50/0.85/0.85) — recheck with ARCH-LM in Phase 3 |
| Seasonality | STL s=5: F_S ≤ 0.03, seasonal ≤ 0.27 % of variance; s=252: F_S = 0 (CONVERTS, PURE), 0.04 BTC, 0.11 NVDA; weekday ANOVA p 0.26–0.61, Kruskal p ≥ 0.09 → **no seasonality, no SARIMA** |
| Outliers | Hampel(21, 4σ) ∪ rolling IQR(63, k=3): CONVERTS 12, PURE 11, BTC 26, NVDA 7 days; **kept** (real events). DeepSeek day 2025-01-27: CONVERTS −0.30 log, NVDA −0.19, PURE −0.12 |
| Rolling corr 120d | CONVERTS–PURE gap with BTC: −0.10 (Jun 2025) → −0.31 (Dec 2025); NVDA correlation moves together for both groups (not converts-specific) |
| Rolling EG (250d) | p < 0.05 in only 3.6 % of windows CONVERTS–BTC, **0.5 % PURE–BTC**, 9.7 % CONVERTS–NVDA → no discrimination; H1 looks fragile |
| Breaks | full sample: BIC 0 breaks CONVERTS~BTC; 1 break 2022-09-27 for CONVERTS~BTC+NVDA (early listing regime). After it: sup-F 8.63 at **2025-01-22** for CONVERTS~BTC+NVDA, PURE Chow p = 0.15 there; without DeepSeek day F = 6.52, p = 0.0002 |
| Betas at pivot | CONVERTS β_BTC 1.03 → 0.71, β_NVDA 0.31 → 0.87; PURE β_BTC 1.15 → 1.01, β_NVDA 0.32 → 0.49 |
| Split | train 1,102 (→ 2026-05-06): 778 pre-pivot / 324 post-pivot; test 123 entirely post-pivot |

### Decisions and why
| Decision | Why |
|---|---|
| Pivot = 2025-01-22 (candidate B), validated by the student | only break specific to CONVERTS (control PURE not breaking), direction matches H2, robust to DeepSeek day, enough post-pivot data |
| Keep 2024-02-27 (A, spread break) and 2025-08-13 (C, correlation/level split) as robustness dates | evidence is moderate; results of Phase 4 must not hinge on one date |
| Outliers kept, no winsorising | real market events; winsorising would bias volatility/GARCH; some carry the pivot information. Dummies only as a Phase 3 robustness check |
| ADF with trend for levels, constant for returns; KPSS same | prices may drift, returns cannot |
| No SARIMA | no weekly or annual seasonality (STL strength and weekday tests) |

### Open questions
- Chow p-values are naive (date found by scanning). Optional: compute Andrews sup-F critical values / `strucchange::sctest` in R for a proper p-value.
- The transition looks gradual (betas change early 2025, correlations and levels split from Aug 2025). Discuss in report.
- H1 (pure miners cointegrated with BTC) is not supported on 1-year windows — test on full sample in Phase 4 and report honestly.
- CONVERTS squared returns show no autocorrelation although realised vol clusters visibly — ARCH-LM in Phase 3/5.
- Test set (123 days) is entirely post-pivot and ends with a sharp CONVERTS drop.

---

## Phase 3: ARIMA / SARIMA, Python + R ✅ (2026-11-12)

### Status
- [x] `notebooks/python/03_arima.ipynb` runs top-to-bottom from a fresh kernel (0 errors, 0 warnings)
- [x] `notebooks/r/03_arima.Rmd` knits (R 4.6.2, forecast 9.0.2); it READS Python's outputs, so run the Python notebook first
- [x] Helpers: `src/arima.py` (order grid, residual diagnostics, ARCH-LM, rolling-origin forecasts, quick scores), `R/arima_helpers.R`
- [x] `results/forecasts_arima.csv` (common format), `results/03_*.csv`, `figures/fig_03_01` … `fig_03_06`
- [x] `pmdarima==2.1.1` pinned. R: `nsdiffs(test="ch")` needs package `uroot` → used OCSB + "seas" in R instead (Python has OCSB + CH)

### Common forecast format (decided here, used by every later model)
`date, model, series, origin, horizon, y_true, y_pred, lower, upper`
- `y_*` on the **index level** (points), not log; level forecast = exp(log forecast) = median; bounds = exp(log bounds), 95 %.
- **Rolling origins, parameters fixed from train** (`res.apply`, no refit): origins = last train day + every test day except the last (123), horizons 1..10 → 119 errors at h = 5, 114 at h = 10. Resolves the Phase 1 open question (single vs rolling origins).

### Key results
| Topic | Result |
|---|---|
| Chosen model | **ARIMA(0,1,0) without drift** for CONVERTS and PURE (= random walk). Manual, BIC and auto_arima/auto.arima with d = 1 agree |
| AIC grid CONVERTS | (0,1,1) best by AIC but ΔAIC(0,1,0) = 0.37 only; BIC prefers (0,1,0) by 4.63; MA coef 0.047 (se 0.030), not significant |
| Free d | auto_arima → (5,2,1) Python / (5,2,0) R: pmdarima/forecast KPSS asks d = 2 for CONVERTS (ADF, PP say 1) → over-differencing, rejected |
| Seasonality | D = 0 (OCSB, CH/seas); seasonal AR/MA LR p = 0.076 / 0.070 / 0.19 (CONVERTS); BIC worse → **no SARIMA** |
| Ljung-Box residuals | CONVERTS p = 0.32 / 0.35 / 0.81 (5/10/20); PURE p = 0.30 / 0.18 / 0.43 → white noise |
| Normality | rejected (CONVERTS JB 43.8, SW p 1.8e-5); with 11 outlier dummies JB 0.8 (p 0.68), order unchanged (0,0,0 on returns) |
| **ARCH-LM** | **CONVERTS not rejected** (p 0.61 lag 5, 0.92 lag 10; also not pre-pivot p 0.30, not post-pivot p 0.76); **PURE rejected** (p 0.0057 / 0.0047) |
| Forecast preview CONVERTS | rw RMSE 28.77 (h5) / 36.10 (h10), MAE 23.47 / 28.27, MAPE 10.5 % / 13.6 %, 95 % coverage 96.6 % / 98.2 %; arima_011 slightly worse (28.85 / 36.15) |
| Forecast preview PURE | rw RMSE 7.24 / 10.01; arima_011 identical to 2 decimals |
| Python vs R | same orders; coef rel. diff ≤ 0.015 (MA), σ² ≤ 0.0011; loglik diff ≤ 0.00019; first-origin forecast rel. diff ≤ 5.5e-5, bounds ≤ 2.4e-4 |

### Decisions and why
| Decision | Why |
|---|---|
| ARIMA(0,1,0), no drift | parsimony + BIC + auto search agree; extra MA term not significant and does not help out of sample |
| Keep `arima_011` in the forecast file | a genuine competitor for Diebold-Mariano; `rw` IS the chosen ARIMA, so no duplicate "arima_010" row |
| d = 1 imposed in auto search | Phase 2 ADF+KPSS evidence; d = 2 is over-differencing |
| No dummies in the main model | outliers are real events (Phase 2 decision); dummies only as robustness |

### Open questions
- **CONVERTS shows no ARCH effect** on train (all sub-periods) while PURE does. Phase 5 must still fit GARCH (brief) but report this honestly; check ARCH-LM on the full sample and on individual converts (IREN, CIFR, WULF).
- Coverage ≥ 95 % is computed on overlapping origins (not independent).
- R notebooks depend on Python outputs (run order: Python then R) — state it in the README / report.

---

## Phase 4: VAR, Granger, Johansen, VECM, Python + R ✅ (2026-11-12)

### Status
- [x] `notebooks/python/04_var_vecm.ipynb` runs top-to-bottom (0 errors, 0 warnings); `notebooks/r/04_var_vecm.Rmd` knits (reads Python's CSVs → run Python first)
- [x] Helpers: `src/multivariate.py` (lag table, VAR diagnostics, pairwise Granger, IRF with bands, Johansen pair, Engle-Granger, half-life, VECM, VAR/VECM rolling forecasts — checked equal to statsmodels `forecast`/`predict`), `R/var_helpers.R`
- [x] `results/04_*.csv`, `results/forecasts_var.csv` (var1, var1_post), `results/forecasts_vecm.csv` (vecm_nvda), `figures/fig_04_01..03`

### Data-use decision
Inference pre/post pivot (VAR, Granger, IRF, Johansen) uses ALL observations of each regime (full 1,224 returns; pre 777; post 447 incl. test days) — it is description, not forecasting. Forecast models are fitted on TRAIN only. Robustness: post-pivot on train only (324) and alternative pivots A / C.

### Key results
| Topic | Result |
|---|---|
| VAR order | AIC = BIC = HQ = FPE → **p = 0** in all 3 periods; VAR(1) used as the minimum for Granger. Stable (max modulus 0.085 / 0.086 / 0.137), Portmanteau p 0.74 / 0.60 / 0.79, JB rejected, ARCH per equation rejected for BTC/NVDA/PURE, not CONVERTS (R multivariate ARCH: rejected everywhere) |
| Granger | 3 rejections out of 24 at 5 % (CONVERTS→NVDA full 0.040; PURE→BTC pre 0.035; NVDA→PURE post 0.016), none robust. BTC→CONVERTS p 0.55 / 0.77 / 0.091; NVDA→CONVERTS 0.94 / 0.47 / 0.12 → **no lead-lag, link is same-day** |
| IRF h=0 (pre → post) | BTC→CONVERTS 0.0326 → 0.0257 (−21 %); BTC→PURE 0.0405 → 0.0303 (−25 %); **NVDA→CONVERTS 0.0105 → 0.0228 (×2.2, 95 % bands disjoint)**; NVDA→PURE 0.0140 → 0.0128 |
| Johansen (trace, cv 15.49) | only **CONVERTS–NVDA**: full 16.63, pre 17.19 (rank 1), **post 6.13 (none)**. CONVERTS–BTC never. PURE–BTC never (EG full p 0.045 only); PURE–NVDA EG full p 0.022 only |
| R check | trace stats identical (diff 2.6e-11) but urca 5 % cv = 17.95 → R does NOT reject for CONVERTS–NVDA (max-eig rejects in both) → **borderline cointegration**. Granger 24/24 same conclusion (max p diff 0.00054); IRF identical (5e-15); VECM α, β identical |
| VECM CONVERTS–NVDA | full: β −0.935, α_CONVERTS −0.0108 (p 0.0003), half-life 64 d; pre: β −0.646, α −0.0151 (p 0.0005), half-life 45 d; α_NVDA negative & significant (NVDA does not correct) |
| Robustness | post on train only: nothing significant, no cointegration; alt pivots: no robust Granger; rank-2 Johansen results (C post CONVERTS–BTC, A post PURE–NVDA) flagged as small-sample artefacts |
| Forecast preview (RMSE h5 / h10) | rw 28.77 / 36.10; var1 29.15 / 37.10; var1_post 30.41 / 41.71; **vecm_nvda 27.86 / 33.78** (train coint CONVERTS–NVDA trace 16.09, maxeig not rejected; α −0.0103, half-life 67 d) |

### Answer to the research question (Phase 4 view)
Converts gained a **same-day exposure to NVDA** after the pivot (specific to them, PURE unchanged), **in addition to** — not instead of — BTC (BTC sensitivity fell similarly for both groups and remains slightly larger). No Granger lead-lag in any period. No long-run BTC leash ever existed for CONVERTS; the only long-run link (NVDA) is borderline and pre-pivot only. **H1 not supported** (PURE–BTC not cointegrated by Johansen). Evidence is mixed — reported as such.

### Open questions
- Post-pivot sample (447 d) is short for cointegration tests (low power).
- Is the vecm_nvda forecast gain significant? → Diebold-Mariano in Phase 7.
- Phase 5: ARCH on VAR residuals already shows ARCH for BTC/NVDA/PURE, not CONVERTS (per equation).

---

## Phase 5: ARCH / GARCH, Python + R ✅ (2026-11-12)

### Status
- [x] `notebooks/python/05_garch.ipynb` runs top-to-bottom (0 errors, 0 warnings); `notebooks/r/05_garch.Rmd` knits (rugarch 1.5.6; reads Python CSVs → run Python first)
- [x] Helpers: `src/garch.py` (specs, persistence/half-life, std-resid diagnostics, QQ vs Student-t, rolling vol forecasts with train-only parameters, naive vol benchmarks, MSE/QLIKE)
- [x] `results/05_*.csv`, `results/forecasts_garch_vol.csv` (VARIANCE forecasts in %²; y_true = r², y_pred = σ̂²; lower/upper empty), `figures/fig_05_01..03`
- [x] 6 events on the conditional-vol chart, each checked in the press (sources in the notebook): FTX 2022-11-09, BTC ETFs 2024-01-10, DeepSeek 2025-01-27, TeraWulf-Google 2025-08-14, IREN-Microsoft 2025-11-03, BTC < 70k 2026-02-05
- [x] `arch==9.0.0` pinned. Returns in % (100 × log return)

### Key results
| Topic | Result |
|---|---|
| ARCH-LM | ARIMA resid: CONVERTS p 0.61 / 0.92 (no ARCH), PURE p 0.0057 / 0.0047. VAR resid: PURE yes, BTC lag 5 only (0.030), CONVERTS & NVDA no (train). Full-sample CONVERTS p 0.51. Single stocks: IREN 0.0021, WULF 0.015, CIFR 0.17; MARA, CLSK < 0.001, RIOT 0.16 → index averaging dilutes firm-specific vol bursts |
| CONVERTS models (train) | GARCH-t: α 0.015 (p 0.13), β 0.954, persistence 0.969, ν 11.2; LR vs constant-t 7.07 (p 0.029); AIC 7167.4 vs const 7170.5 but **BIC prefers constant variance** (7185.5 vs 7192.5). GJR γ 0.012 (p 0.28): no asymmetry |
| EGARCH | Python (`arch`) optimum degenerate: size effect −0.052, mean −0.30 %/day, SE ≈ 1e-8, one-step test variance collapses (median 3e-5 %²). rugarch finds regular solution (size +0.049, persistence 0.936, LL = GARCH-t) → EGARCH excluded |
| Other series | GARCH clearly justified for PURE (LR p 0.0003), BTC, NVDA (p < 1e-5); persistence GARCH-t 0.973 / 0.968 / 0.985; NVDA leverage γ 0.079 |
| Std resid (GARCH-t) | LB z, LB z², ARCH-LM z all not rejected (p ≥ 0.22) for CONVERTS, PURE, BTC; KS vs Student rejected (BTC strongly) |
| Events (vol 5 d after / before) | DeepSeek: CONVERTS +9 %, PURE −0 %, NVDA +60 %; BTC < 70k: PURE +24 %, CONVERTS +6 %, BTC +50 %; FTX: BTC +77 % |
| Pre / post persistence | pre identified (CONVERTS 0.964, PURE 0.922, BTC 0.976, NVDA 0.992); post only NVDA identified (0.959) — CONVERTS/PURE/BTC SE(β) ≥ β, rugarch gives different values → not comparable |
| |r| correlation pre → post | CONVERTS–BTC 0.316 → 0.274, **CONVERTS–NVDA 0.063 → 0.310**; PURE–BTC 0.447 → 0.397, PURE–NVDA 0.150 → 0.237 |
| Vol forecasts (QLIKE h5 / h10) | CONVERTS: const_var best 1.112 / 1.129 (garch_t 1.119 / 1.134, hist_var20 1.229 / 1.259); PURE: garch_t best 1.269 / 1.220; BTC: garch_t best 1.845 / 1.901 |
| Python vs R | GARCH / GJR close (Python LL higher by ≤ 1.8, α+β diff ≤ 0.01); first-origin variance forecast diff ≤ 0.28 % |

### Decisions and why
| Decision | Why |
|---|---|
| GARCH(1,1)-t main model for all series | required by brief, stable, Student-t clearly better than normal |
| EGARCH excluded from forecasts | degenerate/unstable fit in `arch`; rugarch's regular fit adds nothing over GARCH-t |
| No GARCH(2,1) | std residuals of GARCH(1,1) show no remaining ARCH (brief: only if diagnostics justify) |
| Model-free |r| correlations for the pre/post question | post-pivot GARCH parameters not identified on 447 obs |
| QLIKE as main vol loss | robust to the noise of r² as a variance proxy (Patton 2011) |

### Open questions
- Phase 7: DM test on QLIKE losses for vol forecasts (optional) and on price forecasts (main).
- Phase 6 hybrid: ARIMA residuals of CONVERTS have no ARCH and no autocorrelation → expect little for the LSTM to learn.

---

## Phase 6: LSTM, GRU, walk-forward, hybrid — Python only ✅ (2026-11-12)

### Status
- [x] `notebooks/python/06_deep_learning.ipynb` runs top-to-bottom in ≈ 1.5 min on CPU (0 errors, 0 warnings); labelled "Python only" at the top (brief §8.1)
- [x] **PyTorch 2.15.0+cpu** (pinned with the CPU index in requirements.txt), scikit-learn 1.9.1. `dl.set_torch_seed`: all seeds + `torch.use_deterministic_algorithms(True)` + 1 thread → a fresh re-run reproduced every number exactly
- [x] Helpers: `src/dl.py` (windows, LSTM/GRU module, training with early stopping, purged train/val split, cumulative log-level errors, rolling forecasts with empirical intervals)
- [x] `results/forecasts_dl.csv` (lstm, gru, hybrid_arima_lstm), `results/06_*.csv`, `figures/fig_06_01..03`
- [x] Prophet (§4.3, optional) NOT done: no seasonality in the data (Phase 2), which is what Prophet models

### Design
- Target: next 10 CONVERTS returns, **direct multi-output** (exogenous BTC/NVDA unknown in the future → no recursion). Level = last log level + cumulated returns.
- Inputs: univariate vs exogenous (CONVERTS, BTC, NVDA returns + CONVERTS rv20). StandardScaler fit on train rows only.
- Validation for early stopping: last 15 % of train windows, 10-window purge gap. Fixed hyperparameters: 1 layer, 32 units, dropout 0.2, Adam 1e-3, batch 64, ≤ 150 epochs, patience 15.
- Grid 3 windows × 2 inputs × 2 cells = 12 fits. Walk-forward: `TimeSeriesSplit(5, gap=10)` expanding.
- Hybrid on **ARIMA(0,1,1)** (on ARIMA(0,1,0) residuals = returns, so the hybrid would equal the univariate LSTM). Intervals: empirical 2.5 / 97.5 % quantiles of validation log-level errors.

### Key results
| Topic | Result |
|---|---|
| Grid | all 12 models at the random-walk level: val-loss ratio 0.995–0.9997; exogenous inputs slightly better; best w = 10 exogenous for both (GRU 0.8676, LSTM 0.8691 vs RW 0.8720); best epoch 5–9 |
| Curves | LSTM val loss rises after ≈ 10 epochs (overfitting); val < train only because the val period is calmer |
| Walk-forward (5 folds, log-level RMSE) | LSTM h5 0.1458 ± 0.0179 vs RW 0.1462 (ratio 0.996, 3/5 folds better); GRU h5 0.1472 ± 0.0164 (ratio 1.007); h10 ratios 0.999 / 1.001 → no superiority |
| Hybrid | MA θ 0.047; residual-LSTM val loss 0.8695 vs zero forecast 0.8698 → no nonlinear structure in residuals |
| Test (RMSE h5 / h10) | rw 28.77 / 36.10; hybrid 29.09 / 36.99; lstm 29.53 / 38.53; gru 30.13 / 40.07. 95 % coverage at h10 falls to 90 % for lstm/gru |
| Drift | networks forecast +1.6 % (LSTM), +2.0 % (GRU), +0.55 % (hybrid) between h1 and h10 (train mean return) → hurts on the falling test period |
| Seeds 42 / 1 / 2 | LSTM h5 29.5–30.1, GRU 30.0–30.2: always above rw |

### Open questions
- Phase 7: DM tests (lstm, gru, hybrid vs rw), and best classical (vecm_nvda) vs best deep model (hybrid by RMSE).

---

## Phase 7: Evaluation, Diebold-Mariano, extensions ✅ (2026-11-12)

### Status
- [x] `notebooks/python/07_evaluation.ipynb` runs top-to-bottom (0 errors, 0 warnings). Reads only `results/forecasts_*.csv` (+ panel for the extensions); exception stated: classical models refitted once on train to time them; DL times from `06_grid.csv`
- [x] `src/metrics.py`: `point_metrics`, `dm_test` (HLN correction, Student t(n−1), optional Newey-West `nw_lags`), full docstring. `tests/test_metrics.py`: 7 tests, reproduce R `forecast::dm.test` to 1e-8 → `python -m pytest tests -q` passes
- [x] `src/dcc.py`: two-step DCC(1,1) on GARCH(1,1)-t standardised residuals; `notebooks/r/07_dcc.Rmd` cross-check with **rmgarch 1.4.3** (installed, added to `R/install_packages.R`)
- [x] `results/model_comparison.csv`, `results/07_*.csv`, `figures/fig_07_01..04`; pytest 9.2.0 pinned

### Key results
| Topic | Result |
|---|---|
| Ranking (RMSE h5 / h10, ratio to rw) | vecm_nvda 27.86 / 33.78 (0.969 / 0.936); rw 28.77 / 36.10; arima_011 28.85 / 36.15; hybrid 29.09 / 36.99; var1 29.15 / 37.10; lstm 29.53 / 38.53; gru 30.13 / 40.07; var1_post 30.41 / 41.71. Same order for RMSE, MAE, MAPE, both horizons |
| DM vs rw (squared error) | **no model significantly better**: vecm p 0.49 / 0.53; arima, var1, lstm, gru p 0.12–0.51; **hybrid significantly worse** (p 0.009 / 0.008; not after Bonferroni 0.05/16); var1_post borderline worse (p 0.097 / 0.070; NW(20) 0.050 / 0.047). vecm vs hybrid p 0.38 / 0.40 |
| DM vol (QLIKE, garch_t vs const) | CONVERTS p 0.37 / 0.32; PURE p 0.51 / 0.48; BTC h5 p 0.11, h10 standard DM −10.5 (variance underestimated) → NW(20) DM −2.89, p 0.005: GARCH better |
| Recommendation | random walk as reference; vecm_nvda as interpretable model to monitor (best, fits in milliseconds, but gain not significant & cointegration borderline); no deep learning for this use case; GARCH-t for BTC/PURE vol, constant for CONVERTS |
| Rolling 90-d corr ("crossing lines") | CONVERTS–NVDA > CONVERTS–BTC: 20.5 % of days pre-pivot (mostly May–Nov 2022, PURE 26 % too) vs **39.6 % post** (PURE 3.4 %). Episodes: Apr–Jul 2025 (62 d), Aug–Sep 2025, 2026-06-16 → end (95 d). CONVERTS–BTC 0.644 (2025-01-21) → 0.166 (2025-09-23) → 0.337 (2026-10-30); CONVERTS–NVDA 0.513 at the end |
| DCC(1,1) | stable; a 0.008–0.033, b 0.95–0.97. Mean corr pre → post: CONVERTS–NVDA **0.334 → 0.418**, CONVERTS–BTC 0.501 → 0.477, PURE–BTC 0.650 → 0.634, PURE–NVDA 0.409 → 0.418. rmgarch: a, b within 0.002, path correlation ≥ 0.9996 |

### Overall answer (Phases 4–7)
The AI converts gained a **daily exposure to NVIDIA that adds to — not replaces — their Bitcoin link** after early 2025: impact response ×2.2 (Phase 4), |r| correlation 0.06 → 0.31 (Phase 5), DCC 0.33 → 0.42 and crossing lines 40 % of post-pivot days (Phase 7), none of which appears in the pure-miner control. No long-run decoupling (CONVERTS never cointegrated with BTC; H1 not supported). For forecasting, nothing beats the random walk significantly.

### Open questions
- DCC / rolling means pre-pivot include 2022 (everything correlated with NVDA); a 2023–2024-only baseline would sharpen the contrast (not computed).

---

## Phase 8: LLM material ✅ (2026-11-12) — material only, the LLM part is the student's

### Status
- [x] `src/llm_summary.py` + `llm/make_stats_summary.py` → `llm/stats_summary.md` (370 lines, numbers only; sections 0 data, A descriptive + ADF/KPSS + Ljung-Box + STL, B ARIMA / VAR-Granger-IRF / Johansen-VECM / ARCH-GARCH / DCC, C model comparison + DM + forward forecasts)
- [x] **Forward forecasts** from the last day 2026-10-30 (train-only parameters, same models): `results/08_forward_forecasts.csv` — needed for the simulated recommendations. CONVERTS last level 117.56; rw 117.56 [79.48; 173.89] at h = 10; vecm_nvda 120.87 [81.94; 178.29] at h = 10; GARCH-t annualised vol h10: CONVERTS 0.992, PURE 0.873, BTC 0.480. Future dates are business days (US holidays not removed)
- [x] `llm/prompts.md` (a: model hypotheses from section A only; b: committee explanation from 0+B+C; c: simulated recommendations + self-listed limits from 0+C; d: self-check follow-up). Each asks for French and forbids invented numbers
- [x] `llm/my_interpretation_TEMPLATE.md`, `llm/comparison_TEMPLATE.md` (error types H/C/S/D/M/O), `llm/CHECKLIST_LLM_ERRORS.md` (subject, method, recommendation and form errors with the file that proves each), `llm/answers/README.md`, `llm/README.md`
- [x] **No LLM answer, conversation or comparison was written.**

### What the student must do before Phase 9
1. Write `llm/my_interpretation.md` (from the template) BEFORE using the LLM.
2. Run prompts a, b, c (fresh conversations) and d in a real LLM; paste everything verbatim in `llm/answers/`.
3. Fill `llm/comparison.md` with the checklist.

---

## Translation to English ✅ (2026-11-17)

At the student's request, the whole project is now in **English** (this overrides the "French" rule of the prompt guide; the brief imposes no language).
- Translated: markdown of all 7 Python notebooks, all 5 Rmd, `src/` strings (test conclusions, verdicts), `R/` helpers, every CSV column name and categorical value (e.g. `modèle`→`model`, `période`→`period`, `avant pivot`→`pre-pivot`), plot labels, `llm/` files (prompts now ask the LLM to answer in English), report builder.
- Report renamed `report/rapport.*` → `report/report.docx` / `report/report.pdf` (22 pages); review marker is now `[TO REVIEW]` (31 paragraphs), student placeholders `[TO BE WRITTEN BY THE STUDENT]`.
- Re-run: Python notebooks 01–07 (0 errors), all Rmd knitted, `pytest` 7 passed, `stats_summary.md` regenerated. **All numbers unchanged** (e.g. RMSE h5 vecm_nvda 27.86, rw 28.77).
- French version kept as a backup in `../Bitcoin miners_FR_backup_2026-11-17/`.

## Phase 9: Report, defence notes, final check 🟡 (2026-11-17) — everything except the LLM-dependent parts

### Done
- [x] Report draft `report/report.docx` + `.pdf` (22 pages, English, brief order, figures/tables read from `results/` and `figures/` by `report/build/report_content.py`); 31 `[TO REVIEW]` paragraphs
- [x] `report/DEFENSE_NOTES.md`: per section what / why / how to read the key figure / likely examiner questions with answers
- [x] Fresh-environment reproducibility check (clean copy, new venv from requirements.txt, results/ and figures/ emptied): all 7 Python notebooks, pytest (7 passed), stats summary and all 5 Rmd run with exit 0; 73 regenerated CSVs identical to the project's except wall-clock training times (≤ 0.5 s)
- [x] `report/REQUIREMENTS_CHECKLIST.md`: every bullet of brief §1–§8 with status and file. Missing (bonus only): §4.3 additional models, §7 text-sentiment / FinBERT. Partial: 4.88 years < 5 (justified)
- [x] `report/build/make_submission.ps1` → `BitcoinMiners_AI_TimeSeries.zip` (draft, 18.8 MB; warns while the LLM files are missing)

### Still to do (student first, then a short Claude round)
1. Student: `llm/my_interpretation.md` (before the LLM), run prompts a–d in a real LLM, save full answers in `llm/answers/prompt_a.md`…`prompt_d.md`, fill `llm/comparison.md`.
2. Claude: write report §9.1–9.5 and appendix B **from those files only**, adapt §10.2, rebuild docx/pdf (`python report/build/report_content.py`, `node report/build/build_docx.js`, `report/build/export_pdf.ps1`), add the LLM errors to DEFENSE_NOTES §9, re-run `make_submission.ps1`.
3. Student: rewrite the 31 `[TO REVIEW]` paragraphs in your own words, fill name / instructor / date on the title page, confirm the deadline and the report language with the instructor, practise DEFENSE_NOTES out loud.
