# Mapping the Consumption Gap: Planned Data Center Capacity versus Electricity Supply in California

M.S. capstone project. Repository layout, data provenance rules, and how to reproduce every
download are described here. Analysis lives in `notebooks/` (numbered by report chapter) and
shared code in `src/`.

## Layout

```
data/raw/<group>/<access-date>/   immutable downloads; never edited, never committed (see .gitignore)
data/raw/manifest.csv             one row per raw file: url, access date, sha256, bytes, content type
data/processed/                   derived tables written by notebooks (rebuildable), plus three tracked hand-made
                                  tables: CEC tier transcription, CEC forecast parameters, CBRE California market series
data/snapshots/<date>/            monthly registry snapshots (ERCOT, CEC docket, PJM, Epoch, EIA-860M, Census)
docs/DATA_CATALOG.md              rendered view of the manifest (make catalog)
logs/                             fetch logs and logs/fetch_failures.csv
notebooks/                        00 inventory, 01 baseline grid, 02 data center growth, 03 supply growth,
                                  04 gap model, 05 regimes and flexibility
report/                           LaTeX source (tectonic) for the final report
scripts/                          fetch_all.py (registry downloads), fetch_caiso.py (Today's Outlook 5-minute history),
                                  fetch_caiso_oasis.py (OASIS day-ahead LMPs, monthly), fetch_caiso_library.py (curtailment
                                  and renewables report archives), fetch_infogram.py (CBRE chart data), record_manual.py
                                  (register hand-obtained files), assemble_cbre_series.py (tidy CBRE market series), snapshot.py (monthly),
                                  verify_raw.py (opens key files), check_coverage.py (expected-vs-actual completeness), build_catalog.py
src/                              sources.py (registry), fetch.py (downloader), paths.py
```

## Environment

Python 3.12 virtual environment in `.venv` (Homebrew python@3.12). Exact pins are in
`requirements.lock.txt`; top-level dependencies in `requirements.txt`.

```bash
make env          # create .venv and install pinned packages
make fetch        # all regular-size raw sources (about 2 minutes)
make fetch-large  # EIA-930 interchange files and the Kollar-Grady Zenodo bundle (about 2.5 GB)
make caiso        # CAISO Today's Outlook 5-minute history, OASIS day-ahead LMPs, curtailment and renewables report archives
make snapshot     # monthly registry snapshot; run on the 1st of each month
make catalog      # regenerate docs/DATA_CATALOG.md
make lab          # JupyterLab
```

The snapshot is scheduled through a user-level LaunchAgent installed on 2026-09-21
(`~/Library/LaunchAgents/com.katze.capstone.snapshot.plist`, 09:00 on the 1st of each month, log in
`logs/snapshot_launchd.log`). To remove it: `launchctl bootout gui/$(id -u)/com.katze.capstone.snapshot`.
`scripts/install_snapshot_cron.sh` is the cron alternative.

## Chapter pipelines

| Chapter | Run | Outputs |
|---|---|---|
| 1 Current status (baseline grid, prices, carbon, existing data center load, institutions) | `make ch1` (= `scripts/run_chapter1.py`, `scripts/make_ch1_tables.py`, `scripts/build_notebook_ch1.py --execute`) | `data/processed/ch1_*`, `figures/fig1_*`, `report/tables/ch1_*.tex`, `notebooks/01_baseline_grid.ipynb`, `report/sections/02_current_status.tex` |
| 2 Data center growth (Census chart, Chow and Bai-Perron breaks, ARIMA/ETS forecasts, California proxies, tier vintages, RQ1 table) | `make ch2` (= `scripts/run_chapter2.py`, `scripts/make_ch2_tables.py`, `scripts/build_notebook_ch2.py --execute`) | `data/processed/ch2_*`, `figures/fig2_*`, `report/tables/ch2_*.tex`, `notebooks/02_data_center_growth.ipynb`, `report/sections/03_data_center_growth.tex` |

## Provenance rules

1. Every raw file is downloaded by `src/fetch.py` from the URL recorded in `src/sources.py`,
   stored under its access date, and hashed (SHA-256) into `data/raw/manifest.csv`.
   Nothing in `data/raw` is ever edited by hand.
2. Sources tagged `mirror` are official documents fetched from a third party because the
   publisher blocks scripted downloads (Duke via the Illinois Commerce Commission docket;
   the LBNL 2025 update via RTO Insider). Verify against the publisher's copy before citing.
3. Sources tagged `manual` are gated and must be downloaded by hand into
   `data/raw/<group>/<date>/` and appended to the manifest with `scripts/fetch_all.py --id <id>`
   once a working URL is known, or recorded by hand with their SHA-256.
