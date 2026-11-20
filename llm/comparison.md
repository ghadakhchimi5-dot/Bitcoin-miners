# Human / LLM comparison (filled in AFTER getting the LLM's answers)

> Brief §5, bullet 4: where do the two interpretations agree? Where is the LLM wrong, oversimplifying, or inventing an unfounded causality?
> **[TO REVIEW]** Drafted by Claude (Opus 5.5, in Claude Code) at the student's request: every row was checked against `llm/stats_summary.md`, but the student must re-check and rewrite it in their own words.

**LLM used:** qwen2.5:3b (Qwen2 family, 3.1B parameters, Q4_K_M quantisation, digest 357c53fb659c), run locally with Ollama 0.40.16 on CPU via `llm/run_ollama.py` (context 16,384 tokens, seed 42, default temperature)  **Conversation dates:** 2026-11-20, 17:27 (prompt a), 17:37 (b), 17:57 (d after b), 18:05 (c), 18:09 (d after c)

Answers: `llm/answers/prompt_a.md` … `prompt_d.md`. Section references (A.2, B.3, C…) point to `llm/stats_summary.md`, which is exactly the material the LLM received.

## 1. Verification table

Error types (column 5):
- **H**: hallucinated number or result (absent from the tables provided, or wrong);
- **C**: invented causality (correlation or Granger presented as a cause);
- **S**: oversimplification (nuance, uncertainty or borderline result erased);
- **D**: dated or outdated fact (general knowledge of the LLM, wrong or not verifiable);
- **M**: method error (test misread, reversed H0, p-value misread);
- **O**: important omission (key limit or result left out);
- **—**: correct statement.

