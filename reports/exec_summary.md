# Executive Summary — FP&A Analytics for a Brokerage (SYNTHETIC DATA)

**Fictional firm:** NorthPeak Securities. **All figures synthetic; no real company data.**

## Headline numbers (actual runs, seed 42)

- **Dec 2025 (latest close month):** revenue $2,663,624; costs $2,005,968; net P&L $657,655.
- **Daily flash, 2025-12-30:** revenue $82,529; net P&L $23,214. MTD net P&L $658,966 (30 days). Flag: one_offs +91.1% day-over-day.
- **Client revenue, Dec 2025 (client-attributed subset):** institutional $1,209,120; retail $490,209; introducing brokers $477,245. Top client C030 $150,586.

## What was built

A rules-based FP&A pipeline: monthly close flux explainer (variance vs prior month and vs budget, plain-English driver per material line), daily P&L flash generator (movers + flags), client-revenue dashboard (standalone HTML), a 10-slide board deck, and a numpy OLS forecast benchmarked against a naive seasonal baseline.

## Flux explainer: 4/4 injected events recovered

Jun 2024 volume spike → commissions; Mar 2025 fee-schedule change → platform fees; Jul 2025 one-off legal expense ($285,000) → one_offs; Sep 2025 onboarding (C041, +$151,421) → client note. These events are invented test fixtures, not real events.

## Forecast: OLS beats naive on 5 of 6 lines (hold-out Oct–Dec 2025)

Total revenue: OLS MAPE 1.21% vs naive 7.98%. Honest exception: commissions, where naive wins (4.59% vs OLS 5.04%). Daily anomaly flagger (|z| > 3): 0 flags in 90 days.

## Limitations

Synthetic data only; no sklearn/Databricks/Streamlit in this build; OLS trained on 21 months with a 3-month hold-out; no real client data; deck GitHub link is a placeholder. Tests: 5/5 passing (stdlib unittest).

**Author:** Bhupesh Chandra Dimri — bhupesh7cd@gmail.com
