#!/usr/bin/env python
"""Build notebooks/01_baseline_grid.ipynb from cells defined here, then execute it in place
(jupyter nbconvert --execute). The notebook reads the processed tables written by
scripts/run_chapter1.py and re-displays every figure with a short reading of it, so the
chapter's evidence chain is visible in one document."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "01_baseline_grid.ipynb"

md = lambda s: nbf.v4.new_markdown_cell(s)  # noqa: E731
code = lambda s: nbf.v4.new_code_cell(s)  # noqa: E731

cells = [
    md("""# 01 · Current status of data centers and the grid in California

Chapter 1 of *Mapping the Consumption Gap*. Answers "how much of the state's power do data centers use" and builds the grid baseline from Section 3.2 of the proposal.

All numbers come from `data/raw` through `src/ch1_baseline.py`; `scripts/run_chapter1.py` writes the tables (`data/processed/ch1_*`) and figures (`figures/fig1_*`) that this notebook displays. Every table names the manifest `source_id` it was built from.

| Step | Sources (manifest ids) |
|---|---|
| 1. Hourly demand, generation by fuel, interchange, 2019-2025 | `eia930_balance_*` (Adjusted series), cross-checked against `caiso_outlook_demand` |
| 2. Day-ahead price duration curves, negative-price hours | `caiso_dam_lmp_monthly_dlap`, `caiso_dam_lmp_monthly_hubs`, `eia_ice_wholesale_*` |
| 3. Hourly carbon intensity | `caiso_outlook_co2`, `caiso_outlook_demand`, `epa_egrid2023_rev1` |
| 4. Existing data center load, four ways | `epri_powering_intelligence_2024`, `cec_dc_methodology_memo_2026`, `kollar_grady_2025_zenodo`, `epoch_data_centers`, `svp_*`, `eia861_2024` |
| 5. Institutional context | `cec_tn268288`, `cec_tn269506`, `cec_tn261964`, `cec_tn261975`, `cec_tn268459`, `pge_*`, `cpuc_oir_rate_design_2026_04`, `ca_sb57_*`, `ca_sb886_*`, `ca_ab222_*`, `cpuc_news_streamlined_connections` |
"""),
    code("""import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path().resolve().parent))
import pandas as pd, numpy as np
from IPython.display import Image, display
from src.paths import PROCESSED, FIGURES
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 40)
def show(name): display(Image(filename=str(FIGURES / f"{name}.png")))
def table(name, **kw): return pd.read_csv(PROCESSED / f"{name}.csv", **kw)
rec = json.loads((PROCESSED / "ch1_run_record.json").read_text()); rec"""),
    md("""## 1. Grid baseline: CAISO hourly demand, net load, imports (EIA-930, 2019-2025)

EIA-930 "Adjusted" series for the CISO balancing authority. Net load = demand − utility-scale solar − wind. Imports = −net interchange. EIA-930's CISO demand includes storage charging and pumping load, whereas CAISO's Today's Outlook 'Current demand' excludes charging; in 2025 the gap between the two tracks battery charging almost one-for-one. Both are kept: `demand` (EIA definition) and `demand_ex_storage` (EIA demand minus CAISO-reported charging). Hours where EIA demand is implausibly low (below 85 percent of CAISO demand plus charging, or under 5 GW) are reporting artifacts and are nulled (listed in `ch1_eia930_flagged_hours.csv`). EIA-930 has no CISO interchange in any variant from 2024-07-02 to 2024-11-03 and no hydro for parts of 2019-2020; those hours are filled from CAISO's five-minute imports and hydro series via a per-year linear calibration (`ch1_eia930_fill_log.csv`)."""),
    code("""summ = table("ch1_ciso_annual_summary", index_col=0)
cols = ["hours","energy_TWh","avg_demand_MW","peak_demand_MW","peak_demand_time","load_factor","peak_net_load_MW","peak_net_load_time","min_net_load_MW","min_net_load_ex_storage_MW","storage_charging_TWh","solar_TWh","wind_TWh","gas_TWh","net_imports_TWh","import_share_of_demand","solar_wind_share_of_demand"]
summ[cols].round(3)"""),
    code("""table("ch1_eia930_flagged_hours", index_col=0)"""),
    code("""table("ch1_eia930_fill_log").round(3)"""),
    md("""**Reading.** CAISO annual demand has been flat at roughly 214-224 TWh since 2019 while utility-scale solar and wind rose from a fifth to nearly a third of demand and net imports fell from a quarter of demand to 13-16 percent (2023-2025). The hourly peak record remains September 6, 2022 (51.1 GW)."""),
    code("""show("fig1_01_load_duration_curves")"""),
    code("""show("fig1_02_net_load_duration_curves")"""),
    md("""**Reading.** The load duration curves barely move between years; the net-load duration curves fall steadily at the low end, and by 2025 the lowest-net-load hours are near or below zero, meaning utility solar and wind alone exceed CAISO demand in those hours. This is the midday surplus that later chapters treat as a resource for flexible load."""),
    code("""show("fig1_03_seasonal_daily_profiles")"""),
    md("""**Reading.** Demand profiles (top) are similar across years; net-load profiles (bottom) show the deepening midday trough and a steeper, later evening ramp. In spring 2025 the average midday net load is about 6 GW against roughly 21 GW at 8 pm."""),
    code("""timing = table("ch1_top100_net_load_timing", index_col=0)
