"""Chapter 4, RQ3: the crosswalk of data and measurement regimes for large-load pipelines, the common taxonomy, the counting rules and
California's headline number under each rule. Every cell names the manifest source it was read from."""
from __future__ import annotations

import pandas as pd

from src.ch1_baseline import raw_path

CRITERIA = ["granularity", "stage_taxonomy", "verification", "timeliness", "coverage", "public_access"]

REGIMES = [
    {"regime": "CEC energization tiers (California)", "source_ids": "cec_dc_methodology_memo_2026; cec_tn272026; cec_assembly_hearing_2026_01_28; cec_tn268459",
     "granularity": "MW by utility and tier, published as aggregates; project level only in SCE's public database (TN 266008, 268459)",
     "stage_taxonomy": "three groups: signed agreement, active application, inquiry (2026 IEPR proposes a longer milestone list from inquiry to ramp)",
     "verification": "utility-reported; no deposit or site-control test in the public record; confidence levels 70/33/0 or 100/50/10 applied by CEC staff",
     "timeliness": "annual IEPR data request (December 2024, summer 2025, December 2025 vintages); SCE database twice a year",
     "coverage": "no size threshold; seven utilities reported for the 2025 IEPR (VEA's 2,600 MW are in Nevada)",
     "public_access": "docket documents and workshop decks; project-level detail confidential except SCE"},
    {"regime": "ERCOT large load interconnection (Texas)", "source_ids": "ercot_tac_2026_03_large_load_status; ercot_monthly_2025_11; ercot_ops_overview_2026_06; ercot_house_hearing_2026_04_09; ercot_nprr1267_status_report_proposal",
     "granularity": "MW by status, load zone, TSP, project type, size class and in-service year; monthly snapshots",
     "stage_taxonomy": "no studies submitted; under ERCOT review; planning studies approved (Section 9.4/9.5 requirements met); approved to energize but not operational; observed energized",
     "verification": "TSP planning studies reviewed by ERCOT; observed energization measured from telemetry (non-simultaneous peak); Batch Zero (July 2026) adds attestations and a load information form; PUCT rule 25.194 proposes USD 50,000/MW security",
     "timeliness": "monthly (ERCOT Monthly, operational overview, NPRR1267 status report approved July 2025); board and legislative decks quarterly",
     "coverage": "loads of 75 MW or more at a point of interconnection (SB 6 threshold); 20 MW co-located with a resource",
     "public_access": "aggregated public reports; customer identities confidential"},
    {"regime": "PJM load forecast adjustments", "source_ids": "pjm_lar_summary_2025_11_24; pjm_2026_load_forecast_report; pjm_2026_load_report_tables",
     "granularity": "MW by zone and year 2026-2046 (Tables B-9, B-9b); firm and non-firm by zone in the LAS summary",
     "stage_taxonomy": "firm (electric service obligation or construction commitment) versus non-firm (letters of authorization, feasibility studies, other agreements)",
     "verification": "utility submissions reviewed by PJM: 70% utilization unless supported, ramps of at least 36 months, non-firm zero before 2030 and 50% from 2030 with national scaling",
     "timeliness": "annual cycle (requests July, review September to November, forecast January)",
     "coverage": "large load adjustments submitted by transmission owners; no MW threshold stated in the summary",
     "public_access": "load report, tables and the Load Analysis Subcommittee decks are public; project lists are not"},
    {"regime": "EIA pilot data center surveys (federal)", "source_ids": "eia_press585_dc_pilot_surveys",
     "granularity": "facility-level consumption for at least one data center per company (196 companies identified)",
     "stage_taxonomy": "operating facilities only; measures energy use, energy sources, site characteristics, servers and cooling",
     "verification": "voluntary web survey (Texas, Washington) and interviews (Northern Virginia and DC)",
     "timeliness": "pilot launched March 25 2026; no publication schedule yet",
     "coverage": "three regions; California not included",
     "public_access": "results not yet published; EIA states the aim of faster cycles and finer detail"},
    {"regime": "Texas SB 6 (2025)", "source_ids": "texas_sb6_2025_enrolled; ercot_house_hearing_2026_04_09",
     "granularity": "statute: disclosure duties per large load customer to the utility and ERCOT",
     "stage_taxonomy": "interconnection standards to be set by the PUCT; PUCT rule 25.370 (March 2026) counts only loads with an executed interconnection agreement in the forecast after 2026",
     "verification": "disclosure of similar requests elsewhere in the state and of on-site backup generation; flat study fee of at least USD 100,000; proposed USD 50,000/MW financial security (rule 25.194)",
     "timeliness": "standards and forecast rule in force from 2026; monthly ERCOT reporting continues",
     "coverage": "demand of 75 MW or more (the PUCT may lower it); curtailment service for loads of at least 75 MW during emergencies",
     "public_access": "utilities barred from selling or sharing customer submissions except to the PUCT and ERCOT"},
    {"regime": "FERC Docket RM26-4 (federal)", "source_ids": "caiso_comments_ferc_rm26_4_2025_11; nerc_rm26_4_accelerated_plan_2026_03; ferc_news_2026_04_16_large_load; ferc_news_2026_06_18_show_cause",
     "granularity": "no data collection yet; the ANOPR (Oct 23 2025) proposes interconnection procedures for loads above 20 MW",
     "stage_taxonomy": "study, agreement and transition provisions modelled on Order No. 2023 (CAISO comments); June 18 2026 show cause orders name five categories of reform",
     "verification": "to be set in each RTO/ISO tariff; the orders give the six RTOs/ISOs 60 days to justify or file revisions (CAISO Docket EL26-71-000)",
     "timeliness": "ANOPR Oct 2025; comments Nov 2025; FERC committed to act by June 2026 (Apr 16 2026) and issued the orders Jun 18 2026",
     "coverage": "transmission-connected loads above 20 MW in the six RTO/ISO regions, about two-thirds of jurisdictional load",
     "public_access": "docket filings public through eLibrary (ferc.gov rejects non-browser clients, so only the CAISO and NERC filings and two news pages are in the raw store)"},
]