| # | Prompt | LLM statement (exact quote) | Correct? | Error type | My correction | Evidence |
|---|---|---|---|---|---|---|
| 1 | a | "KPSS test results show non-stationary at the difference (log return) form." (repeated for all four series) | No | M | KPSS on returns gives p = 0.1000 (upper bound) for all four: H0 = stationarity is **not** rejected; ADF p = 0.0000 rejects the unit root. Returns are stationary. | A.2 |
| 2 | a | "The series is likely I(1) based on the ADF test results." | Yes | — | ADF does not reject in level (p = 0.1386 CONVERTS … 0.6060 NVDA), KPSS rejects in level (p = 0.01). | A.2 |
| 3 | a | "The Ljung-Box test on returns and squared returns show significant autocorrelation at lags 5, 10, and 20." (CONVERTS; same claim for all four) | No | M | CONVERTS: returns p = 0.3667 / 0.2416 / 0.5674, squared 0.5040 / 0.8511 / 0.8462 — nothing significant. Only PURE and BTC squared returns (p = 0.0027, 0.0036 at lag 5) and NVDA (0.0385 returns, 0.0128 squared, lag 5 only). | A.3 |
| 4 | a | "The skewness is moderate (0.11230) and kurtosis is slightly elevated (0.95184) which suggests mild fat tails." | Yes | — | Numbers copied exactly (0.95184 is *excess* kurtosis). | A.1 |
| 5 | a | PURE: "kurtosis is elevated (0.58893), suggesting heavier tails." | Partly | S | 0.58893 is the **lowest** excess kurtosis of the four series; PURE has the thinnest tails, BTC (6.51) and NVDA (3.93) the fattest. | A.1 |
| 6 | a | BTC: "kurtosis is elevated (6.50614), suggesting lighter tails." | No | M | Excess kurtosis 6.51 means the **heaviest** tails of the four, not lighter. | A.1 |
| 7 | a | "Heteroscedasticity: The KPSS test for stationarity on the difference of log returns shows no significant non-stationarity." | No | M | KPSS tests the mean, not the variance (and contradicts row 1). Heteroscedasticity is read from Ljung-Box on squared returns: present for PURE, BTC, weakly NVDA, absent for CONVERTS. | A.3 |
| 8 | a | "The STL decomposition shows strong seasonal component (99.66%)" (98.63%, 99.76%, 99.91% for the others) | No | M | 0.9966 is the **trend** strength F_T, not seasonal; CONVERTS seasonal strength F_S = 0.0093 (period 5) and 0.0000 (period 252). Same misreading for all four series. | A.4 |
| 9 | a | "Transformation: No transformation required as they are already I(1)." | No | M | An I(1) series must be differenced (d = 1, i.e. log returns) — especially for the VAR it proposes on the same series. | A.2 |
| 10 | a | "Orders suggested by the Box-Jenkins method (e.g., ARIMA(1,1,1))", justified by "the autocorrelation observed in the ADF and Ljung-Box tests" | No | M | No autocorrelation in returns (row 3), so the natural candidate is ARIMA(0,1,0); the AIC/BIC grid indeed keeps (0,1,0)/(0,1,1). | A.3; B.1 |
| 11 | a | GARCH(1,1) proposed for NVDA only | Partly | O | NVDA is justified (p = 0.0128), but the evidence is stronger for PURE (0.0027) and BTC (0.0036), which get no GARCH; no Student-t errors despite fat tails. | A.1; A.3 |
| 12 | a | "VAR … Series: CONVERTS, PURE, NVDA … (e.g., VAR(2))" | No | O | BTC is left out of the model meant to test the link with Bitcoin; lag 2 is not justified (all criteria later choose p = 0). | B.2 |
| 13 | a | "Granger causality tests to identify if one series Granger-causes another, indicating a possible regime change." | No | M | Granger tests lead-lag predictability, not regime change; a regime change needs a sub-sample split / structural-break test. | — |
| 14 | a | (Models proposed for the research question: VAR only) | — | O | No cointegration / VECM although all log prices are I(1), no time-varying correlation (DCC / rolling), no pre/post-break estimation. | A.2 |
| 15 | a | "The ADF and KPSS tests should consistently show non-stationarity for all series at the difference form, indicating the need for differencing." | No | M | Contradicts the table it was given (row 1); in difference both tests agree on stationarity. | A.2 |
| 16 | a | "If the skewness is close to 0 and the kurtosis is close to the normal value (3)…" | No | M | The table reports **excess** kurtosis, whose normal value is 0. | A.1 |
| 17 | a | "The STL decomposition should show strong seasonal components for all series, suggesting a clear seasonal pattern." | No | M | F_S ≤ 0.0297 at period 5 and ≤ 0.1146 at period 252: no seasonality, no seasonal model needed. | A.4 |
| 18 | a | "The Granger causality tests results would need to be interpreted cautiously, as they are hypothesis tests and do not guarantee causality." | Yes | — | Correct caution. | — |
| 19 | b | "The study detected a regime change on January 22, 2025, based on structural-break tests." | Yes | — | Matches the data table. | 0 |
| 20 | b | "Before this date, the miners (CONVERTS index) were linked to Bitcoin (BTC), as shown by the mean returns (log level) of CONVERTS being significantly Granger-caused by BTC returns." | No | H | BTC → CONVERTS pre-pivot p = 0.7705 (full 0.5501): never significant. All information criteria choose p = 0 lags. | B.2 |
| 21 | b | "After January 22, 2025, there was no longer a significant Granger-causality." | No | M | There was none before either; the post-pivot p-value (0.0907) is actually the *lowest* of the three. The "before/after" story is invented. | B.2 |
| 22 | b | "After January 22, 2025, the miners stopped being linked to Bitcoin" | No | S | Same-day BTC response of CONVERTS post-pivot 0.0257 [0.0203, 0.0311], still larger than NVDA's 0.0228; DCC CONVERTS–BTC 0.5009 → 0.4768. The link weakened slightly, as for PURE (0.0405 → 0.0303). | B.2; B.5 |
| 23 | b | "…suggesting that their returns no longer predict Bitcoin's returns." | No | M | Direction reversed relative to the previous sentence; CONVERTS → BTC is never significant (p = 0.2262 pre, 0.7681 post). | B.2 |
| 24 | b | "This shift is supported by the ARIMA model on the log level of CONVERTS, which shows a regime change around the pivot date." | No | H | The ARIMA table is estimated on the train sample without any break; it says nothing about a regime change. | B.1 |
| 25 | b | "The DCC … results … showing a significant decrease in correlation with BTC after January 22, 2025, compared to NVDA." | Partly | S | CONVERTS–BTC 0.5009 → 0.4768 (−0.02) is tiny and untested; the half about NVDA rising (0.3343 → 0.4184) is right. | B.5 |
| 26 | b | "…the Diebold-Mariano test, which shows that the model predicting the miners' performance on NVDA (NVIDIA) is more accurate than predicting on BTC." | No | H | No such test exists: each DM test compares a model with the random walk on CONVERTS. The VECM CONVERTS–NVDA is not significantly better than the random walk (p = 0.4922 / 0.5252). | C |
| 27 | b | "The volatility forecast comparison (GARCH model) shows that the volatility of the CONVERTS index increased after January 22, 2025" | No | H | No such result. Post-pivot GARCH for CONVERTS is **not identified** (se(α) 0.1959 for α = 0.0000; se(β) 0.9744 for β = 0.7957); ARCH-LM on CONVERTS p = 0.6104. | B.4 |
| 28 | b | "The volatility of the PURE (purity Bitcoin) index remained relatively stable" | No | H | Not in the tables; PURE post-pivot GARCH is also not identified (persistence 0.9216 → 0.0579 with se(β) 0.2953). | B.4 |
| 29 | b | "In the short-term (5-day and 10-day rolling correlation), the miners showed a significant increase in correlation with NVDA" | No | H | Only a 90-day rolling correlation and the DCC exist; no significance test; and for PURE the share of days with NVDA > BTC **fell** (0.2602 → 0.0336). | B.5 |
| 30 | b | "after January 22, 2025, the miners were more correlated with NVIDIA's performance compared to Bitcoin's performance." | No | S | CONVERTS post-pivot DCC with NVDA 0.4184 < with BTC 0.4768; NVDA exceeds BTC on only 39.6% of post-pivot days. Exposure to NVDA was **added**, BTC was not replaced. | B.5 |
| 31 | b | "…the models that show the most significant improvement in accuracy are the hybrid ARIMA LSTM model. This model performs better than the classical models" | No | M | Sign of the DM test misread: DM > 0 = model 1 less accurate. Hybrid DM = 2.6571 (p = 0.0090) at h = 5 → **significantly worse** than the random walk; RMSE ratio 1.011 / 1.025. The nominally best model is the VECM (0.969 / 0.936), not significant. | C |
| 32 | b | "The hybrid model is also the most interpretable" | No | H | The table rates its interpretability "low"; random walk, ARIMA and VECM are "high". | C |
| 33 | b | Limitations: daily data noisy; macroeconomic, regulatory and mining-cost factors not included | Yes | — | Valid but generic. | — |
| 34 | b | (Whole answer) | — | O | Prompt required a number behind every statement: almost none given. Never mentions cointegration (long run), the PURE control-group contrast, the impulse responses, the Cholesky-order caveat, the small post-pivot sample, or multiple testing. | B.2–B.5 |
| 35 | b | "The forecasting model (hybrid ARIMA LSTM) provides the best balance of accuracy, interpretability, and statistical significance." | No | M | Worst on all three counts among the serious candidates (rows 31–32); the random walk (cheapest, as accurate) or the VECM should be kept. | C |
| 36 | c | "Proposed Position: Buy … Horizon: 10 trading days" | No | S | No model beats the random walk significantly; the forward forecast gain (+2.8%) is tiny versus the 95% interval. A neutral position is the only defensible one. | C; C.2 |
| 37 | c | "The hybrid_arima_lstm model with h=10 has the lowest RMSE (1368.238)" | No | H | 1368.238 is its **MSE**; its RMSE is 36.990. Lowest RMSE at h = 10: VECM 33.776. | C |
| 38 | c | "…and the highest 95% PI coverage (93.860) among all models tested." | No | H | 93.860 is the hybrid's coverage, but among the lowest (VECM / RW / VAR 98.246, ARIMA 99.123). | C |
| 39 | c | "The forecasted level for 2026-11-13 is 120.87, with a 95% confidence interval of 81.94 to 178.29." | Partly | S | Numbers exact, but they come from the **VECM**, not the hybrid model the paragraph discusses; the interval (−30% / +52% around 117.56) makes the forecast uninformative for a buy. | C.2 |
| 40 | c | "The forecasted annualised volatility for 10 days is 0.992, which is relatively high but within reasonable bounds" | Yes | — | Number exact (CONVERTS, h = 10). Understated: ≈ 99% annualised ≈ 20% standard deviation over 10 days. | C.2 |
| 41 | c | "The out-of-sample forecasts have shown stability and accuracy in their volatility forecasts" | No | H | For CONVERTS, GARCH-t volatility forecasts are not better than a constant variance (QLIKE DM p = 0.3693 / 0.3188). | C |
| 42 | c | "The Diebold-Mariano test (DM) p-value for this model is 0.0077, indicating that this model is significantly more accurate than the benchmark (rw)" | No | M | DM = 2.7135 > 0: significantly **less** accurate. Also 0.0077 does not pass Bonferroni for 16 DM tests (0.05/16 ≈ 0.003). | C |
| 43 | c | "very high 95% PI coverage (93.860), suggesting that the model is highly accurate in predicting the index level" | No | M | Coverage measures the calibration of the intervals, not point accuracy; 93.9% is actually *below* the nominal 95%. | C |
| 44 | c | "The models do not account for transaction costs, liquidity, or position sizing" | Yes | — | Correct (stated in the material). | C.2 |
| 45 | c | "…new technologies, such as ASICs, that could disrupt the mining industry." | No | D | ASICs have been the standard Bitcoin mining hardware for over a decade; not a new disruptive technology. | general knowledge |
| 46 | c | (Limits and risks section) | — | O | No "not investment advice" statement (only "a guide"); no tail risk (−30.1% on 2025-01-27; normality rejected); no company risk (dilution, AI-contract execution, client concentration); no warning that the 123-day test set is a single regime; nothing on PURE, BTC or NVDA. | A.1; C |
| 47 | c | "While these models provide strong evidence of their predictive power" | No | S | No model beats the random walk significantly; the only significant DM result says the hybrid is worse. | C |
| 48 | d | (after b) Verification table: every claim's "exact number" is "2025-01-22" and every claim is "Correct" | No | M | A fake check: the date is not the number behind any of the 9 claims, and 7 of the 9 are wrong (rows 20–32). | B; C |
| 49 | d | (after b) "None of the values quoted are directly from the provided tables." / "None of the values quoted are incorrectly reported." | No | M | Self-contradictory: unverifiable claims cannot be declared correct. | — |
| 50 | d | (after b) "Granger causality is tested using the Ljung-Box and Jarque-Bera tests." | No | M | **New error**: Granger causality is an F test in the VAR; Ljung-Box and Jarque-Bera are residual diagnostics. | B.1; B.2 |
| 51 | d | (after b) "The VAR(1) estimated in each period shows Granger causality from BTC to CONVERTS and from NVDA to CONVERTS." | No | H | **New error**: BTC → CONVERTS p = 0.5501 / 0.7705 / 0.0907; NVDA → CONVERTS 0.9373 / 0.4693 / 0.1248 — none below 0.05. | B.2 |
| 52 | d | (after b, under "Economic Causality") "This suggests that miners' performance is better predicted by NVDA than by BTC after January 22, 2025." | No | C | Presented as economic causality, from a DM comparison that does not exist (row 26). | C |
| 53 | d | (after b) "the p-values are not above 0.05. Therefore, these results are not presented as proof but rather as significant." | No | H | The relevant DM p-values (VECM vs RW) are 0.4922 / 0.5252 — far above 0.05. | C |
| 54 | d | (after b) "Revised Sentences" 1–9 | No | O | The "rewritten" sentences are copies of the wrong originals: no error was corrected. | — |
| 55 | d | (after c) "The hybrid_arima_lstm model with h=10 has the lowest RMSE. \| 1368.238 \| Correct" | No | M | The MSE-for-RMSE error (row 37) is confirmed instead of caught. | C |
| 56 | d | (after c) "The DM p-value for the hybrid_arima_lstm model with h=10 compared to the hybrid_arima_lstm model itself is 0.0087." (and 0.0051) | No | M | **New error**: 0.0087 and 0.0051 are the Newey-West p-values of hybrid vs random walk at h = 10 and h = 5. | C |
| 57 | d | (after c) "The hybrid_arima_lstm model with h=10 has the highest 95% PI coverage and the lowest RMSE for the Pure series." (same for BTC and NVDA) | No | H | **New error**: forecast accuracy was evaluated on the CONVERTS level only. | C |
| 58 | d | (after c) "Granger causality tests are not provided in the table" | Yes | — | True for the prompt c material (sections 0 and C). | 0; C |
| 59 | d | (after c) "a DM p-value of 0.0077, which is significant at the 0.05 level" (as evidence of strong predictive power) | No | M | Sign error persists (row 42). | C |

