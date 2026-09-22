#!/usr/bin/env python
"""Render chapter 4 LaTeX tables (report/tables/ch4_*.tex) from the processed CSV/JSON outputs."""
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
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#").replace("->", r"$\rightarrow$")


def write(name, lines):
    (OUT / f"{name}.tex").write_text("\n".join(lines)); print("  table", name)


def tab(cols, header, rows, name):
    write(name, [r"\begin{tabular}{" + cols + "}", r"\toprule", header + r" \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])


def main() -> int:
    # 1. tiers and IEPR growth
    t = pd.read_csv(PROCESSED / "ch4_ca_tiers.csv")
    rows = [f"{esc(r.tier)} & {r.mw_all_reporting:,.0f} & {r.mw_excluded_nevada:,.0f} & {r.mw_california:,.0f} \\\\" for r in t.itertuples()]
    rows.append(r"\midrule" + f"\nTotal & {t.mw_all_reporting.sum():,.0f} & {t.mw_excluded_nevada.sum():,.0f} & {t.mw_california.sum():,.0f} \\\\")
    tab("lrrr", "Tier (December 2025) & All reporting utilities (MW) & VEA, Nevada (MW) & California (MW)", rows, "ch4_tiers")
    g = pd.read_csv(PROCESSED / "ch4_iepr_growth_summary.csv")
    rows = [f"{esc(r.case)} & {esc(r.scenario)} & {r.energy_non_dc_2025_GWh/1000:.1f} & {r.energy_non_dc_2030_GWh/1000:.1f} & {r.energy_non_dc_growth_GWh/1000:.1f} & {r.peak_non_dc_2025_MW:,.0f} & {r.peak_non_dc_2030_MW:,.0f} & {r.peak_non_dc_growth_MW:,.0f} & {r.cec_dc_peak_2030_MW:,.0f} & {r.cec_dc_energy_2030_GWh/1000:.1f} \\\\" for r in g.itertuples()]
    tab("llrrrrrrrr", "Case & CED 2025 scenario & Energy 2025 (TWh) & Energy 2030 & Growth & Peak 2025 (MW) & Peak 2030 & Growth & CEC DC peak 2030 (MW) & CEC DC energy 2030 (TWh)", rows, "ch4_growth")
    # 2. ERCOT rates and chain
    r_ = pd.read_csv(PROCESSED / "ch4_ercot_transition_rates.csv")
    rows = [f"{esc(r.transition)} & {r.flow_mw:,.0f} & {r.months:.1f} & {r.pool_mw:,.0f} & {100*r.monthly_hazard:.2f} & {100*r.annual_probability:.1f} & {esc(r.window)} \\\\" for r in r_.itertuples()]
    tab("lrrrrrl", "Transition & Flow (MW) & Months & Pool (MW) & Monthly hazard (\\%) & Annual (\\%) & Window", rows, "ch4_ercot_rates")
    c = pd.read_csv(PROCESSED / "ch4_ercot_chain.csv")
    piv = c.pivot_table(index="start_state", columns=["hazard_scale", "cancel_hazard"], values="p_energized")
    piv = piv.reindex(["No studies submitted", "Under ERCOT review", "Planning studies approved", "Approved to energize"])
    hdr = "Start phase (California tier) & " + " & ".join(f"{sc:g}x, cancel {100*ch:g}\\%" for sc, ch in piv.columns)
    names = {"No studies submitted": "No studies submitted (inquiry)", "Under ERCOT review": "Under ERCOT review (application)", "Planning studies approved": "Planning studies approved (signed agreement)", "Approved to energize": "Approved to energize"}
    rows = [f"{esc(names[i])} & " + " & ".join(f"{100*v:.1f}" for v in piv.loc[i]) + r" \\" for i in piv.index]
    tab("l" + "r" * len(piv.columns), hdr, rows, "ch4_ercot_chain")
    # 3. demand cases
    d = pd.read_csv(PROCESSED / "ch4_demand_cases_2030.csv")
    def f(v, fmt):
        return "--" if pd.isna(v) else format(v, fmt)
    rows = [f"{esc(r.case)} & {f(r.p_agreement, '.2f')} & {f(r.p_application, '.2f')} & {f(r.p_inquiry, '.2f')} & {f(r.utilization, '.2f')} & {f(r.ramp_agreement, '.2f')} & {f(r.ramp_application, '.2f')} & {f(r.load_factor, '.2f')} & {r.dc_peak_mw_2030:,.0f} & {r.dc_energy_twh_2030:.1f} \\\\" for r in d.itertuples()]
    tab("lrrrrrrrrr", "Case & P(agreement) & P(application) & P(inquiry) & Utilization & Ramp agr. & Ramp app./inq. & Load factor & Peak 2030 (MW) & Energy 2030 (TWh)", rows, "ch4_demand_cases")
    rp = pd.read_csv(PROCESSED / "ch4_cec_replication.csv")
    rows = [f"{esc(r.scenario)} & {r.full_ramp_statewide_mw:,.0f} & {r.memo_endpoint_2040_mw:,.0f} & {r.full_ramp_california_mw:,.0f} & {r.effective_p_agreement:.2f} / {r.effective_p_application:.2f} / {r.effective_p_inquiry:.2f} & {100*r.ramp_share_2030:.0f} & {r.replicated_2030_california_mw:,.0f} & {r.published_2030_caiso_mw:,.0f} & {r.published_2030_vea_mw:,.0f} & {r.published_2030_california_mw:,.0f} \\\\" for r in rp.itertuples()]
    tab("lrrrrrrrrr", "Scenario & Full-ramp statewide (MW) & Memo 2040 endpoint & Full-ramp California & Effective P (agr. / app. / inq.) & CEC ramp share 2030 (\\%) & Replicated 2030 California (MW) & Published CAISO 2030 & of which VEA & Published California 2030", rows, "ch4_cec_replication")
    pr = pd.read_csv(PROCESSED / "ch4_cec_ramp_profile.csv"); yrs_p = [2025, 2026, 2027, 2028, 2029, 2030, 2032, 2035, 2040]
    rows = []
    for scen in ("Planning", "Local Reliability"):
        sub = pr[pr.scenario == scen].set_index("year")
        rows.append(f"{scen}: CAISO data center component (MW) & " + " & ".join(f"{sub.loc[y, 'caiso_data_center_mw']:,.0f}" for y in yrs_p) + r" \\")
        rows.append(f"{scen}: share of 2040 (\\%) & " + " & ".join(f"{100*sub.loc[y, 'share_of_2040']:.0f}" for y in yrs_p) + r" \\")
    tab("l" + "r" * len(yrs_p), "CEC ramp profile & " + " & ".join(str(y) for y in yrs_p), rows, "ch4_cec_ramp")
    tt = pd.read_csv(PROCESSED / "ch4_demand_totals_2030.csv")
    keep = ["Upper bound: every MW builds, flat load", "Upper bound at CEC utilization", "CEC central (Planning forecast, published)", "CEC high (Local Reliability, published)", "ERCOT-calibrated stock-flow", "PJM-style: firm only (signed agreements)"]
    rows = []
    for c in keep:
        for r in tt[tt.demand_case == c].itertuples():
            rows.append(f"{esc(c)} & {esc(r.iepr_case)} & {r.non_dc_peak_2030_MW:,.0f} & {r.dc_peak_MW:,.0f} & {r.total_peak_2030_MW:,.0f} & {r.peak_growth_2025_2030_MW:,.0f} & {r.non_dc_energy_2030_TWh:.1f} & {r.dc_energy_TWh:.1f} & {r.total_energy_2030_TWh:.1f} & {r.energy_growth_2025_2030_TWh:.1f} \\\\")
        rows.append(r"\addlinespace")
    tab("llrrrrrrrr", "Demand case & IEPR case & Non-DC peak 2030 (MW) & DC peak & Total peak & Growth from 2025 & Non-DC energy 2030 (TWh) & DC energy & Total energy & Growth from 2025", rows[:-1], "ch4_demand_totals")
    # 4. Monte Carlo inputs and summary
    i = pd.read_csv(PROCESSED / "ch4_mc_inputs.csv")
    rows = [f"{esc(r.input)} & {esc(r.distribution)} & {f(r.low, '.2f')} & {f(r.mode, '.2f')} & {f(r.high, '.2f')} & {esc(r.basis)} \\\\" for r in i.itertuples()]
    write("ch4_mc_inputs", [r"\begin{tabular}{llrrrp{7.2cm}}", r"\toprule", r"Input & Distribution & Low & Mode & High & Basis \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])
    s = pd.read_csv(PROCESSED / "ch4_mc_summary.csv"); ub = pd.read_csv(PROCESSED / "ch4_upper_bound_2030.csv")
    lab = {"gap_energy_twh": "Energy gap (TWh)", "gap_peak_mw": "Net-peak gap (MW)", "dc_peak_mw": "Data center peak (MW)", "dc_energy_twh": "Data center energy (TWh)", "abs_energy_balance_twh": "Absolute energy balance (TWh)", "abs_peak_balance_mw": "Absolute peak balance (MW)"}
    rows = []
    for metric in ["gap_energy_twh", "gap_peak_mw", "dc_peak_mw", "dc_energy_twh"]:
        fmt = ",.0f" if "mw" in metric else ".1f"
        for case in ["all cases", "low", "mid", "high"]:
            r = s[(s.metric == metric) & (s.iepr_case == case)].iloc[0]
            rows.append(f"{lab[metric]} & {esc(case)} & {format(r['mean'], fmt)} & {format(r['p05'], fmt)} & {format(r['p25'], fmt)} & {format(r['p50'], fmt)} & {format(r['p75'], fmt)} & {format(r['p95'], fmt)} & {100*r['share_positive']:.0f} \\\\")
        ubm = {"gap_energy_twh": ub.gap_energy_twh, "gap_peak_mw": ub.gap_peak_mw, "dc_peak_mw": ub.dc_peak_mw, "dc_energy_twh": ub.dc_energy_twh}[metric]
        rows.append(f"\\quad upper bound (every MW builds, flat) & low to high, Diablo on or off & {format(ubm.mean(), fmt)} & {format(ubm.min(), fmt)} & -- & -- & -- & {format(ubm.max(), fmt)} & 100 \\\\")
        rows.append(r"\midrule")
    rows = rows[:-1]
    tab("llrrrrrrr", "Metric & IEPR case & Mean & P5 & P25 & P50 & P75 & P95 & Share $>0$ (\\%)", rows, "ch4_mc_summary")
    # 5. tornado and Sobol
    t_ = pd.read_csv(PROCESSED / "ch4_tornado.csv")
    rows = [f"{esc(r.input)} & {r.low_value:.3g} & {r.high_value:.3g} & {r.gap_energy_low:.0f} & {r.gap_energy_high:.0f} & {r.swing_energy:.0f} & {r.gap_peak_low:,.0f} & {r.gap_peak_high:,.0f} & {r.swing_peak:,.0f} \\\\" for r in t_.itertuples()]
    rows.append(r"\midrule" + f"\nbase (all inputs at their medians) & & & {t_.base_gap_energy.iloc[0]:.0f} & & & {t_.base_gap_peak.iloc[0]:,.0f} & & \\\\")
    rows.append(f"upper bound (every MW builds, flat; deterministic) & & & {ub.gap_energy_twh.min():.0f} & {ub.gap_energy_twh.max():.0f} & & {ub.gap_peak_mw.min():,.0f} & {ub.gap_peak_mw.max():,.0f} & \\\\")
    tab("lrrrrrrrr", "Input & Low & High & Energy gap at low (TWh) & at high & Swing & Peak gap at low (MW) & at high & Swing", rows, "ch4_tornado")
    so = pd.read_csv(PROCESSED / "ch4_sobol.csv"); pv = so.pivot(index="input", columns="metric", values=["S1", "S1_conf", "ST", "ST_conf"]).sort_values(("ST", "gap_energy_twh"), ascending=False)
    rows = [f"{esc(i)} & {pv.loc[i, ('S1', 'gap_energy_twh')]:.3f} & {pv.loc[i, ('S1_conf', 'gap_energy_twh')]:.3f} & {pv.loc[i, ('ST', 'gap_energy_twh')]:.3f} & {pv.loc[i, ('S1', 'gap_peak_mw')]:.3f} & {pv.loc[i, ('S1_conf', 'gap_peak_mw')]:.3f} & {pv.loc[i, ('ST', 'gap_peak_mw')]:.3f} \\\\" for i in pv.index]
    tab("lrrrrrr", "Input & S1 energy & $\\pm$ & ST energy & S1 peak & $\\pm$ & ST peak", rows, "ch4_sobol")
    # 6. headroom
    hs = pd.read_csv(PROCESSED / "ch4_headroom_summary.csv"); hd = pd.read_csv(PROCESSED / "ch4_headroom_detail.csv")
    piv = hs.pivot(index="variant", columns="limit", values="headroom_mw")
    order = ["Duke seasons (Nov-Feb winter), 2019-2025", "Dec-Feb winter, 2019-2025", "Duke seasons, 2022-2025 only", "single annual threshold, 2019-2025"]
    rows = [f"{esc(v)} & " + " & ".join("--" if pd.isna(piv.loc[v, l]) else f"{piv.loc[v, l]:,.0f}" for l in piv.columns) + r" \\" for v in order]
    rows.append(f"Duke (2016-2024, EIA-930 CISO) & " + " & ".join(f"{hs[hs.limit == l].duke_caiso_gw.iloc[0]*1000:,.0f}" if pd.notna(hs[hs.limit == l].duke_caiso_gw.iloc[0]) else "--" for l in piv.columns) + r" \\")
    tab("lrrrr", "Variant & " + " & ".join(f"{100*l:g}\\%" for l in piv.columns), rows, "ch4_headroom")
    m = hd[hd.variant == order[0]].groupby("limit")[["hours_curtailed", "share_winter", "hours_below_90pct", "hours_below_75pct", "hours_below_50pct", "max_curtailment_mw"]].mean()
    rows = [f"{100*l:g} & {hs[(hs.variant == order[0]) & (hs.limit == l)].headroom_mw.iloc[0]:,.0f} & {r.hours_curtailed:.0f} & {100*r.share_winter:.0f} & {r.hours_below_90pct:.0f} & {r.hours_below_75pct:.0f} & {r.hours_below_50pct:.0f} & {r.max_curtailment_mw:,.0f} \\\\" for l, r in m.iterrows()]
    tab("rrrrrrrr", "Limit (\\%) & Headroom (MW) & Hours curtailed per year & Share in Nov-Feb (\\%) & Hours below 90\\% available & below 75\\% & below 50\\% & Largest hourly cut (MW)", rows, "ch4_headroom_detail")
    hy = pd.read_csv(PROCESSED / "ch4_headroom_by_year.csv")
    for variant, name in (("Duke seasons (Nov-Feb winter)", "ch4_headroom_by_year"), ("single historical peak", "ch4_headroom_by_year_single")):
        sub = hy[hy.variant == variant]
        lims = [0.0025, 0.005, 0.01, 0.05]
        rows = []
        for y in sorted(sub.year.unique()):
            r = sub[sub.year == y].set_index("limit")
            rows.append(f"{int(y)} & " + " & ".join(f"{r.loc[l, 'headroom_hours_criterion_mw']:,.0f}" for l in lims) + " & " + " & ".join(f"{r.loc[l, 'headroom_energy_criterion_mw']:,.0f}" for l in lims) + r" \\")
        mn = sub.groupby("limit")[["headroom_hours_criterion_mw", "headroom_energy_criterion_mw"]].agg(["min", "max"])
        rows.append(r"\midrule" + "\nrange & " + " & ".join(f"{mn.loc[l, ('headroom_hours_criterion_mw', 'min')]:,.0f}--{mn.loc[l, ('headroom_hours_criterion_mw', 'max')]:,.0f}" for l in lims) + " & " + " & ".join(f"{mn.loc[l, ('headroom_energy_criterion_mw', 'min')]:,.0f}--{mn.loc[l, ('headroom_energy_criterion_mw', 'max')]:,.0f}" for l in lims) + r" \\")
        tab("lrrrrrrrr", "Year & \\multicolumn{4}{c}{Hours above the peak under 0.25 / 0.5 / 1 / 5\\% of the year (MW)} & \\multicolumn{4}{c}{Curtailed energy under 0.25 / 0.5 / 1 / 5\\% (Duke, MW)}", rows, name)
    hv = pd.read_csv(PROCESSED / "ch4_headroom_vs_gap.csv")
    rows = [f"{100*r.limit:g} & {r.headroom_mw:,.0f} & {100*r.share_of_dc_cec_central:.0f} & {100*r.share_of_dc_ercot:.0f} & {100*r.share_of_dc_pjm_firm:.0f} & {100*r.share_of_dc_cec_high:.0f} & {100*r.share_of_dc_upper_bound:.0f} & {100*r.share_of_peak_gap_p50:.0f} & {100*r.share_of_peak_gap_p95:.0f} & {100*r.share_of_upper_bound_peak_gap:.0f} \\\\" for r in hv.itertuples()]
    tab("rrrrrrrrrr", "Limit (\\%) & Headroom (MW) & of CEC central DC (\\%) & of ERCOT-calibrated & of PJM firm & of CEC high & of upper-bound DC & of peak gap P50 & of peak gap P95 & of upper-bound peak gap", rows, "ch4_headroom_vs_gap")
    es = pd.read_csv(PROCESSED / "ch4_energy_side.csv")
    rows = [f"{esc(r.item)} & {r.value:,.0f} & {esc(r.unit)} & {'--' if pd.isna(r.midday_share_pct) else format(r.midday_share_pct, '.0f')} & {'--' if pd.isna(r.flexible_1gw_energy_gwh) else format(r.flexible_1gw_energy_gwh, ',.0f')} & {esc(r.source)} \\\\" for r in es.itertuples()]
    tab("lrrrrl", "Item & Value & Unit & Share in 10--16 h (\\%) & Energy a 1 GW flexible load could absorb (GWh) & Source", rows, "ch4_energy_side")
    # 7. regimes
    cw = pd.read_csv(PROCESSED / "ch4_regime_crosswalk.csv")
    cols = ["granularity", "stage_taxonomy", "verification", "timeliness", "coverage", "public_access"]
    rows = [f"\\textbf{{{esc(r.regime)}}} & " + " & ".join(esc(getattr(r, c_)) for c_ in cols) + r" \\" + "\n" + r"\addlinespace" for r in cw.itertuples()]
    write("ch4_crosswalk", [r"\begin{tabular}{p{2.4cm}p{3.1cm}p{3.4cm}p{3.6cm}p{2.6cm}p{2.6cm}p{2.6cm}}", r"\toprule", "Regime & Granularity & Stage taxonomy & Verification & Timeliness & Coverage & Public access \\\\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])
    sc = pd.read_csv(PROCESSED / "ch4_regime_scores.csv"); rb = pd.read_csv(PROCESSED / "ch4_regime_rubric.csv")
    cols_s = ["granularity", "stage_taxonomy", "verification", "timeliness", "coverage", "public_access"]
    rows = [f"{esc(r.regime)} & " + " & ".join(str(int(getattr(r, c_))) for c_ in cols_s) + f" & {int(r.total)} \\\\" for r in sc.itertuples()]
    tab("lrrrrrrr", "Regime & Granularity & Stage taxonomy & Verification & Timeliness & Coverage & Public access & Total (of 18)", rows, "ch4_scores")
    write("ch4_scores_note", [r"\begin{minipage}{\textwidth}\scriptsize Rubric: " + "; ".join(f"\\textit{{{esc(r.criterion.replace('_', ' '))}}}: {esc(r.rubric)}" for r in rb.itertuples()) + r".\end{minipage}"])
    tx = pd.read_csv(PROCESSED / "ch4_common_taxonomy.csv")
    rows = [" & ".join(esc(v) for v in r) + r" \\" + "\n" + r"\addlinespace" for r in tx.itertuples(index=False)]
    write("ch4_taxonomy", [r"\begin{tabular}{p{2.3cm}p{2.6cm}p{2.8cm}p{2.7cm}p{2.3cm}p{3.0cm}p{2.7cm}}", r"\toprule", " & ".join(esc(c_) for c_ in tx.columns) + r" \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])
    hl = pd.read_csv(PROCESSED / "ch4_headline_by_regime.csv")
    rows = [f"{esc(r.counting_rule)} & {'--' if pd.isna(r.california_mw) else format(r.california_mw, ',.0f')} & {esc(r.what_is_counted)} \\\\" for r in hl.itertuples()]
    write("ch4_headline", [r"\begin{tabular}{p{5.2cm}rp{8.6cm}}", r"\toprule", r"Counting rule & California (MW) & What is counted \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])
    sz = pd.read_csv(PROCESSED / "ch4_sce_size_classes.csv")
    rows = [f"{esc(r.size_class)} & {r.projects} & {r.requested_mw:,.0f} & {100*r.share_of_active_mw:.0f} \\\\" for r in sz.itertuples()]
    tab("lrrr", "Size class & Projects & Requested (MW) & Share of active MW (\\%)", rows, "ch4_sce_sizes")
    pj = pd.read_csv(PROCESSED / "ch4_pjm_adjustments.csv"); lar = pd.read_csv(PROCESSED / "ch4_pjm_lar_chart_readings.csv")
    yrs = [2026, 2027, 2028, 2029, 2030, 2035, 2040, 2046]
    rows = []
    for tb in pj.table.unique():
        r = pj[(pj.table == tb) & (pj.zone == "PJM RTO")].set_index("year").mw
        rows.append(f"{esc(tb)} (RTO, Excel table) & " + " & ".join(f"{r[y]:,.0f}" for y in yrs) + r" \\")
    l2 = lar.set_index("year")
    for col, name in (("request_mw", "Requested (LAS chart, Nov 2025, approximate)"), ("firm_mw", "Firm (LAS chart)"), ("non_firm_mw", "Non-firm (LAS chart)")):
        rows.append(f"{name} & " + " & ".join(f"{l2.loc[y, col]:,.0f}" if y in l2.index else "--" for y in yrs) + r" \\")
    tab("l" + "r" * len(yrs), "PJM RTO large load adjustment (MW) & " + " & ".join(str(y) for y in yrs), rows, "ch4_pjm")
    # 8. emissions
    em = pd.read_csv(PROCESSED / "ch4_emissions_flat_vs_flexible.csv"); pv = em.pivot_table(index=["strategy", "share_hours"], columns="year", values="t_per_gwh")
    order = [("flat", 0.0)] + [(s_, sh) for sh in (0.05, 0.10, 0.25) for s_ in ("curtail", "shift")]
    rows = [f"{s_} & {100*sh:.0f} & " + " & ".join(f"{pv.loc[(s_, sh), y]:.0f}" for y in pv.columns) + f" & {100*(1 - pv.loc[(s_, sh), 2025]/pv.loc[('flat', 0.0), 2025]):.0f} \\\\" for s_, sh in order]
    tab("lr" + "r" * len(pv.columns) + "r", "Strategy & Share of hours (\\%) & " + " & ".join(str(int(y)) for y in pv.columns) + " & Change vs flat, 2025 (\\%)", rows, "ch4_emissions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
