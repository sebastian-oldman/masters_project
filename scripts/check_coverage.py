#!/usr/bin/env python
"""Completeness check: compare files on disk against the full expected set for every
periodic dataset and report gaps (missing files, missing days, short months)."""
from __future__ import annotations

import csv
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402
from src.paths import RAW, MANIFEST  # noqa: E402
from src.sources import all_sources, MONTHS  # noqa: E402

man = pd.read_csv(MANIFEST)
have = set(man.source_id)
srcs = {s.id: s for s in all_sources()}
gaps = []


def report(name, missing, extra=""):
    status = "OK " if not missing else "GAP"
    print(f"[{status}] {name}: {len(missing)} missing {extra}")
    if missing:
        print("      " + ", ".join(map(str, list(missing)[:40])) + (" ..." if len(missing) > 40 else ""))
        gaps.append((name, list(missing)))


# 1. registry vs manifest, by group
for g in sorted({s.group for s in srcs.values()}):
    ids = [i for i, s in srcs.items() if s.group == g]
    miss = [i for i in ids if i not in have and not srcs[i].optional]
    opt = [i for i in ids if i not in have and srcs[i].optional]
    report(f"registry group {g} ({len(ids)} registered)", miss, f"| optional not fetched: {len(opt)} {opt[:6]}")

# 2. EIA-930 half-years and CISO hour counts
for kind, first in (("balance", (2015, "jul_dec")), ("subregion", (2018, "jul_dec")), ("interchange", (2015, "jul_dec"))):
    exp = []
    for y in range(first[0], 2027):
        for h in ("jan_jun", "jul_dec"):
            if (y, h) < first: continue
            if (y, h) > (2026, "jan_jun"): continue
            exp.append(f"eia930_{kind}_{y}_{h}")
    report(f"EIA-930 {kind} half-year files", [e for e in exp if e not in have])
rows = man[man.source_id.str.startswith("eia930_balance_")]
short = []
for _, r in rows.iterrows():
    n = 0
    for c in pd.read_csv(RAW.parent.parent / r.local_path, usecols=["Balancing Authority"], chunksize=500000):
        n += int((c["Balancing Authority"] == "CISO").sum())
    y, h = re.search(r"_(\d{4})_(\w+)$", r.source_id).groups()
    days = (date(int(y), 7, 1) - date(int(y), 1, 1)).days if h == "jan_jun" else (date(int(y) + 1, 1, 1) - date(int(y), 7, 1)).days
    if r.source_id == "eia930_balance_2015_jul_dec": days = (date(2016, 1, 1) - date(2015, 7, 1)).days
    exp_hours = days * 24
    if n < 0.97 * exp_hours and r.source_id not in ("eia930_balance_2026_jan_jun", "eia930_balance_2026_jul_dec"):  # current half-year is partial by design
        short.append(f"{r.source_id}: {n}/{exp_hours} CISO hours")
report("EIA-930 BALANCE CISO hour counts (>=97% of half-year)", short)

# 3. annual EIA series
for g, first, last in (("eia861", 2010, 2024), ("eia923", 2010, 2025), ("eia860", 2010, 2025)):
    report(f"{g} years {first}-{last}", [f"{g}_{y}" for y in range(first, last + 1) if f"{g}_{y}" not in have])
exp = []
y, m = 2015, 7
while (y, m) <= (2026, 7):
    exp.append(f"eia860m_{y}_{m:02d}"); m += 1
    if m == 13: y, m = y + 1, 1
report("EIA-860M monthly vintages Jul 2015 - Jul 2026", [e for e in exp if e not in have])

# 4. QCEW quarters
exp = [f"qcew_518210_{y}q{q}" for y in range(2015, 2026) for q in (1, 2, 3, 4)] + ["qcew_518210_2026q1"]
report("QCEW 518210 quarterly 2015Q1-2026Q1", [e for e in exp if e not in have])
report("QCEW annual 2015-2024", [e for y in range(2015, 2025) for e in (f"qcew_518210_{y}_annual", f"qcew_area06000_{y}_annual") if e not in have])

