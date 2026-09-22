#!/usr/bin/env python
"""Render chapter 2 LaTeX tables (report/tables/ch2_*.tex) from the processed CSV/JSON outputs."""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402

from src.paths import PROCESSED, ROOT  # noqa: E402

OUT = ROOT / "report" / "tables"
OUT.mkdir(exist_ok=True)


def esc(s):
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("->", r"$\rightarrow$")


def write(name, lines):
    (OUT / f"{name}.tex").write_text("\n".join(lines))
    print("  table", name)


def pct(x, d=0):
    return "--" if pd.isna(x) else f"{100*float(x):.{d}f}"


def main() -> int:
    # Bai-Perron on Census
    bp = pd.read_csv(PROCESSED / "ch2_census_bai_perron.csv")
    rows = [f"{int(r.m)} & {esc(r.breaks) if isinstance(r.breaks, str) else '--'} & {r.ssr:.3f} & {r.bic:.3f} & {r.lwz:.3f} & {('--' if pd.isna(r.supF_0_m) else f'{r.supF_0_m:.1f}')} \\\\" for _, r in bp.iterrows()]
    write("ch2_bai_perron", [r"\begin{tabular}{lllrrr}", r"\toprule", r"Breaks $m$ & Break dates (first month of new regime) & SSR & BIC & LWZ & supF(0$|m$) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])

    seg = pd.read_csv(PROCESSED / "ch2_census_segment_growth.csv")
    rows = [f"{r.segment_start} to {r.segment_end} & {int(r.months)} & {pct(r.cagr)} & [{pct(r.cagr_lo95)}, {pct(r.cagr_hi95)}] \\\\" for _, r in seg.iterrows()]
    write("ch2_segment_growth", [r"\begin{tabular}{lrrr}", r"\toprule", r"Segment (BIC partition) & Months & Compound growth (\%/yr) & 95\% interval \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])

    # comparison across series
    comp = pd.read_csv(PROCESSED / "ch2_break_test_comparison.csv")
    rows = []
    for _, r in comp.iterrows():
        if pd.notna(r.get("chow_p", float("nan"))):
            ci = r.get("bp_break1_ci90", "")
            try:
                ci_t = ast.literal_eval(ci) if isinstance(ci, str) and ci.startswith("(") else None
            except Exception:
                ci_t = None
            ci_s = f"{str(ci_t[0])[:7]} to {str(ci_t[1])[:7]}" if ci_t else "--"
            rows.append(f"{esc(r.series)} & {int(r.n)} & {r.chow_F:.1f} & {r.chow_p:.3f} & {r.wald_hac_p:.3f} & {pct(r.cagr_pre)} [{pct(r.cagr_pre_lo)}, {pct(r.cagr_pre_hi)}] & {pct(r.cagr_post)} [{pct(r.cagr_post_lo)}, {pct(r.cagr_post_hi)}] & {str(r.bp_break1)[:7]} & {ci_s} & {esc(str(r.bp_breaks_bic))[:40]} & {r.bp_supF_1_boot_p:.3f} \\\\")
        else:
            rows.append(f"{esc(r.series)} & {int(r.n) if pd.notna(r.get('n', float('nan'))) else 0} & \\multicolumn{{9}}{{l}}{{{esc(str(r.get('note', r.get('error', ''))))[:90]}}} \\\\")
    write("ch2_break_comparison", [r"\begin{tabular}{p{5.6cm}rrrrllllp{3cm}r}", r"\toprule",
                                    r"Series & $n$ & Chow $F$ & $p$ & HAC $p$ & Growth before (\%/yr) & Growth after (\%/yr) & BP break (1) & 90\% interval & BP breaks (BIC) & boot.\ $p$ \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])

    # forecasts
    fa = pd.read_csv(PROCESSED / "ch2_census_forecast_arima.csv", index_col=0, parse_dates=True)
    fe = pd.read_csv(PROCESSED / "ch2_census_forecast_ets.csv", index_col=0, parse_dates=True)
    summ = json.loads((PROCESSED / "ch2_census_break_summary.json").read_text())
    rows = []
    for h in (6, 12, 24):
        a, e = fa.iloc[h - 1], fe.iloc[h - 1]
        rows.append(f"{fa.index[h-1]:%b %Y} & {a['mean']/1000:.1f} & [{a['lo80']/1000:.1f}, {a['hi80']/1000:.1f}] & [{a['lo95']/1000:.1f}, {a['hi95']/1000:.1f}] & {e['mean']/1000:.1f} & [{e['lo80']/1000:.1f}, {e['hi80']/1000:.1f}] & [{e['lo95']/1000:.1f}, {e['hi95']/1000:.1f}] \\\\")
    write("ch2_forecast", [r"\begin{tabular}{lrllrll}", r"\toprule", r" & \multicolumn{3}{c}{ARIMA" + esc(str(tuple(summ['arima']['order']))) + r" with drift} & \multicolumn{3}{c}{ETS(A,Ad,N)} \\",
                           r"Month & Mean & 80\% band & 95\% band & Mean & 80\% band & 95\% band \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}", r"\\[2pt] {\footnotesize Billion dollars per year, seasonally adjusted annual rate.}"])

    # tier vintages
    tv = pd.read_csv(PROCESSED / "ch2_tier_vintages.csv")
    piv = tv[~tv.label.str.contains("SCE database")].groupby(["vintage", "label", "tier"]).mw.sum().unstack("tier").fillna(0)
    rows = []
    for (v, lab), r in piv.iterrows():
        rows.append(f"{esc(lab)} & {r.get('Signed agreement', 0):,.0f} & {r.get('Active application', 0):,.0f} & {r.get('Inquiry', 0):,.0f} & {r.get('Agreements + applications (no inquiries)', 0):,.0f} & {r.get('All tiers', 0) + r.get('Total restated', 0):,.0f} & {r.sum():,.0f} \\\\")
    sce = tv[tv.label.str.contains("SCE database")].groupby(["label", "tier"]).mw.sum().unstack("tier").fillna(0)
    for lab, r in sce.iterrows():
        rows.append(f"{esc(lab)} (SCE only) & {r.get('Signed agreement', 0):,.0f} & {r.get('Active application', 0):,.0f} & {r.get('Inquiry', 0):,.0f} & -- & canceled {r.get('Canceled', 0):,.0f} & {r.get('Signed agreement', 0)+r.get('Active application', 0)+r.get('Inquiry', 0):,.0f} \\\\")
    write("ch2_tier_vintages", [r"\begin{tabular}{p{5.2cm}rrrrrr}", r"\toprule", r"Vintage & Signed & Applications & Inquiries & Agr.+appl. only & Unsplit total & Total active (MW) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])

    # RQ1
    rq = pd.read_csv(PROCESSED / "ch2_rq1_table.csv"); den = json.loads((PROCESSED / "ch2_rq1_denominators.json").read_text())
    rows = [f"{esc(r.stage)} & {r.mw:,.0f} & {r.share_of_caiso_record_peak_pct:.1f} & {r.share_of_caiso_2025_peak_pct:.1f} & {r.multiple_of_existing_dc_peak_1000MW:.1f}x & {esc(r.multiple_of_existing_dc_avg_load_range)}x & {r.share_of_IEPR_planning_managed_net_peak_growth_2025_2030_pct:.0f} & {r.expected_demand_share_of_managed_net_peak_growth_pct:.0f} \\\\" for _, r in rq.iterrows()]
    write("ch2_rq1", [r"\begin{tabular}{lrrrrrrr}", r"\toprule",
                      r"Stage (Dec 2025) & MW & \% of CAISO & \% of 2025 & $\times$ existing & $\times$ existing & \% of IEPR & \% of IEPR growth \\",
                      r" & & record peak & peak & DC peak & DC avg. load & peak growth & at 67\% util. \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])
    write("ch2_rq1_note", [r"\footnotesize Denominators: CAISO record peak " + f"{den['caiso_record_peak_mw']:,.0f}" + r" MW (Sept.\ 6, 2022); 2025 hourly peak " + f"{den['caiso_2025_peak_mw']:,.0f}" + r" MW; existing data center peak $\approx$1,000 MW (CEC); existing average load " + f"{den['existing_dc_avg_load_mw_low']:,.0f}--{den['existing_dc_avg_load_mw_high']:,.0f}" + r" MW (chapter 1 range); IEPR planning-scenario CAISO managed net peak growth 2025--2030 " + f"{den['iepr_planning_caiso_managed_net_peak_2030_mw']-den['iepr_planning_caiso_managed_net_peak_2025_mw']:,.0f}" + r" MW."])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
