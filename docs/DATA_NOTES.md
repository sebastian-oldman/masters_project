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
- **Epoch AI Frontier Data Centers Hub has no California site.** 87 sites in the 2026-09-21 snapshot (89 in the 2026-09-22 snapshot), addresses in 23 states, none in CA.
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

## Chapter 2 findings that affect later chapters (2026-09-21, `scripts/run_chapter2.py`)

- **Census C30 data center line (SAAR):** $1.64B (Jan 2014) -> $13.9B (Nov 2022) -> $75.2B (Jul 2026 prelim.); 10.0% of private
  nonresidential construction. Chow with December 2022 as the first post-launch observation: F = 63, p < 0.001; growth 26%/yr [22, 31] through Nov 2022, 53%/yr [46, 61] from Dec 2022 (assigning November to the post period gives 54).
  Bai-Perron (15% trimming, up to five breaks so the choice is uncensored): BIC and LWZ choose four breaks, Oct 2016, Dec 2018,
  Mar 2022, Jun 2024; segments 53% / 42% / 9% / 61% / 36% per year, the last (Jun 2024-Jul 2026) 36% [31, 41]. Sequential
  supF(l+1|l) with bootstrap p: 1|0 p = 0.02, 2|1 p = 0.085 (stops at one break at 5%), 3|2 p = 0.02, 4|3 p = 0.005.
  supF(0|1) = 125, bootstrap p = 0.01; ruptures agrees within a month for m = 4. (Audit note: with the search capped at three
  breaks the first pass reported three; the cap was binding.) ARIMA(1,1,1)+drift and ETS(A,Ad,N): ~$95-100B by Jul 2027,
  $115-135B by Jul 2028, 95% bands ~$50-260B. The SA history is `census_c30_privsatime` (privtime.xlsx is NSA only).
- **California proxies decelerated after 2022:** QCEW 518210 CA (now from 2014Q1; the BLS API has no 518210 slice before 2014)
  employment 24.5k (2014Q1) -> 74k (2022Q4) -> 84k (2026Q1), growth 12%/yr -> -0.3%/yr after 2023Q1 (Chow F = 15, p < 0.001;
  single-break bootstrap p = 0.035; BIC 4 breaks, last 2023Q3; sequential 0); establishments 1,327 -> 4,494, 11% -> 0.5%
  (F = 11; bootstrap p = 0.285; sequential 0); wages 22% -> 11% (p = 0.007), breaks 2019Q1, 2021Q4. CBRE Silicon Valley under
  construction 44 MW (H1 2016) -> 142 MW (H2 2022) -> 125-168 MW since, no break at H1 2023 (p = 0.61), BIC break H2 2020, LWZ
  and sequential none (p = 0.14); Epoch frontier sites: US 0 -> 15.3 GW (no site in California by country/address fields and
  none of the 87 sites has a California address), California 0 of 87. Cushman tables gated; JLL single period only.
- **Tier vintages** (`ch2_tier_vintages.csv`): Dec 2024 PG&E+SCE agr.+appl. 6,771 MW; summer 2025 seven utilities 21,756 MW,
  with PG&E 10,080 agr.+appl. / 1,588 inquiries and SCE 143 / 5,685 from the published deck p.7 (the Nov 12 2025 workshop copy
  TN267165 labelled SCE 2,492 and SVP 1,382; published deck: 143 and 1,375, used here); Dec 2025 5,086 / 9,587 / 8,604 =
  23,277 MW (memo Table 1 by utility sums to 23,278); Aug 2026 workshop restates Dec 2025. SCE database: Aug 2025
  51/216/5,934 active + 709 canceled; Jan 2026 76/3,314/1,772 + 3,137 canceled. PG&E earnings pipeline (PG&E stages, no
  inquiries; TN272065 p.9, Q2 2026 earnings): Mar 2026 1,700 appl.+prelim. eng. / 3,110 final eng. / 140 ICA / 140 construction
  = 5,090; Jun 2026 8,200 / 3,880 / 490 / 140 = 12,710. Cal Advocates (TN272807): only ~650 MW of WPAs filed at the CPUC.
  Docket sweep (25-IEPR-03 and 26-IEPR-03 logs, 2026-09-21): no further public tier vintage; PG&E's monthly data center data
  requests are confidential (TN268048, TN272858 etc.).
- **RQ1 denominators** (`ch2_rq1_denominators.json`): CAISO record 52,061 MW (2022-09-06 16:57) and hourly 51,104 MW; 2025 peak
  43,860 MW; existing DC peak ~1,000 MW; existing avg load 800-1,065 MW (chapter 1 statewide estimate A and assumed conversion B only); CED 2025
  planning-scenario CAISO managed net peak 46,479 -> 50,498 MW (2025-2030, +4,019); baseline consumption peak 50,502 -> 56,180;
  data center at CAISO peak 96 -> 1,743 MW (local reliability 4,377); statewide energy 263,196 -> 298,167 GWh; data-center-only
  deliveries 729 -> 12,078 GWh (sum of planning-area totals; the DC form's STATEWIDE row is empty). Ratios (California-only 20,677 MW; VEA's 2,600 MW are in Nevada): 39.7% of record peak (44.7% for the reported 23,277 MW), 20.7x existing DC peak, 19-26x existing avg load, 5.1x IEPR peak growth to 2030 (3.4x at 67% utilization), energy-equivalent 107 TWh = 3.1x statewide energy growth.

## Review response (2026-09-22): claims checked against the code and data, and what changed

