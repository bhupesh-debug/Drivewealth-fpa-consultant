"""Monthly close flux engine (rules-based, no ML).

Materiality rule (documented, applied uniformly):
  A line is MATERIAL if |variance| >= $25,000 AND |variance %| >= 5%.
  Variance % vs prior month uses prior-month actual; vs budget uses budget.
  One-offs use an additional rule: actual > 3x the 24-month median one-off
  level is always flagged, because a small base makes % noisy.

Attribution rules (in priority order):
  1. one_offs spike            -> One-off
  2. commissions + volume move -> Volume (driver: trading_volume)
  3. platform_fees + fee move  -> Price / fee schedule (driver: fee_per_account)
  4. client start/stop in month -> Client onboarding / offboarding
  5. otherwise                  -> Mix / other (stated as unexplained, not invented)

CLI: python -m src.flux --month YYYY-MM   (or --latest)
Writes reports/flux_YYYY-MM.md and prints the report.
"""
import argparse
import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "synthetic")
REPORTS = os.path.join(ROOT, "reports")
ABS_THRESHOLD = 25_000
PCT_THRESHOLD = 0.05


def load():
    monthly = pd.read_csv(os.path.join(DATA, "monthly_close.csv"))
    drivers = pd.read_csv(os.path.join(DATA, "drivers.csv"))
    clients = pd.read_csv(os.path.join(DATA, "client_monthly_revenue.csv"))
    return monthly, drivers, clients


def pct_change(new, old):
    return (new - old) / old if old else 0.0


def attribute(line, month, monthly, drivers, clients, prev_month):
    """Return a plain-English driver attribution for one line/month."""
    drivers = drivers.set_index("month")
    if line == "one_offs":
        med = monthly[monthly.line == "one_offs"]["actual"].median()
        cur = monthly[(monthly.month == month) & (monthly.line == line)]["actual"].iloc[0]
        if cur > 3 * med:
            return ("One-off: one-off expense far above its 24-month median "
                    f"(${med:,.0f}); treat as non-recurring, not a run-rate change.")
        return "One-off: within normal one-off range; no single item identified."
    if line == "commissions" and month in drivers.index and prev_month in drivers.index:
        vol_chg = pct_change(drivers.loc[month, "trading_volume"],
                             drivers.loc[prev_month, "trading_volume"])
        if abs(vol_chg) >= 0.10:
            d = "rose" if vol_chg > 0 else "fell"
            return (f"Volume: trading volume {d} {vol_chg:+.1%} vs prior month, "
                    "consistent with the commissions move (volume-driven).")
    if line == "platform_fees" and month in drivers.index and prev_month in drivers.index:
        fee_chg = pct_change(drivers.loc[month, "fee_per_account"],
                             drivers.loc[prev_month, "fee_per_account"])
        if abs(fee_chg) >= 0.10:
            return (f"Price (fee schedule): fee per account moved {fee_chg:+.1%} "
                    "vs prior month, consistent with a fee-schedule change.")
    # NOTE: client onboarding/offboarding is reported at month level in the
    # client-concentration note (client revenue is not split by P&L line in
    # this dataset), NOT attributed to individual P&L lines -- attributing
    # one client's start to every moving line would be false precision.
    return "Mix / other: no single volume, price, one-off or client driver " \
           "explains the move under the documented rules; flagged for follow-up."


def client_concentration_note(month, prev_month, clients):
    cur = clients[clients.month == month].groupby("client_id")["revenue"].sum()
    prev = clients[clients.month == prev_month].groupby("client_id")["revenue"].sum()
    chg = (cur - prev).fillna(0).sort_values()
    top_up = chg.tail(1)
    top_dn = chg.head(1)
    notes = []
    if len(top_up) and top_up.iloc[0] > 0:
        notes.append(f"Largest client gain: {top_up.index[0]} "
                     f"(${top_up.iloc[0]:+,.0f}).")
    if len(top_dn) and top_dn.iloc[0] < 0:
        notes.append(f"Largest client decline: {top_dn.index[0]} "
                     f"(${top_dn.iloc[0]:+,.0f}).")
    started = [c for c in cur.index if prev.get(c, 0) == 0 and cur[c] > 0]
    stopped = [c for c in prev.index if cur.get(c, 0) == 0 and prev[c] > 0]
    if started:
        notes.append("Client onboarding in month: " + ", ".join(started) + ".")
    if stopped:
        notes.append("Client offboarding in month: " + ", ".join(stopped) + ".")
    return " ".join(notes)