def crosswalk_matrix() -> pd.DataFrame:
    return pd.DataFrame(REGIMES)[["regime"] + CRITERIA + ["source_ids"]]


COMMON_STAGES = ["1 Inquiry or screening", "2 Application and study", "3 Agreement or financial commitment", "4 Approved to energize or under construction", "5 Energized and observed"]


def common_taxonomy() -> pd.DataFrame:
    rows = [
        ("1 Inquiry or screening", "Inquiry (Group 3)", "No studies submitted", "not counted (no adjustment without an agreement)", "not applicable (operating facilities)", "screening study after the flat study fee", "request submitted; study queue"),
        ("2 Application and study", "Active application (Group 2)", "Under ERCOT review", "non-firm: feasibility study, letter of authorization", "not applicable", "interconnection standards; intermediate agreement with site control and security (proposed rule 25.194)", "study process (60-day study proposed for flexible loads)"),
        ("3 Agreement or financial commitment", "Signed agreement (Group 1)", "Planning studies approved; Section 9.4/9.5 requirements met", "firm: electric service obligation or construction commitment", "not applicable", "interconnection agreement; USD 50,000/MW fee converts to non-refundable", "interconnection agreement; cost responsibility for upgrades"),
        ("4 Approved to energize or under construction", "not distinguished (construction and initial energization in the 2026 milestone list)", "Approved to energize but not operational", "firm with ramp of at least 36 months", "not applicable", "curtailment protocol before interconnection", "transition provisions for loads already under study"),
        ("5 Energized and observed", "existing load (about 1,000 MW peak, Dec 2025)", "Observed energized (all-time non-simultaneous peak)", "embedded in the historical load", "surveyed consumption, energy sources, servers, cooling", "curtailment during emergencies; telemetry to ERCOT", "flexible service options"),
    ]
    return pd.DataFrame(rows, columns=["common_stage", "CEC tiers", "ERCOT phases", "PJM firm / non-firm", "EIA pilot survey", "Texas SB 6 / PUCT", "FERC RM26-4"])


