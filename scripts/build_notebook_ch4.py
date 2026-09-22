#!/usr/bin/env python
"""Build and execute notebooks/04_gap_model.ipynb and notebooks/05_regimes_flexibility.ipynb from the chapter 4 outputs."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
md = lambda s: nbf.v4.new_markdown_cell(s)  # noqa: E731
code = lambda s: nbf.v4.new_code_cell(s)  # noqa: E731

SETUP = code("""import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path().resolve().parent))
import pandas as pd, numpy as np
from IPython.display import Image, display
from src.paths import PROCESSED, FIGURES
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", 90)
def show(name): display(Image(filename=str(FIGURES / f"{name}.png")))
def table(name, **kw): return pd.read_csv(PROCESSED / f"{name}.csv", **kw).convert_dtypes()  # integer-valued columns display as integers""")

NB4 = [
    md("""# 04 · Putting it together: the 2030 gap (RQ2)

Chapter 4 of *Mapping the Consumption Gap*, part 1. Demand scenarios for 2030 under four counting rules (the proposal's upper bound, the CEC's central case, an ERCOT-calibrated stock-flow case and a PJM-style firm-only case) on top of the IEPR's low/mid/high non-data-center growth; a 10,000-draw Monte Carlo of the 2030 energy and net-peak gap against the probability-weighted supply of chapter 3; and one-at-a-time and Sobol sensitivity.

Outputs are produced by `scripts/run_chapter4.py` from `src/ch4_gap.py` (about a minute); this notebook displays them.

| Step | Sources (manifest ids) |
|---|---|
| 1. Tiers and IEPR growth | `cec_assembly_hearing_2026_01_28`, `cec_dc_methodology_memo_2026`, `cec_tn268722/268727/268725/268726` (CED 2025 forms), `cec_tn268124` (peak components), `cec_tn268824` (data center deliveries) |
| 2. ERCOT stock-flow | `ercot_board_2025_12_system_planning`, `ercot_tac_2026_03_large_load_status`, `ercot_monthly_2025_07 .. 2026_06`, `ercot_house_hearing_2026_04_09`, `ercot_board_2026_05_interconnection_update`, `ercot_ops_overview_2026_06/08` |
| 3. Demand cases | the above plus `pjm_lar_summary_2025_11_24` (PJM rules) |
| 4-5. Monte Carlo and sensitivity | chapter 3 outputs (`ch3_cases_2030`, `ch3_planned_current_weighted`, `ch3_capacity_factors`, `ch3_elcc_values`, `ch3_supply_by_year`, `ch3_cec_imports_by_year`) |
"""),
    SETUP,
    md("""## 1. California tiers and the IEPR's non-data-center growth

The December 2025 tiers are the CEC's published statewide totals minus VEA's requests, which are in Nevada. Non-data-center demand in 2025 and 2030 is the CED 2025 statewide energy to serve load and coincident peak minus the CEC's own data center component (energy from the Planning forecast's data center allocations, peak from the CAISO DATA_CENTER column of the peak workbook). Low = Planning (managed), mid = Baseline (before AAEE/AAFS), high = Local Reliability; the Local Reliability plus known loads case is shown for reference."""),
    code("""table("ch4_ca_tiers")"""),
    code("""json.loads((PROCESSED / "ch4_cec_parameters.json").read_text())"""),
    code("""g = table("ch4_iepr_growth_cases"); g.round(0)"""),
    code("""table("ch4_iepr_growth_summary").round(0)"""),
    code("""dc = table("ch4_ced2025_data_center_component"); dc[(dc.tac.isin(["CAISO", "VEA"])) & (dc.year.isin([2025, 2028, 2030]))].pivot_table(index=["scenario", "tac"], columns="year", values="data_center_mw")"""),
    md("""**The CEC case rebuilt from its parameters.** Confidence by tier times 67 percent utilization, with SVP's requests exempt from the confidence levels (memo p. 9), reproduces the memo's 2040 endpoints exactly (4,855 MW Planning, 7,381 MW Local Reliability). The CEC's own ramp profile, the share of the 2040 CAISO component reached in each year, puts 36 and 60 percent of that demand on line by 2030; the replicated 2030 values are within 2 and 6 percent of the published components once VEA is removed."""),
    code("""table("ch4_cec_replication").round(3).T"""),
    code("""pr = table("ch4_cec_ramp_profile"); pr.pivot(index="year", columns="scenario", values="share_of_2040").round(3).T"""),
    md("""## 2. ERCOT phase-transition rates and the stock-flow chain

Monthly stocks by phase were transcribed from ERCOT's monthly newsletters, the March 2026 TAC report, the April and June 2026 board decks, the April 2026 legislative hearing decks and the June and August 2026 operational overviews (every value carries its manifest id). Four monthly hazards are estimated from the flows between phases, and a Markov chain gives the probability that a project starting in each phase is energized within 60 months, the horizon from the December 2025 tier vintage to December 2030. California tiers map to ERCOT phases as inquiry = no studies submitted, application = under ERCOT review, signed agreement = planning studies approved."""),
    code("""table("ch4_ercot_queue_monthly")"""),
    code("""table("ch4_ercot_approvals_monthly")"""),
    code("""s = table("ch4_ercot_status_snapshots"); s[s.in_service_year_through == s.groupby("snapshot").in_service_year_through.transform("max")].pivot_table(index=["snapshot", "as_of"], columns="status", values="mw").round(0)"""),
    code("""table("ch4_ercot_narrative")"""),
    code("""table("ch4_ercot_transition_rates").round(4)"""),
    code("""c = table("ch4_ercot_chain"); c.pivot_table(index="start_state", columns=["hazard_scale", "cancel_hazard"], values="p_energized").round(3)"""),
    code("""show("fig4_05_ercot_queue")"""),
    md("""**Reading.** ERCOT's tracked requests went from 63 GW in December 2024 to 239 GW in March 2026 before the March 2026 submissions, then to 411 GW (87 percent data centers) and 466 GW by June 2026. Approvals moved far more slowly: planning studies approved rose from 12.9 to 16.6 GW and approvals to energize from 6.9 to 9.0 GW between May 2025 and March 2026 (9.5 GW by August 2026), and the observed monthly peak of approved loads was 4.0 to 4.3 GW. The monthly hazards are 2.1 percent from no-studies to review (an upper bound, since cancellations leave the same stock), 0.75 percent from review to studies approved, 1.6 percent from studies approved to approval to energize and 3.1 percent from approval to observed energization. At those rates a project that already has approved studies has a 37 percent chance of being energized within 60 months, one under review 6 percent and one without studies 2 percent; doubling every hazard gives 72, 25 and 12 percent."""),
    md("""## 3. Demand cases for 2030

Each row applies a counting rule to the same 20,677 MW: the proposal's upper bound (every MW builds, flat), the CEC's published Planning and Local Reliability values (and a literal replication of the CEC parameters: confidence 70/33/0 or 100/50/10, 67 percent utilization, a 7-year linear ramp with applications and inquiries starting in 2028), the ERCOT-calibrated chain, and the PJM rules (only signed agreements count before 2030, at 70 percent utilization with a ramp of at least 36 months; from 2030 half of non-firm requests). Energy uses a 0.88 load factor except where the CEC's own deliveries are used."""),
    code("""table("ch4_demand_cases_2030").round(3)"""),
    md("""Each demand case on top of each IEPR non-data-center case (statewide peak and energy in 2030 and the growth from 2025):"""),
    code("""tt = table("ch4_demand_totals_2030"); tt[tt.demand_case.isin(["Upper bound: every MW builds, flat load", "CEC central (Planning forecast, published)", "CEC high (Local Reliability, published)", "ERCOT-calibrated stock-flow", "PJM-style: firm only (signed agreements)"])].round(1)"""),
    code("""show("fig4_01_demand_scenarios_2030")"""),
    md("""## 4. Monte Carlo gap model

10,000 draws over the tier realization probabilities, utilization, the share of realized capacity on line by 2030, the load factor, per-unit completion of the 229 planned generating units (chapter 3 logit probabilities), the hydro capacity factor, solar and wind output, 2030 net imports, the IEPR growth case, Diablo Canyon's status and the planning reserve margin. The **energy gap** is demand growth 2025-2030 (non-data-center growth plus the data center case) minus supply growth (weighted new capacity at recent capacity factors, minus retirements, plus the change in imports); the **net-peak gap** is demand peak growth times one plus the reserve margin minus the change in ELCC-weighted capacity. Positive values mean that demand growth outruns supply growth at recent operating patterns; the absolute balances compare 2030 levels directly (in-state ELCC only, so imports' peak contribution is excluded). The upper bound is reported in every table."""),
    code("""table("ch4_mc_inputs")"""),
    code("""table("ch4_mc_summary").round(1)"""),
    code("""table("ch4_upper_bound_2030").round(1)"""),
    code("""json.loads((PROCESSED / "ch4_mc_key_numbers.json").read_text())"""),
    code("""d = pd.read_parquet(PROCESSED / "ch4_mc_draws.parquet"); d.groupby(["case_name", "diablo_continues"])[["gap_energy_twh", "gap_peak_mw", "dc_peak_mw", "supply_energy_growth_twh", "elcc_growth_mw"]].median().round(1)"""),
    code("""show("fig4_02_gap_distributions")"""),
    md("""**Reading.** The median 2030 energy gap is 50 TWh (P5 19, P95 78) and the median net-peak gap 7.2 GW (P5 4.2, P95 10.1); both are positive in every draw because non-data-center growth alone (24 to 45 TWh, 3.6 to 5.8 GW) exceeds the supply growth the weighted pipeline delivers (mean 5 TWh and 1.1 GW of ELCC, with Diablo Canyon's 2.3 GW the single largest swing). The data center contribution is 2.3 GW and 18 TWh at the median (P5-P95 1.4 to 3.6 GW). Closing the median energy gap with the existing gas fleet would require raising its capacity factor from 0.24 to 0.40. The proposal's upper bound, every requested MW operating flat, gives an energy gap of 202 to 242 TWh and a peak gap of 25.5 to 30.2 GW, four to five times the probability-weighted P95."""),
    md("""## 5. Sensitivity

One-at-a-time swings hold every other input at its median and move one input between its 5th and 95th percentiles (low and high case for the IEPR case; retired and continuing for Diablo Canyon). Sobol first-order and total indices come from SALib's Sobol sequence (15,360 model evaluations); the per-unit completion is represented by its realization fraction."""),
    code("""table("ch4_tornado").round(2)"""),
    code("""sb = table("ch4_sobol"); sb.pivot(index="input", columns="metric", values=["S1", "ST"]).round(3).sort_values(("ST", "gap_energy_twh"), ascending=False)"""),
    code("""show("fig4_03_sensitivity")"""),
    md("""**Reading.** The energy gap is governed by the supply side and the non-data-center forecast: imports (28 TWh swing), the IEPR case (22), hydro (20) and Diablo Canyon (18) dominate, and the three data center probabilities together explain about 3 percent of the variance. The peak gap depends on Diablo Canyon (ST 0.39), the IEPR case (0.35), the data center ramp (0.14) and generation completion (0.07). The first-order indices sum to about one in both cases, so the model is nearly additive and the tornado ranking is reliable."""),
]

