# Project plan: phases 0 to 5 (roadmap of 2026-09-21)

This is the roadmap that the chapters were built against, saved here verbatim from the working session of September 21, 2026
(it was previously only in the chat history). Status on 2026-09-22: Phase 0 (data sources), Phase 1 (chapter 1, current status),
Phase 2 (chapter 2, data center growth), Phase 3 (chapter 3, energy production growth) and Phase 4 (chapter 4, putting it together)
are built and audited; see `docs/DATA_NOTES.md` for the audit records and `README.md` for the `make ch1` to `make ch4` pipelines.
Still open: the abstract, introduction and discussion sections of the report and the defense material.

---

Here is a start-to-finish roadmap, rebuilt around California only and organized so that the final report's four chapters map directly onto the four research questions plus the new questions you listed.

Two scope notes before the plan. Dropping Finland removes the Fingrid and EK replication and the Irish comparison, so RQ3 needs rewording to "CEC tiers, ERCOT queue, PJM vetting, and federal instruments." Keep Texas as data rather than narrative, because ERCOT publishes the only monthly, phase-level series large enough to estimate how pipelines actually shrink, and you need that to weight California's tiers with something other than the CEC's own confidence levels.

## Data sources to lock in during week one

| Need | Dataset | Owner | Granularity | Access |
|---|---|---|---|---|
| Hourly demand, generation by fuel, imports | EIA-930 Hourly Grid Monitor, CISO balancing authority and CAL region | EIA | Hourly, mid-2018 onward | CSV download, EIA API v2, or the `gridstatus` Python library |
| Annual retail sales by sector and utility | EIA-861 | EIA | Annual | Bulk CSV |
| Generation by plant and fuel | EIA-923 | EIA | Monthly | Bulk CSV |
| Existing and planned generators with status codes | EIA-860 annual and EIA-860M monthly, including archived monthly vintages back to 2015 | EIA | Unit level | Bulk XLSX per vintage |
| State generation, consumption, imports | CEC Energy Almanac and ECDMS | CEC | Annual, county and sector | Web CSV |
| Official demand forecast and data center forecast | 2025 IEPR demand forecast, Preliminary Data Center Forecast, docket 25-IEPR-03 | CEC | Forms and results | Docket downloads |
| Energization tiers | CEC deck from the Jan 28, 2026 Assembly hearing, plus later IEPR docket updates | CEC | Statewide aggregate by tier | PDF, transcribe with page citation |
| Prices, load, renewables, curtailment, CO2 | CAISO OASIS, Today's Outlook downloads, monthly curtailment and emissions reports | CAISO | Hourly and 5-minute | OASIS API or `gridstatus` |
| Resource adequacy, ELCC values, reserve margin | CPUC RA reports and IRP decisions | CPUC | Annual | PDFs |
| Construction spending, data center category | Census C30 Value of Construction Put in Place, private, seasonally adjusted annual rate | Census | Monthly, national, 2014 onward | XLSX from census.gov/construction/c30 |
| California data center industry growth | BLS QCEW, NAICS 518210, California and counties | BLS | Quarterly | CSV or API |
| Facility inventory with power and status | Epoch AI Frontier Data Centers Hub; Kollar and Grady 2025 dataset | Epoch, journal supplement | Facility | CSV |
| MW built and under construction by market | CBRE, Cushman and Wakefield, JLL semiannual market reports for Silicon Valley, Los Angeles, Sacramento | Industry | Semiannual | PDFs, digitize into a series |
| Existing data center share estimates | LBNL 2024 report; EPRI 2024 Powering Intelligence state table | LBNL, EPRI | National and state | PDFs |
| Municipal cluster disclosure | Silicon Valley Power annual reports and IRP | City of Santa Clara | Annual | PDFs |
| Texas queue by phase | ERCOT large load interconnection status reports | ERCOT | Monthly by phase | PDF and XLSX |
| PJM firm and non-firm adjustment | PJM 2026 Load Forecast Report | PJM | Zone | PDF |
| Emission factors | EPA eGRID 2023, CAMX subregion | EPA | Annual | XLSX |

