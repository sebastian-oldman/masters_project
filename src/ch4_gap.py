"""Chapter 4: putting it together (RQ2, RQ3, RQ4).

Demand scenarios for 2030 (proposal upper bound, CEC central, an ERCOT-calibrated stock-flow case, a PJM-style firm-only case) on
top of the IEPR's low/mid/high non-data-center growth; the Monte Carlo gap model with one-at-a-time and Sobol sensitivity; the
Duke-style curtailment-enabled headroom replication on CAISO hourly load; and a flat-versus-flexible emissions comparison.
Regime crosswalk tables live in src/ch4_regimes.py. Every transcribed number carries its manifest source id.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.ch1_baseline import raw_path
from src.paths import PROCESSED

HORIZON = 2030
BASE_YEAR = 2025
MONTHS_TO_HORIZON = 60  # December 2025 tier vintage to December 2030
HOURS = 8760
TIERS = ["Signed agreement", "Active application", "Inquiry"]
TIER_KEY = {"Signed agreement": "Agreement", "Active application": "Application", "Inquiry": "Inquiry"}  # names used in the CEC parameter file


# =============================================================================== 1. California tiers, CEC parameters, CED 2025 scenarios
def ca_tiers(vintage: str = "2025-12", exclude_utilities=("VEA",)) -> pd.DataFrame:
    """Requested capacity by tier (MW) at the December 2025 vintage. The headline uses the CEC's published statewide tier totals
    (5,086 / 9,587 / 8,604 MW) minus the utilities outside California (VEA, Nevada), which reproduces chapter 2's 20,677 MW; the sum of
    the utility rows in the memo's Table 1 is carried as a check (it differs by 1 MW of rounding in the inquiry tier)."""
    t = pd.read_csv(PROCESSED / "ch2_tier_vintages.csv"); t = t[t.vintage == vintage]
    pub = pd.read_csv(PROCESSED / "cec_data_center_tiers_transcription.csv"); pub = pub[pub.vintage == "2025 IEPR final tiers"].set_index("tier_or_item").value_mw
    published = {"Signed agreement": float(pub["Signed Agreements"]), "Active application": float(pub["Active Applications"]), "Inquiry": float(pub["Inquiries"])}
    rows = []
    for tier in TIERS:
        sub = t[t.tier == tier]; nev = float(sub[sub.utility.isin(exclude_utilities)].mw.sum())
        rows.append({"tier": tier, "mw_california": published[tier] - nev, "mw_all_reporting": published[tier], "mw_excluded_nevada": nev,
                     "utility_rows_california_mw": float(sub[~sub.utility.isin(exclude_utilities)].mw.sum()),
                     "source": "cec_assembly_hearing_2026_01_28 p.7 statewide tier totals; cec_dc_methodology_memo_2026 Table 1 utility rows (VEA excluded)"})
    return pd.DataFrame(rows)


def tiers_by_utility(vintage: str = "2025-12") -> pd.DataFrame:
    """Requested MW by utility and tier at the vintage (memo Table 1 rows)."""
    t = pd.read_csv(PROCESSED / "ch2_tier_vintages.csv"); t = t[t.vintage == vintage]
    return t.pivot(index="utility", columns="tier", values="mw").fillna(0.0)[TIERS]


CEC_ENDPOINTS_2040 = {"Planning": 4855.0, "Local Reliability": 7381.0}  # cec_dc_methodology_memo_2026 Figures 4 and 5 (statewide incremental demand in 2040)


