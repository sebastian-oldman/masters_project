#!/usr/bin/env python
"""Chapter 3: energy production growth in California (supply side of RQ2). Writes data/processed/ch3_* and figures/fig3_*."""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src import ch3_supply as c3  # noqa: E402
from src.paths import FIGURES, PROCESSED  # noqa: E402
from src.provenance import stamp  # noqa: E402

plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 200, "font.size": 9, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})
COL = {"Natural gas": "#8c8c8c", "Nuclear": "#7b3294", "Hydro": "#2c7bb6", "Large hydro": "#2c7bb6", "Small hydro": "#74add1", "Geothermal": "#b35806", "Biomass": "#8c510a",
       "Wind": "#1a9850", "Solar": "#fdb863", "Batteries": "#d7191c", "Pumped storage": "#2166ac", "Coal and petcoke": "#252525", "Oil": "#636363", "Other": "#bdbdbd", "Imports": "#e0e0e0"}
GEN_ORDER = ["Nuclear", "Coal and petcoke", "Oil", "Other", "Natural gas", "Biomass", "Geothermal", "Hydro", "Wind", "Solar"]
CAP_ORDER = ["Nuclear", "Coal and petcoke", "Oil", "Other", "Natural gas", "Biomass", "Geothermal", "Large hydro", "Small hydro", "Pumped storage", "Wind", "Solar", "Batteries"]


def save(fig, name):
    stamp(fig, name)
    fig.savefig(FIGURES / f"{name}.png", bbox_inches="tight"); fig.savefig(FIGURES / f"{name}.pdf", bbox_inches="tight"); plt.close(fig); print("  figure", name)


