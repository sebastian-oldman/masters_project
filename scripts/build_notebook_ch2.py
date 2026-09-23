#!/usr/bin/env python
"""Build and execute notebooks/02_data_center_growth.ipynb from the chapter 2 outputs."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "02_data_center_growth.ipynb"
md = lambda s: nbf.v4.new_markdown_cell(s)  # noqa: E731
code = lambda s: nbf.v4.new_code_cell(s)  # noqa: E731

cells = [
    md("""# 02 · Data center growth in California (RQ1)

Chapter 2 of *Mapping the Consumption Gap*. Reproduces the national construction-spending chart with rigor, tests for structural breaks, builds the California proxies, assembles every vintage of the CEC energization tiers, and answers RQ1 in a table.

Outputs are produced by `scripts/run_chapter2.py` from `src/ch2_growth.py`; this notebook displays them. Bootstrap p-values use 199 moving-block replications; rerunning the pipeline reproduces them exactly (fixed seeds).

| Step | Sources (manifest ids) |
|---|---|
| 1-2. Census chart, breaks, forecasts | `census_c30_privsatime`, `census_c30_privtime` |
| 3. California proxies | `qcew_518210_*`, `cbre_*_infogram_*` (via `cbre_california_market_series.csv`), `epoch_data_center_timelines`, `epoch_data_centers` |
| 4. Tier vintages | `cec_dc_forecast_2024iepr`, `cec_prelim_dc_forecast_2025`, `cec_dc_methodology_memo_2026`, `cec_assembly_hearing_2026_01_28`, `cec_tn266008`, `cec_tn268459`, `cec_tn272026` |
| 5. RQ1 denominators | `caiso_key_statistics_2026_08`, chapter 1 tables, `cec_tn268124`, `cec_tn268727`, `cec_tn268824` |
"""),
    code("""import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path().resolve().parent))
import pandas as pd, numpy as np
from IPython.display import Image, display
from src.paths import PROCESSED, FIGURES
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", 80)
def show(name): display(Image(filename=str(FIGURES / f"{name}.png")))
def table(name, **kw): return pd.read_csv(PROCESSED / f"{name}.csv", **kw)"""),
    md("""## 1. The Census chart, reproduced from the raw C30 workbook

