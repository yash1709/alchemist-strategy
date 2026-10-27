"""Alchemist 2026 strategy backtester (replica built from the two videos).

Rules implemented (see STRATEGY.md for the full spec and the assumptions made):
  Track 1: 6 Nifty50 ETFs, each with a fixed day-of-month (1,5,10,15,20,25).
           Lump sum on the first due date, then a monthly SIP on the same day.
  Track 2: the paired Bank Nifty ETF is bought (lump sum) when the Track 1 ETF
           falls 5% below its average buy price, then SIPs monthly.
  Exit:    sell ALL units of an ETF when price >= avg * (1 + 5%).
  Profit:  moved into a Gold ETF that is never sold (or compounded if reinvest=True).
  Bud mode (2026 September update): when capital used > 80%, SIPs stop; instead,
           buy half a SIP in the held ETF that fell >= 3% from its LAST buy price
           (largest fall first), at most one buy per day.

Usage:  python alchemist_backtest.py --start 2022-09-01 --end 2026-01-09 --capital 100000
"""
import argparse
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
import yfinance as yf

# (Nifty ETF, Bank Nifty counterpart, day of month). Order follows the videos'
# 1,5,10,15,20,25 schedule; the video only names NIFTYBEES/BANKBEES and the
# "Nifty I ETF"/"Bank I ETF" explicitly, the rest are assumptions - edit freely.
# Exact codes from the "ETFs Selection" slide of the Jan-2026 video (5:50): top 6 Nifty50 and
# Bank Nifty ETFs by traded volume. Days 1,5,10,15,20,25 follow the table order.
PAIRS = [
    ("NIFTYBEES.NS", "BANKBEES.NS", 1),
    ("NIFTYIETF.NS", "BANKIETF.NS", 5),
    ("SETFNIF50.NS", "SETFNIFBK.NS", 10),
    ("NIFTY1.NS", "BANKNIFTY1.NS", 15),
    ("HDFCNIFTY.NS", "HDFCNIFBAN.NS", 20),
    ("NIFTYBETA.NS", "BANKBETA.NS", 25),
]
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".price_cache")
GOLD = "GOLDBEES.NS"
BENCH = "NIFTYBEES.NS"


@dataclass
class Pos:
    ticker: str
    day: int                 # fixed day-of-month
    units: float = 0.0
    invested: float = 0.0
    last_buy: float = 0.0
    next_due: pd.Timestamp = None   # next lump/SIP calendar date
    active: bool = True      # Track 1: always; Track 2: only after trigger

    @property
    def avg(self):
        return self.invested / self.units if self.units else 0.0


def add_month(d: pd.Timestamp, day: int) -> pd.Timestamp:
    d = d + pd.offsets.MonthBegin(1)
    return d.replace(day=min(day, d.days_in_month))


def xirr(flows):
    """flows: list[(Timestamp, amount)]; simple bisection."""
    if not flows or not any(a > 0 for _, a in flows) or not any(a < 0 for _, a in flows):
        return float("nan")
    t0 = flows[0][0]
    def npv(r):
        return sum(a / (1 + r) ** ((d - t0).days / 365.0) for d, a in flows)
    lo, hi = -0.99, 10.0
    if npv(lo) * npv(hi) > 0:
        return float("nan")
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return mid


def _nse_close(sym, start, end):
    """Daily closes straight from NSE (Yahoo's history for several of these ETFs is truncated)."""
    cache = os.path.join(CACHE_DIR, f"{sym}_{start}_{end}.csv")
    if os.path.exists(cache):
        return pd.read_csv(cache, index_col=0, parse_dates=True).iloc[:, 0]
    from jugaad_data.nse import stock_df
    df = stock_df(symbol=sym, from_date=pd.Timestamp(start).date(), to_date=pd.Timestamp(end).date(), series="EQ")
    s = df.set_index("DATE")["CLOSE"].sort_index().rename(sym + ".NS")
    s.index = pd.to_datetime(s.index)
    os.makedirs(CACHE_DIR, exist_ok=True)
    s.to_csv(cache)
    return s


def split_adjust(s):
    """Back-adjust unit splits/consolidations (one-day moves beyond x5 / x0.2 in an ETF are never real)."""
    s = s.dropna().copy()
    r = s / s.shift(1)
    for dt in r.index[(r < 0.2) | (r > 5)]:
        f = round(1 / r[dt]) if r[dt] < 1 else 1 / round(r[dt])
        s[s.index < dt] *= 1 / f
    return s


def load_prices(tickers, start, end):
    cols = {}
    for t in tickers:
        try:
            cols[t] = _nse_close(t.replace(".NS", ""), start, end)
        except Exception:
            y = yf.Ticker(t).history(start=start, end=end)["Close"].dropna()
            y.index = y.index.tz_localize(None)
            if len(y):
                cols[t] = y
    px = pd.DataFrame({t: split_adjust(s) for t, s in cols.items()}).sort_index()
    return px[px.index >= pd.Timestamp(start)].dropna(how="all")


