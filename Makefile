PY=.venv/bin/python
TODAY=$(shell date +%F)

.PHONY: env fetch fetch-large caiso snapshot catalog lab report clean-parts ch1

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

report:                    ## build report/main.pdf with tectonic
	cd report && tectonic main.tex

clean-parts:               ## remove interrupted downloads
	find data/raw -name '*.part' -delete