- **Fig 1.04 heatmap (confirmed).** Each panel had its own colour normalisation under one colourbar. Fixed: common vmin/vmax across years.
- **Figs 1.01-1.03 (confirmed, disclosure added).** Valid demand hours 8,435 / 8,783 / 8,760 / 8,760 / 8,759 / 8,757 / 8,743 (2019-2025); 2019 misses 325 hours (3.7%). Axis now "percent of valid hours"; legend carries the counts; captions state the artifact filter, the CAISO fills and that annual energy = mean of valid hours x calendar hours. The storage-adjusted curve is labelled as the estimated net fleet charging (pumped storage not removed) and missing battery hours stay NaN instead of zero charging.
- **Fig 1.05 (confirmed).** Axis truncation is now stated with the extremes (2024 maxima 649 / 628 / 637 $/MWh; minima -33 / -67 / -63); one colour per DLAP in both panels.
- **Fig 1.06 (confirmed).** Partial years are no longer ranked against full years: the left panel shows complete 2024 and 2025 and matched Jan 1-Sep 22 windows with the share of hours (`ch1_negative_price_hours_windows.csv`: SCE 1,045 / 775 / 890 hours = 16 / 12 / 14%).
- **Fig 1.07 carbon (largely confirmed; rebuilt).** (a) Clipping: 374 (2024) and 425 (2025) negative hours; flooring moved 2025 from 186.31 to 187.68 g/kWh. The headline is now the unclipped accounting series; the floored series is a sensitivity. (b) All-missing hours: the old loader summed NaN sources to 0 t/h (four 2024 days had 2-9 such hours); fixed with min_count and an explicit valid-hour rule (>= 6 of 12 intervals for CO2 and demand, demand > 5 GW). (c) DST: CAISO's daily files are a fixed 288-row clock grid on every day, including transition days, so there is no repeated hour to recover; documented as a <= 2 hour/year limitation. (d) EIA's December 2023 warning: verified for EIA-930 (CISO gas matches CAISO's fuel mix to 0.1 TWh/month through Nov 2023, then exceeds it by 0.7-1.8 TWh/month: +20 TWh in 2024, +25 TWh in 2025), but not for CAISO's own CO2 accounting (implied gas factor 432-452 kg/MWh in every month Jun 2023-Jun 2024; CAISO gas share 48.8 / 47.8 / 47.9% Nov-Jan). Chapter text, table and figure now say so; `ch1_gas_series_comparability_monthly.csv` holds the check. (e) Found while checking: the fuel-source files use 'Natural gas' / 'Large hydro' before mid-2021, which the loader did not read (CAISO gas showed 0 TWh for 2019-2020); fixed (65 / 74 / 79 TWh). eGRID CAMX is labelled a generation output rate with a different boundary; the percentile band is labelled variability.
- **Fig 1.08 existing use (confirmed; rebuilt).** Items regrouped as A statewide estimate (EPRI 2023: 9.33 TWh = 3.9% of EIA-861 2023 retail sales of 239.5 TWh; EPRI's own 3.70% uses a different denominator), B assumed conversion (CEC ~1,000 MW x assumed 0.80-0.95 load factor, 7.0-8.3 TWh, 2.9-3.4% of 2024 sales), C illustrative sensitivity (321 facility points x assumed 42 GWh per facility = 55% of SVP 2023 retail sales / 58 facilities, scaled 0.5-1.0: 6.8-13.6 TWh; no peak or utilization factor), D SVP subset (53-60% of SVP retail sales 4.48 TWh, supply 4.59 TWh: 2.4-2.7 TWh). The old bottom-up (energy share applied to a peak, utilization used as a load factor; 7.0-20.7 TWh) is withdrawn. The chapter-2 average-load denominator now uses A and B only (800-1,065 MW).
- **Fig 2.01 (confirmed).** Labelled national nominal dollars, SAAR.
- **Fig 2.02 (confirmed).** The first post-launch observation is now December 2022: pre/post growth 26.2% / 53.2% (was 26.3% / 53.9% with November in the post period); Chow F unchanged at 63.0. Forecasts labelled as back-transformed log medians; rolling-origin backtest added (`ch2_census_forecast_backtest.csv`): 12-month MAPE 14% ARIMA, 19% ETS, 13% drift benchmark, 31% naive; 95% coverage 92% / 79%; all models biased low. Forecasts are exploratory and national.
- **Fig 2.03 (confirmed).** Epoch's missing California observations are a coverage limit and are described as such; no California series is drawn. Tiny p-values printed as <0.001; the single-break column is labelled as the one-break fit.
- **Fig 2.04 and RQ1 (confirmed; rebuilt).** The memo's Table 1 footnote places VEA's 2,600 MW in Nevada; California-only totals are 20,677 MW (Dec 2025; 20,678 by utility rows) and 19,156 MW (summer 2025). Nevada is hatched and the California totals are labelled; the 1 MW rows-versus-marginals difference is stated, not edited away. SCE's noncanceled totals fall from 6,201 to 5,162 MW (canceled 709 -> 3,137); cancellations are drawn beside, not on top of, the active bars. The three source families are divided and the title says they are not one growth series. The RQ1 table is California-only with Nevada and the reported total as memo rows: 39.7% of the CAISO record instantaneous peak (scale reference only), 47.1% of the 2025 peak, 20.7x existing DC peak, 19-26x existing average load, 5.1x IEPR managed-net-peak growth 2025-2030 (3.4x at 67%), 107 TWh = 3.1x statewide energy growth.
- **Not changed (deferred with reasons).** An independent check of the CAISO CO2 accounting against CAISO's GHG tracking reports, and an inflation adjustment of the Census series, need sources not yet in the raw store; both are listed for the supply chapter. The CBRE, QCEW, OASIS and Census values the review reproduced were confirmed unchanged.

## Chapter 3 findings that affect later chapters (2026-09-22, `scripts/run_chapter3.py`, about 6 minutes)

- **Supply series** (`ch3_supply_by_year.csv`): EIA-923 in-state generation by resource 2010-2025 (204 -> 205 TWh; gas 109 -> 75 TWh,
  53% -> 36% of in-state; solar 0.8 -> 55 TWh; solar+wind 3% -> 34%; nuclear halved after San Onofre); CEC statewide net imports
  2012-2024 (103 -> 62 TWh, 34% -> 22% of the total system; 2025 not yet published). EIA-923 and CEC in-state totals agree within
  1% in every overlapping year. The CEC per-year page captured for 2021 repeats the 2020 table (flagged in
  `ch3_cec_imports_by_year.csv`); the multi-year table is used. Hydro is not split by size in EIA-923 (no unit capacity).
- **Capacity** (`ch3_eia860_capacity_by_resource.csv`): EIA-860 operable nameplate 72.6 GW (2010) -> 107.4 GW (2025); solar 0.5 -> 24.8 GW;
  batteries 0 -> 14.9 GW / 50.6 GWh (281 units; `ch3_battery_capacity.csv`); gas 45.5 -> 40.4 GW. Classification is by energy source
  and prime mover (EIA's Technology field starts only in 2012-2013). CAISO curtailment 0.19 TWh (2015) -> 3.77 TWh (2025); 4.95 TWh in
  Jan-Aug 2026 (`ch3_caiso_curtailment_annual.csv`).
- **Retirements** (`ch3_eia860m_planned_retirements.csv`, `ch3_otc_units.csv`): EIA-860M July 2026 planned dates 3,364 MW through 2030
  (2026: Alamitos 3-5 + Huntington Beach 2 = 1,333; 2027: Ormond Beach 1-2 = 1,612; 2029: 408 incl. Scattergood 1-2). OTC policy
  (SWRCB, amended 2023-08-15, Table 1; manifest `swrcb_otc_policy_2023`): Alamitos/Huntington/Ormond 2026-12-31; Haynes 1, 2, 8,
  Harbor 5, Scattergood 1-2 2029-12-31; Diablo Canyon 1-2 2030-10-31 (SB 846). Haynes (724 MW), Harbor 5 (75 MW) and Diablo Canyon
  (2,323 MW) have no EIA retirement date; the policy dates are used for them in case C. Total through 2030: 6,486 MW.
- **Realization model** (`ch3_vintage_outcomes.csv` and `ch3_realization_by_*.csv`): January EIA-860M planned lists 2016-2022 for
  California, outcome in the December 2025 file (its Canceled or Postponed sheet is cumulative; units absent from every sheet are
  treated as cancelled). 925 unit-vintages, 513 units, 64 GW: 69% of units / 65% of MW operating by Dec 2025; by vintage 66/51/50/68/
  76/71/68% of MW; solar 71%, batteries 76%, wind 78%, gas 44%, geothermal 6%; under construction 77% vs approvals not initiated 54%.
  Logit (cluster-robust by unit, `ch3_logit_coefficients.csv`): lead time OR 0.46/yr (p<0.001), window OR 1.17/yr (p=0.005), under
  construction OR 1.98 (p=0.055), gas OR 0.44 (p=0.075), geothermal OR 0.11 (p=0.052), log MW OR 1.17 (p=0.09); AUC 0.78, pseudo R2
  0.18. Delay among completers: median 3.0 months, 26% on time or early, 24% > 12 months late, p90 24 months; cumulative incidence
  of completion (cancellation as competing risk, step values) 53% at 12 months, 62% at 24, 68% at 36, 70% at 60; cancellation 23% by 60 months.
  Capacity basis: net summer MW for the January 2016 vintage (no nameplate column), nameplate afterwards.
- **2030 cases** (`ch3_cases_2030.csv`, `ch3_cases_2030_summary.json`): existing Dec 2025 107.5 GW; July 2026 planned list through
  2030 = 229 units, 20,054 MW (batteries 9,922; solar 7,931; pumped storage 1,600 = Whale Rock 600 + Haiwee 1,000, approvals not
  initiated; wind 344; gas engines 170); model-weighted 13,221 MW (batteries/solar 71%, wind 78%, gas 31%, pumped storage 13%; under
  construction 88%, approvals not initiated 36%). ELCC (E3/Astrape 2023 Table 1, Tranche 6 = 2028): solar 8.8%, in-state wind 14.7%,
  4-hour battery 76.5%, 8-hour PSH 88.7%; firm resources 0.95 (biomass/oil 0.90, other 0.80) and hydro 0.55/0.45 are stated assumptions.
  Capacity factors 2023-2025: gas 0.244, nuclear 0.879, hydro 0.342, geothermal 0.430, wind 0.265, solar 0.244.
  A everything builds 127,566 MW / 236 TWh / 78,297 MW ELCC; B model-weighted 120,732 / 231 / 74,467; C minus retirements
  114,246 / 204 / 68,306 (Diablo Canyon continuing: 116,569 / 222 / 70,512). For gas, energy at the fleet-average capacity factor
  overstates the energy of retiring peakers.
- **Not available / limits:** CEC statewide imports before 2012 and for 2025 (the CEC per-year pages for 2010-2014 return 404; the
  EIA state profile table was not retrievable); hydro small/large split in EIA-923; the CAISO NQC list carries no nameplate, so
  class-level NQC ratios were not derived (ELCC/derate assumptions used instead).

## Chapter 3 audit (2026-09-22): most recent data, integer years, and where each reported number lives

- **Newest inputs added.** `eia923_2026` (EIA-923 monthly file through June 2026, released 2026-08-21; contains EIA "State-Fuel Level
  Increment" rows for annually reporting plants, so it is a statewide estimate, preliminary). EIA-930 2026 Jan-Jun for CAISO net imports.
  EIA-860M July 2026 for capacity and batteries (August 2026 not published as of 2026-09-22, checked). CEC 2025 total-system page
  returns 404 and the multi-year table still ends in 2024 (re-checked 2026-09-22). Curtailment CSV re-fetched: unchanged, through Aug 2026.
  Outputs: `ch3_generation_jan_jun_2025_2026_monthly_respondents.csv` (Jan-Jun 2025 97.4 TWh vs 2026 89.6 TWh; gas 30.6 -> 22.2, solar
  27.5 -> 29.1, hydro 15.1 -> 13.7, nuclear 8.7 -> 9.5), `ch3_caiso_net_imports_jan_jun.csv` (15.7 -> 20.6 TWh), `ch3_capacity_snapshot_2026_07.*`
  (109.4 GW; batteries 305 units, 16.3 GW, 55.6 GWh). A matched-plant comparison is NOT valid for the monthly file (its increment rows
  absorb annual respondents), so the comparison is done on all rows in both years.
- **Integer years.** All year and month columns in ch3 outputs are nullable integers (no more 2025.0); the notebook's `table()` helper
  calls `convert_dtypes()` so integer-valued columns display as integers; figure axes use integer year ticks.
- **Model specification.** `ch3_logit_specs.csv`: A lead time + window + status (main); B without status; C planned year + vintage fixed
  effects (the literal "planned year" specification). Same technology and status ranking across specifications.
- **Provenance of the numbers quoted in the chapter and in the summary to the user** (all are in the files below; figures now print them):
  | number | file (field) | table | figure |
  |---|---|---|---|
  | in-state 204 -> 205 TWh; gas 109 -> 75 TWh; solar 0.8 -> 55 TWh | `ch3_supply_by_year.csv` | ch3_generation | fig3_01 (labels 2010, 2025) |
  | gas share 53 -> 36 %; solar+wind 3 -> 34 %; imports 34 -> 22 % | derived from `ch3_supply_by_year.csv` | -- | fig3_01 right panel (end labels) |
  | net imports 103 (2012) -> 62 TWh (2024) | `ch3_cec_generation_multi_year.csv` (Net Imports) | ch3_generation | fig3_01 (label 2024) |
  | capacity 73 -> 107 GW; 109 GW Jul 2026 | `ch3_eia860_capacity_by_resource.csv`, `ch3_capacity_snapshot_2026_07.json` | ch3_capacity | fig3_02 left (labels) |
  | batteries 15 GW / 51 GWh (2025), 16.3 GW / 56 GWh (Jul 2026) | `ch3_battery_capacity.csv`, snapshot json | ch3_capacity | fig3_02 middle (labels) |
  | curtailment 0.2 -> 3.8 TWh; 4.9 TWh Jan-Aug 2026 | `ch3_caiso_curtailment_annual.csv` | ch3_capacity | fig3_02 right (bar labels) |
  | retirements 6.5 GW through 2030 (EIA 3.4; OTC-only 0.8; Diablo 2.3) | `ch3_eia860m_planned_retirements.csv`, `ch3_otc_units.csv`, `ch3_cases_2030_summary.json` (retirements_through_2030_mw) | ch3_retirements | fig3_03 (box and bar labels) |
  | 925 unit-vintages, 513 units, 64 GW, 65 % of MW / 69 % of units completed | `ch3_logit_summary.json`, `ch3_realization_by_vintage.csv` | ch3_realization_vintage | fig3_04 top-left (box) |
  | by technology 71/76/78/44/6 %; by status 77 vs 54 % | `ch3_realization_by_technology.csv`, `ch3_realization_by_status.csv` | ch3_realization_tech, ch3_realization_vintage | fig3_04 top-right |
  | odds ratios 0.46, 1.17, 1.98, 0.44, 1.17; AUC 0.78 | `ch3_logit_coefficients.csv`, `ch3_logit_summary.json` | ch3_logit | fig3_04 bottom-left (box) |
  | median delay 3.0 months; 26 % on time; 24 % > 12 months; CIF 53/62/70 %; cancel 23 % | `ch3_logit_summary.json` (delay), `ch3_delay_cif.csv` | ch3_delay | fig3_04 bottom-right (markers and box) |
  | planned 20.1 GW / 229 units; weighted 13.2 GW; shares 71/78/31/13 %; 88 vs 36 % by status | `ch3_planned_current_weighted.csv`, `ch3_cases_2030_summary.json` | ch3_cases_2030 | fig3_05 (box) |
  | cases 128/121/114 GW, 236/231/204 TWh, 78/74/68 GW; Diablo continuing 117/222/71 | `ch3_cases_2030.csv`, `ch3_cases_2030_summary.json` | ch3_cases_2030 | fig3_05 (bar labels) |

## Chapters 1 and 2 audit (2026-09-22): newest data, annotated figures, and where each reported number lives

- **Newest inputs re-checked.** Epoch hub re-fetched: snapshot now 89 sites (was 87), 75 in the US, still none in California; US cumulative
  power 15.2 GW at Sep 2026 (was 15.3). EIA-930 2026 Jul-Dec refreshed (server file of 2026-09-22). Census C30 file on disk already
  carries the Sep 1 2026 release (July 2026 preliminary); next release Oct 1. QCEW 2026 Q2 not yet published (404). EIA-861 2025 and
  EIA-860M Aug 2026 not yet published (server 503/HTML). OASIS prices run to Sep 22, 2026 in the repository. The chapter 1 hourly
  series intentionally end at 2025 (complete years); 2026 appears where a matched window is possible (negative-price hours).
- **Integer years.** Notebooks 01 and 02 show no float-formatted years (scanned); all year columns are integers.
- **Figures now print the quoted numbers.** fig1_01 (annual demand range, peak record, load factor), fig1_02 (minimum net load, hours
  below zero with and without battery charging), fig1_03 (12-14h and 20h means per season, 2019 vs 2025), fig1_04 (median start hour,
  Jul-Sep share, 17-21h share per year), fig1_05 (price extremes; 11-14h and 18-20h mean price ranges), fig1_06 (negative-hour counts
  and shares; share of negative hours in 10-16h), fig1_07 (2019 and 2025 intensities, 2025 percentiles, floored variant, seasonal
  midday and night means), fig1_08 (all four estimates with shares), fig2_01 (Jan 2014, Nov 2022 and Jul 2026 values, shares of
  nonresidential construction, mean month-over-month growth), fig2_02 (segment growth, supF and sequential test; forecast medians,
  bands and backtest), fig2_03 (QCEW, CBRE and Epoch end values), fig2_04 (California-only total and its three ratios).
- **Provenance of the numbers quoted in chapters 1 and 2 and in the summaries to the user:**
  | number | file (field) | table | figure |
  |---|---|---|---|
  | annual demand 216-224 TWh; peak 51.1 GW Sep 6 2022; load factor 0.50-0.58 | `ch1_ciso_annual_summary.csv` (energy_TWh, peak_demand_MW, load_factor) | ch1_annual_summary | fig1_01 |
  | min net load -3.3 GW (2025); 80 / 205 hours below zero excl. charging (2024 / 2025) | `ch1_ciso_annual_summary.csv` (min_net_load_MW); `ciso_hourly_2019_2025_clean.parquet` (net_load_ex_storage) | ch1_annual_summary | fig1_02 |
  | spring 12-14h net load 10.6 -> 6.4 GW; 20h ~22 GW; summer 18.2 -> 9.8 GW | `ch1_seasonal_profiles.csv` | -- | fig1_03 |
  | top-100 hours: median 18:00 -> 20:00; Jul-Sep >= 90%; 17-21h >= 78%; solar 0.6-1.2 GW; gas 17-23 GW; imports 4-9 GW | `ch1_top100_net_load_timing.csv` | ch1_top100_timing | fig1_04 |
  | SCE negative hours 1,131 / 877 / 890; matched window 1,045 / 775 / 890; 77-94% in 10-16h; midday USD 8-29, evening 51-65 | `ch1_price_stats.csv`, `ch1_negative_price_hours_windows.csv`, `ch1_price_by_hour_of_day.csv` | ch1_price_stats | fig1_05, fig1_06 |
  | price extremes 2024 max 649/628/637 | `caiso_dam_lmp_hourly.parquet` | ch1_price_stats (max) | fig1_05 |
  | carbon 257 -> 186 g/kWh (floored 188); P5 1, P95 319; spring midday 10, summer 46; night 237-315; eGRID 198 | `ch1_carbon_intensity_annual.csv`, `ch1_carbon_intensity_diurnal.csv`, `ch1_egrid_camx_2023.json` | ch1_carbon | fig1_07 |
  | existing use: EPRI 9.3 TWh = 3.9% (2023); CEC 7.0-8.3 TWh; sensitivity 6.8-13.6; SVP 2.4-2.7 | `ch1_dc_load_estimates.csv`, `ch1_ca_retail_sales_eia861.csv`, `ch1_svp_fact_sheets.csv` | ch1_dc_estimates | fig1_08 |
  | Census $1.6B -> $13.9B -> $75.2B; shares 0.5 / 2.1 / 10.0%; MoM 1.2% vs 4.1% | `ch2_census_c30_data_center.csv` | -- | fig2_01 |
  | Chow F 63; 26% -> 53%; BP breaks Oct 2016, Dec 2018, Mar 2022, Jun 2024; segments 53/42/9/61/36; supF 125 p 0.02 | `ch2_census_break_summary.json`, `ch2_census_bai_perron.csv`, `ch2_census_segment_growth.csv` | ch2_bai_perron, ch2_segment_growth, ch2_break_comparison | fig2_02 |
  | forecasts $95-100B (Jul 2027), $115-135B (Jul 2028), bands $51-259B; backtest MAPE 14 / 19 / 13 | `ch2_census_forecast_arima.csv`, `ch2_census_forecast_ets.csv`, `ch2_census_forecast_backtest.csv` | ch2_forecast, ch2_forecast_backtest | fig2_02 |
  | QCEW 25k -> 74k -> 84k; establishments 1,327 -> 4,494; CBRE 44 -> 142 -> 125-168 MW, inventory 411 -> 509; Epoch US 15.2 GW, 0 CA | `ch2_qcew_518210_california.csv`, `ch2_cbre_california.csv`, `ch2_epoch_timeline.csv`, `ch2_break_test_comparison.csv` | ch2_break_comparison | fig2_03 |
  | tiers 6,771 / 21,756 / 23,277 (20,677 in CA); SCE 6,201 -> 5,162 active, 709 -> 3,137 canceled; PG&E 5,090 / 12,710 | `ch2_tier_vintages.csv` | ch2_tier_vintages | fig2_04 |
  | RQ1 ratios 39.7% of record peak, 20.7x existing peak, 19-26x average load, 5.1x IEPR peak growth (3.4x at 67%), 107 TWh = 3.1x | `ch2_rq1_table.csv`, `ch2_rq1_denominators.json` | ch2_rq1 | fig2_04 (box; IEPR ratios in the table only) |

## Chapters 1 and 2: numbers that appear only in the text (second pass, 2026-09-22)

A machine check compared every quantified number in the two chapter texts with the text embedded in the figure PDFs and the
LaTeX tables. Numbers not printed on a figure are listed here with their source; three new tables (`ch1_svp`,
`ch1_gas_comparability`, `ch2_tier_vintages_detail`) and two RQ1 columns now carry most of them.
  | number in the text | where it comes from |
  |---|---|
  | EPRI 9,331,619 MWh, 3.70% (2023) | EPRI Powering Intelligence 2024, state table pp. 13 and 28 (`dc_share/EPRI_3002028905_Powering_Intelligence_2024.pdf`); `ch1_dc_load_estimates.csv` basis column |
  | SVP 669.2 MW peak, 78.3% load factor, 4.48 / 4.59 TWh, 55% / 53% / 60% shares, 64-67% utilization | `ch1_svp_fact_sheets.csv` (Table ch1_svp); SVP Assembly deck Jan 2026 slides 2 and 4; SVP data center page; SVP IRP 2025 |
  | gas comparability: 0.1 TWh/month match, +0.7 to +1.8 TWh/month after Dec 2023, +20 / +25 TWh in 2024 / 2025; 432-452 kg/MWh; CAISO gas share 48.8 / 47.8 / 47.9% | `ch1_gas_series_comparability_monthly.csv` (Table ch1_gas_comparability); `ch1_carbon_intensity_annual.csv` (implied_gas_kg_per_MWh) |
  | 2023 accounting intensity 242 g/kWh; eGRID 198 | `ch1_carbon_intensity_annual.csv` (241.9), `ch1_egrid_camx_2023.json` (198.06) |
  | 1.5 GW PG&E final engineering (Feb 2025), 80 / 200 / 400 MW SCE (Feb 2025), 8,298 / 76 / 3,314 / 1,773 / 3,137 MW SCE database, 5,828 MW summer 2025 | docket TN 261964 p.3, TN 261975 p.3, TN 268459 (`ch2_tier_vintages.csv`), CEC preliminary deck p.6 (Table ch2_tier_vintages_detail) |
  | institutional context: 20,677 / 23,277 / 2,600 MW | chapter 2, `ch2_rq1_denominators.json` |
  | Census forecast medians 95 / 98 (Jul 2027), 115 / 133 (Jul 2028), bands 51-259 | `ch2_census_forecast_ets.csv`, `ch2_census_forecast_arima.csv` (Table ch2_forecast, fig2_02 box) |
  | vintage detail: 5,808 / 963 (Dec 2024); 11,668 / 1,375 / 85 / 5,828 / 100 / 100 / 2,600 (summer 2025), 10,080 / 143 split, workshop-copy labels 1,382 and 2,492; 14,747 / 4,624 (Dec 2025 by utility); PG&E 1,700 / 3,110 / 140 / 140 and 8,200 / 3,880 / 490 / 140; Cal Advocates 650 MW | `ch2_tier_vintages.csv` (Table ch2_tier_vintages_detail), CEC preliminary deck pp. 6-7, TN 267165 pp. 7-8, memo Table 1, TN 272065 p.9, TN 272807 p.3 |
  | IEPR denominators 46,479 / 50,498 MW, 263 / 298 TWh, 12.1 TWh deliveries, 96 / 1,743 / 4,377 MW data center at peak | `ch2_rq1_denominators.json`, `ch2_ced2025_planning_totals.csv` (RQ1 note) |
  | RQ1 energy equivalent 107 TWh = 3.1x; 3.4x at 67% | `ch2_rq1_table.csv` (RQ1 table columns) |
  | Epoch 89 sites / 75 US / 15.2 GW; QCEW breaks; CBRE latest 144 MW | `ch2_epoch_timeline.csv`, `ch2_break_test_comparison.csv`, `ch2_cbre_california.csv` (fig2_03 boxes) |
  | hourly EIA-930 peak 51,104 MW | `ch1_ciso_annual_summary.csv` (fig1_01 as 51.1 GW) |
- **Manifest duplicates.** Re-fetching a source appends a new manifest row with the new access date (immutable downloads by date).
  `src/ch1_baseline.manifest()` and `scripts/verify_raw.py` resolve to the newest row; `scripts/check_coverage.py` uses a set of ids.
  Ad-hoc code must do the same (the `TypeError: argument of type 'method' is not iterable` in a check on 2026-09-22 was a throwaway
  snippet indexing a duplicated id, not the pipeline).

## Provenance appendix (2026-09-22)

`scripts/make_provenance_appendix.py` (`make provenance`) writes `report/tables/provenance_ch1..3.tex`, one row per figure: content,
processed files, raw manifest ids and the producing code; it fails if a named figure or processed file is missing. The appendix
`report/sections/07_appendix_provenance.tex` is the last chapter of the report so a reader of the PDF can trace each figure to its
data without the repository. Third pass on chapters 1-2: the only patch failure on 2026-09-22 (an assertion on the forecast sentence
in the chapter 2 text, whose wording differed by one word) was re-applied with the exact sentence; verified: the sentence now reads
"July 2027 at $95 to $98 billion and July 2028 at $115 to $133 billion, bands $51 to $259 billion", the notebook carries the same
wording and the transcription table cell, and the five new tables (`ch1_svp`, `ch1_gas_comparability`, `ch2_tier_vintages_detail`,
`_b`, `_c`) exist and compile. Residual text-only numbers are the derived ratios and source-document facts listed in the previous
section.

## Cross-chapter number check (2026-09-22, final)

Every quantified number in each chapter text was searched in the text of all report figures (PDF text layer) and all LaTeX tables.
- chapter 1: 81 numbers, 77 found; text-only: 1.8, 242, 3.70, 9331619 (EPRI's own figures 9,331,619 MWh and 3.70%; rounded values 242 = 241.9, 1.8 = 1.78, 117 = 116.6, 9.9 = 9,922 MW, 278 = 216 + 62; and the derived differences 3,100 and 8,000).
- chapter 2: 81 numbers, 79 found; text-only: 3100, 8000 (EPRI's own figures 9,331,619 MWh and 3.70%; rounded values 242 = 241.9, 1.8 = 1.78, 117 = 116.6, 9.9 = 9,922 MW, 278 = 216 + 62; and the derived differences 3,100 and 8,000).
- chapter 3: 70 numbers, 67 found; text-only: 117, 278, 9.9 (EPRI's own figures 9,331,619 MWh and 3.70%; rounded values 242 = 241.9, 1.8 = 1.78, 117 = 116.6, 9.9 = 9,922 MW, 278 = 216 + 62; and the derived differences 3,100 and 8,000).

## Chapter 4 findings (2026-09-22, `scripts/run_chapter4.py`, about a minute; `make ch4`)

**New raw sources (fetched 2026-09-22, group `ercot`, `pjm`, `ferc`):** ERCOT Monthly Operational Overview June and August 2026 (`ercot_ops_overview_2026_06/08`; the July 2026 file returned 404 at the guessed path); PJM Load Adjustment Requests Summary of Nov 24 2025 (`pjm_lar_summary_2025_11_24`), the 2026 load report tables and the adjustment breakdown workbooks (`pjm_2026_load_report_tables`, `pjm_2026_load_adjustment_breakdown`); CAISO's comments on the FERC ANOPR (`caiso_comments_ferc_rm26_4_2025_11`) and NERC's accelerated large-load plan (`nerc_rm26_4_accelerated_plan_2026_03`); FERC news pages of Apr 16 and Jun 18 2026 (`ferc_news_2026_04_16_large_load`, `ferc_news_2026_06_18_show_cause`). The FERC docket page `https://www.ferc.gov/rm26-4` returns HTTP 403 to non-browser clients (registered as optional, logged as MISS); it was read in a browser on 2026-09-22 and states the Oct 23 2025 DOE directive and the 20 MW threshold, consistent with the CAISO comments.

**Transcribed ERCOT series (`src/ch4_gap.py`, every row with its manifest id):** monthly tracked large-load MW Jan 2025 to Mar 2026 (standalone and co-located) from the Dec 2025 board deck (slide 3) and the Mar 2026 TAC report (slide 2); the two November 2025 values (225,816 and 230,799 MW) are the same month from decks three months apart and both are kept. Planning studies approved and approved to energize, May 2025 to Mar 2026 (TAC slide 4). Five status-by-in-service-year snapshots: TAC Mar 13 2026 (MW, 2022-2030), House hearing Mar 26 2026 (MW, 2025-2030), ERCOT Monthly April 2026 (GW, 2022-2033, 'Section 9.5 requirements met' mapped to studies approved), Board Jun 1 2026 and Operational overview Jun 30 2026 (GW; 'Section 9.4 only' plus 'Section 9.4/9.5 met' mapped to studies approved). Narrative points (63 GW Dec 2024; 7,500/5,300/2,200 MW Nov 18 2025; 8,786 MW and 3,977 MW Jan 2026; 9,042 and 3,883 MW Mar 2026; 8,926 and 3,966 MW Jun 2026; 9,456 and 4,316 MW Aug 2026; 410.6 GW Mar 26 2026; 445.8 GW Apr 2026; 438 GW May 2026; 465.5 GW Jun 2026). The charts were read from the extracted page images; GW-denominated tables were multiplied by 1,000.

**ERCOT hazards (`ch4_ercot_transition_rates.csv`):** studies approved to approval to energize 1.56%/month (flow 2,168 MW over 10 months, pool 13,860 MW); under review to studies approved 0.75% (gross inflow 5,878 MW; pool = mean of the Nov 18 2025 residual 76,139 MW and the Mar 13 2026 stock 79,825 MW); no studies to review 2.12% (queue growth minus the change in the no-studies stock over 3.8 months; cancellations exit the same stock, so an upper bound); approval to observed energization 3.05% (2025 addition 923 MW to the observed-energized stock over a 2,524 MW not-operational pool). Chain over 60 months: 36.7% (studies approved), 5.9% (under review), 1.6% (no studies), 84.4% (approved to energize); scaled hazards and a 0.5%/month cancellation hazard in `ch4_ercot_chain.csv`. These rates were measured while the queue quadrupled and describe study throughput as much as viability.

**CED 2025 non-data-center growth (`ch4_iepr_growth_summary.csv`):** low = Planning (TN 268727), mid = Baseline (TN 268722; its CAISO coincident peak equals the Planning BASELINE_NET_LOAD, asserted in the script), high = Local Reliability (TN 268725), plus Local Reliability with known loads (TN 268726, whose extra 3,980 MW sits in OTHER_ADJUSTMENTS, not DATA_CENTER). Data center energy: Planning deliveries from TN 268824 (729 GWh 2025, 12,078 GWh 2030); other scenarios scaled by the CAISO DATA_CENTER peak ratio (LR 2030: 30,330 GWh). The CAISO DATA_CENTER column includes VEA's Nevada requests (160 MW Planning, 242 MW LR in 2030); California-only CEC values are 1,583 and 4,135 MW. Statewide non-DC growth 2025-2030: 23.6/40.5/45.3 TWh and 3,625/4,988/5,792 MW.

**Tiers:** California-only 5,086 / 6,987 / 8,604 = 20,677 MW from the published statewide tier totals minus VEA (the memo's utility rows sum to 8,605 MW of inquiries, 1 MW of rounding; `ch4_ca_tiers.csv` carries both).

**CEC literal replication does not reproduce the published component:** confidence x 0.67 x linear 7-year ramp (agreements from 2026: 5/7; groups 2-3 from 2028: 3/7) gives 2,366 MW (Planning) and 3,684 MW (LR) against the published 1,583 and 4,135 MW; the CEC uses utility-supplied schedules where available and exempts SVP from confidence levels (memo p. 9). The published values are the central and high cases; the replication is a check row.

**Monte Carlo (`ch4_mc_draws.parquet`, 10,000 draws, seed 20260922):** definitions and input ranges in `ch4_mc_inputs.csv`; the supply base is the 2025 fleet at 2023-2025 capacity factors (216.1 TWh in-state, against 205.1 TWh actual 2025 generation) plus 2024 CEC imports (62.2 TWh), ELCC 68,307 MW; gaps are increments 2025-2030 so the boundaries cancel. Results: energy gap P5/P50/P95 19/50/78 TWh; net-peak gap 4,160/7,169/10,068 MW; DC peak 1,387/2,292/3,556 MW; both gaps positive in every draw. Upper bound (every MW, flat, central supply): 202-242 TWh, 25.5-30.2 GW. Gas capacity factor needed to close the P50 energy gap 0.40 (P95 0.49) from 0.24. Diablo Canyon is a Bernoulli(0.5) switch (SB 846 extension to Oct 2030; federal licence renewal); conditional medians 59/42 TWh and 8.4/6.2 GW. Planning reserve margin uniform 0.15-0.17 is an assumption (CPUC RA range) with no raw file behind it.

**Sobol (`ch4_sobol.csv`):** SALib `sobol.sample` N=1024, 13 inputs, no second order (15,360 evaluations); categorical inputs mapped from uniforms (IEPR case three equal bins, Diablo Canyon split at 0.5); per-unit completion represented by the realization fraction quantile. Sum of S1 = 1.01 (energy) and 0.99 (peak).

**Headroom (`ch4_headroom_*.csv`):** CAISO hourly demand 2019-2025 (371 missing hours interpolated; the single 2026 hour-ending row is dropped by the >=8,000-hours filter); thresholds winter 31,226 MW (Nov-Feb) and 51,104 MW (other months); headroom 3,112/3,798/4,641/8,031 MW at 0.25/0.5/1/5% versus Duke's CAISO 4,200/5,000/5,900 MW (Figure 1 p. 8 and Figure 8 p. 23 of the mirror PDF; Duke's 5% value is not printed per BA). Variants: Dec-Feb winter 3,244/4,023/4,977/9,001; 2022-2025 only 2,684/3,322/4,093/7,187; single threshold 11,593/13,578/16,033/24,334. At 0.5%: 197 hours/year curtailed, 98% in Nov-Feb, 18 hours/year with less than half of the load available; the largest single-hour cut over the seven years equals the whole 3.8 GW (yearly maxima average 2,912 MW, the table value).

**Regimes:** SCE database TN 268459 (Jan 29 2026), groups 1-3: 73 projects, 5,162 MW; 76% of MW in projects >=75 MW, 95% >=20 MW. PJM Table B-9 RTO 2030: 33,707 MW above embedded; B-9b 38,805 MW; the LAS chart readings (request ~60 GW, firm ~35 GW, non-firm ~5 GW in 2030) are approximate values read from a vector chart and are labelled as such in `ch4_pjm_lar_chart_readings.csv`.

**Emissions:** CAISO accounting intensity, valid hours; flat 183 t/GWh 2025 (239 in 2023); curtail 25% of hours 146; shift 25% 121 (bottom-quarter mean 44 g/kWh).

**Provenance of chapter 4 numbers:** every quantified number in `report/sections/05_putting_it_together.tex` (108 distinct values) was found in a chapter 4 figure text layer or a chapter 4 table by the machine check run on 2026-09-22 (script inline in the session log; rounding tolerance 0.6% with unit scaling).

## Chapter 4 audit (2026-09-22): requirement-by-requirement check, missing data resolved, and where each number lives

**Pasted errors from the build session.** Three of the five pasted outputs ("(eval):N: === not found" after a CED annual-peaks dump, an ERCOT link listing and a notebook-builder listing) are not pipeline errors: they come from `echo ====` separators in exploratory shell commands, which zsh parses as `=command` expansion. The data in those outputs (the CED annual peaks for three scenarios and five TAC areas, the ERCOT Large Load Integration page links, the chapter 3 notebook builder) were read in full and are used by the pipeline. The fourth, `TypeError` in `make_ch4_tables.py`, was a real bug (`r.mean` on a pandas row) fixed the same day; all 26 chapter 4 tables now generate. The fifth was the bundle README listing, again an echo artefact.

**Item 1, demand scenarios.** Upper bound, CEC central, ERCOT-calibrated and PJM-style cases, each added to the IEPR low/mid/high non-data-center growth (`ch4_demand_totals_2030.csv`, PDF Table 5.6). The CEC case is now rebuilt from its published parameters: confidence x 67% with SVP exempt from the confidence levels (memo p. 9) reproduces the memo's 2040 endpoints (4,855 and 7,381 MW) to within 1 MW (`ch4_cec_replication.csv`); the CEC ramp is read from the peak workbook as the share of the 2040 CAISO component reached each year (`ch4_cec_ramp_profile.csv`: 36% Planning, 60% Local Reliability in 2030); replicated 2030 California-only values 1,549 / 3,896 MW against the published 1,583 / 4,135 MW. The earlier "literal replication" rows (2,366 / 3,684 MW, which ignored the SVP exemption and assumed ramp start years) are superseded.

**Item 2, Monte Carlo.** Unchanged results (the CEC replication does not enter the draws; the ramp input's basis now cites the CEC's 36/60%). Upper-bound rows appear in PDF Tables 5.3 (cases), 5.6 (totals), 5.10 (MC summary), 5.11 (tornado) and 5.17 (headroom vs gap). Diablo Canyon: the NRC issued the renewed licences on April 2 2026 (`nrc_diablo_canyon_rod_2026`, `gov_ca_diablo_license_2026_04_02`); SB 846 authorises operation only through 2030, so the Bernoulli(0.5) switch stands and its basis is now documented.

**Item 3, sensitivity.** Tornado and Sobol unchanged; the tornado table carries the upper-bound row.

**Item 4, headroom.** Added the per-year solution for 2019-2025 under the phase plan's hours criterion (hours above the historical peak threshold under 0.25/0.5/1/5% of the year; closed form from sorted margins) and Duke's energy criterion, for the Duke seasonal thresholds and for a single historical peak (`ch4_headroom_by_year.csv`, PDF Tables 5.15 and 5.16, new top-right panel of PDF Figure 5.4). At 0.5%: energy criterion 3.3-4.2 GW by year (pooled 3.8), hours criterion 2.0-2.9 GW; single peak 11.4-16.2 and 7.0-11.7 GW. The midday share of negative-price hours (10-16 h) from chapter 1 is now a column of `ch4_energy_side.csv` (77-94%).

**Item 5, crosswalk.** Added a 0-3 score per criterion under a stated rubric (`ch4_regime_scores.csv`, `ch4_regime_rubric.csv`, PDF Table 5.20, PDF Figure 5.5): ERCOT 13, CEC 10, PJM 8, SB 6 7, FERC 7, EIA pilot 4 of 18. ERCOT series extended with the April and July 2026 operational overviews (`ercot_ops_overview_2026_04/07`; the April chart is the one reused in the June 1 board deck, so that snapshot is dated April 30 2026; the ERCOT Monthly April 2026 snapshot is dated by its May 13 2026 posting): July 2026 queue 467.4 GW by 2033; approved to energize 9,012 MW (Apr) and 9,456 MW (Jul, Aug); observed monthly peaks 4,006 (Apr), 4,370 (Jul), 4,316 MW (Aug). The May 2026 overview was not found at the guessed paths.

**Item 6, emissions.** Unchanged.

**Provenance check after the audit:** every quantified number in `report/sections/05_putting_it_together.tex` is in a chapter 4 figure text layer or table (machine check re-run 2026-09-22 after the audit; see the session log for the count).

## Phase 5 (2026-09-22): writing, freeze, tag, export, defense

**Writing.** `report/sections/00_abstract.tex`, `01_introduction.tex` (question, RQs restated for the California-only scope, contribution, related work, structure) and `06_discussion.tex` (contribution restated as an independent replication and audit of the CEC method; what the audit found about each assumption; what the gap is and is not; policy implications for the CEC, CPUC/CAISO, resource planning, the Legislature and EIA; limitations; future work; conclusion) were written; the title page carries the author, program and the freeze date. Every number in these sections was checked against the figure text layers and the tables of chapters 1-4 (machine check, 2026-09-22).

**Every figure carries its source line.** `src/provenance.py` holds the figure-to-files-to-manifest-ids-to-code map (moved from the appendix script) and `stamp()`, which writes the line under each figure at save time in all four chapter scripts (chapter 1's save now also crops with `bbox_inches="tight"`). The same line is printed under each figure in the report (`report/tables/figsrc_<fig>.tex`, generated by `make provenance`) and the appendix repeats the map as tables. The stamp is deterministic (it carries the freeze date, not a build time), so the bundle comparison stays byte-for-byte.

**Freeze.** `make freeze` (= `scripts/freeze_data.py --date 2026-09-22`) wrote `data/raw/manifest_frozen_2026-09-22.csv` (643 rows, 640 source ids, all referenced files present) and `docs/DATA_FREEZE.md` with the rule that nothing fetched after the date enters the report; the frozen manifest is tracked in git. The repository tag `data-freeze-2026-09-22` is to be created on the commit that carries this freeze.

**Export.** `make release` (= `scripts/export_release.py --date 2026-09-22`) writes `release/consumption_gap_2026-09-22/` (report PDF, defense deck, every `ch*_*` CSV and JSON plus the Monte Carlo draws parquet and the transcription CSVs, all figures, all LaTeX tables, the five executed notebooks, the frozen manifest, the docs and the report source) with `CONTENTS.md` listing every file and its SHA-256, and a zip of the folder. `release/` is ignored by git; the zip is the submission artefact.

**Defense.** `report/defense/defense.tex` (beamer, 21 slides, `make defense`): question, RQs and method, one slide per chapter result with the figures, contribution, policy, limits, conclusion and a reproducibility backup slide. The deck quotes only numbers that appear in the report's figures and tables.

## Phase 5 audit (2026-09-22): what was checked and what changed

- **Chapter 5 (PDF chapter 6) restates the contribution as a replication and audit with transparent, tested assumptions.** The phrase is now backed by an assumption register (`scripts/make_assumption_register.py` -> `data/processed/ch5_assumption_register.csv`, `report/tables/ch5_assumption_register.tex`, PDF Table 6.1): 18 assumptions, each with its value or range, the source it rests on, the test applied and the result, generated from the chapter outputs (tornado swings, Sobol indices, the CEC replication, the ERCOT chain variants, the headroom variants, the emissions variants). Two assumptions that the Monte Carlo does not draw are tested deterministically in the register: the ELCC values (battery ELCC 0.60 or 0.90 instead of 0.765 moves the peak gap by about +1.2 or -0.9 GW through the weighted new batteries; a 0.90 gas derate on new gas by +0.003 GW) and the flat, coincident data center load (the CEC's 85 percent coincidence would cut the median data center peak contribution by about 340 MW). The end-2030 annualization of data center energy is quantified (calendar-2030 energy about 14 percent lower under the CEC ramp profile).
- **Every figure carries its source file and manifest row.** Audit found one figure (fig1_04) saved outside the shared helper and therefore unstamped; fixed and chapter 1 regenerated. All 24 figure PDFs now carry the line (checked by text extraction with whitespace normalized), all 24 report figures print it, and the 16 deck figures are the same stamped images. The free-text raw-source labels in the provenance map (dated series such as `eia923_2010 .. 2025`, directory-level ids such as the CAISO Today's Outlook series) now resolve to manifest ids through `src.provenance.RAW_LABEL_IDS`; `make provenance` fails if any label does not resolve, writes `data/processed/ch5_manifest_rows_used.csv` (238 ids) and prints the rows (owner, access date, SHA-256, URL) as Appendix B of the report, so the manifest row itself is in the document.
- **Freeze:** `docs/DATA_FREEZE.md` and `data/raw/manifest_frozen_2026-09-22.csv` (643 rows, 640 ids, no missing files) unchanged; the freeze date appears on the title page, in the abstract and on every figure.
- **Tag:** `data-freeze-2026-09-22` exists on the commit that carries the freeze (created by the author). The audit changes go in a later commit; a second tag `report-2026-09-22` on that commit marks the exported report.
- **Export:** re-run after the audit so the zip carries the final PDF, the register CSV and the manifest-rows CSV; `CONTENTS.md` lists every file with its SHA-256.
- **Defense deck:** 16 stamped figures; all 85 quoted numbers trace to report figures or tables (machine check).
- **Bundle finding (2026-09-22, Phase 5 audit):** the resolver check run inside the Desktop bundle found seven ids that its figures name but its filtered manifest lacked (the three CAISO Today's Outlook series ids, the two OASIS price ids, the EPRI 2024 paper and the CAISO August 2026 key statistics PDF); the directories were already present, the two PDFs were copied, the seven manifest rows were added (bundle manifest 281 rows, 278 ids) and the bundle was refrozen. The bundle's provenance appendix, assumption register and manifest-rows CSV are now identical to the repository's.
