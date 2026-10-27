"""Streamlit front-end for the Alchemist strategy backtester."""
import os
import warnings

import pandas as pd
import streamlit as st

warnings.filterwarnings("ignore")
import alchemist_backtest as A  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="Alchemist Strategy", page_icon="🧪", layout="wide")
st.title("Alchemist Strategy")
st.caption("Backtester for the Nifty 50 / Bank Nifty / Gold ETF accumulation strategy. "
           "Educational only, not investment advice.")


@st.cache_data(show_spinner=False)
def bounds():
    snap = pd.read_csv(A.SNAPSHOT, index_col=0, parse_dates=True)
    return snap.index.min().date(), snap.index.max().date()


@st.cache_data(show_spinner="Running backtest...")
def backtest(start, end, capital, target, t2, bud_on, bud_thresh, bud_fall, lump, sip, reinvest):
    return A.run(str(start), str(end), capital, lump_pct=lump, sip_pct=sip, target=target,
                 t2_trigger=t2, use_bud=bud_on, bud_thresh=bud_thresh, bud_fall=bud_fall,
                 reinvest=reinvest, verbose=False)


tab_bt, tab_rules, tab_cmp = st.tabs(["Backtest", "Strategy rules", "Compare modes"])

lo, hi = bounds()
with st.sidebar:
    st.header("Parameters")
    start = st.date_input("Start", pd.Timestamp("2022-09-01").date(), min_value=lo, max_value=hi)
    end = st.date_input("End", pd.Timestamp("2026-01-09").date(), min_value=lo, max_value=hi)
    capital = st.number_input("Total capital (Rs)", 10_000, 100_000_000, 100_000, step=10_000)
    lump = st.number_input("Lump sum, % of capital", 1.0, 20.0, 6.0, 0.5) / 100
    sip = st.number_input("SIP, % of capital", 0.2, 10.0, 1.6, 0.2) / 100
    target = st.number_input("Sell target, %", 1.0, 20.0, 5.0, 0.5) / 100
    t2 = -st.number_input("Track 2 trigger: fall vs average, %", 1.0, 30.0, 5.0, 0.5) / 100
    bud_on = st.toggle("Bud mode (Sept 2026 update)", value=False)
    bud_thresh = st.slider("Bud mode starts above % deployed", 50, 100, 80) / 100
    bud_fall = -st.number_input("Bud buy: fall vs last buy, %", 1.0, 15.0, 3.0, 0.5) / 100
    reinvest = st.toggle("Compound profits (instead of buying gold)", value=False)
    st.caption(f"Price data: {lo} to {hi}")

if start >= end:
    st.error("Start must be before end.")
    st.stop()

args = (start, end, float(capital), target, t2, bud_on, bud_thresh, bud_fall, lump, sip, reinvest)
res = backtest(*args)

with tab_bt:
    c = st.columns(5)
    c[0].metric("Overall profit", f"{res['overall_pct']:.1%}", f"Rs {res['overall']:,.0f}")
    c[1].metric("Nifty lump sum", f"{res['benchmark_pct']:.1%}")
    c[2].metric("XIRR (ETF legs)", f"{res['xirr']:.1%}")
    c[3].metric("Sells booked", res["sells"])
    c[4].metric("Max deployed", f"Rs {res['max_invested']:,.0f}")

    c = st.columns(4)
    c[0].metric("Realised ETF profit", f"Rs {res['realized']:,.0f}")
    c[1].metric("Open ETF cost", f"Rs {res['open_cost']:,.0f}")
    c[2].metric("Gold value", f"Rs {res['gold_value']:,.0f}", f"cost Rs {res['gold_cost']:,.0f}")
    c[3].metric("Days in Bud mode", res["bud_days"])

    s = res["series"]
    st.subheader("Profit vs Nifty lump sum (Rs)")
    st.line_chart(s[["profit", "benchmark_profit"]].rename(
        columns={"profit": "Alchemist", "benchmark_profit": "Nifty lump sum"}))
    st.subheader("Capital deployed (Rs)")
    st.area_chart(s[["deployed"]])

    st.subheader("Booked trades")
    log = res["log"].copy()
    if len(log):
        log["return"] = log["profit"] / log["cost"]
        st.dataframe(log.style.format({"cost": "{:,.0f}", "proceeds": "{:,.0f}",
                                       "profit": "{:,.0f}", "return": "{:.1%}"}),
                     width="stretch", hide_index=True)
        st.download_button("Download trades (CSV)", log.to_csv(index=False), "alchemist_trades.csv")
        by = log.groupby("etf")["profit"].agg(["count", "sum"]).rename(columns={"count": "sells", "sum": "profit"})
        st.bar_chart(by["profit"])
    else:
        st.info("No sells in this period.")

    with st.expander("ETF pairs used"):
        st.table(pd.DataFrame(res["pairs"], columns=["Track 1", "Track 2", "Buy day"])
                 .assign(**{"Track 1": lambda d: d["Track 1"].str.replace(".NS", "", regex=False),
                            "Track 2": lambda d: d["Track 2"].str.replace(".NS", "", regex=False)}))
    st.caption("Fills at daily close, whole units, no brokerage or tax. Past results are not a promise.")

with tab_rules:
    with open(os.path.join(HERE, "STRATEGY.md"), encoding="utf-8") as f:
        st.markdown(f.read())

with tab_cmp:
    st.write("Same period and capital, SIP-only (January video) versus Bud mode (September update).")
    rows = {}
    for label, bud in (("SIP only", False), ("With Bud mode", True)):
        r = backtest(start, end, float(capital), target, t2, bud, bud_thresh, bud_fall, lump, sip, reinvest)
        rows[label] = {
            "Overall profit": r["overall_pct"], "XIRR": r["xirr"], "Sells": r["sells"],
            "Max deployed": r["max_invested"], "Avg deployed": r["avg_invested"],
        }
    df = pd.DataFrame(rows).T
    st.dataframe(df.style.format({"Overall profit": "{:.1%}", "XIRR": "{:.1%}", "Sells": "{:.0f}",
                                  "Max deployed": "{:,.0f}", "Avg deployed": "{:,.0f}"}),
                 width="stretch")
    st.caption(f"Nifty lump sum over the same period: {res['benchmark_pct']:.1%}")
