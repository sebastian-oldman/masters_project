"""Registry of every raw data source used by the project.

Each Source is one downloadable file (or one saved HTML page). Generators
below expand families of files (EIA-930 half-years, EIA-860M monthly
vintages, QCEW quarters, ...). `all_sources()` returns the full list.

Tags:
  large   - >50 MB, can be skipped with --exclude-tag large
  html    - a web page saved as evidence, not a dataset
  mirror  - official document fetched from a third-party mirror because the
            publisher's site blocks scripted downloads; provenance noted
  manual  - known to be gated or bot-protected; fetch is attempted but a
            failure is expected and must be resolved by hand
  vintage - a dated vintage of a series that gets revised or re-issued
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


@dataclass
class Source:
    id: str
    group: str
    owner: str
    title: str
    url: str
    filename: str | None = None
    fallback_urls: list[str] = field(default_factory=list)
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    optional: bool = False  # True: a 404 is expected/possible, log as info

    def to_dict(self):
        return asdict(self)


UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36 capstone-data-fetch/0.1")


# --------------------------------------------------------------------------
# EIA
# --------------------------------------------------------------------------
def eia930(first_year=2015, last_year=2026) -> list[Source]:
    """EIA-930 six-month bulk files. BALANCE starts 2015 Jul-Dec, SUBREGION 2018 Jul-Dec."""
    out = []
    base = "https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/"
    for y in range(first_year, last_year + 1):
        for half in ("Jan_Jun", "Jul_Dec"):
            if y == 2015 and half == "Jan_Jun":
                continue
            if y == last_year and half == "Jul_Dec":
                # current half-year file exists but is partial; snapshot it, mark optional
                opt = True
            else:
                opt = False
            for kind, first in (("BALANCE", 2015), ("SUBREGION", 2018), ("INTERCHANGE", 2015)):
                if y < first or (y == first and half == "Jan_Jun"):
                    continue
                fn = f"EIA930_{kind}_{y}_{half}.csv"
                tags = ["large"] if kind == "INTERCHANGE" else []
                out.append(Source(
                    id=f"eia930_{kind.lower()}_{y}_{half.lower()}", group="eia930", owner="EIA",
                    title=f"EIA-930 Hourly Electric Grid Monitor {kind} {y} {half.replace('_', '-')}",
                    url=base + fn, filename=fn, tags=tags, optional=opt,
                    notes="All balancing authorities; filter BA=CISO (and LDWP, BANC, IID, TIDC for the CAL region)."))
    return out


def eia861(first=2010, last=2024) -> list[Source]:
    out = []
    for y in range(first, last + 1):
        fn = f"f861{y}.zip" if y >= 2012 else f"f861{y % 100:02d}.zip"  # 2010-2011 use two-digit years
        cur = f"https://www.eia.gov/electricity/data/eia861/zip/{fn}"
        arch = f"https://www.eia.gov/electricity/data/eia861/archive/zip/{fn}"
        out.append(Source(id=f"eia861_{y}", group="eia861", owner="EIA",
                          title=f"EIA-861 Annual Electric Power Industry Report {y}",
                          url=arch if y < last else cur, fallback_urls=[cur if y < last else arch],
                          filename=fn, notes="Retail sales by utility, sector and state (Sales_Ult_Cust)."))
    return out


def eia923(first=2010, last=2026) -> list[Source]:
    out = []
    for y in range(first, last + 1):
        fn = f"f923_{y}.zip"
        cur = f"https://www.eia.gov/electricity/data/eia923/xls/{fn}"
        arch = f"https://www.eia.gov/electricity/data/eia923/archive/xls/{fn}"
        out.append(Source(id=f"eia923_{y}", group="eia923", owner="EIA",
                          title=f"EIA-923 Power Plant Operations Report {y}" + (" (current-year monthly file, monthly respondents only, year to date)" if y == 2026 else ""),
                          url=arch if y < last else cur, fallback_urls=[cur if y < last else arch],
                          filename=fn, notes="Monthly generation and fuel consumption by plant."))
    return out


def eia860(first=2010, last=2025) -> list[Source]:
    out = []
    for y in range(first, last + 1):
        fn = f"eia860{y}.zip"
        cur = f"https://www.eia.gov/electricity/data/eia860/xls/{fn}"
        arch = f"https://www.eia.gov/electricity/data/eia860/archive/xls/{fn}"
        out.append(Source(id=f"eia860_{y}", group="eia860", owner="EIA",
                          title=f"EIA-860 Annual Electric Generator Report {y}",
                          url=arch if y < last else cur, fallback_urls=[cur if y < last else arch],
                          filename=fn, notes="Generator-level inventory incl. planned units and retirement dates."))
    return out


def eia860m(first=(2015, 7), last=(2026, 8)) -> list[Source]:
    """Monthly EIA-860M vintages. Archive begins July 2015. Newest months live under xls/."""
    out = []
    y, m = first
    while (y, m) <= last:
        mon = MONTHS[m - 1]
        fn = f"{mon}_generator{y}.xlsx"
        arch = f"https://www.eia.gov/electricity/data/eia860m/archive/xls/{fn}"
        cur = f"https://www.eia.gov/electricity/data/eia860m/xls/{fn}"
        recent = (y, m) >= (2026, 6)
        out.append(Source(id=f"eia860m_{y}_{m:02d}", group="eia860m", owner="EIA",
                          title=f"EIA-860M Preliminary Monthly Electric Generator Inventory, {mon.title()} {y}",
                          url=cur if recent else arch, fallback_urls=[arch if recent else cur],
                          filename=fn, tags=["vintage"], optional=(y, m) >= (2026, 8),
                          notes="Operating, planned, retired and cancelled tabs; use for vintage realization model."))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


# --------------------------------------------------------------------------
# BLS QCEW (NAICS 518210 data processing, hosting and related services)
# --------------------------------------------------------------------------
def qcew(first=2014, last=2026) -> list[Source]:
    out = []
    for y in range(first, last + 1):
        for q in (1, 2, 3, 4):
            if y == last and q > 1:
                continue
            out.append(Source(id=f"qcew_518210_{y}q{q}", group="bls_qcew", owner="BLS",
                              title=f"QCEW industry slice NAICS 518210, {y} Q{q} (all areas)",
                              url=f"https://data.bls.gov/cew/data/api/{y}/{q}/industry/518210.csv",
                              filename=f"qcew_518210_{y}q{q}.csv", optional=(y >= 2026),
                              notes="Filter area_fips 06000 (California) and 06xxx counties."))
        if y <= 2025:
            out.append(Source(id=f"qcew_518210_{y}_annual", group="bls_qcew", owner="BLS",
                              title=f"QCEW industry slice NAICS 518210, {y} annual averages (all areas)",
                              url=f"https://data.bls.gov/cew/data/api/{y}/a/industry/518210.csv",
                              filename=f"qcew_518210_{y}_annual.csv", optional=(y >= 2025)))
            out.append(Source(id=f"qcew_area06000_{y}_annual", group="bls_qcew", owner="BLS",
                              title=f"QCEW area slice California (06000), {y} annual averages (all industries)",
                              url=f"https://data.bls.gov/cew/data/api/{y}/a/area/06000.csv",
                              filename=f"qcew_area06000_{y}_annual.csv", optional=(y >= 2025),
                              notes="Denominator for 518210 share of state employment."))
    return out


# --------------------------------------------------------------------------
# CEC docket 25-IEPR-03 (demand forecast) — transaction numbers verified 2026-09-21
# --------------------------------------------------------------------------
CEC_DOCKET_TNS = [
    # data center forecast method and tiers
    (267165, "2025 IEPR Preliminary Data Center Forecast presentation (Nov 12 2025 docketing of Oct 30 workshop deck)"),
    (267170, "Draft Impacts of Known Loads for the 2025 IEPR Demand Forecast presentation"),
    (265229, "Incorporating New Load Energization Requests to Utilities presentation (Aug 2025)"),
    (261964, "PG&E Data Center Pipeline presentation, Feb 26 2025 IEPR workshop"),
    (261965, "EPRI AI and Data Center Growth presentation, Feb 26 2025 IEPR workshop"),
    (261975, "SCE Data Center Forecast presentation (updated), Feb 26 2025 IEPR workshop"),
    (261716, "STACK Infrastructure comments regarding data center load forecasting"),
    # project-level and allocation tables
    (268459, "SCE IEPR25 Data Center Database PUBLIC 2026-01-29"),
    (266008, "SCE IEPR25 Data Center Database PUBLIC 2025-08-29"),
    (268824, "CED 2025 Planning Forecast Form 1.1c Data Center Allocations (final)"),
    (268504, "Draft CED 2025 Form 1.1c Data Center Allocations"),
    (268659, "Draft CED 2024 Planning Forecast LSE BAA Tables and Data Center Allocations"),
    # PG&E confidentiality requests (institutional evidence of withheld project-level data)
    (265852, "PG&E Data Center Request for Confidentiality, Aug 2025"),
    (267083, "PG&E Non Data Center Large Load Request for Confidentiality, Nov 2025"),
    (267896, "PG&E Data Center Request for Confidentiality, Dec 2025"),
    (268283, "PG&E Data Center Request for Confidentiality, Jan 2026"),
    (268596, "PG&E Data Center Request for Confidentiality, Feb 2026"),
    # single forecast set agreement (CEC/CPUC/CAISO)
    (268288, "Single Forecast Set Agreement supporting documentation for the 2025 IEPR forecast (Jan 2026)"),
    (269494, "Updated Single Forecast Set Agreement (Apr 15 2026)"),
    (269506, "2025 IEPR forecast Single Forecast Set Agreement, updated 2026-04-15 (supersedes TN 268288)"),
    # CED 2025 results
    (268727, "CED 2025 Planning Forecast LSE and BAA Tables (final)"),
    (268726, "CED 2025 Local Reliability with Known Loads Scenario LSE and BAA Tables (final)"),
    (268725, "CED 2025 Local Reliability Scenario LSE and BAA Tables (final)"),
    (268722, "CED 2025 Baseline Forecast LSE and BAA Tables (final)"),
    (268723, "CED 2024 Planning Forecast Updated LSE and BAA Tables (final)"),
    (268124, "CED 2025 Peak Forecast"),
    (268125, "CED 2025 Hourly Forecast CAISO Local Reliability"),
    (268126, "CED 2025 Hourly Forecast CAISO Local Reliability plus Known loads"),
    (268127, "CED 2025 Hourly Forecast CAISO Planning Scenario"),
    (268128, "CED 2025 Hourly Forecast PGE Local Reliability"),
    (268129, "CED 2025 Hourly Forecast PGE Local Reliability plus Known loads"),
    (268130, "CED 2025 Hourly Forecast PGE Planning Scenario"),
    (268131, "CED 2025 Hourly Forecast SCE Local Reliability"),
    (268116, "CED 2025 Hourly Forecast SCE Local Reliability plus Known loads"),
    (268117, "CED 2025 Hourly Forecast SCE Planning Scenario"),
    (268118, "CED 2025 Hourly Forecast SDGE Local Reliability"),
    (268119, "CED 2025 Hourly Forecast SDGE Local Reliability plus Known loads"),
    (268120, "CED 2025 Hourly Forecast SDGE Planning Scenario"),
    (268121, "CED 2025 Hourly Forecast VEA Local Reliability"),
    (268122, "CED 2025 Hourly Forecast VEA Local Reliability plus Known loads"),
    (268123, "CED 2025 Hourly Forecast VEA Planning Scenario"),
    (268076, "Corrected presentation, 2025 California Energy Demand annual consumption and sales forecasts"),
    (268017, "Draft CED 2025 Peak Forecast, Planning Scenarios"),
    (268018, "Draft CED 2025 Peak Forecast, Local Reliability Scenarios"),
    (268239, "CED 2025 Electricity Rate Forecast"),
    (268187, "Notice of Availability, California Energy Demand Forecast 2025-2045"),
    (268180, "Transcript, IEPR Commissioner Workshop on Load Modifier Energy Demand Forecast Results, Nov 13 2025"),
    (268806, "Transcript, IEPR Commissioner Workshop on Energy Demand Forecast Draft Results"),
]

CEC_OTHER_TNS = [
    (253461, "svp", "City of Santa Clara dba Silicon Valley Power 2023 Integrated Resource Plan (CEC filing)"),
    (264908, "svp", "Presentation by Silicon Valley Power to the CEC (2025)"),
    (265948, "svp", "CEC Review of Silicon Valley Power 2023 Integrated Resource Plan"),
]


CEC_DOCKET_2026_TNS = [
    (272026, "Presentation - Data Center Demand Forecast (Smith, CEC), IEPR workshop Aug 18 2026"),
    (272043, "Presentation - Load Energization Requests (Known Loads), REVISED (Sanada, CEC), Aug 19 2026 (replaces TN 272024)"),
    (272024, "Presentation - Load Energization Requests (Known Loads) (Sanada, CEC), Aug 18 2026, original"),
    (272023, "Presentation - Known Loads Preliminary Analysis (Wilson, CEC), Aug 18 2026"),
    (272065, "Presentation - PG&E Data Center Forecasting (Jenny Conde), Aug 20 2026"),
    (272027, "Presentation - Forecasting perspectives from San Jose Clean Energy, Aug 18 2026"),
    (272022, "Presentation - IEPR Workshop on Energy Demand Forecast Inputs and Assumptions, intro (Javanbakht, CEC)"),
    (272025, "Presentation - Economic and Demographic Updates for the 2026 IEPR (Cooper, CEC)"),
    (272220, "Presentation - Electricity Rate Forecast Updates for the 2026 IEPR (Marshall, CEC), Aug 28 2026"),
    (271964, "SVCE Data Center Load Forecasting (Silicon Valley Clean Energy), Aug 11 2026"),
    (271963, "Silicon Valley Power, City of Santa Clara - Load Forecast Discussion, Aug 11 2026"),
    (271962, "San Jose Clean Energy - CEC DAWG meeting, Aug 11 2026"),
    (271974, "City of Palo Alto Utilities - CEC Demand Analysis Working Group meeting, Aug 12 2026"),
    (272858, "PG&E Data Center Request for Confidentiality, Sep 2026"),
    (272131, "Transcript - IEPR Commissioner Workshop on Energy Demand Forecast Inputs and Assumptions, Aug 18 2026"),
    (272804, "Transcript - IEPR Commissioner Workshop on Load Modifier Inputs and Assumptions, Aug 31 2026"),
    (272798, "SCE comments on 2026 IEPR workshops on energy demand forecast inputs and load modifier assumptions"),
    (272812, "San Jose Clean Energy comments on 2026 IEPR demand forecast workshops"),
    (272807, "Public Advocates Office comments on the 2026 IEPR Update demand forecast workshop"),
    (272792, "CalCCA comments on the IEPR Commissioner workshop on energy demand forecast inputs and assumptions"),
    (272816, "Industrious Labs, Earthjustice, Sierra Club, 2035 Initiative comments on AAFS 6"),
    (268799, "Memo to open new docket 26-IEPR-03"),
]


def cec_docket() -> list[Source]:
    out = []
    for tn, title in CEC_DOCKET_TNS:
        out.append(Source(id=f"cec_tn{tn}", group="cec_iepr_docket", owner="CEC",
                          title=f"CEC docket 25-IEPR-03 TN {tn}: {title}",
                          url=f"https://efiling.energy.ca.gov/GetDocument.aspx?tn={tn}",
                          notes="File type resolved from Content-Disposition at download."))
    for tn, title in CEC_DOCKET_2026_TNS:
        out.append(Source(id=f"cec_tn{tn}", group="cec_iepr_docket", owner="CEC",
                          title=f"CEC docket 26-IEPR-03 TN {tn}: {title}",
                          url=f"https://efiling.energy.ca.gov/GetDocument.aspx?tn={tn}",
                          notes="2026 IEPR cycle. File type resolved from Content-Disposition at download.", tags=["vintage"]))
    out.append(Source(id="cec_docket_log_26iepr03", group="cec_iepr_docket", owner="CEC",
                      title="Docket log listing for 26-IEPR-03 (HTML)",
                      url="https://efiling.energy.ca.gov/Lists/DocketLog.aspx?docketnumber=26-IEPR-03",
                      filename="docketlog_26-IEPR-03.html", tags=["html", "vintage"]))
    for tn, grp, title in CEC_OTHER_TNS:
        out.append(Source(id=f"cec_tn{tn}", group=grp, owner="CEC e-filing",
                          title=f"CEC TN {tn}: {title}",
                          url=f"https://efiling.energy.ca.gov/GetDocument.aspx?tn={tn}"))
    out.append(Source(id="cec_docket_log_25iepr03", group="cec_iepr_docket", owner="CEC",
                      title="Docket log listing for 25-IEPR-03 (HTML)",
                      url="https://efiling.energy.ca.gov/Lists/DocketLog.aspx?docketnumber=25-IEPR-03",
                      filename="docketlog_25-IEPR-03.html", tags=["html", "vintage"]))
    return out


# --------------------------------------------------------------------------
# Static list
# --------------------------------------------------------------------------
STATIC: list[Source] = [
    # ---- CEC energization tiers and data center forecast documents ----
    Source("cec_assembly_hearing_2026_01_28", "cec_tiers", "CEC / CA Assembly",
           "CEC presentation to Assembly Utilities & Energy and Privacy & Consumer Protection joint oversight hearing on Energy Impacts of AI, Jan 28 2026 (energization tiers slide)",
           "https://autl.assembly.ca.gov/media/1402", filename="CEC_Assembly_AI_energy_hearing_2026-01-28.pdf",
           notes="Source of 5,086 / 9,587 / 8,604 MW tier figures (Dec 2025). Transcribe with page citation."),
    Source("cec_prelim_dc_forecast_2025", "cec_tiers", "CEC",
           "2025 IEPR Preliminary Data Center Forecast (Oct 30 2025 workshop deck, ADA version)",
           "https://www.energy.ca.gov/sites/default/files/2025-11/2025_IEPR_Preliminary_Data_Center_Forecast_ada.pdf"),
    Source("cec_dc_methodology_memo_2026", "cec_tiers", "CEC",
           "Data Center Methodology Memo, supporting document for the 2025 IEPR forecast (Apr 2026)",
           "https://www.energy.ca.gov/sites/default/files/2026-04/Data_Center_Methodology_Memo_ada.pdf"),
    Source("cec_dc_forecast_2024iepr", "cec_tiers", "CEC",
           "2024 IEPR Data Center Forecast (Jenny Chen), final ADA version, Mar 2025",
           "https://www.energy.ca.gov/sites/default/files/2025-03/Data_Center_Forecast_Final_ada.pdf"),
    Source("cec_ced2025_demand_side_page", "cec_tiers", "CEC",
           "CED 2025 Demand Side Modeling page (HTML index of forecast products)",
           "https://www.energy.ca.gov/data-reports/california-energy-planning-library/forecasts-and-system-planning/demand-side-3",
           filename="cec_ced2025_demand_side_modeling.html", tags=["html"]),

    # ---- CEC Energy Almanac / consumption database ----
    Source("cec_cons_elec_county_annual", "cec_almanac", "CEC", "Electricity consumption by county, annual (ECDMS export)",
           "https://www.energy.ca.gov/filebrowser/download/8144?fid=8144", filename="AGG_CONSUMPTION_ELEC_COUNTY_TBL_ada.xlsx"),
    Source("cec_cons_elec_county_monthly", "cec_almanac", "CEC", "Electricity consumption by county, monthly (ECDMS export)",
           "https://www.energy.ca.gov/filebrowser/download/9337?fid=9337", filename="AGG_CONSUMPTION_ELEC_COUNTY_TBL_MONTHLY.xlsx"),
    Source("cec_cons_elec_utility_annual", "cec_almanac", "CEC", "Electricity consumption by utility and sector, annual (ECDMS export)",
           "https://www.energy.ca.gov/filebrowser/download/8168?fid=8168", filename="AGG_CONSUMPTION_ELEC_UTILITY_TBL_ada.xlsx"),
    Source("cec_cons_elec_utility_monthly", "cec_almanac", "CEC", "Electricity consumption by utility and sector, monthly (ECDMS export)",
           "https://www.energy.ca.gov/filebrowser/download/9338?fid=9338", filename="AGG_CONSUMPTION_ELEC_UTILITY_TBL_MONTHLY.xlsx"),
    Source("cec_cons_elec_total", "cec_almanac", "CEC", "Total statewide electricity consumption table (ECDMS export)",
           "https://www.energy.ca.gov/filebrowser/download/8148?fid=8148", filename="TOTAL_ELEC_TBL_ada.xlsx"),
    Source("cec_cons_ng_utility_annual", "cec_almanac", "CEC", "Natural gas consumption by utility, annual (ECDMS export)",
           "https://www.energy.ca.gov/filebrowser/download/8147?fid=8147", filename="AGG_CONSUMPTION_NG_UTILITY_TBL_ada.xlsx", optional=True),
    Source("cec_cons_ng_total", "cec_almanac", "CEC", "Total statewide natural gas consumption (ECDMS export)",
           "https://www.energy.ca.gov/filebrowser/download/8149?fid=8149", filename="TOTAL_NG_TBL_ada.xlsx", optional=True),
    Source("cec_cons_data_files_page", "cec_almanac", "CEC", "Energy consumption data files index page (HTML)",
           "https://www.energy.ca.gov/files/energy-consumption-data-files", filename="cec_energy_consumption_data_files.html", tags=["html"]),
    Source("cec_gen_capacity_energy_page", "cec_almanac", "CEC", "Electric generation capacity and energy page (HTML tables)",
           "https://www.energy.ca.gov/data-reports/energy-almanac/california-electricity-data/electric-generation-capacity-and-energy",
           filename="cec_electric_generation_capacity_and_energy.html", tags=["html"]),
    Source("cec_elec_energy_generation_page", "cec_almanac", "CEC", "California electrical energy generation page (HTML tables, in-state vs imports)",
           "https://www.energy.ca.gov/data-reports/energy-almanac/california-electricity-data/california-electrical-energy-generation",
           filename="cec_california_electrical_energy_generation.html", tags=["html"]),
    Source("cec_storage_survey_page", "cec_almanac", "CEC", "California energy storage system survey page (HTML)",
           "https://www.energy.ca.gov/data-reports/energy-almanac/california-electricity-data/california-energy-storage-system-survey",
           filename="cec_energy_storage_system_survey.html", tags=["html"]),
] + [
    Source(f"cec_total_system_generation_{y}", "cec_almanac", "CEC", f"{y} Total System Electric Generation page (HTML table)",
           f"https://www.energy.ca.gov/data-reports/energy-almanac/california-electricity-data/{y}-total-system-electric-generation",
           filename=f"cec_{y}_total_system_electric_generation.html", tags=["html"], optional=(y < 2019))
    for y in range(2015, 2025)
] + [
    # ---- CAISO ----
    Source("caiso_nqc_2026", "caiso", "CAISO", "Net Qualifying Capacity report for compliance year 2026 (resource-level QC values)",
           "https://www.caiso.com/documents/final-net-qualifying-capacity-report-for-compliance-year-2026.xlsx"),
    Source("caiso_nqc_2025", "caiso", "CAISO", "Final Net Qualifying Capacity report for compliance year 2025",
           "https://www.caiso.com/documents/final-net-qualifying-capacity-report-for-compliance-year-2025.xlsx"),
    Source("caiso_summer_assessment_2026_appendix", "caiso", "CAISO", "2026 Summer Loads and Resources Assessment, technical appendix",
           "https://www.caiso.com/documents/2026-summer-loads-and-resources-assessment-technical-appendix.pdf"),
    Source("caiso_key_statistics_2026_06", "caiso", "CAISO", "CAISO Key Statistics, June 2026 (peak records, curtailment totals)",
           "https://www.caiso.com/documents/key-statistics-jun-2026.pdf", tags=["vintage"]),
    Source("caiso_prod_curtail_2024", "caiso", "CAISO", "Production and curtailments data 2024 (wind/solar curtailment by hour)",
           "https://www.caiso.com/documents/production-and-curtailments-data-2024.xlsx"),
    Source("caiso_prod_curtail_2025", "caiso", "CAISO", "Production and curtailments data 2025 (report discontinued June 2025; partial)",
           "https://www.caiso.com/documents/production-and-curtailments-data-2025.xlsx"),
] + [
    Source(f"caiso_prod_curtail_{y}", "caiso", "CAISO", f"Production and curtailments data {y}",
           f"https://www.caiso.com/documents/production-and-curtailments-data-{y}.xlsx", optional=True)
    for y in range(2017, 2024)
] + [
    Source("caiso_nqc_efc_library_page", "caiso", "CAISO", "NQC and EFC library page (HTML)",
           "https://www.caiso.com/library/net-qualifying-capacity-nqc-and-effective-flexible-capacity-efc",
           filename="caiso_nqc_efc_library.html", tags=["html"]),
    Source("caiso_prod_curtail_library_page", "caiso", "CAISO", "Production and curtailments data library page (HTML)",
           "https://www.caiso.com/library/production-curtailments-data", filename="caiso_production_curtailments_library.html", tags=["html"]),

    # ---- CPUC resource adequacy ----
] + [
    Source(f"cpuc_ra_report_{y}", "cpuc", "CPUC", f"{y} Resource Adequacy Report",
           "https://www.cpuc.ca.gov" + p)
    for y, p in [
        (2015, "/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/2015-ra-report.pdf"),
        (2016, "/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/2016rareport.pdf"),
        (2017, "/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/2017rareport.pdf"),
        (2018, "/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/2018-ra-report-rev.pdf"),
        (2019, "/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/2019-ra-report_revised-012324.pdf"),
        (2020, "/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/2020-ra-report_v15-revised-011624.pdf"),
        (2021, "/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/2021-ra-report---update-011624.pdf"),
        (2022, "/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/2022-ra-report_05022024.pdf"),
        (2023, "/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/2023-resource-adequacy-reportv2.pdf"),
    ]
] + [
    Source("cpuc_ra_homepage", "cpuc", "CPUC", "Resource Adequacy homepage (HTML, index of reports and decisions)",
           "https://www.cpuc.ca.gov/industries-and-topics/electrical-energy/electric-power-procurement/resource-adequacy-homepage",
           filename="cpuc_resource_adequacy_homepage.html", tags=["html"]),
    Source("cpuc_ra_compliance_materials", "cpuc", "CPUC", "Resource Adequacy compliance materials page (HTML)",
           "https://www.cpuc.ca.gov/industries-and-topics/electrical-energy/electric-power-procurement/resource-adequacy-homepage/resource-adequacy-compliance-materials",
           filename="cpuc_ra_compliance_materials.html", tags=["html"]),

    # ---- Census C30 construction spending ----
    Source("census_c30_privtime", "census_c30", "U.S. Census Bureau",
           "Value of Construction Put in Place, private, historical monthly time series (seasonally adjusted annual rate), incl. Data center line",
           "https://www.census.gov/construction/c30/xlsx/privtime.xlsx", tags=["vintage"]),
    Source("census_c30_privsa", "census_c30", "U.S. Census Bureau", "Value of Construction Put in Place, private, latest monthly release (SA)",
           "https://www.census.gov/construction/c30/xlsx/privsa.xlsx", tags=["vintage"]),
    Source("census_c30_totsatime", "census_c30", "U.S. Census Bureau", "Value of Construction Put in Place, total, historical monthly SA time series",
           "https://www.census.gov/construction/c30/xlsx/totsatime.xlsx", tags=["vintage"]),
    Source("census_c30_index_page", "census_c30", "U.S. Census Bureau", "C30 data index page (HTML)",
           "https://www.census.gov/construction/c30/data/index.html", filename="census_c30_data_index.html", tags=["html"]),

    # ---- Facility inventories ----
    Source("epoch_data_centers", "facilities", "Epoch AI", "Frontier Data Centers Hub: data_centers.csv",
           "https://epoch.ai/data/data_centers/data_centers.csv", tags=["vintage"]),
    Source("epoch_data_center_timelines", "facilities", "Epoch AI", "Frontier Data Centers Hub: data_center_timelines.csv (construction and power ramp timelines)",
           "https://epoch.ai/data/data_centers/data_center_timelines.csv", tags=["vintage"]),
    Source("epoch_chip_quantities", "facilities", "Epoch AI", "Frontier Data Centers Hub: data_centers_chip_quantities.csv",
           "https://epoch.ai/data/data_centers/data_centers_chip_quantities.csv", tags=["vintage"]),
    Source("epoch_chillers", "facilities", "Epoch AI", "Frontier Data Centers Hub: data_center_chillers.csv",
           "https://epoch.ai/data/data_centers/data_center_chillers.csv", tags=["vintage"], optional=True),
    Source("epoch_cooling_towers", "facilities", "Epoch AI", "Frontier Data Centers Hub: data_center_cooling_towers.csv",
           "https://epoch.ai/data/data_centers/data_center_cooling_towers.csv", tags=["vintage"], optional=True),
    Source("epoch_bundle_zip", "facilities", "Epoch AI", "Frontier Data Centers Hub: full download bundle (zip)",
           "https://epoch.ai/data/data_centers/data_centers.zip", tags=["vintage"]),
    Source("epoch_hub_page", "facilities", "Epoch AI", "Frontier Data Centers Hub landing page (HTML, documentation and FAQ)",
           "https://epoch.ai/data/data-centers", filename="epoch_data_centers_hub.html", tags=["html"]),
    Source("kollar_grady_2025_zenodo", "facilities", "Kollar & Grady (Zenodo 10.5281/zenodo.17372375)",
           "Dataset for 'The relationship between data centers and the climate is a systems challenge: a spatial analysis of United States data centers' (Environ. Res. Commun. 2025)",
           "https://zenodo.org/records/17372375/files/DataCenterRiskRepository.zip?download=1",
           fallback_urls=["https://zenodo.org/api/records/17372375/files/DataCenterRiskRepository.zip/content"],
           filename="DataCenterRiskRepository.zip", tags=["large"]),

    # ---- Existing data center share estimates ----
    Source("lbnl_2024_dc_energy_report", "dc_share", "LBNL",
           "2024 United States Data Center Energy Usage Report (Shehabi et al., LBNL-2001637)",
           "https://eta-publications.lbl.gov/sites/default/files/2024-12/lbnl-2024-united-states-data-center-energy-usage-report_1.pdf",
           filename="lbnl-2024-united-states-data-center-energy-usage-report.pdf"),
    Source("lbnl_2025_dc_energy_update_mirror", "dc_share", "LBNL (mirror: RTO Insider)",
           "United States Data Center Energy Usage Report: 2025 Update (LBNL-2001758) - mirror copy; verify against eta.lbl.gov",
           "https://www.rtoinsider.com/wp-content/uploads/2026/06/data-center-energy-usage-2025-update.pdf",
           filename="lbnl-2025-data-center-energy-usage-update_MIRROR.pdf", tags=["mirror"], optional=True),
    Source("epri_powering_intelligence_2024", "dc_share", "EPRI",
           "Powering Intelligence: Analyzing AI and Data Center Energy Consumption (2024 white paper 3002028905, state table)",
           "https://restservice.epri.com/publicdownload/000000003002028905/0/Product",
           filename="EPRI_3002028905_Powering_Intelligence_2024.pdf"),
    Source("epri_powering_intelligence_2026_update", "dc_share", "EPRI",
           "Powering Intelligence: Updated U.S. Data Center Scenarios (2026 attachment 97025)",
           "https://restservice.epri.com/publicattachment/97025", filename="EPRI_Powering_Intelligence_2026_update.pdf", optional=True),

    # ---- Texas / ERCOT ----
    Source("ercot_tac_2026_03_large_load_status", "ercot", "ERCOT",
           "Large Load Interconnection Status Update, March 2026 TAC report (queue phase definitions)",
           "https://www.ercot.com/files/docs/2026/03/12/March-TAC-Report.pdf", filename="ERCOT_March-TAC-Report_2026.pdf"),
    Source("ercot_board_2025_12_system_planning", "ercot", "ERCOT",
           "System Planning and Weatherization Update to the Board, Dec 2025 (226 GW large load, 73% data centers)",
           "https://www.ercot.com/files/docs/2025/12/02/16.2-System-Planning-and-Weatherization-Update_Revised.pdf"),
    Source("ercot_house_hearing_2026_04_09", "ercot", "ERCOT", "Large Load Update to Texas House State Affairs hearing, Apr 9 2026 (~410 GW)",
           "https://www.ercot.com/files/docs/2026/04/09/ERCOTLargeLoadUpdate-April9HouseStateAffairsHearing.pdf"),
    Source("ercot_senate_hearing_2026_04_01", "ercot", "ERCOT", "Large Load Update to Texas Senate Business & Commerce hearing, Apr 1 2026",
           "https://www.ercot.com/files/docs/2026/04/01/ERCOT_LargeLoad_Update_April2026_B-C_-Hearing.pdf"),
    Source("ercot_board_2026_05_interconnection_update", "ercot", "ERCOT", "Interconnection and Grid Analysis Update (Jeff Billo), May 2026 board item 8",
           "https://www.ercot.com/files/docs/2026/05/24/8-Interconnection-and-Grid-Analysis-Update.pdf"),
    Source("ercot_presentations_index", "ercot", "ERCOT", "ERCOT news/presentations index page (HTML; lists ERCOT Monthly PDFs)",
           "https://www.ercot.com/news/presentations", filename="ercot_presentations_index.html", tags=["html", "vintage"]),
    Source("ercot_large_load_integration_page", "ercot", "ERCOT", "Large Load Integration services page (HTML)",
           "https://www.ercot.com/services/rq/large-load-integration", filename="ercot_large_load_integration.html", tags=["html"]),
    Source("texas_sb6_2025_enrolled", "ercot", "Texas Legislature", "Texas S.B. 6 (89R, 2025) enrolled bill text",
           "https://capitol.texas.gov/tlodocs/89R/billtext/pdf/SB00006F.pdf", filename="Texas_SB6_89R_enrolled.pdf"),
] + [
    Source(f"ercot_monthly_{y}_{m:02d}", "ercot", "ERCOT", f"ERCOT Monthly, {MONTHS[m-1].title()} {y} (large load queue totals by status)",
           u, filename=f"ERCOT-Monthly-{y}-{m:02d}.pdf", tags=["vintage"])
    for (y, m, u) in [
        (2025, 2, "https://www.ercot.com/files/docs/2025/03/03/ERCOT-Monthly-February2025.pdf"),
        (2025, 3, "https://www.ercot.com/files/docs/2025/04/09/ERCOT-Monthly-March2025.pdf"),
        (2025, 4, "https://www.ercot.com/files/docs/2025/05/02/ERCOT-Monthly-April-2025-FINAL.pdf"),
        (2025, 5, "https://www.ercot.com/files/docs/2025/06/05/ERCOT-Monthly-May-2025.pdf"),
        (2025, 6, "https://www.ercot.com/files/docs/2025/07/09/ERCOT-Monthly-June-2025.pdf"),
        (2025, 7, "https://www.ercot.com/files/docs/2025/08/06/ERCOT-Monthly-July-2025.pdf"),
        (2025, 8, "https://www.ercot.com/files/docs/2025/09/10/ERCOT-Monthly-August-2025.pdf"),
        (2025, 9, "https://www.ercot.com/files/docs/2025/10/09/ERCOT-Monthly-September-2025.pdf"),
        (2025, 10, "https://www.ercot.com/files/docs/2025/11/14/ERCOT-Monthly-October-2025.pdf"),
        (2025, 11, "https://www.ercot.com/files/docs/2025/12/19/ERCOT-Monthly-November-2025-FINAL.pdf"),
        (2025, 12, "https://www.ercot.com/files/docs/2026/01/20/ERCOT-Monthly-December-2025-FINAL.pdf"),
        (2026, 1, "https://www.ercot.com/files/docs/2026/02/13/ERCOT-Monthly-January-2026-FINAL.pdf"),
        (2026, 2, "https://www.ercot.com/files/docs/2026/03/17/ERCOT-Monthly-February-2026-FINAL.pdf"),
        (2026, 4, "https://www.ercot.com/files/docs/2026/05/13/ERCOT-Monthly-April-2026-FINAL.pdf"),
        (2026, 5, "https://www.ercot.com/files/docs/2026/06/19/ERCOT-Monthly-May-2026.pdf"),
        (2026, 6, "https://www.ercot.com/files/docs/2026/07/10/ERCOT-Monthly-June-2026-FINAL.pdf"),
    ]
] + [
    # ---- PJM ----
    Source("pjm_2026_load_forecast_report", "pjm", "PJM", "PJM 2026 Load Forecast Report (Jan 14 2026; firm / non-firm large load adjustments)",
           "https://www.pjm.com/-/media/DotCom/library/reports-notices/load-forecast/2026-load-report.pdf", filename="PJM_2026-load-report.pdf"),
    Source("pjm_2025_load_forecast_report", "pjm", "PJM", "PJM 2025 Load Forecast Report (prior vintage for comparison)",
           "https://www.pjm.com/-/media/DotCom/library/reports-notices/load-forecast/2025-load-report.pdf", filename="PJM_2025-load-report.pdf", optional=True),
    Source("pjm_load_forecast_page", "pjm", "PJM", "PJM load forecast development process page (HTML)",
           "https://www.pjm.com/planning/resource-adequacy-planning/load-forecast-dev-process", filename="pjm_load_forecast_page.html", tags=["html"], optional=True),

    # ---- EIA daily wholesale hub prices from ICE (NP15 / SP15 day-ahead peak, off-peak) ----
] + [
    Source(f"eia_ice_wholesale_{y}", "eia_wholesale", "EIA (ICE data)",
           f"EIA wholesale electricity market data from ICE, {y}: daily hub prices incl. NP15 and SP15",
           (f"https://www.eia.gov/electricity/wholesale/xls/archive/ice_electric-{y}final.{'xls' if y <= 2016 else 'xlsx'}"
            if y < 2026 else "https://www.eia.gov/electricity/wholesale/xls/ice_electric-2026.xlsx"),
           optional=True, notes="Fills 2015-Aug 2023 where CAISO OASIS no longer serves hourly DAM LMPs (about 3-year retention).")
    for y in range(2015, 2027)
] + [
    # ---- EPA eGRID ----
    Source("epa_egrid2023_rev1", "egrid", "U.S. EPA", "eGRID2023 data file (rev1), incl. CAMX subregion emission rates",
           "https://www.epa.gov/system/files/documents/2025-01/egrid2023_data_rev1.xlsx"),

    # ---- Context documents cited in the proposal ----
    Source("nerc_ltra_2025", "context", "NERC", "2025 Long-Term Reliability Assessment",
           "https://www.nerc.com/globalassets/our-work/assessments/nerc_ltra_2025.pdf"),
    Source("nerc_large_loads_gap_assessment_2026", "context", "NERC", "Assessment of Gaps in Existing Practices, Requirements, and Reliability Standards for Emerging Large Loads (Mar 2026)",
           "https://www.nerc.com/globalassets/our-work/guidelines/reliability/white-paper---assessment-of-gaps.pdf",
           filename="NERC_large_loads_gap_assessment_2026.pdf"),
    Source("nerc_large_loads_characteristics_whitepaper", "context", "NERC", "Characteristics and Risks of Emerging Large Loads (RSTC white paper)",
           "https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/whitepaper-characteristics-and-risks-of-emerging-large-loads.pdf", optional=True),
    Source("duke_rethinking_load_growth_2025_mirror", "context", "Duke Nicholas Institute (mirror: Illinois Commerce Commission docket P2025-0679)",
           "Rethinking Load Growth: Assessing the Potential for Integration of Large Flexible Loads in US Power Systems (Norris et al. 2025, NI R 25-01) - mirror; Duke site blocks scripted downloads",
           "https://www.icc.illinois.gov/docket/P2025-0679/documents/371138/files/650737.pdf",
           filename="Duke_Rethinking_Load_Growth_2025_MIRROR.pdf", tags=["mirror"]),
    Source("lbnl_queued_up_2025_osti", "context", "LBNL (via OSTI 3008763)", "Queued Up: 2025 Edition, characteristics of power plants seeking transmission interconnection as of end of 2024",
           "https://www.osti.gov/servlets/purl/3008763", filename="LBNL_Queued_Up_2025_edition.pdf"),
    Source("grid_strategies_load_growth_2025", "context", "Grid Strategies", "National Load Growth Report 2025",
           "https://gridstrategiesllc.com/wp-content/uploads/Grid-Strategies-National-Load-Growth-Report-2025.pdf"),
    Source("grid_strategies_ltra_review_2025", "context", "Grid Strategies", "Review of NERC's 2025 Long-Term Reliability Assessment",
           "https://gridstrategiesllc.com/wp-content/uploads/FINAL-2025-LTRA-Review.pdf", optional=True),
    Source("jlarc_data_centers_virginia_2024", "context", "Virginia JLARC", "Data Centers in Virginia, Report 598 (Dec 2024)",
           "https://jlarc.virginia.gov/pdfs/reports/Rpt598-1.pdf", filename="JLARC_Rpt598_Data_Centers_in_Virginia_2024.pdf"),
    Source("congress_crs_r48646", "context", "Congressional Research Service", "Data Centers and Their Energy Consumption: FAQ (R48646, May 2026)",
           "https://www.congress.gov/crs-product/R48646", filename="CRS_R48646.html", tags=["html"], optional=True),
    Source("eia_press585_dc_pilot_surveys", "context", "EIA", "EIA press release 585 (Mar 25 2026): pilot data center energy surveys",
           "https://www.eia.gov/pressroom/releases/press585.php", filename="EIA_press585.html", tags=["html"], optional=True),
    Source("sierra_club_dc_state_policies_2026", "context", "Sierra Club", "Data Center State Policies, fifty-state scan (Jan 2026) - site blocks scripted downloads",
           "https://www.sierraclub.org/sites/default/files/2026-01/policies-for-data-centers-2026.pdf", tags=["manual"], optional=True),
    Source("iea_energy_and_ai_2025", "context", "IEA", "Energy and AI (2025) report landing page - IEA blocks scripted downloads; download by hand",
           "https://www.iea.org/reports/energy-and-ai", filename="IEA_energy_and_ai_landing.html", tags=["manual", "html"], optional=True),

    # ---- Commercial market reports (gated; pages saved, PDFs by hand) ----
    Source("cbre_na_dc_trends_h1_2025_page", "market_reports", "CBRE", "North America Data Center Trends H1 2025 report page (HTML; PDF is gated)",
           "https://www.cbre.com/insights/reports/north-america-data-center-trends-h1-2025", filename="cbre_na_dc_trends_h1_2025.html", tags=["html", "manual"], optional=True),
    Source("cbre_na_dc_trends_h1_2025_profiles", "market_reports", "CBRE", "North America Data Center Trends H1 2025 market profiles page (HTML)",
           "https://www.cbre.com/insights/local-response/north-america-data-center-trends-h1-2025-market-profiles", filename="cbre_na_dc_trends_h1_2025_profiles.html", tags=["html", "manual"], optional=True),
    Source("cw_global_dc_market_comparison_page", "market_reports", "Cushman & Wakefield", "Global Data Center Market Comparison 2026 page (HTML; PDF is gated)",
           "https://www.cushmanwakefield.com/en/insights/global-data-center-market-comparison", filename="cw_global_dc_market_comparison.html", tags=["html", "manual"], optional=True),
]

STATIC += [
    # ---- Added in the audit pass (2026-09-21) ----
    Source("eia930_reference_tables", "eia930", "EIA", "EIA-930 reference tables: balancing authorities, regions (CAL = BANC, CISO, IID, LDWP, TIDC) and subregions",
           "https://www.eia.gov/electricity/930-content/EIA930_Reference_Tables.xlsx",
           notes="Needed to build the CAL region aggregate, which is not a row in the six-month files."),
    Source("caiso_curtailments_monthly_csv", "caiso", "CAISO", "Monthly wind and solar curtailment totals (MWh) since 2014, CSV behind the Managing the Evolving Grid chart",
           "https://www.caiso.com/content/charts/curtailments-monthly.csv", filename="caiso_curtailments-monthly.csv", tags=["vintage"]),
    Source("caiso_managing_evolving_grid_page", "caiso", "CAISO", "Managing the evolving grid page (HTML; hosts the monthly curtailment chart)",
           "https://www.caiso.com/about/our-business/managing-the-evolving-grid", filename="caiso_managing_the_evolving_grid.html", tags=["html"]),
    Source("caiso_key_statistics_2026_08", "caiso", "CAISO", "CAISO Key Statistics, August 2026",
           "https://www.caiso.com/documents/key-statistics-aug-2026.pdf", tags=["vintage"], optional=True),
    Source("cpuc_ra_sod_guide_2026", "cpuc", "CPUC", "2026 Resource Adequacy and Slice of Day filing guide (counting rules, PRM, QC methods)",
           "https://www.cpuc.ca.gov/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/resource-adequacy-compliance-materials/guides-and-resources/2026-ra-slice-of-day-filing-guide.pdf"),
    Source("cpuc_ra_sod_guide_2025", "cpuc", "CPUC", "2025 Resource Adequacy and Slice of Day filing guide",
           "https://www.cpuc.ca.gov/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/resource-adequacy-compliance-materials/guides-and-resources/2025-ra-slice-of-day-filing-guide.pdf"),
    Source("cpuc_lole_2026_appendix_b", "cpuc", "CPUC", "Appendix B to Loss of Load Expectation Study for 2026 (revised): LOLE and Slice-of-Day PRM proposal, Dec 2024",
           "https://www.cpuc.ca.gov/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/resource-adequacy-compliance-materials/slice-of-day-compliance-materials/appendix-b-lole-and-sod-prm-proposal_dec2024.pdf"),
    Source("cpuc_lole_2026_appendix_a", "cpuc", "CPUC", "Appendix A to Loss of Load Expectation Study for 2026 (revised)",
           "https://docs.cpuc.ca.gov/PublishedDocs/Efile/G000/M539/K203/539203368.PDF", filename="CPUC_LOLE_2026_Appendix_A_539203368.pdf"),
    Source("cpuc_d2402047_psp", "cpuc", "CPUC", "Decision 24-02-047 (Feb 2024): 2023 Preferred System Plan, 2024-2026 IRP cycle",
           "https://docs.cpuc.ca.gov/PublishedDocs/Published/G000/M525/K918/525918033.PDF", filename="CPUC_D2402047_PSP_525918033.pdf"),
    Source("cpuc_ra_oir_2025_09_30", "cpuc", "CPUC", "Order Instituting Rulemaking on resource adequacy, Sept 30 2025 (new RA proceeding)",
           "https://docs.cpuc.ca.gov/PublishedDocs/Efile/G000/M582/K082/582082526.PDF", filename="CPUC_RA_OIR_2025-09-30_582082526.pdf", optional=True),
    Source("cpuc_track3_fact_sheet", "cpuc", "CPUC", "Fact sheet on the Track 3 RA decision (slice of day, PRM)",
           "https://www.cpuc.ca.gov/-/media/cpuc-website/divisions/energy-division/documents/resource-adequacy-homepage/oga-fact-sheet-on-track-3-decision-final.pdf", optional=True),
    Source("cpuc_e3_astrape_incremental_elcc_2023", "cpuc", "CPUC / E3 / Astrape (via Wayback Machine capture 2025-11-20)", "Updated Incremental ELCC Study for Mid-Term Reliability Procurement (Feb 2023): ELCC values by technology and year",
           "http://web.archive.org/web/20251120173029id_/https://www.cpuc.ca.gov/-/media/cpuc-website/divisions/energy-division/documents/integrated-resource-plan-and-long-term-procurement-plan-irp-ltpp/20230210_irp_e3_astrape_updated_incremental_elcc_study.pdf",
           filename="CPUC_E3_Astrape_Updated_Incremental_ELCC_Study_2023-02.pdf", tags=["mirror"], notes="CPUC moved the file (404 as of 2026-09-21); Wayback capture used."),
    Source("cpuc_mtr_elcc_transmittal_memo_2023", "cpuc", "CPUC (via Wayback Machine capture 2025-11-20)", "Mid-term reliability ELCC values public transmittal memo, Feb 2023",
           "http://web.archive.org/web/20251120173028id_/https://www.cpuc.ca.gov/-/media/cpuc-website/divisions/energy-division/documents/integrated-resource-plan-and-long-term-procurement-plan-irp-ltpp/2023-02-irp_mtr_elccs-public_transmittal_memo_v1.pdf",
           filename="CPUC_MTR_ELCC_transmittal_memo_2023-02.pdf", tags=["mirror"]),
    Source("cpuc_tpp_2025_26_modeling_assumptions_deck", "cpuc", "CPUC", "2025-2026 TPP proposed decision RESOLVE and SERVM analysis slide deck",
           "https://www.cpuc.ca.gov/-/media/cpuc-website/divisions/energy-division/documents/integrated-resource-plan-and-long-term-procurement-plan-irp-ltpp/2024-2026-irp-cycle-events-and-materials/assumptions-for-the-2025-2026-tpp/25-26-tpp-pd-resolve-and-servm-analysis-slide-deck.pdf", optional=True),
    Source("cpuc_tpp_2024_25_modeling_assumptions", "cpuc", "CPUC", "Modeling assumptions for the 2024-2025 Transmission Planning Process",
           "https://www.cpuc.ca.gov/-/media/cpuc-website/divisions/energy-division/documents/integrated-resource-plan-and-long-term-procurement-plan-irp-ltpp/2023-irp-cycle-events-and-materials/assumptions-for-the-2024-2025-tpp/modeling_assumptions_24-25tpp.pdf", optional=True),
    Source("jll_na_dc_report_midyear_2025_mirror", "market_reports", "JLL (mirror: Real Estate Daily News)", "JLL North America Data Center Report, Midyear 2025 - mirror copy",
           "https://realestatedaily-news.com/wp-content/uploads/2025/08/JLL-North-America-Data-Center-Report-Midyear-2025-8.14.25.pdf",
           filename="JLL_NA_Data_Center_Report_Midyear_2025_MIRROR.pdf", tags=["mirror"]),
    Source("cbre_na_dc_trends_h2_2025_page", "market_reports", "CBRE", "North America Data Center Trends H2 2025 book page (HTML)",
           "https://www.cbre.com/insights/books/north-america-data-center-trends-h2-2025", filename="cbre_na_dc_trends_h2_2025.html", tags=["html", "manual"], optional=True),
    Source("cbre_na_dc_trends_h1_2026_page", "market_reports", "CBRE", "North America Data Center Trends H1 2026 book page (HTML)",
           "https://www.cbre.com/insights/books/north-america-data-center-trends-h1-2026", filename="cbre_na_dc_trends_h1_2026.html", tags=["html", "manual"], optional=True),
    Source("cbre_press_2025_records", "market_reports", "CBRE", "CBRE press release: Fast-growing North American data center market set records in 2025 (HTML)",
           "https://www.cbre.com/press-releases/fast-growing-north-american-data-center-market-set-records-in-2025", filename="cbre_press_release_2025_records.html", tags=["html"], optional=True),
    Source("cw_americas_dc_update_page", "market_reports", "Cushman & Wakefield", "Americas Data Center Update H2 2025 page (HTML)",
           "https://www.cushmanwakefield.com/en/insights/americas-data-center-update", filename="cw_americas_dc_update.html", tags=["html", "manual"], optional=True),
    Source("pge_quarterly_earnings_page", "cec_tiers", "PG&E Corporation", "PG&E Corporation quarterly earnings reports page (data center pipeline table by PG&E stage each quarter; Q2 2026 table reproduced in CEC docket TN 272065 p.9)",
           "https://investor.pgecorp.com/financials/quarterly-earnings-reports/default.aspx", filename="pge_quarterly_earnings_page.html", tags=["html", "manual", "vintage"], optional=True,
           notes="Manual: download each quarter's earnings presentation PDF and record the Data Center Pipeline table (Application & Preliminary Engineering, Final Engineering, ICA, Construction)."),
    Source("swrcb_otc_policy_2023", "cpuc", "State Water Resources Control Board", "Once-Through Cooling Policy as last amended August 15, 2023 (Table 1 compliance dates: Alamitos 3-5, Huntington Beach 2, Ormond Beach 1-2 by 2026-12-31; Haynes 1, 2, 8, Harbor 5, Scattergood 1-2 by 2029-12-31)",
           "https://www.waterboards.ca.gov/water_issues/programs/ocean/cwa316/docs/otc-policy-2023/otc-policy-2023.pdf", filename="swrcb_otc_policy_2023.pdf"),
    Source("swrcb_otc_program_page", "cpuc", "State Water Resources Control Board", "Once-through cooling program page (HTML)",
           "https://www.waterboards.ca.gov/water_issues/programs/ocean/cwa316/", filename="swrcb_otc_program_page.html", tags=["html"], optional=True),
    Source("jll_press_yearend_2025", "market_reports", "JLL", "JLL newsroom: North America Data Center Report year-end 2025 (HTML)",
           "https://www.jll.com/en-us/newsroom/jll-north-america-data-center-report-year-end-2025", filename="jll_press_yearend_2025.html", tags=["html"], optional=True),
    Source("ercot_board_2026_04_interconnection_update", "ercot", "ERCOT", "Interconnection and Grid Analysis Update (Jeff Billo), Apr 2026 board item 9",
           "https://www.ercot.com/files/docs/2026/04/13/9-Interconnection-and-Grid-Analysis-Update.pdf", optional=True),
    Source("ercot_large_load_process_qa_2025_12", "ercot", "ERCOT", "Large Load Interconnection Process Q&A, Dec 2025",
           "https://www.ercot.com/files/docs/2025/12/24/Large-Load-Interconnection-Process-Q-A.pdf", optional=True),
    Source("ercot_nprr1267_status_report_proposal", "ercot", "ERCOT", "NPRR1267 Large Load Interconnection Status Report proposal (Jan 2025, docx)",
           "https://www.ercot.com/files/docs/2025/01/08/1267NPRR-01%20Large%20Load%20Interconnection%20Status%20Report%20010825.docx",
           filename="ERCOT_NPRR1267_Large_Load_Interconnection_Status_Report.docx", optional=True),
]


STATIC += [
    Source("cec_ced_2025_2045_report", "cec_iepr_docket", "CEC", "California Energy Demand Forecast, 2025-2045: adopted forecast report (Jan 21 2026 business meeting item 06)",
           "https://www.energy.ca.gov/filebrowser/download/9328?fid=9328", filename="CEC_California_Energy_Demand_Forecast_2025-2045_Item06_ada.pdf"),
    Source("cec_ced_2025_2045_resolution", "cec_iepr_docket", "CEC", "Resolution adopting the California Energy Demand Forecast 2025-2045 (Jan 21 2026)",
           "https://www.energy.ca.gov/filebrowser/download/9208?fid=9208", filename="CEC_Resolution_CED_2025-2045_Item06_ada.pdf"),
    Source("cec_2025_iepr_report_page", "cec_iepr_docket", "CEC", "2025 Integrated Energy Policy Report publication page (HTML)",
           "https://www.energy.ca.gov/publications/2026/2025-integrated-energy-policy-report", filename="cec_2025_iepr_publication_page.html", tags=["html"], optional=True),
    Source("cec_ced_2025_2045_page", "cec_iepr_docket", "CEC", "California Energy Demand 2025-2045 report page (HTML)",
           "https://www.energy.ca.gov/data-reports/reports/integrated-energy-policy-report-iepr/2025-integrated-energy-policy-report-0", filename="cec_ced_2025_2045_page.html", tags=["html"], optional=True),
    Source("cpuc_d2506048_prm_2026_2027", "cpuc", "CPUC", "Decision 25-06-048 (Jun 26 2025): 18 percent planning reserve margin for 2026-2027, local and flexible capacity requirements, RA refinements",
           "https://docs.cpuc.ca.gov/PublishedDocs/Published/G000/M571/K237/571237404.PDF", filename="CPUC_D2506048_PRM_571237404.pdf"),
    Source("cpuc_r2510003_proposed_decision_2026_06", "cpuc", "CPUC", "Proposed decision in R.25-10-003 (resource adequacy rulemaking), Jun 1 2026",
           "https://docs.cpuc.ca.gov/PublishedDocs/Efile/G000/M608/K058/608058096.PDF", filename="CPUC_R2510003_PD_2026-06-01_608058096.pdf", optional=True),
]

STATIC += [
    Source("svp_fact_sheet_2017", "svp", "Silicon Valley Power (via Wayback Machine capture 20260509224755)", "Silicon Valley Power 2017 Utility Fact Sheet",
           "http://web.archive.org/web/20260509224755id_/https://www.siliconvalleypower.com/home/showpublisheddocument/63875/636918608411270000",
           filename="SVP_fact_sheet_2017.pdf", tags=["mirror"],
           notes="Original: https://www.siliconvalleypower.com/home/showpublisheddocument/63875/636918608411270000 (site blocks scripted downloads)."),
    Source("svp_fact_sheet_2018", "svp", "Silicon Valley Power (via Wayback Machine capture 20260509233703)", "Silicon Valley Power 2018 Utility Fact Sheet",
           "http://web.archive.org/web/20260509233703id_/https://www.siliconvalleypower.com/home/showpublisheddocument/66906/637200353755670000",
           filename="SVP_fact_sheet_2018.pdf", tags=["mirror"],
           notes="Original: https://www.siliconvalleypower.com/home/showpublisheddocument/66906/637200353755670000 (site blocks scripted downloads)."),
    Source("svp_fact_sheet_2019", "svp", "Silicon Valley Power (via Wayback Machine capture 20260509224600)", "Silicon Valley Power 2019 Utility Fact Sheet",
           "http://web.archive.org/web/20260509224600id_/https://www.siliconvalleypower.com/home/showpublisheddocument/66908/637200354106170000",
           filename="SVP_fact_sheet_2019.pdf", tags=["mirror"],
           notes="Original: https://www.siliconvalleypower.com/home/showpublisheddocument/66908/637200354106170000 (site blocks scripted downloads)."),
    Source("svp_fact_sheet_2020", "svp", "Silicon Valley Power (via Wayback Machine capture 20260509231536)", "Silicon Valley Power 2020 Utility Fact Sheet",
           "http://web.archive.org/web/20260509231536id_/https://www.siliconvalleypower.com/home/showpublisheddocument/72343/637515110025130000",
           filename="SVP_fact_sheet_2020.pdf", tags=["mirror"],
           notes="Original: https://www.siliconvalleypower.com/home/showpublisheddocument/72343/637515110025130000 (site blocks scripted downloads)."),
    Source("svp_fact_sheet_2021", "svp", "Silicon Valley Power (via Wayback Machine capture 20260509232142)", "Silicon Valley Power 2021 Utility Fact Sheet",
           "http://web.archive.org/web/20260509232142id_/https://www.siliconvalleypower.com/home/showpublisheddocument/76639/637812250378500000",
           filename="SVP_fact_sheet_2021.pdf", tags=["mirror"],
           notes="Original: https://www.siliconvalleypower.com/home/showpublisheddocument/76639/637812250378500000 (site blocks scripted downloads)."),
    Source("svp_fact_sheet_2022", "svp", "Silicon Valley Power (via Wayback Machine capture 20260509223802)", "Silicon Valley Power 2022 Utility Fact Sheet",
           "http://web.archive.org/web/20260509223802id_/https://www.siliconvalleypower.com/home/showpublisheddocument/79910/638151194612430000",
           filename="SVP_fact_sheet_2022.pdf", tags=["mirror"],
           notes="Original: https://www.siliconvalleypower.com/home/showpublisheddocument/79910/638151194612430000 (site blocks scripted downloads)."),
    Source("svp_fact_sheet_2023", "svp", "Silicon Valley Power (via Wayback Machine capture 20260509225205)", "Silicon Valley Power 2023 Utility Fact Sheet",
           "http://web.archive.org/web/20260509225205id_/https://www.siliconvalleypower.com/home/showpublisheddocument/83511/638470585164300000",
           filename="SVP_fact_sheet_2023.pdf", tags=["mirror"],
           notes="Original: https://www.siliconvalleypower.com/home/showpublisheddocument/83511/638470585164300000 (site blocks scripted downloads)."),
    Source("svp_financial_statement_fy2025", "svp", "Silicon Valley Power (via Wayback Machine capture 20260509224919)", "Silicon Valley Power Financial Statement, June 30 2025 (with totals as of June 30 2024)",
           "http://web.archive.org/web/20260509224919id_/https://www.siliconvalleypower.com/home/showpublisheddocument/88630/639010527486700000",
           filename="SVP_financial_statement_fy2025.pdf", tags=["mirror"],
           notes="Original: https://www.siliconvalleypower.com/home/showpublisheddocument/88630/639010527486700000 (site blocks scripted downloads)."),
    Source("svp_fact_sheet_page_wayback", "svp", "Silicon Valley Power (via Wayback Machine)", "SVP Utility Fact Sheet page, Wayback capture 2026-04-22 (HTML)",
           "http://web.archive.org/web/20260422021223id_/https://www.siliconvalleypower.com/svp-and-community/about-svp/utility-fact-sheet", filename="svp_utility_fact_sheet_page_wayback.html", tags=["html", "mirror"]),
    Source("svp_data_centers_page_wayback", "svp", "Silicon Valley Power (via Wayback Machine)", "SVP Data Centers in Santa Clara page, Wayback capture 2026-07-09 (HTML)",
           "http://web.archive.org/web/20260709222236id_/https://www.siliconvalleypower.com/businesses/data-centers-in-santa-clara", filename="svp_data_centers_page_wayback.html", tags=["html", "mirror"]),
]

STATIC += [
    Source("cpuc_oir_rate_design_2026_04", "cpuc", "CPUC", "Order Instituting Rulemaking on electric rate design incl. data centers and large transmission-connected loads, issued Apr 10 2026",
           "https://docs.cpuc.ca.gov/PublishedDocs/Published/G000/M604/K677/604677976.PDF", filename="CPUC_OIR_rate_design_large_loads_2026-04-10_604677976.pdf"),
    Source("cpuc_news_streamlined_connections", "cpuc", "CPUC", "CPUC news: streamlines electric grid connections for high-energy users like data centers and EV chargers (HTML)",
           "https://www.cpuc.ca.gov/news-and-updates/all-news/cpuc-streamlines-electric-grid-connections-for-high-energy-users-like-data-centers-and-ev-chargers", filename="cpuc_news_streamlined_connections.html", tags=["html"], optional=True),
    Source("pge_press_2025_07_31_pipeline_10gw", "context", "PG&E Corporation", "PG&E press release, Jul 31 2025: data center demand pipeline swells to 10 gigawatts (HTML)",
           "https://investor.pgecorp.com/news-events/press-releases/press-release-details/2025/PGE-Data-Center-Demand-Pipeline-Swells-to-10-Gigawatts-with-Potential-to-Unlock-Billions-in-Benefits-for-California/default.aspx", filename="pge_press_2025-07-31_pipeline_10gw.html", tags=["html"], optional=True),
    Source("pge_press_accelerating_connection", "context", "PG&E Corporation", "PG&E press release: accelerating connection of new data centers throughout Northern and Central California (HTML)",
           "https://investor.pgecorp.com/news-events/press-releases/press-release-details/2025/PGE-Accelerating-Connection-of-New-Data-Centers-throughout-Northern-and-Central-California/default.aspx", filename="pge_press_accelerating_connection.html", tags=["html"], optional=True),
    Source("pge_8k_q2_2026", "context", "PG&E Corporation (SEC)", "PG&E Form 8-K, Q2 2026 earnings press release (data center pipeline 12.7 GW)",
           "https://www.sec.gov/Archives/edgar/data/0001004980/000100498026000047/pge-q22026pressrelease.htm", filename="pge_8k_q2_2026_press_release.htm", tags=["html"], optional=True),
    Source("utilitydive_pge_127gw_2026", "context", "Utility Dive", "PG&E says it has 12.7 GW in data center pipeline as it courts smaller loads (HTML)",
           "https://www.utilitydive.com/news/pge-claims-127-gw-in-data-center-pipeline-as-utility-courts-smaller-loads/826099/", filename="utilitydive_pge_12.7gw_2026.html", tags=["html"], optional=True),
    Source("ca_sb57_2025_status", "context", "California Legislature", "SB 57 (Padilla, 2025) bill status page: data center cost-shift assessment, signed Oct 11 2025 (HTML)",
           "https://leginfo.legislature.ca.gov/faces/billStatusClient.xhtml?bill_id=202520260SB57", filename="leginfo_SB57_status.html", tags=["html"], optional=True),
    Source("ca_sb886_2026_status", "context", "California Legislature", "SB 886 (Padilla, 2026) bill status page: data center tariff for 25 MW+ transmission-level customers (HTML)",
           "https://leginfo.legislature.ca.gov/faces/billStatusClient.xhtml?bill_id=202520260SB886", filename="leginfo_SB886_status.html", tags=["html"], optional=True),
    Source("ca_ab222_2025_status", "context", "California Legislature", "AB 222 (Bauer-Kahan, 2025) bill status page: data center PUE and cost shifts (HTML)",
           "https://leginfo.legislature.ca.gov/faces/billStatusClient.xhtml?bill_id=202520260AB222", filename="leginfo_AB222_status.html", tags=["html"], optional=True),
    Source("padilla_sb57_signed_release", "context", "Office of Sen. Steve Padilla", "Press release: legislation to protect ratepayers from data center energy costs signed into law (HTML)",
           "https://sd18.senate.ca.gov/news/legislation-protect-california-ratepayers-paying-data-centers-energy-costs-signed-law", filename="padilla_sb57_signed.html", tags=["html"], optional=True),
    Source("pillsbury_ca_data_center_deal_2026", "context", "Pillsbury (law firm summary)", "California data center deal puts new large loads on a cost-causation track (Aug 2026, HTML)",
           "https://www.pillsburylaw.com/en/news-and-insights/california-data-center-deal-large-loads-cost-causation-track.html", filename="pillsbury_ca_data_center_deal_2026.html", tags=["html"], optional=True),
    Source("hansonbridgett_cpuc_data_centers_2026", "context", "Hanson Bridgett (law firm summary)", "CPUC will address electric rate impacts of data centers and other large energy users (Apr 2026, HTML)",
           "https://www.hansonbridgett.com/publications/260427_2087_cpuc-data-centers", filename="hansonbridgett_cpuc_data_centers_2026.html", tags=["html"], optional=True),
    Source("mayerbrown_ca_data_center_bills_2025", "context", "Mayer Brown (law firm summary)", "Efforts to regulate California data centers falter for now (Dec 2025, HTML)",
           "https://www.mayerbrown.com/en/insights/publications/2025/12/efforts-to-regulate-california-data-centers-falter-for-now", filename="mayerbrown_ca_data_center_bills_2025.html", tags=["html"], optional=True),
]

STATIC += [
    Source("svp_assembly_hearing_2026_01_28", "svp", "Silicon Valley Power / CA Assembly", "SVP presentation to the Assembly joint oversight hearing on Energy Impacts of AI, Jan 28 2026 (data centers 55% of power use, 51% of sales)",
           "https://autl.assembly.ca.gov/media/1404", filename="SVP_Assembly_AI_energy_hearing_2026-01-28.pdf"),
    Source("ca_sb886_2026_text", "context", "California Legislature", "SB 886 (Padilla, 2026) chaptered bill text: California Technology Innovation and Ratepayer Protection Act (HTML)",
           "https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260SB886", filename="leginfo_SB886_text.html", tags=["html"], optional=True),
    Source("ca_sb57_2025_text", "context", "California Legislature", "SB 57 (Padilla, 2025) chaptered bill text (HTML)",
           "https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260SB57", filename="leginfo_SB57_text.html", tags=["html"], optional=True),
    Source("kqed_newsom_signs_data_center_bills_2026", "context", "KQED", "Newsom signs new restrictions on data center development (Sep 2026, HTML)",
           "https://www.kqed.org/news/12100746/newsom-signs-new-restrictions-on-data-center-development", filename="kqed_newsom_signs_data_center_bills_2026.html", tags=["html"], optional=True),
    Source("sjspotlight_santa_clara_capacity_2025", "context", "San Jose Spotlight", "Santa Clara data centers hit max energy capacity (2025, HTML; data centers ~60% of Santa Clara power)",
           "https://sanjosespotlight.com/santa-clara-data-centers-hit-max-energy-capacity/", filename="sjspotlight_santa_clara_capacity_2025.html", tags=["html"], optional=True),
    Source("cec_tn261964_pge_pipeline_feb2025", "cec_iepr_docket", "CEC", "PG&E Data Center Pipeline presentation, Feb 26 2025 IEPR workshop (duplicate id guard)",
           "https://efiling.energy.ca.gov/GetDocument.aspx?tn=261964", optional=True),
]

STATIC += [
    Source("census_c30_privsatime", "census_c30", "U.S. Census Bureau",
           "Value of Private Construction Put in Place, seasonally adjusted annual rate, historical monthly time series incl. Data center (2014 onward)",
           "https://www.census.gov/construction/c30/xlsx/privsatime.xlsx", tags=["vintage"]),
    Source("census_c30_release", "census_c30", "U.S. Census Bureau", "Monthly Construction Spending release workbook (latest)",
           "https://www.census.gov/construction/c30/xlsx/release.xlsx", tags=["vintage"], optional=True),
]


def all_sources() -> list[Source]:
    srcs = (STATIC + eia930() + eia861() + eia923() + eia860() + eia860m()
            + qcew() + cec_docket())
    ids = [s.id for s in srcs]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate source ids: {sorted(dupes)}")
    return srcs


def by_group() -> dict[str, list[Source]]:
    d: dict[str, list[Source]] = {}
    for s in all_sources():
        d.setdefault(s.group, []).append(s)
    return d


if __name__ == "__main__":
    for g, ss in by_group().items():
        print(f"{g:20s} {len(ss):4d}")
    print("total", len(all_sources()))

# ---- Chapter 4 additions (2026-09-22): ERCOT operational overviews, PJM 2026 adjustment records, FERC docket RM26-4 filings ----
STATIC += [
    Source("ercot_ops_overview_2026_06", "ercot", "ERCOT", "ERCOT Monthly Operational Overview, June 2026 (large load queue by status and in-service year 2022-2033; 8,926 MW approved to energize, 3,966 MW observed)",
           "https://www.ercot.com/files/docs/2026/07/17/ERCOT-Monthly-Operational-Overview-June-2026.pdf"),
    Source("ercot_ops_overview_2026_08", "ercot", "ERCOT", "ERCOT Monthly Operational Overview, August 2026 (9,456 MW approved to energize, 4,316 MW observed in August 2026)",
           "https://www.ercot.com/files/docs/2026/09/16/ERCOT-Monthly-Operational-Overview-August-2026.pdf"),
    Source("pjm_lar_summary_2025_11_24", "pjm", "PJM", "Load Adjustment Requests Summary for the 2026 Load Forecast, preliminary (Load Analysis Subcommittee, Nov 24 2025): firm = ESO/CC, non-firm derated, 70% utilization, 36-month ramp",
           "https://www.pjm.com/-/media/DotCom/committees-groups/subcommittees/las/2025/20251124/20251124-item-03---large-load-adjustment-requests-summary.pdf"),
    Source("pjm_2026_load_report_tables", "pjm", "PJM", "2026 PJM Load Forecast Report tables (xlsx; Tables B-9 and B-9b, large load adjustments by zone, 2026-2046)",
           "https://www.pjm.com/-/media/DotCom/planning/res-adeq/load-forecast/2026-load-report-tables.xlsx"),
    Source("pjm_2026_load_adjustment_breakdown", "pjm", "PJM", "2026 load adjustment breakdown for capacity obligations (xlsx; Table B-9 adjustments above embedded by zone)",
           "https://www.pjm.com/-/media/DotCom/planning/res-adeq/load-forecast/2026-load-adjustment-breakdown-for-capacity-obligations.xlsx"),
    Source("caiso_comments_ferc_rm26_4_2025_11", "ferc", "CAISO", "CAISO comments on the FERC ANOPR Interconnection of Large Loads to the Interstate Transmission System, Docket RM26-4-000 (Nov 21 2025; describes the 20 MW threshold and CAISO's process)",
           "https://www.caiso.com/documents/nov-21-2025-comments-on-the-advanced-notice-of-proposed-rulemaking-interconnection-of-large-loads-to-the-interstate-transmission-system-rm26-4.pdf"),
    Source("nerc_rm26_4_accelerated_plan_2026_03", "ferc", "NERC", "NERC accelerated large load action plan, supplemental filing in Docket RM26-4-000 (Mar 20 2026)",
           "https://www.nerc.com/globalassets/who-we-are/legal--regulatory/filings--orders/nerc-filings-to-ferc/2026/nerc_accelerated-ll-action-plan_rm26-4_signed.pdf"),
    Source("ferc_rm26_4_docket_page", "ferc", "FERC", "FERC docket page RM26-4-000 (HTML; ferc.gov serves a JavaScript challenge to non-browser clients, so the stored file may be the challenge page; the page was read in a browser on 2026-09-22)",
           "https://www.ferc.gov/rm26-4", filename="ferc_rm26_4.html", tags=["html"], optional=True),
    Source("ferc_news_2026_04_16_large_load", "ferc", "FERC", "FERC news release, Apr 16 2026: FERC to act on the large load interconnection docket by June 2026 (HTML; same caveat)",
           "https://www.ferc.gov/news-events/news/ferc-act-large-load-interconnection-docket-june-2026", filename="ferc_news_2026_04_16.html", tags=["html"], optional=True),
]

STATIC += [
    Source("ferc_news_2026_06_18_show_cause", "ferc", "FERC", "FERC news release, Jun 18 2026: show cause orders to the six RTOs/ISOs on large load interconnection (E-7 to E-12; CAISO is Docket EL26-71-000) (HTML)",
           "https://ferc.gov/news-events/news/ferc-launches-aggressive-targeted-action-speed-large-load-integration", filename="ferc_news_2026_06_18.html", tags=["html"], optional=True),
]

STATIC += [
    Source("ercot_ops_overview_2026_04", "ercot", "ERCOT", "ERCOT Monthly Operational Overview, April 2026 (large load queue by status; approved to energize and observed load)",
           "https://www.ercot.com/files/docs/2026/05/19/ERCOT-Monthly-Operational-Overview-April-2026.pdf"),
    Source("ercot_ops_overview_2026_07", "ercot", "ERCOT", "ERCOT Monthly Operational Overview, July 2026 (large load queue by status; approved to energize and observed load)",
           "https://www.ercot.com/files/docs/2026/08/17/ERCOT-Monthly-Operational-Overview-July-2026.pdf"),
    Source("nrc_diablo_canyon_rod_2026", "context", "U.S. Nuclear Regulatory Commission", "Diablo Canyon license renewal application: Record of Decision (ML26022A077; renewed licences issued April 2 2026)",
           "https://www.nrc.gov/docs/ML2602/ML26022A077.pdf", filename="NRC_Diablo_Canyon_LRA_Record_of_Decision_ML26022A077.pdf", optional=True),
    Source("gov_ca_diablo_license_2026_04_02", "context", "Office of the Governor of California", "Governor Newsom welcomes approval of Diablo Canyon license renewals (Apr 2 2026; SB 846 limits operation to 2030 absent legislative action) (HTML)",
           "https://www.gov.ca.gov/2026/04/02/governor-newsom-welcomes-approval-of-diablo-canyon-license-renewals-delivering-on-californias-commitment-to-a-clean-and-reliable-grid/", filename="gov_ca_diablo_license_2026_04_02.html", tags=["html"], optional=True),
]
