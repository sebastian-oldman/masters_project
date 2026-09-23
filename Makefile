PY=.venv/bin/python
TODAY=$(shell date +%F)

.PHONY: env fetch fetch-large caiso snapshot catalog lab report clean-parts ch1 ch2 ch3 ch4 provenance freeze release defense overleaf brief

env:                       ## create the virtual environment (Python 3.12) and install pins
	/opt/homebrew/bin/python3.12 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.lock.txt
	.venv/bin/python -m ipykernel install --user --name capstone --display-name "capstone (.venv)"

fetch:                     ## download all regular-size raw sources for today's access date
	$(PY) scripts/fetch_all.py --exclude-tag large --workers 6 2>&1 | tee logs/fetch_all_$(TODAY).log

fetch-large:               ## EIA-930 interchange files and the Zenodo bundle
	$(PY) scripts/fetch_all.py --only-tag large --workers 2 2>&1 | tee logs/fetch_large_$(TODAY).log

caiso:                     ## CAISO Today's Outlook history + OASIS day-ahead LMPs
	$(PY) scripts/fetch_caiso.py --stage outlook 2>&1 | tee logs/fetch_caiso_outlook_$(TODAY).log
	$(PY) scripts/fetch_caiso.py --stage lmp 2>&1 | tee logs/fetch_caiso_lmp_$(TODAY).log

snapshot:                  ## monthly registry snapshot (run on the 1st of each month)
	$(PY) scripts/snapshot.py 2>&1 | tee logs/snapshot_$(TODAY).log

catalog:                   ## regenerate docs/DATA_CATALOG.md from the manifest
	$(PY) scripts/build_catalog.py

lab:                       ## start JupyterLab
	.venv/bin/jupyter lab

ch1:                       ## chapter 1 tables, figures, notebook and LaTeX tables
	$(PY) scripts/run_chapter1.py && $(PY) scripts/make_ch1_tables.py && $(PY) scripts/build_notebook_ch1.py --execute

ch2:                       ## chapter 2 tables, figures, notebook and LaTeX tables
	$(PY) scripts/run_chapter2.py && $(PY) scripts/make_ch2_tables.py && $(PY) scripts/build_notebook_ch2.py --execute

ch3:                       ## chapter 3 supply side: generation, capacity, retirements, realization model, 2030 cases (about 6 minutes)
	$(PY) scripts/run_chapter3.py && $(PY) scripts/make_ch3_tables.py && $(PY) scripts/build_notebook_ch3.py --execute

ch4:                       ## chapter 4 gap model, sensitivity, headroom, crosswalk, emissions (about a minute)
	$(PY) scripts/run_chapter4.py && $(PY) scripts/make_ch4_tables.py && $(PY) scripts/build_notebook_ch4.py --execute

report:                    ## build report/main.pdf with tectonic
	cd report && tectonic main.tex

clean-parts:               ## remove interrupted downloads
	find data/raw -name '*.part' -delete

provenance:                ## appendix tables mapping every figure to its processed files, raw sources and code; manifest rows behind the figures; assumption register
	$(PY) scripts/make_provenance_appendix.py && $(PY) scripts/make_assumption_register.py

FREEZE=2026-09-22

freeze:                    ## freeze the raw data: dated manifest copy and docs/DATA_FREEZE.md
	$(PY) scripts/freeze_data.py --date $(FREEZE)

defense:                   ## build the defense deck report/defense/defense.pdf with tectonic
	cd report/defense && tectonic defense.tex

release:                   ## export report, defense deck, processed CSVs, figures, tables, notebooks and frozen manifest to release/
	$(PY) scripts/export_release.py --date $(FREEZE)

brief:                     ## build the advisor progress memo report/brief/advisor_brief_<date>.pdf
	cd report/brief && tectonic advisor_brief_$(FREEZE).tex

overleaf:                  ## package report, memo and deck as an Overleaf-ready zip in release/
	$(PY) scripts/export_overleaf.py --date $(FREEZE)
