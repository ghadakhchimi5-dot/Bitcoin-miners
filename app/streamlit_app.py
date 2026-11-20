"""Presentation app: every phase of the project, from the data to the LLM critique.

Run from the project root:
    .venv\\Scripts\\streamlit run app/streamlit_app.py

Read-only: every number and figure comes from data/, results/, figures/ and llm/ (nothing is re-estimated),
except the optional "Live demo" tab, which queries the local Ollama server.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
RES, FIG, LLM = ROOT / "results", ROOT / "figures", ROOT / "llm"
CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
PIVOT = CFG["pivot_date"]
TEST_START, TEST_END = CFG["split"]["test_start"], CFG["split"]["test_end"]
OLLAMA = "http://localhost:11434"

COLORS = {"CONVERTS": "#E4572E", "PURE": "#4C78A8", "BTC": "#F2A541", "NVDA": "#59A14F",
          "IREN": "#F28E2B", "CIFR": "#E15759", "WULF": "#B07AA1", "MARA": "#76B7B2", "CLSK": "#9C755F", "RIOT": "#5B8FD6"}
MODEL_NAMES = {"rw": "Random walk", "arima_011": "ARIMA(0,1,1)", "var1": "VAR(1)", "var1_post": "VAR(1) post-pivot",
               "vecm_nvda": "VECM CONVERTS–NVDA", "lstm": "LSTM", "gru": "GRU", "hybrid_arima_lstm": "ARIMA + LSTM hybrid"}
ERROR_TYPES = {"H": "Hallucinated number / result", "C": "Invented causality", "S": "Oversimplification",
               "D": "Dated / outdated fact", "M": "Method error", "O": "Important omission", "—": "Correct"}

st.set_page_config(page_title="Bitcoin miners and AI", layout="wide")


# ---------------------------------------------------------------------------------------------- loaders / helpers
@st.cache_data
def csv(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(RES / name, **kw)


@st.cache_data
def panel() -> pd.DataFrame:
    p = ROOT / "data" / "processed"
    df = pd.read_parquet(p / "panel.parquet") if (p / "panel.parquet").exists() else pd.read_csv(p / "panel.csv")
    if "Date" in df.columns:
        df = df.set_index("Date")
    df.index = pd.to_datetime(df.index)
    return df


@st.cache_data
def text(path: str) -> str:
    p = ROOT / path
    return p.read_text(encoding="utf-8") if p.exists() else ""


def md(s: str) -> None:
    """Render project markdown safely ($ would start LaTeX, single ~ would strike through, |e| breaks tables)."""
    s = s.replace("$", r"\$").replace("~", r"\~").replace("|e|", r"\|e\|").replace("|r|", r"\|r\|")
    st.markdown(s)


def fmt(x):
    if isinstance(x, (bool, np.bool_)):
        return "yes" if x else "no"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, (float, np.floating)):
        if np.isnan(x):
            return "—"
        if x != 0 and (abs(x) < 1e-3 or abs(x) >= 1e5):
            return f"{x:.2e}"
        return f"{x:.4f}"
    return x


def table(df: pd.DataFrame, p_cols=(), height: int | None = None) -> None:
    """Dataframe with readable numbers; p-value columns below 0.05 are highlighted."""
    sty = df.style.format(fmt)
    pc = [c for c in p_cols if c in df.columns]
    if pc:
        sty = sty.map(lambda v: "background-color: rgba(228,87,46,0.28); font-weight: 600"
                      if isinstance(v, (int, float, np.floating)) and not pd.isna(v) and v < 0.05 else "", subset=pc)
    kw = {"height": height} if height else {}
    st.dataframe(sty, hide_index=True, **kw)


def figure(name: str, caption: str = "") -> None:
    p = FIG / f"{name}.png"
    if p.exists():
        st.image(str(p), caption=caption or None)
    else:
        st.caption(f"(figure {name} not found)")


def mark(fig: go.Figure, pivot: bool = True, split: bool = True) -> go.Figure:
    """Pivot date line and test-set band on a date axis."""
    if split:
        fig.add_shape(type="rect", x0=TEST_START, x1=TEST_END, y0=0, y1=1, yref="paper",
                      fillcolor="gray", opacity=0.12, line_width=0, layer="below")
        fig.add_annotation(x=TEST_START, y=1, yref="paper", text="test set", showarrow=False,
                           xanchor="left", yanchor="bottom", font=dict(size=11))
    if pivot:
        fig.add_shape(type="line", x0=PIVOT, x1=PIVOT, y0=0, y1=1, yref="paper", line=dict(dash="dash", color="gray"))
        fig.add_annotation(x=PIVOT, y=1, yref="paper", text=f"pivot {PIVOT}", showarrow=False,
                           xanchor="right", yanchor="bottom", font=dict(size=11))
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.15), hovermode="x unified")
    return fig


def gallery(names: dict[str, str]) -> None:
    choice = st.selectbox("Figure", list(names), format_func=lambda k: names[k], key=f"gal_{list(names)[0]}")
    figure(choice, names[choice])


def takeaway(s: str) -> None:
    st.info(s)


# ---------------------------------------------------------------------------------------------- LLM parsing
@st.cache_data
def comparison_rows() -> pd.DataFrame:
    rows = []
    for line in text("llm/comparison.md").splitlines():
        if re.match(r"^\| \d+ \|", line):
            cells = [c.strip().replace("\\|", "|").replace("**", "") for c in re.split(r"(?<!\\)\|", line)[1:-1]]
            if len(cells) == 7:
                rows.append(cells)
    df = pd.DataFrame(rows, columns=["#", "Prompt", "LLM statement", "Correct?", "Error type", "Correction", "Evidence"])
    df["#"] = df["#"].astype(int)
    return df


@st.cache_data
def answers(letter: str) -> list[dict]:
    t = text(f"llm/answers/prompt_{letter}.md")
    metas = re.findall(r"^LLM: (.*)\nDate and time: (.*)\nNew conversation: (.*)$", t, flags=re.M)
    blocks = re.findall(r"## (.+?) — prompt exactly as sent\n\n````text\n(.*?)\n````\n\n## .+? — full answer \(verbatim, not edited\)\n\n"
                        r"(.*?)\n\n\*Run statistics: (\{.*?\})\*", t, flags=re.S)
    out = []
    for i, (title, prompt, answer, stats) in enumerate(blocks):
        m = metas[i] if i < len(metas) else ("?", "?", "?")
        out.append({"title": title, "prompt": prompt, "answer": answer, "stats": json.loads(stats),
                    "llm": m[0], "date": m[1], "new": m[2]})
    return out


def section(md_text: str, start: str, end: str | None = None) -> str:
    i = md_text.find(start)
    if i < 0:
        return ""
    j = md_text.find(end, i + len(start)) if end else -1
    return md_text[i:j] if j > 0 else md_text[i:]


# ================================================================================================ PAGES
def page_overview():
    st.title("Did Bitcoin miners leave Bitcoin for AI?")
    st.markdown("A multivariate time-series study of listed Bitcoin miners that pivoted to AI / HPC data centres, "
                "benchmarked against miners that stayed pure Bitcoin.")
    st.markdown("> **Research question.** Did the AI converts (IREN, CIFR, WULF) lose their link with Bitcoin and become tied to "
                "AI stocks (NVIDIA), while pure miners (MARA, CLSK, RIOT) stayed tied to Bitcoin?")

    irf = csv("04_irf.csv")
    g = lambda per, sh, rs: irf[(irf.period == per) & (irf.shock == sh) & (irf.response == rs) & (irf.h == 0)]["irf"].iloc[0]
    dcc = csv("07_dcc_params.csv").set_index("pair")
    mc = csv("model_comparison.csv")
    best = mc[mc.h == 5].sort_values("RMSE / RMSE rw").iloc[0]
    cmp_ = comparison_rows()
    c = st.columns(5)
    c[0].metric("Trading days", f"{CFG['split']['n_obs']:,}", f"{CFG['dates']['start']} → {TEST_END}", delta_color="off")
    c[1].metric("Pivot date (detected)", PIVOT, "Chow test, converts only", delta_color="off")
    c[2].metric("CONVERTS response to NVDA shock", f"{g('post-pivot', 'NVDA', 'CONVERTS'):.4f}",
                f"was {g('pre-pivot', 'NVDA', 'CONVERTS'):.4f} before the pivot")
    c[3].metric("Best model vs random walk (h=5)", f"{best['RMSE / RMSE rw']:.3f}", f"{MODEL_NAMES.get(best['model'], best['model'])}, not significant",
                delta_color="off")
    if len(cmp_):
        n_ok = (cmp_["Error type"] == "—").sum()
        c[4].metric("LLM claims correct", f"{n_ok} / {len(cmp_)}", "qwen2.5:3b, local", delta_color="off")

    st.subheader("Key findings")
    findings = pd.DataFrame([
        ["The pivot is detected on 22 Jan 2025, for converts only", "Chow scan + Bai-Perron (EDA)"],
        ["Converts gained AI exposure: same-day response to an NVIDIA shock doubles after the pivot",
         f"IRF {g('pre-pivot', 'NVDA', 'CONVERTS'):.4f} → {g('post-pivot', 'NVDA', 'CONVERTS'):.4f}; PURE {g('pre-pivot', 'NVDA', 'PURE'):.4f} → {g('post-pivot', 'NVDA', 'PURE'):.4f}"],
        ["…without leaving Bitcoin: their BTC link falls only slightly, as much as the pure miners'",
         f"BTC shock: CONVERTS {g('pre-pivot', 'BTC', 'CONVERTS'):.4f} → {g('post-pivot', 'BTC', 'CONVERTS'):.4f}; PURE {g('pre-pivot', 'BTC', 'PURE'):.4f} → {g('post-pivot', 'BTC', 'PURE'):.4f}"],
        ["No long-run or predictive link with Bitcoin, for either group", "Johansen: no cointegration with BTC; no robust Granger causality"],
        ["Dynamic correlation with NVIDIA rises for converts only",
         f"DCC CONVERTS–NVDA {dcc.loc['CONVERTS–NVDA', 'mean DCC corr pre-pivot']:.2f} → {dcc.loc['CONVERTS–NVDA', 'mean DCC corr post-pivot']:.2f}"],
        ["No model beats the random walk at 1–2 weeks", "Diebold-Mariano p ≈ 0.5 for the best model (VECM)"],
        ["A small LLM misreads the tables and cannot check itself", "See the LLM critique page"],
    ], columns=["Finding", "Evidence"])
    st.dataframe(findings, hide_index=True)
    st.success("**Bottom line:** the converts did not *leave* Bitcoin — they **added** an AI factor on top of it. "
               "The change is visible in co-movements but cannot be exploited for forecasting.")

    st.subheader("Pipeline")
    st.graphviz_chart("""