## 2. Summary counts

| Prompt | Statements checked | Correct | H | C | S | D | M | O |
|---|---|---|---|---|---|---|---|---|
| a | 18 | 3 | 0 | 0 | 1 | 0 | 11 | 3 |
| b | 17 | 2 | 7 | 0 | 3 | 0 | 4 | 1 |
| c | 12 | 2 | 3 | 0 | 3 | 1 | 2 | 1 |
| d (self-check) | 12 | 1 | 3 | 1 | 0 | 0 | 6 | 1 |
| **Total** | **59** | **8 (14%)** | **13** | **1** | **7** | **1** | **23** | **6** |

## 3. Agreement with my interpretation (`my_interpretation.md`)

- Log prices are I(1) according to ADF (row 2) — agreed.
- GARCH is justified for NVDA (row 11, partly) and was not proposed for CONVERTS — consistent with my reading (ARCH-LM p = 0.61), but the LLM reached it without citing that evidence.
- The pivot date comes from structural-break tests (row 19), not from news — agreed; it did not link the date to a specific announcement.
- The correlation of CONVERTS with NVDA increased after the pivot (DCC 0.33 → 0.42) — the direction is right (half of row 25), but the LLM turned it into "more correlated with NVIDIA than with Bitcoin" (row 30), which the numbers contradict.
- Granger causality ≠ causality (row 18) and transaction costs / liquidity / position sizing are not modelled (row 44) — agreed.

