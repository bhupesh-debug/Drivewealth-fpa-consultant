"""Build notebooks/01_eda.ipynb, 02_flux_analysis.ipynb, 03_forecast.ipynb
by EXECUTING each cell in-process (shared namespace per notebook) and
storing the captured stdout as stream outputs. No nbformat/jupyter needed.
Run: python build_notebooks.py
"""
import io, json, os, sys, contextlib

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
NB = os.path.join(ROOT, "notebooks")
os.makedirs(NB, exist_ok=True)

NOTEBOOKS = {
 "01_eda.ipynb": [
  "# 01 — Exploratory analysis (SYNTHETIC DATA, fictional NorthPeak Securities)\nimport pandas as pd\nmonthly = pd.read_csv('data/synthetic/monthly_close.csv')\nprint(monthly.shape)\nprint(monthly.head(10).to_string(index=False))",
  "rev = monthly[monthly.category=='revenue'].groupby('month')['actual'].sum()\ncost = monthly[monthly.category=='cost'].groupby('month')['actual'].sum()\nprint('Latest month revenue:', round(float(rev.iloc[-1]), 2))\nprint('Latest month costs:', round(float(cost.iloc[-1]), 2))\nprint('Latest month net P&L:', round(float(rev.iloc[-1]-cost.iloc[-1]), 2))\nprint(rev.describe().to_string())",
  "clients = pd.read_csv('data/synthetic/client_monthly_revenue.csv')\nprint(clients.groupby('segment')['revenue'].sum().to_string())\ndaily = pd.read_csv('data/synthetic/daily_flash.csv')\nprint('Daily rows:', len(daily), '| mean daily net P&L:', round(float(daily['net_pnl'].mean()), 2))",
 ],
 "02_flux_analysis.ipynb": [
  "# 02 — Flux analysis vs injected ground truth (SYNTHETIC DATA)\nfrom src.flux import flux_report\nfor m in ['2024-06', '2025-03', '2025-07', '2025-09']:\n    rep = flux_report(m)\n    print('===', m, 'prev', rep['prev_month'], '===')\n    for r in rep['lines']:\n        if r['material']:\n            print(r['line'], f\"vs prior {r['vs_prior']:+,.0f} ({r['vs_prior_pct']:+.1%})\", '-', r['explanation'])\n    print('Client note:', rep['client_note'])",
  "gt = __import__('pandas').read_csv('data/synthetic/ground_truth_events.csv')\nprint(gt.to_string(index=False))",
 ],
 "03_forecast.ipynb": [
  "# 03 — Forecast comparison: OLS trend+seasonal vs naive seasonal (SYNTHETIC DATA)\nfrom src.forecast import compare, flag_anomalies\ncmp_df = compare()\nprint(cmp_df[['line','ols_mape','naive_mape','ols_rmse','naive_rmse','ols_beats_naive_mape']].to_string(index=False))",
  "flags = flag_anomalies()\nprint('Anomaly flags (|z| > 3, rolling 30-day):', len(flags))\nprint(flags.to_string(index=False) if len(flags) else 'No daily P&L anomalies flagged in the 90-day window.')",
 ],
}

for name, cells in NOTEBOOKS.items():
    ns = {}
    nb_cells = []
    for i, src in enumerate(cells, 1):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(compile(src, f"<{name} cell {i}>", "exec"), ns)
        out = buf.getvalue()
        assert out.strip(), f"empty output in {name} cell {i}"
        nb_cells.append({
            "cell_type": "code", "execution_count": i,
            "metadata": {}, "outputs": [{"output_type": "stream", "name": "stdout", "text": out}],
            "source": src.splitlines(keepends=True) if False else [l + "\n" for l in src.splitlines()],
        })
    nb = {"cells": nb_cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.12"}},
          "nbformat": 4, "nbformat_minor": 5}
    path = os.path.join(NB, name)
    with open(path, "w") as f:
        json.dump(nb, f, indent=1)
    print(f"Wrote {path} ({len(nb_cells)} executed cells)")