def cec_forecast_replication(params: dict, dc_comp: pd.DataFrame, exclude_utilities=("VEA",)) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Rebuild the CEC forecast from its published parameters: confidence by tier x 67% utilization, with SVP's requests exempt from the
    confidence levels (memo p. 9), which reproduces the memo's 2040 endpoints; then apply the CEC's own ramp profile, the share of the
    2040 CAISO data center component reached in each year, to obtain 2030. Returns (summary by scenario, ramp profile, effective tier probabilities)."""
    by_u = tiers_by_utility(); util = params["utilization"]; conf = params["confidence"]
    caiso = dc_comp[(dc_comp.tac == "CAISO")].set_index(["scenario", "year"]).data_center_mw
    rows, eff = [], {}
    for scen, key in (("Planning", "mid"), ("Local Reliability", "high")):
        full_all, full_ca, weighted = 0.0, 0.0, {t: 0.0 for t in TIERS}
        for u, r in by_u.iterrows():
            for t in TIERS:
                c = 1.0 if u == "SVP" else conf[(TIER_KEY[t], key)]
                full_all += r[t] * c * util
                if u not in exclude_utilities:
                    full_ca += r[t] * c * util; weighted[t] += r[t] * c
        ca_tot = by_u.drop(index=[u for u in exclude_utilities if u in by_u.index])[TIERS].sum()
        eff[scen] = {t: weighted[t] / ca_tot[t] for t in TIERS}
        ramp30 = float(caiso[(scen, HORIZON)] / caiso[(scen, 2040)])
        vea = dc_comp[(dc_comp.tac == "VEA") & (dc_comp.scenario == scen) & (dc_comp.year == HORIZON)].data_center_mw.iloc[0]
        rows.append({"scenario": scen, "full_ramp_statewide_mw": full_all, "memo_endpoint_2040_mw": CEC_ENDPOINTS_2040[scen], "difference_mw": full_all - CEC_ENDPOINTS_2040[scen],
                     "full_ramp_california_mw": full_ca, "ramp_share_2030": ramp30, "replicated_2030_california_mw": full_ca * ramp30,
                     "published_2030_caiso_mw": float(caiso[(scen, HORIZON)]), "published_2030_vea_mw": float(vea), "published_2030_california_mw": float(caiso[(scen, HORIZON)] - vea),
                     **{f"effective_p_{TIER_KEY[t].lower()}": eff[scen][t] for t in TIERS}})
    prof = []
    for scen in ("Planning", "Local Reliability"):
        for y in range(2025, 2041):
            prof.append({"scenario": scen, "year": y, "caiso_data_center_mw": float(caiso[(scen, y)]), "share_of_2040": float(caiso[(scen, y)] / caiso[(scen, 2040)])})
    pr = pd.DataFrame(prof); pr["year"] = pr["year"].astype("Int64")
    return pd.DataFrame(rows), pr, eff


def cec_parameters() -> dict:
    p = pd.read_csv(PROCESSED / "cec_data_center_forecast_parameters.csv")
    conf = {(r.tier, r.scenario): float(r.value) for _, r in p[p.parameter == "confidence_level"].iterrows()}
    util = float(p[(p.parameter == "utilization_factor")].value.iloc[0])
    return {"confidence": conf, "utilization": util, "ramp_years": 7, "group1_start_year": 2026, "group23_start_year": 2028,
            "load_factor_range": (0.85, 0.90),
            "basis": "cec_dc_methodology_memo_2026 Table 2 (p. 8-9): 67% utilization; confidence 70/33/0 (Planning) and 100/50/10 (Local Reliability); "
                     "linear ramp over 7 years; Group 2 start dates without a signed agreement moved to 2028; hourly load factors 85-90% of annual maximum (p. 11)"}


CED_FORMS = {"Planning": "cec_tn268727", "Baseline": "cec_tn268722", "Local Reliability": "cec_tn268725", "Local Reliability plus known": "cec_tn268726"}
GROWTH_CASES = [("low", "Planning"), ("mid", "Baseline"), ("high", "Local Reliability"), ("high plus known loads", "Local Reliability plus known")]


def _form_rows(sheet: pd.DataFrame, labels: dict[str, str]) -> dict[str, pd.Series]:
    """Pick labelled rows out of a CED form sheet; the header row holds the forecast years from column 2."""
    hdr = next(i for i in range(15) if pd.to_numeric(sheet.iloc[i, 2:8], errors="coerce").between(2020, 2050).all())
    years = [int(v) for v in sheet.iloc[hdr, 2:].tolist() if pd.notna(v) and str(v).replace(".0", "").isdigit()]
    col0 = sheet.iloc[:, 0].astype(str).str.strip()
    out = {}
    for key, label in labels.items():
        m = sheet[col0 == label]
        if len(m) == 0:
            raise KeyError(f"row '{label}' not found")
        out[key] = pd.Series(pd.to_numeric(m.iloc[0, 2:2 + len(years)], errors="coerce").values, index=years)
    return out


def ced2025_scenarios() -> pd.DataFrame:
    """Energy to serve load (Form 1.5a) and 1-in-2 coincident peaks (Form 1.5b), CAISO and statewide, for the four CED 2025 workbooks."""
    rows = []
    for scen, sid in CED_FORMS.items():
        x = pd.ExcelFile(raw_path(sid))
        e = _form_rows(x.parse("Form 1.5a", header=None), {"energy_caiso_GWh": "Total California ISO", "energy_statewide_GWh": "Total STATEWIDE"})
        p = _form_rows(x.parse("Form 1.5b", header=None), {"peak_caiso_coincident_MW": "Total California ISO Coincident Peak", "peak_statewide_coincident_MW": "Total STATEWIDE Coincident Peak",
                                                           "peak_statewide_noncoincident_MW": "Total STATEWIDE Noncoincident Peak"})
        for metric, s in {**e, **p}.items():
            for y, v in s.items():
                rows.append({"scenario": scen, "metric": metric, "year": int(y), "value": float(v), "source": f"{sid} {'Form 1.5a' if 'energy' in metric else 'Form 1.5b'}"})
    d = pd.DataFrame(rows); d["year"] = d["year"].astype("Int64")
    return d


def ced2025_data_center_component() -> pd.DataFrame:
    """DATA_CENTER component of the coincident peak by scenario, TAC area and year (TN 268124 annual_peaks). The Baseline workbook
    carries the Planning data center component (its CAISO peak equals the Planning BASELINE_NET_LOAD), so it is copied."""
    a = pd.read_excel(raw_path("cec_tn268124"), sheet_name="annual_peaks")
    a = a[a.COINCIDENT == True]  # noqa: E712
    name = {"Planning_Scenario": "Planning", "Local_Reliability": "Local Reliability", "Local_Reliability_plusKnown": "Local Reliability plus known"}
    d = pd.DataFrame({"scenario": a.SCENARIO.map(name), "tac": a.TAC, "year": a.YEAR.astype(int), "data_center_mw": a.DATA_CENTER.astype(float),
                      "other_adjustments_mw": a.OTHER_ADJUSTMENTS.astype(float), "baseline_net_load_mw": a.BASELINE_NET_LOAD.astype(float),
                      "managed_net_load_mw": a.MANAGED_NET_LOAD.astype(float), "source": "cec_tn268124 annual_peaks"})
    b = d[d.scenario == "Planning"].copy(); b["scenario"] = "Baseline"; b["source"] = "cec_tn268124 annual_peaks (Planning component; Baseline = Planning before AAEE/AAFS)"
    d = pd.concat([d, b], ignore_index=True); d["year"] = d["year"].astype("Int64")
    return d


def ced2025_data_center_energy(dc_comp: pd.DataFrame) -> pd.DataFrame:
    """Data center deliveries (GWh) by scenario and year: TN 268824 Form 1.1c for the Planning forecast; other scenarios scaled by the
    ratio of their CAISO data center peak component to the Planning component in the same year."""
    t = pd.read_csv(PROCESSED / "ch2_ced2025_planning_totals.csv")
    r = t[(t.metric == "data_center_deliveries") & t.scope.str.startswith("Statewide")].iloc[0]
    plan = {int(c[1:]): float(r[c]) for c in t.columns if c.startswith("y") and pd.notna(r[c])}
    caiso = dc_comp[dc_comp.tac == "CAISO"].set_index(["scenario", "year"]).data_center_mw
    rows = []
    for scen in CED_FORMS:
        for y, gwh in sorted(plan.items()):
            if y not in caiso.loc["Planning"].index:
                continue
            ratio = 1.0 if scen in ("Planning", "Baseline") else float(caiso[(scen, y)] / caiso[("Planning", y)])
            rows.append({"scenario": scen, "year": y, "data_center_gwh": gwh * ratio, "scale_to_planning": ratio,
                         "basis": "cec_tn268824 Form 1.1c data center deliveries" + ("" if ratio == 1.0 else "; scaled by CAISO data center peak ratio (cec_tn268124)")})
    d = pd.DataFrame(rows); d["year"] = d["year"].astype("Int64")
    return d


def iepr_growth_cases(scen: pd.DataFrame, dc_comp: pd.DataFrame, dc_energy: pd.DataFrame) -> pd.DataFrame:
    """Non-data-center demand in 2025 and 2030 by IEPR case: statewide energy to serve load and coincident peak minus the CEC's own
    data center component (energy from TN 268824, peak from the CAISO DATA_CENTER column, which includes VEA's Nevada requests)."""
    rows = []
    for case, s in GROWTH_CASES:
        E = scen[(scen.scenario == s) & (scen.metric == "energy_statewide_GWh")].set_index("year").value
        P = scen[(scen.scenario == s) & (scen.metric == "peak_statewide_coincident_MW")].set_index("year").value
        Pc = scen[(scen.scenario == s) & (scen.metric == "peak_caiso_coincident_MW")].set_index("year").value
        Ec = scen[(scen.scenario == s) & (scen.metric == "energy_caiso_GWh")].set_index("year").value
        dcp = dc_comp[(dc_comp.scenario == s) & (dc_comp.tac == "CAISO")].set_index("year").data_center_mw
        dcv = dc_comp[(dc_comp.scenario == s) & (dc_comp.tac == "VEA")].set_index("year").data_center_mw
        dce = dc_energy[dc_energy.scenario == s].set_index("year").data_center_gwh
        for y in (BASE_YEAR, HORIZON):
            rows.append({"case": case, "scenario": s, "year": y, "energy_statewide_GWh": float(E[y]), "dc_energy_GWh": float(dce[y]), "energy_non_dc_GWh": float(E[y] - dce[y]),
                         "peak_statewide_MW": float(P[y]), "dc_peak_caiso_MW": float(dcp[y]), "dc_peak_vea_MW": float(dcv[y]), "peak_non_dc_MW": float(P[y] - dcp[y]),
                         "caiso_peak_MW": float(Pc[y]), "caiso_energy_GWh": float(Ec[y])})
    d = pd.DataFrame(rows); d["year"] = d["year"].astype("Int64")
    return d


def growth_summary(g: pd.DataFrame) -> pd.DataFrame:
    out = []
    for case, sub in g.groupby("case", sort=False):
        a, b = sub[sub.year == BASE_YEAR].iloc[0], sub[sub.year == HORIZON].iloc[0]
        out.append({"case": case, "scenario": a.scenario, "energy_non_dc_2025_GWh": a.energy_non_dc_GWh, "energy_non_dc_2030_GWh": b.energy_non_dc_GWh,
                    "energy_non_dc_growth_GWh": b.energy_non_dc_GWh - a.energy_non_dc_GWh, "peak_non_dc_2025_MW": a.peak_non_dc_MW, "peak_non_dc_2030_MW": b.peak_non_dc_MW,
                    "peak_non_dc_growth_MW": b.peak_non_dc_MW - a.peak_non_dc_MW, "cec_dc_peak_2030_MW": b.dc_peak_caiso_MW, "cec_dc_energy_2030_GWh": b.dc_energy_GWh,
                    "energy_total_2030_GWh": b.energy_statewide_GWh, "peak_total_2030_MW": b.peak_statewide_MW})
    return pd.DataFrame(out)


# =============================================================================== 2. ERCOT large load queue transcriptions
# Values read from the charts and text of the ERCOT documents in the raw store (manifest ids in each row). Monthly totals are the
# "Tracked Large Load Projects (MW)" bars; the two November 2025 values are the same month from two decks issued three months apart.
ERCOT_QUEUE_MONTHLY = [
    ("2025-01", 72920, 10710, "ercot_board_2025_12_system_planning", "slide 3 chart, snapshots through Nov 18 2025"),
    ("2025-02", 85826, 13221, "ercot_board_2025_12_system_planning", ""), ("2025-03", 96502, 14703, "ercot_board_2025_12_system_planning", ""),
    ("2025-04", 121927, 14698, "ercot_board_2025_12_system_planning", ""), ("2025-05", 144571, 25044, "ercot_board_2025_12_system_planning", ""),
    ("2025-06", 147784, 25043, "ercot_board_2025_12_system_planning", ""), ("2025-07", 155964, 26443, "ercot_board_2025_12_system_planning", ""),
    ("2025-08", 163851, 25477, "ercot_board_2025_12_system_planning", ""), ("2025-09", 168009, 27413, "ercot_board_2025_12_system_planning", ""),
    ("2025-10", 180187, 31907, "ercot_board_2025_12_system_planning", ""), ("2025-11", 193863, 31953, "ercot_board_2025_12_system_planning", "as of Nov 18 2025"),
    ("2025-11", 198649, 32150, "ercot_tac_2026_03_large_load_status", "slide 2 chart 'Large Load Queue - Past 12 Months'; later snapshot of November"),
    ("2025-12", 202475, 34714, "ercot_tac_2026_03_large_load_status", ""), ("2026-01", 204448, 28677, "ercot_tac_2026_03_large_load_status", ""),
    ("2026-02", 213105, 28643, "ercot_tac_2026_03_large_load_status", ""), ("2026-03", 210114, 28515, "ercot_tac_2026_03_large_load_status", "before the 137 new submissions (~140 GW) of March 2026"),
]
ERCOT_APPROVALS_MONTHLY = [  # (month, planning studies approved MW, approved to energize MW); source ercot_tac_2026_03_large_load_status slide 4
    ("2025-05", 12905, 6874), ("2025-06", 13049, 6874), ("2025-07", 13979, 7150), ("2025-08", 13171, 7502), ("2025-09", 13276, 7502), ("2025-10", 13456, 7502),
    ("2025-11", 14361, 7712), ("2025-12", 13452, 8786), ("2026-01", 15093, 8786), ("2026-02", 15855, 9042), ("2026-03", 16615, 9042),
]
ERCOT_STATUSES = ["No studies submitted", "Under ERCOT review", "Planning studies approved", "Approved to energize, not operational", "Observed energized"]
_S = ERCOT_STATUSES
ERCOT_STATUS_SNAPSHOTS = {  # cumulative MW by in-service year (the 'Actual and Projected Large Load Growth' charts), by status
    ("TAC report", "2026-03-13", "ercot_tac_2026_03_large_load_status", "slide 3 table (MW)"): {
        "years": [2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030],
        _S[0]: [0, 0, 0, 0, 2704, 20341, 53546, 95879, 130303], _S[1]: [0, 0, 0, 0, 7353, 28454, 48171, 58831, 79825],
        _S[2]: [0, 0, 0, 0, 3181, 9164, 14348, 17180, 19482], _S[3]: [0, 0, 0, 946, 2759, 2952, 2952, 3252, 3252], _S[4]: [2634, 4286, 4845, 5768, 5768, 5768, 5768, 5768, 5768]},
    ("House hearing", "2026-03-26", "ercot_house_hearing_2026_04_09", "slide 3 table (MW); after the March 2026 submissions"): {
        "years": [2025, 2026, 2027, 2028, 2029, 2030],
        _S[0]: [0, 25253, 101702, 177879, 238188, 293651], _S[1]: [0, 6478, 30539, 51315, 61966, 86605], _S[2]: [30, 3181, 10739, 15923, 19040, 21343],
        _S[3]: [935, 2748, 2941, 2941, 3241, 3241], _S[4]: [5778] * 6},
    ("ERCOT Monthly", "2026-05-13", "ercot_monthly_2026_04", "p. 4 table (GW, 'Section 9.5 Requirements Met' mapped to planning studies approved); newsletter posted May 13 2026"): {
        "years": list(range(2022, 2034)),
        _S[0]: [0, 0, 0, 0, 24900, 99700, 184400, 251300, 291600, 309200, 316600, 321000], _S[1]: [0, 0, 0, 0, 6400, 29300, 50600, 65600, 87300, 91300, 92600, 93700],
        _S[2]: [0, 0, 0, 0, 3300, 10600, 16100, 18400, 21500, 21700, 21900, 22000], _S[3]: [0, 0, 0, 900, 2700, 2900, 2900, 3200, 3200, 3200, 3200, 3200],
        _S[4]: [2600, 4300, 4800, 5900, 5900, 5900, 5900, 5900, 5900, 5900, 5900, 5900]},
    ("Operational overview", "2026-04-30", "ercot_ops_overview_2026_04", "slide 9 table (GW; 'Section 9.4 only' plus 'Section 9.4/9.5 met' mapped to planning studies approved); the same chart is slide 2 of the June 1 2026 board deck (ercot_board_2026_05_interconnection_update)"): {
        "years": list(range(2022, 2034)),
        _S[0]: [0, 0, 0, 0, 26900, 122600, 232300, 282900, 311100, 321100, 321400, 321400], _S[1]: [0, 0, 0, 0, 8900, 43300, 60100, 70000, 80200, 80200, 80200, 80200],
        _S[2]: [0, 0, 0, 0, 8700, 19900, 25100, 27500, 27500, 27500, 27500, 27500], _S[3]: [0, 300, 1400, 3000, 3100, 3100, 3100, 3100, 3100, 3100, 3100, 3100],
        _S[4]: [2600, 4500, 5000, 5800, 5900, 5900, 5900, 5900, 5900, 5900, 5900, 5900]},
    ("Operational overview", "2026-06-30", "ercot_ops_overview_2026_06", "slide 9 table (GW; same mapping as the June board deck)"): {
        "years": list(range(2022, 2034)),
        _S[0]: [0, 0, 0, 4100, 32300, 102400, 186200, 228800, 242200, 253700, 254000, 254000], _S[1]: [0, 0, 0, 3000, 11000, 48500, 104100, 124500, 135600, 144000, 144000, 144000],
        _S[2]: [0, 0, 0, 0, 12600, 41400, 50400, 54200, 58100, 58100, 58500, 58500], _S[3]: [0, 400, 1800, 3100, 3200, 3200, 3200, 3200, 3200, 3200, 3200, 3200],
        _S[4]: [3300, 4300, 4800, 5700, 5700, 5700, 5700, 5700, 5700, 5700, 5700, 5700]},
    ("Operational overview", "2026-07-31", "ercot_ops_overview_2026_07", "slide 9 table (GW; same mapping)"): {
        "years": list(range(2022, 2034)),
        _S[0]: [0, 0, 0, 4100, 32300, 101000, 180600, 221100, 233100, 244600, 244900, 244900], _S[1]: [0, 0, 0, 3000, 9900, 44500, 94000, 114100, 126500, 132000, 132000, 132000],
        _S[2]: [0, 0, 0, 0, 15300, 48600, 67100, 73700, 77600, 80600, 81000, 81000], _S[3]: [0, 400, 1800, 3200, 3700, 3700, 3700, 3700, 3700, 3700, 3700, 3700],
        _S[4]: [3300, 4300, 4800, 5700, 5700, 5700, 5700, 5700, 5700, 5700, 5700, 5700]},
}
ERCOT_NARRATIVE = [  # (as of, metric, MW, source id, quote)
    ("2024-12-31", "tracked large load requests", 63000, "ercot_monthly_2025_07", "156,000 MW ... compared to 63,000 MW in December of 2024"),
    ("2024-10-31", "tracked large load requests", 56000, "ercot_monthly_2025_10", "approximately 205 GW ... up from just 56 GW a year ago"),
    ("2025-06-30", "tracked large load requests", 156000, "ercot_monthly_2025_07", "As of June 2025, ERCOT is tracking approximately 156,000 MW"),
    ("2025-10-31", "tracked large load requests", 205000, "ercot_monthly_2025_10", "approximately 205 GW ... roughly 70% ... data centers"),
    ("2025-11-18", "tracked large load requests", 226000, "ercot_monthly_2025_11", "approximately 226,000 MW ... 128,000 MW have not yet submitted their Planning Studies"),
    ("2025-11-18", "no studies submitted", 128000, "ercot_monthly_2025_11", "same"),
    ("2025-11-18", "approved to energize", 7500, "ercot_monthly_2025_11", "approximately 7,500 MW ... approved to energize, with 5,300 MW having been observed energized and an additional 2,200 MW ... not yet operational"),
    ("2025-11-18", "observed energized", 5300, "ercot_monthly_2025_11", "same"),
    ("2025-11-18", "approved to energize, not operational", 2200, "ercot_monthly_2025_11", "same"),
    ("2026-01-21", "tracked large load requests", 232500, "ercot_monthly_2026_01", "approximately 232,500 megawatts ... after project cancellations in December"),
    ("2026-01-21", "approved to energize", 8786, "ercot_monthly_2026_01", "8,786 MW of large load demand has received approval to energize"),
    ("2026-01-31", "observed monthly non-simultaneous peak", 3977, "ercot_monthly_2026_01", "non-simultaneous peak demand of 3,977 MW ... additional 4,809 MW approved to energize but not yet observed operational"),
    ("2026-02-28", "tracked large load requests", 232000, "ercot_monthly_2026_02", "over 232,000 MW currently in the large load interconnection process"),
    ("2026-03-13", "approved to energize", 9042, "ercot_tac_2026_03_large_load_status", "Of the 9042 MW that have received Approval to Energize ... non-simultaneous monthly peak consumption of 3883 MW"),
    ("2026-03-13", "observed monthly non-simultaneous peak", 3883, "ercot_tac_2026_03_large_load_status", "same"),
    ("2026-03-26", "tracked large load requests", 410618, "ercot_house_hearing_2026_04_09", "approximately 410 GW ... of which ~87% are data centers; increase of 178 GW since the end of 2025"),
    ("2026-04-30", "tracked large load requests", 445800, "ercot_monthly_2026_04", "applications of large loads now totaling 445.8 gigawatts (GW) by 2033"),
    ("2026-05-31", "tracked large load requests", 438000, "ercot_board_2026_05_interconnection_update", "ERCOT is tracking 438 GW of Large Load Interconnection Requests"),
    ("2026-06-30", "tracked large load requests", 465500, "ercot_ops_overview_2026_06", "slide 9 chart total by 2033"),
    ("2026-06-30", "approved to energize", 8926, "ercot_ops_overview_2026_06", "Of the 8,926 MW that have received Approval to Energize ... 3,966 MW in June 2026"),
    ("2026-06-30", "observed monthly non-simultaneous peak", 3966, "ercot_ops_overview_2026_06", "same"),
    ("2026-06-30", "batch zero requested load", 450000, "ercot_monthly_2026_06", "roughly 450+ gigawatts (GW) of requested load ... roughly 100+ GW to qualify as Base or Studied Load"),
    ("2026-04-30", "approved to energize", 9012, "ercot_ops_overview_2026_04", "Of the 9,012 MW that have received Approval to Energize ... 4,006 MW in April 2026"),
    ("2026-04-30", "observed monthly non-simultaneous peak", 4006, "ercot_ops_overview_2026_04", "same"),
    ("2026-07-31", "tracked large load requests", 467400, "ercot_ops_overview_2026_07", "slide 9 chart total by 2033"),
    ("2026-07-31", "approved to energize", 9456, "ercot_ops_overview_2026_07", "Of the 9,456 MW that have received Approval to Energize ... 4,370 MW in July 2026"),
    ("2026-07-31", "observed monthly non-simultaneous peak", 4370, "ercot_ops_overview_2026_07", "same"),
    ("2026-08-31", "approved to energize", 9456, "ercot_ops_overview_2026_08", "Of the 9,456 MW that have received Approval to Energize ... 4,316 MW in August 2026"),
    ("2026-08-31", "observed monthly non-simultaneous peak", 4316, "ercot_ops_overview_2026_08", "same"),
]


def ercot_series() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    q = pd.DataFrame(ERCOT_QUEUE_MONTHLY, columns=["month", "standalone_mw", "colocated_mw", "source", "note"]); q["total_mw"] = q.standalone_mw + q.colocated_mw
    a = pd.DataFrame(ERCOT_APPROVALS_MONTHLY, columns=["month", "planning_studies_approved_mw", "approved_to_energize_mw"]); a["source"] = "ercot_tac_2026_03_large_load_status slide 4"
    rows = []
    for (label, as_of, sid, note), d in ERCOT_STATUS_SNAPSHOTS.items():
        for st in ERCOT_STATUSES:
            for y, v in zip(d["years"], d[st]):
                rows.append({"snapshot": label, "as_of": as_of, "source": sid, "note": note, "status": st, "in_service_year_through": y, "mw": float(v)})
    s = pd.DataFrame(rows); s["in_service_year_through"] = s["in_service_year_through"].astype("Int64")
    n = pd.DataFrame(ERCOT_NARRATIVE, columns=["as_of", "metric", "mw", "source", "quote"])
    return q, a, s, n


def ercot_transition_rates(q: pd.DataFrame, a: pd.DataFrame, s: pd.DataFrame, n: pd.DataFrame) -> pd.DataFrame:
    """Monthly hazards between ERCOT phases from the transcribed stocks and flows. Each row records numerator, denominator and window."""
    rows = []
    # planning studies approved -> approved to energize: flow = change in the A2E stock; pool = mean PSA stock over the window
    a2e0, a2e1 = a.approved_to_energize_mw.iloc[0], a.approved_to_energize_mw.iloc[-1]; months = len(a) - 1
    psa_pool = a.planning_studies_approved_mw.iloc[:-1].mean()
    h_psa_a2e = (a2e1 - a2e0) / months / psa_pool
    rows.append({"transition": "Planning studies approved -> approved to energize", "monthly_hazard": h_psa_a2e, "flow_mw": a2e1 - a2e0, "months": months, "pool_mw": psa_pool,
                 "window": f"{a.month.iloc[0]} to {a.month.iloc[-1]}", "derivation": "increase of the approved-to-energize stock divided by months and by the mean planning-studies-approved stock (TAC Mar 2026 slide 4)"})
    # under review -> planning studies approved: gross inflow to PSA = change in PSA stock + outflow to A2E; pool = under-review stock (Nov 18 2025 residual and Mar 13 2026 snapshot)
    psa0, psa1 = a.planning_studies_approved_mw.iloc[0], a.planning_studies_approved_mw.iloc[-1]
    nov = n.set_index(["as_of", "metric"]).mw
    uer_nov = nov[("2025-11-18", "tracked large load requests")] - nov[("2025-11-18", "no studies submitted")] - nov[("2025-11-18", "approved to energize")] - a.set_index("month").planning_studies_approved_mw["2025-11"]
    tac = s[(s.snapshot == "TAC report") & (s.in_service_year_through == 2030)].set_index("status").mw
    uer_pool = np.mean([uer_nov, tac["Under ERCOT review"]])
    gross_psa = (psa1 - psa0) + (a2e1 - a2e0)
    h_uer_psa = gross_psa / months / uer_pool
    rows.append({"transition": "Under ERCOT review -> planning studies approved", "monthly_hazard": h_uer_psa, "flow_mw": gross_psa, "months": months, "pool_mw": uer_pool,
                 "window": f"{a.month.iloc[0]} to {a.month.iloc[-1]}", "derivation": f"change in the planning-studies-approved stock plus the outflow to approved-to-energize, divided by the mean under-review stock ({uer_nov:,.0f} MW residual on Nov 18 2025 and {tac['Under ERCOT review']:,.0f} MW on Mar 13 2026)"})
    # no studies submitted -> under review (or exit): new entries are assumed to enter as 'no studies submitted'
    nss0, nss1 = nov[("2025-11-18", "no studies submitted")], tac["No studies submitted"]
    tot0, tot1 = nov[("2025-11-18", "tracked large load requests")], tac.sum()
    m_win = (pd.Timestamp("2026-03-13") - pd.Timestamp("2025-11-18")).days / 30.44
    outflow = (tot1 - tot0) - (nss1 - nss0)
    h_nss_uer = outflow / m_win / np.mean([nss0, nss1])
    rows.append({"transition": "No studies submitted -> under ERCOT review (or cancellation)", "monthly_hazard": h_nss_uer, "flow_mw": outflow, "months": m_win, "pool_mw": np.mean([nss0, nss1]),
                 "window": "2025-11-18 to 2026-03-13", "derivation": "queue growth minus the change in the no-studies stock (new requests enter without studies); cancellations leave the same stock, so this is an upper bound for advancement"})
    # approved to energize (not operational) -> observed energized: 2025 additions to the observed-energized stock over the mean not-operational stock
    en = s[(s.snapshot == "TAC report") & (s.status == "Observed energized")].set_index("in_service_year_through").mw
    add_2025 = en[2025] - en[2024]
    a2e_nop = a.set_index("month").approved_to_energize_mw - en[2025]  # approved but not yet observed, May 2025 - Mar 2026
    pool_nop = float(np.mean([nov[("2025-11-18", "approved to energize, not operational")], tac["Approved to energize, not operational"], (a2e_nop.clip(lower=0)).mean()]))
    h_a2e_en = add_2025 / 12 / pool_nop
    rows.append({"transition": "Approved to energize -> observed energized", "monthly_hazard": h_a2e_en, "flow_mw": add_2025, "months": 12, "pool_mw": pool_nop,
                 "window": "calendar 2025", "derivation": "2025 addition to the observed-energized stock (all-time non-simultaneous peak, TAC slide 3) over the mean approved-but-not-operational stock"})
    d = pd.DataFrame(rows)
    d["annual_probability"] = 1 - (1 - d.monthly_hazard) ** 12
    return d


def ercot_chain(rates: pd.DataFrame, months: int = MONTHS_TO_HORIZON, cancel_hazard: float = 0.0, scale: float = 1.0) -> pd.DataFrame:
    """Probability of being energized within `months` for a project starting in each ERCOT phase, from a monthly Markov chain with the
    estimated hazards (optionally scaled) and an optional monthly cancellation hazard applied to the three pre-approval phases."""
    h = dict(zip(rates.transition.str.split(" -> ").str[0].str.lower(), (rates.monthly_hazard * scale).clip(0, 1)))
    hn, hu, hp, he = h["no studies submitted"], h["under ercot review"], h["planning studies approved"], h["approved to energize"]
    states = ["No studies submitted", "Under ERCOT review", "Planning studies approved", "Approved to energize", "Energized", "Cancelled"]
    M = np.zeros((6, 6))
    M[0] = [1 - hn - cancel_hazard, hn, 0, 0, 0, cancel_hazard]; M[1] = [0, 1 - hu - cancel_hazard, hu, 0, 0, cancel_hazard]
    M[2] = [0, 0, 1 - hp - cancel_hazard, hp, 0, cancel_hazard]; M[3] = [0, 0, 0, 1 - he, he, 0]; M[4, 4] = 1; M[5, 5] = 1
    P = np.linalg.matrix_power(M, months)
    return pd.DataFrame({"start_state": states[:4], "p_energized": P[:4, 4], "p_cancelled": P[:4, 5], "p_still_in_queue": 1 - P[:4, 4] - P[:4, 5], "months": months, "hazard_scale": scale, "cancel_hazard": cancel_hazard})


TIER_TO_ERCOT = {"Inquiry": "No studies submitted", "Active application": "Under ERCOT review", "Signed agreement": "Planning studies approved"}


# =============================================================================== 3. Demand cases for 2030
def demand_cases_2030(tiers: pd.DataFrame, params: dict, chain: pd.DataFrame, growth: pd.DataFrame, rep: pd.DataFrame | None = None, eff: dict | None = None, load_factor: float = 0.88) -> pd.DataFrame:
    """Data center peak (MW) and energy (TWh) added by 2030 under each counting rule, California-only tiers of December 2025."""
    mw = tiers.set_index("tier").mw_california
    conf = params["confidence"]; util = params["utilization"]; ramp_years = params["ramp_years"]
    r1 = min(1.0, (HORIZON + 1 - params["group1_start_year"]) / ramp_years)   # agreements ramping linearly from the start of 2026
    r23 = min(1.0, (HORIZON + 1 - params["group23_start_year"]) / ramp_years)  # applications and inquiries moved to a 2028 start
    pe = chain.set_index("start_state").p_energized
    g30 = growth.set_index("case")
    rows = []

    def add(case, group, p, u, ramp, lf, basis, dc_mw=None, dc_twh=None):
        weights = {t: p[t] * u * ramp[t] for t in TIERS}
        peak = sum(mw[t] * weights[t] for t in TIERS) if dc_mw is None else dc_mw
        twh = peak * HOURS * lf / 1e6 if dc_twh is None else dc_twh
        rows.append({"case": case, "group": group, **{f"p_{TIER_KEY[t].lower()}": p[t] for t in TIERS}, "utilization": u, **{f"ramp_{TIER_KEY[t].lower()}": ramp[t] for t in TIERS},
                     "load_factor": lf, "dc_peak_mw_2030": peak, "dc_energy_twh_2030": twh, "basis": basis})

    add("Upper bound: every MW builds, flat load", "proposal", {t: 1.0 for t in TIERS}, 1.0, {t: 1.0 for t in TIERS}, 1.0,
        "proposal's bound: all three tiers energized by 2030 at requested capacity, flat (load factor 1)")
    add("Upper bound at CEC utilization", "proposal", {t: 1.0 for t in TIERS}, util, {t: 1.0 for t in TIERS}, load_factor,
        "all tiers energized by 2030, 67% utilization, load factor 0.88")
    add("CEC central (Planning forecast, published)", "CEC", {t: conf[(TIER_KEY[t], "mid")] for t in TIERS}, util, {"Signed agreement": np.nan, "Active application": np.nan, "Inquiry": np.nan}, np.nan,
        "CEC 2025 IEPR Planning forecast: CAISO data center peak component 2030 minus VEA (cec_tn268124); energy from TN 268824 data center deliveries",
        dc_mw=g30.loc["low", "cec_dc_peak_2030_MW"] - _vea_2030("Planning"), dc_twh=g30.loc["low", "cec_dc_energy_2030_GWh"] / 1000)
    rp = rep.set_index("scenario") if rep is not None else None
    if rp is not None:
        add("CEC central, replicated from parameters", "CEC", eff["Planning"], util, {t: float(rp.loc["Planning", "ramp_share_2030"]) for t in TIERS}, load_factor,
            f"confidence 70/33/0 with SVP exempt (effective {eff['Planning']['Signed agreement']:.2f}/{eff['Planning']['Active application']:.2f}/{eff['Planning']['Inquiry']:.2f}) x 67%, which reproduces the memo's 2040 endpoint of {CEC_ENDPOINTS_2040['Planning']:,.0f} MW; the CEC's own ramp profile puts {100*rp.loc['Planning', 'ramp_share_2030']:.0f}% of it on line by 2030")
    else:
        add("CEC central, literal replication", "CEC", {t: conf[(TIER_KEY[t], "mid")] for t in TIERS}, util, {"Signed agreement": r1, "Active application": r23, "Inquiry": r23}, load_factor,
            f"confidence 70/33/0 x 67% x linear 7-year ramp (agreements from 2026: {r1:.2f}; applications and inquiries from 2028: {r23:.2f})")
    add("CEC high (Local Reliability, published)", "CEC", {t: conf[(TIER_KEY[t], "high")] for t in TIERS}, util, {t: np.nan for t in TIERS}, np.nan,
        "CEC 2025 IEPR Local Reliability scenario: CAISO data center peak component 2030 minus VEA; energy scaled from the Planning deliveries",
        dc_mw=g30.loc["high", "cec_dc_peak_2030_MW"] - _vea_2030("Local Reliability"), dc_twh=g30.loc["high", "cec_dc_energy_2030_GWh"] / 1000)
    if rp is not None:
        add("CEC high, replicated from parameters", "CEC", eff["Local Reliability"], util, {t: float(rp.loc["Local Reliability", "ramp_share_2030"]) for t in TIERS}, load_factor,
            f"confidence 100/50/10 with SVP exempt (effective {eff['Local Reliability']['Signed agreement']:.2f}/{eff['Local Reliability']['Active application']:.2f}/{eff['Local Reliability']['Inquiry']:.2f}) x 67%, reproducing the memo's {CEC_ENDPOINTS_2040['Local Reliability']:,.0f} MW; ramp share {100*rp.loc['Local Reliability', 'ramp_share_2030']:.0f}% by 2030")
    else:
        add("CEC high, literal replication", "CEC", {t: conf[(TIER_KEY[t], "high")] for t in TIERS}, util, {"Signed agreement": r1, "Active application": r23, "Inquiry": r23}, load_factor, "confidence 100/50/10 x 67% x the same ramps")
    add("ERCOT-calibrated stock-flow", "ERCOT", {t: float(pe[TIER_TO_ERCOT[t]]) for t in TIERS}, util, {t: 1.0 for t in TIERS}, load_factor,
        "probability of energization within 60 months from the ERCOT monthly hazards (inquiry = no studies submitted, application = under review, agreement = studies approved); 67% utilization; timing inside the chain")
    add("ERCOT-calibrated, ERCOT observed utilization", "ERCOT", {t: float(pe[TIER_TO_ERCOT[t]]) for t in TIERS}, ERCOT_OBSERVED_UTILIZATION, {t: 1.0 for t in TIERS}, load_factor,
        f"same probabilities; utilization = ERCOT observed energized over approved to energize ({ERCOT_OBSERVED_UTILIZATION:.2f}, Mar 2026)")
    add("PJM-style: firm only (signed agreements)", "PJM", {"Signed agreement": 1.0, "Active application": 0.0, "Inquiry": 0.0}, PJM_UTILIZATION, {t: 1.0 for t in TIERS}, load_factor,
        "PJM 2026 rule: only projects with an ESO/construction commitment count before 2030, at 70% utilization and a ramp of at least 36 months (complete by 2030)")
    add("PJM-style: firm plus half of non-firm from 2030", "PJM", {"Signed agreement": 1.0, "Active application": 0.5, "Inquiry": 0.5}, PJM_UTILIZATION, {t: 1.0 for t in TIERS}, load_factor,
        "PJM's 2030-and-later treatment of non-firm requests (50% before national scaling), applied to applications and inquiries")
    return pd.DataFrame(rows)


def demand_totals_2030(cases: pd.DataFrame, growth: pd.DataFrame, load_factor: float = 0.88) -> pd.DataFrame:
    """Every demand case on top of each IEPR non-data-center case: 2030 statewide peak and energy and their growth from 2025."""
    g = growth.set_index("case"); rows = []
    for c in cases.itertuples():
        for case in ("low", "mid", "high"):
            r = g.loc[case]
            rows.append({"demand_case": c.case, "iepr_case": case, "scenario": r.scenario, "non_dc_peak_2030_MW": r.peak_non_dc_2030_MW, "dc_peak_MW": c.dc_peak_mw_2030, "total_peak_2030_MW": r.peak_non_dc_2030_MW + c.dc_peak_mw_2030,
                         "peak_growth_2025_2030_MW": r.peak_non_dc_growth_MW + c.dc_peak_mw_2030, "non_dc_energy_2030_TWh": r.energy_non_dc_2030_GWh / 1000, "dc_energy_TWh": c.dc_energy_twh_2030,
                         "total_energy_2030_TWh": r.energy_non_dc_2030_GWh / 1000 + c.dc_energy_twh_2030, "energy_growth_2025_2030_TWh": r.energy_non_dc_growth_GWh / 1000 + c.dc_energy_twh_2030})
    return pd.DataFrame(rows)


ERCOT_OBSERVED_UTILIZATION = 5768 / 9042  # observed energized (all-time non-simultaneous peak) over approved to energize, March 13 2026
PJM_UTILIZATION = 0.70  # pjm_lar_summary_2025_11_24 slide 4
_VEA = {}


def _vea_2030(scenario: str) -> float:
    if not _VEA:
        d = ced2025_data_center_component()
        for s_, g in d[(d.tac == "VEA") & (d.year == HORIZON)].groupby("scenario"):
            _VEA[s_] = float(g.data_center_mw.iloc[0])
    return _VEA[scenario]


# =============================================================================== 4. Supply model for 2030 (from chapter 3) and the Monte Carlo gap model
class SupplyModel:
    """Existing fleet, planned units with completion probabilities, retirements, capacity factors and ELCCs from chapter 3."""

    def __init__(self):
        cases = pd.read_csv(PROCESSED / "ch3_cases_2030.csv")
        a = cases[cases.case.str.startswith("A")].set_index("resource"); c = cases[cases.case.str.startswith("C")].set_index("resource")
        self.resources = list(a.index)
        self.existing = a.existing_mw.astype(float)
        self.retire = c.retirements_mw.astype(float)  # through 2030 incl. OTC units without EIA dates and Diablo Canyon
        self.diablo_mw = float(c.loc["Nuclear", "retirements_mw"])
        self.cf = pd.read_csv(PROCESSED / "ch3_capacity_factors.csv").set_index("resource").capacity_factor.reindex(self.resources).astype(float)
        self.elcc = pd.read_csv(PROCESSED / "ch3_elcc_values.csv").set_index("resource").elcc.reindex(self.resources).astype(float)
        u = pd.read_csv(PROCESSED / "ch3_planned_current_weighted.csv")
        self.units = u[["key", "resource", "mw", "p_2030"]].reset_index(drop=True)
        self.planned_by_resource = self.units.groupby("resource").mw.sum().reindex(self.resources).fillna(0.0)
        s = pd.read_csv(PROCESSED / "ch3_supply_by_year.csv", index_col=0)
        cap = pd.read_csv(PROCESSED / "ch3_eia860_capacity_by_resource.csv").pivot(index="year", columns="resource", values="nameplate_mw")
        hyd = (s["Hydro"] / ((cap["Large hydro"] + cap["Small hydro"]) * 8.76)).dropna()
        self.hydro_cf_history = hyd  # 2010-2025
        imp = pd.read_csv(PROCESSED / "ch3_cec_imports_by_year.csv"); imp = imp[imp.consistent]
        self.imports_history = ((imp.nw_imports_gwh + imp.sw_imports_gwh) / 1000).set_axis(imp.year)  # TWh, CEC statewide net imports
        self.in_state_2025_twh = float(s.loc[2025, "Total in-state"] / 1000)

    def hydro_mask(self):
        return np.array([r in ("Large hydro", "Small hydro") for r in self.resources])

    def base(self, prm: float = 0.16) -> dict:
        cap = self.existing.values
        e = (cap * 8.76 * self.cf.values / 1000).sum(); elcc = (cap * self.elcc.values).sum()
        return {"capacity_mw": cap.sum(), "in_state_energy_twh": e, "imports_twh": float(self.imports_history.iloc[-1]), "elcc_mw": elcc}

    def evaluate(self, completed_mw: np.ndarray, hydro_cf: np.ndarray, vre_scale: np.ndarray, imports_twh: np.ndarray, diablo_continues: np.ndarray) -> dict:
        """Vectorised over draws. completed_mw: (n, R) MW of planned units completed; other arguments length n."""
        n = completed_mw.shape[0]
        cap = self.existing.values[None, :] + completed_mw - self.retire.values[None, :]
        nuc = self.resources.index("Nuclear")
        cap[:, nuc] += diablo_continues * self.diablo_mw
        cf = np.tile(self.cf.values, (n, 1))
        cf[:, self.hydro_mask()] = hydro_cf[:, None]
        for r in ("Solar", "Wind"):
            cf[:, self.resources.index(r)] *= vre_scale
        energy = (cap * 8.76 * cf / 1000).sum(axis=1)
        elcc = (cap * self.elcc.values[None, :]).sum(axis=1)
        return {"capacity_mw": cap.sum(axis=1), "in_state_energy_twh": energy, "supply_energy_twh": energy + imports_twh, "elcc_mw": elcc}


def tri(rng, low, mode, high, n):
    return rng.triangular(low, mode, high, n)


def mc_inputs(rates_chain: pd.DataFrame, supply: SupplyModel, cec: dict) -> pd.DataFrame:
    """Input distributions of the Monte Carlo, with the evidence behind each bound."""
    pe = rates_chain.set_index("start_state").p_energized
    hy = supply.hydro_cf_history; im = supply.imports_history
    rows = [
        ("p_agreement", "triangular", 0.50, cec["confidence"][("Agreement", "mid")], cec["confidence"][("Agreement", "high")], f"CEC 70% (Planning) to 100% (Local Reliability); lower bound above the ERCOT chain value for studies-approved projects ({pe['Planning studies approved']:.2f})"),
        ("p_application", "triangular", 0.10, cec["confidence"][("Application", "mid")], cec["confidence"][("Application", "high")], f"CEC 33% to 50%; lower bound above the ERCOT chain value for projects under review ({pe['Under ERCOT review']:.2f})"),
        ("p_inquiry", "triangular", 0.00, 0.03, cec["confidence"][("Inquiry", "high")], f"CEC 0% to 10% (0.02 effective in the Planning forecast with SVP exempt); mode above the ERCOT chain value for projects without studies ({pe['No studies submitted']:.2f})"),
        ("utilization", "triangular", 0.46, cec["utilization"], PJM_UTILIZATION, "ERCOT monthly observed peak over approved (4,316 of 9,456 MW, Aug 2026) to PJM's 70%; mode CEC 67%"),
        ("ramp_2030", "triangular", 0.30, 0.55, 1.00, "share of realized capacity on line by end-2030: the CEC's own ramp profile reaches 36% (Planning) and 60% (Local Reliability) of full demand by 2030; PJM's 36-month ramp gives 1.0"),
        ("load_factor", "triangular", 0.80, 0.88, 0.95, "chapter 1 assumption range; CEC observed 85-90% (memo p. 11)"),
        ("gen_realization", "per-unit Bernoulli", np.nan, np.nan, np.nan, "each planned unit completes with its chapter 3 logit probability p_2030 (229 units, 20.1 GW)"),
        ("hydro_cf", "triangular", float(hy.min()), float(hy.loc[2023:2025].mean()), float(hy.max()), f"hydro capacity factor 2010-2025 range {hy.min():.2f}-{hy.max():.2f}, mode 2023-2025 mean"),
        ("vre_scale", "triangular", 0.90, 1.00, 1.10, "solar and wind capacity factors within 10% of their 2023-2025 means"),
        ("imports_twh", "triangular", float(im.loc[2019:].min()), float(im.iloc[-1]), float(im.max()), f"CEC statewide net imports: 2019-2024 minimum {im.loc[2019:].min():.0f}, 2024 value {im.iloc[-1]:.0f}, 2012-2024 maximum {im.max():.0f} TWh"),
        ("iepr_case", "categorical", 0, 1, 2, "low = Planning, mid = Baseline, high = Local Reliability, equal weights"),
        ("diablo_continues", "Bernoulli(0.5)", 0, np.nan, 1, "Diablo Canyon operating in 2030 or retired as in chapter 3 case C: the NRC renewed both licences on April 2 2026, but SB 846 authorises operation only through 2030 and any extension needs legislative action (gov_ca_diablo_license_2026_04_02, nrc_diablo_canyon_rod_2026)"),
        ("prm", "uniform", 0.15, 0.16, 0.17, "planning reserve margin applied to the peak: CPUC resource adequacy range 15-17%"),
    ]
    return pd.DataFrame(rows, columns=["input", "distribution", "low", "mode", "high", "basis"])


def monte_carlo(n: int, tiers: pd.DataFrame, growth: pd.DataFrame, supply: SupplyModel, inputs: pd.DataFrame, seed: int = 20260922) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    q = inputs.set_index("input")
    mw = tiers.set_index("tier").mw_california
    d = {}
    for k in ("p_agreement", "p_application", "p_inquiry", "utilization", "ramp_2030", "load_factor", "hydro_cf", "vre_scale", "imports_twh"):
        d[k] = tri(rng, q.loc[k, "low"], q.loc[k, "mode"], q.loc[k, "high"], n)
    d["iepr_case"] = rng.integers(0, 3, n)
    d["diablo_continues"] = rng.integers(0, 2, n)
    d["prm"] = rng.uniform(q.loc["prm", "low"], q.loc["prm", "high"], n)
    # per-unit completion
    U = supply.units
    bern = rng.random((n, len(U))) < U.p_2030.values[None, :]
    R = len(supply.resources); ridx = np.array([supply.resources.index(r) for r in U.resource])
    completed = np.zeros((n, R))
    for j in range(R):
        cols = ridx == j
        if cols.any():
            completed[:, j] = (bern[:, cols] * U.mw.values[None, cols]).sum(axis=1)
    d["gen_realization"] = completed.sum(axis=1) / U.mw.sum()
    out = evaluate_gap(d, completed, mw, growth, supply)
    return pd.DataFrame({**d, **out})


CASE_NAMES = np.array(["low", "mid", "high"])


def evaluate_gap(d: dict, completed: np.ndarray, mw: pd.Series, growth: pd.DataFrame, supply: SupplyModel) -> dict:
    """Vectorised gap computation shared by the Monte Carlo, the tornado and the Sobol runs."""
    n = len(d["utilization"])
    g = growth.set_index("case")
    dc_mw = (mw["Signed agreement"] * d["p_agreement"] + mw["Active application"] * d["p_application"] + mw["Inquiry"] * d["p_inquiry"]) * d["utilization"] * d["ramp_2030"]
    dc_twh = dc_mw * HOURS * d["load_factor"] / 1e6
    case = CASE_NAMES[np.asarray(d["iepr_case"]).astype(int)]
    dE = g.loc[case, "energy_non_dc_growth_GWh"].values / 1000; dP = g.loc[case, "peak_non_dc_growth_MW"].values
    E30 = g.loc[case, "energy_non_dc_2030_GWh"].values / 1000; P30 = g.loc[case, "peak_non_dc_2030_MW"].values
    base = supply.base()
    s = supply.evaluate(completed, np.asarray(d["hydro_cf"]), np.asarray(d["vre_scale"]), np.asarray(d["imports_twh"]), np.asarray(d["diablo_continues"]).astype(float))
    d_supply_energy = s["supply_energy_twh"] - (base["in_state_energy_twh"] + base["imports_twh"])
    d_elcc = s["elcc_mw"] - base["elcc_mw"]
    gap_energy = dE + dc_twh - d_supply_energy
    gap_peak = (dP + dc_mw) * (1 + np.asarray(d["prm"])) - d_elcc
    abs_energy = (E30 + dc_twh) - s["supply_energy_twh"]
    abs_peak = (P30 + dc_mw) * (1 + np.asarray(d["prm"])) - s["elcc_mw"]
    return {"case_name": case, "dc_peak_mw": dc_mw, "dc_energy_twh": dc_twh, "non_dc_energy_growth_twh": dE, "non_dc_peak_growth_mw": dP,
            "supply_energy_growth_twh": d_supply_energy, "elcc_growth_mw": d_elcc, "supply_energy_2030_twh": s["supply_energy_twh"], "elcc_2030_mw": s["elcc_mw"],
            "capacity_2030_mw": s["capacity_mw"], "gap_energy_twh": gap_energy, "gap_peak_mw": gap_peak, "abs_energy_balance_twh": abs_energy, "abs_peak_balance_mw": abs_peak,
            "demand_energy_2030_twh": E30 + dc_twh, "demand_peak_2030_mw": P30 + dc_mw}


def completed_from_fraction(frac: np.ndarray, supply: SupplyModel, planned_by_resource: pd.Series | None = None) -> np.ndarray:
    """Planned MW completed by resource for a scalar realization fraction (used by the tornado and Sobol runs)."""
    p = (supply.planned_by_resource if planned_by_resource is None else planned_by_resource).values
    return np.asarray(frac)[:, None] * p[None, :]


def summarize(draws: pd.DataFrame, cols=("gap_energy_twh", "gap_peak_mw", "dc_peak_mw", "dc_energy_twh", "abs_energy_balance_twh", "abs_peak_balance_mw")) -> pd.DataFrame:
    rows = []
    for name, sub in [("all cases", draws)] + [(c, draws[draws.case_name == c]) for c in CASE_NAMES]:
        for c in cols:
            v = sub[c].values
            rows.append({"iepr_case": name, "metric": c, "n": len(v), "mean": v.mean(), "p05": np.percentile(v, 5), "p25": np.percentile(v, 25), "p50": np.percentile(v, 50),
                         "p75": np.percentile(v, 75), "p95": np.percentile(v, 95), "share_positive": (v > 0).mean()})
    return pd.DataFrame(rows)


def upper_bound_rows(tiers: pd.DataFrame, growth: pd.DataFrame, supply: SupplyModel, inputs: pd.DataFrame) -> pd.DataFrame:
    """The proposal's upper bound evaluated deterministically for each IEPR case at the central supply (chapter 3 case B, imports at 2024)."""
    q = inputs.set_index("input"); mw = tiers.set_index("tier").mw_california
    rows = []
    for i, case in enumerate(CASE_NAMES):
        for diablo in (0.0, 1.0):
            d = {"p_agreement": np.array([1.0]), "p_application": np.array([1.0]), "p_inquiry": np.array([1.0]), "utilization": np.array([1.0]), "ramp_2030": np.array([1.0]), "load_factor": np.array([1.0]),
                 "hydro_cf": np.array([q.loc["hydro_cf", "mode"]]), "vre_scale": np.array([1.0]), "imports_twh": np.array([q.loc["imports_twh", "mode"]]), "iepr_case": np.array([i]),
                 "diablo_continues": np.array([diablo]), "prm": np.array([q.loc["prm", "mode"]])}
            comp = completed_from_fraction(np.array([supply.units.assign(w=lambda x: x.mw * x.p_2030).w.sum() / supply.units.mw.sum()]), supply)
            out = evaluate_gap(d, comp, mw, growth, supply)
            rows.append({"iepr_case": case, "diablo_continues": bool(diablo), **{k: float(v[0]) for k, v in out.items() if k != "case_name"}})
    return pd.DataFrame(rows)


def tornado(tiers: pd.DataFrame, growth: pd.DataFrame, supply: SupplyModel, inputs: pd.DataFrame, draws: pd.DataFrame) -> pd.DataFrame:
    """One-at-a-time: each input at its 5th and 95th percentile (categorical: low and high case, Diablo retired and continuing) with the others at their medians."""
    q = inputs.set_index("input"); mw = tiers.set_index("tier").mw_california
    cont = ["p_agreement", "p_application", "p_inquiry", "utilization", "ramp_2030", "load_factor", "hydro_cf", "vre_scale", "imports_twh", "prm", "gen_realization"]
    med = {k: float(np.median(draws[k])) for k in cont}
    med["iepr_case"] = 1; med["diablo_continues"] = 0.5
    def run(over: dict) -> dict:
        d = {k: np.array([over.get(k, med[k])]) for k in cont + ["iepr_case", "diablo_continues"]}
        comp = completed_from_fraction(d.pop("gen_realization"), supply)
        return evaluate_gap(d, comp, mw, growth, supply)
    base = run({})
    rows = []
    for k in cont + ["iepr_case", "diablo_continues"]:
        if k == "iepr_case":
            lo, hi = 0, 2
        elif k == "diablo_continues":
            lo, hi = 0.0, 1.0
        else:
            lo, hi = float(np.percentile(draws[k], 5)), float(np.percentile(draws[k], 95))
        a, b = run({k: lo}), run({k: hi})
        rows.append({"input": k, "low_value": lo, "high_value": hi, "gap_energy_low": float(a["gap_energy_twh"][0]), "gap_energy_high": float(b["gap_energy_twh"][0]),
                     "gap_peak_low": float(a["gap_peak_mw"][0]), "gap_peak_high": float(b["gap_peak_mw"][0]), "base_gap_energy": float(base["gap_energy_twh"][0]), "base_gap_peak": float(base["gap_peak_mw"][0])})
    t = pd.DataFrame(rows)
    t["swing_energy"] = (t.gap_energy_high - t.gap_energy_low).abs(); t["swing_peak"] = (t.gap_peak_high - t.gap_peak_low).abs()
    return t.sort_values("swing_energy", ascending=False).reset_index(drop=True)


def sobol_indices(tiers: pd.DataFrame, growth: pd.DataFrame, supply: SupplyModel, inputs: pd.DataFrame, draws: pd.DataFrame, n_base: int = 1024, seed: int = 7) -> pd.DataFrame:
    """Sobol first-order and total indices with SALib; the per-unit completion is represented by its realization fraction (quantile of the
    Bernoulli draws), the IEPR case by a uniform mapped to three equal bins and Diablo Canyon by a uniform split at 0.5."""
    from SALib.analyze import sobol as sobol_an
    from SALib.sample import sobol as sobol_sm
    q = inputs.set_index("input"); mw = tiers.set_index("tier").mw_california
    names = ["p_agreement", "p_application", "p_inquiry", "utilization", "ramp_2030", "load_factor", "gen_realization", "hydro_cf", "vre_scale", "imports_twh", "iepr_case", "diablo_continues", "prm"]
    problem = {"num_vars": len(names), "names": names, "bounds": [[0, 1]] * len(names)}
    X = sobol_sm.sample(problem, n_base, calc_second_order=False, seed=seed)
    d = {}
    for j, k in enumerate(names):
        u = X[:, j]
        if k in ("iepr_case",):
            d[k] = np.minimum((u * 3).astype(int), 2)
        elif k == "diablo_continues":
            d[k] = (u >= 0.5).astype(float)
        elif k == "prm":
            d[k] = q.loc[k, "low"] + u * (q.loc[k, "high"] - q.loc[k, "low"])
        elif k == "gen_realization":
            d[k] = np.quantile(draws.gen_realization.values, u)
        else:
            d[k] = _tri_ppf(u, q.loc[k, "low"], q.loc[k, "mode"], q.loc[k, "high"])
    comp = completed_from_fraction(d["gen_realization"], supply)
    out = evaluate_gap({k: v for k, v in d.items() if k != "gen_realization"}, comp, mw, growth, supply)
    rows = []
    for metric in ("gap_energy_twh", "gap_peak_mw"):
        Si = sobol_an.analyze(problem, np.asarray(out[metric], dtype=float), calc_second_order=False, print_to_console=False, seed=seed)
        for j, k in enumerate(names):
            rows.append({"metric": metric, "input": k, "S1": Si["S1"][j], "S1_conf": Si["S1_conf"][j], "ST": Si["ST"][j], "ST_conf": Si["ST_conf"][j], "n_evaluations": len(X)})
    return pd.DataFrame(rows)


def _tri_ppf(u, a, c, b):
    u = np.asarray(u); f = (c - a) / (b - a) if b > a else 0.5
    return np.where(u < f, a + np.sqrt(u * (b - a) * (c - a)), b - np.sqrt((1 - u) * (b - a) * (b - c)))


# =============================================================================== 5. Curtailment-enabled headroom (Duke replication)
DUKE_CAISO = {0.0025: 4.2, 0.005: 5.0, 0.01: 5.9}  # GW, Duke Nicholas Institute 2025, Figure 1 (p. 8) and Figure 8 (p. 23), CAISO bars
DUKE_METHOD = "duke_rethinking_load_growth_2025_mirror: hourly BA demand 2016-2024 (EIA-930), constant load addition, curtailment = max(0, demand + L - seasonal peak threshold), thresholds = maximum winter and summer peak across all years, average annual curtailment rate over years, goal-seek L for 0.25/0.5/1/5% (Appendix C)"


def headroom(demand: pd.Series, limits=(0.0025, 0.005, 0.01, 0.05), winter_months=(11, 12, 1, 2), years=None, l_max: float = 25000, step: float = 50) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Duke's goal-seek on CAISO hourly demand. Returns (curve by L, summary by limit, per-year detail at each limit)."""
    d = demand.copy().interpolate(limit_direction="both")
    full = d.groupby(d.index.year).size(); d = d[d.index.year.isin(full[full >= 8000].index)]  # drop the single 2026 hour-ending row
    if years is not None:
        d = d[d.index.year.isin(years)]
    idx = d.index
    is_winter = np.isin(idx.month, winter_months)
    thr = np.where(is_winter, d[is_winter].max(), d[~is_winter].max())
    L = np.arange(step, l_max + step, step)
    yrs = np.array(sorted(set(idx.year)))
    rate = np.zeros((len(yrs), len(L))); hours = np.zeros_like(rate)
    dv = d.values
    for i, y in enumerate(yrs):
        m = idx.year == y
        excess = dv[m][:, None] + L[None, :] - thr[m][:, None]
        curt = np.clip(excess, 0, None)
        rate[i] = curt.sum(axis=0) / (L * m.sum())
        hours[i] = (curt > 0).sum(axis=0)
    avg = rate.mean(axis=0)
    curve = pd.DataFrame({"load_addition_mw": L, "avg_curtailment_rate": avg, "avg_hours_curtailed": hours.mean(axis=0)})
    rows, detail = [], []
    for lim in limits:
        Lstar = float(np.interp(lim, avg, L)) if avg[-1] >= lim else np.nan
        rows.append({"limit": lim, "headroom_mw": Lstar, "duke_caiso_gw": DUKE_CAISO.get(lim, np.nan), "winter_threshold_mw": float(d[is_winter].max()), "summer_threshold_mw": float(d[~is_winter].max())})
        if not np.isnan(Lstar):
            for i, y in enumerate(yrs):
                m = idx.year == y
                excess = np.clip(dv[m] + Lstar - thr[m], 0, None)
                mon = idx.month[m]
                summer = np.isin(mon, [6, 7, 8]); winter = np.isin(mon, list(winter_months))
                avail = 1 - excess / Lstar
                detail.append({"limit": lim, "year": int(y), "curtailment_rate": excess.sum() / (Lstar * m.sum()), "hours_curtailed": int((excess > 0).sum()), "curtailed_mwh": float(excess.sum()),
                               "share_winter": float(excess[winter].sum() / excess.sum()) if excess.sum() > 0 else np.nan, "share_summer": float(excess[summer].sum() / excess.sum()) if excess.sum() > 0 else np.nan,
                               "hours_below_90pct": int((avail < 0.9).sum()), "hours_below_75pct": int((avail < 0.75).sum()), "hours_below_50pct": int((avail < 0.5).sum()), "max_curtailment_mw": float(excess.max())})
    det = pd.DataFrame(detail)
    if len(det):
        det["year"] = det["year"].astype("Int64")
    return curve, pd.DataFrame(rows), det


def headroom_by_year(demand: pd.Series, limits=(0.0025, 0.005, 0.01, 0.05), winter_months=(11, 12, 1, 2), l_max: float = 40000, step: float = 25) -> pd.DataFrame:
    """Per-year headroom, 2019-2025, under two criteria and two threshold definitions. Hours criterion: the largest constant addition L such
    that the hours in which demand plus L exceeds the historical peak threshold stay below the limit as a share of the year's hours (closed
    form from the sorted margins). Energy criterion: Duke's curtailed energy over the load's potential energy, solved year by year. Thresholds:
    Duke seasons (Nov-Feb winter peak and the peak of the other months, across all years) or the single all-years peak."""
    d = demand.copy().interpolate(limit_direction="both")
    full = d.groupby(d.index.year).size(); d = d[d.index.year.isin(full[full >= 8000].index)]
    idx = d.index; rows = []
    for variant, wm in (("Duke seasons (Nov-Feb winter)", winter_months), ("single historical peak", (99,))):
        is_w = np.isin(idx.month, wm)
        thr = np.where(is_w, d[is_w].max() if is_w.any() else d.max(), d[~is_w].max())
        margin = thr - d.values
        L = np.arange(step, l_max + step, step)
        for y in sorted(set(idx.year)):
            m = idx.year == y; mg = np.sort(margin[m]); n = m.sum()
            excess = np.clip(d.values[m][:, None] + L[None, :] - thr[m][:, None], 0, None); rate = excess.sum(axis=0) / (L * n)
            for lim in limits:
                k = int(np.floor(lim * n))
                l_hours = float(mg[k]) if k < n else np.nan
                l_energy = float(np.interp(lim, rate, L)) if rate[-1] >= lim else np.nan
                rows.append({"variant": variant, "year": int(y), "limit": lim, "headroom_hours_criterion_mw": l_hours, "headroom_energy_criterion_mw": l_energy, "hours_in_year": int(n),
                             "winter_threshold_mw": float(d[is_w].max()) if is_w.any() else np.nan, "other_threshold_mw": float(d[~is_w].max())})
    out = pd.DataFrame(rows); out["year"] = out["year"].astype("Int64")
    return out


# =============================================================================== 6. Flat versus flexible load emissions
def flat_vs_flexible_emissions(years=(2023, 2024, 2025), shares=(0.05, 0.10, 0.25)) -> pd.DataFrame:
    """Emissions of a 1 MW load over a year: flat; curtailed to zero in the highest-intensity share of hours (energy lost); and shifted,
    the same energy moved from those hours to the lowest-intensity hours (load doubles there). CAISO accounting intensity, valid hours."""
    c = pd.read_parquet(PROCESSED / "caiso_co2_intensity_hourly.parquet")
    c = c[c.valid_hour & c.year.isin(years)]
    rows = []
    for y, g in c.groupby("year"):
        I = g.intensity_accounting_g_per_kWh.values  # g/kWh = t/GWh
        n = len(I); flat = I.mean()
        rows.append({"year": int(y), "strategy": "flat", "share_hours": 0.0, "t_per_gwh": flat, "energy_share": 1.0, "peak_multiple": 1.0})
        order = np.argsort(I)
        for s in shares:
            k = int(round(s * n)); hi = order[-k:]; lo = order[:k]
            curt = np.delete(I, hi).sum() / n
            rows.append({"year": int(y), "strategy": "curtail", "share_hours": s, "t_per_gwh": curt / (1 - k / n), "energy_share": 1 - k / n, "peak_multiple": 1.0})
            shifted = (I.sum() - I[hi].sum() + I[lo].sum()) / n
            rows.append({"year": int(y), "strategy": "shift", "share_hours": s, "t_per_gwh": shifted, "energy_share": 1.0, "peak_multiple": 2.0})
    d = pd.DataFrame(rows); d["year"] = d["year"].astype("Int64")
    return d