NB5 = [
    md("""# 05 · Regimes and flexibility (RQ3 and RQ4)

Chapter 4 of *Mapping the Consumption Gap*, part 2. The Duke-style curtailment-enabled headroom replicated on CAISO hourly load 2019-2025 (RQ4), the energy-side argument from negative-price hours and curtailment, the crosswalk of six data and measurement regimes with a common taxonomy and California's headline number under each counting rule (RQ3), and the optional emissions comparison of a flat versus a curtailable load.

Outputs are produced by `scripts/run_chapter4.py` from `src/ch4_gap.py` and `src/ch4_regimes.py`; this notebook displays them.

| Step | Sources (manifest ids) |
|---|---|
| Headroom | `ciso_hourly_2019_2025_clean.parquet` (chapter 1, EIA-930 CISO adjusted demand), `duke_rethinking_load_growth_2025_mirror` (method and CAISO values) |
| Energy side | chapter 1 price statistics (`caiso_oasis` day-ahead LMPs), chapter 3 curtailment (`caiso_curtailments_monthly_csv`) |
| Crosswalk | `cec_dc_methodology_memo_2026`, `cec_tn268459`, ERCOT decks and monthlies, `pjm_lar_summary_2025_11_24`, `pjm_2026_load_report_tables`, `eia_press585_dc_pilot_surveys`, `texas_sb6_2025_enrolled`, `caiso_comments_ferc_rm26_4_2025_11`, `nerc_rm26_4_accelerated_plan_2026_03`, `ferc_news_2026_04_16_large_load`, `ferc_news_2026_06_18_show_cause` |
| Emissions | `caiso_co2_intensity_hourly.parquet` (chapter 1, CAISO Today's Outlook) |
"""),
    SETUP,
    md("""## 1. Curtailment-enabled headroom (RQ4)

Duke's method: add a constant load L to every hour, count as curtailment any excess of demand plus L over the seasonal peak threshold (the maximum winter and non-winter demand across all years; for Pacific-coast balancing authorities winter is November to February), average the annual curtailment rate over the years, and goal-seek L for 0.25, 0.5, 1 and 5 percent. Three variants test the season definition and the sample of years."""),
    code("""table("ch4_headroom_summary").round(0)"""),
    code("""h = table("ch4_headroom_detail"); h[h.variant.str.startswith("Duke seasons (Nov")].groupby("limit")[["curtailment_rate", "hours_curtailed", "curtailed_mwh", "share_winter", "hours_below_90pct", "hours_below_75pct", "hours_below_50pct", "max_curtailment_mw"]].mean().round(3)"""),
    code("""h[(h.variant.str.startswith("Duke seasons (Nov")) & (h.limit == 0.005)].round(3)"""),
    md("""**Year by year.** The phase plan asks for the largest flat addition such that the hours above the historical peak stay under 0.25, 0.5 and 1 percent of each year. That hours criterion is solved in closed form from the sorted margins to the threshold, next to Duke's energy criterion solved year by year, for the Duke seasonal thresholds and for a single all-years peak."""),
    code("""hy = table("ch4_headroom_by_year"); hy.pivot_table(index=["variant", "year"], columns="limit", values=["headroom_hours_criterion_mw", "headroom_energy_criterion_mw"]).round(0)"""),
    code("""table("ch4_headroom_vs_gap").round(3)"""),
    code("""table("ch4_energy_side").round(0)"""),
    code("""show("fig4_04_headroom")"""),
    md("""**Reading.** On 2019-2025 CAISO demand the pooled headroom is 3.1 GW at 0.25 percent curtailment, 3.8 GW at 0.5 percent, 4.6 GW at 1 percent and 8.0 GW at 5 percent, against Duke's 4.2, 5.0 and 5.9 GW on 2016-2024 data; solved year by year, the energy criterion gives 3.3 to 4.2 GW at 0.5 percent and the stricter hours criterion 2.0 to 2.9 GW; the difference comes from the sample of years (the 2022-2025 subsample gives 2.7 to 4.1 GW) and the winter threshold, since 97 to 99 percent of the curtailment falls in November to February when winter evening loads sit close to the winter peak. At the 0.5 percent headroom the new load is curtailed in about 197 hours a year, in 18 of which less than half of it is available, and the largest single-hour cut is 3.8 GW. That headroom is 2.4 times the CEC's central data center addition, about equal to the PJM firm-only case, 53 percent of the median probability-weighted peak gap and 13 percent of the upper-bound peak gap. On the energy side, the SCE load-aggregation point had 877 negative-price day-ahead hours in 2025 (1,131 in 2024) and CAISO curtailed 3.8 TWh of wind and solar in 2025 and 4.9 TWh in January to August 2026, the equivalent of a 430 MW flat load running all year."""),
    md("""## 2. Regime crosswalk (RQ3)"""),
    code("""table("ch4_regime_crosswalk")"""),
    code("""table("ch4_regime_scores")"""),
    code("""table("ch4_regime_rubric")"""),
    code("""show("fig4_07_regime_scores")"""),
    code("""table("ch4_common_taxonomy")"""),
    code("""table("ch4_headline_by_regime").round(0)"""),
    code("""table("ch4_sce_size_classes").round(3)"""),
    code("""p = table("ch4_pjm_adjustments"); p[p.zone == "PJM RTO"].pivot(index="table", columns="year", values="mw")"""),
    code("""table("ch4_pjm_lar_chart_readings")"""),
    code("""show("fig4_05_ercot_queue")"""),
    md("""**Reading.** The same 20,677 MW is 20,677 MW under the CEC's and ERCOT's counting rules (both count every request regardless of study status), 5,086 MW under the PJM firm-only rule and the Texas forecast rule that admits only executed agreements after 2026 (3,560 MW of demand at PJM's 70 percent utilization), about 2,400 MW under ERCOT's realized phase-transition rates, and about 1,000 MW of measured existing load under a consumption survey like the EIA pilot. Thresholds cannot be applied to the CEC aggregates; in SCE's public project-level database 76 percent of active requested MW is in projects of 75 MW or more (the SB 6 threshold) and 95 percent in projects of 20 MW or more (the FERC ANOPR threshold)."""),
    md("""## 3. Emissions of a flat versus a curtailable load (optional)

CAISO hourly accounting intensity (chapter 1, valid hours). A 1 MW load is either flat, curtailed to zero in the highest-intensity 5, 10 or 25 percent of hours (energy lost), or shifted, with the same energy moved from those hours to the lowest-intensity hours (load doubles there)."""),
    code("""em = table("ch4_emissions_flat_vs_flexible"); em.pivot_table(index=["strategy", "share_hours"], columns="year", values="t_per_gwh").round(1)"""),
    code("""show("fig4_06_emissions_flat_vs_flexible")"""),
    md("""**Reading.** A flat load carried 183 t CO2 per GWh in 2025 (239 in 2023). Curtailing it in the highest-intensity quarter of hours lowers the intensity of what it still consumes by 20 percent; shifting the same energy into the lowest-intensity quarter of hours, which had a mean accounting intensity of 44 g/kWh in 2025, lowers it by 34 percent to 121 t per GWh."""),
]


def build(name, cells):
    nb = nbf.v4.new_notebook(); nb["cells"] = cells
    nb["metadata"] = {"kernelspec": {"display_name": "capstone (.venv)", "language": "python", "name": "capstone"}, "language_info": {"name": "python"}}
    path = ROOT / "notebooks" / name; nbf.write(nb, path); print("wrote", path)
    if "--execute" in sys.argv:
        subprocess.run([str(ROOT / ".venv/bin/jupyter"), "nbconvert", "--to", "notebook", "--execute", "--inplace", "--ExecutePreprocessor.timeout=1200", str(path)], check=True, cwd=ROOT)
        print("executed", name)


build("04_gap_model.ipynb", NB4)
build("05_regimes_flexibility.ipynb", NB5)
