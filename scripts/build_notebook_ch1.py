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
    md("""**Data quality.** Valid demand hours per year are in `hours`; 2019 has 325 missing hours (3.7 percent) after the artifact filter, later years at most 27. Annual energy = mean of valid hours x calendar hours (missing hours imputed at the annual mean); duration curves and profiles use valid hours only. EIA-930's CISO natural gas series changed method in December 2023 (EIA warning): it matches CAISO's own fuel mix within 0.1 TWh a month through November 2023 and exceeds it by 0.7-1.8 TWh a month afterwards, so gas columns must not be compared across that date."""),
    code("""table("ch1_gas_series_comparability_monthly", index_col=0).loc["2023-08-01":"2024-04-01"].round(2)"""),
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
    code("""table("ch1_negative_price_hours_windows").round(1)"""),
    md("""**Reading.** Negative day-ahead prices are now routine in Southern California: the SCE aggregation point cleared below zero in 1,131 hours of 2024 and 877 hours of 2025, and 890 hours in the first 265 days of 2026; on the matched January 1 to September 22 window that is 1,045 / 775 / 890 hours (16 / 12 / 14 percent of hours), so 2026 sits between the two complete years. PG&E's point saw 190-294 hours. Three quarters or more of those hours fall between 10 am and 4 pm, concentrated in February-June. Daily block prices from ICE almost never go negative, which is why the hourly series is needed. This is the California-specific fact that matters for load flexibility: a data center able to shift or add consumption into those hours faces a zero or negative marginal energy price."""),
    md("""## 3. Hourly carbon intensity of CAISO demand

CAISO's Today's Outlook reports 5-minute CO2 by source including imports (metric tons per hour), with export emissions netted against imports. The indicator is CAISO's accounting total divided by CAISO demand (g CO2 per kWh, energy-weighted per year): an accounting rate for the supply serving CAISO demand, not a measured consumption footprint. Negative hours (net exports) are kept in the headline series; a floored-at-zero variant is the sensitivity. CAISO publishes a fixed 288-row clock grid per day (daylight-saving hours cannot be separated); an hour is valid with at least 6 of 12 intervals for both CO2 and demand, and all-missing hours stay missing instead of becoming zero. EIA's December 2023 gas-method warning applies to EIA-930, not to CAISO's accounting: the implied gas emission factor stays at 432-452 kg/MWh month by month across the change. eGRID's CAMX rate is a generation output rate with a different boundary."""),
    code("""cs = table("ch1_carbon_intensity_annual", index_col=0).round(1); eg = json.loads((PROCESSED / "ch1_egrid_camx_2023.json").read_text()); print(eg); cs"""),
    code("""show("fig1_07_carbon_intensity")"""),
    code("""bat = table("ch1_battery_summary", index_col=0).round(2); bat"""),
    md("""**Reading.** The accounting intensity fell from about 257 g/kWh in 2019 to 186 g/kWh in 2025 (floored variant 188), with average spring midday hours near 10 g/kWh, summer midday about 46 g/kWh, and night hours 240-315 g/kWh; coverage is 99.8 percent of calendar hours or better. eGRID's 2023 CAMX generation rate (198 g/kWh) is a single-year reference with a different boundary, lower than the 2023 accounting figure (242 g/kWh). The decline is an accounting result consistent with the solar and battery additions; an independent check against CAISO's GHG tracking reports is deferred to the supply chapter. Battery discharge grew from 0.05 TWh in 2019 to 12.3 TWh in 2025 with a 10.7 GW peak, which is what moved the net-peak hours later in the evening."""),
    md("""## 4. Existing data center electricity use in California: evidence and assumptions

The four items are not four comparable estimates of one quantity. A is the only statewide historical estimate (EPRI, 2023); B converts the CEC's ~1,000 MW existing peak with an assumed annual load factor; C is an illustrative count-based sensitivity (facility points x an assumed per-facility energy taken from the SVP cluster, no peak or utilization factor); D is a single-utility subset. Shares use EIA-861 retail sales (Parts A + C + D) of the matching year."""),
    code("""rs = table("ch1_ca_retail_sales_eia861"); rs.round(2)"""),
    code("""est = table("ch1_dc_load_estimates"); est[["method","low_TWh","central_TWh","high_TWh","low_share_pct","central_share_pct","high_share_pct"]].round(2)"""),
    code("""for _, r in est.iterrows(): print(f"- {r.method}\\n    basis: {r.basis}\\n    sources: {r.source}\\n")"""),
    code("""show("fig1_08_existing_dc_load_estimates")"""),
    code("""svp = table("ch1_svp_fact_sheets"); bu = json.loads((PROCESSED / "ch1_bottom_up_inputs.json").read_text()); print(bu); svp.round(2)  # peak, load factor, retail sales and supply from the SVP fact sheets (report Table: Silicon Valley Power fact-sheet series)"""),
    md("""**Reading.** The statewide estimate and the assumed conversion agree: EPRI's 2023 figure (9.3 TWh, 3.9 percent of 2023 retail sales; 3.70 percent on EPRI's own denominator) and the CEC's ~1,000 MW existing peak converted at an assumed 0.80-0.95 annual load factor (7.0-8.3 TWh, 2.9-3.4 percent of 2024 sales). The count-based sensitivity (321 Kollar-Grady facility points x an assumed 42 GWh per facility from the SVP cluster, scaled 0.5-1.0) gives 6.8-13.6 TWh (2.8-5.7 percent) and is an assumption set, not a measurement; the Epoch snapshot's lack of California observations is a coverage limit. Silicon Valley Power's 58 data centers at 53-60 percent of SVP's 4.48 TWh of 2023 retail sales are 2.4-2.7 TWh, about one percent of statewide sales. The defensible statement is: existing data centers used about 3 to 4 percent of California's electricity in 2023-2025, no metered statewide total exists, and one municipal utility hosts roughly a quarter to a third of it. Against this roughly 1 GW of existing peak, the CEC's December 2025 energization requests located in California total 20,677 MW (23,277 MW including VEA's 2,600 MW in Nevada), a ratio of about 21 that is the subject of chapter 2."""),
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