The Census series is exactly what the chart you attached uses. It is national only, so for California you build proxies from QCEW, the Epoch facility timeline, CEC tier vintages, and the digitized market reports. Say plainly in the report that no state-level construction spending series exists.

## Step-by-step roadmap

**Phase 0, setup, days 1 to 4.** Create one git repository with `data/raw/<source>/<date>/` for immutable downloads, a `manifest.csv` recording URL, access date and SHA-256 for every file, `notebooks/` numbered by chapter, `src/` for shared functions, `figures/`, and `report/` in LaTeX. Pin a Python environment with pandas, statsmodels, lifelines, SALib, scipy, matplotlib and `gridstatus`. Write the snapshot script on day one and run it monthly from now on. It should pull the ERCOT status report, the CEC docket listing, the PJM forecast page, the Epoch CSV, and the EIA-860M file. Every month you wait costs one data point.

**Phase 1, current status of data centers and the grid, chapter 1.** This answers "how much of the state's power do data centers use" and builds the baseline from Section 3.2 of the proposal.

1. Pull EIA-930 hourly CAISO demand, generation by fuel, and net interchange for 2019 through 2025. Build the load duration curve, the net-load duration curve after solar and wind, and average daily profiles by season. Identify the top 100 net-peak hours per year and their timing.
2. Build the day-ahead price duration curve from CAISO default load aggregation point prices, and count negative-price hours per year. That is a California-specific fact that matters later for flexibility.
3. Compute hourly carbon intensity from CAISO's emissions reports and eGRID CAMX for the annual factor.
4. Estimate existing data center load four ways and present the range as a single figure against California retail sales from EIA-861: the EPRI state share, the CEC preliminary forecast's existing-load baseline, a bottom-up sum of Epoch and Kollar-Grady California facilities times a utilization range, and the Silicon Valley Power disclosure as an anchored local cluster. Do not pick one. The spread is the finding.
5. Document the institutional context: the January 2026 decision to hold the tiers out of the adopted forecast, PG&E's and SCE's public large-load pipeline statements, and any CPUC large-load tariff proceeding. Verify the last item, since I cannot confirm its docket.

**Phase 2, data center growth in California, chapter 2.** This answers RQ1 and reproduces the attached chart with rigor.

1. Reproduce the Census chart from the raw C30 file, annotated at the ChatGPT launch in November 2022. Add a second panel of month-over-month growth.
2. Fit a structural break model on the log series: a Chow test at the known date, then Bai-Perron to let the data locate breaks. Report pre-break and post-break compound growth rates with confidence intervals, and an ETS or ARIMA forecast with prediction bands.
3. Build the California proxies: QCEW establishment and employment counts for NAICS 518210 by quarter, MW under construction by California market digitized from consecutive CBRE and Cushman reports, and a cumulative capacity timeline from Epoch's California facilities. Fit the same break test to each and compare break dates.
4. Assemble every vintage of the CEC tiers you can find, starting with the October 2025 forecast deck and the December 2025 hearing numbers, then IEPR updates as they appear. Plot tiers as stacked bars against CAISO record peak and against the existing data center load range from chapter 1. Sum the tiers and state both ratios explicitly.
5. Write RQ1's answer as a table: MW by stage, share of CAISO peak, share of existing data center load, and share of the IEPR mid-case load growth to 2030.

**Phase 3, energy production growth in California, chapter 3.** This is the supply side of RQ2, which the proposal left thin.

