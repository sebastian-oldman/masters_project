#!/usr/bin/env python
"""Chapter 4: putting it together (RQ2 gap model, RQ4 headroom, RQ3 crosswalk). Writes data/processed/ch4_* and figures/fig4_*.
Runs in about a minute: four CED workbooks, a 10,000-draw Monte Carlo, a 28,672-evaluation Sobol design and the hourly headroom goal-seek."""
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
import matplotlib.dates as mdates  # noqa: E402

from src import ch4_gap as g  # noqa: E402
from src import ch4_regimes as rg  # noqa: E402
from src.paths import FIGURES, PROCESSED  # noqa: E402
from src.provenance import stamp  # noqa: E402

plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 200, "font.size": 9, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})
BOX = dict(boxstyle="round,pad=0.3", fc="white", ec="grey", lw=0.5)
GROUP_COL = {"proposal": "#d7191c", "CEC": "#2c7bb6", "ERCOT": "#fdae61", "PJM": "#7b3294"}
STATUS_COL = {"No studies submitted": "#ff7f0e", "Under ERCOT review": "#9467bd", "Planning studies approved": "#5f6b73", "Approved to energize, not operational": "#17becf", "Observed energized": "#2ca02c"}


def save(fig, name):
    stamp(fig, name)
    fig.savefig(FIGURES / f"{name}.png", bbox_inches="tight"); fig.savefig(FIGURES / f"{name}.pdf", bbox_inches="tight"); plt.close(fig); print("  figure", name)


