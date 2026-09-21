#!/usr/bin/env python
"""Monthly registry snapshot. Run on the first of each month (see Makefile / cron).

Writes data/snapshots/<YYYY-MM-DD>/ with:
  ercot/      Large Load Integration page, presentations index, any new "ERCOT Monthly"
              PDFs discovered on the 2025/2026 presentation pages
  cec/        docket log HTML for 25-IEPR-03 and 26-IEPR-03, parsed to docket_entries.csv,
              plus any new entries whose title mentions data centers / large loads / known loads
  pjm/        load-forecast page and the current load report PDF it links
  epoch/      the five Frontier Data Centers Hub CSVs and the zip bundle
  eia860m/    the newest EIA-860M monthly file that exists
  census/     C30 privtime.xlsx (the data-center construction series gets revised)
  caiso/      CAISO key statistics PDF for the previous month
and a manifest.csv (sha256, bytes, url, status) for everything saved.

Snapshots are the project's original longitudinal dataset; never edit them.
"""
from __future__ import annotations

import csv
import hashlib
import html as htmllib
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from src.paths import SNAPSHOTS  # noqa: E402
from src.sources import UA, MONTHS  # noqa: E402

TODAY = date.today()
OUT = SNAPSHOTS / TODAY.isoformat()
MAN = OUT / "manifest.csv"
S = requests.Session()
S.headers["User-Agent"] = UA
KEY = re.compile(r"data cent|large load|known load|energization", re.I)


def save(url: str, dest: Path, expect_binary=False) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    row = {"url": url, "path": str(dest.relative_to(SNAPSHOTS.parent.parent)), "status": "", "bytes": 0, "sha256": "", "note": ""}
    try:
        r = S.get(url, timeout=180)
        row["status"] = r.status_code
        ct = r.headers.get("Content-Type", "").split(";")[0]
        if r.status_code == 200 and r.content:
            if expect_binary and ct.startswith("text/html"):
                row["note"] = f"expected binary, got {ct}"
            else:
                dest.write_bytes(r.content)
                row["bytes"] = len(r.content)
                row["sha256"] = hashlib.sha256(r.content).hexdigest()
    except requests.RequestException as e:
        row["note"] = f"{type(e).__name__}: {e}"[:200]
    with MAN.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if f.tell() == 0:
            w.writeheader()
        w.writerow(row)
    print(f"{row['status']:>4} {row['bytes']:>10}  {dest.name}  {row['note']}")
    return row


def prior_snapshot_files() -> set[str]:
    names = set()
    for d in SNAPSHOTS.iterdir():
        if d.is_dir() and d.name != TODAY.isoformat():
            names.update(p.name for p in d.rglob("*") if p.is_file())
    return names


def ercot(seen: set[str]) -> None:
    save("https://www.ercot.com/services/rq/large-load-integration", OUT / "ercot" / "large_load_integration.html")
    for y in ("", "2025"):  # root page lists the current year; /2025 is the archive
        dest = OUT / "ercot" / f"presentations_{y or 'current'}.html"
        r = save(f"https://www.ercot.com/news/presentations/{y}".rstrip("/"), dest)
        if r["bytes"]:
            page = dest.read_text(errors="ignore")
            for u in sorted(set(re.findall(r'https://www\.ercot\.com/files/docs/[^"]*ERCOT-Monthly[^"]*\.pdf', page))):
                name = u.rsplit("/", 1)[-1]
                if name not in seen:
                    save(u, OUT / "ercot" / name, expect_binary=True)
    # month-name guesses for the two most recent ERCOT Monthly issues (dates vary, so try a window)
    for back in (1, 2):
        m = TODAY.month - back
        y = TODAY.year
        if m <= 0:
            m += 12
            y -= 1
        mon = MONTHS[m - 1].title()
        for name in (f"ERCOT-Monthly-{mon}-{y}-FINAL.pdf", f"ERCOT-Monthly-{mon}-{y}.pdf", f"ERCOT-Monthly-{mon}{y}.pdf"):
            if name in seen:
                continue
            pub_y, pub_m = (y, m + 1) if m < 12 else (y + 1, 1)
            for day in range(1, 29):
                u = f"https://www.ercot.com/files/docs/{pub_y}/{pub_m:02d}/{day:02d}/{name}"
                try:
                    if S.head(u, timeout=30).status_code == 200:
                        save(u, OUT / "ercot" / name, expect_binary=True)
                        seen.add(name)
                        break
                except requests.RequestException:
                    pass


