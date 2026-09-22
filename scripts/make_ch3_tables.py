#!/usr/bin/env python
"""Render chapter 3 LaTeX tables (report/tables/ch3_*.tex) from the processed CSV/JSON outputs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402

from src.paths import PROCESSED, ROOT  # noqa: E402

OUT = ROOT / "report" / "tables"
OUT.mkdir(exist_ok=True)
GEN_ROWS = ["Natural gas", "Nuclear", "Hydro", "Geothermal", "Biomass", "Wind", "Solar", "Coal and petcoke", "Oil", "Other", "Batteries", "Pumped storage"]
CAP_ROWS = ["Natural gas", "Nuclear", "Large hydro", "Small hydro", "Pumped storage", "Geothermal", "Biomass", "Wind", "Solar", "Batteries", "Coal and petcoke", "Oil", "Other"]


def esc(s):
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def write(name, lines):
    (OUT / f"{name}.tex").write_text("\n".join(lines)); print("  table", name)


def main() -> int:
    years = [2010, 2015, 2020, 2023, 2024, 2025]
    s = pd.read_csv(PROCESSED / "ch3_supply_by_year.csv", index_col=0)
    rows = [f"{esc(r)} & " + " & ".join(f"{s.loc[y, r]/1000:.1f}" if r in s and pd.notna(s.loc[y, r]) else "--" for y in years) + r" \\" for r in GEN_ROWS]
    rows.append(r"\midrule" + "\n" + "Total in-state & " + " & ".join(f"{s.loc[y, 'Total in-state']/1000:.1f}" for y in years) + r" \\")
    rows.append("Net imports, CEC statewide & " + " & ".join(f"{s.loc[y, 'CEC net imports']/1000:.1f}" if pd.notna(s.loc[y, "CEC net imports"]) else "--" for y in years) + r" \\")
    rows.append("Net imports, CAISO only (EIA-930) & " + " & ".join(f"{s.loc[y, 'CAISO net imports (EIA-930, chapter 1)']/1000:.1f}" if pd.notna(s.loc[y, "CAISO net imports (EIA-930, chapter 1)"]) else "--" for y in years) + r" \\")
    write("ch3_generation", [r"\begin{tabular}{l" + "r" * len(years) + "}", r"\toprule", "Resource (TWh) & " + " & ".join(str(y) for y in years) + r" \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])

    c = pd.read_csv(PROCESSED / "ch3_eia860_capacity_by_resource.csv"); cp = c.pivot(index="year", columns="resource", values="nameplate_mw")
    rows = [f"{esc(r)} & " + " & ".join(f"{cp.loc[y, r]/1000:.1f}" if r in cp and pd.notna(cp.loc[y, r]) else "--" for y in years) + r" \\" for r in CAP_ROWS]
    snap = pd.read_csv(PROCESSED / "ch3_capacity_snapshot_2026_07.csv").set_index("resource"); si = json.loads((PROCESSED / "ch3_capacity_snapshot_2026_07.json").read_text())
    rows = [f"{esc(r)} & " + " & ".join(f"{cp.loc[y, r]/1000:.1f}" if r in cp and pd.notna(cp.loc[y, r]) else "--" for y in years) + f" & {snap.nameplate_mw.get(r, 0)/1000:.1f}" + r" \\" for r in CAP_ROWS]
    rows.append(r"\midrule" + "\n" + "Total & " + " & ".join(f"{cp.loc[y, 'Total']/1000:.1f}" for y in years) + f" & {si['total_mw']/1000:.1f}" + r" \\")
    bat = pd.read_csv(PROCESSED / "ch3_battery_capacity.csv").set_index("year")
    rows.append("Battery energy capacity (GWh) & " + " & ".join(f"{bat.loc[y, 'energy_mwh']/1000:.1f}" if y in bat.index else "--" for y in years) + f" & {si['batteries_mwh']/1000:.1f}" + r" \\")
    cur = pd.read_csv(PROCESSED / "ch3_caiso_curtailment_annual.csv").set_index("year")
    rows.append("CAISO wind and solar curtailment (TWh) & " + " & ".join(f"{cur.loc[y, 'curtailed_gwh']/1000:.2f}" if y in cur.index and cur.loc[y, "months"] == 12 else "--" for y in years) + f" & {cur.loc[2026, 'curtailed_gwh']/1000:.2f} (Jan--Aug)" + r" \\")
    write("ch3_capacity", [r"\begin{tabular}{l" + "r" * (len(years) + 1) + "}", r"\toprule", "Technology (GW nameplate) & " + " & ".join(str(y) for y in years) + r" & Jul 2026 \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])
    write("ch3_capacity_note", [r"\footnotesize The 2010--2025 columns are the EIA-860 annual files; the July 2026 column is the EIA-860M monthly inventory, which is preliminary."])

    h1 = pd.read_csv(PROCESSED / "ch3_generation_jan_jun_2025_2026_monthly_respondents.csv"); hp = h1.pivot(index="resource", columns="year", values="gwh_jan_jun")
    ytd = pd.read_csv(PROCESSED / "ch3_caiso_net_imports_jan_jun.csv").set_index("year")
    order = ["Natural gas", "Nuclear", "Hydro", "Geothermal", "Biomass", "Wind", "Solar", "Coal and petcoke", "Oil", "Other", "Batteries", "Pumped storage", "Total in-state", "of which EIA state-level increment rows"]
    rows = []
    for r in order:
        if r not in hp.index: continue
        a, b = hp.loc[r, 2025], hp.loc[r, 2026]; ch = f"{(b/a-1)*100:+.0f}" if (a and abs(a) > 50 and not r.startswith("of which")) else "--"
        rows.append((r"\midrule" + "\n" if r == "Total in-state" else "") + f"{esc(r)} & {a/1000:.1f} & {b/1000:.1f} & {ch} \\\\")
    rows.append(f"CAISO net imports, EIA-930 (CAISO footprint) & {ytd.loc[2025, 'caiso_net_imports_twh']:.1f} & {ytd.loc[2026, 'caiso_net_imports_twh']:.1f} & {(ytd.loc[2026, 'caiso_net_imports_twh']/ytd.loc[2025, 'caiso_net_imports_twh']-1)*100:+.0f} \\\\")
    write("ch3_ytd2026", [r"\begin{tabular}{lrrr}", r"\toprule", r"January--June (TWh) & 2025 (final) & 2026 (preliminary) & Change (\%) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])

    sp = pd.read_csv(PROCESSED / "ch3_logit_specs.csv")
    f2 = lambda v: "--" if pd.isna(v) else f"{v:.2f}"  # noqa: E731
    rows = [f"{esc(r.specification)} & {int(r.n)} & {r.pseudo_r2:.3f} & {r.auc:.3f} & {f2(r.or_lead_or_planned_year)} & {f2(r.or_under_construction)} & {f2(r.or_natural_gas)} & {f2(r.or_log_mw)} \\\\" for r in sp.itertuples()]
    write("ch3_logit_specs", [r"\begin{tabular}{p{6.2cm}rrrrrrr}", r"\toprule", r"Specification & $n$ & Pseudo $R^2$ & AUC & OR: lead time (A, B) or planned year (C), per year & OR: under construction & OR: gas vs solar & OR: log MW \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])

    otc = pd.read_csv(PROCESSED / "ch3_otc_units.csv"); sched = pd.read_csv(PROCESSED / "ch3_eia860m_planned_retirements.csv")
    rows = []
    for (pn, cd), g in otc.groupby(["plant_name", "otc_compliance_date"], sort=False):
        eia = g["eia_planned_retirement_year"].dropna().unique()
        rows.append(f"{esc(pn)} & {esc(', '.join(g.gen_id.astype(str)))} & {esc(g.technology.iloc[0])} & {g.mw.sum():,.0f} & {int(g.operating_year.min())}--{int(g.operating_year.max())} & {cd} & {', '.join(str(int(e)) for e in eia) if len(eia) else 'none'} \\\\")
    other = sched[(sched.planned_retirement_year <= 2030) & (~sched.otc_unit)]
    rows.append(r"\midrule" + "\n" + f"Other units with an EIA date through 2030 & {len(other)} units & mixed & {other.mw.sum():,.0f} & -- & -- & {int(other.planned_retirement_year.min())}--{int(other.planned_retirement_year.max())} \\\\")
    write("ch3_retirements", [r"\begin{tabular}{p{3.6cm}p{1.4cm}p{3.2cm}rrll}", r"\toprule", r"Plant & Units & Technology & MW & In service & OTC compliance date & EIA-860M planned retirement \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])

    bt = pd.read_csv(PROCESSED / "ch3_realization_by_technology.csv").sort_values("mw_planned", ascending=False)
    rows = [f"{esc(r.resource)} & {int(r.units)} & {r.mw_planned:,.0f} & {100*r.completion_rate_units:.0f} & {100*r.completion_rate_mw:.0f} & {r.cancelled_mw:,.0f} & {r.still_planned_mw:,.0f} & {r.median_delay_months_completed:.0f} \\\\" for r in bt.itertuples() if r.units >= 10]
    write("ch3_realization_tech", [r"\begin{tabular}{lrrrrrrr}", r"\toprule", r"Technology & Unit-vintages & Planned MW & Completed (\% units) & Completed (\% MW) & Cancelled MW & Still planned MW & Median delay (months) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])
    bv = pd.read_csv(PROCESSED / "ch3_realization_by_vintage.csv")
    rows = [f"January {int(r.vintage)} & {int(r.units)} & {r.mw_planned:,.0f} & {100*r.completion_rate_units:.0f} & {100*r.completion_rate_mw:.0f} & {r.cancelled_mw:,.0f} & {r.still_planned_mw:,.0f} & {r.median_delay_months_completed:.0f} \\\\" for r in bv.itertuples()]
    bs = pd.read_csv(PROCESSED / "ch3_realization_by_status.csv").sort_values("mw_planned", ascending=False)
    rows.append(r"\midrule")
    rows += [f"Status: {esc(r.status_group)} & {int(r.units)} & {r.mw_planned:,.0f} & {100*r.completion_rate_units:.0f} & {100*r.completion_rate_mw:.0f} & {r.cancelled_mw:,.0f} & {r.still_planned_mw:,.0f} & {r.median_delay_months_completed:.0f} \\\\" for r in bs.itertuples()]
    write("ch3_realization_vintage", [r"\begin{tabular}{lrrrrrrr}", r"\toprule", r"Vintage or status at the vintage & Unit-vintages & Planned MW & Completed (\% units) & Completed (\% MW) & Cancelled MW & Still planned MW & Median delay (months) \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])

    co = pd.read_csv(PROCESSED / "ch3_logit_coefficients.csv"); summ = json.loads((PROCESSED / "ch3_logit_summary.json").read_text())
    def term(t):
        t = t.replace("C(tech, Treatment('Solar'))[T.", "Technology: ").replace("C(status_group, Treatment('approvals not initiated'))[T.", "Status: ").replace("]", "")
        return {"log_mw": "log nameplate MW", "lead_years": "Planned lead time (years)", "window_years": "Observation window (years)", "Intercept": "Intercept (solar, approvals not initiated)"}.get(t, t)
    rows = [f"{esc(term(r.term))} & {r.coef:.3f} & {r.se:.3f} & {r.odds_ratio:.2f} & {('<0.001' if r.p < 0.001 else f'{r.p:.3f}')} \\\\" for r in co.itertuples()]
    write("ch3_logit", [r"\begin{tabular}{lrrrr}", r"\toprule", r"Term & Coefficient & Cluster SE & Odds ratio & $p$ \\", r"\midrule", *rows, r"\midrule",
                        f"Observations & {summ['n_obs']} unit-vintages ({summ['n_units']} units) & & & \\\\", f"Pseudo $R^2$ / in-sample AUC & {summ['pseudo_r2']:.3f} / {summ['auc_in_sample']:.3f} & & & \\\\", r"\bottomrule", r"\end{tabular}"])

    st = summ["delay"]; cif = pd.read_csv(PROCESSED / "ch3_delay_cif.csv")
    def at(t, col): return float(cif.loc[cif.t_months <= t, col].iloc[-1]) if (cif.t_months <= t).any() else float("nan")
    rows = [f"Completed unit-vintages & {st['n_completed']} \\\\", f"Median delay, planned to actual commercial date & {st['median_delay_months']:.1f} months \\\\", f"Mean delay & {st['mean_delay_months']:.1f} months \\\\",
            f"On time or early & {100*st['share_on_time_or_early']:.0f}\\% \\\\", f"More than 12 months late & {100*st['share_late_over_12m']:.0f}\\% \\\\", f"90th percentile delay & {st['p90_delay_months']:.0f} months \\\\", r"\midrule",
            *[f"Cumulative completion by {t} months after the planned date (cancellation as competing risk) & {100*at(t, 'cif_complete'):.0f}\\% \\\\" for t in (12, 24, 36, 60)],
            f"Cumulative cancellation or drop by 60 months & {100*at(60, 'cif_cancel'):.0f}\\% \\\\"]
    write("ch3_delay", [r"\begin{tabular}{p{11cm}r}", r"\toprule", r"Statistic & Value \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])

    cases = pd.read_csv(PROCESSED / "ch3_cases_2030.csv"); cs = json.loads((PROCESSED / "ch3_cases_2030_summary.json").read_text()); ex = pd.read_csv(PROCESSED / "ch3_existing_capacity_2025.csv").set_index("resource")
    piv = cases.pivot(index="resource", columns="case", values="capacity_mw"); order = list(piv.columns)
    rows = [f"{esc(r)} & {ex.nameplate_mw.get(r, 0):,.0f} & " + " & ".join(f"{piv.loc[r, c]:,.0f}" for c in order) + r" \\" for r in CAP_ROWS if r in piv.index]
    tot = cases.groupby("case")[["capacity_mw", "energy_twh", "peak_contribution_mw"]].sum()
    rows.append(r"\midrule" + "\n" + f"Total capacity (MW) & {ex.nameplate_mw.sum():,.0f} & " + " & ".join(f"{tot.loc[c, 'capacity_mw']:,.0f}" for c in order) + r" \\")
    rows.append("Energy at realised capacity factors (TWh) & -- & " + " & ".join(f"{tot.loc[c, 'energy_twh']:.0f}" for c in order) + r" \\")
    rows.append("ELCC-derated peak contribution (MW) & -- & " + " & ".join(f"{tot.loc[c, 'peak_contribution_mw']:,.0f}" for c in order) + r" \\")
    d = cs["case_C_diablo_continues"]; rows.append(f"Case C with Diablo Canyon continuing: capacity / energy / peak & -- & -- & -- & {d['capacity_mw']:,.0f} MW / {d['energy_twh']:.0f} TWh / {d['peak_contribution_mw']:,.0f} MW \\\\")
    write("ch3_cases_2030", [r"\begin{tabular}{lrrrr}", r"\toprule", r"Technology & Existing Dec 2025 & A. Everything builds & B. Model-weighted & C. Weighted minus retirements \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])

    el = pd.read_csv(PROCESSED / "ch3_elcc_values.csv"); cf = pd.read_csv(PROCESSED / "ch3_capacity_factors.csv").set_index("resource")
    rows = [f"{esc(r.resource)} & {r.elcc:.3f} & {cf.loc[r.resource, 'capacity_factor']:.3f} & {esc(r.basis)} \\\\" for r in el.itertuples()]
    write("ch3_elcc", [r"\begin{tabular}{lrrp{9cm}}", r"\toprule", r"Technology & ELCC or derate & Capacity factor 2023--2025 & Basis \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