timing[["top100_net_load_min_MW","top100_net_load_max_MW","distinct_days","share_Jul_Sep","share_hours_17_21","median_hour","earliest_hour","latest_hour","mean_solar_MW","mean_imports_MW","mean_gas_MW"]].round(2)"""),
    code("""show("fig1_04_top100_net_load_timing")"""),
    md("""**Reading.** The 100 highest net-load hours of each year fall almost entirely in July-September and between 5 pm and 9 pm, and their median start time has moved from 6 pm (2019-2020) to 8 pm (2023-2025). Solar contributes under 1.3 GW on average in these hours. A flat data center load therefore adds one-for-one to the hours that set capacity needs; storage and gas, not solar, serve them."""),
    md("""## 2. Day-ahead prices at the default load aggregation points (OASIS PRC_LMP, DAM)

OASIS serves hourly day-ahead prices from July 2023 onward (about 39 months of retention). 2024 and 2025 are complete years; 2023 covers July-December and 2026 covers January to September 22. EIA's daily ICE hub prices (NP15, SP15) extend to 2015 but are daily block averages."""),
    code("""ps = table("ch1_price_stats")
ps[ps.node.str.startswith("DLAP")][["label","year","hours","full_year","mean","median","p5","p95","min","max","hours_negative","hours_le_5","hours_ge_200","share_negative","neg_hours_10_16_share"]].round(3)"""),
    code("""show("fig1_05_price_duration_and_diurnal")"""),
    code("""show("fig1_06_negative_price_hours")"""),
    code("""nb = table("ch1_negative_price_hours_by_month")
nb[nb.year.isin([2024, 2025, 2026])].pivot(index="month", columns="year", values=["DLAP_PGAE-APND","DLAP_SCE-APND","DLAP_SDGE-APND"])"""),
    code("""ice = table("ch1_ice_daily_hub_prices_negative_days"); ice[ice.hub.str.contains("DA")]"""),
    md("""**Reading.** Negative day-ahead prices are now routine in Southern California: the SCE aggregation point cleared below zero in 1,131 hours of 2024 and 877 hours of 2025, and 890 hours in the first 265 days of 2026; PG&E's point saw 190-294 hours. Three quarters or more of those hours fall between 10 am and 4 pm, concentrated in February-June. Daily block prices from ICE almost never go negative, which is why the hourly series is needed. This is the California-specific fact that matters for load flexibility: a data center able to shift or add consumption into those hours faces a zero or negative marginal energy price."""),
    md("""## 3. Hourly carbon intensity of CAISO demand

CAISO's Today's Outlook reports 5-minute CO2 by source including imports (metric tons per hour). Intensity here is total CO2 divided by CAISO demand, in g CO2 per kWh, energy-weighted per year; net CO2 is negative in export-heavy hours (CAISO nets export emissions against imports) and is floored at zero rather than dropped. eGRID's CAMX annual output emission rate is the reference annual factor (generation-based, 2023)."""),
    code("""cs = table("ch1_carbon_intensity_annual", index_col=0).round(1); eg = json.loads((PROCESSED / "ch1_egrid_camx_2023.json").read_text()); print(eg); cs"""),
    code("""show("fig1_07_carbon_intensity")"""),
    code("""bat = table("ch1_battery_summary", index_col=0).round(2); bat"""),
    md("""**Reading.** Load-based intensity fell from about 257 g/kWh in 2019 to about 188 g/kWh in 2025, with average spring midday hours under 30 g/kWh, summer midday about 50 g/kWh, and night hours 240-300 g/kWh. eGRID's 2023 CAMX output rate (198 g/kWh) is lower than the CAISO load-based 2023 figure (242 g/kWh) because it is generation-based, excludes the default import factor and covers the whole CAMX subregion; the trend is the same. Battery discharge grew from 0.05 TWh in 2019 to 12.3 TWh in 2025 with a 10.7 GW peak, which is what moved the net-peak hours later in the evening."""),
    md("""## 4. Existing data center load in California, four ways

The four estimates are independent in method and source. They are shown against EIA-861 California retail sales for 2024 (Parts A + C + D, to avoid counting delivery-only sales twice). The spread is the finding; no single number is chosen."""),
    code("""rs = table("ch1_ca_retail_sales_eia861"); rs.round(2)"""),
    code("""est = table("ch1_dc_load_estimates"); est[["method","low_TWh","central_TWh","high_TWh","low_share_pct","central_share_pct","high_share_pct"]].round(2)"""),
    code("""for _, r in est.iterrows(): print(f"- {r.method}\\n    basis: {r.basis}\\n    sources: {r.source}\\n")"""),
    code("""show("fig1_08_existing_dc_load_estimates")"""),
    code("""svp = table("ch1_svp_fact_sheets"); bu = json.loads((PROCESSED / "ch1_bottom_up_inputs.json").read_text()); print(bu); svp.round(2)"""),
    md("""**Reading.** The two institutional estimates agree: EPRI's 2023 figure (9.3 TWh, 3.7 percent of state consumption) and the CEC's December 2025 baseline of about 1,000 MW of existing data center peak demand (7.0-8.3 TWh at plausible load factors, 2.9-3.4 percent of 2024 retail sales). The count-based bottom-up from 321 Kollar-Grady facility points is wide (7.0-20.7 TWh: count x SVP-anchored 7.1 MW average peak scaled 0.7-1.3 x utilization 0.50-0.80) because no public source gives per-facility power in California; Epoch's frontier hub lists no California site at all (checked programmatically: 0 of 87 addresses). Silicon Valley Power's cluster alone, 58 data centers drawing 53-60 percent of a 4.6 TWh utility, is 2.4-2.8 TWh, about a third of the CEC statewide baseline and one percent of state retail sales. The defensible statement is: existing data centers use about 3 to 4 percent of California's electricity, possibly more, and one municipal utility in Santa Clara hosts roughly a third of it. Against this roughly 1 GW of existing peak, the CEC's December 2025 energization tiers total 23,277 MW, a 23-fold ratio that is the California analogue of Finland's 27x and the subject of chapter 2."""),
    md("""## 5. Institutional context (documented in `report/sections/02_current_status.tex`)

- **January 2026 single forecast set agreement.** The CEC adopted the CED 2025-2045 forecast set on January 21, 2026 with three data center scenarios, but the joint CEC-CPUC-CAISO agreement (TN 268288, updated April 15, 2026 as TN 269506) directs that CPUC IRP and CAISO bulk-system studies for the 2026-2027 and 2027-2028 transmission planning cycles continue to use the 2024 IEPR planning forecast, and that 2027 resource adequacy requirements use the 2025 IEPR forecast without known loads. Only local transmission studies use the 2025 IEPR local reliability forecast with known loads. Stated rationale: "manages volatility and promotes stability" and gives staff "additional time to collect and review historical data, observe the impacts of known loads, data centers" (TN 269506, pp. 7-8).
- **PG&E pipeline statements.** About 1.5 GW in final engineering or construction (Feb 2025 IEPR workshop, TN 261964); 10 GW pipeline over ten years with 17 projects of about 1.5 GW in final engineering for 2026-2030 (press release, July 31, 2025); "over 12 gigawatts" (Q2 2026 Form 8-K). PG&E has filed a confidentiality request for its project-level data center data every month since August 2025.
- **SCE statements.** Existing data center demand 80 MW with 200 MW near-term and 400 MW mid-term growth (Feb 2025 IEPR workshop, TN 261975); public project database of January 29, 2026 (TN 268459): 115 entries, 8,298 MW requested peak, of which 76 MW in signed agreements, 3,314 MW in applications, 1,773 MW in inquiries and 3,137 MW already canceled; the CEC's summer 2025 tally for SCE was 5,828 MW.
- **CPUC large-load proceedings (verified).** Rulemaking R.26-04-009 on Advanced Electric Rate Design (issued April 10, 2026) will "consider rate design issues for data centers and other large load customers" in coordination with the SB 57 assessment due January 1, 2027. SB 57 (Padilla) was chaptered October 11, 2025 (Stats. 2025, ch. 647). SB 886 (Padilla), the California Technology Innovation and Ratepayer Protection Act, was chaptered September 21, 2026 and requires the CPUC to establish tariffs or update electric rules for participating large customers by January 1, 2028 that prevent stranded costs or cost shifts to other customers. AB 222 was held in Senate Appropriations on August 29, 2025. The CPUC approved interim PG&E Electric Rule 30 for transmission-level service on July 24, 2025.
"""),
]

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "capstone (.venv)", "language": "python", "name": "capstone"}, "language_info": {"name": "python"}}
nbf.write(nb, NB)
print("wrote", NB)
if "--execute" in sys.argv:
    subprocess.run([str(ROOT / ".venv/bin/jupyter"), "nbconvert", "--to", "notebook", "--execute", "--inplace",
                    "--ExecutePreprocessor.timeout=1200", str(NB)], check=True, cwd=ROOT)
    print("executed")
