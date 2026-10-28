# FP&A Analytics for a Brokerage — Monthly Close, Daily Flash & Client Revenue

**One-liner:** A rules-based FP&A analytics project (flux explainer, daily P&L flash pipeline, client-revenue dashboards, board deck, exec reporting) built on fully synthetic data for a fictional brokerage.

## Honest-fit framing — read this first

The target role is a **pure FP&A role with NO ML requirements** (FP&A Consultant, monthly close flux analysis, daily P&L flash reporting, client revenue dashboards, board decks, exec reporting; tools Excel, PowerPoint, Databricks, Claude/AI tools). **This project is therefore deliberately framed as an analytics + forecasting project, NOT deep learning or LLM work.** There is no deep-learning model and no LLM component, and none is claimed. The core is a **rules-based flux explainer** with documented materiality thresholds and driver attribution, plus a transparent numpy OLS trend+seasonal forecast benchmarked against a naive seasonal baseline. A rules-based explainer beating a black-box model on this data would be a feature, not a weakness: it is auditable, explainable to auditors and executives, and it never invents a driver it cannot support. On this synthetic data the OLS model beats the naive baseline on 5 of 6 lines (see Results) — and where it loses (commissions), that loss is reported, not hidden.

## Problem statement

Close and flash reporting done by hand is slow, narrative-heavy, and hard to reproduce: variance tables show *what* moved but not *why*, daily flash totals arrive without movers or flags, and client revenue is rarely tied back to the P&L move it caused. This project automates all three with one seeded, reproducible pipeline.

## Dataset — ALL SYNTHETIC, fictional firm

- **Firm:** NorthPeak Securities (fictional). The DriveWealth name never appears in any dataset, and **no figure in this project is real DriveWealth data**.
- **Monthly close:** 24 months, Jan 2024–Dec 2025, actuals + budget. 5 revenue lines (commissions, payment for order flow, margin interest, platform/subscription fees, custody fees) and 5 cost lines (clearing, compensation, technology, occupancy, one-offs). 240 rows.
- **Clients:** 42 fictional clients (24 retail, 11 institutional including the Sep-2025 onboarding client, 6 introducing brokers, 1 offboarded retail client), 1,008 client-months.
- **Daily flash:** 90 days, 2025-10-02 to 2025-12-30, full P&L line breakdown per day.
- **Drivers:** monthly trading volume, fee per account, active accounts.
- **Injected ground truth (invented for testing only, never real events):** Jun 2024 volume spike; Mar 2025 fee-schedule change; Jul 2025 one-off legal expense ($285,000); Sep 2025 large institutional client onboarding (C041, $151,421 in its first month). The flux explainer is scored against these — it recovers all four (see tests).
- **Reproducibility:** `python -m src.data_gen --seed 42` regenerates identical files.

## How to run (step by step)

```bash
# Use the project environment (pandas, numpy, matplotlib, reportlab, python-pptx)
~/workspace/quant-ipo-engine/.venv/bin/python -m src.data_gen --seed 42
~/workspace/quant-ipo-engine/.venv/bin/python -m src.flux --month 2025-09   # or --latest
~/workspace/quant-ipo-engine/.venv/bin/python -m src.flash --date 2025-12-30
~/workspace/quant-ipo-engine/.venv/bin/python -m src.forecast
~/workspace/quant-ipo-engine/.venv/bin/python -m src.dashboard   # reports/dashboard.html
~/workspace/quant-ipo-engine/.venv/bin/python -m src.deck        # 10-slide deck
~/workspace/quant-ipo-engine/.venv/bin/python build_notebooks.py # executed notebooks
~/workspace/quant-ipo-engine/.venv/bin/python build_report.py    # PDF final report
~/workspace/quant-ipo-engine/.venv/bin/python -m unittest discover -s tests -v
```

Open `reports/dashboard.html` directly in a browser — no server needed.

## Results summary (REAL numbers from actual runs, seed 42)

