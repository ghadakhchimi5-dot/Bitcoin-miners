# Checklist of typical LLM errors on THIS project

Go through it line by line while re-reading each LLM answer. For each item, the column "What our results show" gives the reference to check. A ticked box means the LLM made the error; then report it in `comparison.md`.

## 1. Errors about the subject (the "expected story")

| ☐ | Possible LLM error | What our results show | Where to check |
|---|---|---|---|
| ☐ | "Bitcoin miners are simple Bitcoin proxies." | PURE's correlation with BTC is only ≈ 0.6 (DCC), and PURE is **not** cointegrated with BTC according to Johansen | `04_cointegration.csv`, `07_dcc_params.csv` |
| ☐ | "The converts abandoned / left Bitcoin." | Their link with BTC falls only a little (DCC 0.50 → 0.48; shock response −21%, as much as PURE). The exposure to NVDA **adds to** the link with BTC | `04_irf.csv`, `07_dcc_params.csv` |
| ☐ | "The converts are now cointegrated with NVIDIA." | The CONVERTS–NVDA cointegration exists **only before** the pivot, it is **borderline** (R does not keep it), and it disappears after | `04_cointegration.csv`, `04_cointegration_r_vs_python.csv` |
| ☐ | Linking the pivot to a specific announcement (Microsoft contract, Google deal…) as if the date came from it | The date 2025-01-22 was **detected by structural-break tests**, not chosen from the news. The contracts mentioned came later (August and November 2025) | notebook 02, section 6; `02_chow_candidates.csv` |
| ☐ | Invented or outdated dated facts (contract amount, installed capacity, current price) | Only six events were checked, with their sources | notebook 05, section 4 |

## 2. Statistical method errors

| ☐ | Possible LLM error | Correction | Where to check |
|---|---|---|---|
| ☐ | Granger causality presented as true causality ("BTC drives the converts") | Granger means "helps predict", and no reference → group Granger causality is robust here | `04_granger.csv`, `04_robustness.csv` |
| ☐ | Correlation (or impulse response) presented as a cause | The impulse response depends on the Cholesky order. BTC closes 3 to 4 h after stocks | notebook 04, section 3; `DATA_DICTIONARY.md` |
| ☐ | Invented p-value, or misleadingly rounded | Compare each p-value with the table, to the decimal | `stats_summary.md` |
| ☐ | Reversed H0 (e.g. "KPSS p = 0.01, so stationary") | ADF: H0 = unit root. KPSS: H0 = stationarity | `02_stationarity_adf_kpss.csv` |
| ☐ | "The VECM significantly beats the random walk" | Its RMSE is lower, but DM p = 0.49: **not significant** | `07_dm_tests.csv` |
| ☐ | "GARCH is necessary for CONVERTS" | ARCH-LM not rejected (p = 0.61). BIC prefers a constant variance, and the constant variance forecasts as well | `05_archlm.csv`, `05_garch_comparison.csv`, `07_dm_vol.csv` |
| ☐ | "EGARCH is the best model (best AIC)" | Degenerate solution in `arch`, not reproduced by `rugarch`, collapsing forecasts | notebook 05, sections 2 and 6 |
| ☐ | "The LSTM/GRU captures non-linearities and outperforms classical models" | The networks do not beat the random walk, neither in walk-forward, nor on the test set, nor with other seeds | `06_walk_forward_summary.csv`, `model_comparison.csv` |
| ☐ | Comparing models on RMSE alone, without a significance test | Ask for the Diebold-Mariano result | `07_dm_tests.csv` |
| ☐ | Ignoring that a rejection at p = 0.009 among 16 tests does not survive Bonferroni | Multiple-testing problem | notebook 07, section 2 |
| ☐ | Recommending a SARIMA or a seasonal model | F_S ≤ 0.03, no day-of-week effect | `02_stl_seasonality.csv`, `02_weekday_effect.csv` |
| ☐ | Interpreting the post-pivot GARCH persistence | It is not identified (standard error ≥ estimate) for CONVERTS, PURE and BTC | `05_persistence_pre_post.csv` |
| ☐ | Confusing log return and simple return, or daily and annualised volatility | Returns are daily log returns; annualised volatility = σ·√252 | `DATA_DICTIONARY.md` |

## 3. Errors in the simulated recommendations (prompt c)

| ☐ | Possible LLM error | Why it is an error |
|---|---|---|
| ☐ | Recommending to buy because the VECM forecasts a slight rise (117.6 → 120.9 over 10 days) | The rise is tiny compared with the 95% interval (≈ 82 to 178), and the VECM does not significantly beat the random walk |
| ☐ | **Ignoring transaction costs**, the bid-ask spread, the liquidity of small caps | They are not modelled; with an annualised volatility ≈ 100%, they can absorb any expected gain |
| ☐ | Ignoring tail risk (−30% crashes in one day, as on 2025-01-27) | Tails are fat (Jarque-Bera rejected); a normal distribution underestimates this risk |
| ☐ | Ignoring company-specific risk (dilution, execution of AI contracts, dependence on a few clients) | This risk is not visible in a 3-stock index and is not modelled |
| ☐ | Presenting a 123-day test sample (a single falling period) as representative | There is only one regime in the test set |
| ☐ | Not stating that this is an academic exercise and not advice | Ethical and regulatory requirement |
| ☐ | Recommending a CONVERTS / NVDA hedge as if the relationship were stable | The cointegration is borderline and disappears after the pivot; the DCC correlation ranges from 0.08 to 0.64 |

## 4. Form errors to look for

| ☐ | Possible LLM error |
|---|---|
| ☐ | Confident tone on a result flagged "borderline", "mixed" or "not significant" |
| ☐ | Correct numbers attributed to the wrong series or the wrong period |
| ☐ | Generic answer about "cryptocurrencies", unrelated to the tables provided |
| ☐ | Self-check (prompt d) that declares everything correct without really comparing with the tables |
