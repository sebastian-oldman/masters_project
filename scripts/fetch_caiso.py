#!/usr/bin/env python
"""Collect CAISO time series that are not available as bulk files.

Stage A  Today's Outlook history (5-minute CSVs, one file per day and kind)
         https://www.caiso.com/outlook/history/YYYYMMDD/{co2,fuelsource,demand,netdemand,renewables}.csv
         -> data/raw/caiso_outlook/<access_date>/<kind>/YYYYMMDD.csv
Stage B  OASIS day-ahead hourly LMPs at the three IOU default load aggregation
         points and the NP15/SP15/ZP26 trading hubs, via gridstatus
         -> data/raw/caiso_oasis/<access_date>/dam_lmp_<year>.csv
Stage C  Daily wind/solar curtailment (gridstatus parses CAISO's daily PDF reports)
         -> data/raw/caiso_oasis/<access_date>/curtailment_<year>.csv

Each stage writes its own manifest_<stage>.csv and one summary row per
collection in data/raw/manifest.csv.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from src.fetch import _append_row, MANIFEST_FIELDS  # noqa: E402
from src.paths import RAW, MANIFEST, LOGS  # noqa: E402
from src.sources import UA  # noqa: E402

KINDS = ["co2", "fuelsource", "demand", "netdemand", "renewables"]
OUTLOOK_START = date(2018, 4, 10)
LOCATIONS = ["DLAP_PGAE-APND", "DLAP_SCE-APND", "DLAP_SDGE-APND",
             "TH_NP15_GEN-APND", "TH_SP15_GEN-APND", "TH_ZP26_GEN-APND"]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def summary_row(source_id, group, title, url, out_dir: Path, access_date, notes, n_files, total_bytes, combined_hash):
    row = {"source_id": source_id, "group": group, "owner": "CAISO", "title": title, "url": url,
           "final_url": url, "filename": f"{n_files} files", "local_path": str(out_dir.relative_to(RAW.parent.parent)),
           "access_date": access_date, "sha256": combined_hash, "bytes": total_bytes, "http_status": "200",
           "content_type": "text/csv", "tags": "collection", "notes": notes}
    _append_row(MANIFEST, MANIFEST_FIELDS, row)


# ---------------------------------------------------------------- Stage A
def stage_outlook(access_date: str, start: date, end: date, workers: int) -> None:
    base = RAW / "caiso_outlook" / access_date
    base.mkdir(parents=True, exist_ok=True)
    man = base / "manifest_outlook.csv"
    done = set()
    if man.exists():
        with man.open(newline="") as f:
            done = {(r["kind"], r["day"]) for r in csv.DictReader(f)}
    jobs = [(k, d) for k in KINDS for d in _days(start, end) if (k, d.strftime("%Y%m%d")) not in done]
    print(f"[outlook] {len(jobs)} day-files to fetch ({len(done)} already present)", flush=True)
    sess_local = {}

    def work(job):
        kind, d = job
        ds = d.strftime("%Y%m%d")
        url = f"https://www.caiso.com/outlook/history/{ds}/{kind}.csv"
        dest = base / kind / f"{ds}.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        s = sess_local.setdefault("s", requests.Session())
        for attempt in range(4):
            try:
                r = s.get(url, headers={"User-Agent": UA}, timeout=60)
                if r.status_code == 404:
                    return (kind, ds, "404", 0, "")
                if r.status_code == 200 and r.content.strip():
                    dest.write_bytes(r.content)
                    return (kind, ds, "200", len(r.content), sha256_of(dest))
                time.sleep(1.5 * (attempt + 1))
            except requests.RequestException:
                time.sleep(2 * (attempt + 1))
        return (kind, ds, "ERR", 0, "")

    new = not man.exists()
    with man.open("a", newline="") as f, ThreadPoolExecutor(max_workers=workers) as ex:
        w = csv.writer(f)
        if new:
            w.writerow(["kind", "day", "status", "bytes", "sha256"])
        n = 0
        for fut in as_completed([ex.submit(work, j) for j in jobs]):
            w.writerow(fut.result())
            n += 1
            if n % 500 == 0:
                f.flush()
                print(f"[outlook] {n}/{len(jobs)}", flush=True)
    # summary rows
    with man.open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["status"] == "200"]
    for kind in KINDS:
        rk = sorted((r for r in rows if r["kind"] == kind), key=lambda r: r["day"])
        if not rk:
            continue
        combined = hashlib.sha256("".join(r["sha256"] for r in rk).encode()).hexdigest()
        summary_row(f"caiso_outlook_{kind}", "caiso_outlook",
                    f"CAISO Today's Outlook history, {kind}.csv, 5-minute, {rk[0]['day']} to {rk[-1]['day']}",
                    "https://www.caiso.com/outlook/history/YYYYMMDD/" + kind + ".csv", base / kind, access_date,
                    "One CSV per day; combined hash = sha256 of concatenated per-file hashes in day order.",
                    len(rk), sum(int(r["bytes"]) for r in rk), combined)
    print("[outlook] done", flush=True)


def _days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


# ---------------------------------------------------------------- Stage B/C
def stage_oasis(access_date: str, first_year: int, last_year: int, do_lmp: bool, do_curtail: bool) -> None:
    import pandas as pd
    import gridstatus

    base = RAW / "caiso_oasis" / access_date
    base.mkdir(parents=True, exist_ok=True)
    iso = gridstatus.CAISO()
    today = date.today()
    for year in range(first_year, last_year + 1):
        start = f"{year}-01-01"
        end = f"{year+1}-01-01" if year < today.year else today.isoformat()
        if do_lmp:
            dest = base / f"dam_lmp_{year}.csv"
            if not dest.exists():
                print(f"[oasis] DAM LMP {year} ...", flush=True)
                try:
                    df = iso.get_lmp(date=start, end=end, market=gridstatus.Markets.DAY_AHEAD_HOURLY,
                                     locations=LOCATIONS, sleep=5, verbose=False)
                    df.to_csv(dest, index=False)
                    summary_row(f"caiso_dam_lmp_{year}", "caiso_oasis",
                                f"CAISO OASIS day-ahead hourly LMP {year}, DLAP PGAE/SCE/SDGE and NP15/SP15/ZP26 hubs (via gridstatus {gridstatus.__version__})",
                                "http://oasis.caiso.com/oasisapi/SingleZip?queryname=PRC_LMP&market_run_id=DAM", dest, access_date,
                                "Columns: Time, Location, LMP, Energy, Congestion, Loss. Retrieved through gridstatus.", 1,
                                dest.stat().st_size, sha256_of(dest))
                except Exception as e:  # keep going; record failure
                    print(f"[oasis] DAM LMP {year} FAILED: {e}", flush=True)
                    _append_row(LOGS / "fetch_failures.csv",
                                ["source_id", "group", "url", "access_date", "http_status", "content_type", "error", "optional", "tags"],
                                {"source_id": f"caiso_dam_lmp_{year}", "group": "caiso_oasis", "url": "OASIS PRC_LMP", "access_date": access_date,
                                 "error": str(e)[:300], "optional": False, "tags": ""})
        if do_curtail and year >= 2016:
            dest = base / f"curtailment_{year}.csv"
            if not dest.exists():
                print(f"[oasis] curtailment {year} ...", flush=True)
                try:
                    s2 = "2016-06-30" if year == 2016 else start
                    df = iso.get_curtailment(date=s2, end=end, verbose=False)
                    df.to_csv(dest, index=False)
                    summary_row(f"caiso_curtailment_{year}", "caiso_oasis",
                                f"CAISO daily wind/solar real-time dispatch curtailment {year} (parsed from daily PDF reports via gridstatus)",
                                "https://www.caiso.com/library/daily-wind-solar-real-time-dispatch-curtailment-reports", dest, access_date,
                                "Hourly curtailed MWh by fuel and curtailment type.", 1, dest.stat().st_size, sha256_of(dest))
                except Exception as e:
                    print(f"[oasis] curtailment {year} FAILED: {e}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["outlook", "lmp", "curtailment", "all"], default="all")
    ap.add_argument("--access-date", default=date.today().isoformat())
    ap.add_argument("--start", default=OUTLOOK_START.isoformat())
    ap.add_argument("--end", default=(date.today() - timedelta(days=1)).isoformat())
    ap.add_argument("--first-year", type=int, default=2019)
    ap.add_argument("--last-year", type=int, default=date.today().year)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    if a.stage in ("outlook", "all"):
        stage_outlook(a.access_date, date.fromisoformat(a.start), date.fromisoformat(a.end), a.workers)
    if a.stage in ("lmp", "curtailment", "all"):
        stage_oasis(a.access_date, a.first_year, a.last_year, do_lmp=a.stage in ("lmp", "all"),
                    do_curtail=a.stage in ("curtailment", "all"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