def run(start, end, capital=100_000.0, lump_pct=0.06, sip_pct=0.016, bud_frac=0.5,
        target=0.05, t2_trigger=-0.05, bud_thresh=0.80, bud_fall=-0.03,
        reinvest=False, use_bud=True, pairs=PAIRS):
    tickers = sorted({t for p in pairs for t in p[:2]} | {GOLD, BENCH})
    px = load_prices(tickers, start, end)
    avail = [t for t in tickers if t in px.columns and px[t].notna().any()]
    pairs = [p for p in pairs if p[0] in avail and p[1] in avail]
    if not pairs:
        raise SystemExit("No ETF pairs with data; edit PAIRS.")
    dropped = sorted(set(tickers) - set(avail))
    if dropped:
        print("No data (skipped):", dropped)
    px = px.ffill()

    days = px.index
    t1 = [Pos(a, d, next_due=pd.Timestamp(start).replace(day=1).replace(day=d)) for a, _, d in pairs]
    # first due date on/after start
    for p in t1:
        while p.next_due < pd.Timestamp(start):
            p.next_due = add_month(p.next_due, p.day)
    t2 = [Pos(b, d, active=False) for _, b, d in pairs]

    gold_units = gold_cost = 0.0
    realized = 0.0
    flows = []          # ETF cash flows for XIRR (gold excluded: funded by profit)
    max_inv, inv_series, n_sells, max_ships = 0.0, [], 0, 0
    sold_log = []
    C = capital

    def price(t, d):
        v = px.at[d, t]
        return None if pd.isna(v) else float(v)

    def buy(pos, amt, d, p):
        qty = max(1, round(amt / p))          # whole units, may slightly overshoot (as in videos)
        cost = qty * p
        pos.units += qty
        pos.invested += cost
        pos.last_buy = p
        flows.append((d, -cost))

    def all_pos():
        return t1 + t2

    for d in days:
        used = sum(x.invested for x in all_pos())
        mode = "BUD" if (use_bud and used > bud_thresh * C) else "SHIP"
        lump, sip, bud = lump_pct * C, sip_pct * C, sip_pct * C * bud_frac

        # ---- scheduled buys (Track 1 and active Track 2) ----
        for pos in all_pos():
            p = price(pos.ticker, d)
            if p is None or not pos.active or d < pos.next_due:
                continue
            if pos.units == 0:                       # flat: lump restart (ship mode only)
                if mode == "SHIP" and pos in t1:
                    buy(pos, lump, d, p)
                    pos.next_due = add_month(d, pos.day)
                elif pos in t2:
                    pass
            elif mode == "SHIP":                     # SIP
                buy(pos, sip, d, p)
                pos.next_due = add_month(d, pos.day)

        # ---- Track 2 trigger: Track 1 ETF 5% under its average ----
        for a, b in zip(t1, t2):
            pa, pb = price(a.ticker, d), price(b.ticker, d)
            if a.units and pa is not None and pb is not None and b.units == 0 and not b.active:
                if pa <= a.avg * (1 + t2_trigger) and mode == "SHIP":
                    b.active = True
                    buy(b, lump, d, pb)
                    b.next_due = add_month(d, d.day)
                    b.day = d.day

        # ---- Bud mode: one buy per day, deepest fall from last buy ----
        if mode == "BUD":
            cands = []
            for pos in all_pos():
                p = price(pos.ticker, d)
                if p is not None and pos.units and p / pos.last_buy - 1 <= bud_fall:
                    cands.append((p / pos.last_buy - 1, pos, p))
            if cands:
                _, pos, p = min(cands, key=lambda c: c[0])
                buy(pos, bud, d, p)

        # ---- sells ----
        for pos in all_pos():
            p = price(pos.ticker, d)
            if p is None or not pos.units:
                continue
            if p >= pos.avg * (1 + target):
                proceeds = pos.units * p
                profit = proceeds - pos.invested
                flows.append((d, proceeds))
                realized += profit
                n_sells += 1
                sold_log.append((d, pos.ticker, pos.invested, proceeds, profit))
                if reinvest:
                    C += profit
                else:
                    g = price(GOLD, d)
                    if g:
                        q = profit / g
                        gold_units += q
                        gold_cost += profit
                pos.units = pos.invested = pos.last_buy = 0.0
                if pos in t2:
                    pos.active = False

        cur = sum(x.invested for x in all_pos())
        max_inv = max(max_inv, cur)
        inv_series.append(cur)

    last = days[-1]
    open_val = sum(x.units * price(x.ticker, last) for x in all_pos() if x.units)
    open_cost = sum(x.invested for x in all_pos())
    flows.append((last, open_val))
    gold_val = gold_units * price(GOLD, last) if gold_units else 0.0
    overall = realized + (open_val - open_cost) + (gold_val - gold_cost)

    bench = px[BENCH].dropna()
    bench_ret = bench.iloc[-1] / bench.iloc[0] - 1

    print(f"\nPeriod: {days[0].date()} -> {last.date()}   capital: {capital:,.0f}   reinvest={reinvest}")
    print(f"Sells booked: {n_sells}   Realised ETF profit: {realized:,.0f}")
    print(f"Open ETF value: {open_val:,.0f} (cost {open_cost:,.0f})   Max invested: {max_inv:,.0f}   "
          f"Avg invested: {np.mean(inv_series):,.0f}")
    print(f"Gold value: {gold_val:,.0f} (cost {gold_cost:,.0f})")
    print(f"OVERALL profit: {overall:,.0f}  = {overall / capital:.2%} of capital")
    print(f"XIRR (ETF legs only): {xirr(sorted(flows)):.2%}")
    print(f"Benchmark lump-sum {BENCH}: {bench_ret:.2%}")
    return pd.DataFrame(sold_log, columns=["date", "etf", "cost", "proceeds", "profit"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2022-09-01")
    ap.add_argument("--end", default="2026-01-09")
    ap.add_argument("--capital", type=float, default=100_000)
    ap.add_argument("--target", type=float, default=0.05)
    ap.add_argument("--no-bud", action="store_true")
    ap.add_argument("--reinvest", action="store_true")
    a = ap.parse_args()
    log = run(a.start, a.end, a.capital, target=a.target, use_bud=not a.no_bud, reinvest=a.reinvest)
    log.to_csv("sold_log.csv", index=False)
    print("Trade log -> sold_log.csv")
