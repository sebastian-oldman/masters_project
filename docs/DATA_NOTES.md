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

