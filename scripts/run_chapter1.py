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
from src.provenance import stamp  # noqa: E402

plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 200, "font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})
YEARS = list(range(2019, 2026))
CMAP = plt.get_cmap("viridis")
YCOL = {y: CMAP(i / (len(YEARS) - 1)) for i, y in enumerate(YEARS)}


def cached(path, loader, required_col):
    """Read a processed parquet cache, rebuilding it when it is missing or predates the current loader."""
    if path.exists():
        d = pd.read_parquet(path)
        if required_col in d.columns:
            return d
        print(f"  rebuilding stale cache {path.name}")
    d = loader(); d.to_parquet(path)
    return d


def save(fig, name):
    fig.tight_layout()
    stamp(fig, name)
    fig.savefig(FIGURES / f"{name}.png", bbox_inches="tight")
    fig.savefig(FIGURES / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  figure", name)


def main() -> int:
    # ------------------------------------------------------------------ 1. EIA-930 baseline
    print("1. EIA-930 CISO hourly")
    hp = PROCESSED / "ciso_hourly_2019_2025.parquet"
    h = pd.read_parquet(hp) if hp.exists() else c1.load_eia930_ciso(2019, 2025)
    if not hp.exists():
        h.to_parquet(hp)
    ci0 = cached(PROCESSED / "caiso_co2_intensity_hourly.parquet", lambda: c1.load_caiso_outlook_hourly(2019, 2025), "valid_hour")
    fm0 = cached(PROCESSED / "caiso_fuelmix_hourly.parquet", lambda: c1.load_caiso_fuelmix_hourly(2019, 2025), "n_intervals")
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
    vh = {y: int(summ.loc[y, "hours"]) for y in YEARS}
    for y in YEARS:
        ax.plot(ldc.index, ldc[y] / 1000, color=YCOL[y], label=f"{y} ({vh[y]:,} valid h)", lw=1.3)
    ax.set_xlabel("Percent of valid hours in year (hours flagged as reporting artifacts excluded)"); ax.set_ylabel("CAISO demand (GW)"); ax.set_title("Load duration curves, CAISO balancing authority, 2019-2025 (EIA-930 Adjusted demand)")
    pk = summ["peak_demand_MW"].idxmax(); pkt = pd.Timestamp(summ.loc[pk, "peak_demand_time"])
    ax.annotate(f"record hourly demand {summ.loc[pk, 'peak_demand_MW']/1000:.1f} GW\n{pkt:%b %-d, %Y} (hour ending {pkt:%H:%M})", xy=(0, summ.loc[pk, "peak_demand_MW"] / 1000), xytext=(14, 47), fontsize=7, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5), arrowprops=dict(arrowstyle="-", color="grey", lw=0.6))
    ax.text(0.98, 0.55, f"annual demand {summ.energy_TWh.min():.0f}-{summ.energy_TWh.max():.0f} TWh (2019-2025)\npeak {summ.peak_demand_MW.min()/1000:.1f}-{summ.peak_demand_MW.max()/1000:.1f} GW; load factor {summ.load_factor.min():.2f}-{summ.load_factor.max():.2f}", transform=ax.transAxes, ha="right", fontsize=7, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    ax.legend(ncol=3, fontsize=7.5); save(fig, "fig1_01_load_duration_curves")

    # Fig 1.2 net-load duration curves
    fig, ax = plt.subplots(figsize=(7, 4))
    for y in YEARS:
        ax.plot(nldc.index, nldc[y] / 1000, color=YCOL[y], label=f"{y} ({vh[y]:,} valid h)", lw=1.3)
    nl_ex = c1.duration_curves(h.rename(columns={"net_load_ex_storage": "nlx"}), "nlx")
    ax.plot(nl_ex.index, nl_ex[2025] / 1000, color=YCOL[2025], ls="--", lw=1.1, label="2025 minus estimated net battery charging\n(CAISO fleet net; pumped storage not removed)")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("Percent of valid hours in year"); ax.set_ylabel("Net load = demand - utility solar - wind (GW)")
    neg_ex = {y: int((h[h.year == y]["net_load_ex_storage"] < 0).sum()) for y in (2024, 2025)}; neg_raw = {y: int((h[h.year == y]["net_load"] < 0).sum()) for y in (2024, 2025)}
    ax.text(0.98, 0.62, f"minimum net load: {summ.loc[2019, 'min_net_load_MW']/1000:.1f} GW (2019), {summ.loc[2025, 'min_net_load_MW']/1000:.1f} GW (2025)\nhours with net load below zero: {neg_raw[2024]} (2024), {neg_raw[2025]} (2025)\nexcluding estimated battery charging: {neg_ex[2024]} (2024), {neg_ex[2025]} (2025)", transform=ax.transAxes, ha="right", fontsize=7, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    ax.set_title("Net-load duration curves, CAISO, 2019-2025"); ax.legend(ncol=3, fontsize=7, loc="lower left"); save(fig, "fig1_02_net_load_duration_curves")

    # Fig 1.3 seasonal average daily profiles: demand and net load, 2019 vs 2025
    fig, axes = plt.subplots(2, 4, figsize=(11, 5.2), sharex=True, sharey="row")
    for j, s in enumerate(c1.SEASON_ORDER):
        for y, ls in ((2019, "--"), (2022, ":"), (2025, "-")):
            g = prof[(prof.year == y) & (prof.season == s)]
            axes[0, j].plot(g.hour, g.demand / 1000, ls, color=YCOL[y], label=f"{y}", lw=1.4)
            axes[1, j].plot(g.hour, g.net_load / 1000, ls, color=YCOL[y], label=f"{y}", lw=1.4)
        axes[0, j].set_title(s); axes[1, j].set_xlabel("Hour of day (local, interval start)")
        axes[1, j].axhline(0, color="k", lw=0.5)
        mid = {y: prof[(prof.year == y) & (prof.season == s) & prof.hour.between(12, 14)].net_load.mean() / 1000 for y in (2019, 2025)}; ev = {y: prof[(prof.year == y) & (prof.season == s) & (prof.hour == 20)].net_load.mean() / 1000 for y in (2019, 2025)}
        axes[1, j].text(0.03, 0.05, f"12-14h mean: {mid[2019]:.1f} GW (2019), {mid[2025]:.1f} GW (2025)\n20h: {ev[2019]:.1f} GW (2019), {ev[2025]:.1f} GW (2025)", transform=axes[1, j].transAxes, fontsize=6.3, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    axes[0, 0].set_ylabel("Demand (GW)"); axes[1, 0].set_ylabel("Net load (GW)"); axes[0, 0].legend(fontsize=8)
    fig.suptitle("Average daily profiles by season, CAISO: demand (top) and net load (bottom), 2019 / 2022 / 2025", y=1.0)
    save(fig, "fig1_03_seasonal_daily_profiles")

    # Fig 1.4 top-100 net-load hours timing: month x hour heatmaps per year
    fig, axes = plt.subplots(1, len(YEARS), figsize=(15, 3.8), sharey=True)
    mats = {y: pd.crosstab(top[top.year == y].hour, top[top.year == y].month).reindex(index=range(12, 24), columns=range(5, 11), fill_value=0) for y in YEARS}
    vmax = max(int(m.values.max()) for m in mats.values())  # one colour scale for every panel
    for ax, y in zip(axes, YEARS):
        im = ax.imshow(mats[y].values, aspect="auto", cmap="magma_r", origin="lower", extent=[4.5, 10.5, 11.5, 23.5], vmin=0, vmax=vmax)
        ax.set_title(f"{y}\nmedian {int(timing.loc[y, 'median_hour'])}:00\nJul-Sep {100*timing.loc[y, 'share_Jul_Sep']:.0f}%\n17-21h {100*timing.loc[y, 'share_hours_17_21']:.0f}%", fontsize=7.5); ax.set_xlabel("Month"); ax.set_xticks(range(5, 11))
    axes[0].set_ylabel("Hour of day (local, interval start)")
    fig.colorbar(im, ax=axes, shrink=0.8, label=f"count of top-100 net-load hours (common scale, 0-{vmax})")
    fig.suptitle("When the 100 highest net-load hours occur, CAISO, by year (panel titles: median start hour, share in July-September, share between 17:00 and 21:00)", y=1.12, fontsize=9.5)
    stamp(fig, "fig1_04_top100_net_load_timing"); fig.savefig(FIGURES / "fig1_04_top100_net_load_timing.png", bbox_inches="tight"); fig.savefig(FIGURES / "fig1_04_top100_net_load_timing.pdf", bbox_inches="tight"); plt.close(fig); print("  figure fig1_04_top100_net_load_timing")

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

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    DCOL = {"DLAP_PGAE-APND": "C0", "DLAP_SCE-APND": "C3", "DLAP_SDGE-APND": "C2"}  # one colour per DLAP in both panels; dashed = 2024, solid = 2025
    for node, lab in c1.DLAPS.items():
        for y, ls in ((2024, "--"), (2025, "-")):
            if (node, y) in pdc.columns:
                axes[0].plot(pdc.index, pdc[(node, y)], ls, color=DCOL[node], label=f"{lab} {y}", lw=1.2)
    ext = {y: {node: (float(p[node][p.index.year == y].min()), float(p[node][p.index.year == y].max())) for node in c1.DLAPS} for y in (2024, 2025)}
    axes[0].axhline(0, color="k", lw=0.6); axes[0].set_ylim(-60, 250); axes[0].set_xlabel("Percent of hours in year"); axes[0].set_ylabel("Day-ahead LMP ($/MWh)")
    axes[0].set_title("Price duration curves, CAISO DLAPs, 2024 and 2025 (OASIS DAM)"); axes[0].legend(fontsize=7)
    axes[0].text(0.02, 0.03, "Axis truncated at -60 and 250 $/MWh. Extremes, PG&E / SCE / SDG&E:\n2024 max " + "/".join(f"{ext[2024][n][1]:.0f}" for n in c1.DLAPS) + ", min " + "/".join(f"{ext[2024][n][0]:.0f}" for n in c1.DLAPS)
                 + "; 2025 max " + "/".join(f"{ext[2025][n][1]:.0f}" for n in c1.DLAPS) + ", min " + "/".join(f"{ext[2025][n][0]:.0f}" for n in c1.DLAPS), transform=axes[0].transAxes, fontsize=6.5, color="grey", va="bottom")
    for node, lab in c1.DLAPS.items():
        g = pbh.xs(2025, level="year")[node]
        axes[1].plot(g.index, g.values, color=DCOL[node], label=f"{lab} 2025")
        g = pbh.xs(2024, level="year")[node]
        axes[1].plot(g.index, g.values, "--", color=DCOL[node], label=f"{lab} 2024", alpha=0.7)
    mids = [pbh.xs(yy, level="year")[n].loc[11:14].mean() for yy in (2024, 2025) for n in c1.DLAPS]; eves = [pbh.xs(yy, level="year")[n].loc[18:20].mean() for yy in (2024, 2025) for n in c1.DLAPS]
    axes[1].text(0.03, 0.05, f"mean price 11-14h: USD {min(mids):.0f}-{max(mids):.0f} per MWh; 18-20h: USD {min(eves):.0f}-{max(eves):.0f} per MWh\n(three DLAPs, 2024 and 2025)", transform=axes[1].transAxes, fontsize=6.8, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    axes[1].axhline(0, color="k", lw=0.6); axes[1].set_xlabel("Hour of day (local)"); axes[1].set_ylabel("Mean day-ahead LMP ($/MWh)"); axes[1].set_title("Average day-ahead price by hour of day"); axes[1].legend(fontsize=7, ncol=2)
    save(fig, "fig1_05_price_duration_and_diurnal")

    # like-for-like windows: complete years, and January 1 to the last available 2026 date for 2024, 2025 and 2026
    last = p.index.max(); md = last.strftime("%b %d")
    ytd_rows = []
    for y in (2024, 2025, 2026):
        w = p[(p.index.year == y) & ((p.index.month < last.month) | ((p.index.month == last.month) & (p.index.day <= last.day)))]
        for node, lab in c1.DLAPS.items():
            g = w[node].dropna(); ytd_rows.append({"window": f"Jan 1-{md}", "year": y, "node": node, "label": lab, "hours": len(g), "hours_negative": int((g < 0).sum()), "share_negative_pct": 100 * (g < 0).mean()})
    for y in (2024, 2025):
        g = p[p.index.year == y]
        for node, lab in c1.DLAPS.items():
            gg = g[node].dropna(); ytd_rows.append({"window": "full year", "year": y, "node": node, "label": lab, "hours": len(gg), "hours_negative": int((gg < 0).sum()), "share_negative_pct": 100 * (gg < 0).mean()})
    ytd = pd.DataFrame(ytd_rows); ytd.to_csv(PROCESSED / "ch1_negative_price_hours_windows.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    cats = [("full year", 2024), ("full year", 2025), (f"Jan 1-{md}", 2024), (f"Jan 1-{md}", 2025), (f"Jan 1-{md}", 2026)]
    xs = np.arange(len(cats)); wdt = 0.26
    for k, (node, lab) in enumerate(c1.DLAPS.items()):
        vals = [float(ytd[(ytd.window == w_) & (ytd.year == y_) & (ytd.node == node)].hours_negative.iloc[0]) for w_, y_ in cats]
        shares = [float(ytd[(ytd.window == w_) & (ytd.year == y_) & (ytd.node == node)].share_negative_pct.iloc[0]) for w_, y_ in cats]
        bars = axes[0].bar(xs + (k - 1) * wdt, vals, wdt, color=DCOL[node], label=lab)
        for b_, v_, sh in zip(bars, vals, shares):
            axes[0].text(b_.get_x() + b_.get_width() / 2, b_.get_height() + 12, f"{v_:,.0f}\n{sh:.0f}%", ha="center", fontsize=5.8)
    axes[0].set_xticks(xs); axes[0].set_xticklabels([f"{y_}\n{w_}" for w_, y_ in cats], fontsize=8); axes[0].set_ylim(0, 1350)
    axes[0].legend(fontsize=8, loc="upper right"); axes[0].set_ylabel("Hours with day-ahead LMP < $0"); axes[0].set_title(f"Negative-price hours by DLAP: complete years and matched Jan 1-{md} windows\n(labels: share of hours in the window; OASIS retention starts July 2023)")
    for node, lab in c1.DLAPS.items():
        g = nbm[node].unstack("year")
        for y in (2024, 2025, 2026):
            if y in g.columns:
                axes[1].plot(g.index, g[y], marker="o", ms=3, label=f"{lab} {y}", alpha=0.85 if y != 2026 else 0.6)
    mid_share = pst[pst.node.isin(c1.DLAPS) & pst.year.isin([2024, 2025])].neg_hours_10_16_share
    axes[1].text(0.98, 0.55, f"{100*mid_share.min():.0f}-{100*mid_share.max():.0f}% of negative hours fall\nbetween 10:00 and 16:00 (2024-2025, three DLAPs)", transform=axes[1].transAxes, ha="right", fontsize=6.8, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    axes[1].set_xlabel("Month"); axes[1].set_ylabel("Negative-price hours"); axes[1].set_title("Negative-price hours by month"); axes[1].set_ylim(0, 430); axes[1].legend(fontsize=6.5, ncol=3, loc="upper right")
    save(fig, "fig1_06_negative_price_hours")

    # ------------------------------------------------------------------ 3. carbon intensity
    print("3. Carbon intensity")
    ci = cached(PROCESSED / "caiso_co2_intensity_hourly.parquet", lambda: c1.load_caiso_outlook_hourly(2019, 2025), "valid_hour")
    csum = c1.carbon_summary(ci)
    csum["implied_gas_kg_per_MWh"] = (ci[ci.valid_hour].groupby("year")["Natural Gas CO2"].sum() / fm0[fm0.index.year.isin(YEARS)].groupby("year")["natural_gas"].sum() * 1000)
    csum.to_csv(PROCESSED / "ch1_carbon_intensity_annual.csv")
    # monthly cross-check of the EIA-930 gas series (method change Dec 2023) against CAISO's own fuel mix and CO2 accounting
    mon = pd.DataFrame({"eia930_gas_TWh": h.groupby(pd.Grouper(freq="MS"))["gas"].sum() / 1e6}); mon.index = mon.index.tz_localize(None)
    cm = pd.DataFrame({"caiso_fuelmix_gas_TWh": fm0.groupby(pd.Grouper(freq="MS"))["natural_gas"].sum() / 1e6,
                       "caiso_gas_co2_Mt": ci.groupby(pd.Grouper(freq="MS"))["Natural Gas CO2"].sum() / 1e6,
                       "caiso_demand_TWh": ci.groupby(pd.Grouper(freq="MS"))["demand_MW"].sum() / 1e6,
                       "co2_accounting_g_per_kWh": ci[ci.valid_hour].groupby(pd.Grouper(freq="MS"))["co2_total_tph"].sum() / ci[ci.valid_hour].groupby(pd.Grouper(freq="MS"))["demand_MW"].sum() * 1000})
    mon = mon.join(cm, how="inner"); mon["implied_gas_kg_per_MWh"] = mon.caiso_gas_co2_Mt / mon.caiso_fuelmix_gas_TWh * 1000
    mon["eia_minus_caiso_gas_TWh"] = mon.eia930_gas_TWh - mon.caiso_fuelmix_gas_TWh
    mon.round(3).to_csv(PROCESSED / "ch1_gas_series_comparability_monthly.csv")
    eg = c1.egrid_camx(); (PROCESSED / "ch1_egrid_camx_2023.json").write_text(json.dumps(eg, indent=1))
    diurnal = ci.groupby(["year", "season", "hour"])["intensity_g_per_kWh"].mean().reset_index(); diurnal.to_csv(PROCESSED / "ch1_carbon_intensity_diurnal.csv", index=False)
    cdc = c1.duration_curves(ci.rename(columns={"intensity_g_per_kWh": "ci"}), "ci"); cdc.to_csv(PROCESSED / "ch1_carbon_intensity_duration.csv")
    fm = fm0
    bat = c1.battery_summary(fm); bat.to_csv(PROCESSED / "ch1_battery_summary.csv")

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    axes[0].plot(csum.index, csum.energy_weighted_g_per_kWh, marker="o", label="CAISO CO2 accounting / demand, energy-weighted\n(imports net of exports; negative hours kept)")
    axes[0].plot(csum.index, csum.energy_weighted_floored_g_per_kWh, marker="s", ms=3, ls=":", color="C0", alpha=0.8, label="same, negative hours floored at zero (sensitivity)")
    axes[0].fill_between(csum.index, csum.p5_g_per_kWh, csum.p95_g_per_kWh, alpha=0.2, label="hourly 5th-95th percentile (variability, not a confidence interval)")
    axes[0].axhline(eg["co2_output_rate_g_per_kWh"], color="C3", ls="--", label=f"eGRID 2023 CAMX generation output rate ({eg['co2_output_rate_g_per_kWh']:.0f}): different boundary")
    axes[0].axvline(2023.92, color="grey", ls=":", lw=1, label="Dec 2023: CAISO gas data method change (affects the EIA-930 gas series, not this accounting series)")
    for yy in (2019, 2025):
        axes[0].annotate(f"{csum.loc[yy, 'energy_weighted_g_per_kWh']:.0f} g/kWh ({yy})", xy=(yy, csum.loc[yy, "energy_weighted_g_per_kWh"]), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=7, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    axes[0].text(0.03, 0.06, f"2025 hourly 5th / 95th percentile: {csum.loc[2025, 'p5_g_per_kWh']:.0f} / {csum.loc[2025, 'p95_g_per_kWh']:.0f} g/kWh\nfloored variant 2025: {csum.loc[2025, 'energy_weighted_floored_g_per_kWh']:.0f} g/kWh", transform=axes[0].transAxes, fontsize=6.5, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    axes[0].set_ylabel("g CO2 per kWh"); axes[0].set_title("Annual CO2 accounting intensity of CAISO demand"); axes[0].legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.14), frameon=False); axes[0].set_ylim(0, None)
    for y in YEARS:
        axes[1].plot(cdc.index, cdc[y], color=YCOL[y], label=str(y), lw=1.2)
    axes[1].axhline(0, color="k", lw=0.5); axes[1].set_ylim(-160, 450)
    nlow = {y: int((ci[(ci.year == y) & ci.valid_hour].intensity_accounting_g_per_kWh < -160).sum()) for y in YEARS}
    axes[1].text(0.02, 0.03, "axis cut at -160: " + ", ".join(f"{y} has {n}" for y, n in nlow.items() if n) + " hours below (export accounting)", transform=axes[1].transAxes, fontsize=6, color="grey")
    axes[1].set_xlabel("Percent of valid hours in year"); axes[1].set_ylabel("g CO2 per kWh (accounting, can be negative)"); axes[1].set_title("Hourly intensity duration curves"); axes[1].legend(fontsize=7, ncol=2, loc="upper right")
    for s, ls in zip(c1.SEASON_ORDER, ("-", "--", ":", "-.")):
        g = diurnal[(diurnal.year == 2025) & (diurnal.season == s)]
        axes[2].plot(g.hour, g.intensity_g_per_kWh, ls, label=f"2025 {s}")
    g = diurnal[(diurnal.year == 2019)].groupby("hour")["intensity_g_per_kWh"].mean(); axes[2].plot(g.index, g.values, color="grey", lw=2, alpha=0.6, label="2019 all seasons")
    d25 = diurnal[diurnal.year == 2025]; midv = {s_: d25[(d25.season == s_) & d25.hour.between(12, 14)].intensity_g_per_kWh.mean() for s_ in ("MAM", "JJA")}; night = d25[d25.hour.between(0, 4)].groupby("season").intensity_g_per_kWh.mean()
    axes[2].text(0.5, 0.42, f"2025 12-14h mean: spring {midv['MAM']:.0f}, summer {midv['JJA']:.0f} g/kWh\n2025 0-4h mean by season: {night.min():.0f}-{night.max():.0f} g/kWh", transform=axes[2].transAxes, ha="center", fontsize=6.5, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    axes[2].set_xlabel("Hour of day (local)"); axes[2].set_title("Average diurnal accounting intensity"); axes[2].set_ylim(-20, 430); axes[2].axhline(0, color="k", lw=0.5); axes[2].legend(fontsize=7, ncol=3, loc="upper center")
    save(fig, "fig1_07_carbon_intensity")

    # ------------------------------------------------------------------ 4. existing data center load, four ways
    print("4. Existing data center load")
    rs = pd.DataFrame([c1.ca_retail_sales_eia861(y) for y in range(2019, 2025)]); rs.to_csv(PROCESSED / "ch1_ca_retail_sales_eia861.csv", index=False)
    retail_2024 = float(rs.loc[rs.year == 2024, "retail_sales_TWh"].iloc[0]); retail_2023 = float(rs.loc[rs.year == 2023, "retail_sales_TWh"].iloc[0])
    svp = c1.svp_fact_sheet_energy(); svp.to_csv(PROCESSED / "ch1_svp_fact_sheets.csv", index=False)
    pts = c1.kollar_grady_california(); pts.to_csv(PROCESSED / "ch1_kollar_grady_points_california_flag.csv", index=False)
    n_ca, n_sc = int(pts.in_california.sum()), int(pts.santa_clara_12km.sum())
    svp_sales23 = float(svp.loc[svp.fact_sheet_year == 2023, "retail_sales_GWh"].iloc[0])
    epoch = pd.read_csv(c1.raw_path("epoch_data_centers"))
    n_epoch_ca = int(epoch["Address"].astype(str).str.contains(r", CA\b|California", regex=True).sum())
    bu = c1.bottom_up_estimate(n_ca, n_sc, svp_dc_energy_GWh=0.55 * svp_sales23, n_epoch_ca=n_epoch_ca)
    est = c1.dc_load_estimates(rs)
    est = pd.concat([est, pd.DataFrame([dict(group="C. Illustrative sensitivity", method=f"Count-based: {n_ca} Kollar-Grady facility points x assumed energy per facility", year=2023, denominator_year=2023,
                                              low_TWh=bu["low_TWh"], central_TWh=bu["central_TWh"], high_TWh=bu["high_TWh"],
                                              basis=(f"{n_ca} Kollar-Grady facility points inside California ({n_sc} within 12 km of Santa Clara); the Epoch AI snapshot has no California observation ({n_epoch_ca} sites), which is a coverage limit, not a count of zero; "
                                                     f"assumed annual energy per facility = SVP cluster average {bu['avg_energy_GWh_per_facility_svp_anchor']:.1f} GWh (55% of SVP 2023 retail sales over 58 data centers, i.e. {bu['avg_load_MW_per_facility_svp_anchor']:.1f} MW average load) scaled 0.5 / 0.75 / 1.0 "
                                                     f"because the statewide inventory includes many small facilities; no peak or utilization factor is used; representativeness of the SVP average is untested"),
                                              source="kollar_grady_2025_zenodo; epoch_data_centers; svp_fact_sheet_2023; svp_assembly_hearing_2026_01_28",
                                              retail_sales_TWh=retail_2023)])], ignore_index=True)
    for k in ("low", "central", "high"):
        est[f"{k}_share_pct"] = est[f"{k}_TWh"] / est["retail_sales_TWh"] * 100
    est = est.sort_values("group").reset_index(drop=True)
    est.to_csv(PROCESSED / "ch1_dc_load_estimates.csv", index=False)
    (PROCESSED / "ch1_bottom_up_inputs.json").write_text(json.dumps(bu, indent=1))

    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ylab = {"A. Statewide estimate": "A. Statewide historical estimate\nEPRI 2024 table, 2023 consumption",
            "B. Assumed conversion": "B. Assumed conversion\nCEC ~1,000 MW existing peak (Dec 2025)\nx assumed load factor 0.80-0.95",
            "C. Illustrative sensitivity": f"C. Illustrative count-based sensitivity\n{n_ca} facility points x assumed {bu['avg_energy_GWh_per_facility_svp_anchor']:.0f} GWh\nper facility, scaled 0.5-1.0",
            "D. Utility subset": "D. Utility subset, not statewide\nSilicon Valley Power: 53-60% of\nSVP 2023 retail sales"}
    gcol = {"A. Statewide estimate": "C0", "B. Assumed conversion": "C1", "C. Illustrative sensitivity": "C2", "D. Utility subset": "C3"}
    for i, r in est.iterrows():
        ax.barh(i, max(r.high_TWh - r.low_TWh, 0.12), left=r.low_TWh, height=0.5, color=gcol[r.group], alpha=0.35)
        ax.plot([r.central_TWh], [i], "k|", ms=18, mew=2)
        txt = (f"{r.central_TWh:.1f} TWh = {r.central_share_pct:.1f}% of {r.denominator_year} retail sales" if r.high_TWh == r.low_TWh
               else f"{r.low_TWh:.1f}-{r.high_TWh:.1f} TWh = {r.low_share_pct:.1f}-{r.high_share_pct:.1f}% of {r.denominator_year} retail sales")
        ax.text(max(r.high_TWh, r.central_TWh) + 0.3, i, txt, va="center", fontsize=8)
    ax.set_yticks(range(len(est))); ax.set_yticklabels([ylab[g] for g in est.group], fontsize=7.5); ax.invert_yaxis()
    ax.set_xlabel(f"TWh per year; shares use EIA-861 California retail sales of the matching year (2023: {retail_2023:.1f} TWh, 2024: {retail_2024:.1f} TWh)", fontsize=8)
    ax.set_xlim(0, max(est.high_TWh) * 1.9)
    ax.set_title("Evidence and assumptions for California data center electricity use: differing years and coverage", fontsize=10)
    save(fig, "fig1_08_existing_dc_load_estimates")

    # ------------------------------------------------------------------ 5. run record
    record = {"years": YEARS, "ciso_hours": int(len(h)), "ciso_valid_demand_hours": {int(y): int(v) for y, v in summ["hours"].items()}, "lmp_hours": int(len(p)), "co2_valid_hours": {int(y): int(v) for y, v in csum["hours"].items()},
              "retail_sales_2024_TWh": retail_2024, "retail_sales_2023_TWh": retail_2023, "kollar_grady_california_points": n_ca, "outputs": sorted(x.name for x in PROCESSED.glob("ch1_*"))}
    (PROCESSED / "ch1_run_record.json").write_text(json.dumps(record, indent=1, default=str))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