US private construction spending in the Census Bureau's "Data center" category (a line item under nonresidential/office since January 2014), seasonally adjusted annual rate, millions of dollars. The second panel is month-over-month growth."""),
    code("""c = table("ch2_census_c30_data_center", index_col=0, parse_dates=True)
c[["data_center_saar","data_center_nsa","nonresidential_saar","dc_share_of_nonres_pct","mom_growth_pct","yoy_growth_pct","flag_saar"]].iloc[[0, 60, 106, 107, -3, -2, -1]].round(2)"""),
    code("""show("fig2_01_census_data_center_construction")"""),
    md("""**Reading.** Spending rose from $1.6 billion a year in January 2014 to $13.9 billion in November 2022 and $75.2 billion in July 2026 (preliminary), and data centers went from 0.5 percent to 10 percent of all private nonresidential construction. Month-over-month growth averaged 4.1 percent in 2023-2026 against 1.2 percent in 2019-2021."""),
    md("""## 2. Structural breaks and forecasts on the log series

- **Chow test** at December 2022, the first full month after the November 30, 2022 launch (the November observation stays in the pre-launch segment): break in intercept and slope of the log-linear trend, classical F plus a HAC-robust Wald test.
- **Bai-Perron**: global least-squares search over all partitions with 15 percent trimming (minimum segment 23 months) and up to five breaks (the most the trimming allows, so the choice is uncensored); number of breaks chosen by BIC, by LWZ and by the sequential supF(l+1|l) procedure with moving-block residual bootstrap p-values; supF(0|1) with the same bootstrap; the single-break date with a residual-bootstrap 90 percent interval; `ruptures` dynamic programming as a cross-check.
- **Forecasts**: ARIMA(p,1,q) with drift chosen by AIC, and ETS with damped additive trend, both on log levels, 24 months ahead; point forecasts are back-transformed log medians. A rolling-origin backtest over the last 24 months compares both with naive and drift benchmarks."""),
    code("""summ = json.loads((PROCESSED / "ch2_census_break_summary.json").read_text())
{k: summ[k] for k in ["chow_F","chow_p","wald_hac_p","cagr_pre","cagr_pre_lo","cagr_pre_hi","cagr_post","cagr_post_lo","cagr_post_hi","bp_break1","bp_break1_ci90","bp_supF_1","bp_supF_1_boot_p","bp_breaks_bic","bp_m_bic","bp_m_lwz","bp_m_seq","bp_seq_p","ruptures_dynp","arima","ets"]}"""),
    code("""pd.DataFrame(summ["sequential"]["levels"]).T.rename_axis("breaks tested (l+1 | l)").round(3)"""),
    code("""table("ch2_census_bai_perron").round(3)"""),
    code("""table("ch2_census_segment_growth").round(3)"""),
    code("""show("fig2_02_census_breaks_and_forecast")"""),
    code("""fa = table("ch2_census_forecast_arima", index_col=0, parse_dates=True); fe = table("ch2_census_forecast_ets", index_col=0, parse_dates=True)
pd.concat({"ARIMA": (fa/1000).round(1), "ETS": (fe/1000).round(1)}, axis=1).iloc[[0, 5, 11, 17, 23]]"""),
    code("""table("ch2_census_forecast_backtest").round(2)"""),
    md("""**Reading.** The known-date test is unambiguous (Chow F = 63, p < 0.001; HAC Wald p < 0.001): compound growth was 26 percent a year [22, 31] through November 2022 and 53 percent a year [46, 61] from December 2022, the first full post-launch month (assigning November to the post period, as the first pass did, gave 54). The test dates the trend change; it does not establish that the launch caused it. Letting the data locate breaks changes the story in two respects. BIC and LWZ both choose four breaks (October 2016, December 2018, March 2022, June 2024), so the acceleration began eight months before ChatGPT, in the hyperscaler capital-spending ramp of early 2022, and it has already slowed once: 61 percent a year [56, 67] from March 2022 to May 2024, then 36 percent a year [31, 41] from June 2024 to July 2026, still four times the 9 percent of 2019 to early 2022. The sequential supF(l+1|l) procedure is more conservative: supF(1|0) = 125 rejects no break (p = 0.02) but supF(2|1) = 37 has p = 0.085, so at 5 percent it stops at one break (November 2020), although the third and fourth breaks are each significant once the earlier ones are in place (p = 0.02, 0.005). `ruptures` reproduces all four BIC dates within one month. Both forecasts continue the recent trend with wide bands: $95-98 billion by July 2027 and $115-133 billion by July 2028 (medians), with 95 percent bands spanning $51-259 billion by then. The backtest is the caveat: at a 12-month horizon the MAPE is 14 percent (ARIMA) and 19 percent (ETS) against 13 percent for a log random walk with drift, all forecasts ran low on average, and the 95 percent bands covered 92 and 79 percent of outcomes. National nominal dollars, not California megawatts."""),
    md("""## 3. California proxies: QCEW, CBRE, Epoch

No state-level construction-spending series exists. Three proxies are tested with the same battery (Chow at the first period after November 2022, Bai-Perron):
- BLS QCEW, NAICS 518210, private, California: establishments, employment, wages by quarter (2014 Q1 to 2026 Q1; the BLS open-data API serves no 518210 slice before 2014).
- CBRE Silicon Valley colocation market: MW under construction each half-year since H1 2016 (chapter history table) and inventory (overview tables). Cushman & Wakefield's tables are gated; JLL gives single-period inventory only.
- Epoch AI frontier facilities: cumulative facility power from per-site timelines. The snapshot contains no California observation, which is a limit of the hub's coverage rather than evidence of zero California activity, so only the national series can be tested."""),
    code("""comp = table("ch2_break_test_comparison")
comp[["series","n","start","end","known_break_period","chow_F","chow_p","wald_hac_p","cagr_pre","cagr_post","bp_break1","bp_break1_ci90","bp_m_bic","bp_m_lwz","bp_m_seq","bp_breaks_bic","bp_supF_1_boot_p","note"]].round(3)"""),
    code("""comp[["series","bp_seq_p"]].dropna()"""),
    code("""show("fig2_03_california_proxies")"""),
    code("""q = table("ch2_qcew_518210_california"); q["fips"] = q.fips.astype(str).str.zfill(5)
st = q[q.fips=="06000"].set_index("period")[["qtrly_estabs","employment","total_qtrly_wages"]]
st.iloc[[0, 8, 16, 24, 31, 32, 36, 40, -1]]"""),
    code("""cb = table("ch2_cbre_california"); cb[(cb.kind=="chapter_history")&(cb.metric=="under_construction_mw")][["period","value","edition"]].reset_index(drop=True).T"""),
    md("""**Reading.** The California proxies move the opposite way from the national construction series. QCEW employment in data processing and hosting grew 12 percent a year from 2014 through 2022 (25,000 to 74,000 jobs), then flattened (−0.3 percent a year after 2023 Q1, Chow F = 15, p < 0.001); establishments show the same pattern (11 percent to 0.5 percent). Data-located breaks in these quarterly series are diffuse: BIC places four breaks in each (the last in 2023 Q3 and 2023 Q2), the single-break bootstrap is significant for employment (p = 0.035) but not establishments (p = 0.285), and the sequential procedure keeps none. Silicon Valley's construction pipeline rose from about 44 MW in 2016 to 142 MW by late 2022 and has since sat between 125 and 168 MW with no break at 2023 (Chow p = 0.61; BIC one break at H2 2020, LWZ and sequential none), while the national frontier-site series went from nothing to 15 GW (a reconstruction from sampled sites). Epoch's snapshot has no California observation (coverage, not a count of zero). In short, the post-2022 boom shows up in California only as requests to connect, not as built or staffed capacity, which is consistent with the power constraints Silicon Valley Power and CBRE both describe."""),
    md("""## 4. Every vintage of the CEC energization tiers

Vintages found in the record: December 2024 (PG&E and SCE agreements plus applications, from the 2024 IEPR Update comparison), summer 2025 (seven utilities; PG&E and SCE split into agreements plus applications versus inquiries from the published deck's page 7, the other five as totals), December 2025 (seven utilities by tier, methodology memo Table 1 and the Assembly slide), the August 2026 workshop (restates December 2025), SCE's two public project databases (August 2025 and January 2026, the only vintages with cancellations), and PG&E's own pipeline by PG&E stage from its Q2 2026 earnings table (March and June 2026, reproduced in TN 272065). The workshop copy of the preliminary deck (TN 267165) labelled SCE's summer-2025 agreements plus applications as 2,492 MW and SVP's total as 1,382 MW; the published deck corrects these to 143 and 1,375 MW and the corrected values are used. VEA's 2,600 MW (summer 2025 and December 2025) are located in Nevada per the memo footnote and are separated from the California-only totals (19,156 and 20,677 MW); SCE's canceled requests are shown separately from its active pipeline. The June 2026 known-load charts in the 2026 IEPR workshop are images without numbers; the monthly snapshot watches docket 26-IEPR-03 for the next vintage."""),
    code("""tv = table("ch2_tier_vintages"); tv.pivot_table(index=["vintage","label"], columns="tier", values="mw", aggfunc="sum").fillna(0).round(0)"""),
    code("""tv[tv.note.astype(str).str.len() > 0][["vintage","label","utility","tier","mw","note"]]"""),
    code("""tv.sort_values(["vintage","label","utility","tier"])[["vintage","label","utility","tier","mw","source"]]  # every utility-by-tier MW figure quoted in the chapter, with its source"""),
    code("""show("fig2_04_tier_vintages")"""),
    md("""### The workshop format: current capacity, statistics of the projects, data centers against electric cars

Two figures in the layout of the Finnish workshop slides: the existing capacity with the Santa Clara (SVP) cluster's share of the statewide 2023 estimate, the December 2025 requests by stage with their ratios to the existing peak and to the CAISO record peak, and the annual energy of the requests expressed in electric-car years (3 MWh per car per year, the assumption from the Finnish slides; no California per-vehicle figure is in the record)."""),
    code("""table("ch2_project_statistics").round(2)"""),
    code("""table("ch2_sce_largest_requests")"""),
    code("""show("fig2_05_project_statistics")"""),
    code("""table("ch2_ev_equivalents").round(2)"""),
    code("""show("fig2_06_data_centers_vs_evs")"""),
    code("""table("ch2_cec_forecast_reference_points")"""),
    md("""**Reading.** Requests grew from 6,771 MW (December 2024, two utilities, no inquiries) to 21,756 MW (summer 2025; PG&E 10,080 MW in agreements plus applications and 1,588 MW in inquiries, SCE 143 and 5,685 MW) and 23,277 MW (December 2025): 5,086 MW signed, 9,587 MW in application, 8,604 MW in inquiry. Of these, VEA's 2,600 MW of applications are in Nevada, so the California-only totals are 19,156 MW (summer 2025) and 20,677 MW (December 2025). The three source families (CEC vintages, SCE database, PG&E pipeline) differ in utilities, stages and dates and are not one growth series. PG&E's own pipeline (PG&E stages, no inquiries) then went from 5,090 MW in March 2026 to 12,710 MW in June 2026 after the 2026 cluster study, with 3,880 MW at signed work performance agreement, 490 MW at interconnection construction agreement and 140 MW in construction; Cal Advocates notes PG&E had filed only about 650 MW of such agreements with the CPUC. The sum is 45 percent of CAISO's record peak of 52,061 MW and 23 times the roughly 1,000 MW of existing data center peak demand the CEC reports, or 10 to 29 times the chapter 1 range of existing average load. SCE's public database shows what happens inside a vintage: between August 2025 and January 2026 its inquiries fell from 5,934 MW to 1,772 MW as 3,100 MW moved into applications, and canceled requests rose from 709 MW to 3,137 MW, and the active total fell from 6,201 to 5,162 MW, so the growth in SCE's records is cancellations: 38 percent of everything SCE had ever logged was canceled within five months."""),
    md("""## 5. RQ1: the pipeline by stage against the grid, existing load and the adopted forecast"""),
    code("""rq = table("ch2_rq1_table"); rq.round(1)"""),
    code("""den = json.loads((PROCESSED / "ch2_rq1_denominators.json").read_text()); {k: round(v, 1) for k, v in den.items()}"""),
    code("""table("ch2_ced2025_planning_totals")[["metric","scope","y2025","y2030","y2040"]].round(0)"""),
    md("""**Answer to RQ1.** By stage, the planned data center capacity located in California is 5,086 MW signed, 6,987 MW in application and 8,604 MW in inquiry, 20,677 MW in total (December 2025; the CEC's reported 23,277 MW includes 2,600 MW of VEA applications in Nevada). That total is 40 percent of CAISO's record instantaneous peak (a scale comparison, not a coincident ratio) and 47 percent of the 2025 peak; 21 times the state's existing data center peak demand and 19-26 times the existing average load implied by the chapter 1 statewide estimate and conversion; and 5.1 times the growth in CAISO's managed net peak that the adopted 2025 IEPR planning forecast projects between 2025 and 2030 (4,019 MW). Even at the CEC's 67 percent utilization the pipeline is 3.4 times that growth, and its energy equivalent (about 107 TWh a year) is 3.1 times the statewide energy growth the forecast expects over the same period. Requests are not simultaneous demand and signed agreements are not operating capacity. The CEC's own forecast already embeds part of this: its data center component at the CAISO peak rises from 96 MW in 2025 to 1,743 MW in 2030 in the planning scenario (4,377 MW in the local-reliability scenario), and its data-center-only deliveries reach 12.1 TWh in 2030, about a third of projected statewide energy growth. The gap between requests and forecast is the object of the rest of the study."""),
]
nb = nbf.v4.new_notebook(); nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "capstone (.venv)", "language": "python", "name": "capstone"}, "language_info": {"name": "python"}}
nbf.write(nb, NB); print("wrote", NB)
if "--execute" in sys.argv:
    subprocess.run([str(ROOT / ".venv/bin/jupyter"), "nbconvert", "--to", "notebook", "--execute", "--inplace", "--ExecutePreprocessor.timeout=1200", str(NB)], check=True, cwd=ROOT)
    print("executed")
