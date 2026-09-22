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

- **Chow test** at December 2022 (first month after the ChatGPT launch): break in intercept and slope of the log-linear trend, classical F plus a HAC-robust Wald test.
- **Bai-Perron**: global least-squares search over all partitions with 15 percent trimming (minimum segment 23 months), number of breaks chosen by BIC and LWZ; supF(0|1) with a moving-block residual bootstrap p-value; the single-break date with a residual-bootstrap 90 percent interval; `ruptures` dynamic programming as a cross-check.
- **Forecasts**: ARIMA(p,1,q) with drift chosen by AIC, and ETS with damped additive trend, both on log levels, 24 months ahead."""),
    code("""summ = json.loads((PROCESSED / "ch2_census_break_summary.json").read_text())
{k: summ[k] for k in ["chow_F","chow_p","wald_hac_p","cagr_pre","cagr_pre_lo","cagr_pre_hi","cagr_post","cagr_post_lo","cagr_post_hi","bp_break1","bp_break1_ci90","bp_supF_1","bp_supF_1_boot_p","bp_breaks_bic","bp_m_bic","bp_m_lwz","ruptures_dynp","arima","ets"]}"""),
    code("""table("ch2_census_bai_perron").round(3)"""),
    code("""table("ch2_census_segment_growth").round(3)"""),
    code("""show("fig2_02_census_breaks_and_forecast")"""),
    code("""fa = table("ch2_census_forecast_arima", index_col=0, parse_dates=True); fe = table("ch2_census_forecast_ets", index_col=0, parse_dates=True)
pd.concat({"ARIMA": (fa/1000).round(1), "ETS": (fe/1000).round(1)}, axis=1).iloc[[0, 5, 11, 17, 23]]"""),
    md("""**Reading.** The known-date test is unambiguous (Chow F = 63, p < 0.001; HAC Wald p < 0.001): compound growth was 26 percent a year [22, 31] before December 2022 and 54 percent a year [47, 61] after. Letting the data locate breaks changes the story in one respect: BIC and LWZ both choose three breaks, October 2016, December 2018 and March 2022, so the acceleration began eight months before ChatGPT, in the hyperscaler capital-spending ramp of early 2022. Growth in the last segment (March 2022 to July 2026) is 55 percent a year [50, 61]. The bootstrap confirms the single-break supF is far outside the no-break distribution (p = 0.01) and `ruptures` reproduces every break date within one month. Both forecasts continue the trend with wide bands: roughly $95-100 billion by July 2027 and $115-135 billion by July 2028, with 95 percent bands spanning $50-260 billion by then."""),
    md("""## 3. California proxies: QCEW, CBRE, Epoch

No state-level construction-spending series exists. Three proxies are tested with the same battery (Chow at the first period after November 2022, Bai-Perron):
- BLS QCEW, NAICS 518210, private, California: establishments, employment, wages by quarter (2015 Q1 to 2026 Q1).
- CBRE Silicon Valley colocation market: MW under construction each half-year since H1 2016 (chapter history table) and inventory (overview tables). Cushman & Wakefield's tables are gated; JLL gives single-period inventory only.
- Epoch AI frontier facilities: cumulative facility power from per-site timelines. Epoch lists no California site, so the California series is identically zero and only the national series can be tested."""),
    code("""comp = table("ch2_break_test_comparison")
comp[["series","n","start","end","known_break_period","chow_F","chow_p","wald_hac_p","cagr_pre","cagr_post","bp_break1","bp_break1_ci90","bp_breaks_bic","bp_supF_1_boot_p","note"]].round(3)"""),
    code("""show("fig2_03_california_proxies")"""),
    code("""q = table("ch2_qcew_518210_california"); q["fips"] = q.fips.astype(str).str.zfill(5)
