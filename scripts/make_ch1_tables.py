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
    rows = [f"{y} & {r.energy_weighted_g_per_kWh:.1f} & {r.energy_weighted_floored_g_per_kWh:.1f} & {int(r.hours_net_co2_negative)} & {r.p5_g_per_kWh:.0f} & {r.p95_g_per_kWh:.0f} & {r.co2_Mt:.1f} & {100*r.imports_co2_share:.0f} & {100*r.gas_co2_share:.0f} & {r.coverage_pct:.1f} \\\\" for y, r in c.iterrows()]
    write("ch1_carbon", "\n".join([
        r"\begin{tabular}{lrrrrrrrrr}", r"\toprule",
        r"Year & Accounting & Floored & Negative & P5 & P95 & CO$_2$ & Imports & Gas & Valid \\",
        r" & (g/kWh) & (g/kWh) & hours & (g/kWh) & (g/kWh) & (Mt) & share (\%) & share (\%) & hours (\%) \\", r"\midrule", *rows, r"\midrule",
        f"eGRID 2023 CAMX generation output rate & {eg['co2_output_rate_g_per_kWh']:.1f} & -- & -- & -- & -- & {eg['co2_Mt']:.1f} & -- & -- & -- \\\\",
        r"\bottomrule", r"\end{tabular}"]))

    e = pd.read_csv(PROCESSED / "ch1_dc_load_estimates.csv")
    rows = []
    for _, r in e.iterrows():
        rng = f"{r.central_TWh:.1f}" if r.low_TWh == r.high_TWh else f"{r.low_TWh:.1f}--{r.high_TWh:.1f}"
        sh = f"{r.central_share_pct:.1f}" if r.low_TWh == r.high_TWh else f"{r.low_share_pct:.1f}--{r.high_share_pct:.1f}"
        rows.append(f"{esc(r.group)} & {esc(r.method)} & {int(r.year)} & {rng} & {sh} ({int(r.denominator_year)}) \\\\")
    write("ch1_dc_estimates", "\n".join([
        r"\begin{tabular}{p{2.6cm}p{6.2cm}rrr}", r"\toprule",
        r"Group & Method & Data year & TWh per year & Share of retail sales, \% (year) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"]))

    b = pd.read_csv(PROCESSED / "ch1_battery_summary.csv", index_col=0)
    rows = [f"{y} & {r.discharge_TWh:.2f} & {-r.charge_TWh:.2f} & {r.peak_discharge_MW/1000:.1f} & {-r.peak_charge_MW/1000:.1f} \\\\" for y, r in b.iterrows()]
    write("ch1_battery", "\n".join([r"\begin{tabular}{lrrrr}", r"\toprule", r"Year & Discharge (TWh) & Charge (TWh) & Peak discharge (GW) & Peak charge (GW) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"]))
    svp = pd.read_csv(PROCESSED / "ch1_svp_fact_sheets.csv")
    rows = [f"{int(r.fact_sheet_year)} & {r.peak_MW:.1f} & {100*r.load_factor:.1f} & {('--' if pd.isna(r.retail_sales_GWh) else f'{r.retail_sales_GWh/1000:.2f}')} & {r.supply_GWh/1000:.2f} & {r.energy_GWh_est/1000:.2f} \\\\" for r in svp.itertuples()]
    write("ch1_svp", "\n".join([r"\begin{tabular}{lrrrrr}", r"\toprule", r"Fact sheet year & Peak demand (MW) & System load factor (\%) & Retail sales (TWh) & Purchased and generated supply (TWh) & Peak $\times$ load factor $\times$ 8760 (TWh) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"]))
    write("ch1_svp_note", r"\footnotesize Silicon Valley Power utility fact sheets; retail sales are reported from 2020. Data center shares applied to 2023 retail sales: 53 percent (SVP data center page), 55 percent (SVP Assembly deck, January 2026), about 60 percent (Santa Clara officials, 2025); SVP reports 64 to 67 percent utilization of requested capacity for its data center customers.")

    g = pd.read_csv(PROCESSED / "ch1_gas_series_comparability_monthly.csv", index_col=0).loc["2023-09-01":"2024-04-01"]
    rows = [f"{pd.Timestamp(i):%b %Y} & {r.eia930_gas_TWh:.2f} & {r.caiso_fuelmix_gas_TWh:.2f} & {r.eia_minus_caiso_gas_TWh:+.2f} & {100*r.caiso_fuelmix_gas_TWh/r.caiso_demand_TWh:.1f} & {r.implied_gas_kg_per_MWh:.0f} \\\\" for i, r in g.iterrows()]
    ann = pd.read_csv(PROCESSED / "ch1_gas_series_comparability_monthly.csv", index_col=0); ann.index = pd.to_datetime(ann.index); ay = ann.groupby(ann.index.year)[["eia930_gas_TWh", "caiso_fuelmix_gas_TWh", "eia_minus_caiso_gas_TWh"]].sum()
    rows.append(r"\midrule"); rows += [f"{int(y)} total & {r.eia930_gas_TWh:.1f} & {r.caiso_fuelmix_gas_TWh:.1f} & {r.eia_minus_caiso_gas_TWh:+.1f} & -- & -- \\\\" for y, r in ay.loc[2023:2025].iterrows()]
    write("ch1_gas_comparability", "\n".join([r"\begin{tabular}{lrrrrr}", r"\toprule", r"Month & EIA-930 CISO gas (TWh) & CAISO fuel-mix gas (TWh) & EIA minus CAISO (TWh) & CAISO gas share of demand (\%) & Implied gas CO$_2$ factor, CAISO accounting (kg/MWh) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"]))

    # workshop format: minimum, maximum and mean of the 2025-2026 hourly series; monthly gross imports and exports
    ws = pd.read_csv(PROCESSED / "ch1_workshop_stats.csv")
    rows = []
    for r in ws.itertuples():
        fmt = (lambda v: f"{v:,.0f}") if r.unit == "MW" else (lambda v: f"{v:,.1f}")
        rows.append(f"{esc(r.series)} & {esc(r.period)} & {esc(r.unit)} & {int(r.hours):,} & {fmt(r.min)} & {esc(str(r.min_time)[:16])} & {fmt(r.max)} & {esc(str(r.max_time)[:16])} & {fmt(r.mean)} \\\\")
    write("ch1_workshop_stats", "\n".join([
        r"\begin{tabular}{llllrlrlr}", r"\toprule",
        r"Series & Period & Unit & Hours & Minimum & at & Maximum & at & Mean \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"]))
    ie = pd.read_csv(PROCESSED / "ch1_imports_exports_monthly.csv")
    rows = [f"{int(r.year)}-{int(r.month):02d} & {r.imports_GWh:,.0f} & {r.exports_GWh:,.0f} & {r.net_imports_GWh:,.0f} & {int(r.hours)} / {int(r.calendar_hours)}{'' if r.complete else ' (incomplete)'} \\\\" for r in ie.itertuples()]
    tot = [f"\\midrule 2025 total & {ie[ie.year==2025].imports_GWh.sum():,.0f} & {ie[ie.year==2025].exports_GWh.sum():,.0f} & {ie[ie.year==2025].net_imports_GWh.sum():,.0f} & {int(ie[ie.year==2025].hours.sum())} \\\\",
           f"2026 to date & {ie[ie.year==2026].imports_GWh.sum():,.0f} & {ie[ie.year==2026].exports_GWh.sum():,.0f} & {ie[ie.year==2026].net_imports_GWh.sum():,.0f} & {int(ie[ie.year==2026].hours.sum())} \\\\"]
    write("ch1_imports_exports_monthly", "\n".join([
        r"\begin{tabular}{lrrrl}", r"\toprule", r"Month & Gross imports & Gross exports & Net imports & Hours present \\", r" & (GWh) & (GWh) & (GWh) & \\", r"\midrule", *rows, *tot, r"\bottomrule", r"\end{tabular}"]))
    rec = json.loads((PROCESSED / "ch1_run_record.json").read_text())["workshop_format"]; ck = rec["interchange_check"]
    write("ch1_imports_exports_note", r"\parbox{\textwidth}{\footnotesize Check: the hourly sum of the neighbour flows against the balance file's net interchange over " + f"{ck['hours_compared']:,}" + r" hours of 2025--2026: mean absolute difference " + f"{ck['mean_abs_diff_MW']:.0f}" + r"~MW, correlation " + f"{ck['correlation']:.4f}" + ".}")
    inst = pd.read_csv(PROCESSED / "ch1_installed_wind_solar_2026_07.csv")
    rows = [f"{esc(r.technology.capitalize())} & {r.ba_nameplate_mw:,.0f} & {int(r.ba_units):,} & {r.california_nameplate_mw:,.0f} & {int(r.california_units):,} \\\\" for r in inst.itertuples()]
    write("ch1_installed_wind_solar", "\n".join([
        r"\begin{tabular}{lrrrr}", r"\toprule", r"Technology & \multicolumn{2}{c}{CAISO balancing authority} & \multicolumn{2}{c}{State of California} \\", r" & nameplate (MW) & units & nameplate (MW) & units \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