# 5. CAISO Today's Outlook day coverage
base = RAW / "caiso_outlook" / "2026-09-21"
end = date(2026, 9, 20)
for kind, start in (("co2", date(2018, 4, 10)), ("fuelsource", date(2018, 4, 10)), ("demand", date(2018, 4, 10)), ("netdemand", date(2018, 4, 10)), ("renewables", None)):
    files = {p.stem for p in (base / kind).glob("*.csv")}
    if start is None:
        start = date.fromisoformat(min(files)[:4] + "-" + min(files)[4:6] + "-" + min(files)[6:]) if files else end
    d, miss = start, []
    while d <= end:
        if d.strftime("%Y%m%d") not in files: miss.append(d.isoformat())
        d += timedelta(days=1)
    report(f"CAISO outlook {kind} daily {start} to {end} ({len(files)} files)", miss)

# 6. CAISO library daily coverage
lib = RAW / "caiso_library" / "2026-09-21"
pdfs = list((lib / "curtailment_daily_pdf").glob("*.pdf")) + list((lib / "curtailment_daily_pdf").glob("*.xlsx"))
mon = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
got = set()
for p in pdfs:
    n = p.name.lower()
    n = n.replace("wind_solarreal-timedispatchcurtailmentreport02dec_2020", "report02dec_2021")  # CAISO mislabeled the Dec 2 2021 report
    n = re.sub(r"-(january|february|march|april|june|july|august|september|october|november|december)-", lambda mm: "-" + mm.group(1)[:3] + "-", n)
    pats = [r"-([a-z]{3})-(\d{2})-(\d{4})(?:-v\d)?\.", r"report([a-z]{3})(\d{2})_?(\d{4})\.", r"report([a-z]{3})(\d{2})-(\d{4})\.",
            r"report-?([a-z]{3})(\d{2})_(\d{4})\."]
    m1 = None
    for pt in pats:
        m1 = re.search(pt, n)
        if m1: break
    m2 = re.search(r"report(\d{2})([a-z]{3})_(\d{4})\.", n)  # e.g. report20aug_2018
    if m1 and m1.group(1) in mon:
        got.add(date(int(m1.group(3)), mon[m1.group(1)], int(m1.group(2))))
    elif m2 and m2.group(2) in mon:
        got.add(date(int(m2.group(3)), mon[m2.group(2)], int(m2.group(1))))
d, miss = date(2016, 6, 30), []
while d <= date(2025, 5, 31):
    if d not in got: miss.append(d.isoformat())
    d += timedelta(days=1)
report(f"CAISO daily curtailment reports 2016-06-30 to 2025-05-31 ({len(got)} dated files of {len(pdfs)})", miss)
htmls = list((lib / "renewables_daily_html").glob("*.html"))
got = set()
for p in htmls:
    m1 = re.search(r"-([a-z]{3})-(\d{2})-(\d{4})(?:-corrected)?\.html", p.name.lower())
    if m1: got.add(date(int(m1.group(3)), mon[m1.group(1)], int(m1.group(2))))
d, miss = date(2025, 6, 1), []
while d <= end:
    if d not in got: miss.append(d.isoformat())
    d += timedelta(days=1)
report(f"CAISO daily renewable reports 2025-06-01 to {end} ({len(got)} files)", miss)
mpdfs = list((lib / "renewables_monthly_pdf").glob("*"))
print(f"[INFO] CAISO monthly renewables performance reports: {len(mpdfs)} files, e.g. {sorted(p.name for p in mpdfs)[:2]} ... {sorted(p.name for p in mpdfs)[-2:]}")

# 7. OASIS months
for grp in ("dlap", "hubs"):
    mf = RAW / "caiso_oasis" / "2026-09-21" / "dam_lmp" / f"manifest_dam_lmp_{grp}.csv"
    if mf.exists():
        rows = list(csv.DictReader(mf.open()))
        ok = {r["month"] for r in rows if r["status"] == "ok"}
        bad = [f"{r['month']}:{r['status']}" for r in rows if r["status"] != "ok"]
        exp = [f"{y}-{m:02d}" for y in range(2023, 2027) for m in range(1, 13) if (y, m) >= (2023, 7) and (y, m) <= (2026, 9)]
        report(f"OASIS DAM LMP {grp} months 2023-07 to 2026-09 ({len(ok)} ok so far)", [e for e in exp if e not in ok], f"| non-ok rows: {bad[:8]}")
    else:
        print(f"[INFO] OASIS {grp}: not started")

# 8. ERCOT monthlies
exp = [f"ercot_monthly_{y}_{m:02d}" for (y, m) in [(2025, mm) for mm in range(2, 13)] + [(2026, mm) for mm in range(1, 9)]]
report("ERCOT Monthly Feb 2025 - Aug 2026", [e for e in exp if e not in have])

print("\nTOTAL gap groups:", len(gaps))
