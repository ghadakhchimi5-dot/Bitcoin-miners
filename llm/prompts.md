# Prompts for the LLM-assisted analysis (brief §5)

> **To be done by the student, in a real LLM** (ChatGPT, Claude, Gemini…). No answer is written here.
>
> **Order to follow:**
> 1. Fill in `my_interpretation_TEMPLATE.md` **before** opening the LLM: the expert interpretation must be independent.
> 2. Open a **new conversation** for each prompt (a, b, c), then send prompt d in the same conversation as the one it checks.
> 3. Copy the answer **in full**, without editing it, into `llm/answers/` (see `llm/answers/README.md`), with the model name and version, the date and the time.
> 4. Fill in `comparison_TEMPLATE.md` with the help of `CHECKLIST_LLM_ERRORS.md`.
>
> Replace the `[PASTE HERE …]` blocks with the indicated section of `llm/stats_summary.md`, copied as is (markdown tables included). Add nothing else: the LLM must have only these numbers.

---

## Prompt a — Model hypotheses from the descriptive statistics

*Goal (§5, bullet 1): the LLM proposes models from the descriptive statistics and stationarity tests alone, without knowing our modelling results.*

```
You are a statistician specialising in financial time series. Answer in English.

Context: I am studying four daily series (2021-12-14 → 2026-10-30, 1,225 trading days):
- CONVERTS: equal-weighted index of three listed Bitcoin miners that have pivoted to AI data centres (IREN, CIFR, WULF);
- PURE: equal-weighted index of three miners that stayed pure Bitcoin (MARA, CLSK, RIOT);
- BTC: Bitcoin in US dollars;
- NVDA: NVIDIA stock.
My research question: "did the converted miners lose their link with Bitcoin and become tied to AI stocks?".

Here are the descriptive statistics and tests I computed (and nothing else):

[PASTE HERE SECTION "A. Descriptive statistics and stationarity" OF llm/stats_summary.md]

Questions:
1. What do these statistics tell you about each series (stationarity, order of integration, autocorrelation, distribution tails, heteroscedasticity, seasonality)? Quote the numbers you rely on.
2. Which models do you recommend I test, and why? For each model: the series and transformation to use, the orders or specifications you propose, and the diagnostic that justifies it.
3. Which models would answer my research question (link between the series, regime change)?
4. What results would you expect to obtain? Clearly separate what the numbers show from what you assume.
Do not invent any number that is not in the tables. If you lack information to conclude, say so.
```

---

## Prompt b — Explanation for a non-statistician investment committee

*Goal (§5, bullet 2): plain-language explanation of the model results. The answer goes in the report's appendix.*

```
You are a quantitative analyst presenting a study to an investment committee of non-statistician decision-makers. Answer in English, in simple terms, without mathematical formulas, in 600 to 900 words.

The study addresses the question: "did the Bitcoin miners that pivoted to AI (CONVERTS index: IREN, CIFR, WULF) lose their link with Bitcoin and become tied to AI stocks (NVIDIA)?". The miners that stayed pure Bitcoin (PURE index: MARA, CLSK, RIOT) are the control group. A regime-change date was detected statistically: 2025-01-22.

Here are all the numerical results of the study:

[PASTE HERE SECTIONS 0, B AND C (C.1 and C.2) OF llm/stats_summary.md]

Explain to the committee:
1. The answer to the research question, with the level of certainty the results allow.
2. What the main results mean in practice (short-run and long-run links, volatility, correlations, forecast tests).
3. Which forecasting model to keep and why, taking into account accuracy, statistical significance, interpretability and cost.
4. The three main limitations of the study.
Back every statement with a number from the tables, and do not quote any number that is not in them.
```

---

## Prompt c — Simulated investment recommendations, with their limits

*Goal (§5, bullet 3): SIMULATED recommendations from the forecasts, with the LLM stating the limits and risks itself. The student then adds a critical complement in `comparison_TEMPLATE.md`.*

```
Academic exercise: this is not real investment advice. Answer in English.

You play the role of a portfolio manager. From the forecasts and their evaluation below, give SIMULATED investment recommendations for the next 10 trading days on the CONVERTS index (Bitcoin miners converted to AI), and possibly PURE, BTC and NVDA.

[PASTE HERE SECTIONS 0 AND C (C.1 and C.2) OF llm/stats_summary.md]

For each recommendation, state:
1. the proposed position (buy, sell, neutral, hedge…) and the horizon;
2. which exact numbers it relies on (forecast, interval, forecast volatility, test results);
3. the level of confidence it deserves, given the statistical significance of the models.

Then, in a separate section titled "Limits and risks", list yourself ALL the limits and risks of these recommendations: statistical limits, data limits, market risks, operational risks, and everything that was not modelled.
Do not invent any number that is not in the tables.
```

---

## Prompt d — Follow-up: the LLM checks its own statistical claims

*Send in the SAME conversation, right after the answer to prompt b (then, if time allows, after the answer to prompt c).*

```
Re-read your previous answer and check it critically, in English.

1. Build a table of every numerical or statistical claim you made, with three columns: "claim", "exact number from the table provided (copy it)", "correct / incorrect / not verifiable".
2. Flag any p-value, statistic or value you quoted that does not appear word for word in the tables I gave you.
3. For each cause-and-effect relationship you stated, say whether a test in the study really allows concluding causality. Think about the difference between Granger causality and economic causality, and between correlation and causation.
4. Say whether you presented as significant a result whose p-value is above 0.05, or as proof a result flagged as "borderline".
5. Rewrite only the sentences that need to be corrected.
```
