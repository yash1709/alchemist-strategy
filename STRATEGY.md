# Alchemist Strategy (2026 version) – Playbook

An ETF accumulation system on Nifty 50, Bank Nifty and Gold. No stock picking, no charts, no indicators.
Not investment advice; any profit or loss is yours.

## 1. Setup (once)

**Total capital (C)** – the amount you commit, e.g. Rs 1,00,000.

| Amount | Formula | Example (C = 1L) |
|---|---|---|
| Lump sum | 6% of C | Rs 6,000 |
| SIP | 1.6% of C | Rs 1,600 |
| Bud buy | 50% of SIP | Rs 800 |

**ETF pairs** – each Nifty ETF (Track 1) has a fixed buy day and a Bank Nifty partner (Track 2):

| Buy day | Track 1 (Nifty 50) | Track 2 partner (Bank Nifty) |
|---|---|---|
| 1st | NIFTYBEES | BANKBEES |
| 5th | NIFTYIETF | BANKIETF |
| 10th | SETFNIF50 | SETFNIFBK |
| 15th | NIFTY1 | BANKNIFTY1 |
| 20th | HDFCNIFTY | HDFCNIFBAN |
| 25th | NIFTYBETA | BANKBETA |

**Gold ETF** (e.g. GOLDBEES) – where booked profits are parked.

If a buy day falls on a weekend or market holiday, buy on the next trading day.

## 2. Track 1 – Nifty ETFs (calendar driven)

1. **Start:** on a buy day, put one lump sum into that day's ETF. Start the next ETF on its own buy day (every 5 days, so you can begin mid-month).
2. **SIP:** each following month, on the same buy day, add one SIP to that ETF.
3. **Exit:** the moment price >= **average cost x 1.05**, sell ALL units of that ETF. No trailing stops.
4. **Restart:** that ETF starts over with a lump sum on its buy day:
   - sold before its buy day this month -> restart this month
   - sold on or after its buy day -> restart next month

## 3. Track 2 – Bank Nifty ETFs (dip driven)

1. **Trigger:** when a Track 1 ETF falls **5% below its average cost** (not below its all-time high), buy one lump sum of its Bank Nifty partner that day.
2. **SIP:** add one SIP to that partner on the same day each following month.
3. **Exit:** same as Track 1: sell everything at average cost x 1.05.
4. **Reset:** the partner stays inactive until its Track 1 ETF triggers again.

## 4. Profit handling

- Every booked profit is used to buy the Gold ETF. Never sell gold; it is the long-term accumulator and diversifier.
- Optional: take ~20% of post-tax profit as personal "income" before investing the rest.
- If instead you want to compound inside the strategy, add the profit to C. Do not do both.

## 5. Bud mode (capital protection)

Switch **when more than 80% of C is deployed** in Track 1 + Track 2 (sideways/bear market):

- **Stop SIPs.** Use the Bud buy (50% of SIP) instead.
- **Bud rule:** buy any held ETF that is >= **3% below its LAST buy price** (not its average).
- If several qualify, buy only the one that fell the most. **One Bud buy per day.**
- Return to normal SIP mode when deployed capital drops back to 80% or below.
- If capital hits 100%, lower the sell target (5% -> 4% -> 3%) to free capital, then restore it.

## 6. Daily / monthly checklist

Daily (after market):
1. Any Track 1 ETF at +5% over average? -> sell all, buy Gold with the profit.
2. Any Track 2 ETF at +5%? -> same.
3. Any Track 1 ETF 5% under average with an inactive partner? -> lump-sum the partner.
4. Bud mode on? -> find the largest fall below -3% from last buy; make one Bud buy.

On each buy day:
5. Flat ETF -> lump sum. Held ETF -> SIP (skip SIPs if in Bud mode).

Record for every ETF: units, total invested, average cost, last buy price, next buy date.

## 7. Parameters you may tune

| Parameter | Default |
|---|---|
| Lump sum / SIP | 6% / 1.6% of C |
| Sell target | 5% |
| Track 2 trigger | -5% vs average |
| Bud mode on at | > 80% deployed |
| Bud buy size / fall | 50% of SIP / -3% vs last buy |
| Gold | GOLDBEES, never sold |

## 8. Reference results (past, not a promise)

1-Sep-2022 to 9-Jan-2026, Rs 1L: Nifty lump sum ~+54%; Alchemist ~+77% (video, SIP mode). My replica
(`alchemist_backtest.py`) gave ~75% in SIP mode and ~66% with Bud mode, which trades return for safer capital use.
Sources: Fire in India "Alchemist 2026" videos (Jan and Sep 2026), originated by Mahesh Kaushik.
