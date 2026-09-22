# Data notes from the week-one lock-in (2026-09-21)

Findings from opening every key raw file (`scripts/verify_raw.py`, log in `logs/verify_raw_2026-09-21.log`).
Read these before starting the notebooks.

## Confirmed contents

- **CEC energization tiers.** `cec_assembly_hearing_2026_01_28` page 7 reads "5,086 MW Signed Agreements,
  9,587 MW Active Applications, 8,604 MW Inquiries", sourced to utility data as of December 2025.
- **CEC method parameters.** `cec_tn272026` (Aug 20 2026 workshop deck, docket 26-IEPR-03) states the 2025 IEPR
  assumptions explicitly: confidence levels mid/high of 0%/10% (inquiries), 33%/50% (applications), 70%/100%
  (agreements); utilization factor 67% defined as requested capacity versus actual peak; ramp rate supplied by the
  utility or linear. The same deck charts the CEC's own weighted data center demand: Planning (mid) scenario
  rising from 413 MW to 4,855 MW and Local Reliability (high) from 684 MW to 7,381 MW over the forecast horizon.
  This is the forecast RQ2's central case replicates and stress-tests.
- **Ramp assumptions.** `cec_prelim_dc_forecast_2025`: "Year 0-5: 149%, Year 6+: 113%, linear ramp over 7 years,
  source SVP", applied to projects without ramp information.
- **Project-level data exist for SCE only.** `cec_tn266008` (Aug 2025) and `cec_tn268459` (Jan 2026) are SCE's
  public data center databases: about 110 rows with status, substation, requested peak MW and MW by year
  2025-2034. PG&E filed confidentiality requests every month instead (`cec_tn265852` ... `cec_tn272858`).
  That asymmetry is itself evidence for RQ3.
- **New tier vintage is coming.** Docket 26-IEPR-03 (opened Feb 2026) holds the Aug 2026 workshop:
  data center forecast (TN 272026), energization requests / known loads (TN 272043, 272023), PG&E forecasting
  (TN 272065), SVCE, SVP, SJCE and Palo Alto filings. The monthly snapshot watches this docket.
- **EIA-930.** BALANCE files carry CISO hourly demand, net generation and interchange; SUBREGION files split
  CISO into PGAE, SCE, SDGE and VEA from July 2018. 2026 H1 max hourly CISO demand in the file is 38,369 MW.
- **EIA-860M.** All 133 monthly vintages from July 2015 to July 2026 open. The header row moves between
  vintages (row 1 in 2016, row 2 later); detect it by searching for "Plant State". California planned rows:
  145 in Jan 2016, 230 in Jul 2026.
- **QCEW 518210.** California statewide (area 06000, own_code 5 private) 2025 Q1: 4,446 establishments,
  81,355 employees. County rows are present for all 06xxx counties.
- **Epoch AI Frontier Data Centers Hub has no California site.** 87 sites, addresses in 23 states, none in CA.
  Frontier-scale AI training campuses are not being built in California; the Kollar-Grady inventory and CEC
  tiers are the California facility sources. Report this as a finding, not a data gap.