- **Latest month (Dec 2025, synthetic):** revenue $2,663,624; costs $2,005,968; net P&L $657,655.
- **Flash example (2025-12-30, synthetic):** revenue $82,529; costs $59,315; net P&L $23,214. MTD (30 days): revenue $2,404,761; net P&L $658,966. One flag: one_offs +91.1% day-over-day (≥20% threshold).
- **Flux ground-truth recovery: 4/4.** Jun 2024 commissions +$227,310 (+25.4%) → "Volume" (volume +43.6%); Mar 2025 platform fees +$67,556 (+20.7%) → "Price (fee schedule)" (fee/account +21.4%); Jul 2025 one_offs $285,000 → "One-off" (vs $26,870 median); Sep 2025 client note → onboarding C041 (+$151,421).
- **Daily P&L anomaly flagger (|z| > 3, rolling 30-day): 0 flags in the 90-day window** — reported as-is; the window is calm by construction.
- **Forecast hold-out, Oct–Dec 2025 (OLS trend+seasonal vs naive same-month-last-year):**

| Line | OLS MAPE | Naive MAPE | OLS RMSE | Naive RMSE | OLS wins? |
|---|---|---|---|---|---|
| commissions | 5.04% | 4.59% | $46,639 | $45,549 | No — baseline wins |
| payment_for_order_flow | 3.00% | 3.92% | $21,179 | $33,794 | Yes |
| margin_interest | 1.67% | 8.01% | $9,250 | $42,515 | Yes |
| platform_fees | 2.38% | 22.79% | $10,695 | $90,299 | Yes |
| custody_fees | 3.74% | 6.93% | $9,137 | $16,206 | Yes |
| **total_revenue** | **1.21%** | **7.98%** | **$37,300** | **$216,515** | **Yes** |

OLS beats the baseline on 5 of 6 lines. The commissions miss is honest: with only 21 training months and a noisy volume-driven line, the naive seasonal baseline wins that line by 0.45pp of MAPE.

## The five JD focuses — where the evidence is

1. **Monthly close flux analysis** — `src/flux.py`, `reports/flux_YYYY-MM.md`. Variance vs prior month AND vs budget; materiality |variance| ≥ $25,000 AND ≥ 5% (one-offs also > 3× median).
2. **Daily P&L flash reporting** — `src/flash.py`, `reports/flash_YYYY-MM-DD.md/.csv`. Day vs prior day vs MTD, top movers, ≥20% and |z| > 2 flags.
3. **Client revenue dashboards** — `src/dashboard.py` (segment + top-8-client charts), `data/synthetic/client_monthly_revenue.csv`.
4. **Board decks** — `src/deck.py` → `reports/DriveWealth_FPA_Consultant_Deck.pptx`, exactly 10 slides.
5. **Exec reporting** — `reports/exec_summary.md` (one page) and `reports/DriveWealth_FPA_Project_Report.pdf`.

## Limitations — stated openly

- **All data are synthetic.** Nothing here validates against a real close, real clients, or real DriveWealth figures; thresholds and model performance would need re-validation on real data.
- **No sklearn, scipy, pytest, or Streamlit** in this environment (and none is claimed): tests use stdlib `unittest`, regression uses numpy OLS, the dashboard is standalone HTML with matplotlib PNGs — not Streamlit.
- **No Databricks** in this build: the pipeline is local Python replicating what a Databricks/SQL pipeline would do; a Databricks port is listed as future work.
- **No real client data** and no access to any employer's systems; client names are generic fictional labels.
- **OLS limits:** 21 training months, one trend + annual seasonality, no exogenous drivers (volume, rates) in the forecast itself; the 3-month hold-out is small, so MAPE differences under ~1pp should not be over-read.
- **Anomaly flagger:** 0 flags in 90 calm synthetic days is not evidence it works on stressed data — it was not stress-tested with injected daily anomalies.
- **Deck GitHub link is a placeholder** by design — no URL is invented.

## Tests

5 stdlib unittest tests, all passing (verified run): flux ground-truth recovery; flash totals reconcile to source data; forecast returns finite metrics; dashboard builds non-empty HTML containing KPI values; deck has 10 slides.

## Author

Bhupesh Chandra Dimri — bhupesh7cd@gmail.com