## 4. Disagreements and the most serious errors (with explanation)

- **Reading the Diebold-Mariano sign backwards** (rows 31, 35, 42, 59). The table states that DM > 0 means model 1 is less accurate; the hybrid ARIMA-LSTM has DM = 2.66 / 2.71, so it is significantly *worse* than the random walk. The LLM turned the study's clearest negative result into its main recommendation, and the self-check confirmed it. This is the most consequential error: it drives the model choice in b and the "buy" in c.
- **"The converts stopped being linked to Bitcoin"** (rows 22, 30). Our main finding is the opposite: BTC remains their largest same-day driver and the BTC link fell by the same amount for the control group; the converts *added* an NVDA exposure. The LLM told the "expected story" instead of reading the tables, and it never used the PURE control group.
- **Invented results** (rows 20, 24, 26, 27, 28, 29, 51, 57): significant Granger causality that does not exist, a GARCH volatility increase from a model that is not identified, a DM test comparing NVDA with BTC, 5- and 10-day rolling correlations, hybrid results for series that were never forecast. The instruction "do not quote any number that is not in the tables" was respected only in the literal sense: the model mostly avoided numbers and asserted results instead.
- **Table misreading in prompt a** (rows 1, 3, 6, 8): reversed KPSS reading, p-values read as "significant" when they are large, trend strength reported as seasonal strength, excess kurtosis compared with 3. These lead to wrong model suggestions (ARIMA(1,1,1), seasonal patterns, "no transformation" for I(1) series).
- **Omissions**: no cointegration / VECM, no time-varying correlation, BTC left out of the proposed VAR (rows 12, 14); in b, no long-run analysis and no control-group contrast (row 34).

