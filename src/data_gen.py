"""Synthetic data generator for a FICTIONAL brokerage, NorthPeak Securities.

All data are SYNTHETIC. Nothing here is real DriveWealth data, and the
DriveWealth name never appears in any dataset produced by this module.

Design
------
* 24 months of monthly close data, Jan 2024 - Dec 2025, actuals + budget.
* 5 revenue lines, 5 cost lines shaped like a brokerage P&L.
* 40 fictional clients across retail / institutional / introducing-broker
  segments, with monthly revenue per client.
* 90 days of daily P&L flash data (2025-10-02 to 2025-12-30).
* Monthly business drivers (volume, fee per account, accounts).
* Four KNOWN injected flux events, recorded in ground_truth_events.csv,
  so the flux explainer can be scored against truth. These are invented
  for testing only -- never real events.

Deterministic: same --seed always produces the same files.
"""
import argparse
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "synthetic")

REVENUE_LINES = {
    "commissions": 820_000,
    "payment_for_order_flow": 610_000,
    "margin_interest": 480_000,
    "platform_fees": 310_000,
    "custody_fees": 210_000,
}
COST_LINES = {
    "clearing": 390_000,
    "compensation": 880_000,
    "technology": 340_000,
    "occupancy": 150_000,
    "one_offs": 25_000,
}
SEGMENTS = ["retail", "institutional", "introducing_broker"]

# Injected ground-truth events: (month, line, event, keyword for tests)
EVENTS = [
    ("2024-06", "commissions", "volume_spike",
     "Trading-volume spike: retail trading volumes surged in June 2024."),
    ("2025-03", "platform_fees", "fee_schedule_change",
     "Fee-schedule change: platform fee per account stepped up from March 2025."),
    ("2025-07", "one_offs", "one_off_legal_expense",
     "One-off legal expense booked in July 2025."),
    ("2025-09", "institutional_revenue", "client_onboarding",
     "Client onboarding: a large institutional client onboarded in September 2025."),
]