- **Kollar and Grady.** Zenodo bundle has 396 members: code (preprocessing, WRI water stress, heat, risk
  scores, Moran's I) and data. Zenodo rejects browser-like user agents; the fetcher sends `curl/8.0` for it.
- **CEC ECDMS exports.** `AGG_CONSUMPTION_ELEC_UTILITY_TBL` is 11,459 rows of YEAR, PLANNING_AREA, AGENCY_NAME,
  AGENCY_TYPE, SECTOR, GWh from 1990. The interactive ECDMS host was unreachable; these are the same tables
  served from energy.ca.gov.
- **CAISO NQC 2026** has sheets "2026 NQC List", "2026 Other", "2026 Tech Factors" (monthly QC by resource).
- **PJM 2026 report** states the firm (ESO/CC) versus non-firm derating rule in its introduction.
- **EPRI 2024** ranks California third among states by 2023 data center load; the state table is in the PDF.

## Limits found

- **CAISO OASIS retention.** OASIS returns "No data returned for the specified selection" for day-ahead LMPs
  before roughly September 2023 (tested versions 1, 3, 12). Hourly DAM prices therefore cover Sept 2023 onward.
  For 2015-2023 use `eia_wholesale` (EIA's daily ICE hub prices for NP15 and SP15, peak and off-peak) and
  CAISO's annual market reports for statistics.
- **CAISO curtailment.** The `production-and-curtailments-data` workbooks exist only for 2024 and 2025 (the
  report was discontinued June 2025). gridstatus's curtailment parser now 404s. For June 2025 onward,
  curtailment totals are in the daily renewables reports and the monthly Key Statistics PDFs; parse the PDFs.
- **CAISO Today's Outlook history** covers 2018-04-10 onward for co2, fuelsource, demand and netdemand
  (3,086 days each) and 2,118 days for renewables, which starts later.
- **Gated documents (manual):** Sierra Club fifty-state scan (403), IEA Energy and AI (403), CRS R48646 (403),
  CBRE and Cushman & Wakefield PDFs (form-gated). Download by hand, place under `data/raw/<group>/<date>/`,
  and append to the manifest.
- **Mirrors used:** Duke "Rethinking Load Growth" from the Illinois Commerce Commission docket; LBNL 2025 update
  from RTO Insider. Compare hashes with the publisher copies before citing.
- **ERCOT Monthly** March 2026 was not listed on ERCOT's presentations index; July and August 2026 not yet posted.
  The snapshot script re-checks the index each month.
- **EIA-860M August 2026** not yet published at run time (expected early October).

## Audit pass (2026-09-21, second session)

Resolved
- **OASIS retention boundary pinned.** Day-ahead LMPs return data from July 2023 onward (June 2023 and earlier return
  "No data"), about 39 months. gridstatus dropped rate-limited months silently, so `scripts/fetch_caiso_oasis.py`
  now queries OASIS directly month by month with 429 back-off and row-count validation (5 rows per hour-node:
  LMP, energy, congestion, loss, greenhouse gas). Earlier years: EIA's daily ICE hub prices (`eia_wholesale`, NP15 and SP15, 2015-2026).
- **Curtailment fully covered without gridstatus.** Monthly totals CSV since 2014 (`caiso_curtailments_monthly_csv`);
  daily PDFs June 2016 to May 2025 (3,261 files, `caiso_library/curtailment_daily_pdf`); daily renewable reports
  June 2025 onward (479 HTML files with JS arrays `x_vals`, `tot_gen_solar_iso_rtd`, curtailment MWh and MW by hour,
  `caiso_library/renewables_daily_html`); 106 monthly renewables performance reports; the 2024 and 2025 workbooks.
- **Filename truncation bug** in `src/fetch.py` fixed (extension is now preserved); the four affected CED 2025 files
  were re-fetched (hourly CAISO forecasts are 22 MB each).
- **Selection bug** in `scripts/fetch_all.py` fixed: `--group` and `--id` now select the union.
- **CBRE market series obtained as data.** The Silicon Valley chapter figures are Infogram embeds whose JSON carries the
  table; `scripts/fetch_infogram.py` saves the JSON and extracts CSVs. Figure 1 gives H1 2016 to H1 2026 MW under
  construction, preleased, new deliveries and vacancy; Figure 2 gives annual absorption and vacancy. Both the H2 2025
  and H1 2026 editions are stored as separate vintages. The full PDFs remain form-gated (not needed for the series).
- **SVP annual documents** (utility fact sheets 2017-2023, FY2025 financial statement, data center page) fetched from
  Wayback captures because siliconvalleypower.com returns 403 to scripts. 2016 and 2024 fact sheets are not archived.
- **CPUC ELCC and PRM sources** added: D.25-06-048 (18 percent PRM 2026-2027), D.24-02-047, 2025/2026 Slice-of-Day
  guides, LOLE 2026 appendices, E3/Astrape incremental ELCC study (Wayback; CPUC moved the file).
- **CEC adopted forecast report** (California Energy Demand Forecast 2025-2045, Jan 21 2026 item 06) and resolution added.
- **EIA history extended** to 2010 for EIA-861, EIA-923 and EIA-860 (EIA-861 2010-2011 use two-digit-year file names).
- **CAL region**: EIA-930 six-month files have no region rows; `eia930_reference_tables` gives BA membership.
- **Tier transcription with page citations** written to `data/processed/cec_data_center_tiers_transcription.csv`
  and the CEC method parameters to `data/processed/cec_data_center_forecast_parameters.csv`.
- **Monthly snapshot scheduled** via LaunchAgent `com.katze.capstone.snapshot` (1st of month, 09:00); the snapshot
  now also captures the monthly curtailment CSV and reads the ERCOT presentations index at its current address.

Still by hand (all optional context, none blocks the analysis)
- Sierra Club fifty-state policy scan (403), IEA Energy and AI (403), CRS R48646 (403).
- CBRE, Cushman & Wakefield and JLL full PDFs (form-gated); the series needed from CBRE is captured as data.
- SVP 2016 and 2024 utility fact sheets (not in Wayback); ERCOT Monthly March, July and August 2026 (not on the
  index yet); EIA-860M August 2026 (not yet published). The monthly snapshot re-checks ERCOT and EIA-860M.
- **SVP FY2025 financial statement is truncated** in the Wayback capture (5,242,880 of 6,046,530 bytes) and does not
  open; download the original by hand from the SVP Utility Fact Sheet page and re-record it. The 2017-2023 fact
  sheets are complete (one page each: accounts, peak demand, load factor, line miles).
- **Daily renewable report HTML files do contain the data**: one inline script declares arrays such as
  `curt_hourly_econ_system`, `curt_hourly_econ_local`, `curt_hourly_ss_local`, `curt_hourly_ss_system` (24 hourly
  values, MWh), `curt_monthly_ytd_*` and wind/solar generation series. Parse with a regex over `name = [...]` pairs
  (see the check in `logs/verify_raw_2026-09-21.log`); `x_vals` is built at runtime and is empty in the file.
- **Monthly curtailment CSV** columns are `Date`, `Wind and solar curtailment` (MWh) and a third column whose header
  is the file's as-of date; ignore the third column.

## Completeness check (2026-09-21, `scripts/check_coverage.py`, log in `logs/check_coverage_2026-09-21.log`)

Expected-versus-actual for every periodic dataset: EIA-930 half-years (all 64 files, CISO hour counts complete for every
finished half-year), EIA-861/923/860 years 2010 onward, all 133 EIA-860M vintages, all 45 QCEW quarters and annual files,
all five Today's Outlook series (3,086 days each, no missing day from 2018-04-10 to 2026-09-20), all 3,259 daily
curtailment reports from 2016-06-30 to 2025-05-31 (CAISO's own filenames are irregular; one file named
`...report02dec_2020.pdf` contains the December 2, 2021 report, and `...july-31-2024-v2.pdf` is the July 31, 2024 report),
all 477 daily renewable reports from 2025-06-01 (November 5, 2025 is a "-corrected" file), all 106 monthly renewables
performance reports (HTML pages), and OASIS day-ahead LMP months July 2023 to September 2026 for both node groups
(September 2026 is partial because the month is not over). The only registered items not on disk are ERCOT Monthly
March, July and August 2026 (not published by ERCOT as of 2026-09-21), EIA-860M August 2026 (not yet released), and the
optional gated documents listed above.

## CBRE market series (added in the completeness pass)

`scripts/fetch_infogram.py` now reads Infogram table cells (spreadsheet-style dicts) as well as chart cells. Overview
tables were captured for seven editions (H1 2023, H2 2023, H1 2024, H2 2024, H1 2025, H2 2025, H1 2026). Table layouts:
Figure 1/2 "state of the market" (older editions merge available MW and vacancy in one cell), the "Total Inventory /
Under Construction" table (present in H2 2023, H1 2025, H2 2025, H1 2026), and the "% Change" table of year-over-year
change in under-construction MW. `scripts/assemble_cbre_series.py` parses all three layouts into
`data/processed/cbre_california_market_series.csv` (275 rows: market, period, metric, value, source file). Silicon
Valley is a primary market in every edition; Southern California is a secondary market from H1 2024; Sacramento is not a
CBRE market (JLL names it as an emerging Northern California submarket; JLL's Midyear 2025 report gives Northern
California 810 MW and Southern California 355 MW of colocation inventory). The Silicon Valley chapter history table
(H1 2016 to H1 2026) is the longest series and should be the report's primary California construction proxy.

## Chapter 1 findings that affect later chapters (2026-09-21, `scripts/run_chapter1.py`)

- **EIA-930 CISO demand includes storage charging; CAISO's reported demand excludes it.** In 2025 the hourly gap
  between the two tracks CAISO's battery charging with slope 0.91 and correlation 0.87 (14.2 TWh of charging in 2025).
  The processed hourly table carries both `demand` (EIA) and `demand_ex_storage` (EIA minus CAISO charging). Use the
  EIA definition for grid load, the ex-storage one for end-use load.
- **EIA-930 artifacts.** 347 hours (325 in Jan-May 2019) have EIA demand below 85 percent of CAISO demand plus
  charging or under 5 GW; they are nulled (`ch1_eia930_flagged_hours.csv`) and annual energy is mean x calendar hours.
- **Net-peak timing.** The 100 highest net-load hours start at a median of 20:00 since 2023 (18:00 in 2019), 90-98
  percent in Jul-Sep, with solar contributing 0.6-1.2 GW on average: use these hours for the capacity side of the gap.
- **Negative day-ahead prices** at the SCE DLAP: 1,131 hours (2024), 877 (2025), 890 (2026 to Sep 22); PG&E 190-294.
  OASIS retention starts July 2023, so the price history is 2024-2025 full years only.
- **Carbon intensity** (load-based, incl. imports): 257 g/kWh (2019) to 195 (2025); eGRID CAMX 2023 = 198 g/kWh.
- **Existing data center load, four ways:** EPRI 9.3 TWh (2023); CEC 1,000 MW existing peak (Dec 2025) = 7.0-8.3 TWh;
  count-based bottom-up from 321 Kollar-Grady points 8.4-18.3 TWh (Epoch has no CA site); SVP cluster 2.4-2.8 TWh.
  Retail sales denominator: EIA-861 2024 Parts A+C+D = 245.7 TWh (Part B duplicates C). Pipeline/existing peak = 23x.
- **Institutional record.** Single Forecast Set Agreement (TN 269506 pp. 7-8) keeps IRP and bulk TPP on the 2024 IEPR
  forecast and RA 2027 on the 2025 IEPR without known loads; CPUC R.26-04-009 (Apr 2026) covers large-load rate
  design; SB 57 chaptered 2025-10-11; SB 886 chaptered 2026-09-21 (tariffs by 2028-01-01); AB 222 held 2025-08-29;
  PG&E Rule 30 interim approved 2025-07-24; PG&E pipeline 1.5 GW (Feb 2025) -> 10 GW (Jul 2025) -> >12 GW (Q2 2026);
  SCE public database Jan 2026: 8,298 MW requested, 3,137 MW canceled.

## Chapter 1 audit corrections (2026-09-21, second pass)

- **EIA-930 interchange gap.** No CISO interchange value exists in the reported, imputed or adjusted columns from
  2024-07-02 to 2024-11-03 (2,232 hours), plus 24-96 hours in 2021, 2023 and 2025. Hydro is missing for 2,196 hours
  of 2019 and 5,675 of 2020. Reading only the Adjusted columns had silently undercounted 2024 net imports (23.4 TWh);
  the loader now coalesces adjusted -> imputed -> reported, and remaining gaps are filled from CAISO's own five-minute
  imports and hydro (hourly means) through a per-year linear calibration fitted on overlapping hours (imports:
  correlation 0.986-0.995, EIA = 0.9 x CAISO + ~0.9 GW). Corrected 2024 net imports: 31.7 TWh (14 percent of demand).
  Fill log: `ch1_eia930_fill_log.csv`.
- **Carbon intensity.** CAISO nets export emissions against imports, so net CO2 is negative in 374 hours of 2024 and
  425 of 2025. Those hours were previously dropped; intensity is now floored at zero and the hours kept. Annual
  energy-weighted intensity: 2024 201 g/kWh, 2025 188 g/kWh (was 207 and 195).
- **Bottom-up estimate** now separates facility count (321 Kollar-Grady points in California; Epoch has 0 California
  addresses of 87, checked programmatically) x average peak per facility (SVP anchor 7.1 MW, scaled 0.7/1.0/1.3) x
  utilization (0.50/0.67/0.80): 7.0-20.7 TWh (2.8-8.4 percent of 2024 retail sales).
- **Exploration-time errors** seen while building the chapter (eGRID path guess, EIA-861 header lookup, pandas fillna
  with an ndarray, CAISO '0:05' timestamps, a broken string in the table generator) were all fixed in
  `src/ch1_baseline.py` and `scripts/make_ch1_tables.py`; none affects the outputs, which are produced by `make ch1`.
