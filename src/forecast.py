"""Client-revenue forecasting: numpy OLS trend+seasonal vs naive baseline.

No sklearn is used (not available in this environment). OLS is solved with
numpy.linalg.lstsq on features [1, t, sin(2*pi*t/12), cos(2*pi*t/12)].

Baseline (naive seasonal): forecast = same month last year.
Hold-out: last 3 months (Oct-Dec 2025); train on the first 21 months.
Metrics per revenue line and for total revenue: MAPE and RMSE.
The comparison is reported honestly: if OLS does not beat the baseline
on a line, that is printed and recorded, not hidden.

Also: a rules-based anomaly flagger on daily P&L -- rolling 30-day
mean/std (prior 30 days only), flag |z| > 3.

Running this module prints the full comparison table.
"""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "synthetic")
REVENUE_LINES = ["commissions", "payment_for_order_flow", "margin_interest",
                 "platform_fees", "custody_fees"]


def design(t):
    t = np.asarray(t, dtype=float)
    return np.column_stack([np.ones_like(t), t,
                            np.sin(2 * np.pi * t / 12.0),
                            np.cos(2 * np.pi * t / 12.0)])


def mape(y, f):
    y = np.asarray(y, float); f = np.asarray(f, float)
    return float(np.mean(np.abs((y - f) / y)) * 100)


def rmse(y, f):
    return float(np.sqrt(np.mean((np.asarray(y, float) - np.asarray(f, float)) ** 2)))


def compare():
    monthly = pd.read_csv(os.path.join(DATA, "monthly_close.csv"))
    rev = monthly[monthly.category == "revenue"]
    piv = rev.pivot(index="month", columns="line", values="actual").sort_index()
    piv["total_revenue"] = piv[REVENUE_LINES].sum(axis=1)
    months = list(piv.index)
    n = len(months)
    train_idx, test_idx = np.arange(n - 3), np.arange(n - 3, n)
    rows = []
    for col in REVENUE_LINES + ["total_revenue"]:
        y = piv[col].values.astype(float)
        beta, *_ = np.linalg.lstsq(design(train_idx), y[train_idx], rcond=None)
        ols_pred = design(test_idx) @ beta
        naive_pred = y[test_idx - 12]  # same month last year
        rows.append({
            "line": col,
            "ols_mape": mape(y[test_idx], ols_pred),
            "ols_rmse": rmse(y[test_idx], ols_pred),
            "naive_mape": mape(y[test_idx], naive_pred),
            "naive_rmse": rmse(y[test_idx], naive_pred),
            "ols_beats_naive_mape": mape(y[test_idx], ols_pred) < mape(y[test_idx], naive_pred),
            "holdout_months": "2025-10 to 2025-12",
            "holdout_actual": [round(float(v), 2) for v in y[test_idx]],
            "ols_forecast": [round(float(v), 2) for v in ols_pred],
            "naive_forecast": [round(float(v), 2) for v in naive_pred],
        })
    return pd.DataFrame(rows)


def flag_anomalies():
    """Rules-based daily P&L anomaly flagger: |z| > 3 vs prior 30 days."""
    df = pd.read_csv(os.path.join(DATA, "daily_flash.csv"), parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    flags = []
    vals = df["net_pnl"].values.astype(float)
    for i in range(30, len(df)):
        mu, sd = vals[i - 30:i].mean(), vals[i - 30:i].std(ddof=0)
        z = (vals[i] - mu) / sd if sd else 0.0
        if abs(z) > 3:
            flags.append({"date": str(df.loc[i, "date"].date()),
                          "net_pnl": float(vals[i]), "z": round(float(z), 2)})
    return pd.DataFrame(flags)


def main():
    cmp_df = compare()
    print("Forecast comparison — hold-out Oct-Dec 2025 (SYNTHETIC DATA)")
    print(cmp_df[["line", "ols_mape", "naive_mape", "ols_rmse", "naive_rmse",
                  "ols_beats_naive_mape"]].to_string(index=False))
    for _, r in cmp_df.iterrows():
        verdict = "OLS beats naive seasonal on MAPE" if r["ols_beats_naive_mape"] \
            else "OLS does NOT beat naive seasonal on MAPE — baseline wins on this line"
        print(f"{r['line']}: OLS MAPE {r['ols_mape']:.2f}% vs naive "
              f"{r['naive_mape']:.2f}% — {verdict}.")
    flags = flag_anomalies()
    print(f"\nDaily P&L anomaly flags (|z| > 3, rolling 30-day): {len(flags)}")
    if len(flags):
        print(flags.to_string(index=False))
    return cmp_df, flags


if __name__ == "__main__":
    main()