def main() -> int:
    # ------------------------------------------------------------ 1. generation, imports, capacity, storage, curtailment
    print("1. Generation by resource, imports, capacity, storage, curtailment")
    gen = c3.eia923_ca_generation(); gen.to_csv(PROCESSED / "ch3_eia923_generation_by_resource.csv", index=False)
    my = c3.cec_multi_year_generation(); my.to_csv(PROCESSED / "ch3_cec_generation_multi_year.csv", index=False)
    ty = c3.cec_total_system_by_year()
    # the CEC page captured for 2021 repeats the 2020 table; keep a per-year page only when its in-state total matches the multi-year table within 2 percent
    ins_my = my[my.category == "Total In-State Generation"].set_index("year")["gwh"]
    tot_rows = ty.loc[ty.groupby("year")["energy_mix_gwh"].idxmax()].set_index("year")
    tot_rows["multi_year_in_state_gwh"] = ins_my.reindex(tot_rows.index)
    dup = (tot_rows[["in_state_gwh", "nw_imports_gwh", "sw_imports_gwh"]] == tot_rows[["in_state_gwh", "nw_imports_gwh", "sw_imports_gwh"]].shift(1)).all(axis=1)
    tot_rows["consistent"] = ((tot_rows["in_state_gwh"] / tot_rows["multi_year_in_state_gwh"] - 1).abs() < 0.02) & ~dup
    tot_rows["note"] = np.where(dup, "page repeats the previous year's table; dropped", "")
    imports = tot_rows[["in_state_gwh", "nw_imports_gwh", "sw_imports_gwh", "energy_mix_gwh", "multi_year_in_state_gwh", "consistent", "note"]].reset_index()
    imports.to_csv(PROCESSED / "ch3_cec_imports_by_year.csv", index=False); ty.to_csv(PROCESSED / "ch3_cec_total_system_by_year_pages.csv", index=False)
    ge_page, cap_page = c3.cec_capacity_and_energy_page(); ge_page.to_csv(PROCESSED / "ch3_cec_generation_2021_2025.csv", index=False); cap_page.to_csv(PROCESSED / "ch3_cec_capacity_2021_2025.csv", index=False)
    cap = c3.eia860_ca_capacity(); cap.to_csv(PROCESSED / "ch3_eia860_capacity_by_resource.csv", index=False)
    bat = c3.eia860_ca_battery_energy(); bat.to_csv(PROCESSED / "ch3_battery_capacity.csv", index=False)
    cur = c3.caiso_curtailment_annual(); cur.to_csv(PROCESSED / "ch3_caiso_curtailment_annual.csv", index=False)
    h1 = c3.eia923_h1_monthly_respondents(); h1.to_csv(PROCESSED / "ch3_generation_jan_jun_2025_2026_monthly_respondents.csv", index=False)
    ytd = c3.caiso_net_imports_ytd(); ytd.to_csv(PROCESSED / "ch3_caiso_net_imports_jan_jun.csv", index=False)
    snap, snapinfo = c3.eia860m_capacity_snapshot("eia860m_2026_07"); snap.to_csv(PROCESSED / "ch3_capacity_snapshot_2026_07.csv", index=False); (PROCESSED / "ch3_capacity_snapshot_2026_07.json").write_text(json.dumps(snapinfo, indent=1))
    print(f"   2026 year to date: in-state Jan-Jun (monthly respondents) {h1[(h1.year == 2026) & h1.resource.str.startswith('Total')].gwh_jan_jun.iloc[0]/1000:.1f} TWh vs {h1[(h1.year == 2025) & h1.resource.str.startswith('Total')].gwh_jan_jun.iloc[0]/1000:.1f} in 2025; July 2026 capacity {snapinfo['total_mw']/1000:.1f} GW, batteries {snapinfo['batteries_mw']/1000:.1f} GW / {snapinfo['batteries_mwh']/1000:.1f} GWh")
    ch1 = pd.read_csv(PROCESSED / "ch1_ciso_annual_summary.csv", index_col=0)
    net_imp = my[my.category == "Net Imports"].set_index("year")["gwh"]
    supply = gen.pivot(index="year", columns="resource", values="gwh").fillna(0)
    supply["CEC net imports"] = net_imp.reindex(supply.index)
    supply["CAISO net imports (EIA-930, chapter 1)"] = (ch1["net_imports_TWh"] * 1000).reindex(supply.index)
    supply.to_csv(PROCESSED / "ch3_supply_by_year.csv")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axes[0]; yrs = supply.index.values
    stack = [supply[r].clip(lower=0).values / 1000 for r in GEN_ORDER if r in supply]
    ax.stackplot(yrs, *stack, labels=[r for r in GEN_ORDER if r in supply], colors=[COL[r] for r in GEN_ORDER if r in supply], alpha=0.9)
    base = np.sum(stack, axis=0)
    imp = supply["CEC net imports"].values / 1000
    ax.fill_between(yrs, base, base + np.nan_to_num(imp), where=~np.isnan(imp), color=COL["Imports"], hatch="//", edgecolor="grey", label="Net imports, CEC statewide (2012-2024)")
    proxy = supply["CAISO net imports (EIA-930, chapter 1)"].values / 1000; ok = ~np.isnan(proxy)
    ax.plot(yrs[ok], (base + proxy)[ok], color="k", ls=":", lw=1.2, label="In-state + CAISO net imports, 2019-2025 (EIA-930; CAISO footprint only)")
    tot_in = supply["Total in-state"] / 1000; bx = dict(boxstyle="round,pad=0.2", fc="white", ec="grey", lw=0.5)
    ax.annotate(f"in-state {tot_in.loc[2025]:.0f} TWh (2025)", xy=(2025, base[-1]), xytext=(2022.6, 228), fontsize=7.5, ha="center", bbox=bx, arrowprops=dict(arrowstyle="-", color="grey", lw=0.6))
    i24 = list(yrs).index(2024); ax.text(2018.5, base[i24] + imp[i24] / 2 + 12, f"net imports {imp[i24]:.0f} TWh (2024)", fontsize=7.5, ha="center", bbox=bx)
    ax.text(2010.15, base[0] + 6, f"in-state {tot_in.loc[2010]:.0f} TWh (2010)", fontsize=7.5, bbox=bx)
    ax.set_xlim(2010, 2025); ax.set_ylabel("TWh"); ax.set_title("California electricity supply: in-state generation by resource (EIA-923) and net imports (CEC)")
    ax.legend(fontsize=6.8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False)
    ax = axes[1]
    ins = supply[[r for r in GEN_ORDER if r in supply]].sum(axis=1)
    ax.plot(yrs, (supply["Solar"] + supply["Wind"]) / ins * 100, marker="o", ms=3, color=COL["Solar"], label="solar + wind share of in-state generation")
    ax.plot(yrs, supply["Natural gas"] / ins * 100, marker="o", ms=3, color=COL["Natural gas"], label="natural gas share of in-state generation")
    tot = ins + supply["CEC net imports"]
    ax.plot(yrs, supply["CEC net imports"] / tot * 100, marker="s", ms=3, color="k", label="net imports share of total system (CEC)")
    sw = ((supply["Solar"] + supply["Wind"]) / ins * 100); gs = (supply["Natural gas"] / ins * 100); ims = (supply["CEC net imports"] / tot * 100)
    for ser, y_, col in ((sw, 2025, COL["Solar"]), (gs, 2025, COL["Natural gas"]), (ims, 2024, "k"), (sw, 2010, COL["Solar"]), (gs, 2010, COL["Natural gas"]), (ims, 2012, "k")):
        ax.annotate(f"{ser[y_]:.0f}%", xy=(y_, ser[y_]), xytext=(4 if y_ > 2015 else -22, 4), textcoords="offset points", fontsize=7.5, color=col)
    ax.set_ylabel("percent"); ax.set_title("Shares (labels: first and last year)"); ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False); ax.set_xlim(2010, 2026.2)
    save(fig, "fig3_01_generation_by_resource")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), gridspec_kw={"width_ratios": [1.5, 1, 1]})
    ax = axes[0]; cp = cap[cap.resource != "Total"].pivot(index="year", columns="resource", values="nameplate_mw").fillna(0)
    ax.stackplot(cp.index.values, *[cp[r].values / 1000 for r in CAP_ORDER if r in cp], labels=[r for r in CAP_ORDER if r in cp], colors=[COL[r] for r in CAP_ORDER if r in cp], alpha=0.9)
    tot_cap = cp[[r for r in CAP_ORDER if r in cp]].sum(axis=1) / 1000  # GW
    ax.plot([2026.5], [snapinfo["total_mw"] / 1000], "ko", ms=4); ax.text(2026.5, snapinfo["total_mw"] / 1000 + 6, f"{snapinfo['total_mw']/1000:.0f} GW\nJul 2026\n(EIA-860M)", fontsize=6.8, ha="center", va="bottom")
    ax.text(2024.85, tot_cap.loc[2025] + 3, f"{tot_cap.loc[2025]:.0f} GW (2025)", fontsize=7.5, ha="right"); ax.text(2010.1, tot_cap.loc[2010] + 3, f"{tot_cap.loc[2010]:.0f} GW (2010)", fontsize=7.5)
    ax.set_ylabel("GW nameplate"); ax.set_title("Operable capacity by technology\n(EIA-860 annual; July 2026 from EIA-860M)", fontsize=9); ax.set_xlim(2010, 2027.6); ax.set_ylim(0, 150); ax.legend(fontsize=6.5, loc="upper left", ncol=2)
    ax = axes[1]; ax.bar(bat.year, bat.power_mw / 1000, color=COL["Batteries"], alpha=0.8, label="power, GW (EIA-860 annual)"); ax.bar([2026], [snapinfo["batteries_mw"] / 1000], color="none", edgecolor=COL["Batteries"], hatch="//", label="power, GW (EIA-860M, Jul 2026)")
    ax.set_ylabel("GW"); ax2 = ax.twinx(); ax2.plot(list(bat.year) + [2026], list(bat.energy_mwh / 1000) + [snapinfo["batteries_mwh"] / 1000], "k.-", label="energy, GWh"); ax2.set_ylabel("GWh"); ax2.grid(False)
    b25 = bat.set_index("year").loc[2025]
    ax.annotate(f"2025: {b25['power_mw']/1000:.1f} GW, {b25['energy_mwh']/1000:.0f} GWh", xy=(2025, b25["power_mw"] / 1000), xytext=(2023.6, 19.0), ha="right", fontsize=6.8, arrowprops=dict(arrowstyle="-", color="grey", lw=0.6))
    ax.annotate(f"Jul 2026: {snapinfo['batteries_mw']/1000:.1f} GW, {snapinfo['batteries_mwh']/1000:.0f} GWh", xy=(2026, snapinfo["batteries_mw"] / 1000), xytext=(2024.6, 21.6), ha="right", fontsize=6.8, arrowprops=dict(arrowstyle="-", color="grey", lw=0.6))
    ax.set_xlim(2015.3, 2027.3); ax.set_xticks(range(2016, 2027, 2)); ax.set_ylim(0, snapinfo["batteries_mw"] / 1000 * 1.5); ax2.set_ylim(0, snapinfo["batteries_mwh"] / 1000 * 1.5)
    ax.set_title("Battery storage, operable (EIA-860)"); h1_, l1 = ax.get_legend_handles_labels(); h2_, l2 = ax2.get_legend_handles_labels(); ax.legend(h1_ + h2_, l1 + l2, fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=1, frameon=False)  # below the axes: no overlap with bars or labels
    ax = axes[2]; full = cur[cur.months == 12]; part = cur[cur.months < 12]
    ax.bar(full.year, full.curtailed_gwh / 1000, color=COL["Solar"], edgecolor="k", label="full year"); ax.bar(part.year, part.curtailed_gwh / 1000, color="none", edgecolor="k", hatch="//", label="partial year: " + ", ".join(f"{int(y)} ({int(m)} months)" for y, m in zip(part.year, part.months)))
    for y_, v in zip(cur.year, cur.curtailed_gwh / 1000):
        if y_ >= 2019: ax.text(y_, v + 0.05, f"{v:.1f}", ha="center", fontsize=6.5)
    ax.set_ylabel("TWh curtailed"); ax.set_title("CAISO wind and solar curtailment"); ax.legend(fontsize=6.5, loc="upper left"); ax.set_xticks(range(2014, 2027, 2)); ax.set_ylim(0, cur.curtailed_gwh.max() / 1000 * 1.2)
    fig.subplots_adjust(wspace=0.42)
    save(fig, "fig3_02_capacity_storage_curtailment")

    # ------------------------------------------------------------ 2. retirements
    print("2. Retirement schedule")
    sched, otc = c3.retirement_schedule(); sched.to_csv(PROCESSED / "ch3_eia860m_planned_retirements.csv", index=False); otc.to_csv(PROCESSED / "ch3_otc_units.csv", index=False)
    yr_tab = sched[sched.planned_retirement_year <= 2035].groupby(["planned_retirement_year", "resource"])["mw"].sum().unstack().fillna(0)
    fig, ax = plt.subplots(figsize=(10, 4.4)); bottom = np.zeros(len(yr_tab))
    for r in yr_tab.columns:
        ax.bar(yr_tab.index, yr_tab[r], bottom=bottom, width=0.55, color=COL.get(r, "#999"), label=f"{r} (EIA-860M planned retirement date)"); bottom += yr_tab[r].values
    extra = otc[otc.eia_planned_retirement_year.isna()].groupby("schedule_year")["mw"].sum()
    for y, mw in extra.items():
        b = float(yr_tab.sum(axis=1).get(y, 0.0)); ax.bar(y, mw, bottom=b, width=0.55, color="none", edgecolor="k", hatch="//", label="no EIA date: OTC compliance date (Haynes, Harbor 2029; Diablo Canyon 2030)" if y == extra.index[0] else None)
    for y, txt in ((2026, "Alamitos 3-5,\nHuntington Bch 2\n(OTC 12/2026)"), (2027, "Ormond Beach 1-2\n(OTC 12/2026,\nEIA 1/2027)"), (2029, "Scattergood 1-2\n(EIA 2029);\nHaynes 1, 2, 8\nand Harbor 5\n(OTC 12/2029)"), (2030, "Diablo Canyon 1-2\n(OTC 10/2030,\nSB 846)")):
        tot = float(yr_tab.sum(axis=1).get(y, 0.0)) + float(extra.get(y, 0.0)); ax.text(y, tot + 60, f"{tot:,.0f} MW\n" + txt, ha="center", fontsize=6.3, va="bottom")
    tot30 = float(yr_tab.loc[yr_tab.index <= 2030].sum().sum()) + float(extra[extra.index <= 2030].sum())
    ax.text(2033, 1300, f"Scheduled through 2030: {tot30:,.0f} MW\nEIA dates: {float(yr_tab.loc[yr_tab.index <= 2030].sum().sum()):,.0f} MW\nOTC dates without EIA date: {float(extra[extra.index <= 2030].sum()):,.0f} MW\n(of which Diablo Canyon {float(otc[otc.plant_id.astype(str) == '6099'].mw.sum()):,.0f} MW)", ha="center", va="center", fontsize=7, bbox=dict(boxstyle="round", fc="white", ec="grey"))
    ax.set_xticks(range(2026, 2036)); ax.set_xlabel("year"); ax.set_ylabel("MW"); ax.set_ylim(0, 4200); ax.set_title("Scheduled retirements in California: EIA-860M planned dates and State Water Board once-through-cooling compliance dates", fontsize=9.5)
    ax.legend(fontsize=7, loc="upper right"); save(fig, "fig3_03_retirement_schedule")

    # ------------------------------------------------------------ 3. realization model
    print("3. Realization model from EIA-860M vintages")
    d = c3.eia860m_vintage_outcomes(); d.to_csv(PROCESSED / "ch3_vintage_outcomes.csv", index=False)
    by_tech = c3.realization_by(d, "resource"); by_tech.to_csv(PROCESSED / "ch3_realization_by_technology.csv", index=False)
    by_v = c3.realization_by(d, "vintage"); by_v.to_csv(PROCESSED / "ch3_realization_by_vintage.csv", index=False)
    by_s = c3.realization_by(d, "status_group"); by_s.to_csv(PROCESSED / "ch3_realization_by_status.csv", index=False)
    res, m = c3.fit_completion_logit(d, with_status=True); res0, m0 = c3.fit_completion_logit(d, with_status=False)
    resy, my = c3.fit_completion_logit(d, with_status=True, spec="planned_year")
    def orr(r, key):
        k = [t for t in r.params.index if key in t]; return float(np.exp(r.params[k[0]])) if k else np.nan
    specs = pd.DataFrame([
        {"specification": "A. lead time + window + status (main)", "n": int(res.nobs), "pseudo_r2": res.prsquared, "auc": c3._auc(m.completed_i, m.p_hat), "or_lead_or_planned_year": orr(res, "lead_years"), "or_under_construction": orr(res, "under construction"), "or_natural_gas": orr(res, "Natural gas"), "or_log_mw": orr(res, "log_mw")},
        {"specification": "B. lead time + window, no status", "n": int(res0.nobs), "pseudo_r2": res0.prsquared, "auc": c3._auc(m0.completed_i, m0.p_hat), "or_lead_or_planned_year": orr(res0, "lead_years"), "or_under_construction": np.nan, "or_natural_gas": orr(res0, "Natural gas"), "or_log_mw": orr(res0, "log_mw")},
        {"specification": "C. planned year + vintage fixed effects + status", "n": int(resy.nobs), "pseudo_r2": resy.prsquared, "auc": c3._auc(my.completed_i, my.p_hat), "or_lead_or_planned_year": orr(resy, "planned_year_f"), "or_under_construction": orr(resy, "under construction"), "or_natural_gas": orr(resy, "Natural gas"), "or_log_mw": orr(resy, "log_mw")},
    ]); specs.to_csv(PROCESSED / "ch3_logit_specs.csv", index=False)
    coefs = pd.DataFrame({"term": res.params.index, "coef": res.params.values, "se": res.bse.values, "p": res.pvalues.values, "odds_ratio": np.exp(res.params.values)})
    coefs.to_csv(PROCESSED / "ch3_logit_coefficients.csv", index=False)
    summ = {"n_obs": int(res.nobs), "n_units": int(m.key.nunique()), "pseudo_r2": float(res.prsquared), "auc_in_sample": c3._auc(m.completed_i, m.p_hat), "llf": float(res.llf),
            "no_status": {"pseudo_r2": float(res0.prsquared), "auc_in_sample": c3._auc(m0.completed_i, m0.p_hat), "coef": {k: float(v) for k, v in res0.params.items()}},
            "completion_rate_overall_units": float(d.completed.mean()), "completion_rate_overall_mw": float(d.loc[d.completed, "mw"].sum() / d.mw.sum())}
    km, cif, st = c3.km_delay(d); km.to_csv(PROCESSED / "ch3_delay_km.csv", index=False); cif.to_csv(PROCESSED / "ch3_delay_cif.csv", index=False); summ["delay"] = st
    (PROCESSED / "ch3_logit_summary.json").write_text(json.dumps(summ, indent=1))
    print(f"   {summ['n_obs']} unit-vintages, {summ['n_units']} units; completion {100*summ['completion_rate_overall_mw']:.0f}% of MW; AUC {summ['auc_in_sample']:.2f}; median delay {st['median_delay_months']:.1f} months")

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 9.0)); fig.subplots_adjust(hspace=0.42, wspace=0.28)
    ax = axes[0, 0]; ov = d.assign(grp=np.where(d.completed, "completed by Dec 2025", np.where(d.outcome == "still planned", "still planned", "cancelled or dropped"))).groupby(["vintage", "grp"])["mw"].sum().unstack().fillna(0) / 1000
    bottom = np.zeros(len(ov))
    for g, colr in (("completed by Dec 2025", "#1a9850"), ("still planned", "#fdb863"), ("cancelled or dropped", "#d7191c")):
        ax.bar(ov.index, ov[g], bottom=bottom, color=colr, label=g); bottom += ov[g].values
    for i, (v, tot) in enumerate(ov.sum(axis=1).items()): ax.text(v, tot + 0.2, f"{100*ov.loc[v, 'completed by Dec 2025']/tot:.0f}%", ha="center", fontsize=7.5)
    ax.text(0.98, 0.97, f"all vintages: {100*d.loc[d.completed, 'mw'].sum()/d.mw.sum():.0f}% of {d.mw.sum()/1000:.0f} GW completed\n({int(d.completed.sum())} of {len(d)} unit-vintages, {d.key.nunique()} units)", transform=ax.transAxes, ha="right", va="top", fontsize=7, bbox=dict(boxstyle="round", fc="white", ec="grey"))
    ax.set_xlabel("January vintage of the EIA-860M planned list"); ax.set_ylabel("GW planned in California"); ax.set_title("Outcome by December 2025 of each January planned list\n(label: share of planned MW completed)", fontsize=9); ax.legend(fontsize=7, loc="upper left"); ax.set_ylim(0, ov.sum(axis=1).max() * 1.3)
    ax = axes[0, 1]; bt = by_tech[by_tech.units >= 15].sort_values("completion_rate_mw")
    ax.barh(bt.resource, bt.completion_rate_mw * 100, color=[COL.get(r, "#999") for r in bt.resource], alpha=0.85, label="share of planned MW completed")
    ax.plot(bt.completion_rate_units * 100, bt.resource, "k|", ms=12, mew=2, label="share of units completed")
    for i, r in enumerate(bt.itertuples()): ax.text(102, i, f"{int(r.units)} units, {r.mw_planned/1000:.1f} GW", va="center", fontsize=7)
    ax.set_xlim(0, 130); ax.set_xlabel("percent"); ax.set_title("Completion by technology, seven vintages pooled\n(technologies with 15 or more unit-vintages)", fontsize=9); ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
    ax = axes[1, 0]; lead = np.linspace(0, 5, 26)
    for tech, ls in (("Solar", "-"), ("Batteries", "--"), ("Natural gas", ":")):
        for sg, colr in (("under construction", "#1a9850"), ("approvals not initiated", "#d7191c")):
            X = pd.DataFrame({"tech": tech, "log_mw": np.log(50.0), "lead_years": lead, "window_years": 4.46, "status_group": sg})
            ax.plot(lead, res.predict(X) * 100, ls, color=colr, label=f"{tech}, {sg}")
    ax.text(0.02, 0.04, f"odds ratios: lead time {orr(res, 'lead_years'):.2f} per year; window {orr(res, 'window_years'):.2f} per year;\nunder construction {orr(res, 'under construction'):.2f}; natural gas vs solar {orr(res, 'Natural gas'):.2f}; log MW {orr(res, 'log_mw'):.2f}\nAUC {c3._auc(m.completed_i, m.p_hat):.2f}, pseudo R2 {res.prsquared:.2f}, n = {int(res.nobs)}", transform=ax.transAxes, fontsize=6.5, va="bottom", bbox=dict(boxstyle="round", fc="white", ec="grey"))
    ax.set_xlabel("planned lead time (years from file date to planned commercial date)"); ax.set_ylabel("predicted completion within a 4.5-year window (%)"); ax.set_title("Logistic model, 50 MW unit, window July 2026 to Dec 2030"); ax.legend(fontsize=6.5, ncol=2); ax.set_ylim(0, 100)
    ax = axes[1, 1]; ax.step(cif.t_months, cif.cif_complete * 100, where="post", color="#1a9850", lw=1.8, label="cumulative completion (cancellation as competing risk)")
    ax.step(cif.t_months, cif.cif_cancel * 100, where="post", color="#d7191c", lw=1.8, label="cumulative cancellation or drop")
    ax.step(km.t_months, (1 - km.S_not_yet_operating) * 100, where="post", color="k", ls="--", lw=1, label="Kaplan-Meier, cancellations censored (upper bound)")
    for tm in (12, 24, 60):
        v = float(cif.loc[cif.t_months <= tm, "cif_complete"].iloc[-1]) * 100; ax.plot([tm], [v], "o", color="#1a9850", ms=4); ax.annotate(f"{v:.0f}% at {tm} mo", xy=(tm, v), xytext=(4 if tm < 60 else -62, -12), textcoords="offset points", fontsize=7, color="#1a9850")
    vc = float(cif.loc[cif.t_months <= 60, "cif_cancel"].iloc[-1]) * 100; ax.annotate(f"{vc:.0f}% cancelled or dropped at 60 mo", xy=(60, vc), xytext=(-120, 8), textcoords="offset points", fontsize=7, color="#d7191c")
    ax.text(0.98, 0.5, f"completed units: median delay {st['median_delay_months']:.1f} months,\n{100*st['share_on_time_or_early']:.0f}% on time or early, {100*st['share_late_over_12m']:.0f}% more than 12 months late", transform=ax.transAxes, ha="right", va="center", fontsize=6.8, bbox=dict(boxstyle="round", fc="white", ec="grey"))
    ax.set_xlim(0, 72); ax.set_xlabel("months after the planned commercial date"); ax.set_ylabel("percent of planned units"); ax.set_title("Delay from planned to actual commercial operation"); ax.legend(fontsize=7, loc="lower right")
    save(fig, "fig3_04_realization_model")

    # ------------------------------------------------------------ 4. 2030 cases
    print("4. Probability-weighted supply for 2030")
    pl = c3.current_planned()
    pl["tech"] = np.where(pl["resource"].isin(m["tech"].unique()), pl["resource"], "Other"); pl["log_mw"] = np.log(pl["mw"].clip(lower=0.1))
    pl["p_2030"] = res.predict(pl); pl["weighted_mw"] = pl["mw"] * pl["p_2030"]; pl.to_csv(PROCESSED / "ch3_planned_current_weighted.csv", index=False)
    ex = c3.existing_capacity_2025(); ex.to_csv(PROCESSED / "ch3_existing_capacity_2025.csv", index=False)
    cf = c3.capacity_factors(gen, cap); cf.to_csv(PROCESSED / "ch3_capacity_factors.csv", index=False)
    elcc = c3.elcc_table(); elcc.to_csv(PROCESSED / "ch3_elcc_values.csv", index=False)
    cases = c3.cases_2030(ex, pl, sched, otc, cf, elcc); cases.to_csv(PROCESSED / "ch3_cases_2030.csv", index=False)
    totals = cases.groupby("case")[["capacity_mw", "energy_twh", "peak_contribution_mw"]].sum()
    # Diablo Canyon sensitivity: case C with the plant continuing (NRC licence renewal pending)
    dc = otc[otc.plant_id == "6099"]; dc_mw = float(dc.mw.sum()); dc_cf = float(cf.set_index("resource").loc["Nuclear", "capacity_factor"]); dc_el = float(elcc.set_index("resource").loc["Nuclear", "elcc"])
    sens = {"case_C_diablo_continues": {"capacity_mw": float(totals.loc["C. Model-weighted minus retirements", "capacity_mw"] + dc_mw), "energy_twh": float(totals.loc["C. Model-weighted minus retirements", "energy_twh"] + dc_mw * dc_cf * 8760 / 1e6),
                                        "peak_contribution_mw": float(totals.loc["C. Model-weighted minus retirements", "peak_contribution_mw"] + dc_mw * dc_el)}}
    summary = {"existing_2025_mw": float(ex.nameplate_mw.sum()), "planned_through_2030_mw": float(pl[pl.planned_year <= 2030].mw.sum()), "planned_units_through_2030": int((pl.planned_year <= 2030).sum()),
               "weighted_planned_through_2030_mw": float(pl[pl.planned_year <= 2030].weighted_mw.sum()), "retirements_through_2030_mw": float(cases[cases.case.str.startswith("C")].retirements_mw.sum()),
               "diablo_canyon_mw": dc_mw, "totals": {k: {c: float(v) for c, v in row.items()} for k, row in totals.iterrows()}, **sens,
               "weighted_share_by_resource": {r: float(v) for r, v in (pl[pl.planned_year <= 2030].groupby("resource").weighted_mw.sum() / pl[pl.planned_year <= 2030].groupby("resource").mw.sum()).items()}}
    (PROCESSED / "ch3_cases_2030_summary.json").write_text(json.dumps(summary, indent=1)); print(json.dumps(summary["totals"], indent=1))

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1.5, 1]})
    short = {"A. Everything builds": "A. Everything\nbuilds", "B. Model-weighted": "B. Model-\nweighted", "C. Model-weighted minus retirements": "C. Weighted\nminus\nretirements"}
    ax = axes[0]; labels = ["Existing\nDec 2025"] + [short[c] for c in totals.index]
    piv = cases.pivot(index="case", columns="resource", values="capacity_mw")
    xs = np.arange(len(labels)); bottom = np.zeros(len(labels))
    for r in CAP_ORDER:
        vals = np.array([float(ex.set_index("resource").nameplate_mw.get(r, 0))] + [float(piv.loc[c, r]) for c in totals.index]) / 1000
        ax.bar(xs, vals, bottom=bottom, color=COL[r], label=r, width=0.6); bottom += vals
    for x, b in zip(xs, bottom): ax.text(x, b + 1, f"{b:.0f} GW", ha="center", fontsize=8, fontweight="bold")
    ax.text(0.5, 0.985, f"July 2026 planned list through 2030: {summary['planned_through_2030_mw']/1000:.1f} GW in {summary['planned_units_through_2030']} units; model-weighted {summary['weighted_planned_through_2030_mw']/1000:.1f} GW\nscheduled retirements {summary['retirements_through_2030_mw']/1000:.1f} GW, of which Diablo Canyon {summary['diablo_canyon_mw']/1000:.1f} GW", transform=ax.transAxes, ha="center", va="top", fontsize=6.8, bbox=dict(boxstyle="round", fc="white", ec="grey"))
    ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=8); ax.set_ylabel("GW nameplate"); ax.set_title("Capacity by technology: existing and three 2030 cases"); ax.legend(fontsize=6.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2), frameon=False); ax.set_ylim(0, bottom.max() * 1.15)
    ax = axes[1]; w = 0.38; xs2 = np.arange(len(totals))
    ax.bar(xs2 - w / 2, totals.energy_twh, w, color="#4575b4", label="energy at realised capacity factors (TWh)")
    ax.set_ylabel("TWh per year"); ax2 = ax.twinx(); ax2.bar(xs2 + w / 2, totals.peak_contribution_mw / 1000, w, color="#d73027", label="ELCC-derated peak contribution (GW)"); ax2.set_ylabel("GW"); ax2.grid(False)
    for x, (e, p) in enumerate(zip(totals.energy_twh, totals.peak_contribution_mw / 1000)): ax.text(x - w / 2, e + 3, f"{e:.0f}", ha="center", fontsize=8); ax2.text(x + w / 2, p + 1, f"{p:.1f}", ha="center", fontsize=8)
    ax.set_xticks(xs2); ax.set_xticklabels([short[c] for c in totals.index], fontsize=8); ax.set_title("Energy and ELCC-derated peak, 2030"); h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.16), frameon=False)
    ax.set_ylim(0, totals.energy_twh.max() * 1.25); ax2.set_ylim(0, totals.peak_contribution_mw.max() / 1000 * 1.25)
    save(fig, "fig3_05_cases_2030")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