def main() -> int:
    # ------------------------------------------------------------ 1. tiers, CEC parameters, CED 2025 scenarios and non-data-center growth
    print("1. Tiers, CEC parameters, CED 2025 scenarios, non-data-center growth")
    tiers = g.ca_tiers(); tiers.to_csv(PROCESSED / "ch4_ca_tiers.csv", index=False)
    params = g.cec_parameters(); (PROCESSED / "ch4_cec_parameters.json").write_text(json.dumps({**params, "confidence": {f"{k[0]}|{k[1]}": v for k, v in params["confidence"].items()}}, indent=1))
    scen = g.ced2025_scenarios(); scen.to_csv(PROCESSED / "ch4_ced2025_scenarios.csv", index=False)
    dc = g.ced2025_data_center_component(); dc.to_csv(PROCESSED / "ch4_ced2025_data_center_component.csv", index=False)
    dce = g.ced2025_data_center_energy(dc); dce.to_csv(PROCESSED / "ch4_ced2025_data_center_energy.csv", index=False)
    growth = g.iepr_growth_cases(scen, dc, dce); growth.to_csv(PROCESSED / "ch4_iepr_growth_cases.csv", index=False)
    gs = g.growth_summary(growth); gs.to_csv(PROCESSED / "ch4_iepr_growth_summary.csv", index=False)
    rep, prof, eff = g.cec_forecast_replication(params, dc); rep.to_csv(PROCESSED / "ch4_cec_replication.csv", index=False); prof.to_csv(PROCESSED / "ch4_cec_ramp_profile.csv", index=False)
    assert (rep.difference_mw.abs() < 1).all(), "CEC parameters with the SVP exemption should reproduce the memo's 2040 endpoints"
    print(f"   CEC parameters reproduce the memo endpoints: " + "; ".join(f"{r.scenario} {r.full_ramp_statewide_mw:,.0f} vs {r.memo_endpoint_2040_mw:,.0f} MW; 2030 replicated {r.replicated_2030_california_mw:,.0f} vs published {r.published_2030_california_mw:,.0f} MW (California-only)" for r in rep.itertuples()))
    chk = dc[(dc.tac == "CAISO") & (dc.scenario == "Baseline") & (dc.year.between(2025, 2030))].set_index("year").baseline_net_load_mw
    base_peak = scen[(scen.scenario == "Baseline") & (scen.metric == "peak_caiso_coincident_MW")].set_index("year").value.reindex(chk.index)
    assert (chk.values == base_peak.values).all(), "Baseline workbook peak should equal the Planning baseline net load"
    print(f"   California-only tiers {tiers.mw_california.sum():,.0f} MW; non-data-center peak growth 2025-2030 low/mid/high {gs.peak_non_dc_growth_MW.iloc[0]:,.0f}/{gs.peak_non_dc_growth_MW.iloc[1]:,.0f}/{gs.peak_non_dc_growth_MW.iloc[2]:,.0f} MW; energy {gs.energy_non_dc_growth_GWh.iloc[0]/1000:.1f}/{gs.energy_non_dc_growth_GWh.iloc[1]/1000:.1f}/{gs.energy_non_dc_growth_GWh.iloc[2]/1000:.1f} TWh")

    # ------------------------------------------------------------ 2. ERCOT queue series, transition rates, PJM adjustments
    print("2. ERCOT queue series, transition rates and chain; PJM adjustment tables")
    q, a, s, n = g.ercot_series()
    q.to_csv(PROCESSED / "ch4_ercot_queue_monthly.csv", index=False); a.to_csv(PROCESSED / "ch4_ercot_approvals_monthly.csv", index=False)
    s.to_csv(PROCESSED / "ch4_ercot_status_snapshots.csv", index=False); n.to_csv(PROCESSED / "ch4_ercot_narrative.csv", index=False)
    rates = g.ercot_transition_rates(q, a, s, n); rates.to_csv(PROCESSED / "ch4_ercot_transition_rates.csv", index=False)
    chain = g.ercot_chain(rates)
    chains = pd.concat([g.ercot_chain(rates, scale=sc, cancel_hazard=ch) for sc in (1.0, 2.0, 3.0) for ch in (0.0, 0.005)], ignore_index=True)
    chains.to_csv(PROCESSED / "ch4_ercot_chain.csv", index=False)
    pjm = rg.pjm_adjustment_tables(); pjm.to_csv(PROCESSED / "ch4_pjm_adjustments.csv", index=False)
    pd.DataFrame(rg.PJM_LAR_CHART, columns=["year", "request_mw", "firm_mw", "non_firm_mw"]).assign(source="pjm_lar_summary_2025_11_24 slide 8, read from chart (approximate)").to_csv(PROCESSED / "ch4_pjm_lar_chart_readings.csv", index=False)
    print("   monthly hazards: " + "; ".join(f"{r.transition.split(' -> ')[0]} {100*r.monthly_hazard:.2f}%" for r in rates.itertuples()))
    print("   P(energized within 60 months): " + "; ".join(f"{r.start_state} {r.p_energized:.3f}" for r in chain.itertuples()))

    # ------------------------------------------------------------ 3. demand cases for 2030
    print("3. Demand cases for 2030")
    cases = g.demand_cases_2030(tiers, params, chain, gs, rep, eff); cases.to_csv(PROCESSED / "ch4_demand_cases_2030.csv", index=False)
    totals = g.demand_totals_2030(cases, gs); totals.to_csv(PROCESSED / "ch4_demand_totals_2030.csv", index=False)
    sup = g.SupplyModel(); base = sup.base()
    c3 = json.loads((PROCESSED / "ch3_cases_2030_summary.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]; cc = cases.iloc[::-1]
    bars = ax.barh(range(len(cc)), cc.dc_peak_mw_2030 / 1000, color=[GROUP_COL[x] for x in cc.group])
    ax.set_yticks(range(len(cc))); ax.set_yticklabels([c.replace(": ", ":\n") if len(c) > 34 else c for c in cc.case], fontsize=7.5)
    for b, v, e in zip(bars, cc.dc_peak_mw_2030, cc.dc_energy_twh_2030):
        ax.text(b.get_width() + 0.15, b.get_y() + b.get_height() / 2, f"{v:,.0f} MW, {e:.1f} TWh", va="center", fontsize=7)
    ax.set_xlim(0, cc.dc_peak_mw_2030.max() / 1000 * 1.35); ax.set_xlabel("data center peak added by 2030 (GW), California-only tiers of December 2025")
    ax.set_title("Data center demand in 2030 under each counting rule", fontsize=9)
    ax.text(0.98, 0.62, f"tiers: agreements {tiers.mw_california.iloc[0]:,.0f}, applications {tiers.mw_california.iloc[1]:,.0f}, inquiries {tiers.mw_california.iloc[2]:,.0f} MW\n(VEA's {tiers.mw_excluded_nevada.sum():,.0f} MW of Nevada applications excluded)", transform=ax.transAxes, ha="right", va="center", fontsize=7, bbox=BOX)
    ax = axes[1]
    pick = [("CEC central", "CEC central (Planning forecast, published)"), ("PJM firm", "PJM-style: firm only (signed agreements)"), ("upper bound", "Upper bound: every MW builds, flat load")]
    x = np.arange(3); w = 0.26
    for j, (lab, key) in enumerate(pick):
        dcmw = float(cases.set_index("case").loc[key, "dc_peak_mw_2030"])
        nd = gs.peak_non_dc_2030_MW.iloc[:3].values / 1000
        ax.bar(x + (j - 1) * w, nd, w, color="#bdbdbd", edgecolor="white")
        ax.bar(x + (j - 1) * w, np.full(3, dcmw / 1000), w, bottom=nd, color=GROUP_COL[["CEC", "PJM", "proposal"][j]], edgecolor="white", label=f"data center: {lab} ({dcmw/1000:.1f} GW)")
        for xi, v in zip(x + (j - 1) * w, nd + dcmw / 1000):
            ax.text(xi, v + 0.4, f"{v:.1f}", ha="center", fontsize=6.5)
    ax.set_xticks(x); ax.set_xticklabels([f"{c} ({s_})\nnon-DC {v/1000:.1f} GW" for c, s_, v in zip(gs.case.iloc[:3], gs.scenario.iloc[:3], gs.peak_non_dc_2030_MW.iloc[:3])], fontsize=7.5)
    for key, ls, off in (("A. Everything builds", ":", 0.3), ("B. Model-weighted", "--", 0.3), ("C. Model-weighted minus retirements", "-.", -2.2)):
        v = c3["totals"][key]["peak_contribution_mw"] / 1000; ax.axhline(v, color="k", ls=ls, lw=0.9); ax.text(2.48, v + off, f"supply case {key[:1]}: {v:.0f} GW" + (f"\n(= existing fleet ELCC {base['elcc_mw']/1000:.0f} GW)" if key.startswith("C") else ""), fontsize=6.3, ha="left", va="bottom")
    ax.axhline(base["elcc_mw"] / 1000, color="grey", lw=0.8)
    ax.set_xlim(-0.55, 3.45); ax.set_ylim(0, 92); ax.set_ylabel("GW"); ax.set_title("2030 statewide coincident peak by IEPR case (non-DC plus data centers)\nagainst ELCC-derated supply of Chapter 3", fontsize=9)
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1, frameon=False)
    save(fig, "fig4_01_demand_scenarios_2030")

    # ------------------------------------------------------------ 4. Monte Carlo gap model
    print("4. Monte Carlo gap model (10,000 draws)")
    inputs = g.mc_inputs(chain, sup, params); inputs.to_csv(PROCESSED / "ch4_mc_inputs.csv", index=False)
    draws = g.monte_carlo(10000, tiers, gs, sup, inputs); draws.to_parquet(PROCESSED / "ch4_mc_draws.parquet")
    summ = g.summarize(draws); summ.to_csv(PROCESSED / "ch4_mc_summary.csv", index=False)
    ub = g.upper_bound_rows(tiers, gs, sup, inputs); ub.to_csv(PROCESSED / "ch4_upper_bound_2030.csv", index=False)
    gas_cf = sup.cf["Natural gas"]; gas_cap_2030 = sup.existing["Natural gas"] - sup.retire["Natural gas"]
    p50e = float(summ[(summ.iepr_case == "all cases") & (summ.metric == "gap_energy_twh")].p50.iloc[0]); p95e = float(summ[(summ.iepr_case == "all cases") & (summ.metric == "gap_energy_twh")].p95.iloc[0])
    key = {"base_supply": base, "in_state_2025_actual_twh": sup.in_state_2025_twh, "gas_capacity_2030_mw": float(gas_cap_2030), "gas_cf_2023_2025": float(gas_cf),
           "gas_cf_to_close_p50_energy_gap": float(gas_cf + p50e * 1000 / (gas_cap_2030 * 8.76)), "gas_cf_to_close_p95_energy_gap": float(gas_cf + p95e * 1000 / (gas_cap_2030 * 8.76)),
           "draws": int(len(draws)), "seed": 20260922}
    (PROCESSED / "ch4_mc_key_numbers.json").write_text(json.dumps(key, indent=1, default=float))
    allc = summ[summ.iepr_case == "all cases"].set_index("metric")
    print(f"   energy gap 2030 (TWh): P5 {allc.loc['gap_energy_twh','p05']:.0f}, P50 {allc.loc['gap_energy_twh','p50']:.0f}, P95 {allc.loc['gap_energy_twh','p95']:.0f}; peak gap (MW): P5 {allc.loc['gap_peak_mw','p05']:,.0f}, P50 {allc.loc['gap_peak_mw','p50']:,.0f}, P95 {allc.loc['gap_peak_mw','p95']:,.0f}")
    print(f"   upper bound: energy gap {ub.gap_energy_twh.min():.0f}-{ub.gap_energy_twh.max():.0f} TWh, peak gap {ub.gap_peak_mw.min()/1000:.1f}-{ub.gap_peak_mw.max()/1000:.1f} GW; gas CF to close P50 gap {key['gas_cf_to_close_p50_energy_gap']:.2f}")
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.6), constrained_layout=True)
    for ax, col, unit, div in ((axes[0, 0], "gap_energy_twh", "TWh", 1), (axes[0, 1], "gap_peak_mw", "GW", 1000)):
        v = draws[col] / div; ax.hist(v, bins=60, color="#2c7bb6", alpha=0.85)
        for pct, ls in ((5, ":"), (50, "-"), (95, ":")):
            ax.axvline(np.percentile(v, pct), color="k", ls=ls, lw=1)
        ubv = ub[col] / div
        ax.text(0.98, 0.96, f"P5 {np.percentile(v,5):,.0f}  P50 {np.percentile(v,50):,.0f}  P95 {np.percentile(v,95):,.0f} {unit}\nmean {v.mean():,.0f}; share above zero {100*(v>0).mean():.0f}%\nupper bound (every MW, flat): {ubv.min():,.0f} to {ubv.max():,.0f} {unit}", transform=ax.transAxes, ha="right", va="top", fontsize=7, bbox=BOX)
        ax.set_xlabel(f"2030 {'energy' if 'energy' in col else 'net-peak'} gap ({unit}): demand growth minus supply growth, 2025 to 2030" + ("" if "energy" in col else ", with reserve margin"), fontsize=8)
        ax.set_ylabel("draws"); ax.set_title(f"{'Energy' if 'energy' in col else 'Net-peak'} gap in 2030, all 10,000 draws", fontsize=9)
    for ax, col, unit, div in ((axes[1, 0], "gap_energy_twh", "TWh", 1), (axes[1, 1], "gap_peak_mw", "GW", 1000)):
        data = [draws.loc[draws.case_name == c, col] / div for c in g.CASE_NAMES]
        bp = ax.boxplot(data, whis=(5, 95), showfliers=False, widths=0.55, patch_artist=True)
        for patch, colr in zip(bp["boxes"], ("#a6d96a", "#fdae61", "#d7191c")):
            patch.set_facecolor(colr); patch.set_alpha(0.7)
        ax.set_xticks([1, 2, 3]); ax.set_xticklabels([f"{c} ({s_})" for c, s_ in zip(gs.case.iloc[:3], gs.scenario.iloc[:3])], fontsize=8)
        for i, d in enumerate(data, 1):
            ax.text(i, np.percentile(d, 95) + (0.02 * (ax.get_ylim()[1] - ax.get_ylim()[0])), f"P50 {np.percentile(d,50):,.0f}\nP5-P95 {np.percentile(d,5):,.0f} to {np.percentile(d,95):,.0f}", ha="center", fontsize=6.8, bbox=BOX)
        ax.set_ylabel(unit); ax.set_title(f"{'Energy' if 'energy' in col else 'Net-peak'} gap by IEPR growth case (boxes P25-P75, whiskers P5-P95)", fontsize=9)
        ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[1] * 1.25)
    save(fig, "fig4_02_gap_distributions")

    # ------------------------------------------------------------ 5. sensitivity: tornado and Sobol
    print("5. Sensitivity: one-at-a-time tornado and Sobol indices")
    tor = g.tornado(tiers, gs, sup, inputs, draws); tor.to_csv(PROCESSED / "ch4_tornado.csv", index=False)
    sob = g.sobol_indices(tiers, gs, sup, inputs, draws, n_base=1024); sob.to_csv(PROCESSED / "ch4_sobol.csv", index=False)
    print("   largest energy-gap swings: " + "; ".join(f"{r.input} {r.swing_energy:.0f} TWh" for r in tor.head(4).itertuples()))
    print("   Sobol total-order, energy gap: " + "; ".join(f"{r.input} {r.ST:.2f}" for r in sob[sob.metric == 'gap_energy_twh'].sort_values('ST', ascending=False).head(4).itertuples()))
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.2), constrained_layout=True)
    for ax, metric, unit, div, lo, hi, basec in ((axes[0, 0], "energy", "TWh", 1, "gap_energy_low", "gap_energy_high", "base_gap_energy"), (axes[0, 1], "peak", "GW", 1000, "gap_peak_low", "gap_peak_high", "base_gap_peak")):
        t = tor.sort_values(f"swing_{metric}", ascending=True)
        b0 = t[basec].iloc[0] / div
        y = np.arange(len(t))
        ax.barh(y, t[lo] / div - b0, left=b0, color="#a6d96a", label="input at its 5th percentile (or low case)")
        ax.barh(y, t[hi] / div - b0, left=b0, color="#d7191c", alpha=0.75, label="input at its 95th percentile (or high case)")
        ax.set_yticks(y); ax.set_yticklabels([f"{r.input} [{r.low_value:.2g} to {r.high_value:.2g}] -> {getattr(r, lo)/div:,.{0 if div == 1 else 1}f} | {getattr(r, hi)/div:,.{0 if div == 1 else 1}f}" for r in t.itertuples()], fontsize=6.8)
        ax.axvline(b0, color="k", lw=0.8); ax.set_xlabel(f"2030 {metric} gap ({unit}); all other inputs at their medians (base {b0:,.{0 if div == 1 else 1}f} {unit})", fontsize=8)
        ax.set_title(f"One-at-a-time swings, {metric} gap", fontsize=9)
        ax.legend(fontsize=6.5, loc="lower right")
    for ax, metric in ((axes[1, 0], "gap_energy_twh"), (axes[1, 1], "gap_peak_mw")):
        sb = sob[sob.metric == metric].sort_values("ST", ascending=True)
        y = np.arange(len(sb)); ax.barh(y - 0.18, sb.S1, 0.36, color="#2c7bb6", label="first-order S1"); ax.barh(y + 0.18, sb.ST, 0.36, color="#fdae61", label="total-order ST")
        ax.set_yticks(y); ax.set_yticklabels(sb.input, fontsize=7)
        for yi, r in zip(y, sb.itertuples()):
            ax.text(max(r.S1, r.ST) + 0.01, yi, f"{r.ST:.2f}", va="center", fontsize=6.3)
        ax.set_xlim(0, max(0.5, sb.ST.max() * 1.25)); ax.set_xlabel(f"Sobol index, {'energy' if 'energy' in metric else 'peak'} gap ({int(sb.n_evaluations.iloc[0]):,} evaluations, SALib)")
        ax.set_title(f"Sobol indices, {'energy' if 'energy' in metric else 'peak'} gap (sum of S1 = {sb.S1.sum():.2f})", fontsize=9); ax.legend(fontsize=6.5, loc="lower right")
    save(fig, "fig4_03_sensitivity")

    # ------------------------------------------------------------ 6. RQ4: curtailment-enabled headroom
    print("6. Headroom: Duke replication on CAISO hourly load 2019-2025")
    dem = pd.read_parquet(PROCESSED / "ciso_hourly_2019_2025_clean.parquet")["demand"]
    variants = {"Duke seasons (Nov-Feb winter), 2019-2025": dict(), "Dec-Feb winter, 2019-2025": dict(winter_months=(12, 1, 2)), "single annual threshold, 2019-2025": dict(winter_months=(99,)),
                "Duke seasons, 2022-2025 only": dict(years=[2022, 2023, 2024, 2025])}
    curves, summs, dets = {}, [], []
    for name, kw in variants.items():
        c, s_, d_ = g.headroom(dem, **kw); curves[name] = c; s_["variant"] = name; summs.append(s_); d_["variant"] = name; dets.append(d_)
    hs = pd.concat(summs, ignore_index=True); hs.to_csv(PROCESSED / "ch4_headroom_summary.csv", index=False)
    hd = pd.concat(dets, ignore_index=True); hd.to_csv(PROCESSED / "ch4_headroom_detail.csv", index=False)
    cv = pd.concat([c.assign(variant=k) for k, c in curves.items()], ignore_index=True); cv.to_csv(PROCESSED / "ch4_headroom_curve.csv", index=False)
    hby = g.headroom_by_year(dem); hby.to_csv(PROCESSED / "ch4_headroom_by_year.csv", index=False)
    hb = hby[(hby.variant.str.startswith("Duke")) & (hby.limit == 0.005)]
    print(f"   per-year headroom at 0.5% (Duke seasons): hours criterion {hb.headroom_hours_criterion_mw.min()/1000:.1f}-{hb.headroom_hours_criterion_mw.max()/1000:.1f} GW, energy criterion {hb.headroom_energy_criterion_mw.min()/1000:.1f}-{hb.headroom_energy_criterion_mw.max()/1000:.1f} GW")
    main_var = "Duke seasons (Nov-Feb winter), 2019-2025"; hm = hs[hs.variant == main_var].set_index("limit").headroom_mw
    # headroom against the gap
    pk = summ[(summ.metric == "gap_peak_mw")].set_index("iepr_case")
    rows = []
    for lim, hv in hm.items():
        rows.append({"limit": lim, "headroom_mw": hv, "duke_caiso_mw": g.DUKE_CAISO.get(lim, np.nan) * 1000 if lim in g.DUKE_CAISO else np.nan,
                     **{f"share_of_dc_{k}": hv / float(cases.set_index('case').loc[c_, 'dc_peak_mw_2030']) for k, c_ in (("cec_central", "CEC central (Planning forecast, published)"), ("cec_high", "CEC high (Local Reliability, published)"), ("ercot", "ERCOT-calibrated stock-flow"), ("pjm_firm", "PJM-style: firm only (signed agreements)"), ("upper_bound", "Upper bound: every MW builds, flat load"))},
                     "share_of_peak_gap_p50": hv / float(pk.loc["all cases", "p50"]), "share_of_peak_gap_p95": hv / float(pk.loc["all cases", "p95"]), "share_of_upper_bound_peak_gap": hv / float(ub.gap_peak_mw.max())})
    hvg = pd.DataFrame(rows); hvg.to_csv(PROCESSED / "ch4_headroom_vs_gap.csv", index=False)
    # energy-side argument: negative-price hours and curtailment
    ps = pd.read_csv(PROCESSED / "ch1_price_stats.csv"); cur = pd.read_csv(PROCESSED / "ch3_caiso_curtailment_annual.csv").set_index("year")
    es = []
    for _, r in ps[(ps.full_year) & (ps.year.isin([2024, 2025]))].iterrows():
        es.append({"item": f"{r.label} hours with negative day-ahead price, {int(r.year)}", "value": float(r.hours_negative), "unit": "hours", "midday_share_pct": 100 * float(r.neg_hours_10_16_share), "flexible_1gw_energy_gwh": float(r.hours_negative) * 1.0, "source": "ch1_price_stats"})
    for y in (2024, 2025):
        es.append({"item": f"CAISO wind and solar curtailment, {y}", "value": float(cur.loc[y, "curtailed_gwh"]), "unit": "GWh", "flexible_1gw_energy_gwh": np.nan, "source": "ch3_caiso_curtailment_annual"})
    es.append({"item": "CAISO wind and solar curtailment, Jan-Aug 2026", "value": float(cur.loc[2026, "curtailed_gwh"]), "unit": "GWh", "flexible_1gw_energy_gwh": np.nan, "source": "ch3_caiso_curtailment_annual"})
    es.append({"item": "flat load equivalent of 2025 curtailment (GWh / 8,760 h)", "value": float(cur.loc[2025, "curtailed_gwh"] / 8.76), "unit": "MW", "flexible_1gw_energy_gwh": np.nan, "source": "derived"})
    esd = pd.DataFrame(es); esd.to_csv(PROCESSED / "ch4_energy_side.csv", index=False)
    print("   headroom (Duke seasons) at 0.25/0.5/1/5%: " + ", ".join(f"{v/1000:.1f}" for v in hm.values) + " GW vs Duke CAISO 4.2/5.0/5.9 GW")
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 10), constrained_layout=True); axes = axes.ravel()
    ax = axes[0]
    for (name, c), col, ls in zip(curves.items(), ("#d7191c", "#2c7bb6", "#7b3294", "#fdae61"), ("-", "--", "-.", ":")):
        cc_ = c[c.avg_curtailment_rate <= 0.2]; ax.plot(cc_.load_addition_mw / 1000, 100 * cc_.avg_curtailment_rate, color=col, ls=ls, lw=1.4, label=name)
    for lim in (0.0025, 0.005, 0.01, 0.05):
        ax.axhline(100 * lim, color="grey", lw=0.6)
    for lim, gw in g.DUKE_CAISO.items():
        ax.plot(gw, 100 * lim, "k*", ms=9, label="Duke CAISO value" if lim == 0.0025 else None)
    ax.set_yscale("log"); ax.set_ylim(0.05, 80); ax.set_xlim(0, 20); ax.set_xlabel("constant load addition (GW)"); ax.set_ylabel("average annual curtailment of the new load (%)")
    ax.text(0.02, 0.97, "headroom, Duke seasons 2019-2025:\n" + ", ".join(f"{100*l:g}% -> {v/1000:.1f} GW" for l, v in hm.items()) + f"\nDuke (2016-2024): 0.25% 4.2, 0.5% 5.0, 1% 5.9 GW\nthresholds: winter {hs.winter_threshold_mw.iloc[0]:,.0f} MW, other months {hs.summer_threshold_mw.iloc[0]:,.0f} MW", transform=ax.transAxes, va="top", fontsize=6.6, bbox=BOX)
    ax.set_title("Curtailment-enabled headroom on CAISO hourly demand (all years pooled)", fontsize=9); ax.legend(fontsize=6.3, loc="lower right")
    ax = axes[1]
    hbd = hby[hby.variant.str.startswith("Duke")]
    for lim, col in ((0.0025, "#a6d96a"), (0.005, "#fdae61"), (0.01, "#d7191c")):
        sub = hbd[hbd.limit == lim]
        ax.plot(sub.year.astype(int), sub.headroom_energy_criterion_mw / 1000, "-o", ms=4, color=col, label=f"{100*lim:g}% of energy (Duke criterion)")
        ax.plot(sub.year.astype(int), sub.headroom_hours_criterion_mw / 1000, "--s", ms=4, color=col, label=f"{100*lim:g}% of hours above the peak")
        for yv, v in zip(sub.year.astype(int), sub.headroom_energy_criterion_mw / 1000):
            ax.text(yv, v + 0.15, f"{v:.1f}", ha="center", fontsize=5.8, color=col)
    ax.set_xticks(sorted(hbd.year.astype(int).unique())); ax.set_ylabel("headroom (GW)"); ax.set_xlabel("year")
    ax.set_title("Headroom solved year by year, Duke seasonal thresholds", fontsize=9); ax.legend(fontsize=6, ncol=2, loc="upper left")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.3)
    h05 = hbd[hbd.limit == 0.005]
    ax.text(0.98, 0.04, f"0.5%: energy criterion {h05.headroom_energy_criterion_mw.min()/1000:.1f} to {h05.headroom_energy_criterion_mw.max()/1000:.1f} GW by year (pooled {hm[0.005]/1000:.1f});\nhours criterion {h05.headroom_hours_criterion_mw.min()/1000:.1f} to {h05.headroom_hours_criterion_mw.max()/1000:.1f} GW", transform=ax.transAxes, ha="right", va="bottom", fontsize=6.6, bbox=BOX)
    ax = axes[2]
    d05 = hd[(hd.variant == main_var) & (hd.limit == 0.005)]
    ax.bar(d05.year.astype(int), d05.hours_curtailed, color="#2c7bb6")
    for yv, hv in zip(d05.year.astype(int), d05.hours_curtailed):
        ax.text(yv, hv + 4, f"{hv:.0f} h", ha="center", fontsize=6.5)
    ax.set_xticks(d05.year.astype(int).tolist()); ax.set_ylim(0, d05.hours_curtailed.max() * 1.45); ax.set_ylabel("hours with any curtailment"); ax.set_xlabel("year")
    ax.set_title(f"Hours curtailed at the 0.5% headroom ({hm[0.005]/1000:.1f} GW)", fontsize=9)
    ax.text(0.02, 0.97, f"mean {d05.hours_curtailed.mean():.0f} h/yr; {100*d05.share_winter.min():.0f} to {100*d05.share_winter.max():.0f}% of curtailed energy in Nov-Feb;\nhours with less than half of the load available: {d05.hours_below_50pct.mean():.0f}/yr;\nlargest single-hour cut {d05.max_curtailment_mw.max()/1000:.1f} GW of {hm[0.005]/1000:.1f} GW", transform=ax.transAxes, va="top", fontsize=6.6, bbox=BOX)
    ax = axes[3]
    items = [(f"headroom {100*l:g}%", v / 1000, "#2c7bb6") for l, v in hm.items()] + [("CEC central DC", cases.set_index("case").loc["CEC central (Planning forecast, published)", "dc_peak_mw_2030"] / 1000, "#bdbdbd"),
             ("ERCOT-calibrated DC", cases.set_index("case").loc["ERCOT-calibrated stock-flow", "dc_peak_mw_2030"] / 1000, "#bdbdbd"), ("PJM firm DC", cases.set_index("case").loc["PJM-style: firm only (signed agreements)", "dc_peak_mw_2030"] / 1000, "#bdbdbd"),
             ("CEC high DC", cases.set_index("case").loc["CEC high (Local Reliability, published)", "dc_peak_mw_2030"] / 1000, "#bdbdbd"), ("peak gap P50", pk.loc["all cases", "p50"] / 1000, "#fdae61"), ("peak gap P95", pk.loc["all cases", "p95"] / 1000, "#fdae61"),
             ("upper bound DC", cases.set_index("case").loc["Upper bound: every MW builds, flat load", "dc_peak_mw_2030"] / 1000, "#d7191c"), ("upper bound peak gap", ub.gap_peak_mw.max() / 1000, "#d7191c")]
    y = np.arange(len(items))[::-1]
    ax.barh(y, [v for _, v, _ in items], color=[c for _, _, c in items])
    ax.set_yticks(y); ax.set_yticklabels([k for k, _, _ in items], fontsize=7)
    for yi, (_, v, _) in zip(y, items):
        ax.text(v + 0.3, yi, f"{v:.1f}", va="center", fontsize=6.8)
    ax.set_xlabel("GW"); ax.set_xlim(0, max(v for _, v, _ in items) * 1.15); ax.set_title("Headroom against the data center cases and the gap", fontsize=9)
    save(fig, "fig4_04_headroom")

    # ------------------------------------------------------------ 7. RQ3: regimes crosswalk and the ERCOT queue figure
    print("7. Regime crosswalk, taxonomy, headline numbers, ERCOT queue figure")
    cw = rg.crosswalk_matrix(); cw.to_csv(PROCESSED / "ch4_regime_crosswalk.csv", index=False)
    tax = rg.common_taxonomy(); tax.to_csv(PROCESSED / "ch4_common_taxonomy.csv", index=False)
    sz = rg.sce_size_classes(); sz.to_csv(PROCESSED / "ch4_sce_size_classes.csv", index=False)
    hl = rg.headline_by_regime(tiers, cases, sz, chain); hl.to_csv(PROCESSED / "ch4_headline_by_regime.csv", index=False)
    scores = rg.regime_scores(); scores.to_csv(PROCESSED / "ch4_regime_scores.csv", index=False)
    pd.DataFrame([{"criterion": k, "rubric": v} for k, v in rg.RUBRIC.items()]).to_csv(PROCESSED / "ch4_regime_rubric.csv", index=False)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    M = scores.set_index("regime")[rg.CRITERIA]
    im = ax.imshow(M.values, cmap="YlGnBu", vmin=0, vmax=3, aspect="auto")
    ax.set_xticks(range(len(rg.CRITERIA))); ax.set_xticklabels([c.replace("_", " ") for c in rg.CRITERIA], fontsize=8)
    ax.set_yticks(range(len(M))); ax.set_yticklabels([f"{r}  (total {t})" for r, t in zip(M.index, scores.total)], fontsize=8); ax.grid(False)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, str(int(M.values[i, j])), ha="center", va="center", fontsize=9, color="white" if M.values[i, j] >= 2 else "black")
    cb = fig.colorbar(im, ax=ax, ticks=[0, 1, 2, 3], fraction=0.03); cb.set_label("score (0 none to 3 strongest)", fontsize=8)
    ax.set_title("Scored crosswalk of six large-load data and measurement regimes (rubric in the table note)", fontsize=9)
    save(fig, "fig4_07_regime_scores")
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.0), gridspec_kw={"width_ratios": [1.25, 0.95, 1.3]})
    ax = axes[0]
    qq = q.drop_duplicates("month", keep="last").copy(); qq["t"] = pd.to_datetime(qq.month)
    ax.bar(qq.t, qq.standalone_mw / 1000, width=20, color="#5f6b73", label="standalone")
    ax.bar(qq.t, qq.colocated_mw / 1000, width=20, bottom=qq.standalone_mw / 1000, color="#17becf", label="co-located with generation")
    for t_, v in zip(qq.t, qq.total_mw):
        ax.text(t_, v / 1000 + 4, f"{v/1000:.0f}", ha="center", fontsize=6)
    nn = n[(n.metric == "tracked large load requests") & (n.as_of >= "2026-03-26")].copy(); nn["t"] = pd.to_datetime(nn.as_of)
    ax.plot(nn.t, nn.mw / 1000, "o", color="#d7191c", label="later totals (text and charts)")
    for t_, v in zip(nn.t, nn.mw):
        ax.text(t_, v / 1000 + 8, f"{v/1000:.0f}", ha="center", fontsize=6, color="#d7191c")
    dec24 = n[(n.as_of == "2024-12-31")].mw.iloc[0]; ax.plot(pd.Timestamp("2024-12-31"), dec24 / 1000, "o", color="#d7191c"); ax.text(pd.Timestamp("2024-12-31"), dec24 / 1000 - 22, f"{dec24/1000:.0f}", ha="center", fontsize=6, color="#d7191c")
    ax.set_ylabel("GW"); ax.set_title("ERCOT tracked large-load requests by month (GW)", fontsize=9); ax.legend(fontsize=6.5, loc="upper left")
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10))); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    nmax = nn.loc[nn.mw.idxmax()]
    ax.text(0.98, 0.04, f"Dec 2024 {dec24/1000:.0f} GW -> Mar 2026 {qq.total_mw.iloc[-1]/1000:.0f} GW before the\nMarch 2026 submissions -> {nmax.mw/1000:.0f} GW by {pd.Timestamp(nmax.as_of):%b %Y}", transform=ax.transAxes, ha="right", va="bottom", fontsize=6.6, bbox=BOX)
    ax = axes[1]
    aa = a.copy(); aa["t"] = pd.to_datetime(aa.month)
    ax.plot(aa.t, aa.planning_studies_approved_mw / 1000, "-o", ms=3, color="#5f6b73", label="planning studies approved")
    ax.plot(aa.t, aa.approved_to_energize_mw / 1000, "-o", ms=3, color="#17becf", label="approved to energize")
    obs = n[n.metric == "observed monthly non-simultaneous peak"].copy(); obs["t"] = pd.to_datetime(obs.as_of)
    ax.plot(obs.t, obs.mw / 1000, "s", color="#2ca02c", label="observed monthly peak of approved loads")
    a2e_late = n[(n.metric == "approved to energize") & (n.as_of > "2026-03-31")].copy(); a2e_late["t"] = pd.to_datetime(a2e_late.as_of); ax.plot(a2e_late.t, a2e_late.mw / 1000, "o", color="#17becf")
    ax.set_ylabel("GW"); ax.set_title("ERCOT approvals and observed load (GW)", fontsize=9); ax.legend(fontsize=6.5, loc="upper left")
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10))); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.text(0.98, 0.04, f"approved to energize {aa.approved_to_energize_mw.iloc[0]/1000:.1f} (May 2025) -> {aa.approved_to_energize_mw.iloc[-1]/1000:.1f} (Mar 2026) -> {a2e_late.mw.iloc[-1]/1000:.1f} GW (Aug 2026)\nobserved monthly peak {obs.mw.iloc[0]/1000:.1f} (Jan 2026) -> {obs.mw.iloc[-1]/1000:.1f} GW (Aug 2026)\nmonthly hazards: " + "; ".join(f"{100*r.monthly_hazard:.1f}%" for r in rates.itertuples()) + " (see table)", transform=ax.transAxes, ha="right", va="bottom", fontsize=6.2, bbox=BOX)
    ax.set_ylim(0, aa.planning_studies_approved_mw.max() / 1000 * 1.35)
    ax = axes[2]
    snaps = s.groupby(["snapshot", "as_of"]).in_service_year_through.max().reset_index().sort_values("as_of").reset_index(drop=True)
    short = {"TAC report": "TAC report", "House hearing": "House hearing", "ERCOT Monthly": "Monthly", "Board": "Board deck", "Operational overview": "Ops. overview"}
    labels, bottoms = [], np.zeros(len(snaps))
    xs = np.arange(len(snaps))
    for st in g.ERCOT_STATUSES:
        vals = np.array([s[(s.snapshot == r.snapshot) & (s.as_of == r.as_of) & (s.status == st) & (s.in_service_year_through == r.in_service_year_through)].mw.iloc[0] for r in snaps.itertuples()]) / 1000
        ax.bar(xs, vals, bottom=bottoms, color=STATUS_COL[st], label=st, edgecolor="white", lw=0.4); bottoms += vals
    for xi, tot in zip(xs, bottoms):
        ax.text(xi, tot + 5, f"{tot:.0f}", ha="center", fontsize=6.5)
    ax.set_xticks(xs); ax.set_xticklabels([f"{short[r.snapshot]}\n{pd.Timestamp(r.as_of):%b %d}\n{pd.Timestamp(r.as_of):%Y}\nto {r.in_service_year_through}" for r in snaps.itertuples()], fontsize=6)
    ax.set_ylim(0, bottoms.max() * 1.12); ax.set_ylabel("GW"); ax.set_title("ERCOT queue by status at each snapshot (GW)", fontsize=9); ax.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
    save(fig, "fig4_05_ercot_queue")

    # ------------------------------------------------------------ 8. optional: emissions of flat versus curtailable load
    print("8. Emissions of a flat versus a curtailable load")
    em = g.flat_vs_flexible_emissions(); em.to_csv(PROCESSED / "ch4_emissions_flat_vs_flexible.csv", index=False)
    co2 = pd.read_parquet(PROCESSED / "caiso_co2_intensity_hourly.parquet"); co2 = co2[co2.valid_hour & (co2.year == 2025)]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))
    ax = axes[0]
    I = np.sort(co2.intensity_accounting_g_per_kWh.values)[::-1]; xx = np.arange(1, len(I) + 1)
    ax.plot(xx, I, color="#2c7bb6", lw=1.2); k = int(round(0.25 * len(I)))
    ax.fill_between(xx[:k], I[:k], color="#d7191c", alpha=0.25, label="highest-intensity 25% of hours (curtailed or shifted)")
    ax.fill_between(xx[-k:], I[-k:], color="#a6d96a", alpha=0.4, label="lowest-intensity 25% of hours (receive the shifted energy)")
    ax.set_xlabel("hours of 2025, sorted by CO2 accounting intensity"); ax.set_ylabel("g CO2 per kWh (= t per GWh)"); ax.set_title("CAISO hourly intensity, 2025", fontsize=9); ax.legend(fontsize=6.5)
    ax.text(0.98, 0.7, f"annual mean {I.mean():.0f}; top 25% mean {I[:k].mean():.0f}; bottom 25% mean {I[-k:].mean():.0f} g/kWh", transform=ax.transAxes, ha="right", fontsize=6.8, bbox=BOX)
    ax = axes[1]
    piv = em.pivot_table(index=["strategy", "share_hours"], columns="year", values="t_per_gwh")
    order = [("flat", 0.0)] + [(s_, sh) for sh in (0.05, 0.10, 0.25) for s_ in ("curtail", "shift")]
    piv = piv.loc[order]; w = 0.27
    for j, y in enumerate(piv.columns):
        ax.bar(np.arange(len(piv)) + (j - 1) * w, piv[y], w, label=str(y), color=["#bdbdbd", "#fdae61", "#2c7bb6"][j])
        for xi, v in zip(np.arange(len(piv)) + (j - 1) * w, piv[y]):
            ax.text(xi, v + 2, f"{v:.0f}", ha="center", fontsize=5.6)
    ax.set_xticks(np.arange(len(piv))); ax.set_xticklabels([f"{s_}\n{100*sh:.0f}%" if s_ != "flat" else "flat" for s_, sh in piv.index], fontsize=7)
    ax.set_ylim(0, 300); ax.set_xlabel("strategy and share of hours affected"); ax.set_ylabel("t CO2 per GWh consumed"); ax.set_title("Emissions intensity of a 1 MW load: flat, curtailed, or shifted", fontsize=9); ax.legend(fontsize=7, title="year", loc="upper right")
    f25 = piv.loc[("flat", 0.0), 2025]; s25 = piv.loc[("shift", 0.25), 2025]; c25 = piv.loc[("curtail", 0.25), 2025]
    ax.text(0.02, 0.97, f"2025: flat {f25:.0f}; curtail 25% of hours {c25:.0f} ({100*(1-c25/f25):.0f}% lower);\nshift the same energy {s25:.0f} ({100*(1-s25/f25):.0f}% lower)", transform=ax.transAxes, va="top", fontsize=6.8, bbox=BOX)
    save(fig, "fig4_06_emissions_flat_vs_flexible")
    print("done")
    # ------------------------------------------------------------ 9. data centers as a share of California's electricity: history, the forecast cases and the bound
    print("9. Data centers as a share of California's electricity, 2023 to 2040")
    est = pd.read_csv(PROCESSED / "ch1_dc_load_estimates.csv")
    a_row = est[est.group.str.startswith("A.")].iloc[0]; b_row = est[est.group.str.startswith("B.")].iloc[0]
    ex_lo, ex_mid, ex_hi = float(min(a_row.low_TWh, b_row.low_TWh)), float(b_row.central_TWh), float(max(a_row.high_TWh, b_row.high_TWh))
    dce_s = pd.read_csv(PROCESSED / "ch4_ced2025_data_center_energy.csv"); scen_s = pd.read_csv(PROCESSED / "ch4_ced2025_scenarios.csv")
    sw = scen_s[scen_s.metric == "energy_statewide_GWh"].pivot(index="year", columns="scenario", values="value") / 1e3
    srows = []
    for sc in ("Planning", "Local Reliability"):
        d = dce_s[dce_s.scenario == sc].set_index("year").data_center_gwh / 1e3
        for y, v in d.items():
            tot = float(sw.loc[y, sc])
            srows.append(dict(series=f"CED 2025 {sc}: existing plus forecast additions", year=int(y), dc_added_twh=float(v), dc_total_low_twh=ex_lo + v, dc_total_mid_twh=ex_mid + v, dc_total_high_twh=ex_hi + v,
                              denominator_twh=tot, denominator=f"statewide energy to serve load, {sc} (Form 1.5a)", share_low_pct=100 * (ex_lo + v) / tot, share_mid_pct=100 * (ex_mid + v) / tot, share_high_pct=100 * (ex_hi + v) / tot))
    for lab, r_, y in (("History: EPRI statewide estimate 2023", a_row, 2023), ("History: CEC ~1,000 MW converted, 2024 sales", b_row, 2024)):
        srows.append(dict(series=lab, year=y, dc_added_twh=0.0, dc_total_low_twh=float(r_.low_TWh), dc_total_mid_twh=float(r_.central_TWh), dc_total_high_twh=float(r_.high_TWh), denominator_twh=float(r_.retail_sales_TWh),
                          denominator=f"EIA-861 California retail sales {int(r_.denominator_year)}", share_low_pct=float(r_.low_share_pct), share_mid_pct=float(r_.central_share_pct), share_high_pct=float(r_.high_share_pct)))
    dcases = pd.read_csv(PROCESSED / "ch4_demand_cases_2030.csv")
    pl30 = float(sw.loc[2030, "Planning"]); dc30 = float(dce_s[(dce_s.scenario == "Planning") & (dce_s.year == 2030)].data_center_gwh.iloc[0]) / 1e3
    for lab, key in (("Upper bound 2030: every MW builds, flat load", "Upper bound: every"), ("Upper bound 2030 at CEC utilization", "Upper bound at CEC")):
        v = float(dcases[dcases.case.str.startswith(key)].dc_energy_twh_2030.iloc[0]); den_lo, den_mid, den_hi = (pl30 - dc30 + v + e - ex_mid for e in (ex_lo, ex_mid, ex_hi))
        srows.append(dict(series=lab, year=2030, dc_added_twh=v, dc_total_low_twh=ex_lo + v, dc_total_mid_twh=ex_mid + v, dc_total_high_twh=ex_hi + v, denominator_twh=den_mid,
                          denominator="Planning 2030 non-data-center energy plus the bound", share_low_pct=100 * (ex_lo + v) / den_lo, share_mid_pct=100 * (ex_mid + v) / den_mid, share_high_pct=100 * (ex_hi + v) / den_hi))
    share = pd.DataFrame(srows); share.to_csv(PROCESSED / "ch4_dc_share_trajectory.csv", index=False)
    fig, ax = plt.subplots(figsize=(10, 5.4))
    for sc, col in (("Planning", "#1f77b4"), ("Local Reliability", "#d62728")):
        s_ = share[share.series.str.startswith(f"CED 2025 {sc}")].sort_values("year")
        ax.fill_between(s_.year, s_.share_low_pct, s_.share_high_pct, color=col, alpha=0.15)
        ax.plot(s_.year, s_.share_mid_pct, color=col, lw=2, marker="o", ms=4, label=f"CED 2025 {sc}: existing {ex_lo:.1f}-{ex_hi:.1f} TWh plus the forecast data center additions, over statewide energy to serve load")
        for y in (2030, 2040):
            r_ = s_[s_.year == y].iloc[0]; ax.annotate(f"{r_.share_mid_pct:.1f}%\n({r_.dc_total_mid_twh:.0f} of {r_.denominator_twh:.0f} TWh)", (y, r_.share_mid_pct), textcoords="offset points", xytext=(0, 9 if sc == "Local Reliability" else -24), ha="center", fontsize=7.8, color=col)
    hist = share[share.series.str.startswith("History")]
    ax.errorbar(hist.year, hist.share_mid_pct, yerr=[hist.share_mid_pct - hist.share_low_pct, hist.share_high_pct - hist.share_mid_pct], fmt="s", color="k", ms=6, capsize=3, label="history: EPRI 2023 estimate and the CEC ~1,000 MW converted, over EIA-861 retail sales")
    for r_ in hist.itertuples():
        ax.annotate(f"{r_.share_low_pct:.1f}-{r_.share_high_pct:.1f}%" if r_.share_low_pct != r_.share_high_pct else f"{r_.share_mid_pct:.1f}%", (r_.year, r_.share_high_pct), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7.8)
    ub = share[share.series.str.startswith("Upper bound")]
    ax.scatter(ub.year, ub.share_mid_pct, marker="^", s=70, color="#c1272d", zorder=5, label="upper bound 2030: every requested MW on line, flat load (top) or at the CEC's utilization (bottom)")
    for r_ in ub.itertuples():
        ax.annotate(f"{r_.share_mid_pct:.0f}%: {r_.dc_total_mid_twh:.0f} TWh of {r_.denominator_twh:.0f}", (2030, r_.share_mid_pct), textcoords="offset points", xytext=(8, -3), fontsize=7.8, color="#c1272d")
    ax.set_xlim(2022.5, 2040.8); ax.set_ylim(0, max(ub.share_mid_pct.max() * 1.12, 20)); ax.set_ylabel("data center share of California electricity (%)"); ax.set_xlabel("year")
    ax.set_xticks(list(range(2023, 2041, 1))); ax.set_xticklabels([str(y) if y % 2 == 1 else "" for y in range(2023, 2041)], fontsize=8)
    ax.set_title("Data centers as a share of California's electricity: history, the adopted forecast cases and the upper bound", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False)
    fig.subplots_adjust(bottom=0.27)
    save(fig, "fig4_08_dc_share_of_electricity")
    print("   2030 shares: " + "; ".join(f"{r.series.split(':')[0]} {r.share_mid_pct:.1f}%" for r in share[share.year == 2030].itertuples()))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
