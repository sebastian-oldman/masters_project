#!/usr/bin/env python
"""Chapter 2 runner: data center growth in California (RQ1). Writes data/processed/ch2_* and
figures/fig2_*; scripts/make_ch2_tables.py renders the LaTeX tables from these outputs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src import ch2_growth as c2  # noqa: E402
from src.paths import PROCESSED, FIGURES  # noqa: E402
from src.provenance import stamp  # noqa: E402

plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 200, "font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})
BOOT = 199


def save(fig, name, **kw):
    stamp(fig, name)
    fig.savefig(FIGURES / f"{name}.png", bbox_inches="tight", **kw)
    fig.savefig(FIGURES / f"{name}.pdf", bbox_inches="tight", **kw)
    plt.close(fig)
    print("  figure", name)


def main() -> int:
    # ------------------------------------------------------------ 1. Census chart
    print("1. Census C30 data center construction")
    c = c2.census_c30()
    c.to_csv(PROCESSED / "ch2_census_c30_data_center.csv")
    s = c["data_center_saar"].dropna()
    fig, axes = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True, gridspec_kw={"height_ratios": [3, 1.4]})
    ax = axes[0]
    ax.plot(s.index, s / 1000, color="#e0b34a", lw=2, label="US data center construction spending, seasonally adjusted annual rate")
    ax.axvline(c2.CHATGPT, color="grey", ls="--", lw=1)
    ax.annotate("ChatGPT\nlaunch\n(Nov 30, 2022)", xy=(c2.CHATGPT, s.loc["2022-11-30"] / 1000), xytext=(pd.Timestamp("2020-06-30"), 22),
                arrowprops=dict(arrowstyle="->", color="grey"), fontsize=8, ha="center")
    ax.set_ylabel("Billion nominal dollars per year (SAAR)"); ax.set_ylim(0, None)
    ax.set_title("US private construction spending, data center category (nominal dollars, seasonally adjusted annual rate), Jan 2014 to Jul 2026 (Census C30)", fontsize=9.5)
    ax.legend(loc="upper left", fontsize=8)
    last = s.index[-1]
    ax.text(last, s.iloc[-1] / 1000, f" ${s.iloc[-1]/1000:.1f}B\n {last:%b %Y} (prelim.)", fontsize=8, va="center")
    ax.annotate(f"${s.iloc[0]/1000:.1f}B (Jan 2014)", xy=(s.index[0], s.iloc[0] / 1000), xytext=(10, 12), textcoords="offset points", fontsize=7.5)
    ax.annotate(f"${s.loc['2022-11-30']/1000:.1f}B (Nov 2022)", xy=(pd.Timestamp("2022-11-30"), s.loc["2022-11-30"] / 1000), xytext=(-70, -22), textcoords="offset points", fontsize=7.5)
    sh = c["dc_share_of_nonres_pct"]
    ax.text(0.03, 0.62, f"share of private nonresidential construction:\n{sh.iloc[0]:.1f}% (Jan 2014), {sh.loc['2022-11-30']:.1f}% (Nov 2022), {sh.iloc[-1]:.1f}% (Jul 2026)", transform=ax.transAxes, fontsize=7.5, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    ax2 = axes[1]
    mom = c["mom_growth_pct"].dropna()
    ax2.bar(mom.index, mom.values, width=20, color=np.where(mom.values >= 0, "#4a7bb7", "#c44e52"))
    ax2.plot(mom.index, mom.rolling(12).mean(), color="k", lw=1, label="12-month mean")
    ax2.axvline(c2.CHATGPT, color="grey", ls="--", lw=1); ax2.axhline(0, color="k", lw=0.6)
    m1 = mom.loc["2019-01-01":"2021-12-31"].mean(); m2 = mom.loc["2023-01-01":].mean()
    ax2.text(0.98, 0.9, f"mean month-over-month growth: {m1:.1f}% (2019-2021), {m2:.1f}% (2023-Jul 2026)", transform=ax2.transAxes, ha="right", va="top", fontsize=7.5, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    ax2.set_ylabel("Month-over-month\ngrowth (%)"); ax2.legend(fontsize=8, loc="upper left")
    ax2.xaxis.set_major_locator(mdates.YearLocator()); ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.text(0.99, 0.005, "Source: U.S. Census Bureau, Value of Construction Put in Place (privsatime.xlsx), accessed 2026-09-21; p = preliminary", ha="right", fontsize=7, color="grey")
    save(fig, "fig2_01_census_data_center_construction")

    # ------------------------------------------------------------ 2. structural breaks and forecasts
    print("2. Structural breaks and forecasts")
    y = np.log(s.values)
    res = c2.break_analysis(s, 12, c2.CHATGPT_FIRST_POST, max_breaks=5, bootstrap_reps=BOOT, label="Census data center construction (monthly, SAAR)")  # first post-launch observation: December 2022
    bp = c2.bai_perron(y, max_breaks=5)  # five breaks is the most that 15 percent trimming allows, so the choice is uncensored
    sq = c2.sequential_supF(y, max_breaks=5, reps=BOOT)
    bp_table = pd.DataFrame([{"m": m, "breaks": ", ".join(s.index[b].strftime("%Y-%m") for b in v["breaks"]), "ssr": v["ssr"], "bic": v["bic"], "lwz": v["lwz"], "supF_0_m": v["supF"],
                              "supF_seq": sq["levels"].get(m, {}).get("supF_seq", np.nan), "supF_seq_boot_p": sq["levels"].get(m, {}).get("boot_p", np.nan)} for m, v in bp["by_m"].items()])
    print(f"   BIC m={bp['m_bic']}, LWZ m={bp['m_lwz']}, sequential m={sq['m_seq']}")
    bp_table.to_csv(PROCESSED / "ch2_census_bai_perron.csv", index=False)
    # segment growth rates for the BIC-selected partition
    seg_rows = []
    cuts = [0] + list(bp["breaks_bic"]) + [len(y)]
    for a, b in zip(cuts[:-1], cuts[1:]):
        g = c2.growth_rate(y[a:b], 12)
        seg_rows.append({"segment_start": s.index[a].strftime("%Y-%m"), "segment_end": s.index[b - 1].strftime("%Y-%m"), "months": b - a, "cagr": g["cagr"], "cagr_lo95": g["cagr_lo95"], "cagr_hi95": g["cagr_hi95"]})
    seg = pd.DataFrame(seg_rows); seg.to_csv(PROCESSED / "ch2_census_segment_growth.csv", index=False)
    import ruptures as rpt
    sig = np.column_stack([y, np.ones(len(y)), np.arange(len(y))])
    algo = rpt.Dynp(model="linear", min_size=bp["h"], jump=1).fit(sig)
    rupt = {m: [s.index[b - 1].strftime("%Y-%m") for b in algo.predict(n_bkps=m)[:-1]] for m in (1, 2, 3, 4, 5)}
    fa, ia = c2.arima_forecast(np.log(s)); fa.to_csv(PROCESSED / "ch2_census_forecast_arima.csv")
    fe, ie = c2.ets_forecast(np.log(s)); fe.to_csv(PROCESSED / "ch2_census_forecast_ets.csv")
    bt, bt_raw = c2.backtest_forecasts(np.log(s), n_origins=24); bt.to_csv(PROCESSED / "ch2_census_forecast_backtest.csv", index=False); bt_raw.to_csv(PROCESSED / "ch2_census_forecast_backtest_detail.csv", index=False)
    print("   backtest (MAPE %, 12-month horizon):", {m: round(float(v), 1) for m, v in bt[bt.horizon == 12].set_index("model").mape_pct.items()})
    (PROCESSED / "ch2_census_break_summary.json").write_text(json.dumps({**{k: (str(v) if not isinstance(v, (int, float)) else v) for k, v in res.items()}, "ruptures_dynp": rupt, "sequential": {"m_seq": sq["m_seq"], "levels": sq["levels"]}, "arima": {**ia, "params": ia["params"]}, "ets": ie}, indent=1, default=str))

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    ax = axes[0]
    ax.plot(s.index, s / 1000, color="k", lw=1.2, label="observed (SAAR)")
    kb = res["known_break_period"]
    kbi = int(np.searchsorted(s.index.values, np.datetime64(pd.Timestamp(kb))))
    for lo, hi, col, lab in ((0, kbi, "C0", f"pre-launch trend, Jan 2014-Nov 2022: {100*res['cagr_pre']:.0f}%/yr [{100*res['cagr_pre_lo']:.0f}, {100*res['cagr_pre_hi']:.0f}]"),
                             (kbi, len(y), "C3", f"post-launch trend, Dec 2022-Jul 2026: {100*res['cagr_post']:.0f}%/yr [{100*res['cagr_post_lo']:.0f}, {100*res['cagr_post_hi']:.0f}]")):
        X = c2.trend_X(hi - lo); beta, *_ = np.linalg.lstsq(X, y[lo:hi], rcond=None)
        ax.plot(s.index[lo:hi], np.exp(X @ beta) / 1000, color=col, lw=2, label=lab)
    for k, b in enumerate(bp["breaks_bic"]):
        ax.axvline(s.index[b], color="C2", ls=":", lw=1.2, label=("BP breaks (BIC): " + ", ".join(s.index[bb].strftime("%b %Y") for bb in bp["breaks_bic"])) if k == 0 else None)
    ax.axvline(c2.CHATGPT, color="grey", ls="--", lw=1, label="ChatGPT launch, Nov 30 2022 (December 2022 is the first post-launch month)")
    segtxt = "BIC segments, %/yr: " + " / ".join(f"{100*r_.cagr:.0f}" for r_ in seg.itertuples()) + f"\nlast segment {seg.iloc[-1].segment_start} to {seg.iloc[-1].segment_end}: {100*seg.iloc[-1].cagr:.0f}% [{100*seg.iloc[-1].cagr_lo95:.0f}, {100*seg.iloc[-1].cagr_hi95:.0f}]\nsupF(1|0) = {res['bp_supF_1']:.0f}, bootstrap p = {sq['levels'][1]['boot_p']:.2f}; sequential test keeps {sq['m_seq']} break"
    ax.text(0.03, 0.97, segtxt, transform=ax.transAxes, va="top", fontsize=6.8, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    ax.set_yscale("log"); ax.set_ylabel("Billion dollars per year (log scale)"); ax.set_title(f"Log-linear trends and breaks (Chow F = {res['chow_F']:.0f}, p < 0.001)"); ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=2, frameon=False)
    ax = axes[1]
    ax.plot(s.index[-60:], s.iloc[-60:] / 1000, color="k", lw=1.2, label="observed")
    for f, col, lab in ((fa, "C0", f"ARIMA{ia['order']} with drift on log spending, median"), (fe, "C1", "ETS(A,Ad,N) on log spending, median")):
        ax.plot(f.index, f["mean"] / 1000, color=col, lw=1.6, label=lab)
        ax.fill_between(f.index, f["lo80"] / 1000, f["hi80"] / 1000, color=col, alpha=0.25)
        ax.fill_between(f.index, f["lo95"] / 1000, f["hi95"] / 1000, color=col, alpha=0.12)
    b12 = bt[bt.horizon == 12].set_index("model")
    fc_txt = (f"medians, USD billion: Jul 2027 {fa.loc['2027-07-31', 'mean']/1000:.0f} (ARIMA), {fe.loc['2027-07-31', 'mean']/1000:.0f} (ETS)\nJul 2028 {fa.loc['2028-07-31', 'mean']/1000:.0f} (ARIMA), {fe.loc['2028-07-31', 'mean']/1000:.0f} (ETS); 95% bands {min(fa.loc['2028-07-31', 'lo95'], fe.loc['2028-07-31', 'lo95'])/1000:.0f}-{max(fa.loc['2028-07-31', 'hi95'], fe.loc['2028-07-31', 'hi95'])/1000:.0f}"
              f"\nbacktest, 12-month MAPE: ARIMA {b12.loc['ARIMA (log, drift)', 'mape_pct']:.0f}%, ETS {b12.loc['ETS(A,Ad,N) (log)', 'mape_pct']:.0f}%, drift benchmark {b12.loc['drift benchmark (log random walk)', 'mape_pct']:.0f}%")
    ax.text(0.03, 0.66, fc_txt, transform=ax.transAxes, va="top", fontsize=6.6, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    ax.set_ylabel("Billion nominal dollars per year"); ax.set_title("24-month forecasts (back-transformed log medians) with 80% and 95% bands"); ax.legend(fontsize=7.5, loc="upper left")
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.subplots_adjust(bottom=0.27, wspace=0.22)
    save(fig, "fig2_02_census_breaks_and_forecast")

    # ------------------------------------------------------------ 3. California proxies
    print("3. California proxies")
    q = c2.qcew_california(); q.to_csv(PROCESSED / "ch2_qcew_518210_california.csv", index=False)
    st = q[q.fips == "06000"].set_index("period")
    cb = c2.cbre_california(); cb.to_csv(PROCESSED / "ch2_cbre_california.csv", index=False)
    sv_uc = cb[(cb.kind == "chapter_history") & (cb.metric == "under_construction_mw")].set_index("date")["value"].sort_index()
    sv_inv = cb[(cb.kind == "overview") & (cb.market == "Silicon Valley") & (cb.metric == "inventory_mw")].set_index("date")["value"].sort_index()
    ep = c2.epoch_timeline(); ep.to_csv(PROCESSED / "ch2_epoch_timeline.csv")
    proxies = {
        "QCEW 518210 California employment (quarterly)": (st["employment"], 4, pd.Timestamp("2023-03-31")),
        "QCEW 518210 California establishments (quarterly)": (st["qtrly_estabs"].astype(float), 4, pd.Timestamp("2023-03-31")),
        "QCEW 518210 California wages (quarterly)": (st["total_qtrly_wages"].astype(float), 4, pd.Timestamp("2023-03-31")),
        "CBRE Silicon Valley MW under construction (semiannual)": (sv_uc, 2, pd.Timestamp("2023-06-30")),
        "Epoch frontier sites, United States cumulative MW (monthly)": (ep["power_MW_us"], 12, c2.CHATGPT),
    }
    rows = [dict(res)]
    for lab, (ser, ppy, kb) in proxies.items():
        try:
            rows.append(c2.break_analysis(ser, ppy, kb, max_breaks=5, bootstrap_reps=BOOT, label=lab))
        except Exception as e:  # keep going, record the failure
            rows.append({"series": lab, "error": str(e)[:200]})
    rows.append({"series": "Epoch frontier sites, California cumulative MW", "n": 0, "note": "no California observation in the Epoch snapshot (0 of 87 sites): a coverage limit of the hub, not evidence of zero activity; no test possible"})
    comp = pd.DataFrame(rows); comp.to_csv(PROCESSED / "ch2_break_test_comparison.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(12, 7.2))
    fig.subplots_adjust(wspace=0.36, hspace=0.30)  # room for the twin-axis label between the top panels
    ax = axes[0, 0]; ax.plot(st.index, st["employment"] / 1000, color="C0", label="employment (thousands, left)"); ax.set_ylabel("Employment (thousands)")
    ax2 = ax.twinx(); ax2.plot(st.index, st["qtrly_estabs"], color="C1", label="establishments (right)"); ax2.set_ylabel("Establishments"); ax2.grid(False)
    ax.text(0.03, 0.72, f"employment: {st.employment.iloc[0]/1000:.0f}k ({st.index[0]:%Y} Q{st.index[0].quarter}), {st.loc['2022-12-31', 'employment']/1000:.0f}k (2022 Q4), {st.employment.iloc[-1]/1000:.0f}k ({st.index[-1]:%Y} Q{st.index[-1].quarter})\nestablishments: {st.qtrly_estabs.iloc[0]:,.0f} to {st.qtrly_estabs.iloc[-1]:,.0f}", transform=ax.transAxes, va="top", fontsize=6.8, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    ax.axvline(c2.CHATGPT, color="grey", ls="--", lw=1); ax.set_title("California NAICS 518210 (data processing, hosting), BLS QCEW, private"); ax.legend(loc="upper left", fontsize=8); ax2.legend(loc="lower right", fontsize=8)
    ax = axes[0, 1]; ax.bar(sv_uc.index, sv_uc.values.astype(float), width=150, color="C2", label="under construction (MW)"); ax.plot(sv_inv.index, sv_inv.values.astype(float), "k.-", label="inventory (MW, CBRE overview tables)")
    ax.text(0.03, 0.70, f"under construction: {sv_uc.iloc[0]:.0f} MW (H1 2016), {sv_uc.loc['2022-12-31']:.0f} MW (H2 2022),\n{sv_uc.loc['2023-06-30':].min():.0f}-{sv_uc.loc['2023-06-30':].max():.0f} MW since; latest {sv_uc.iloc[-1]:.0f} MW\ninventory: {sv_inv.iloc[0]:.0f} MW (H1 2023) to {sv_inv.iloc[-1]:.0f} MW (H1 2026)", transform=ax.transAxes, va="top", fontsize=6.8, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    ax.axvline(c2.CHATGPT, color="grey", ls="--", lw=1); ax.set_title("CBRE Silicon Valley colocation market, semiannual"); ax.set_ylabel("MW"); ax.legend(fontsize=8, loc="upper left")
    n_us = int(pd.read_csv(c2.raw_path("epoch_data_centers"))["Country"].astype(str).str.contains("United States").sum())
    ax = axes[1, 0]; ax.plot(ep.index, ep["power_MW_us"] / 1000, color="C3", label=f"United States: {n_us} sites in the Epoch snapshot")
    ax.annotate(f"{ep['power_MW_us'].iloc[-1]/1000:.1f} GW ({ep.index[-1]:%b %Y})", xy=(ep.index[-1], ep["power_MW_us"].iloc[-1] / 1000), xytext=(-118, -34), textcoords="offset points", fontsize=7.5, arrowprops=dict(arrowstyle="-", color="grey", lw=0.6))
    ax.text(0.03, 0.78, "California: no observations in\nthis Epoch snapshot (a coverage\nlimit of the hub, not evidence of\nzero activity; no CA series drawn)", transform=ax.transAxes, fontsize=7, color="C4", va="top")
    ax.axvline(c2.CHATGPT, color="grey", ls="--", lw=1); ax.set_title("Epoch AI Frontier Data Centers Hub, cumulative facility power"); ax.set_ylabel("GW"); ax.legend(fontsize=8, loc="upper left")
    ax = axes[1, 1]; ax.axis("off")
    cell = []
    short = {"Census data center construction": "Census US construction", "QCEW 518210 California employment": "QCEW CA employment", "QCEW 518210 California establishments": "QCEW CA establishments",
             "QCEW 518210 California wages": "QCEW CA wages", "CBRE Silicon Valley MW under construction": "CBRE SV construction", "Epoch frontier sites, United States cumulative MW": "Epoch US cumulative MW",
             "Epoch frontier sites, California cumulative MW": "Epoch CA cumulative MW"}
    for _, r in comp.iterrows():
        nm = short.get(r["series"].split(" (")[0], r["series"][:26])
        if "chow_p" in r and pd.notna(r.get("chow_p", np.nan)):
            cell.append([nm, ("<0.001" if r["chow_p"] < 0.0005 else f"{r['chow_p']:.3f}"), f"{100*r['cagr_pre']:.0f}% -> {100*r['cagr_post']:.0f}%", str(r.get("bp_break1", "")), f"{int(r['bp_m_bic'])}/{int(r['bp_m_lwz'])}/{int(r['bp_m_seq'])} (last {str(r.get('bp_breaks_bic', '')).split(', ')[-1]})" if r.get("bp_m_bic", 0) else "0/0/0"])
        else:
            cell.append([nm, "n/a", "n/a", "n/a", "no CA observation in snapshot"])
    tb = ax.table(cellText=cell, colLabels=["series", "Chow\np", "growth\npre -> post", "BP break\n(1 break)", "m: BIC / LWZ / seq.\n(last break)"], loc="center", cellLoc="left", colWidths=[0.27, 0.08, 0.16, 0.13, 0.36])
    tb.auto_set_font_size(False); tb.set_fontsize(5.8); tb.scale(1, 1.6)
    for ci in range(5):
        tb[0, ci].set_height(tb[0, ci].get_height() * 1.8); tb[0, ci].get_text().set_ha("center"); tb[0, ci].set_text_props(ha="center")
    for (ri, ci), c_ in tb.get_celld().items():
        if ri == 0:
            c_.set_text_props(fontsize=5.8, weight="bold")
        c_.PAD = 0.03; ax.set_title("Break tests: known break = first period after Nov 2022; BP = Bai-Perron", fontsize=9)
    save(fig, "fig2_03_california_proxies")

    # ------------------------------------------------------------ 4. tier vintages
    print("4. CEC tier vintages")
    tv = c2.tier_vintages(); tv.to_csv(PROCESSED / "ch2_tier_vintages.csv", index=False)
    ref = c2.cec_forecast_reference_points(); ref.to_csv(PROCESSED / "ch2_cec_forecast_reference_points.csv", index=False)
    caiso_record_mw = 52061.0  # CAISO all-time instantaneous peak, Sept 6 2022 16:57 (Key Statistics)
    caiso_record_hourly = 51104.0  # EIA-930 hourly, chapter 1
    est = pd.read_csv(PROCESSED / "ch1_dc_load_estimates.csv")
    statewide = est[est.group.str.startswith(("A.", "B."))]  # statewide estimate and assumed conversion only (not the illustrative sensitivity or the SVP subset)
    ex_low, ex_high = statewide.low_TWh.min() * 1e6 / 8760, statewide.high_TWh.max() * 1e6 / 8760  # average-load MW range from chapter 1
    ex_cec_peak = 1000.0
    fig, ax = plt.subplots(figsize=(10, 6.2))
    order = ["Signed agreement", "Active application", "Agreements + applications (no inquiries)", "Inquiry", "All tiers", "Canceled"]
    seen = set()
    def lab_once(t):
        if t in seen:
            return None
        seen.add(t); return t
    cols = {"Signed agreement": "#1b7837", "Active application": "#5aae61", "Inquiry": "#a6dba0", "Agreements + applications (no inquiries)": "#7fbf7b", "All tiers": "#bdbdbd", "Canceled": "#d9534f"}
    vint = [("2024-12", "Dec 2024\n(PG&E+SCE,\nno inquiries)"), ("2025-08", "Summer 2025\n(PG&E, SCE split;\n5 others unsplit)"), ("2025-12", "Dec 2025\n(7 utilities by tier)")]
    xs = np.arange(len(vint))
    for i, (v, lab) in enumerate(vint):
        d = tv[(tv.vintage == v) & (~tv.label.str.contains("SCE database|PG&E earnings"))]
        dca, dnv = d[d.utility != "VEA"], d[d.utility == "VEA"]
        bottom = 0
        for tier in order:
            mw = dca[dca.tier == tier].mw.sum()
            if mw > 0:
                ax.bar(i, mw, bottom=bottom, color=cols[tier], edgecolor="white", label=lab_once(tier), width=0.6)
                ax.text(i, bottom + mw / 2, f"{mw:,.0f}", ha="center", va="center", fontsize=8)
                bottom += mw
        ca_total, nv = bottom, float(dnv.mw.sum())
        if nv > 0:
            ax.bar(i, nv, bottom=bottom, color="#e0e0e0", edgecolor="grey", hatch="xx", width=0.6, label=lab_once("VEA requests located in Nevada (inside CAISO, outside California)"))
            ax.text(i, bottom + nv / 2, f"{nv:,.0f} (NV)", ha="center", va="center", fontsize=7.5)
            bottom += nv
        lbl = f"CA {ca_total:,.0f} MW" + (f"\n+{nv:,.0f} NV\n= {bottom:,.0f}" if nv > 0 else "") + ("*" if v == "2025-12" else "")
        ax.text(i, bottom + 400, lbl, ha="center", fontsize=7.5, fontweight="bold", va="bottom")
    # SCE-only vintages as narrow bars
    for j, (v, lab) in enumerate([("2025-08", "SCE database\nAug 2025\n(active | canceled)"), ("2026-01", "SCE database\nJan 2026\n(active | canceled)")]):
        d = tv[(tv.vintage == v) & (tv.label.str.contains("SCE database"))]
        x = 3.2 + j * 0.9; bottom = 0
        for tier in ["Signed agreement", "Active application", "Inquiry"]:
            mw = d[d.tier == tier].mw.sum()
            if mw > 0:
                ax.bar(x, mw, bottom=bottom, color=cols[tier], edgecolor="white", width=0.42, label=lab_once(tier))
                bottom += mw
        ax.text(x, bottom + 400, f"active\n{bottom:,.0f}", ha="center", fontsize=7.5, va="bottom")
        canc = float(d[d.tier == "Canceled"].mw.sum())
        ax.bar(x + 0.32, canc, color=cols["Canceled"], edgecolor="white", width=0.18, hatch="//", label=lab_once("Canceled (drawn separately, not part of the active pipeline)"))
        ax.text(x + 0.43, canc + 300, f"canceled\n{canc:,.0f}", ha="left", fontsize=6.5, va="bottom", color=cols["Canceled"])
        vint.append((v, lab))
    # PG&E's own pipeline (PG&E stage definitions, no inquiries) as narrow bars
    pcols = {"PG&E: application + preliminary engineering": "#5aae61", "PG&E: final engineering (WPA signed)": "#1b7837",
             "PG&E: interconnection construction agreement": "#08306b", "PG&E: construction": "#000000"}
    for j, (v, lab) in enumerate([("2026-03", "PG&E pipeline\nMar 2026\n(PG&E stages)"), ("2026-06", "PG&E pipeline\nJun 2026\n(PG&E stages)")]):
        d = tv[(tv.vintage == v) & (tv.label.str.contains("PG&E earnings"))]
        x = 5.3 + j * 0.85; bottom = 0
        for tier in ["PG&E: application + preliminary engineering", "PG&E: final engineering (WPA signed)", "PG&E: interconnection construction agreement", "PG&E: construction"]:
            mw = d[d.tier == tier].mw.sum()
            if mw > 0:
                ax.bar(x, mw, bottom=bottom, color=pcols[tier], edgecolor="white", width=0.5, hatch="..", label=lab_once(tier + " (no inquiries)"))
                bottom += mw
        ax.text(x, bottom + 400, f"{bottom:,.0f}", ha="center", fontsize=8, va="bottom")
        vint.append((v, lab))
    for xd in (2.65, 4.85):
        ax.axvline(xd, color="grey", lw=0.8, ls="-.")
    ax.text(1.0, 59300, "CEC statewide vintages (7 utilities, CEC tiers)", ha="center", fontsize=7.5, color="grey", va="top"); ax.text(3.75, 59300, "SCE public database\n(one utility)", ha="center", fontsize=7.5, color="grey", va="top"); ax.text(5.7, 59300, "PG&E earnings pipeline\n(one utility, PG&E stages)", ha="center", fontsize=7.5, color="grey", va="top")
    ax.axhline(caiso_record_mw, color="k", ls="--", lw=1); ax.text(-0.4, caiso_record_mw + 600, f"CAISO record instantaneous peak 52,061 MW (Sep 6, 2022): scale reference only", ha="left", fontsize=7.5, va="bottom")
    ax.text(1.5, 30200, "* utility rows sum to 23,278; CEC marginal totals 23,277 (20,677 in CA)", ha="center", fontsize=6.5, color="grey")
    ax.text(4.6, 44500, f"December 2025 requests located in California: 20,677 MW\n= {100*20677/caiso_record_mw:.1f}% of the CAISO record peak ({caiso_record_mw:,.0f} MW)\n= {20677/ex_cec_peak:.1f}x existing data center peak demand (~1,000 MW)\n= {20677/ex_high:.0f}-{20677/ex_low:.0f}x existing average load ({ex_low:,.0f}-{ex_high:,.0f} MW)\n(IEPR comparison in the RQ1 table)", ha="center", va="center", fontsize=7, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="grey", lw=0.5))
    ax.axhspan(ex_low, ex_high, color="C1", alpha=0.18, label=f"existing data center average load, chapter 1 statewide estimate and conversion: {ex_low:,.0f}-{ex_high:,.0f} MW")
    ax.axhline(ex_cec_peak, color="C1", lw=1.2, label="existing data center peak demand, CEC: ~1,000 MW (Dec 2025)")
    ax.set_xticks(list(xs) + [3.2, 4.1, 5.3, 6.15]); ax.set_xticklabels([l for _, l in vint], fontsize=7.5); ax.set_ylabel("MW requested"); ax.set_ylim(0, 60000); ax.set_xlim(-0.5, 6.55)
    ax.set_title("Data center energization requests by vintage and tier, against CAISO's record peak and existing data center load\nThree source families with different utilities, stage definitions and dates: not one consistent growth series", fontsize=9.5)
    ax.legend(fontsize=7, loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.16), frameon=False)
    fig.subplots_adjust(bottom=0.30)
    save(fig, "fig2_04_tier_vintages")

    # ------------------------------------------------------------ 5. RQ1 table
    print("5. RQ1 table")
    # CEC marginal totals as published (memo Table 1 / Assembly slide 7): 5,086 / 9,587 / 8,604 = 23,277 MW; the utility rows sum to 23,278.
    # VEA's 2,600 MW of applications are located in Nevada (memo Table 1 footnote), so the California-only pipeline is 20,677 MW.
    vea_nv = 2600.0
    tiers = {"Signed agreements": 5086.0, "Active applications, California": 9587.0 - vea_nv, "Inquiries": 8604.0}
    total = sum(tiers.values())  # California only
    peaks = c2.ced2025_caiso_peaks()
    pl = peaks[peaks.SCENARIO == "Planning_Scenario"].set_index("YEAR")
    growth_peak_2030 = float(pl.loc[2030, "MANAGED_NET_LOAD"] - pl.loc[2025, "MANAGED_NET_LOAD"])
    growth_base_2030 = float(pl.loc[2030, "BASELINE_CONSUMPTION"] - pl.loc[2025, "BASELINE_CONSUMPTION"])
    dc_at_peak_2030 = float(pl.loc[2030, "DATA_CENTER"]); dc_at_peak_2025 = float(pl.loc[2025, "DATA_CENTER"])
    totals = c2.ced2025_planning_totals(); totals.to_csv(PROCESSED / "ch2_ced2025_planning_totals.csv", index=False)
    en = totals[(totals.metric == "energy_to_serve_load") & (totals.scope == "Statewide total")]
    growth_energy_2030 = float(en.iloc[0]["y2030"] - en.iloc[0]["y2025"]) if len(en) else np.nan
    dcen = totals[(totals.metric == "data_center_deliveries") & (totals.scope.str.startswith("Statewide"))]
    dc_energy_2030 = float(dcen.iloc[0]["y2030"]) if len(dcen) else np.nan
    ch1_2025_peak = 43860.0
    rows = []
    for name, mw in list(tiers.items()) + [("Total, three tiers, California only", total), ("Memo: VEA applications located in Nevada", vea_nv), ("Memo: CEC statewide total including VEA", total + vea_nv)]:
        rows.append({"stage": name, "mw": mw,
                     "share_of_caiso_record_peak_pct": mw / caiso_record_mw * 100,
                     "share_of_caiso_2025_peak_pct": mw / ch1_2025_peak * 100,
                     "multiple_of_existing_dc_peak_1000MW": mw / ex_cec_peak,
                     "multiple_of_existing_dc_avg_load_range": f"{mw/ex_high:.1f}-{mw/ex_low:.1f}",
                     "share_of_IEPR_planning_managed_net_peak_growth_2025_2030_pct": mw / growth_peak_2030 * 100,
                     "share_of_IEPR_planning_baseline_consumption_peak_growth_2025_2030_pct": mw / growth_base_2030 * 100,
                     "expected_demand_at_67pct_utilization_mw": mw * 0.67,
                     "expected_demand_share_of_managed_net_peak_growth_pct": mw * 0.67 / growth_peak_2030 * 100,
                     "energy_equivalent_GWh_at_67pct_util_and_0p88_lf": mw * 0.67 * 0.88 * 8760 / 1000,
                     "energy_share_of_IEPR_statewide_energy_growth_2025_2030_pct": (mw * 0.67 * 0.88 * 8760 / 1000) / growth_energy_2030 * 100})
    rq1 = pd.DataFrame(rows); rq1.to_csv(PROCESSED / "ch2_rq1_table.csv", index=False)
    denom = {"caiso_record_peak_mw": caiso_record_mw, "caiso_record_hourly_eia930_mw": caiso_record_hourly, "caiso_2025_peak_mw": ch1_2025_peak,
             "existing_dc_peak_mw_cec": ex_cec_peak, "existing_dc_avg_load_mw_low": ex_low, "existing_dc_avg_load_mw_high": ex_high,
             "iepr_planning_caiso_managed_net_peak_2025_mw": float(pl.loc[2025, "MANAGED_NET_LOAD"]), "iepr_planning_caiso_managed_net_peak_2030_mw": float(pl.loc[2030, "MANAGED_NET_LOAD"]),
             "iepr_planning_caiso_baseline_consumption_peak_2025_mw": float(pl.loc[2025, "BASELINE_CONSUMPTION"]), "iepr_planning_caiso_baseline_consumption_peak_2030_mw": float(pl.loc[2030, "BASELINE_CONSUMPTION"]),
             "iepr_planning_data_center_at_caiso_peak_2025_mw": dc_at_peak_2025, "iepr_planning_data_center_at_caiso_peak_2030_mw": dc_at_peak_2030,
             "iepr_planning_statewide_energy_growth_2025_2030_GWh": growth_energy_2030, "iepr_planning_statewide_data_center_deliveries_2030_GWh": dc_energy_2030,
             "iepr_planning_statewide_data_center_deliveries_2025_GWh": float(dcen.iloc[0]["y2025"]) if len(dcen) else np.nan,
             "iepr_planning_statewide_energy_2025_GWh": float(en.iloc[0]["y2025"]), "iepr_planning_statewide_energy_2030_GWh": float(en.iloc[0]["y2030"]),
             "total_tiers_mw": total, "total_tiers_mw_california": total, "vea_nevada_applications_mw": vea_nv, "total_tiers_mw_cec_incl_vea": total + vea_nv,
             "ratio_total_to_caiso_record_peak": total / caiso_record_mw, "ratio_cec_total_incl_vea_to_caiso_record_peak": (total + vea_nv) / caiso_record_mw,
             "ratio_total_to_caiso_record_hourly": total / caiso_record_hourly, "ratio_total_to_existing_dc_peak": total / ex_cec_peak,
             "ratio_total_to_existing_dc_avg_load_low": total / ex_high, "ratio_total_to_existing_dc_avg_load_high": total / ex_low}
    (PROCESSED / "ch2_rq1_denominators.json").write_text(json.dumps(denom, indent=1))
    print(json.dumps(denom, indent=1))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