st = q[q.fips=="06000"].set_index("period")[["qtrly_estabs","employment","total_qtrly_wages"]]
st.iloc[[0, 8, 16, 24, 31, 32, 36, 40, -1]]"""),
    code("""cb = table("ch2_cbre_california"); cb[(cb.kind=="chapter_history")&(cb.metric=="under_construction_mw")][["period","value","edition"]].reset_index(drop=True).T"""),
    md("""**Reading.** The California proxies move the opposite way from the national construction series. QCEW employment in data processing and hosting grew 10 percent a year through 2022, then flattened (−0.3 percent a year after 2023 Q1, Chow p < 0.001); establishments show the same pattern and Bai-Perron places their break at 2022 Q3 to 2023 Q1. Silicon Valley's construction pipeline rose from about 44 MW in 2016 to 142 MW by late 2022 and has since sat between 125 and 168 MW with no break at 2023 (Chow p = 0.61), while the national frontier-site series went from nothing to 15 GW. Epoch's inventory has no California site. In short, the post-2022 boom shows up in California only as requests to connect, not as built or staffed capacity, which is consistent with the power constraints Silicon Valley Power and CBRE both describe."""),
    md("""## 4. Every vintage of the CEC energization tiers

Vintages found in the record: December 2024 (PG&E and SCE agreements plus applications, from the 2024 IEPR Update comparison), summer 2025 (seven utilities, totals only; the tier split was shown graphically), December 2025 (seven utilities by tier, methodology memo Table 1 and the Assembly slide), the August 2026 workshop (restates December 2025), and SCE's two public project databases (August 2025 and January 2026), the only utility-level vintages with cancellations. The June 2026 known-load charts in the 2026 IEPR workshop are images without numbers; the monthly snapshot watches docket 26-IEPR-03 for the next vintage."""),
    code("""tv = table("ch2_tier_vintages"); tv.pivot_table(index=["vintage","label"], columns="tier", values="mw", aggfunc="sum").fillna(0).round(0)"""),
    code("""show("fig2_04_tier_vintages")"""),
    code("""table("ch2_cec_forecast_reference_points")"""),
    md("""**Reading.** Requests grew from 6,771 MW (December 2024, two utilities, no inquiries) to 21,756 MW (summer 2025) and 23,277 MW (December 2025): 5,086 MW signed, 9,587 MW in application, 8,604 MW in inquiry. The sum is 45 percent of CAISO's record peak of 52,061 MW and 23 times the roughly 1,000 MW of existing data center peak demand the CEC reports, or 10 to 29 times the chapter 1 range of existing average load. SCE's public database shows what happens inside a vintage: between August 2025 and January 2026 its inquiries fell from 5,934 MW to 1,772 MW as 3,100 MW moved into applications, and canceled requests rose from 709 MW to 3,137 MW, so 38 percent of everything SCE had ever logged was canceled within five months."""),
    md("""## 5. RQ1: the pipeline by stage against the grid, existing load and the adopted forecast"""),
    code("""rq = table("ch2_rq1_table"); rq.round(1)"""),
    code("""den = json.loads((PROCESSED / "ch2_rq1_denominators.json").read_text()); {k: round(v, 1) for k, v in den.items()}"""),
    code("""table("ch2_ced2025_planning_totals")[["metric","scope","y2025","y2030","y2040"]].round(0)"""),
    md("""**Answer to RQ1.** By stage, California's planned data center capacity is 5,086 MW signed, 9,587 MW in application and 8,604 MW in inquiry, 23,277 MW in total (December 2025). That total is 45 percent of CAISO's all-time peak and 53 percent of the 2025 peak; 23 times the state's existing data center peak demand; and 5.8 times the growth in CAISO's managed net peak that the adopted 2025 IEPR planning forecast projects between 2025 and 2030 (4,019 MW). Even at the CEC's 67 percent utilization the pipeline is 3.9 times that growth, and its energy equivalent (about 120 TWh a year) is 3.4 times the statewide energy growth the forecast expects over the same period. The CEC's own forecast already embeds part of this: its data center component at the CAISO peak rises from 96 MW in 2025 to 1,743 MW in 2030 in the planning scenario (4,377 MW in the local-reliability scenario), and its data-center-only deliveries reach 12.1 TWh in 2030, about a third of projected statewide energy growth. The gap between requests and forecast is the object of the rest of the study."""),
]
nb = nbf.v4.new_notebook(); nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "capstone (.venv)", "language": "python", "name": "capstone"}, "language_info": {"name": "python"}}
nbf.write(nb, NB); print("wrote", NB)
if "--execute" in sys.argv:
    subprocess.run([str(ROOT / ".venv/bin/jupyter"), "nbconvert", "--to", "notebook", "--execute", "--inplace", "--ExecutePreprocessor.timeout=1200", str(NB)], check=True, cwd=ROOT)
    print("executed")