def sce_size_classes(source_id: str = "cec_tn268459") -> pd.DataFrame:
    """Requested peak MW of SCE's active data center requests by size class (the only project-level file in the record)."""
    d = pd.read_excel(raw_path(source_id), sheet_name=0)
    d = d.rename(columns={"Requested Peak MW ": "requested_mw", "CEC Grouping": "group", "Status": "status"})
    d["requested_mw"] = pd.to_numeric(d.requested_mw, errors="coerce").fillna(0)
    act = d[d.group.astype(str).str.strip().isin(["1", "2", "3"])]
    bins = [(-1, 20, "under 20 MW"), (20, 75, "20 to under 75 MW"), (75, 1e9, "75 MW and over")]
    rows = []
    for lo, hi, lab in bins:
        m = (act.requested_mw >= lo + (1e-9 if lo >= 0 else 0)) & (act.requested_mw < hi) if lo >= 0 else (act.requested_mw < hi)
        rows.append({"size_class": lab, "projects": int(m.sum()), "requested_mw": float(act.loc[m, "requested_mw"].sum()), "share_of_active_mw": float(act.loc[m, "requested_mw"].sum() / act.requested_mw.sum())})
    out = pd.DataFrame(rows); out["source"] = f"{source_id} (SCE public database, Jan 29 2026; groups 1-3, {len(act)} projects, {act.requested_mw.sum():,.0f} MW)"
    return out


def headline_by_regime(tiers: pd.DataFrame, cases: pd.DataFrame, sizes: pd.DataFrame, chain: pd.DataFrame) -> pd.DataFrame:
    mw = tiers.set_index("tier").mw_california; tot = float(mw.sum()); vea = float(tiers.mw_excluded_nevada.sum())
    c = cases.set_index("case")
    big = sizes.set_index("size_class").share_of_active_mw
    rows = [
        ("CEC: all three tiers", tot, "requested capacity, signed agreements plus applications plus inquiries, California-only (Dec 2025)", "cec_assembly_hearing_2026_01_28; ch2_tier_vintages"),
        ("CEC: all tiers including VEA (Nevada)", tot + vea, "the CEC's published statewide total", "cec_tn272026"),
        ("CEC: agreements plus applications", float(mw["Signed agreement"] + mw["Active application"]), "the comparison the CEC used between the 2024 and 2025 IEPR vintages", "cec_prelim_dc_forecast_2025"),
        ("ERCOT-style: every tracked request", tot, "ERCOT reports all requests of 75 MW or more regardless of study status; the CEC tiers carry no size split, so the total is the same", "ercot_tac_2026_03_large_load_status"),
        ("ERCOT-style: energized by 2030 at the ERCOT hazards", float(c.loc["ERCOT-calibrated stock-flow", "dc_peak_mw_2030"] / c.loc["ERCOT-calibrated stock-flow", "utilization"]), "capacity expected to be energized within 60 months at the monthly phase-transition rates (before utilization)", "ch4_ercot_transition_rates"),
        ("PUCT rule 25.370 (Texas forecast): executed agreements only", float(mw["Signed agreement"]), "only loads with an executed interconnection agreement enter the forecast after 2026", "ercot_house_hearing_2026_04_09 slide 9"),
        ("PJM-style: firm only", float(mw["Signed agreement"]), "electric service obligation or construction commitment; non-firm zero before 2030", "pjm_lar_summary_2025_11_24"),
        ("PJM-style: firm at 70% utilization (demand)", float(c.loc["PJM-style: firm only (signed agreements)", "dc_peak_mw_2030"]), "PJM converts requests to demand at 70% utilization", "pjm_lar_summary_2025_11_24"),
        ("Texas SB 6 threshold (75 MW and over)", float("nan"), f"not computable from the CEC aggregates; in SCE's project-level database {100*big['75 MW and over']:.0f}% of active requested MW is in projects of 75 MW or more", "texas_sb6_2025_enrolled; cec_tn268459"),
        ("FERC RM26-4 threshold (above 20 MW)", float("nan"), f"not computable from the CEC aggregates; in SCE's database {100*(big['75 MW and over'] + big['20 to under 75 MW']):.0f}% of active requested MW is in projects of 20 MW or more", "caiso_comments_ferc_rm26_4_2025_11; cec_tn268459"),
        ("EIA pilot-style: measured consumption of existing facilities", 1000.0, "existing data center peak of about 1,000 MW (CEC, Dec 2025); 7.0 to 9.3 TWh a year in chapter 1", "cec_dc_methodology_memo_2026; ch1_dc_load_estimates"),
    ]
    return pd.DataFrame(rows, columns=["counting_rule", "california_mw", "what_is_counted", "source"])


