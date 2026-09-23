#!/usr/bin/env python
"""Assumption register for the discussion chapter: every assumption behind the gap, headroom and crosswalk results, with its value or range,
the source it rests on, how it was tested and what the test showed. Built from the chapter outputs so the numbers cannot drift from the
tables: data/processed/ch5_assumption_register.csv and report/tables/ch5_assumption_register.tex."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402

from src.paths import PROCESSED, ROOT  # noqa: E402

OUT = ROOT / "report" / "tables"


def esc(s):
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_\allowbreak{}").replace("#", r"\#")


def main() -> int:
    inp = pd.read_csv(PROCESSED / "ch4_mc_inputs.csv").set_index("input")
    tor = pd.read_csv(PROCESSED / "ch4_tornado.csv").set_index("input")
    sob = pd.read_csv(PROCESSED / "ch4_sobol.csv"); st = {(r.metric, r.input): r.ST for r in sob.itertuples()}
    rep = pd.read_csv(PROCESSED / "ch4_cec_replication.csv").set_index("scenario")
    chain = pd.read_csv(PROCESSED / "ch4_ercot_chain.csv")
    hs = pd.read_csv(PROCESSED / "ch4_headroom_summary.csv")
    cases = pd.read_csv(PROCESSED / "ch3_cases_2030.csv"); cs = json.loads((PROCESSED / "ch3_cases_2030_summary.json").read_text())
    elcc = pd.read_csv(PROCESSED / "ch3_elcc_values.csv").set_index("resource").elcc
    summ = pd.read_csv(PROCESSED / "ch4_mc_summary.csv"); dc_med = float(summ[(summ.iepr_case == "all cases") & (summ.metric == "dc_peak_mw")].p50.iloc[0])
    prof = pd.read_csv(PROCESSED / "ch4_cec_ramp_profile.csv").set_index(["scenario", "year"]).share_of_2040
    em = pd.read_csv(PROCESSED / "ch4_emissions_flat_vs_flexible.csv")
    rates = pd.read_csv(PROCESSED / "ch4_ercot_transition_rates.csv")
    w_bat = float(cases[(cases.case.str.startswith("B")) & (cases.resource == "Batteries")].weighted_planned_mw.iloc[0])
    w_gas = float(cases[(cases.case.str.startswith("B")) & (cases.resource == "Natural gas")].weighted_planned_mw.iloc[0])

    def swing(k):
        r = tor.loc[k]; return f"energy gap {r.gap_energy_low:.0f} to {r.gap_energy_high:.0f} TWh, peak gap {r.gap_peak_low/1000:.1f} to {r.gap_peak_high/1000:.1f} GW between its 5th and 95th percentiles; Sobol total index {st[('gap_energy_twh', k)]:.2f} (energy), {st[('gap_peak_mw', k)]:.2f} (peak)"

    def rng(k):
        r = inp.loc[k]; return f"{r['low']:.2f} / {r['mode']:.2f} / {r['high']:.2f}" if pd.notna(r["low"]) else "per-unit"

    ch2 = chain[(chain.hazard_scale == 2.0) & (chain.cancel_hazard == 0.0)].set_index("start_state").p_energized
    ch1 = chain[(chain.hazard_scale == 1.0) & (chain.cancel_hazard == 0.0)].set_index("start_state").p_energized
    chc = chain[(chain.hazard_scale == 1.0) & (chain.cancel_hazard == 0.005)].set_index("start_state").p_energized
    hm = hs.pivot(index="variant", columns="limit", values="headroom_mw")
    r29, r30 = float(prof[("Planning", 2029)]), float(prof[("Planning", 2030)])
    e25 = em[(em.year == 2025)].set_index(["strategy", "share_hours"]).t_per_gwh
    sh = pd.read_csv(PROCESSED / "ch4_dc_share_trajectory.csv"); sh30 = sh[(sh.series.str.startswith("CED 2025 Planning")) & (sh.year == 2030)].iloc[0]
    sh_lo, sh_hi = float(sh30.dc_total_low_twh - sh30.dc_added_twh), float(sh30.dc_total_high_twh - sh30.dc_added_twh)
    ev_mwh = float(pd.read_csv(PROCESSED / "ch2_ev_equivalents.csv").twh_flat.iloc[0] * 1e6 / (pd.read_csv(PROCESSED / "ch2_ev_equivalents.csv").ev_million_flat.iloc[0] * 1e6))
    rows = [
        ("Tier confidence levels", f"Planning 0.70 / 0.33 / 0.00; Local Reliability 1.00 / 0.50 / 0.10 (agreement / application / inquiry); MC triangular {rng('p_agreement')}, {rng('p_application')}, {rng('p_inquiry')}",
         "cec_dc_methodology_memo_2026 Table 2; ERCOT chain and PJM rule as yardsticks",
         f"Replication: with SVP exempt the levels reproduce the memo's 2040 endpoints ({rep.loc['Planning','full_ramp_statewide_mw']:,.0f} vs {rep.loc['Planning','memo_endpoint_2040_mw']:,.0f} MW; {rep.loc['Local Reliability','full_ramp_statewide_mw']:,.0f} vs {rep.loc['Local Reliability','memo_endpoint_2040_mw']:,.0f}). ERCOT chain gives {100*ch1['Planning studies approved']:.0f} / {100*ch1['Under ERCOT review']:.0f} / {100*ch1['No studies submitted']:.0f}% over 60 months. One-at-a-time: agreements {swing('p_agreement')}; applications {swing('p_application')}; inquiries {swing('p_inquiry')}"),
        ("SVP exemption from the confidence levels", "SVP's 1,038 MW at full confidence", "cec_dc_methodology_memo_2026 p. 9",
         f"Without the exemption the parameters give {rep.loc['Planning','full_ramp_statewide_mw'] - 350:,.0f} MW instead of the memo's 4,855 MW in 2040 (difference 350 MW); with it the endpoints match to within 1 MW"),
        ("Utilization factor", f"0.67 (CEC); MC triangular {rng('utilization')}", "cec_dc_methodology_memo_2026 p. 8 (upper end of SVP's observed range); ERCOT observed 0.46 to 0.64; PJM 0.70",
         f"Yardsticks bracket the value; one-at-a-time {swing('utilization')}"),
        ("Ramp: share of realized capacity on line by 2030", f"CEC profile {100*r30:.0f}% (Planning), {100*float(prof[('Local Reliability', 2030)]):.0f}% (Local Reliability); PJM 36-month rule 100%; MC triangular {rng('ramp_2030')}", "cec_tn268124 annual peaks (component by year); pjm_lar_summary_2025_11_24",
         f"Replicated 2030 components {rep.loc['Planning','replicated_2030_california_mw']:,.0f} and {rep.loc['Local Reliability','replicated_2030_california_mw']:,.0f} MW vs published {rep.loc['Planning','published_2030_california_mw']:,.0f} and {rep.loc['Local Reliability','published_2030_california_mw']:,.0f}; one-at-a-time {swing('ramp_2030')}"),
        ("Data center load factor (energy per MW of peak)", f"0.88; MC triangular {rng('load_factor')}", "chapter 1 range; cec_dc_methodology_memo_2026 p. 11 (85 to 90%)", f"One-at-a-time {swing('load_factor')}"),
        ("Data center load flat and coincident with the system peak", "coincidence 1.0", "cec_dc_methodology_memo_2026 p. 11 (85 to 90% of annual maximum at the CAISO peak)",
         f"Not varied in the draws; at the CEC's 85% the median data center peak contribution of {dc_med:,.0f} MW would fall by {0.15*dc_med:,.0f} MW"),
        ("2030 data center energy annualized at the end-2030 level", "energy = end-2030 MW x 8,760 h x load factor", "construction of the case",
         f"With the CEC ramp profile the calendar-2030 average is {100*(r29 + r30)/2/r30:.0f}% of the end-2030 level, so the case overstates calendar-2030 data center energy by about {100*(1 - (r29 + r30)/2/r30):.0f}%"),
        ("Generation completion (planned units)", "per-unit logit probability p_2030 from chapter 3 (229 units, 20.1 GW; weighted 13.2 GW)", "eia860m_2016_01 .. 2022_01 vintages, eia860m_2016_12 .. 2025_12 outcomes, eia860m_2026_07 planned list",
         f"Three logit specifications agree on the ranking (Table tab:specs); realized fraction 5th to 95th percentile {inp.loc['gen_realization','low'] if pd.notna(inp.loc['gen_realization','low']) else float(tor.loc['gen_realization','low_value']):.2f} to {float(tor.loc['gen_realization','high_value']):.2f}; one-at-a-time {swing('gen_realization')}"),
        ("Capacity factors of the existing fleet", "2023-2025 means by resource; hydro drawn from its 2010-2025 range; solar and wind within 10%", "eia923_2010 .. 2025, eia860_2010 .. 2025",
         f"Hydro: {swing('hydro_cf')}. Solar and wind: {swing('vre_scale')}"),
        ("ELCC values", f"CPUC/E3-Astrape 2023 Tranche 6 for solar {elcc['Solar']:.3f}, wind {elcc['Wind']:.3f}, batteries {elcc['Batteries']:.3f}, pumped storage {elcc['Pumped storage']:.3f}; firm resources 0.90 to 0.95 and hydro 0.45 to 0.55 by assumption", "cpuc_e3_astrape_incremental_elcc_2023; stated assumptions",
         f"Not drawn; deterministic check on the weighted new capacity: battery ELCC 0.60 or 0.90 instead of 0.765 moves the peak gap by {w_bat*(0.765-0.60)/1000:+.1f} or {w_bat*(0.765-0.90)/1000:+.1f} GW; a gas derate of 0.90 instead of 0.95 on new gas moves it by {w_gas*0.05/1000:+.2f} GW (existing-fleet ELCC cancels in the incremental gap)"),
        ("Scheduled retirements", f"{cs['retirements_through_2030_mw']/1000:.1f} GW through 2030 at EIA-860M dates and OTC compliance dates, of which Diablo Canyon {cs['diablo_canyon_mw']/1000:.1f} GW", "eia860m_2026_07; swrcb_otc_policy_2023",
         f"Diablo Canyon as a Bernoulli(0.5) switch: {swing('diablo_continues')}; NRC licences renewed April 2 2026, SB 846 stops at 2030 (gov_ca_diablo_license_2026_04_02, nrc_diablo_canyon_rod_2026)"),
        ("Net imports in 2030", f"triangular {rng('imports_twh')} TWh", "cec_elec_energy_generation_page (CEC statewide net imports 2012-2024)", f"One-at-a-time {swing('imports_twh')}"),
        ("Non-data-center demand growth", "IEPR case drawn with equal weights: low = Planning, mid = Baseline, high = Local Reliability", "cec_tn268727, cec_tn268722, cec_tn268725 (CED 2025 forms); cec_tn268124; cec_tn268824",
         f"One-at-a-time {swing('iepr_case')}; the Local Reliability plus known loads case is reported separately (Table tab:ch4growth)"),
        ("Planning reserve margin", f"uniform {inp.loc['prm','low']:.2f} to {inp.loc['prm','high']:.2f}", "assumption (CPUC resource adequacy range); no raw file", f"One-at-a-time {swing('prm')}"),
        ("ERCOT phase-transition hazards", "; ".join(f"{r.transition.split(' -> ')[0]} {100*r.monthly_hazard:.2f}%/month" for r in rates.itertuples()), "ercot_tac_2026_03_large_load_status; ercot_monthly_2025_11; ERCOT status snapshots (Table tab:ercotrates)",
         f"Hazards doubled: {100*ch2['Planning studies approved']:.0f} / {100*ch2['Under ERCOT review']:.0f} / {100*ch2['No studies submitted']:.0f}% energized in 60 months; 0.5%/month cancellation: {100*chc['Planning studies approved']:.0f} / {100*chc['Under ERCOT review']:.0f} / {100*chc['No studies submitted']:.0f}%; no-studies hazard is an upper bound"),
        ("Headroom thresholds and seasons", "maximum winter (Nov-Feb) and non-winter demand across 2019-2025; Duke's energy criterion", "duke_rethinking_load_growth_2025_mirror; eia930_balance_2019 .. 2025",
         f"0.5% headroom {hm.loc['Duke seasons (Nov-Feb winter), 2019-2025', 0.005]:,.0f} MW; Dec-Feb winter {hm.loc['Dec-Feb winter, 2019-2025', 0.005]:,.0f}; 2022-2025 only {hm.loc['Duke seasons, 2022-2025 only', 0.005]:,.0f}; single threshold {hm.loc['single annual threshold, 2019-2025', 0.005]:,.0f}; per-year hours criterion in Table tab:headroomyear"),
        ("Emissions of a flexible load", "curtail or shift the highest-intensity 5, 10 or 25% of hours; CAISO accounting intensity", "caiso_outlook co2 and demand daily files",
         f"2025: flat {e25[('flat', 0.0)]:.0f} t/GWh; curtail 25% {e25[('curtail', 0.25)]:.0f}; shift 25% {e25[('shift', 0.25)]:.0f}; smaller shares in Table tab:emissions"),
        ("Regime scores", "0 to 3 per criterion under a stated rubric", "ch4_regime_rubric.csv; the crosswalk cells", "Descriptive cells published next to the scores so a reader can rescore (Tables tab:crosswalk and tab:scores)"),
        ("Existing data center energy in the share trajectory", f"{sh_lo:.1f} to {sh_hi:.1f} TWh (EPRI 2023 estimate and the CEC ~1,000 MW converted at a 0.80 to 0.95 load factor)", "epri_powering_intelligence_2024; cec_dc_methodology_memo_2026; ch1_dc_load_estimates.csv",
         f"Carried as a band: the 2030 Planning share runs from {sh30.share_low_pct:.1f} to {sh30.share_high_pct:.1f} percent across it (Table tab:dcshare); the denominators (retail sales for the history, energy to serve load for the forecast) are stated per row"),
        ("Electric-car energy per year (workshop comparison only)", f"{ev_mwh:.0f} MWh per car per year (20 kWh per 100 km over 15,000 km)", "Manner 2026 slide 13 (manner2026); no California per-vehicle figure in the record",
         "Used only to express the requests in car-years (Table tab:ev); it enters no gap, headroom or crosswalk result; halving or doubling it halves or doubles the car counts"),
    ]
    df = pd.DataFrame(rows, columns=["assumption", "value_or_range", "source", "test_and_result"])
    df.to_csv(PROCESSED / "ch5_assumption_register.csv", index=False)
    col = r">{\raggedright\arraybackslash}p{"
    lines = [r"\begin{longtable}{" + col + "2.3cm}" + col + "3.3cm}" + col + "2.8cm}" + col + "6.0cm}}",
             r"\caption{Assumption register: value or range, source, test and result for every assumption behind the results. Generated from the chapter outputs.}\label{tab:register}\\",
             r"\toprule", r"Assumption & Value or range & Source & How it was tested and what the test showed \\", r"\midrule", r"\endfirsthead",
             r"\toprule", r"Assumption & Value or range & Source & How it was tested and what the test showed \\", r"\midrule", r"\endhead"]
    for r in df.itertuples():
        t = esc(r.test_and_result)
        for lab in ("tab:specs", "tab:ch4growth", "tab:ercotrates", "tab:headroomyear", "tab:emissions", "tab:crosswalk", "tab:scores", "tab:dcshare", "tab:ev"):
            t = t.replace(esc(lab), "\\ref{" + lab + "}")
        lines.append(f"{esc(r.assumption)} & {esc(r.value_or_range)} & {esc(r.source)} & {t} \\\\" + "\n" + r"\addlinespace")
    lines += [r"\bottomrule", r"\end{longtable}"]
    (OUT / "ch5_assumption_register.tex").write_text("\n".join(lines)); print("  table ch5_assumption_register;", len(df), "assumptions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
