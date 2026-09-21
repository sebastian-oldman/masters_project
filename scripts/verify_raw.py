#!/usr/bin/env python
"""Open the key raw files and print what they contain. Run after fetch_all."""
from __future__ import annotations

import csv
import io
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402
from pypdf import PdfReader  # noqa: E402
from src.paths import RAW, MANIFEST  # noqa: E402

man = pd.read_csv(MANIFEST)
latest = man.sort_values("access_date").groupby("source_id").tail(1).set_index("source_id")


def path(sid: str) -> Path:
    return RAW.parent.parent / latest.loc[sid, "local_path"]


def pdf_text(sid: str, pages=None, maxchars=600) -> str:
    r = PdfReader(str(path(sid)))
    pages = pages or range(len(r.pages))
    txt = " ".join((r.pages[i].extract_text() or "") for i in pages if i < len(r.pages))
    return re.sub(r"\s+", " ", txt)[:maxchars]


def section(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


section("Census C30 privtime.xlsx: Data center line")
df = pd.read_excel(path("census_c30_privtime"), header=None)
hits = df[df.apply(lambda r: r.astype(str).str.contains("Data center", case=False).any(), axis=1)]
print(f"sheet shape {df.shape}; rows mentioning 'Data center': {len(hits)}")
print(hits.iloc[:3, :8].to_string())

section("EIA-930 BALANCE 2026 Jan-Jun: CISO rows")
p = path("eia930_balance_2026_jan_jun")
ciso = pd.concat(c[c["Balancing Authority"] == "CISO"] for c in pd.read_csv(p, chunksize=200_000, low_memory=False))
print(f"file {p.name}: CISO rows {len(ciso)}; columns: {list(ciso.columns)[:12]} ...")
dcol = [c for c in ciso.columns if c.startswith("Demand (MW)")][0]
print(ciso[["UTC Time at End of Hour", dcol]].head(3).to_string(index=False))
print("max hourly demand in file:", ciso[dcol].max())

section("EIA-930 SUBREGION 2026 Jan-Jun: CISO subregions")
sub = pd.concat(c[c["Balancing Authority"] == "CISO"] for c in pd.read_csv(path("eia930_subregion_2026_jan_jun"), chunksize=200_000, low_memory=False))
print(sub.groupby("Sub-Region").size())

section("CEC Assembly hearing deck (Jan 28 2026): pages mentioning MW tiers")
r = PdfReader(str(path("cec_assembly_hearing_2026_01_28")))
print("pages:", len(r.pages))
for i, pg in enumerate(r.pages):
    t = re.sub(r"\s+", " ", pg.extract_text() or "")
    if re.search(r"5,?086|9,?587|8,?604", t):
        print(f"  page {i+1}: {t[:500]}")

section("CEC 26-IEPR-03 TN 272026 Data Center Demand Forecast (Aug 2026): first pages")
print(pdf_text("cec_tn272026", pages=range(0, 6), maxchars=1800))

section("CEC 26-IEPR-03 TN 272043 Load Energization Requests REVISED (Aug 2026)")
print(pdf_text("cec_tn272043", pages=range(0, 5), maxchars=1500))

section("CEC preliminary data center forecast deck (Oct 2025): utilization / confidence text")
t = pdf_text("cec_prelim_dc_forecast_2025", maxchars=100000)
for kw in ("67", "confidence", "ramp", "PG&E", "SCE"):
    m = re.search(r".{0,120}" + re.escape(kw) + r".{0,160}", t)
    print(f"  [{kw}] {m.group(0) if m else 'not found'}")

section("SCE IEPR25 Data Center Database PUBLIC (two vintages)")
for sid in ("cec_tn266008", "cec_tn268459"):
    p = path(sid)
    x = pd.ExcelFile(p)
    print(f"{sid} {p.name}: sheets {x.sheet_names}")
    d = x.parse(x.sheet_names[0])
    print(f"  shape {d.shape}; columns: {list(d.columns)[:14]}")
    print(d.head(3).to_string()[:900])

section("CEC Form 1.1c Data Center Allocations (TN 268824)")
p = path("cec_tn268824"); x = pd.ExcelFile(p); print(p.name, x.sheet_names)
d = x.parse(x.sheet_names[0], header=None); print(d.iloc[:12, :8].to_string())

section("Epoch AI data_centers.csv: California rows")
e = pd.read_csv(path("epoch_data_centers"))
print("columns:", list(e.columns)[:20]); 
loc = [c for c in e.columns if re.search("state|location|region", c, re.I)]
print("location-like columns:", loc)
ca = e[e["Address"].astype(str).str.contains(r", CA\b|California", regex=True)]
print("US states seen in Address:", sorted({m.group(1) for a in e["Address"].astype(str) for m in [re.search(r", ([A-Z]{2})\b", a)] if m}))
print(f"rows {len(e)}, California-matching rows {len(ca)}")
print(ca.iloc[:8, :6].to_string())

section("Kollar & Grady Zenodo bundle: contents")
with zipfile.ZipFile(path("kollar_grady_2025_zenodo")) as z:
    names = z.namelist(); print(len(names), "members")
    for n in names[:25]: print("  ", n)

section("BLS QCEW 518210 2025 Q1: California rows")
q = pd.read_csv(path("qcew_518210_2025q1"))
cal = q[q["area_fips"].astype(str).str.zfill(5).str.startswith("06")]
print(f"rows {len(q)}; California rows {len(cal)}")
print(cal[cal["own_code"] == 5][["area_fips", "own_code", "industry_code", "qtrly_estabs", "month3_emplvl", "total_qtrly_wages"]].head(6).to_string(index=False))

section("EIA-860M vintages: January 2016 and July 2026 sheet names + CA planned counts")
for sid in ("eia860m_2016_01", "eia860m_2026_07"):
    x = pd.ExcelFile(path(sid)); print(sid, x.sheet_names)
    sh = [s for s in x.sheet_names if "Planned" in s][0]
    raw = x.parse(sh, header=None, nrows=6)
    hdr = next(i for i in range(6) if raw.iloc[i].astype(str).str.contains("Plant State").any())
    d = x.parse(sh, header=hdr)
    st = [c for c in d.columns if "State" in str(c)][0]
    print(f"  planned sheet '{sh}': rows {len(d)}; California rows {(d[st]=='CA').sum()}; cols: {list(d.columns)[:10]}")

section("EIA-861 2024 zip members")
with zipfile.ZipFile(path("eia861_2024")) as z: print([n for n in z.namelist()][:20])
section("EIA-923 2025 zip members")
with zipfile.ZipFile(path("eia923_2025")) as z: print(z.namelist()[:10])
section("EIA-860 2025 zip members")
with zipfile.ZipFile(path("eia860_2025")) as z: print(z.namelist()[:12])

section("CEC ECDMS: electricity consumption by utility (annual)")
x = pd.ExcelFile(path("cec_cons_elec_utility_annual")); print(x.sheet_names)
d = x.parse(x.sheet_names[0]); print(d.shape); print(d.head(5).to_string()[:800])

section("eGRID2023: CAMX subregion rows")
x = pd.ExcelFile(path("epa_egrid2023_rev1")); print(x.sheet_names)
sr = x.parse("SRL23", header=1); print(sr[sr.iloc[:, 0].astype(str).str.contains("CAMX")].iloc[:, :8].to_string())

section("CAISO NQC 2026")
x = pd.ExcelFile(path("caiso_nqc_2026")); print(x.sheet_names); d = x.parse(x.sheet_names[0], header=None); print(d.iloc[:6, :8].to_string())

section("ERCOT Monthly June 2026: large load text")
t = pdf_text("ercot_monthly_2026_06", maxchars=200000)
for m in re.finditer(r".{0,160}[Ll]arge [Ll]oad.{0,200}", t):
    print("  ", m.group(0)); break

section("PJM 2026 load report: firm/non-firm mention")
t = pdf_text("pjm_2026_load_forecast_report", pages=range(0, 12), maxchars=200000)
m = re.search(r".{0,200}non-firm.{0,300}", t, re.I); print(m.group(0) if m else "not found in first 12 pages")

section("LBNL 2024 report title page")
print(pdf_text("lbnl_2024_dc_energy_report", pages=range(0, 1), maxchars=300))
section("EPRI 2024 Powering Intelligence: California mention")
t = pdf_text("epri_powering_intelligence_2024", maxchars=400000)
m = re.search(r".{0,200}California.{0,300}", t); print(m.group(0) if m else "not found")