digraph { rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#f3f3f3", fontname="Helvetica", fontsize=11];
 A [label="Yahoo Finance\\n8 tickers"]; B [label="Panel\\nfeatures · indices\\n90/10 split"]; C [label="EDA\\nstationarity · STL\\npivot detection"];
 D [label="ARIMA"]; E [label="VAR · Granger · IRF\\nJohansen · VECM"]; F [label="GARCH family"]; G [label="LSTM · GRU\\nhybrid"];
 H [label="Evaluation\\nRMSE · Diebold-Mariano\\nDCC correlation"]; I [label="LLM critique", fillcolor="#fde2d8"];
 A->B->C; C->D; C->E; C->F; C->G; D->H; E->H; F->H; G->H; H->I; }""")
    st.caption("Classical models are implemented in both Python and R and cross-checked; deep learning and extensions are Python only.")

    st.caption("Academic project — nothing here is investment advice.")


def page_data():
    st.title("1 · Data")
    df = panel()
    a, b = st.columns([2, 1])
    with a:
        st.markdown(f"""
| | |
|---|---|
| **Source** | Yahoo Finance (`yfinance`), adjusted close, frozen snapshot |
| **Window** | {df.index[0].date()} → {df.index[-1].date()} · **{len(df):,}** US trading days |
| **CONVERTS** (studied group) | equal-weighted index of IREN, CIFR, WULF |
| **PURE** (control group) | equal-weighted index of MARA, CLSK, RIOT |
| **References** | BTC-USD (Bitcoin factor), NVDA (AI factor) |
| **Split** | train {CFG['split']['n_train']} days → {CFG['split']['train_end']} · test {CFG['split']['n_test']} days {TEST_START} → {TEST_END} |
""")
    with b:
        st.markdown("**Why start on 2021-12-14?** Before their mergers, Yahoo's WULF history belongs to IKONICS and CIFR's to a SPAC; "
                    "IREN listed on 2021-11-17. The window starts at TeraWulf's first trading day as a miner.")
        st.markdown("**Indices** are the mean of the members' daily log returns, cumulated and rebased to 100.")

    st.subheader("Prices rebased to 100")
    opts = ["CONVERTS", "PURE", "BTC", "NVDA", "IREN", "CIFR", "WULF", "MARA", "CLSK", "RIOT"]
    sel = st.multiselect("Series", opts, default=["CONVERTS", "PURE", "BTC", "NVDA"])
    logy = st.toggle("Log scale", value=True)
    data = {}
    for s in sel:
        data[s] = df[f"{s}_level"] if f"{s}_level" in df else df[f"{s}_adj_close"] / df[f"{s}_adj_close"].iloc[0] * 100
    if data:
        fig = go.Figure([go.Scatter(x=v.index, y=v, name=k, line=dict(color=COLORS.get(k), width=2 if k in ("CONVERTS", "PURE") else 1.3))
                         for k, v in data.items()])
        fig.update_yaxes(type="log" if logy else "linear", title="level (base 100)")
        st.plotly_chart(mark(fig))

    figure("fig_01_rebased_prices_by_group", "Rebased prices by group")


def page_eda():
    st.title("2 · Exploratory analysis and structural breaks")
    t = st.tabs(["Descriptive stats", "Stationarity", "Autocorrelation & seasonality", "Outliers", "Structural breaks (pivot)", "Rolling links", "Figures"])
    with t[0]:
        d = csv("02_descriptive_stats.csv").rename(columns={"Unnamed: 0": "series"})
        table(d)
        takeaway("BTC (excess kurtosis 6.5) and NVDA (3.9) have fat tails; the miner indices much less, because averaging three stocks thins the tails. "
                 "Converts and pure miners are about twice as volatile as BTC and NVDA (≈ 100% annualised).")
        df = panel()
        s = st.selectbox("Distribution of daily log returns", ["CONVERTS", "PURE", "BTC", "NVDA"])
        st.plotly_chart(px.histogram(df[f"{s}_log_return"].dropna(), nbins=80, color_discrete_sequence=[COLORS[s]])
                        .update_layout(showlegend=False, xaxis_title="log return", margin=dict(t=20)))
    with t[1]:
        st.markdown("**ADF** — H0: unit root. **KPSS** — H0: stationarity. A series is I(1) when ADF does not reject in level and both agree in difference.")
        table(csv("02_stationarity_adf_kpss.csv")[["series", "form", "regression", "adf_stat", "adf_p", "kpss_stat", "kpss_p", "verdict"]],
              p_cols=["adf_p", "kpss_p"])
        table(csv("02_integration_order.csv"))
        takeaway("All log prices are I(1), all log returns are stationary → models on returns (VAR, GARCH) or on differenced log prices (ARIMA d = 1), "
                 "cointegration on log prices.")
    with t[2]:
        lb = csv("02_ljungbox_returns.csv")
        lb["variable"] = lb["variable"].replace({"rendement²": "squared return"})
        st.markdown("**Ljung-Box** on returns and squared returns (p-values, highlighted if < 0.05):")
        table(lb.pivot_table(index=["series", "variable"], columns="lag", values="p_value", sort=False).reset_index()
              .rename(columns=lambda c: f"lag {c}" if isinstance(c, (int, np.integer)) else c), p_cols=["lag 5", "lag 10", "lag 20"])
        takeaway("No autocorrelation in returns (prices ≈ random walk). Volatility clusters (squared returns) for PURE, BTC and NVDA — not for the CONVERTS index.")
        st.markdown("**STL seasonal strength** (F_S close to 0 = no seasonality) and **day-of-week effect**:")
        table(csv("02_stl_seasonality.csv")[["series", "period", "seasonal_strength_FS", "trend_strength_FT", "var_share_seasonal"]])
        table(csv("02_weekday_effect.csv").rename(columns={"Unnamed: 0": "series"}), p_cols=["anova_p", "kruskal_p"])
        takeaway("F_S ≤ 0.03 at the weekly period and no weekday effect → no SARIMA.")
    with t[3]:
        o = csv("02_outliers.csv")
        st.markdown(f"**{len(o)} outlier returns** flagged by a Hampel filter / rolling IQR, matched with known events when possible.")
        table(o, height=350)
        figure("fig_02_09_outliers_returns", "Outlier returns")
    with t[4]:
        st.markdown("The pivot date is **detected from the data**, not taken from the news: a Chow scan and Bai-Perron tests on the regressions "
                    "of each index on BTC and NVDA, and on the CONVERTS − PURE spread.")
        table(csv("02_chow_candidates.csv"), p_cols=["p_value"])
        figure("fig_02_12_chow_scan", "Chow F scan")
        with st.expander("Bai-Perron, sub-sample scan and betas per regime"):
            table(csv("02_breaks_bai_perron_full.csv"))
            table(csv("02_chow_scan_subsample.csv"), p_cols=["p_chow_naive"])
            table(csv("02_regime_betas.csv"))
        takeaway(f"Retained pivot: {PIVOT} (significant for CONVERTS, not for PURE). 2024-02-27 and 2025-08-13 are kept as robustness dates. "
                 "Because the date comes from a scan, the Chow p-values are optimistic.")
        figure("fig_02_13_split_and_pivot", "Train/test split and pivot")
    with t[5]:
        rc = csv("02_rolling_corr_120.csv", index_col=0, parse_dates=True)
        cols = st.multiselect("120-day rolling correlation of daily returns", [c for c in rc.columns if "gap" not in c],
                              default=[c for c in rc.columns if "gap" not in c])
        fig = go.Figure([go.Scatter(x=rc.index, y=rc[c], name=c) for c in cols])
        st.plotly_chart(mark(fig).update_yaxes(title="correlation"))
        df = panel()
        sel = st.multiselect("20-day realised volatility (annualised)", ["CONVERTS", "PURE", "BTC", "NVDA"], default=["CONVERTS", "BTC"])
        fig = go.Figure([go.Scatter(x=df.index, y=df[f"{s}_rv20"], name=s, line=dict(color=COLORS[s])) for s in sel])
        st.plotly_chart(mark(fig))
        with st.expander("Rolling Engle-Granger p-values"):
            figure("fig_02_11_rolling_engle_granger")
    with t[6]:
        gallery({"fig_02_01_log_prices_miners": "Log prices of the miners", "fig_02_02_indices_vs_references": "Indices vs references",
                 "fig_02_03_log_returns": "Log returns", "fig_02_04_realised_vol20": "Realised volatility (20 d)",
                 "fig_02_05_acf_pacf_log_price": "ACF / PACF of log prices", "fig_02_06_acf_pacf_log_return": "ACF / PACF of log returns",
                 "fig_02_07_stl_converts_s5": "STL CONVERTS, period 5", "fig_02_08_stl_converts_s252": "STL CONVERTS, period 252",
                 "fig_02_10_rolling_corr_120": "Rolling correlation (120 d)"})


def forecast_explorer(key: str, default_models: list[str]) -> None:
    fc = pd.concat([csv(f) for f in ["forecasts_arima.csv", "forecasts_var.csv", "forecasts_vecm.csv", "forecasts_dl.csv"]
                    if (RES / f).exists()])
    fc = fc[fc.series == "CONVERTS"]
    fc["date"] = pd.to_datetime(fc["date"])
    models = sorted(fc.model.unique(), key=lambda m: list(MODEL_NAMES).index(m) if m in MODEL_NAMES else 99)
    c1, c2, c3 = st.columns([3, 1, 1])
    sel = c1.multiselect("Models", models, default=[m for m in default_models if m in models], format_func=lambda m: MODEL_NAMES.get(m, m), key=f"m_{key}")
    h = c2.select_slider("Horizon h (days)", options=sorted(fc.horizon.unique()), value=5, key=f"h_{key}")
    band = c3.toggle("95% interval", value=len(sel) == 1, key=f"b_{key}")
    sub = fc[fc.horizon == h]
    truth = sub.drop_duplicates("date").set_index("date")["y_true"].sort_index()
    fig = go.Figure([go.Scatter(x=truth.index, y=truth, name="actual", line=dict(color="black", width=2.5))])
    for m in sel:
        s = sub[sub.model == m].sort_values("date")
        if band:
            fig.add_trace(go.Scatter(x=pd.concat([s.date, s.date[::-1]]), y=pd.concat([s.upper, s.lower[::-1]]), fill="toself",
                                     opacity=0.15, line=dict(width=0), name=f"{MODEL_NAMES.get(m, m)} 95%", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=s.date, y=s.y_pred, name=MODEL_NAMES.get(m, m)))
    fig.update_layout(title=f"CONVERTS level: forecast made h = {h} days earlier vs actual (test set)", yaxis_title="index level")
    st.plotly_chart(mark(fig, pivot=False, split=False))


def page_arima():
    st.title("3 · ARIMA (univariate)")
    t = st.tabs(["Identification", "Residual diagnostics", "Forecasts", "Python vs R", "Figures"])
    with t[0]:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Order grid on the CONVERTS log price (train)** — sorted by BIC")
            table(csv("03_order_grid_converts.csv").sort_values("BIC")[["order", "drift", "k", "loglik", "AIC", "BIC", "dAIC", "dBIC"]].head(10))
        with c2:
            st.markdown("**Order grid on the PURE log price (train)**")
            table(csv("03_order_grid_pure.csv").sort_values("BIC")[["order", "drift", "k", "loglik", "AIC", "BIC", "dAIC", "dBIC"]].head(10))
        st.markdown("**Automatic search** (pmdarima in Python, `auto.arima` in R)")
        table(csv("03_auto_arima.csv"))
        st.markdown("**Seasonal tests** (SARIMA vs ARIMA, OCSB / CH seasonal differencing tests)")
        table(csv("03_seasonal_tests.csv"), p_cols=["p_value"])
        takeaway("BIC, auto_arima and R's auto.arima all choose ARIMA(0,1,0): the CONVERTS index is a random walk. "
                 "ARIMA(0,1,1) has the best AIC by a hair and is kept as a challenger. No seasonal component.")
    with t[1]:
        d = csv("03_residual_diagnostics.csv")
        s = st.radio("Series", sorted(d.series.unique()), horizontal=True)
        table(d[d.series == s].drop(columns=["series"]), p_cols=["p_value"])
        st.markdown("**ARCH-LM on CONVERTS residuals by sub-period**")
        table(csv("03_archlm_converts_subperiods.csv"), p_cols=["p_value"])
        takeaway("Residuals are white noise but not normal (fat tails). No ARCH effect in CONVERTS residuals; clear ARCH effect for PURE → GARCH needed for PURE, not CONVERTS.")
    with t[2]:
        st.markdown("Every model is fitted on the training set only and forecasts from **rolling origins** over the 123 test days.")
        forecast_explorer("arima", ["rw", "arima_011"])
        table(csv("03_forecast_scores_preview.csv"))
    with t[3]:
        st.markdown("The R notebook re-estimates the same models from the same data and compares:")
        table(csv("03_python_vs_r.csv"))
        table(csv("forecasts_arima_r_first_origin.csv").head(10))
    with t[4]:
        gallery({"fig_03_01_acf_train_returns": "ACF of train returns", "fig_03_02_residuals_converts": "Residuals CONVERTS",
                 "fig_03_03_residuals_pure": "Residuals PURE", "fig_03_04_forecast_first_origin": "Forecast from the first origin",
                 "fig_03_05_rolling_forecasts_converts": "Rolling forecasts CONVERTS", "fig_03_06_residuals_converts_r": "Residuals CONVERTS (R)"})


def page_var():
    st.title("4 · VAR, Granger causality, impulse responses, cointegration")
    st.markdown("VAR on daily returns of **[BTC, NVDA, CONVERTS, PURE]**, estimated on the full sample, before and after the pivot.")
    t = st.tabs(["Lag order & Granger", "Impulse responses", "Cointegration & VECM", "Robustness", "Diagnostics & Python vs R", "Figures"])
    with t[0]:
        ls = csv("04_var_lag_selection.csv")
        best = ls.groupby("period").apply(lambda x: pd.Series({c: int(x.loc[x[c].idxmin(), "p"]) for c in ["AIC", "BIC", "HQIC", "FPE"]}),
                                          include_groups=False).reset_index()
        st.markdown("**Best lag order** by information criterion (p = 0…10):")
        table(best)
        gr = csv("04_granger.csv")
        gr["link"] = gr["cause"] + " → " + gr["effect"]
        piv = gr.pivot_table(index="link", columns="period", values="p_value", sort=False)[["full", "pre-pivot", "post-pivot"]]
        fig = px.imshow(piv, text_auto=".3f", color_continuous_scale="RdYlGn", zmin=0, zmax=0.2, aspect="auto",
                        labels=dict(color="p-value"), title="Granger causality p-values (VAR(1), F test) — red = below 0.05")
        st.plotly_chart(fig.update_layout(margin=dict(t=50)))
        takeaway("All criteria choose 0 lags: there is no lead-lag predictability. Only 3 of 24 Granger p-values are below 0.05 — about what chance produces — "
                 "and none survives a multiple-testing correction. Granger = 'helps predict', never economic causality.")
    with t[1]:
        irf = csv("04_irf.csv")
        c1, c2 = st.columns(2)
        shock = c1.radio("Shock", sorted(irf.shock.unique()), horizontal=True)
        resp = c2.radio("Response", sorted(irf.response.unique()), horizontal=True)
        s = irf[(irf.shock == shock) & (irf.response == resp)]
        fig = go.Figure()
        for per, col in [("pre-pivot", "#4C78A8"), ("post-pivot", "#E4572E"), ("full", "#999999")]:
            d = s[s.period == per].sort_values("h")
            if d.empty:
                continue
            fig.add_trace(go.Scatter(x=pd.concat([d.h, d.h[::-1]]), y=pd.concat([d.upper, d.lower[::-1]]), fill="toself", opacity=0.15,
                                     line=dict(width=0), fillcolor=col, showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=d.h, y=d.irf, name=per, line=dict(color=col), mode="lines+markers"))
        fig.update_layout(title=f"Orthogonalised response of {resp} to a {shock} shock (95% band)", xaxis_title="days after the shock",
                          yaxis_title="response (log return)", margin=dict(t=50))
        st.plotly_chart(fig)
        h0 = irf[irf.h == 0].pivot_table(index=["shock", "response"], columns="period", values="irf")[["pre-pivot", "post-pivot"]]
        h0["change"] = h0["post-pivot"] / h0["pre-pivot"] - 1
        st.markdown("**Same-day effect (h = 0)**")
        st.dataframe(h0.style.format({"pre-pivot": "{:.4f}", "post-pivot": "{:.4f}", "change": "{:+.0%}"}))
        takeaway("The core evidence: the CONVERTS response to NVDA more than doubles (disjoint bands) while PURE's does not move. "
                 "The BTC response falls by about the same amount for both groups → a market-wide change, not a conversion effect. "
                 "Caveat: Cholesky order (BTC first) and BTC closing 3–4 h after US stocks.")
    with t[2]:
        co = csv("04_cointegration.csv")
        st.markdown("**Johansen trace test** (5% critical value 15.49 in statsmodels, 17.95 in R's urca) and **Engle-Granger**:")
        table(co[["pair", "period", "n", "trace_r0", "cv95_trace_r0", "maxeig_r0", "cv95_maxeig_r0", "rank_trace", "EG_p", "conclusion"]], p_cols=["EG_p"])
        st.markdown("**VECM** where the trace test finds rank 1:")
        table(csv("04_vecm.csv"), p_cols=["p_alpha_group", "p_alpha_reference"])
        takeaway("No cointegration with BTC in any period. CONVERTS–NVDA is cointegrated only on the full and pre-pivot samples, and only with "
                 "statsmodels' critical values (not urca's) → borderline, and absent after the pivot.")
    with t[3]:
        st.markdown("Same tests on alternative samples (other pivot dates, train only):")
        table(csv("04_robustness.csv"), p_cols=[c for c in csv("04_robustness.csv").columns if c.endswith(" p")])
    with t[4]:
        table(csv("04_var_diagnostics.csv"), p_cols=["p_value"])
        with st.expander("Python vs R"):
            for f in ["04_granger_r_vs_python.csv", "04_irf_r_vs_python.csv", "04_cointegration_r_vs_python.csv", "04_vecm_r_vs_python.csv"]:
                st.markdown(f"`{f}`")
                table(csv(f))
    with t[5]:
        gallery({"fig_04_01_irf_pre_post": "Impulse responses before / after the pivot", "fig_04_02_vecm_equilibrium_error": "VECM equilibrium error",
                 "fig_04_03_forecasts_h5": "Forecasts h = 5"})


def page_garch():
    st.title("5 · Volatility (ARCH / GARCH)")
    t = st.tabs(["ARCH tests", "Model comparison", "Before / after pivot", "Conditional volatility", "Around events", "Python vs R", "Figures"])
    with t[0]:
        table(csv("05_archlm.csv"), p_cols=["p_value"])
        takeaway("ARCH effect for PURE, BTC and some individual converts (IREN, WULF), but not for the CONVERTS index: firm-specific spikes average out.")
    with t[1]:
        gc = csv("05_garch_comparison.csv")
        s = st.radio("Series", list(dict.fromkeys(gc.series)), horizontal=True)
        table(gc[gc.series == s][["model", "loglik", "AIC", "BIC", "persistence", "half-life (d)", "nu", "LR vs constant variance", "p(LR)"]], p_cols=["p(LR)"])
        takeaway("GARCH(1,1) with Student-t errors is retained. For CONVERTS, BIC prefers a constant variance; EGARCH's best AIC is a degenerate solution not reproduced in R.")
        st.markdown("**Volatility forecasts: GARCH(1,1)-t vs constant variance** (QLIKE loss, Diebold-Mariano)")
        table(csv("07_dm_vol.csv")[["series", "h", "mean_d", "DM", "p_value", "p NW(20)", "conclusion (5%)"]], p_cols=["p_value", "p NW(20)"])
    with t[2]:
        table(csv("05_persistence_pre_post.csv"))
        st.markdown("**Correlation of absolute returns** (volatility co-movement):")
        table(csv("05_absret_corr_pre_post.csv"))
        takeaway("After the pivot, GARCH persistence is not identified for CONVERTS, PURE and BTC (standard error ≥ estimate). "
                 "What changes clearly is the co-movement of CONVERTS volatility with NVDA: 0.06 → 0.31.")
    with t[3]:
        cv = csv("05_conditional_vol_full.csv", index_col=0, parse_dates=True)
        sel = st.multiselect("GARCH(1,1)-t conditional volatility (annualised)", list(cv.columns), default=list(cv.columns))
        fig = go.Figure([go.Scatter(x=cv.index, y=cv[c], name=c, line=dict(color=COLORS.get(c))) for c in sel])
        st.plotly_chart(mark(fig).update_yaxes(title="annualised volatility"))
    with t[4]:
        table(csv("05_vol_around_events.csv"))
        figure("fig_05_02_conditional_vol_events", "Conditional volatility around events")
    with t[5]:
        table(csv("05_python_vs_r_params.csv"))
        table(csv("05_persistence_pre_post_r.csv"))
    with t[6]:
        gallery({"fig_05_01_qq_std_resid": "QQ-plot of standardised residuals", "fig_05_02_conditional_vol_events": "Volatility around events",
                 "fig_05_03_vol_forecasts_converts": "Volatility forecasts CONVERTS"})


def page_dl():
    st.title("6 · Deep learning (LSTM, GRU, hybrid)")
    t = st.tabs(["Grid search", "Walk-forward validation", "Seed sensitivity", "Figures"])
    with t[0]:
        g = csv("06_grid.csv")
        table(g)
        fig = px.bar(g, x="window", y="ratio vs RW", color="cell", barmode="group", facet_col="inputs",
                     title="Validation loss / random-walk loss (1 = no better than the random walk)")
        fig.add_hline(y=1, line_dash="dash")
        st.plotly_chart(fig.update_yaxes(range=[0.99, 1.005]))
        takeaway("All 12 configurations end at random-walk level (ratio 0.995–0.9997).")
    with t[1]:
        wf = csv("06_walk_forward_folds.csv")
        h = st.radio("Horizon", sorted(wf.h.unique()), horizontal=True)
        fig = px.bar(wf[wf.h == h], x="fold", y="ratio RMSE", color="model", barmode="group", title="RMSE / random-walk RMSE per fold")
        fig.add_hline(y=1, line_dash="dash")
        st.plotly_chart(fig)
        table(csv("06_walk_forward_summary.csv"))
    with t[2]:
        table(csv("06_seed_sensitivity.csv"))
    with t[3]:
        gallery({"fig_06_01_training_curves": "Training curves", "fig_06_02_walk_forward": "Walk-forward", "fig_06_03_forecasts_h5": "Forecasts h = 5"})


def page_eval():
    st.title("7 · Forecast evaluation and dynamic correlation")
    t = st.tabs(["Accuracy", "Diebold-Mariano", "Forecast explorer", "Dynamic correlation", "Forward forecasts", "Figures"])
    mc = csv("model_comparison.csv")
    with t[0]:
        mc2 = mc.assign(name=mc.model.map(lambda m: MODEL_NAMES.get(m, m)), horizon=mc.h.map(lambda h: f"h = {h}"))
        fig = px.bar(mc2.sort_values("RMSE / RMSE rw"), x="RMSE / RMSE rw", y="name", color="horizon", barmode="group", orientation="h",
                     title="RMSE relative to the random walk (< 1 = better)", hover_data=["RMSE", "MAE", "MAPE_%", "95% PI coverage"])
        fig.add_vline(x=1, line_dash="dash")
        st.plotly_chart(fig.update_layout(yaxis_title="", margin=dict(t=50)).update_xaxes(range=[0.9, 1.17]))
        table(mc[["model", "family", "h", "n", "RMSE", "MAE", "MAPE_%", "95% PI coverage", "RMSE / RMSE rw", "interpretability", "training time (s)"]])
        takeaway("All models are within ±6% of the random walk. The VECM is nominally best but not significantly; keep the random walk for point forecasts.")
    with t[1]:
        st.markdown("H0: equal accuracy. **DM > 0 means model 1 is less accurate** than model 2. HLN small-sample correction; NW(20) = Newey-West variance.")
        table(csv("07_dm_tests.csv")[["model 1", "model 2", "h", "n", "mean_d", "DM", "p_value", "p NW(20)", "conclusion (5%)"]], p_cols=["p_value", "p NW(20)"])
        takeaway("The only significant result says the ARIMA + LSTM hybrid is **worse** than the random walk — and with 16 tests it does not survive Bonferroni (0.05/16 ≈ 0.003).")
    with t[2]:
        forecast_explorer("eval", ["rw", "vecm_nvda", "lstm"])
    with t[3]:
        src = st.radio("Measure", ["DCC-GARCH", "90-day rolling correlation"], horizontal=True)
        d = csv("07_dcc_corr.csv" if src == "DCC-GARCH" else "07_rolling_corr_90.csv", index_col=0, parse_dates=True)
        grp = st.radio("Group", ["CONVERTS", "PURE"], horizontal=True)
        fig = go.Figure()
        for c, color in [(f"{grp}–BTC", COLORS["BTC"]), (f"{grp}–NVDA", COLORS["NVDA"])]:
            fig.add_trace(go.Scatter(x=d.index, y=d[c], name=c, line=dict(color=color)))
        st.plotly_chart(mark(fig, split=False).update_layout(title=f"{src}: {grp} with BTC vs with NVDA").update_yaxes(title="correlation"))
        table(csv("07_dcc_params.csv"))
        rc = csv("07_rolling_corr_90.csv", index_col=0, parse_dates=True)
        piv = pd.Timestamp(PIVOT)
        share = pd.DataFrame({"period": ["pre-pivot", "post-pivot"],
                              **{g: [(rc[f"{g}–NVDA"] > rc[f"{g}–BTC"])[rc.index < piv].mean(), (rc[f"{g}–NVDA"] > rc[f"{g}–BTC"])[rc.index >= piv].mean()]
                                 for g in ["CONVERTS", "PURE"]}})
        st.markdown("**Share of days where the correlation with NVDA exceeds the one with BTC** (90-day rolling):")
        st.dataframe(share.style.format({"CONVERTS": "{:.0%}", "PURE": "{:.0%}"}), hide_index=True)
        takeaway("For converts, NVDA overtakes BTC on 40% of post-pivot days (20% before); for pure miners it falls to 3%. BTC still dominates on average.")
        with st.expander("Python vs R (DCC)"):
            table(csv("07_dcc_r_vs_python.csv"))
    with t[4]:
        ff = csv("08_forward_forecasts.csv")
        df = panel()
        hist = df["CONVERTS_level"].iloc[-120:]
        fig = go.Figure([go.Scatter(x=hist.index, y=hist, name="CONVERTS (observed)", line=dict(color="black"))])
        for m, col in [("rw (ARIMA(0,1,0))", "#4C78A8"), ("vecm_nvda", "#E4572E")]:
            s = ff[ff.model == m]
            x = pd.to_datetime(s["target date (business day)"])
            fig.add_trace(go.Scatter(x=pd.concat([x, x[::-1]]), y=pd.concat([s["upper 95%"], s["lower 95%"][::-1]]), fill="toself",
                                     opacity=0.15, line=dict(width=0), fillcolor=col, showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=x, y=s["level forecast"], name=m, line=dict(color=col)))
        fig.update_layout(title=f"10-day forecasts from the last observed day ({df.index[-1].date()}), 95% intervals", hovermode="x unified")
        st.plotly_chart(fig)
        vol = ff[ff.model == "garch_t (volatility)"].pivot_table(index="h", columns="series", values="forecast annualised vol")
        st.markdown("**GARCH(1,1)-t annualised volatility forecast**")
        st.dataframe(vol.style.format("{:.1%}"))
    with t[5]:
        gallery({"fig_07_01_model_comparison": "Model comparison", "fig_07_02_top3_forecasts": "Top-3 forecasts",
                 "fig_07_03_rolling_corr_crossing": "Rolling correlation crossing", "fig_07_04_dcc_correlations": "DCC correlations"})


def page_llm():
    st.title("8 · Generative AI critique (LLM)")
    st.markdown("**Brief §5:** can an LLM interpret our statistical results — and can we detect where it is wrong?")
    rows = comparison_rows()
    t = st.tabs(["Protocol", "Material given", "Prompts", "Expert interpretation", "LLM answers", "Verification", "Lessons", "Live demo"])

    with t[0]:
        st.graphviz_chart("""
