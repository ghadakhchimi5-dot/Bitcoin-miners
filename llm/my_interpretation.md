# My expert interpretation (written BEFORE consulting the LLM)

> Brief §5, bullet 4: the human / LLM comparison is only worth something if this text is written **before** reading the LLM's answers.
> Do not change it after reading the LLM. If a correction is needed, add it at the end of the file, dated.

**Written on:** 2026-11-20, before `llm/run_ollama.py` was first run (no LLM answer existed in `llm/answers/`)  **By:** draft written by Claude (Opus 5.5, in Claude Code) at the student's request, from `llm/stats_summary.md` and `results/` — **[TO REVIEW: the student must check every statement and rewrite it in their own words; disclose the AI drafting if the brief requires it]**

Sources: `llm/stats_summary.md` (same numbers the LLM receives) and the `results/` files it is generated from. Section references (A.1, B.3…) point to `stats_summary.md`.

---

## 1. What the descriptive statistics say (same material as prompt a)

- **Stationarity and order of integration.** All four log prices are I(1): ADF does not reject the unit root (p = 0.1386 CONVERTS, 0.0799 PURE, 0.5654 BTC, 0.6060 NVDA) and KPSS rejects stationarity (p = 0.01, the table's lower bound). All log returns are stationary (ADF p ≈ 0, KPSS p = 0.10, the upper bound). WULF and RIOT are "ambiguous" in level (ADF p = 0.0374 / 0.0340 but KPSS still rejects); with a trend-stationary alternative at the 5% edge and KPSS rejecting, I treat them as I(1) too. (A.2)
- **Autocorrelation of returns.** Essentially none: Ljung-Box p-values on returns are all above 0.13 for CONVERTS, PURE and BTC at lags 5/10/20. NVDA has p = 0.0385 at lag 5 only, not at 10 or 20 — weak and isolated. Prices behave close to a random walk. (A.3)
- **Tails and skewness.** BTC (excess kurtosis 6.51) and NVDA (3.93) have fat tails; the miner indices much less (CONVERTS 0.95, PURE 0.59), because averaging three stocks thins the tails. Normality is still rejected on the index residuals (Jarque-Bera p = 3.0e-10 CONVERTS, B.1). Skewness is small. The largest move is −30.1% for CONVERTS on 2025-01-27, the same day as NVDA's minimum (−18.6%): a shared AI-sector shock, five days after the detected pivot. (A.1)
- **Heteroscedasticity.** Squared returns are autocorrelated for PURE (p = 0.0027 at lag 5) and BTC (p = 0.0036), weakly for NVDA (0.0128 at lag 5 only), and **not for CONVERTS** (p = 0.50 / 0.85 / 0.85). Surprising, since IREN (ARCH-LM p = 0.0021) and WULF (0.0149) individually show ARCH effects (B.4) — the equal-weighted index averages away the volatility clusters.
- **Seasonality.** None. Weekly seasonal strength F_S ≤ 0.03 for every series, annual F_S = 0 for both indices; NVDA's annual 0.11 is too small to matter and is most likely trend leakage in a 4.9-year sample. (A.4)
- **The models I would have chosen from these statistics alone, and why:**
  - ARIMA on the log price with d = 1 and very low orders, expecting ARIMA(0,1,0) (random walk) to be hard to beat, since returns show no autocorrelation.
  - GARCH(1,1) with Student-t errors for PURE, BTC and NVDA (ARCH effects + fat tails). For CONVERTS, a constant variance is probably enough; GARCH only as a check.
  - VAR on returns (stationary) to study short-run links and Granger predictability, and Johansen tests + VECM on log prices (all I(1)) for long-run links — both estimated before / after a break date, since the question is about a regime change.
  - A time-varying correlation model (DCC or rolling correlation), the most direct tool for "link with BTC vs link with NVDA" over time.
  - No SARIMA / seasonal model.

## 2. Answer to the research question (same material as prompt b)

- **Short-run link with BTC and with NVDA, before / after the pivot.**
  - Same-day response to a BTC shock (B.2, orthogonalised IRF): CONVERTS 0.0326 → 0.0257 (−21%); PURE 0.0405 → 0.0303 (−25%). The link with BTC weakens **by the same amount in both groups**, so it is a market-wide change, not a consequence of the conversion.
  - Same-day response to an NVDA shock: CONVERTS 0.0105 → 0.0228 (×2.2, and the bands do not overlap: pre upper 0.0143 < post lower 0.0179); PURE 0.0140 → 0.0128 (unchanged). **This difference-in-differences is the core evidence**: only the converts gained NVDA exposure.
  - DCC (B.5): CONVERTS–BTC 0.50 → 0.48 (stable), CONVERTS–NVDA 0.33 → 0.42; PURE stable on both (0.65 → 0.63; 0.41 → 0.42). Share of days where the 90-day correlation with NVDA exceeds the one with BTC: CONVERTS 20% → 40%, PURE 26% → 3%. Correlation of absolute returns with NVDA: CONVERTS 0.06 → 0.31.
  - Caveats: the IRF depends on the Cholesky order (BTC first, so BTC gets the shared shock), and BTC trades 24/7 while stocks close at 16:00 New York, so "same-day" is not simultaneous.
- **Predictability (Granger causality).** Practically none. All information criteria choose p = 0 lags in every period, so the VAR(1) is already over-specified. Of 24 Granger p-values, only 3 are below 0.05 (CONVERTS → NVDA full 0.0405, PURE → BTC pre 0.0350, NVDA → PURE post 0.0156), about what chance alone produces (24 × 0.05 ≈ 1.2), none survives a Bonferroni correction (0.05/24 ≈ 0.002), and none concerns BTC/NVDA → CONVERTS. Granger causality is "helps predict", never economic causality; here even that is absent. The links are **contemporaneous**, not lead-lag.
- **Long-run link (cointegration, VECM).** No cointegration with BTC for either group, in any period (Johansen trace ≤ 14.52 < 15.49). CONVERTS–NVDA shows rank 1 on the full sample (16.63) and **pre-pivot** (17.19) but not post-pivot (6.13) — the opposite of what "became tied to AI" would predict — and both statistics are below the urca 5% critical value (17.95), and Engle-Granger never rejects (p ≥ 0.17). I read it as a borderline, probably spurious common-trend effect of the 2023-24 rally, not a structural long-run relation. The pre-pivot VECM loading on CONVERTS is significant (α = −0.0151, p = 4.9e-4, half-life 45 days) but inherits that fragility.
- **Volatility.** CONVERTS has no ARCH effect at the index level (ARCH-LM p = 0.61); GARCH(1,1)-t improves the likelihood (LR p = 0.029) but BIC prefers a constant variance with Student-t errors (7185.5 vs 7192.5). EGARCH has the best AIC but its persistence (0.985) and half-life (46 d) are out of line with the other specifications. After the pivot, the GARCH parameters of CONVERTS, PURE and BTC are **not identified** (standard errors ≥ estimates), so nothing can be said about a change in volatility persistence. What does change is the **co-movement of volatility** with NVDA (|r| correlation 0.06 → 0.31).
- **Is the PURE control group valid?** Reasonably: same industry, similar volatility (annualised 0.92 vs 1.00), same exposure to BTC and the same decline of that exposure after the pivot, while its NVDA exposure stays flat. Limits: only 3 stocks per group; the allocation of each firm to "converted" or "pure" is a judgement at a date, and pure miners can also start AI/HPC activity later, which would bias the difference towards zero.
- **My answer in 3 sentences, with my level of certainty.** The converted miners did **not** lose their link with Bitcoin: BTC remains their largest same-day driver (0.0257 vs 0.0228 for NVDA after the pivot) and their DCC correlation with BTC barely moves (0.50 → 0.48), and the decline of the BTC link also occurs in the pure miners. What changed is that they **added** an exposure to AI stocks, which roughly doubled after 2025-01-22 while it stayed flat for the control group — they became hybrid BTC/AI assets, not AI stocks. Certainty: moderate for the short-run correlation shift (consistent across IRF, DCC, rolling correlation and the control group, but only 447 post-pivot days and Cholesky/closing-time caveats); low to none for any long-run tie to NVDA.

## 3. Forecast evaluation and model choice

- **Ranking and significance (Diebold-Mariano).** All models are within about ±6% of the random walk's RMSE at h = 5 (ratio 0.969 to 1.057). The VECM CONVERTS–NVDA is nominally best (RMSE ratio 0.969 at h = 5, 0.936 at h = 10) but **not significantly** better (DM p = 0.49 and 0.53). ARIMA(0,1,1) is identical to the random walk (1.003). LSTM and GRU are worse but not significantly. The hybrid ARIMA-LSTM is **significantly worse** (p = 0.009 / 0.008), and the post-pivot VAR is worse at the edge of significance (NW p = 0.047 at h = 10). With 16 DM tests, only the hybrid's h = 10 result gets near the Bonferroni threshold (0.05/16 ≈ 0.003) and it does not reach it. Test sample: 123 days, a single falling regime.
- Volatility: GARCH(1,1)-t does not forecast CONVERTS or PURE volatility better than a constant variance (QLIKE DM p = 0.37 / 0.51 at h = 5); it is significantly better only for BTC at h = 10 (p = 1.9e-18, NW p = 0.0046).
- **The model I keep, for which use, and why.**
  - For point forecasts of the CONVERTS level: the **random walk**. Nothing beats it significantly, it has no parameters, no training cost (0 s), and its 95% intervals are well calibrated (coverage 96.6% at h = 5).
  - For interpretation: the **VECM** as a descriptive tool (it encodes the CONVERTS–NVDA relation), with the warning that its edge is not significant and that cointegration is borderline and absent post-pivot.
  - For risk: a **constant variance with Student-t errors** for CONVERTS; GARCH(1,1)-t for BTC.
  - Deep learning: rejected — no gain, lower interpretability, higher cost, and the hybrid is significantly worse.

## 4. Simulated recommendations I would make (same material as prompt c)

*Academic exercise, not investment advice.*

- **Position and horizon:** **neutral** on CONVERTS over the next 10 trading days — no directional bet. If an exposure is already held, size it on risk and, if hedging, hedge with **BTC** rather than NVDA.
- **Numbers I rely on:** the random walk forecasts 117.56 (flat) with a 95% interval of 79.48–173.89 at h = 10; the VECM's +2.8% (120.87, interval 81.94–178.29) is tiny compared with the interval and the VECM does not significantly beat the random walk (p = 0.53). Forecast volatility ≈ 99% annualised (0.992 at h = 10), i.e. a 10-day standard deviation of about 0.992 × √(10/252) ≈ 20% (my computation). BTC is the more stable hedge (DCC CONVERTS–BTC between 0.40 and 0.55) than NVDA (0.08 to 0.64), and no cointegration supports a long-run CONVERTS/NVDA hedge after the pivot.
- **Confidence:** low. No model has a significant forecasting edge, so any directional view is noise; the only reliable output is the size of the risk.

## 5. Limits and risks I identify

- **Statistical limits:** non-normal residuals (Jarque-Bera rejects), so Gaussian intervals are approximate; only 447 post-pivot days, which leaves the post-pivot GARCH unidentified and the tests low-powered; many tests (Granger, cointegration pairs × periods, 16 DM tests) with no systematic correction; Cholesky ordering drives the IRF split; the pivot date is itself estimated, which makes pre/post tests slightly optimistic; the 123-day test set covers one regime only.
- **Data limits:** 4.88-year window; BTC price taken at a different time than stock closes; 3-stock equal-weighted indices dominated by idiosyncratic events; Yahoo Finance adjusted prices (no check of corporate actions beyond the adjustment); group membership fixed over the whole sample.
- **Market and unmodelled risks:** transaction costs, bid-ask spreads and liquidity of small caps (not modelled — with ~100% volatility they can absorb any forecast edge); fat tails and one-day crashes (−30% on 2025-01-27); equity dilution, execution and counterparty risk of the AI/HPC contracts, client concentration; energy prices and Bitcoin halving economics; regulation of crypto and of data-centre power use.

## 6. What I expect from the LLM

- **Statements on which I think it will agree with me:** log prices are I(1) and returns are stationary; no seasonality; fat tails especially for BTC and NVDA; ARIMA with d = 1 and GARCH as candidate models; the random walk is hard to beat.
- **Errors I expect to find** (see `CHECKLIST_LLM_ERRORS.md`):
  - recommending GARCH for CONVERTS despite ARCH-LM p = 0.61;
  - "the converts abandoned Bitcoin" or "are cointegrated with NVIDIA", ignoring that cointegration exists only pre-pivot and is borderline;
  - Granger results presented as causality, or p-values above 0.05 called significant;
  - "the VECM outperforms the random walk" without the DM p = 0.49;
  - a "buy" recommendation built on the VECM's +2.8%, ignoring the 82–178 interval and transaction costs;
  - linking the pivot date to a specific news event;
  - since the local model is small (3B parameters), I also expect invented or mis-copied numbers, numbers attributed to the wrong series or period, generic crypto commentary, and a self-check (prompt d) that declares everything correct.
