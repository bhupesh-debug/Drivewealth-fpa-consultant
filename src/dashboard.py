"""Standalone HTML dashboard (no server, no Streamlit).

Builds reports/dashboard.html with matplotlib charts embedded as base64
PNGs plus KPI tiles computed from the synthetic data.
CLI: python -m src.dashboard
"""
import base64
import io
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "synthetic")
REPORTS = os.path.join(ROOT, "reports")


def _b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _line_chart(x, series, title, ylabel):
    fig, ax = plt.subplots(figsize=(7, 3.2))
    for label, y in series:
        ax.plot(x, y, marker="o", ms=3, label=label)
    ax.set_title(title); ax.set_ylabel(ylabel)
    ax.legend(fontsize=8); ax.tick_params(axis="x", labelrotation=45, labelsize=7)
    ax.grid(alpha=0.3)
    return _b64(fig)


def _bar_chart(labels, values, title, ylabel):
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.bar(labels, values)
    ax.set_title(title); ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", labelrotation=30, labelsize=7)
    ax.grid(axis="y", alpha=0.3)
    return _b64(fig)


def build():
    monthly = pd.read_csv(os.path.join(DATA, "monthly_close.csv"))
    clients = pd.read_csv(os.path.join(DATA, "client_monthly_revenue.csv"))
    daily = pd.read_csv(os.path.join(DATA, "daily_flash.csv"), parse_dates=["date"])
    rev = monthly[monthly.category == "revenue"]
    piv = rev.pivot(index="month", columns="line", values="actual").sort_index()
    tot = piv.sum(axis=1)
    bud = monthly[monthly.category == "revenue"].groupby("month")["budget"].sum()
    latest = piv.index[-1]
    latest_rev = float(tot.iloc[-1]); latest_bud = float(bud.iloc[-1])
    latest_cost = float(monthly[(monthly.month == latest)
                                & (monthly.category == "cost")]["actual"].sum())
    net = latest_rev - latest_cost
    seg = clients[clients.month == latest].groupby("segment")["revenue"].sum()
    top = clients[clients.month == latest].groupby("client_id")["revenue"].sum() \
        .sort_values(ascending=False).head(8)
    # Flux waterfall summary: largest vs-prior-month moves in latest month.
    prev = piv.index[-2]
    moves = (piv.loc[latest] - piv.loc[prev]).sort_values()
    charts = {
        "rev_budget": _line_chart(list(piv.index),
                                  [("Actual revenue", tot.values),
                                   ("Budget revenue", bud.values)],
                                  "Monthly revenue vs budget (synthetic)",
                                  "USD"),
        "segment": _bar_chart(list(seg.index), seg.values,
                              f"Client-attributed revenue by segment — {latest}",
                              "USD"),
        "top_clients": _bar_chart(list(top.index), top.values,
                                   f"Top 8 clients — {latest}", "USD"),
        "daily": _line_chart([str(d.date()) for d in daily["date"]],
                             [("Net P&L", daily["net_pnl"].values)],
                             "Daily net P&L flash trend — last 90 days (synthetic)",
                             "USD"),
        "waterfall": _bar_chart(list(moves.index), moves.values,
                                 f"Revenue flux vs prior month — {latest}",
                                 "USD change"),
    }
    kpis = (f"<div class='kpi'>Latest month ({latest}) revenue: "
            f"${latest_rev:,.0f}</div>"
            f"<div class='kpi'>Revenue vs budget: "
            f"${latest_rev - latest_bud:+,.0f} "
            f"({(latest_rev - latest_bud) / latest_bud:+.1%})</div>"
            f"<div class='kpi'>Latest month net P&L: ${net:,.0f}</div>"
            f"<div class='kpi'>Latest month costs: ${latest_cost:,.0f}</div>"
            f"<div class='kpi'>Daily flash days: {len(daily)}</div>")
    sections = "".join(
        f"<h2>{t}</h2><img src='data:image/png;base64,{b}'>"
        for t, b in [("Revenue vs budget", charts["rev_budget"]),
                     ("Revenue by segment", charts["segment"]),
                     ("Top clients", charts["top_clients"]),
                     ("Daily P&L flash trend", charts["daily"]),
                     ("Flux waterfall summary (vs prior month)",
                      charts["waterfall"])])
    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>NorthPeak Securities (fictional) — FP&A Dashboard — SYNTHETIC DATA</title>
<style>body{{font-family:Arial,sans-serif;margin:24px}} .kpi{{display:inline-block;
background:#eef2f7;border-radius:8px;padding:12px 18px;margin:6px;font-weight:bold}}
img{{max-width:100%}}</style></head><body>
<h1>NorthPeak Securities (fictional) — FP&amp;A Dashboard</h1>
<p><b>ALL DATA SYNTHETIC.</b> Fictional brokerage built as a portfolio
project for an FP&amp;A Consultant role. No real company data is used.</p>
{kpis}{sections}</body></html>"""
    os.makedirs(REPORTS, exist_ok=True)
    path = os.path.join(REPORTS, "dashboard.html")
    with open(path, "w") as f:
        f.write(html)
    print(f"Written: {path} ({len(html):,} chars)")
    return path


if __name__ == "__main__":
    build()
