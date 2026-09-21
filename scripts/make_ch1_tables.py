#!/usr/bin/env python
"""Render the chapter 1 LaTeX tables (report/tables/ch1_*.tex) from the processed CSVs so the
report always matches the data. Included from report/sections/02_current_status.tex."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402

from src.paths import PROCESSED, ROOT  # noqa: E402

OUT = ROOT / "report" / "tables"
OUT.mkdir(exist_ok=True)


def esc(s):
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def write(name, body):
    (OUT / f"{name}.tex").write_text(body)
    print("  table", name)


def main() -> int:
    s = pd.read_csv(PROCESSED / "ch1_ciso_annual_summary.csv", index_col=0)
    rows = []
    for y, r in s.iterrows():
        rows.append(f"{y} & {r.energy_TWh:.1f} & {r.peak_demand_MW/1000:.1f} & {r.load_factor:.2f} & {r.peak_net_load_MW/1000:.1f} & "
                    f"{r.min_net_load_MW/1000:.1f} & {r.solar_TWh:.1f} & {r.wind_TWh:.1f} & {r.storage_charging_TWh:.1f} & {r.net_imports_TWh:.1f} & {100*r.import_share_of_demand:.0f} \\\\")
    write("ch1_annual_summary", "\n".join([
        r"\begin{tabular}{lrrrrrrrrrr}", r"\toprule",
        r"Year & Demand & Peak & Load & Peak net & Min net & Solar & Wind & Storage & Net & Imports \\",
        r" & (TWh) & (GW) & factor & load (GW) & load (GW) & (TWh) & (TWh) & charging (TWh) & imports (TWh) & (\% of demand) \\", r"\midrule",
        *rows, r"\bottomrule", r"\end{tabular}"]))

    t = pd.read_csv(PROCESSED / "ch1_top100_net_load_timing.csv", index_col=0)
    rows = [f"{y} & {r.top100_net_load_min_MW/1000:.1f}--{r.top100_net_load_max_MW/1000:.1f} & {int(r.distinct_days)} & {100*r.share_Jul_Sep:.0f} & {100*r.share_hours_17_21:.0f} & {int(r.median_hour)}:00 & {r.mean_solar_MW/1000:.1f} & {r.mean_imports_MW/1000:.1f} & {r.mean_gas_MW/1000:.1f} \\\\" for y, r in t.iterrows()]
    write("ch1_top100_timing", "\n".join([
        r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
        r"Year & Net load range & Distinct & Jul--Sep & 17:00--21:00 & Median & Mean solar & Mean imports & Mean gas \\",
        r" & (GW) & days & (\%) & (\%) & start & (GW) & (GW) & (GW) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"]))

    p = pd.read_csv(PROCESSED / "ch1_price_stats.csv")
    p = p[p.node.str.startswith("DLAP") & p.year.isin([2024, 2025, 2026])]
    rows = [f"{esc(r.label)} & {int(r.year)}{'' if r.full_year else '*'} & {int(r.hours)} & {r['mean']:.1f} & {r['median']:.1f} & {r.p5:.1f} & {r.p95:.1f} & {r['min']:.1f} & {int(r.hours_negative)} & {int(r.hours_le_5)} & {100*r.neg_hours_10_16_share:.0f} \\\\" for _, r in p.iterrows()]
    write("ch1_price_stats_note", r"\footnotesize * partial year: 2026 covers January 1 to September 22.")
    write("ch1_price_stats", "\n".join([
        r"\begin{tabular}{llrrrrrrrrr}", r"\toprule",
        r"Node & Year & Hours & Mean & Median & P5 & P95 & Min & Hours $<\$0$ & Hours $\le\$5$ & Negative hours \\",
        r" & & & \multicolumn{5}{c}{(\$/MWh)} & & & 10:00--16:00 (\%) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"]))

    c = pd.read_csv(PROCESSED / "ch1_carbon_intensity_annual.csv", index_col=0)
    eg = json.loads((PROCESSED / "ch1_egrid_camx_2023.json").read_text())
    rows = [f"{y} & {r.energy_weighted_g_per_kWh:.0f} & {r.p5_g_per_kWh:.0f} & {r.p95_g_per_kWh:.0f} & {r.co2_Mt:.1f} & {100*r.imports_co2_share:.0f} & {100*r.gas_co2_share:.0f} \\\\" for y, r in c.iterrows()]
    write("ch1_carbon", "\n".join([
        r"\begin{tabular}{lrrrrrr}", r"\toprule",
        r"Year & Energy-weighted & P5 & P95 & CO$_2$ & Imports share & Gas share \\",
        r" & (g/kWh) & (g/kWh) & (g/kWh) & (Mt) & (\%) & (\%) \\", r"\midrule", *rows, r"\midrule",
        f"eGRID 2023 CAMX & {eg['co2_output_rate_g_per_kWh']:.0f} & -- & -- & {eg['co2_Mt']:.1f} & -- & -- \\\\",
        r"\bottomrule", r"\end{tabular}"]))

    e = pd.read_csv(PROCESSED / "ch1_dc_load_estimates.csv")
    rows = []
    for _, r in e.iterrows():
        rng = f"{r.central_TWh:.1f}" if r.low_TWh == r.high_TWh else f"{r.low_TWh:.1f}--{r.high_TWh:.1f}"
        sh = f"{r.central_share_pct:.1f}" if r.low_TWh == r.high_TWh else f"{r.low_share_pct:.1f}--{r.high_share_pct:.1f}"
        rows.append(f"{esc(r.method)} & {rng} & {sh} \\\\")
    write("ch1_dc_estimates", "\n".join([
        r"\begin{tabular}{p{6.4cm}rr}", r"\toprule",
        f"Method & TWh per year & Share of {e.retail_sales_TWh.iloc[0]:.0f} TWh (\\%) \\\\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"]))

    b = pd.read_csv(PROCESSED / "ch1_battery_summary.csv", index_col=0)
    rows = [f"{y} & {r.discharge_TWh:.2f} & {-r.charge_TWh:.2f} & {r.peak_discharge_MW/1000:.1f} & {-r.peak_charge_MW/1000:.1f} \\\\" for y, r in b.iterrows()]
    write("ch1_battery", "\n".join([r"\begin{tabular}{lrrrr}", r"\toprule", r"Year & Discharge (TWh) & Charge (TWh) & Peak discharge (GW) & Peak charge (GW) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