digraph { rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#f3f3f3", fontname="Helvetica", fontsize=11];
 R [label="results/\\n(all model outputs)"]; S [label="stats_summary.md\\nnumbers only,\\nno interpretation"];
 H [label="Expert interpretation\\nwritten FIRST"]; L [label="Local LLM\\nqwen2.5:3b (Ollama)\\nprompts a, b, c + d", fillcolor="#fde2d8"];
 A [label="answers/\\nverbatim"]; C [label="comparison.md\\nclaim-by-claim check"];
 R->S; S->H; S->L; L->A; A->C; H->C; S->C [style=dashed, label="source of truth"]; }""")
        c = st.columns(4)
        for col, (k, title, goal) in zip(c, [("a", "Model hypotheses", "Propose models from the descriptive statistics only"),
                                             ("b", "Committee explanation", "Explain the results to non-statisticians (600–900 words)"),
                                             ("c", "Simulated recommendations", "10-day positions + all limits and risks"),
                                             ("d", "Self-check", "Re-read its answer b (then c) and verify every claim")]):
            col.markdown(f"#### Prompt {k}\n**{title}**\n\n{goal}")
        st.markdown("""
**Rules that make the comparison fair**
- The LLM sees **only** `stats_summary.md` (generated by code from `results/`), so every claim can be checked against one source.
- The expert interpretation is written **before** any LLM answer exists.
- Each prompt a, b, c runs in a **new conversation**; d runs in the **same** conversation as the answer it checks.
- Answers are saved **verbatim** with model, version and timestamp — errors are the object of study, never corrected in place.
""")
        a0 = answers("a")
        if a0:
            st.caption(f"Model used: {a0[0]['llm']}")
    with t[1]:
        st.caption("Numbers only, no interpretation — the only material the LLM received.")
        with st.container(height=600):
            md(text("llm/stats_summary.md"))
    with t[2]:
        md(text("llm/prompts.md"))
    with t[3]:
        st.caption("Written before the LLM was queried.")
        with st.container(height=650):
            md(text("llm/my_interpretation.md"))
    with t[4]:
        letter = st.radio("Prompt", ["a", "b", "c", "d"], horizontal=True,
                          format_func=lambda k: {"a": "a · model hypotheses", "b": "b · committee", "c": "c · recommendations", "d": "d · self-check"}[k])
        for blk in answers(letter):
            st.subheader(blk["title"])
            m = st.columns(4)
            m[0].metric("Date", blk["date"])
            m[1].metric("New conversation", "yes" if blk["new"].startswith("yes") else "no (follow-up)")
            m[2].metric("Answer tokens", blk["stats"].get("answer tokens"))
            m[3].metric("Generation time", f"{blk['stats'].get('seconds', 0):.0f} s")
            with st.expander("Prompt exactly as sent"):
                st.code(blk["prompt"], language="text")
            flagged = rows[rows.Prompt == letter]
            if len(flagged):
                st.caption(f"{(flagged['Error type'] != '—').sum()} of {len(flagged)} checked statements in this answer contain an error — see the Verification tab.")
            with st.container(border=True, height=520):
                md(blk["answer"])
    with t[5]:
        if rows.empty:
            st.info("llm/comparison.md not found.")
        else:
            n, ok = len(rows), (rows["Error type"] == "—").sum()
            c = st.columns(4)
            c[0].metric("Statements checked", n)
            c[1].metric("Correct", f"{ok} ({ok / n:.0%})")
            c[2].metric("Method errors (M)", (rows["Error type"] == "M").sum())
            c[3].metric("Hallucinations (H)", (rows["Error type"] == "H").sum())
            cnt = rows.groupby(["Prompt", "Error type"]).size().reset_index(name="n")
            cnt["type"] = cnt["Error type"].map(lambda e: f"{e} · {ERROR_TYPES.get(e, e)}")
            order = [f"{k} · {v}" for k, v in ERROR_TYPES.items()]
            pal = {"H": "#E15759", "C": "#B07AA1", "S": "#F28E2B", "D": "#9C755F", "M": "#E4572E", "O": "#BAB0AC", "—": "#59A14F"}
            fig = px.bar(cnt, x="Prompt", y="n", color="type", category_orders={"type": order, "Prompt": ["a", "b", "c", "d"]},
                         color_discrete_map={f"{k} · {v}": pal[k] for k, v in ERROR_TYPES.items()},
                         title="Statements per prompt, by verdict")
            st.plotly_chart(fig.update_layout(yaxis_title="statements", margin=dict(t=50)))
            f1, f2, f3 = st.columns([1, 2, 2])
            fp = f1.multiselect("Prompt", ["a", "b", "c", "d"], default=["a", "b", "c", "d"])
            fe = f2.multiselect("Verdict", list(ERROR_TYPES), default=list(ERROR_TYPES), format_func=lambda e: f"{e} · {ERROR_TYPES[e]}")
            q = f3.text_input("Search", placeholder="e.g. Diebold, Granger, GARCH")
            sub = rows[rows.Prompt.isin(fp) & rows["Error type"].isin(fe)]
            if q:
                sub = sub[sub.apply(lambda r: q.lower() in " ".join(r.astype(str)).lower(), axis=1)]
            st.dataframe(sub, hide_index=True, height=480,
                         column_config={"LLM statement": st.column_config.TextColumn(width="large"),
                                        "Correction": st.column_config.TextColumn(width="large")})
            with st.expander("Checklist of expected errors, prepared before the run"):
                md(text("llm/CHECKLIST_LLM_ERRORS.md"))
    with t[6]:
        comp = text("llm/comparison.md")
        st.markdown("#### The most serious errors")
        md(section(comp, "## 4.", "## 5.").replace("## 4. Disagreements and the most serious errors (with explanation)", ""))
        a, b = st.columns(2)
        with a:
            st.markdown("#### Did the self-check help?")
            md(section(comp, "## 5.", "## 6.").replace("## 5. Did the self-check (prompt d) correct the errors?", ""))
        with b:
            st.markdown("#### Recommendations: critical complement")
            md(section(comp, "## 6.", "## 7.").replace("## 6. Simulated recommendations (prompt c): my critical complement", ""))
        st.markdown("#### What the LLM brought, and what it could not do")
        md(section(comp, "## 7.").replace("## 7. What the LLM brought (time saved, clarity) and what it could not do", "").replace("(Material for the report, §8.2 and §8.4.)", ""))
        with st.expander("Agreement with the expert interpretation"):
            md(section(comp, "## 3.", "## 4."))
    with t[7]:
        live_demo()


def live_demo():
    st.markdown("Ask the **local** model a question about the project, with a section of `stats_summary.md` as its only context. "
                "Runs on this laptop's CPU (≈ 14 tokens/s), so long answers take a few minutes.")
    try:
        tags = requests.get(f"{OLLAMA}/api/tags", timeout=3).json().get("models", [])
        version = requests.get(f"{OLLAMA}/api/version", timeout=3).json().get("version", "?")
    except requests.RequestException:
        st.error("Ollama is not reachable at localhost:11434. Start the Ollama app (or `ollama serve`) and reload.")
        return
    if not tags:
        st.warning("Ollama is running but no model is pulled. Run `ollama pull qwen2.5:3b`.")
        return
    st.success(f"Ollama {version} is running · {len(tags)} model(s) available")
    names = [m["name"] for m in tags]
    c1, c2 = st.columns([1, 2])
    model = c1.selectbox("Model", names, index=names.index("qwen2.5:3b") if "qwen2.5:3b" in names else 0)
    secs = c2.multiselect("Context given to the model (sections of stats_summary.md)", ["0", "A", "B", "C"], default=["0", "C"],
                          format_func=lambda k: {"0": "0 · Data", "A": "A · Descriptive stats", "B": "B · Model results", "C": "C · Forecasts"}[k])
    q = st.text_area("Question", "Using only the tables, does the VECM forecast significantly better than the random walk? Quote the p-value.")
    if st.button("Ask the local model", type="primary"):
        parts = re.split(r"^(?=## )", text("llm/stats_summary.md"), flags=re.M)
        ctx = "\n\n".join(p for p in parts if re.match(rf"## ({'|'.join(secs) or 'X'})\.", p))
        prompt = (f"You are a statistician. Answer in English, briefly, using ONLY the tables below. Do not invent numbers.\n\n{ctx}\n\nQuestion: {q}")

        def stream():
            with requests.post(f"{OLLAMA}/api/chat", stream=True, timeout=(5, 1800),
                               json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": True,
                                     "options": {"num_ctx": 16384, "seed": 42}}) as r:
                for line in r.iter_lines():
                    if line:
                        j = json.loads(line)
                        if "error" in j:
                            yield f"\n\n**Ollama error:** {j['error']}"
                            return
                        yield j.get("message", {}).get("content", "")

        with st.container(border=True):
            st.write_stream(stream())
        st.caption("Check the answer against the tables on the Material tab — the point of the exercise.")


def page_conclusion():
    st.title("Conclusions and limits")
    st.markdown("""
