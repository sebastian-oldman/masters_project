#!/usr/bin/env python
"""Build and execute notebooks/03_supply_growth.ipynb from the chapter 3 outputs."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "03_supply_growth.ipynb"
md = lambda s: nbf.v4.new_markdown_cell(s)  # noqa: E731
code = lambda s: nbf.v4.new_code_cell(s)  # noqa: E731

cells = [
    md("""# 03 · Energy production growth in California (supply side of RQ2)

Chapter 3 of *Mapping the Consumption Gap*. Generation and imports since 2010, capacity, batteries and curtailment, the retirement schedule, a supply-side realization model estimated on EIA-860M vintages, and probability-weighted planned supply for 2030 in three cases.

Outputs are produced by `scripts/run_chapter3.py` from `src/ch3_supply.py` (about six minutes: sixteen EIA-923 and sixteen EIA-860 annual files plus eighteen EIA-860M monthly files are parsed from the raw zips and workbooks); this notebook displays them.

| Step | Sources (manifest ids) |
|---|---|
| 1. Generation, imports, capacity, storage, curtailment | `eia923_2010..2025`, `eia860_2010..2025`, `cec_elec_energy_generation_page`, `cec_2015..2024_total_system_electric_generation`, `cec_gen_capacity_energy_page`, `caiso_curtailments_monthly_csv` |
| 2. Retirements | `eia860m_2026_07`, `swrcb_otc_policy_2023` |
| 3. Realization model | `eia860m_2016_01 .. 2022_01` (vintages), `eia860m_2016_12 .. 2025_12` (outcomes and exit timing) |
| 4. 2030 cases | `eia860m_2026_07` (current planned list), `eia860m_2025_12` (existing), `cpuc_e3_astrape_incremental_elcc_2023` (ELCC), chapter 1 tables |
"""),
    code("""import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path().resolve().parent))
