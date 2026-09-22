#!/usr/bin/env python
"""Chapter 1 runner: builds every processed table and figure for 'Current status of data
centers and the grid'. Re-runnable; reads raw data through src/ch1_baseline.py.

Outputs
  data/processed/ch1_*.csv|parquet   tables (each with the manifest source ids used)
  figures/fig1_*.png|pdf             figures referenced by report/sections/02_current_status.tex
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src import ch1_baseline as c1  # noqa: E402
from src.paths import PROCESSED, FIGURES  # noqa: E402

plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 200, "font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})
YEARS = list(range(2019, 2026))
CMAP = plt.get_cmap("viridis")
YCOL = {y: CMAP(i / (len(YEARS) - 1)) for i, y in enumerate(YEARS)}


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGURES / f"{name}.png")
    fig.savefig(FIGURES / f"{name}.pdf")
    plt.close(fig)
    print("  figure", name)


def main() -> int:
    # ------------------------------------------------------------------ 1. EIA-930 baseline
    print("1. EIA-930 CISO hourly")
    hp = PROCESSED / "ciso_hourly_2019_2025.parquet"
    h = pd.read_parquet(hp) if hp.exists() else c1.load_eia930_ciso(2019, 2025)
    if not hp.exists():
        h.to_parquet(hp)
    cp0 = PROCESSED / "caiso_co2_intensity_hourly.parquet"
    ci0 = pd.read_parquet(cp0) if cp0.exists() else c1.load_caiso_outlook_hourly(2019, 2025)
    if not cp0.exists():
        ci0.to_parquet(cp0)
    fmp0 = PROCESSED / "caiso_fuelmix_hourly.parquet"
    fm0 = pd.read_parquet(fmp0) if fmp0.exists() else c1.load_caiso_fuelmix_hourly(2019, 2025)
    if not fmp0.exists():
        fm0.to_parquet(fmp0)
    h, flagged = c1.clean_demand_against_caiso(h, ci0, fuelmix_hourly=fm0)
    flagged.to_csv(PROCESSED / "ch1_eia930_flagged_hours.csv")
    # EIA-930 has no CISO interchange for 2024-07-02..2024-11-03 (any variant) and no hydro for parts of
    # 2019-2020: fill from CAISO's own five-minute series via per-year linear calibration and log it.
    h["imports"] = -h["interchange"]
    h, log_imp = c1.fill_from_caiso(h, "imports", fm0["imports"])
    h["interchange"] = -h["imports"]
    hydro_caiso = fm0["hydro_total"]
    h, log_hyd = c1.fill_from_caiso(h, "hydro", hydro_caiso)
    logs = [log_imp, log_hyd]
    for col, src in (("solar", "solar"), ("wind", "wind"), ("gas", "natural_gas"), ("nuclear", "nuclear")):
        if src in fm0:
            h, lg = c1.fill_from_caiso(h, col, fm0[src]); logs.append(lg)
    h["net_load"] = h["demand"] - h["solar"].fillna(0) - h["wind"].fillna(0)
    pd.concat(logs).to_csv(PROCESSED / "ch1_eia930_fill_log.csv", index=False)
    print(f"  filled {int(log_imp.n_filled.sum())} interchange hours, {int(log_hyd.n_filled.sum())} hydro hours and {int(sum(l.n_filled.sum() for l in logs[2:]))} fuel hours from CAISO series")
    h = c1.add_storage_adjusted(h, fm0)
    h.to_parquet(PROCESSED / "ciso_hourly_2019_2025_clean.parquet")
    print(f"  flagged {len(flagged)} EIA-930 hours as reporting artifacts (nulled)")
    summ = c1.annual_summary(h)
    g = h.groupby("year")
    summ["peak_demand_ex_storage_MW"] = g["demand_ex_storage"].max()
    summ["min_net_load_ex_storage_MW"] = g["net_load_ex_storage"].min()
    summ["storage_charging_TWh"] = (-(h["battery_caiso"].clip(upper=0))).groupby(h["year"]).sum() / 1e6
    summ.to_csv(PROCESSED / "ch1_ciso_annual_summary.csv")
    ldc = c1.duration_curves(h, "demand"); ldc.to_csv(PROCESSED / "ch1_load_duration_curves.csv")
    nldc = c1.duration_curves(h, "net_load"); nldc.to_csv(PROCESSED / "ch1_net_load_duration_curves.csv")
    prof = c1.seasonal_profiles(h); prof.to_csv(PROCESSED / "ch1_seasonal_profiles.csv", index=False)
    top = c1.top_hours(h, "net_load", 100); top.to_csv(PROCESSED / "ch1_top100_net_load_hours.csv", index=False)
    timing = c1.top_hours_timing(top); timing.to_csv(PROCESSED / "ch1_top100_net_load_timing.csv")
    topd = c1.top_hours(h, "demand", 100); topd.to_csv(PROCESSED / "ch1_top100_demand_hours.csv", index=False)
    c1.top_hours_timing(topd, "demand").to_csv(PROCESSED / "ch1_top100_demand_timing.csv")

    # Fig 1.1 load duration curves
    fig, ax = plt.subplots(figsize=(7, 4))
    for y in YEARS:
        ax.plot(ldc.index, ldc[y] / 1000, color=YCOL[y], label=str(y), lw=1.3)
    ax.set_xlabel("Percent of hours in year"); ax.set_ylabel("CAISO demand (GW)"); ax.set_title("Load duration curves, CAISO balancing authority, 2019-2025 (EIA-930)")
    ax.legend(ncol=4, fontsize=8); save(fig, "fig1_01_load_duration_curves")

    # Fig 1.2 net-load duration curves
    fig, ax = plt.subplots(figsize=(7, 4))
    for y in YEARS:
        ax.plot(nldc.index, nldc[y] / 1000, color=YCOL[y], label=str(y), lw=1.3)
    nl_ex = c1.duration_curves(h.rename(columns={"net_load_ex_storage": "nlx"}), "nlx")
    ax.plot(nl_ex.index, nl_ex[2025] / 1000, color=YCOL[2025], ls="--", lw=1.1, label="2025 excl. storage charging")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("Percent of hours in year"); ax.set_ylabel("Net load = demand - utility solar - wind (GW)")
    ax.set_title("Net-load duration curves, CAISO, 2019-2025"); ax.legend(ncol=4, fontsize=8); save(fig, "fig1_02_net_load_duration_curves")

    # Fig 1.3 seasonal average daily profiles: demand and net load, 2019 vs 2025
    fig, axes = plt.subplots(2, 4, figsize=(11, 5.2), sharex=True, sharey="row")
    for j, s in enumerate(c1.SEASON_ORDER):
        for y, ls in ((2019, "--"), (2022, ":"), (2025, "-")):
            g = prof[(prof.year == y) & (prof.season == s)]
            axes[0, j].plot(g.hour, g.demand / 1000, ls, color=YCOL[y], label=f"{y}", lw=1.4)
            axes[1, j].plot(g.hour, g.net_load / 1000, ls, color=YCOL[y], label=f"{y}", lw=1.4)
        axes[0, j].set_title(s); axes[1, j].set_xlabel("Hour of day (local, interval start)")
        axes[1, j].axhline(0, color="k", lw=0.5)
    axes[0, 0].set_ylabel("Demand (GW)"); axes[1, 0].set_ylabel("Net load (GW)"); axes[0, 0].legend(fontsize=8)
    fig.suptitle("Average daily profiles by season, CAISO: demand (top) and net load (bottom), 2019 / 2022 / 2025", y=1.0)
    save(fig, "fig1_03_seasonal_daily_profiles")

    # Fig 1.4 top-100 net-load hours timing: month x hour heatmaps per year
    fig, axes = plt.subplots(1, len(YEARS), figsize=(15, 3.8), sharey=True)
    for ax, y in zip(axes, YEARS):
        g = top[top.year == y]
        mat = pd.crosstab(g.hour, g.month).reindex(index=range(12, 24), columns=range(5, 11), fill_value=0)
        im = ax.imshow(mat.values, aspect="auto", cmap="magma_r", origin="lower", extent=[4.5, 10.5, 11.5, 23.5])
        for (i, hr), row in mat.iterrows() if False else []:
            pass
        ax.set_title(f"{y}\nmedian {int(timing.loc[y, 'median_hour'])}:00", fontsize=9); ax.set_xlabel("Month"); ax.set_xticks(range(5, 11))
    axes[0].set_ylabel("Hour of day (local, interval start)")
    fig.colorbar(im, ax=axes, shrink=0.8, label="count of top-100 net-load hours")
    fig.suptitle("When the 100 highest net-load hours occur, CAISO, by year", y=1.02)
    fig.savefig(FIGURES / "fig1_04_top100_net_load_timing.png", bbox_inches="tight"); fig.savefig(FIGURES / "fig1_04_top100_net_load_timing.pdf", bbox_inches="tight"); plt.close(fig); print("  figure fig1_04_top100_net_load_timing")

    # ------------------------------------------------------------------ 2. prices
    print("2. Day-ahead prices")
    pp = PROCESSED / "caiso_dam_lmp_hourly.parquet"
    p = pd.read_parquet(pp) if pp.exists() else c1.load_dam_lmp()
    if not pp.exists():
        p.to_parquet(pp)
    pst = c1.price_stats(p); pst.to_csv(PROCESSED / "ch1_price_stats.csv", index=False)
    pdc = c1.price_duration(p); pdc.to_csv(PROCESSED / "ch1_price_duration_curves.csv")
    nbm = c1.negative_hours_by_month(p); nbm.to_csv(PROCESSED / "ch1_negative_price_hours_by_month.csv")
    pbh = c1.price_by_hour(p); pbh.to_csv(PROCESSED / "ch1_price_by_hour_of_day.csv")
    ice = c1.ice_negative_days(); ice.to_csv(PROCESSED / "ch1_ice_daily_hub_prices_negative_days.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for node, lab in c1.DLAPS.items():
        for y, ls in ((2024, "--"), (2025, "-")):
            if (node, y) in pdc.columns:
                axes[0].plot(pdc.index, pdc[(node, y)], ls, label=f"{lab} {y}", lw=1.2)
    axes[0].axhline(0, color="k", lw=0.6); axes[0].set_ylim(-60, 250); axes[0].set_xlabel("Percent of hours in year"); axes[0].set_ylabel("Day-ahead LMP ($/MWh)")
    axes[0].set_title("Price duration curves, CAISO DLAPs, 2024 and 2025 (OASIS PRC_LMP DAM)"); axes[0].legend(fontsize=7)
    for node, lab in c1.DLAPS.items():
        g = pbh.xs(2025, level="year")[node]
        axes[1].plot(g.index, g.values, label=f"{lab} 2025")
        g = pbh.xs(2024, level="year")[node]
        axes[1].plot(g.index, g.values, "--", label=f"{lab} 2024", alpha=0.7)
    axes[1].axhline(0, color="k", lw=0.6); axes[1].set_xlabel("Hour of day (local)"); axes[1].set_ylabel("Mean day-ahead LMP ($/MWh)"); axes[1].set_title("Average day-ahead price by hour of day"); axes[1].legend(fontsize=7, ncol=2)
    save(fig, "fig1_05_price_duration_and_diurnal")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    d = pst[pst.node.isin(c1.DLAPS)].pivot(index="year", columns="label", values="hours_negative")
    d.plot.bar(ax=axes[0], rot=0); axes[0].set_ylim(0, 1350); axes[0].legend(title=None, fontsize=8, loc="upper left"); axes[0].set_ylabel("Hours with day-ahead LMP < $0"); axes[0].set_title("Negative-price hours per year by DLAP\n(2023 = Jul-Dec only; 2026 = Jan-Sep 22 only)")
    for node, lab in c1.DLAPS.items():
        g = nbm[node].unstack("year")
        for y in (2024, 2025, 2026):
            if y in g.columns:
                axes[1].plot(g.index, g[y], marker="o", ms=3, label=f"{lab} {y}", alpha=0.85 if y != 2026 else 0.6)
    axes[1].set_xlabel("Month"); axes[1].set_ylabel("Negative-price hours"); axes[1].set_title("Negative-price hours by month"); axes[1].set_ylim(0, 430); axes[1].legend(fontsize=6.5, ncol=3, loc="upper right")
    save(fig, "fig1_06_negative_price_hours")

    # ------------------------------------------------------------------ 3. carbon intensity
    print("3. Carbon intensity")
    cp = PROCESSED / "caiso_co2_intensity_hourly.parquet"
    ci = pd.read_parquet(cp) if cp.exists() else c1.load_caiso_outlook_hourly(2019, 2025)
    if not cp.exists():
        ci.to_parquet(cp)
    csum = c1.carbon_summary(ci); csum.to_csv(PROCESSED / "ch1_carbon_intensity_annual.csv")
    eg = c1.egrid_camx(); (PROCESSED / "ch1_egrid_camx_2023.json").write_text(json.dumps(eg, indent=1))
    diurnal = ci.groupby(["year", "season", "hour"])["intensity_g_per_kWh"].mean().reset_index(); diurnal.to_csv(PROCESSED / "ch1_carbon_intensity_diurnal.csv", index=False)
    cdc = c1.duration_curves(ci.rename(columns={"intensity_g_per_kWh": "ci"}), "ci"); cdc.to_csv(PROCESSED / "ch1_carbon_intensity_duration.csv")
    fmp = PROCESSED / "caiso_fuelmix_hourly.parquet"
    fm = pd.read_parquet(fmp) if fmp.exists() else c1.load_caiso_fuelmix_hourly(2019, 2025)
    if not fmp.exists():
        fm.to_parquet(fmp)
    bat = c1.battery_summary(fm); bat.to_csv(PROCESSED / "ch1_battery_summary.csv")

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    axes[0].plot(csum.index, csum.energy_weighted_g_per_kWh, marker="o", label="CAISO load-based, energy-weighted")
    axes[0].fill_between(csum.index, csum.p5_g_per_kWh, csum.p95_g_per_kWh, alpha=0.2, label="hourly 5th-95th percentile")
    axes[0].axhline(eg["co2_output_rate_g_per_kWh"], color="C3", ls="--", label=f"eGRID 2023 CAMX output rate ({eg['co2_output_rate_g_per_kWh']:.0f})")
    axes[0].set_ylabel("g CO2 per kWh"); axes[0].set_title("Annual carbon intensity of CAISO demand"); axes[0].legend(fontsize=7); axes[0].set_ylim(0, None)
    for y in YEARS:
        axes[1].plot(cdc.index, cdc[y], color=YCOL[y], label=str(y), lw=1.2)
    axes[1].set_xlabel("Percent of hours in year"); axes[1].set_ylabel("g CO2 per kWh"); axes[1].set_title("Hourly intensity duration curves"); axes[1].legend(fontsize=7, ncol=2)
    for s, ls in zip(c1.SEASON_ORDER, ("-", "--", ":", "-.")):
        g = diurnal[(diurnal.year == 2025) & (diurnal.season == s)]
        axes[2].plot(g.hour, g.intensity_g_per_kWh, ls, label=f"2025 {s}")
    g = diurnal[(diurnal.year == 2019)].groupby("hour")["intensity_g_per_kWh"].mean(); axes[2].plot(g.index, g.values, color="grey", lw=2, alpha=0.6, label="2019 all seasons")
    axes[2].set_xlabel("Hour of day (local)"); axes[2].set_title("Average diurnal intensity"); axes[2].set_ylim(0, 430); axes[2].legend(fontsize=7, ncol=3, loc="upper center")
    save(fig, "fig1_07_carbon_intensity")

    # ------------------------------------------------------------------ 4. existing data center load, four ways
    print("4. Existing data center load")
    rs = pd.DataFrame([c1.ca_retail_sales_eia861(y) for y in range(2019, 2025)]); rs.to_csv(PROCESSED / "ch1_ca_retail_sales_eia861.csv", index=False)
    retail_2024 = float(rs.loc[rs.year == 2024, "retail_sales_TWh"].iloc[0])
    svp = c1.svp_fact_sheet_energy(); svp.to_csv(PROCESSED / "ch1_svp_fact_sheets.csv", index=False)
    pts = c1.kollar_grady_california(); pts.to_csv(PROCESSED / "ch1_kollar_grady_points_california_flag.csv", index=False)
    n_ca, n_sc = int(pts.in_california.sum()), int(pts.santa_clara_12km.sum())
    e23 = float(svp.loc[svp.fact_sheet_year == 2023, "energy_GWh_est"].iloc[0]) / 1000
    epoch = pd.read_csv(c1.raw_path("epoch_data_centers"))
    n_epoch_ca = int(epoch["Address"].astype(str).str.contains(r", CA\b|California", regex=True).sum())
    bu = c1.bottom_up_estimate(n_ca, n_sc, svp_dc_peak_MW=0.55 * 746.0, n_epoch_ca=n_epoch_ca)
    est = c1.dc_load_estimates(retail_2024, 2024)
    est = pd.concat([est, pd.DataFrame([dict(method="Count-based bottom-up: Kollar-Grady facilities x avg load (Epoch: no CA sites)",
                                              low_TWh=bu["low_TWh"], central_TWh=bu["central_TWh"], high_TWh=bu["high_TWh"],
                                              basis=(f"{n_ca} Kollar-Grady facility points inside California ({n_sc} within 12 km of Santa Clara) plus {n_epoch_ca} Epoch AI frontier sites in California; "
                                                     f"average peak per facility {bu['avg_peak_MW_per_facility_svp_anchor']:.1f} MW (SVP anchor: 55% of a 746 MW system peak over 58 data centers) scaled 0.7/1.0/1.3; "
                                                     f"utilization 0.50/0.67/0.80 (SVP observed 64-67% of requested capacity); energy = count x peak x utilization x 8760"),
                                              source="kollar_grady_2025_zenodo; epoch_data_centers; svp_assembly_hearing_2026_01_28; cec_tn264908",
                                              retail_sales_TWh=retail_2024, retail_year=2024)])], ignore_index=True)
    for k in ("low", "central", "high"):
        est[f"{k}_share_pct"] = est[f"{k}_TWh"] / retail_2024 * 100
    order = ["EPRI 2024 state table (2023)", "CEC existing peak demand x load factor", "Count-based bottom-up: Kollar-Grady facilities x avg load (Epoch: no CA sites)", "Silicon Valley Power cluster only (lower bound)"]
    est["order"] = est.method.map({m: i for i, m in enumerate(order)}); est = est.sort_values("order").drop(columns="order").reset_index(drop=True)
    est.to_csv(PROCESSED / "ch1_dc_load_estimates.csv", index=False)
    (PROCESSED / "ch1_bottom_up_inputs.json").write_text(json.dumps(bu, indent=1))

    fig, ax = plt.subplots(figsize=(8.5, 3.9))
    ylab = ["EPRI 2024 state table\n(2023 consumption)", "CEC: 1,000 MW existing peak\nx load factor 0.80-0.95", "Count-based bottom-up: 321 Kollar-Grady\nfacilities x avg peak x utilization 0.5-0.8", "Silicon Valley Power cluster only\n(53-60% of SVP energy)"]
    for i, r in est.iterrows():
        ax.barh(i, r.high_TWh - r.low_TWh, left=r.low_TWh, height=0.5, color=["C0", "C1", "C2", "C3"][i], alpha=0.35)
        ax.plot([r.central_TWh], [i], "k|", ms=18, mew=2)
        ax.text(max(r.high_TWh, r.central_TWh) + 0.3, i, f"{r.low_TWh:.1f}-{r.high_TWh:.1f} TWh  ({r.low_share_pct:.1f}-{r.high_share_pct:.1f}%)" if r.high_TWh != r.low_TWh else f"{r.central_TWh:.1f} TWh  ({r.central_share_pct:.1f}%)", va="center", fontsize=8)
    ax.set_yticks(range(len(est))); ax.set_yticklabels(ylab, fontsize=8); ax.invert_yaxis()
    ax.set_xlabel(f"TWh per year (bottom axis); share of {retail_2024:.0f} TWh California retail sales, EIA-861 2024 (top axis)")
    ax.set_xlim(0, max(est.high_TWh) * 1.45); ax.set_title("Existing data center load in California, four estimates: the spread is the finding")
    sec = ax.secondary_xaxis("top", functions=(lambda x: x / retail_2024 * 100, lambda x: x * retail_2024 / 100)); sec.set_xlabel("Percent of California retail sales")
    save(fig, "fig1_08_existing_dc_load_estimates")

    # ------------------------------------------------------------------ 5. run record
    record = {"years": YEARS, "ciso_hours": int(len(h)), "lmp_hours": int(len(p)), "co2_hours": int(len(ci)),
              "retail_sales_2024_TWh": retail_2024, "kollar_grady_california_points": n_ca, "outputs": sorted(x.name for x in PROCESSED.glob("ch1_*"))}
    (PROCESSED / "ch1_run_record.json").write_text(json.dumps(record, indent=1, default=str))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