### Answer to the research question
The converted miners **did not leave Bitcoin**: BTC remains their largest same-day driver and their correlation with it barely moves
(DCC 0.50 → 0.48) — and the slight weakening also hits the pure miners. What changed is that they **added an AI factor**: their
same-day response to NVIDIA more than doubles after 22 Jan 2025, while the control group's does not move. They became **hybrid
BTC/AI assets**, not AI stocks.

- **Certainty:** moderate for the short-run shift (consistent across impulse responses, DCC, rolling correlation and the control group);
  low for any long-run tie to NVIDIA (borderline cointegration, only before the pivot).
- **Forecasting:** no model — classical or deep — beats the random walk significantly. The change is visible in co-movements but not exploitable.
- **LLM:** a small local model told the "expected story", read the key test backwards and approved its own errors. Every claim must be checked against the source tables.
""")
    st.markdown("""
### Limits
- **Short post-pivot sample** — 447 days: weak cointegration power, post-pivot GARCH not identified.
- **Pivot date found by scanning** — Chow p-values are optimistic; the transition looks gradual through 2025.
- **Close-time mismatch** — BTC closes 3–4 h after US stocks; affects the Cholesky ordering of impulse responses.
- **Small baskets** — three firms per index; one contract or dilution weighs heavily.
- **Single test regime** — 123 test days, all post-pivot; transaction costs and liquidity not modelled.
- **Granger ≠ causality** — "helps predict" is not economic causation.
""")
    st.caption("Academic project — nothing here is investment advice.")


# ---------------------------------------------------------------------------------------------- navigation
pages = [st.Page(page_overview, title="Overview", default=True),
         st.Page(page_data, title="1 · Data"),
         st.Page(page_eda, title="2 · EDA & pivot"),
         st.Page(page_arima, title="3 · ARIMA"),
         st.Page(page_var, title="4 · VAR / VECM"),
         st.Page(page_garch, title="5 · Volatility"),
         st.Page(page_dl, title="6 · Deep learning"),
         st.Page(page_eval, title="7 · Evaluation"),
         st.Page(page_llm, title="8 · LLM critique"),
         st.Page(page_conclusion, title="Conclusions")]
if __name__ == "__main__":  # `streamlit run` executes the script as __main__; importing it (tests) does not navigate
    with st.sidebar:
        st.markdown("### Bitcoin miners and AI")
        st.caption(f"Pivot {PIVOT} · test {TEST_START} → {TEST_END}")
    st.navigation(pages).run()