1. From EIA-923 and the CEC Almanac, build generation by resource for 2010 through 2025 as a stacked area, in-state versus imports, and capacity by technology from EIA-860. Add battery storage capacity and CAISO curtailment volumes by year. These were missing from the proposal and are the defining features of the California grid.
2. Build the retirement schedule from EIA-860 planned retirement dates, including Diablo Canyon and once-through-cooling gas units.
3. Fit a supply-side realization model from EIA-860M vintages. For every California planned unit in the January file of each year from 2016 to 2022, record its outcome by 2025: operating, cancelled, or still planned. Fit a logistic model of completion on technology, size and planned year, and a Kaplan-Meier delay curve from planned to actual commercial date. This gives you an empirical, California-specific attrition rate to apply to the current planned list, symmetric with the demand-side weighting.
4. Produce probability-weighted planned capacity and energy for 2030 by technology, with ELCC-derated peak contribution using CPUC values. Report three cases: everything builds, model-weighted, and model-weighted minus retirements.

**Phase 4, putting it together, chapter 4.** This answers RQ2, RQ4 and RQ3.

1. Demand scenarios for 2030: the proposal's upper bound where every MW builds and runs flat; the CEC central case using its published confidence levels, utilization and ramp; an ERCOT-calibrated case using phase-transition rates estimated from the monthly ERCOT snapshots as a stock-flow model; and a PJM-style case that only counts signed agreements as firm. Add IEPR low, mid and high non-data-center growth to each.
2. Monte Carlo gap model with ten thousand draws over per-tier realization probability, utilization, ramp timing, generation completion from the Phase 3 model, and the IEPR growth case. Output the distribution of the 2030 gap in TWh and in net-peak MW. Report the upper bound in every table, as the proposal promises.
3. Sensitivity: a one-at-a-time tornado chart plus Sobol indices with SALib so you can say which assumption drives the answer.
4. RQ4 headroom: replicate the Duke method on CAISO hourly load. For each year 2019 to 2025, find the largest flat load addition such that hours above the historical peak stay under 0.25, 0.5 and 1 percent of the year. Compare your numbers to Duke's CAISO range, then express them as a fraction of the capacity gap from step 2. Add the midday negative-price hours from chapter 1 as the energy-side argument for flexible siting.
5. RQ3 crosswalk: a matrix scoring CEC tiers, ERCOT phases, PJM firm and non-firm, the EIA pilot survey, Texas SB 6, and FERC RM26-4 on granularity, stage taxonomy, verification, timeliness, coverage and public access. Plot the ERCOT queue time series as the evidence for speculative inflation. Map each regime's stages onto one common taxonomy and show what California's headline number would be under each regime's counting rule.
6. Optional if time allows: emissions of a flat load versus a curtailable load using CAISO hourly carbon intensity. It is California-specific and replaces the generic UNECE section.

**Phase 5, writing and defense.** Chapter 5 is discussion and policy, restating the contribution as an independent replication and audit of the CEC method with transparent, tested assumptions. Every figure carries its source file and manifest row. Freeze the data on a stated date, tag the repository, and export the processed CSVs with the report.

## Timeline and deliverables

Week one starts today. This assumes a full draft in early December and a defense in the winter. Adjust if your filing deadline differs.

| Weeks | Dates | Milestone |
|---|---|---|
| 1 | Sep 21 to 27 | Repository, manifest, snapshot script running, all raw data downloaded |
| 2 to 3 | Sep 28 to Oct 11 | Chapter 1 complete: baseline curves, existing-load range figure |
| 4 to 5 | Oct 12 to 25 | Chapter 2 complete: Census chart, break tests, California proxies, tier table |
| 6 to 7 | Oct 26 to Nov 8 | Chapter 3 complete: production history, 860M realization model, weighted supply |
| 8 to 9 | Nov 9 to 22 | Chapter 4 core: scenarios, Monte Carlo, sensitivity, headroom replication |
| 10 | Nov 23 to 29 | Crosswalk matrix and RQ3 text |
| 11 | Nov 30 to Dec 6 | Full draft with all figures to advisor |
| 12 | Dec 7 to 13 | Buffer, revisions, defense slides |

Final deliverables stay as proposed: the report, the tagged repository with raw data manifest, processed CSVs and notebooks, and the defense presentation. The only added deliverable is the snapshot dataset with its collection protocol, framed as a seed series since it will hold only three or four months by the draft.

I can turn this into a living project doc with checkboxes if you want to track progress against it.
