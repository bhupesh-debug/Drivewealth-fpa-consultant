"""Daily P&L flash generator (rules-based).

For a given date: day vs prior day and vs month-to-date (MTD) average,
top movers by absolute day-over-day change, and flags:
  * |day-over-day %| >= 20% on any line, or
  * net P&L more than 2 rolling standard deviations from its 30-day mean.

CLI: python -m src.flash --date YYYY-MM-DD
Writes reports/flash_YYYY-MM-DD.md and reports/flash_YYYY-MM-DD.csv.
"""
import argparse
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "synthetic")
REPORTS = os.path.join(ROOT, "reports")
LINES = ["commissions", "payment_for_order_flow", "margin_interest",
         "platform_fees", "custody_fees", "clearing", "compensation",
         "technology", "occupancy", "one_offs"]


def load():
    df = pd.read_csv(os.path.join(DATA, "daily_flash.csv"), parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


def flash_report(date_str):
    df = load()
    idx = df.index[df["date"] == pd.Timestamp(date_str)]
    if len(idx) == 0:
        raise ValueError(f"date {date_str} not in daily data "
                         f"({df['date'].min().date()}..{df['date'].max().date()})")
    i = int(idx[0])
    row = df.iloc[i]
    prev = df.iloc[i - 1] if i > 0 else None
    mtd = df[(df["date"].dt.to_period("M") == row["date"].to_period("M"))
             & (df["date"] <= row["date"])]
    movers = []
    for line in LINES:
        d = float(row[line] - prev[line]) if prev is not None else 0.0
        p = d / float(prev[line]) if prev is not None and prev[line] else 0.0
        movers.append({"line": line, "today": float(row[line]),
                       "prior_day": float(prev[line]) if prev is not None else None,
                       "change": d, "change_pct": p,
                       "mtd_avg": float(mtd[line].mean())})
    movers.sort(key=lambda r: abs(r["change"]), reverse=True)
    flags = []
    for m in movers:
        if abs(m["change_pct"]) >= 0.20:
            flags.append(f"{m['line']}: day-over-day {m['change_pct']:+.1%} "
                         "(>=20% flag threshold).")
    if i >= 30:
        window = df.iloc[i - 30:i]["net_pnl"]
        z = (float(row["net_pnl"]) - window.mean()) / window.std(ddof=0) \
            if window.std(ddof=0) else 0.0
        if abs(z) > 2:
            flags.append(f"net_pnl: z-score {z:+.2f} vs prior 30-day mean "
                         "(|z| > 2 flag threshold).")
    else:
        z = None
    return {"date": date_str, "row": row,
            "prior_date": str(prev["date"].date()) if prev is not None else None,
            "mtd_days": len(mtd), "mtd_total_revenue": float(mtd["total_revenue"].sum()),
            "mtd_total_costs": float(mtd["total_costs"].sum()),
            "mtd_net_pnl": float(mtd["net_pnl"].sum()),
            "movers": movers, "flags": flags,
            "z": z if i >= 30 else None}


def render_md(rep):
    r = rep["row"]
    out = [f"# Daily P&L Flash — {rep['date']} (SYNTHETIC DATA)", "",
           f"Prior day: {rep['prior_date']}. MTD ({rep['mtd_days']} days): "
           f"revenue ${rep['mtd_total_revenue']:,.0f}, costs "
           f"${rep['mtd_total_costs']:,.0f}, net P&L ${rep['mtd_net_pnl']:,.0f}.",
           "", f"**Today:** revenue ${r['total_revenue']:,.0f}, costs "
           f"${r['total_costs']:,.0f}, net P&L ${r['net_pnl']:,.0f}.", "",
           "| Line | Today | Prior day | Change | Change % | MTD daily avg |",
           "|---|---|---|---|---|---|"]
    for m in rep["movers"]:
        out.append(f"| {m['line']} | ${m['today']:,.0f} | ${m['prior_day']:,.0f} | "
                   f"${m['change']:+,.0f} | {m['change_pct']:+.1%} | "
                   f"${m['mtd_avg']:,.0f} |")
    out += ["", "## Flags", ""]
    out += [f"- {f}" for f in rep["flags"]] if rep["flags"] else ["- None."]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    rep = flash_report(args.date)
    md = render_md(rep)
    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, f"flash_{args.date}.md"), "w") as f:
        f.write(md)
    pd.DataFrame(rep["movers"]).to_csv(
        os.path.join(REPORTS, f"flash_{args.date}.csv"), index=False)
    print(md)


if __name__ == "__main__":
    main()