def flux_report(month):
    monthly, drivers, clients = load()
    months = sorted(monthly.month.unique())
    if month not in months:
        raise ValueError(f"month {month} not in data ({months[0]}..{months[-1]})")
    idx = months.index(month)
    prev_month = months[idx - 1] if idx > 0 else None
    cur = monthly[monthly.month == month].set_index("line")
    lines = []
    for line in cur.index:
        a = float(cur.loc[line, "actual"])
        b = float(cur.loc[line, "budget"])
        row = {"line": line, "category": cur.loc[line, "category"],
               "actual": a, "budget": b, "vs_budget": a - b,
               "vs_budget_pct": pct_change(a, b)}
        if prev_month:
            p = float(monthly[(monthly.month == prev_month)
                               & (monthly.line == line)]["actual"].iloc[0])
            row["prior"] = p
            row["vs_prior"] = a - p
            row["vs_prior_pct"] = pct_change(a, p)
            row["material"] = (abs(a - p) >= ABS_THRESHOLD
                               and abs(pct_change(a, p)) >= PCT_THRESHOLD)
            if line == "one_offs":
                med = monthly[monthly.line == "one_offs"]["actual"].median()
                row["material"] = bool(row["material"] or a > 3 * med)
            row["explanation"] = attribute(line, month, monthly, drivers,
                                           clients, prev_month) if row["material"] else ""
        else:
            row["prior"] = None; row["vs_prior"] = None
            row["vs_prior_pct"] = None; row["material"] = False; row["explanation"] = ""
        lines.append(row)
    note = client_concentration_note(month, prev_month, clients) if prev_month else ""
    return {"month": month, "prev_month": prev_month, "lines": lines,
            "client_note": note}


def render_md(rep):
    out = [f"# Monthly Close Flux Report — {rep['month']} (SYNTHETIC DATA)",
           "",
           f"Prior month: {rep['prev_month']}. Materiality: |variance| >= "
           f"$25,000 AND |variance %| >= 5% vs prior month (one-offs: also "
           "flagged if >3x the 24-month median). Fictional firm: NorthPeak "
           "Securities. All figures synthetic.",
           "",
           "| Line | Actual | Budget | vs Budget | vs Prior Month | Material | Explanation |",
           "|---|---|---|---|---|---|---|"]
    for r in rep["lines"]:
        out.append(f"| {r['line']} | ${r['actual']:,.0f} | ${r['budget']:,.0f} | "
                   f"${r['vs_budget']:+,.0f} ({r['vs_budget_pct']:+.1%}) | "
                   f"${r['vs_prior']:+,.0f} ({r['vs_prior_pct']:+.1%}) | "
                   f"{'YES' if r['material'] else 'no'} | {r['explanation']} |")
    out += ["", "## Client concentration", "", rep["client_note"] or "None noted."]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default=None)
    ap.add_argument("--latest", action="store_true")
    args = ap.parse_args()
    monthly, _, _ = load()
    months = sorted(monthly.month.unique())
    month = months[-1] if (args.latest or not args.month) else args.month
    rep = flux_report(month)
    md = render_md(rep)
    os.makedirs(REPORTS, exist_ok=True)
    path = os.path.join(REPORTS, f"flux_{month}.md")
    with open(path, "w") as f:
        f.write(md)
    print(md)
    print(f"Written: {path}")


if __name__ == "__main__":
    main()