## 5. Did the self-check (prompt d) correct the errors?

- **Errors the LLM found itself:** none. Both self-checks declare every claim "Correct".
- **Errors it did not see:** all of them — in particular the DM sign error (rows 55, 59), the invented Granger results, the "stopped being linked to Bitcoin" claim, the MSE reported as RMSE.
- **New errors introduced during the check:** Granger causality "tested using Ljung-Box and Jarque-Bera" (row 50), Granger causality BTC/NVDA → CONVERTS that the tables reject (row 51), DM p-values "not above 0.05" (row 53), a DM test of the hybrid "against itself" (row 56), hybrid results for PURE, BTC and NVDA (row 57), and a causal reading under "Economic causality" (row 52). The verification table uses the pivot date as the "exact number" for every claim (row 48): it has the form of a check without its content.
- Conclusion: asking a small model to verify itself adds confidence, not accuracy. Verification must be done against the source tables by a human (or a deterministic script).

## 6. Simulated recommendations (prompt c): my critical complement

- **Limits and risks the LLM listed correctly:** transaction costs, liquidity, position sizing, slippage (row 44); possible structural breaks; macroeconomic and regulatory factors; volatility possibly higher than forecast.
- **Limits and risks it forgot:** that this is an academic exercise and not advice (only "a guide"); tail risk (one-day falls of −30.1%, Jarque-Bera rejects normality); company-specific risk (equity dilution, execution of AI/HPC contracts, dependence on a few clients) invisible in a 3-stock index; the 123-day test set covers a single falling regime; the forecast intervals (≈ 82 to 178 at h = 10) dwarf the forecast change; any hedge (BTC or NVDA) relies on correlations that vary between 0.08 and 0.64 (CONVERTS–NVDA DCC) and on a CONVERTS–NVDA cointegration that is borderline and absent after the pivot.
- **Recommendations that contradict the statistical significance of the models:** the "Buy" (row 36) relies on a model that is significantly *worse* than the random walk (row 42) and on a +2.8% VECM forecast whose own edge is not significant (DM p = 0.5252). The only defensible simulated position is neutral, with position size set by the ≈ 99% annualised volatility (see `my_interpretation.md` §4).

## 7. What the LLM brought (time saved, clarity) and what it could not do

(Material for the report, §8.2 and §8.4.)

- **Brought:** fast, well-structured, readable text (about 46 minutes of CPU time for five answers, no cost, data never left the machine); a reasonable generic list of investment risks; correct caution about Granger causality in the abstract (row 18).
- **Could not do:** read a statistical table reliably (H0 directions, sign conventions, which column is which, MSE vs RMSE); keep each number attached to the right model, series or period; use a control group; distinguish "not significant" from "significant"; check its own claims — the self-check made things worse.
- **Caveat on scope:** these results are for a small (3.1B-parameter, 4-bit quantised) local model. A large hosted model (ChatGPT, Claude, Gemini) would likely make fewer table-reading errors, so the error rate here (51 of 59 statements wrong or incomplete) should not be generalised to all LLMs; the *types* of error (expected story, causal over-reading, inverted test signs, uncritical self-check) match the checklist prepared in advance (`CHECKLIST_LLM_ERRORS.md`).
- **Disclosure:** the expert interpretation and this comparison were drafted with Claude (another LLM) from the project's own result files, then [TO REVIEW] by the student.