def cec(seen: set[str]) -> None:
    entries = []
    for docket in ("25-IEPR-03", "26-IEPR-03"):
        dest = OUT / "cec" / f"docketlog_{docket}.html"
        r = save(f"https://efiling.energy.ca.gov/Lists/DocketLog.aspx?docketnumber={docket}", dest)
        if not r["bytes"]:
            continue
        t = dest.read_text(errors="ignore")
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
            links = re.findall(r"GetDocument\.aspx\?tn=(\d+)", row)
            if not links:
                continue
            txt = re.sub(r"\s+", " ", htmllib.unescape(re.sub("<[^>]+>", " ", row))).strip()
            m = re.match(r"(\d+)\s+(\d+/\d+/\d+)\s+(.*)", txt)
            entries.append({"docket": docket, "tn": links[0], "date": m.group(2) if m else "", "title": (m.group(3) if m else txt)[:300]})
    with (OUT / "cec" / "docket_entries.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["docket", "tn", "date", "title"])
        w.writeheader()
        w.writerows(entries)
    for e in entries:
        if KEY.search(e["title"]) and not any(n.startswith(f"TN{e['tn']}") for n in seen):
            save(f"https://efiling.energy.ca.gov/GetDocument.aspx?tn={e['tn']}", OUT / "cec" / f"TN{e['tn']}.bin", expect_binary=True)


def pjm(seen: set[str]) -> None:
    dest = OUT / "pjm" / "load_forecast_page.html"
    r = save("https://www.pjm.com/planning/resource-adequacy-planning/load-forecast-dev-process", dest)
    if r["bytes"]:
        page = dest.read_text(errors="ignore")
        for u in sorted(set(re.findall(r'/-/media/[^"]*load-forecast/\d{4}-load-report\.pdf', page, re.I))):
            name = u.rsplit("/", 1)[-1]
            if name not in seen:
                save("https://www.pjm.com" + u, OUT / "pjm" / name, expect_binary=True)


def epoch() -> None:
    for f in ("data_centers.csv", "data_center_timelines.csv", "data_centers_chip_quantities.csv",
              "data_center_chillers.csv", "data_center_cooling_towers.csv", "data_centers.zip"):
        save(f"https://epoch.ai/data/data_centers/{f}", OUT / "epoch" / f, expect_binary=True)


def eia860m(seen: set[str]) -> None:
    for back in (1, 2, 3):
        m, y = TODAY.month - back, TODAY.year
        if m <= 0:
            m, y = m + 12, y - 1
        name = f"{MONTHS[m-1]}_generator{y}.xlsx"
        if name in seen:
            return
        r = save(f"https://www.eia.gov/electricity/data/eia860m/xls/{name}", OUT / "eia860m" / name, expect_binary=True)
        if r["bytes"]:
            return


def census() -> None:
    save("https://www.census.gov/construction/c30/xlsx/privtime.xlsx", OUT / "census" / "privtime.xlsx", expect_binary=True)
    save("https://www.census.gov/construction/c30/xlsx/privsa.xlsx", OUT / "census" / "privsa.xlsx", expect_binary=True)


def caiso(seen: set[str]) -> None:
    save("https://www.caiso.com/content/charts/curtailments-monthly.csv", OUT / "caiso" / "curtailments-monthly.csv", expect_binary=True)
    m, y = TODAY.month - 1, TODAY.year
    if m == 0:
        m, y = 12, y - 1
    name = f"key-statistics-{MONTHS[m-1][:3]}-{y}.pdf"
    if name not in seen:
        save(f"https://www.caiso.com/documents/{name}", OUT / "caiso" / name, expect_binary=True)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    seen = prior_snapshot_files()
    print(f"snapshot {TODAY} -> {OUT}")
    ercot(seen); cec(seen); pjm(seen); epoch(); eia860m(seen); census(); caiso(seen)
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