# ---------------------------------------------------------------- PJM 2026 load forecast: large load adjustments (Tables B-9, B-9b) and the LAS chart readings
PJM_LAR_CHART = [  # approximate values read from pjm_lar_summary_2025_11_24 slide 8 ('RTO'): request, firm, non-firm (MW); preliminary, November 2025
    (2026, 14000, 13000, 0), (2027, 21000, 18000, 0), (2028, 32000, 23000, 0), (2029, 46000, 27000, 0), (2030, 60000, 35000, 5000),
    (2031, 72000, 41000, 10000), (2032, 82000, 46000, 14000), (2035, 98000, 53000, 21000), (2040, 110000, 58000, 25000), (2046, 115000, 61000, 27000),
]


def pjm_adjustment_tables() -> pd.DataFrame:
    """RTO and zone rows of Tables B-9 (adjustments above embedded) and B-9b (total load associated with adjustments), summer peak MW."""
    x = pd.ExcelFile(raw_path("pjm_2026_load_report_tables"))
    rows = []
    for sh, label in (("Table B9", "B-9 adjustments above embedded"), ("Table B9b", "B-9b total load associated with adjustments")):
        d = x.parse(sh, header=None)
        hdr = d.index[d.iloc[:, 1] == 2026].tolist()[0]
        years = [int(v) for v in d.iloc[hdr, 1:].tolist()]
        for i in range(hdr + 1, len(d)):
            z = d.iloc[i, 0]
            if pd.isna(z) or str(z).strip() == "":
                continue
            vals = pd.to_numeric(d.iloc[i, 1:1 + len(years)], errors="coerce").values
            for y, v in zip(years, vals):
                if pd.notna(v):
                    rows.append({"table": label, "zone": str(z).strip(), "year": y, "mw": float(v)})
    out = pd.DataFrame(rows); out["year"] = out["year"].astype("Int64"); out["source"] = "pjm_2026_load_report_tables"
    return out

RUBRIC = {
    "granularity": "0 no data product; 1 aggregates by utility, zone or tier; 2 aggregates by phase, zone, size class and year; 3 project or facility level",
    "stage_taxonomy": "0 operating facilities only; 1 one split (firm/non-firm or agreement/no agreement); 2 three groups; 3 five or more phases",
    "verification": "0 none or voluntary self-report; 1 utility or staff review without money at risk; 2 study or agreement gating; 3 fees, financial security, disclosure duties and curtailment obligations",
    "timeliness": "0 none or one-off pilot; 1 annual; 2 twice a year or quarterly; 3 monthly",
    "coverage": "0 none; 1 partial (three regions or submitted adjustments only); 2 all loads above a threshold in the jurisdiction; 3 all requests regardless of size",
    "public_access": "0 not published or confidential; 1 aggregates only; 2 aggregates plus some project-level or docket detail; 3 full project-level detail",
}
SCORES = {
    "CEC energization tiers (California)": {"granularity": 1, "stage_taxonomy": 2, "verification": 1, "timeliness": 1, "coverage": 3, "public_access": 2},
    "ERCOT large load interconnection (Texas)": {"granularity": 2, "stage_taxonomy": 3, "verification": 2, "timeliness": 3, "coverage": 2, "public_access": 1},
    "PJM load forecast adjustments": {"granularity": 2, "stage_taxonomy": 1, "verification": 2, "timeliness": 1, "coverage": 1, "public_access": 1},
    "EIA pilot data center surveys (federal)": {"granularity": 3, "stage_taxonomy": 0, "verification": 0, "timeliness": 0, "coverage": 1, "public_access": 0},
    "Texas SB 6 (2025)": {"granularity": 0, "stage_taxonomy": 1, "verification": 3, "timeliness": 1, "coverage": 2, "public_access": 0},
    "FERC Docket RM26-4 (federal)": {"granularity": 0, "stage_taxonomy": 1, "verification": 1, "timeliness": 1, "coverage": 2, "public_access": 2},
}


def regime_scores() -> pd.DataFrame:
    """Scores 0-3 per criterion under RUBRIC; the descriptive cells of crosswalk_matrix() are the evidence for each score."""
    rows = [{"regime": r, **sc, "total": sum(sc.values())} for r, sc in SCORES.items()]
    return pd.DataFrame(rows)