4. Series that are revised or re-issued (`vintage` tag: Census C30, EIA-860M, Epoch, ERCOT
   Monthly, CEC docket) are kept as dated vintages and re-captured by the monthly snapshot.
5. Notebooks read only from `data/raw` and write only to `data/processed` and `figures/`.
   Every table and figure in the report cites the manifest `source_id` it was built from.

## Data sources (week-one lock-in)

| Need | Group | What was captured |
|---|---|---|
| Hourly demand, generation by fuel, interchange | `eia930` | EIA-930 six-month BALANCE (2015H2-2026H1), SUBREGION (2018H2-2026H1) and INTERCHANGE files, plus the reference tables (the CAL region is the sum of its member balancing authorities; it is not a row in the files) |
| Retail sales by utility and sector | `eia861` | EIA-861 zip archives 2010-2024 |
| Generation by plant and fuel | `eia923` | EIA-923 zip archives 2010-2025 |
| Existing and planned generators | `eia860`, `eia860m` | EIA-860 2010-2025; EIA-860M every monthly vintage July 2015 to July 2026 |
| State consumption by county and utility | `cec_almanac` | CEC ECDMS exports (annual and monthly), total-system-generation pages 2015-2024, capacity, storage survey |
| Demand forecast and data center forecast | `cec_iepr_docket`, `cec_tiers` | Adopted CED 2025-2045 report and resolution; 25-IEPR-03 docket: preliminary data center forecast deck, methodology memo, Form 1.1c data center allocations, SCE public data center database (two vintages), PG&E confidentiality requests, single forecast set agreement, CED 2025 hourly and peak forecasts; Assembly hearing deck with energization tiers |
| Prices, load, renewables, CO2, curtailment | `caiso`, `caiso_outlook`, `caiso_oasis`, `caiso_library`, `eia_wholesale` | Today's Outlook 5-minute history (CO2, fuel mix, demand, net demand, renewables) from 2018-04-10; OASIS day-ahead hourly LMPs at DLAP and hub nodes from July 2023 (OASIS retention limit) plus EIA daily ICE hub prices 2015-2026; monthly curtailment totals CSV since 2014; 3,261 daily curtailment PDFs (2016 to May 2025); 479 daily renewable reports (June 2025 onward, HTML with embedded data); 106 monthly renewables performance reports; production-and-curtailment workbooks 2024-2025; NQC lists 2025-2026; 2026 summer assessment |
| Resource adequacy | `cpuc` | RA reports 2015-2023; 2025 and 2026 Slice-of-Day filing guides; D.25-06-048 (18 percent PRM for 2026-2027); D.24-02-047 (Preferred System Plan); LOLE 2026 study appendices; E3/Astrape incremental ELCC study and transmittal memo (via Wayback); RA OIR and 2026 proposed decision |
| Construction spending | `census_c30` | C30 private and total time series incl. the Data center line (2014 onward), latest release |
| California data center industry growth | `bls_qcew` | QCEW NAICS 518210 industry slices 2015Q1-2026Q1, annual averages, California area slice |
| Facility inventories | `facilities` | Epoch AI Frontier Data Centers Hub CSVs and bundle; Kollar and Grady 2025 Zenodo repository |
| Data center share estimates | `dc_share` | LBNL 2024 report, LBNL 2025 update (mirror), EPRI 2024 and 2026 |
| Municipal cluster | `svp` | Silicon Valley Power 2023 IRP, CEC review, SVP presentations (2025, Aug 2026), utility fact sheets 2017-2023 and FY2025 financial statement (via Wayback; SVP site blocks scripts), data center page |
| Texas queue | `ercot` | ERCOT Monthly Feb 2025-Apr 2026, TAC status update, board and legislative decks, SB 6 |
| PJM vetting | `pjm` | 2025 and 2026 Load Forecast Reports |
| Emission factors | `egrid` | eGRID2023 rev1 |
| Context | `context` | NERC LTRA 2025 and large-load gap assessment, Duke (mirror), LBNL Queued Up 2025, Grid Strategies 2025, JLARC 598 |
| Market reports | `market_reports` | CBRE North America Data Center Trends: overview chart data for seven editions (H1 2023 to H1 2026; primary and secondary market tables with inventory, available MW, vacancy, absorption, under construction) and the Silicon Valley chapters for H2 2025 and H1 2026 (semiannual history H1 2016 to H1 2026), all pulled from CBRE's Infogram embeds and assembled in `data/processed/cbre_california_market_series.csv` (Silicon Valley and Southern California; CBRE does not track Sacramento); JLL Midyear 2025 report (mirror; Northern and Southern California inventory); Cushman and JLL pages; CBRE press release |

Known gaps after the first run are listed at the bottom of `docs/DATA_CATALOG.md`.
