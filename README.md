# Alchemist Strategy

A rule-based ETF accumulation strategy on **Nifty 50**, **Bank Nifty** and **Gold** ETFs, with a backtester and a Google Sheets tracker. No stock picking, no charts, no indicators.

The strategy originates with Mahesh Kaushik (2022) and was enhanced by the "Fire in India" channel in its *Alchemist 2026* videos (January and September 2026). This repository is an independent re-implementation built from those videos. It is not affiliated with the author, and it is not investment advice. Any profit or loss is yours.

## The strategy in 60 seconds

- **Sizing** (of total capital): lump sum = 6%, monthly SIP = 1.6%, Bud buy = 50% of a SIP.
- **Track 1:** six Nifty 50 ETFs, each with a fixed buy day (1, 5, 10, 15, 20, 25). Lump sum first, then a monthly SIP on the same day.
- **Track 2:** when a Nifty ETF falls 5% below its *average cost*, lump-sum its paired Bank Nifty ETF and SIP it monthly.
- **Exit:** when an ETF reaches average cost +5%, sell all its units. Restart on its buy day (this month if sold before the day, otherwise next month).
- **Profit:** every booked profit buys a Gold ETF that is never sold.
- **Bud mode:** once more than 80% of capital is deployed, stop SIPs. Buy half a SIP in the held ETF that fell at least 3% below its *last buy price* (largest fall first, one buy per day).

Full rules, parameters and a daily checklist are in [STRATEGY.md](STRATEGY.md).

| Buy day | Track 1 (Nifty 50) | Track 2 (Bank Nifty) |
|---|---|---|
| 1 | NIFTYBEES | BANKBEES |
| 5 | NIFTYIETF | BANKIETF |
| 10 | SETFNIF50 | SETFNIFBK |
| 15 | NIFTY1 | BANKNIFTY1 |
| 20 | HDFCNIFTY | HDFCNIFBAN |
| 25 | NIFTYBETA | BANKBETA |

The ETF codes come from the "ETFs Selection" slide of the January video. The day assigned to each pair follows the order of that table.

## Repository contents

| File | Purpose |
|---|---|
| `STRATEGY.md` | The strategy playbook: rules, parameters, checklist |
| `alchemist_backtest.py` | Backtester (NSE prices, split-adjusted) |
| `build_tracker.py` | Generates the Google Sheets / Excel tracker |
| `Alchemist_Tracker.xlsx` | The generated tracker, ready to upload |
| `requirements.txt` | Python dependencies |

## Backtester

```bash
pip install -r requirements.txt

# January-video rules (SIP mode only)
python alchemist_backtest.py --start 2022-09-01 --end 2026-01-09 --capital 100000 --no-bud

# With the September Bud-mode update
python alchemist_backtest.py --start 2022-09-01 --end 2026-01-09 --capital 100000
```

Options: `--capital`, `--target` (sell target, default 0.05), `--no-bud`, `--reinvest` (compound profits instead of buying gold). Trades are written to `sold_log.csv`.

Price data comes from NSE through `jugaad-data`, cached in `.price_cache/`. ETF unit splits (for example HDFCNIFBAN and NIFTYBETA) are back-adjusted automatically. Yahoo Finance is used only as a fallback because its history for several of these ETFs is truncated.

### Results (1 Sep 2022 to 8 Jan 2026, Rs 1 lakh)

| Run | Overall profit | Realised ETF profit |
|---|---|---|
| Video claim (SIP mode) | 77.3% | about Rs 40.6k |
| This replica, `--no-bud` | 75.4% | Rs 39.3k |
| This replica, with Bud mode | 66.5% | Rs 33.7k |
| Nifty lump sum (NIFTYBEES) | about 52% | n/a |

"Overall profit" is realised ETF profit plus unrealised ETF profit plus the gain on the gold bought with booked profits, as a share of starting capital. The remaining 2-point gap to the video likely comes from fills at the daily close here (the author uses real broker prices), whole-unit rounding, one day less of data, and BANKIETF only having NSE history from December 2023. Past results are not a promise.

### Backtest assumptions

- Fills at the daily close, whole units, no brokerage or tax.
- In Bud mode, flat Track 1 ETFs do not restart with a lump sum, and the Track 2 trigger is paused. The videos don't specify either case.
- Profit is invested in GOLDBEES on the day it is booked and never sold.

## Tracker (Google Sheets)

`Alchemist_Tracker.xlsx` is a formula-driven tracker:

- **Dashboard:** positions, average cost, sell targets, next due dates, and an **ACTION** column (`SELL ALL`, `BUY PARTNER`, `BUD BUY #n`, `SIP due`, `LUMP due`), plus profit summary.
- **Settings:** capital and all tunable percentages; the ETF pair table.
- **Trades:** your log of real fills; realised profit per sell is calculated.
- **Gold:** gold purchases and value.
- **Guide:** the daily routine.

To use it, upload the file to Google Drive and open it with Google Sheets. Live prices use `GOOGLEFINANCE`; type a value in the *Manual price* column to override it, or if you use Excel. To regenerate it after changing the layout:

```bash
python build_tracker.py Alchemist_Tracker.xlsx
```

## Limitations

- Holiday-shifted buy dates are not tracked; the tracker shows "due" from the date onward.
- The exact ETF-to-day mapping is inferred from the slide order.
- Backtests use one historical path in a mostly rising market; the strategy's behaviour in a long bear market is untested here.

## Disclaimer

For education only. This is not financial advice, and the author of this repository is not a registered adviser. Do your own research and invest at your own risk.