def build_clients(rng):
    rows = []
    # Segment mix: 24 retail, 10 institutional, 6 introducing brokers.
    counts = {"retail": 24, "institutional": 10, "introducing_broker": 6}
    bases = {"retail": 18_000, "institutional": 95_000, "introducing_broker": 70_000}
    cid = 1
    for seg, n in counts.items():
        for i in range(n):
            base = bases[seg] * rng.uniform(0.55, 1.6)
            rows.append({
                "client_id": f"C{cid:03d}",
                "client_name": f"Fictional {seg.replace('_', ' ').title()} Client {i + 1}",
                "segment": seg,
                "base_monthly_revenue": round(float(base), 2),
                "onboard_month": "2024-01",
            })
            cid += 1
    # The onboarding event client: starts Sep 2025, large institutional.
    rows.append({
        "client_id": "C041",
        "client_name": "Fictional Institutional Client Onboarded Sep 2025",
        "segment": "institutional",
        "base_monthly_revenue": 145_000.0,
        "onboard_month": "2025-09",
    })
    # One small retail client offboards after Oct 2024 (secondary signal).
    rows.append({
        "client_id": "C042",
        "client_name": "Fictional Retail Client Offboarded Nov 2024",
        "segment": "retail",
        "base_monthly_revenue": 12_000.0,
        "onboard_month": "2024-01",
    })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    os.makedirs(OUT, exist_ok=True)

    months = pd.period_range("2024-01", "2025-12", freq="M")
    month_strs = [str(m) for m in months]
    t = np.arange(len(months), dtype=float)
    # Annual seasonality: Q1 soft, Q4 strong.
    seasonal = 1 + 0.06 * np.sin(2 * np.pi * (t - 2) / 12.0)

    # --- Drivers -----------------------------------------------------------
    volume = 2_400_000 * (1 + 0.012 * t) * seasonal * rng.normal(1, 0.03, len(t))
    volume[5] *= 1.38  # Jun 2024 volume spike (index 5)
    fee_per_acct = np.full(len(t), 42.0)
    fee_per_acct[14:] = 51.0  # Mar 2025 fee-schedule change (index 14)
    accounts = 118_000 * (1 + 0.008 * t) * rng.normal(1, 0.01, len(t))
    drivers = pd.DataFrame({
        "month": month_strs,
        "trading_volume_m": np.round(volume / 1e6, 3),
        "trading_volume": np.round(volume, 0),
        "fee_per_account": fee_per_acct,
        "active_accounts": np.round(accounts, 0),
    })
    drivers.to_csv(os.path.join(OUT, "drivers.csv"), index=False)

    # --- Monthly close -----------------------------------------------------
    rows = []
    for i, m in enumerate(month_strs):
        growth = 1 + 0.006 * i
        for line, base in REVENUE_LINES.items():
            budget = base * growth * seasonal[i]
            actual = budget * rng.normal(1, 0.025)
            if line == "commissions" and m == "2024-06":
                actual *= 1.24
            if line == "platform_fees" and i >= 14:
                # Fee step-up: ~21% on the fee-driven portion, net ~+18%.
                actual = budget * 1.18 * rng.normal(1, 0.02)
            if line == "payment_for_order_flow" and m == "2024-06":
                actual *= 1.12
            rows.append({"month": m, "line": line, "category": "revenue",
                         "actual": round(float(actual), 2),
                         "budget": round(float(budget), 2)})
        for line, base in COST_LINES.items():
            budget = base * growth
            actual = budget * rng.normal(1, 0.02)
            if line == "one_offs" and m == "2025-07":
                actual = 285_000.0  # one-off legal expense
            rows.append({"month": m, "line": line, "category": "cost",
                         "actual": round(float(actual), 2),
                         "budget": round(float(budget), 2)})
    monthly = pd.DataFrame(rows)
    monthly.to_csv(os.path.join(OUT, "monthly_close.csv"), index=False)

    # --- Client monthly revenue -------------------------------------------
    clients = build_clients(rng)
    clients.to_csv(os.path.join(OUT, "clients.csv"), index=False)
    # Scale client revenue so segment totals are plausible vs P&L totals:
    # client revenue is a subset view (client-attributed revenue), not a
    # second P&L; it sums to roughly 55% of total revenue each month.
    crow = []
    for _, c in clients.iterrows():
        onboard_idx = month_strs.index(c["onboard_month"])
        for i, m in enumerate(month_strs):
            if i < onboard_idx:
                rev = 0.0
            elif c["client_id"] == "C042" and i >= 10:  # offboarded Nov 2024
                rev = 0.0
            else:
                rev = c["base_monthly_revenue"] * (1 + 0.004 * i) \
                    * seasonal[i] * rng.normal(1, 0.05)
            crow.append({"month": m, "client_id": c["client_id"],
                         "segment": c["segment"], "revenue": round(float(rev), 2)})
    client_monthly = pd.DataFrame(crow)
    client_monthly.to_csv(os.path.join(OUT, "client_monthly_revenue.csv"), index=False)

    # --- Daily flash (90 days) ---------------------------------------------
    days = pd.date_range("2025-10-02", periods=90, freq="D")
    drows = []
    for d in days:
        dow = d.dayofweek
        wk = 0.88 if dow >= 5 else 1.0  # weekend dip
        rev = {}
        rev["commissions"] = 27_000 * wk * rng.normal(1, 0.12)
        rev["payment_for_order_flow"] = 20_000 * wk * rng.normal(1, 0.10)
        rev["margin_interest"] = 16_000 * rng.normal(1, 0.05)
        rev["platform_fees"] = 12_000 * rng.normal(1, 0.04)
        rev["custody_fees"] = 7_000 * rng.normal(1, 0.04)
        costs = {
            "clearing": 13_000 * wk * rng.normal(1, 0.08),
            "compensation": 29_000 * rng.normal(1, 0.03),
            "technology": 11_000 * rng.normal(1, 0.05),
            "occupancy": 5_000 * rng.normal(1, 0.02),
            "one_offs": 800 * rng.normal(1, 0.5),
        }
        row = {"date": d.strftime("%Y-%m-%d")}
        row.update({k: round(float(v), 2) for k, v in rev.items()})
        row.update({k: round(float(v), 2) for k, v in costs.items()})
        # Totals sum the ROUNDED lines, so flash totals reconcile exactly.
        row["total_revenue"] = round(sum(row[k] for k in rev), 2)
        row["total_costs"] = round(sum(row[k] for k in costs), 2)
        row["net_pnl"] = round(row["total_revenue"] - row["total_costs"], 2)
        drows.append(row)
    daily = pd.DataFrame(drows)
    daily.to_csv(os.path.join(OUT, "daily_flash.csv"), index=False)

    # --- Ground truth -------------------------------------------------------
    gt = pd.DataFrame(EVENTS, columns=["month", "line", "event", "description"])
    gt.to_csv(os.path.join(OUT, "ground_truth_events.csv"), index=False)

    print(f"seed={args.seed}")
    print(f"monthly rows: {len(monthly)}, clients: {len(clients)}, "
          f"client-months: {len(client_monthly)}, daily rows: {len(daily)}")
    tot = monthly[(monthly.category == 'revenue')]
    print(f"Dec 2025 total revenue (actual): "
          f"${tot[tot.month == '2025-12']['actual'].sum():,.0f}")


if __name__ == "__main__":
    main()