import pandas as pd, numpy as np
from IPython.display import Image, display
from src.paths import PROCESSED, FIGURES
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", 80)
def show(name): display(Image(filename=str(FIGURES / f"{name}.png")))
def table(name, **kw): return pd.read_csv(PROCESSED / f"{name}.csv", **kw).convert_dtypes()  # integer-valued columns display as integers"""),
    md("""## 1. Generation by resource, imports, capacity, batteries, curtailment

In-state generation by resource is built from the EIA-923 Page 1 schedule (California plants, reported fuel and prime mover classified into resource classes; hydro is not split by size because EIA-923 carries no unit capacity). Net imports are the CEC's statewide total-system series (2012-2024; the CEC has not yet published 2025 imports, and the 2021 per-year page on the CEC site repeats the 2020 table, so the multi-year table is used). The CAISO-only net interchange from chapter 1 is shown as a proxy for 2019-2025."""),
    code("""s = table("ch3_supply_by_year", index_col=0); (s / 1000).round(1).loc[[2010, 2012, 2015, 2018, 2020, 2022, 2023, 2024, 2025]]"""),
    code("""show("fig3_01_generation_by_resource")"""),
    code("""table("ch3_cec_imports_by_year").round(0)"""),
    code("""c = table("ch3_eia860_capacity_by_resource"); (c.pivot(index="year", columns="resource", values="nameplate_mw") / 1000).round(1).loc[[2010, 2013, 2016, 2019, 2022, 2025]]"""),
    code("""pd.concat([table("ch3_battery_capacity").set_index("year"), table("ch3_caiso_curtailment_annual").set_index("year")], axis=1).round(0)"""),
    md("""**Most recent data (2026).** The CEC has not published 2025 statewide imports and the EIA-860 annual file ends in 2025, so the latest points come from three other files: the EIA-923 monthly file through June 2026 (preliminary; it includes EIA's state-level increment rows for plants that report annually), the EIA-860M inventory of July 2026, and the CAISO curtailment series through August 2026. The EIA-860M for August 2026 was not yet published on 2026-09-22 (checked)."""),
    code("""h1 = table("ch3_generation_jan_jun_2025_2026_monthly_respondents"); hp = h1.pivot(index="resource", columns="year", values="gwh_jan_jun"); hp["change_pct"] = (hp[2026] / hp[2025] - 1) * 100; hp.round(1)"""),
    code("""table("ch3_caiso_net_imports_jan_jun").round(2)"""),
    code("""snap = table("ch3_capacity_snapshot_2026_07"); print(json.loads((PROCESSED / "ch3_capacity_snapshot_2026_07.json").read_text())); snap.round(0)"""),
    code("""show("fig3_02_capacity_storage_curtailment")"""),
    md("""**Reading.** In-state generation was 204 TWh in 2010 and 205 TWh in 2025, but its composition inverted: natural gas fell from 109 to 75 TWh (53 to 36 percent of in-state generation) and solar rose from under 1 to 55 TWh, so solar and wind together went from 3 to 34 percent. Nuclear halved with the San Onofre closure. Statewide net imports fell from 103 TWh in 2012 (34 percent of the total system) to 62 TWh in 2024 (22 percent). Operable capacity rose from 73 to 107 GW, of which solar added 24 GW and batteries 15 GW (51 GWh of energy capacity across 281 units by 2025); gas capacity fell only from 45 to 40 GW. Curtailment of wind and solar rose from 0.2 TWh in 2015 to 3.8 TWh in 2025, and reached 4.9 TWh in the first eight months of 2026. The 2026 year-to-date data continue the trend: January to June in-state generation was 89.6 TWh against 97.4 TWh a year earlier, with gas down 28 percent and solar up 6 percent, CAISO net imports rose from 15.7 to 20.6 TWh over the same months, and by July 2026 capacity had reached 109 GW with 16.3 GW and 56 GWh of batteries."""),
    md("""## 2. Retirement schedule

EIA-860M planned retirement dates for every California operating unit, plus the State Water Board once-through-cooling compliance dates (Table 1 of the policy as amended August 2023): Alamitos 3-5, Huntington Beach 2 and Ormond Beach 1-2 by December 31, 2026; Haynes 1, 2 and 8, Harbor 5 and Scattergood 1-2 by December 31, 2029; Diablo Canyon 1-2 by October 31, 2030 (SB 846). Haynes, Harbor and Diablo Canyon carry no retirement date in EIA-860M; the OTC date is used for them in case C."""),
    code("""otc = table("ch3_otc_units"); otc[["plant_name", "gen_id", "technology", "mw", "operating_year", "eia_planned_retirement_year", "otc_compliance_date", "schedule_year"]]"""),
    code("""sched = table("ch3_eia860m_planned_retirements"); sched[sched.planned_retirement_year <= 2035].groupby(["planned_retirement_year", "resource"]).mw.sum().unstack().fillna(0).round(0)"""),
    code("""show("fig3_03_retirement_schedule")"""),
    md("""## 3. Supply-side realization model

For every California unit in the Planned sheet of the January EIA-860M file of each year 2016-2022, the outcome by the December 2025 file is recorded: operating (or operated and since retired), cancelled (the cumulative Canceled or Postponed sheet), still planned, or dropped from the survey without a cancellation record (treated as cancelled). Units that appear in several January lists contribute one observation per vintage; standard errors are clustered by unit.

- **Logistic model** of completion by December 2025 on technology, log nameplate, planned lead time (planned commercial date minus file date), the observation window (December 2025 minus file date) and construction status at the vintage.
- **Delay**: Kaplan-Meier time from the planned to the actual commercial date with cancellations censored (an upper bound), and the cumulative incidence of completion with cancellation as a competing risk (Aalen-Johansen)."""),
    code("""table("ch3_realization_by_vintage").round(2)"""),
    code("""table("ch3_realization_by_technology").sort_values("mw_planned", ascending=False).round(2)"""),
    code("""table("ch3_realization_by_status").round(2)"""),
    code("""table("ch3_logit_coefficients").round(3)"""),
    code("""summ = json.loads((PROCESSED / "ch3_logit_summary.json").read_text()); {k: v for k, v in summ.items() if k != "no_status"}"""),
    code("""table("ch3_logit_specs").round(3)  # A: main; B: without status; C: planned year + vintage fixed effects (the literal specification)"""),
    code("""show("fig3_04_realization_model")"""),
    md("""**Reading.** Across the seven January vintages (925 unit-vintages, 513 distinct units, 64 GW planned), 69 percent of units and 65 percent of planned megawatts were operating by December 2025; by vintage the megawatt completion rate ranges from 50 percent (2018) to 76 percent (2020). Solar (71 percent of MW), batteries (76) and wind (78) complete at similar rates; natural gas completes 44 percent of planned megawatts and geothermal 6 percent. Construction status is the strongest signal: units under construction at the vintage completed 77 percent of their megawatts against 54 percent for units whose approvals had not been initiated. In the logistic model each additional year of planned lead time cuts the odds of completion within the window by more than half (odds ratio 0.46), a longer observation window raises them (1.17 per year), being under construction doubles them (1.98), and gas and geothermal carry lower odds than solar. Lead time and window are a reparametrisation of planned year and vintage; the literal specification with planned year and vintage fixed effects (specification C) gives the same ranking of technologies and status. Among completed units the median delay from the planned to the actual commercial date is 3 months, a quarter are on time or early and a quarter are more than a year late; treating cancellation as a competing risk, 53 percent of planned units are operating within 12 months of their planned date, 62 percent within 24 and 70 percent within 60, while 23 percent have been cancelled or dropped by then."""),
    md("""## 4. Probability-weighted planned supply for 2030

The July 2026 planned list for California (229 units, 20.1 GW with planned dates through 2030) is weighted by the logistic model's completion probability for a window ending December 2030. Energy uses realised 2023-2025 capacity factors (batteries and pumped storage contribute no net energy); peak contribution uses ELCC values from the CPUC/E3-Astrape mid-term reliability study (2028 tranche) for solar, wind, batteries and pumped storage, and stated derates for firm resources and hydro. Case C subtracts the EIA planned retirements through 2030, the OTC units without an EIA date and Diablo Canyon at its OTC compliance date; a sensitivity keeps Diablo Canyon."""),
    code("""pl = table("ch3_planned_current_weighted"); pl[pl.planned_year <= 2030].groupby("resource").agg(units=("mw", "size"), planned_mw=("mw", "sum"), weighted_mw=("weighted_mw", "sum"), mean_p=("p_2030", "mean")).round(2)"""),
    code("""pl[pl.planned_year <= 2030].groupby("status_group").agg(units=("mw", "size"), planned_mw=("mw", "sum"), weighted_mw=("weighted_mw", "sum")).round(0)"""),
    code("""table("ch3_elcc_values"); table("ch3_capacity_factors").round(3)"""),
    code("""cases = table("ch3_cases_2030"); cases.pivot(index="resource", columns="case", values="capacity_mw").round(0)"""),
    code("""cases.groupby("case")[["capacity_mw", "energy_twh", "peak_contribution_mw"]].sum().round(1)"""),
    code("""cs = json.loads((PROCESSED / "ch3_cases_2030_summary.json").read_text()); {k: v for k, v in cs.items() if k != "weighted_share_by_resource"}"""),
    code("""show("fig3_05_cases_2030")"""),
    md("""### The workshop format: production by technology, 2025 and the 2030 cases

The stacked bars repeat Fingrid's projection chart for California: EIA-923 in-state generation in 2025 and the three 2030 cases at realised capacity factors, by technology."""),
    code("""table("ch3_production_projection").pivot(index="resource", columns="column", values="twh").round(1)"""),
    code("""show("fig3_06_production_projection")"""),
    md("""**Reading.** If everything on the July 2026 planned list builds, California's nameplate capacity reaches 128 GW in 2030, 236 TWh a year at realised capacity factors and 78 GW of ELCC-derated peak contribution. Weighting by the realization model removes a third of the planned additions (13.2 of 20.1 GW survive: 71 percent of batteries and solar, 78 percent of wind, 31 percent of gas, 13 percent of the two pumped-storage projects, whose approvals have not been initiated), giving 121 GW, 231 TWh and 74 GW. Subtracting 6.5 GW of scheduled retirements, of which Diablo Canyon is 2.3 GW, leaves 114 GW, 204 TWh and 68 GW; with Diablo Canyon continuing, 117 GW, 222 TWh and 71 GW. The supply side therefore adds about 10 to 13 GW of nameplate and 6 to 8 GW of peak contribution by 2030 net of retirements, against the 4 GW of managed net peak growth in the adopted forecast and the 20.7 GW of data center requests located in California from chapter 2. That comparison is the object of the next chapter."""),
]
nb = nbf.v4.new_notebook(); nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "capstone (.venv)", "language": "python", "name": "capstone"}, "language_info": {"name": "python"}}
nbf.write(nb, NB); print("wrote", NB)
if "--execute" in sys.argv:
    subprocess.run([str(ROOT / ".venv/bin/jupyter"), "nbconvert", "--to", "notebook", "--execute", "--inplace", "--ExecutePreprocessor.timeout=1200", str(NB)], check=True, cwd=ROOT)
    print("executed")
