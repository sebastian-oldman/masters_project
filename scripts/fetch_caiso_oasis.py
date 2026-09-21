#!/usr/bin/env python
"""Direct CAISO OASIS client for day-ahead hourly LMPs (PRC_LMP, market_run_id=DAM).

Why not gridstatus: OASIS rate-limits (HTTP 429) and gridstatus drops the affected
month silently. This client requests one calendar month at a time (OASIS limit is 31
days), retries 429/5xx with backoff, validates the row count against hours x nodes,
and writes one CSV per month under data/raw/caiso_oasis/<access_date>/dam_lmp/.
OASIS retains roughly 39 months online; requests before that return "No data".

Usage: python scripts/fetch_caiso_oasis.py --start 2023-07 --end 2026-09
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import io
import sys
import time
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests  # noqa: E402
from src.fetch import _append_row, MANIFEST_FIELDS  # noqa: E402
from src.paths import RAW, MANIFEST, LOGS  # noqa: E402

NODE_GROUPS = {"dlap": ["DLAP_PGAE-APND", "DLAP_SCE-APND", "DLAP_SDGE-APND"],
               "hubs": ["TH_NP15_GEN-APND", "TH_SP15_GEN-APND", "TH_ZP26_GEN-APND"]}
NODES = NODE_GROUPS["dlap"]  # set from --nodes at runtime
PT = ZoneInfo("America/Los_Angeles")
URL = "https://oasis.caiso.com/oasisapi/SingleZip"
S = requests.Session()
S.headers["User-Agent"] = "capstone-data-fetch/0.1 (academic research; contact via CEC docket)"


def month_bounds(y: int, m: int):
    start = datetime(y, m, 1, tzinfo=PT)
    end = datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=PT)
    return start, end


def fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H:%M-0000")


def fetch_month(y: int, m: int, tries: int = 5) -> tuple[str, list[str]]:
    start, end = month_bounds(y, m)
    params = {"resultformat": 6, "queryname": "PRC_LMP", "version": 12, "market_run_id": "DAM",
              "node": ",".join(NODES), "startdatetime": fmt(start), "enddatetime": fmt(end)}
    for i in range(tries):
        try:
            r = S.get(URL, params=params, timeout=900)  # a month of 3 nodes takes ~2 minutes on OASIS
        except requests.RequestException as e:
            time.sleep(15 * (i + 1)); continue
        if r.status_code == 429:
            time.sleep(30 * (i + 1)); continue
        if r.status_code != 200:
            time.sleep(10 * (i + 1)); continue
        try:
            z = zipfile.ZipFile(io.BytesIO(r.content))
        except zipfile.BadZipFile:
            time.sleep(10); continue
        names = z.namelist()
        if not names:
            return "empty", []
        data = z.read(names[0]).decode("utf-8", errors="replace")
        if names[0].endswith(".xml") or "No data returned" in data[:2000]:
            return "nodata", []
        lines = data.splitlines()
        return "ok", lines
    return "failed", []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-07")
    ap.add_argument("--end", default=date.today().strftime("%Y-%m"))
    ap.add_argument("--access-date", default=date.today().isoformat())
    ap.add_argument("--sleep", type=float, default=6.0)
    ap.add_argument("--nodes", choices=list(NODE_GROUPS), default="dlap")
    a = ap.parse_args()
    global NODES
    NODES = NODE_GROUPS[a.nodes]
    out = RAW / "caiso_oasis" / a.access_date / "dam_lmp"
    out.mkdir(parents=True, exist_ok=True)
    man = out / f"manifest_dam_lmp_{a.nodes}.csv"
    done = {}
    if man.exists():
        with man.open(newline="") as f:
            done = {r["month"]: r for r in csv.DictReader(f) if r["status"] == "ok"}
    y, m = map(int, a.start.split("-")); ey, em = map(int, a.end.split("-"))
    months = []
    while (y, m) <= (ey, em):
        months.append((y, m)); m += 1
        if m == 13: y, m = y + 1, 1
    new = not man.exists()
    with man.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["month", "status", "rows", "expected_rows", "bytes", "sha256", "file"])
        if new: w.writeheader()
        for (yy, mm) in months:
            key = f"{yy}-{mm:02d}"
            if key in done:
                continue
            status, lines = fetch_month(yy, mm)
            row = {"month": key, "status": status, "rows": 0, "expected_rows": 0, "bytes": 0, "sha256": "", "file": ""}
            if status == "ok":
                start, end = month_bounds(yy, mm)
                hours = int((end.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds() // 3600)
                # OASIS returns one row per hour per node per component (LMP, MCE, MCC, MCL, MGHG) -> 5 rows per hour-node
                row["expected_rows"] = hours * len(NODES) * 5
                row["rows"] = len(lines) - 1
                dest = out / f"dam_lmp_{a.nodes}_{key}.csv"
                dest.write_text("\n".join(lines) + "\n")
                row["bytes"] = dest.stat().st_size
                row["sha256"] = hashlib.sha256(dest.read_bytes()).hexdigest()
                row["file"] = dest.name
                if row["rows"] < 0.98 * row["expected_rows"]:
                    row["status"] = "short"
            w.writerow(row); f.flush()
            print(f"{key} {row['status']} rows={row['rows']} expected={row['expected_rows']}", flush=True)
            time.sleep(a.sleep)
    with man.open(newline="") as f:
        ok = sorted((r for r in csv.DictReader(f) if r["status"] == "ok"), key=lambda r: r["month"])
    if ok:
        combined = hashlib.sha256("".join(r["sha256"] for r in ok).encode()).hexdigest()
        _append_row(MANIFEST, MANIFEST_FIELDS, {
            "source_id": f"caiso_dam_lmp_monthly_{a.nodes}", "group": "caiso_oasis", "owner": "CAISO OASIS",
            "title": f"CAISO OASIS day-ahead hourly LMP (PRC_LMP, DAM, v12) {ok[0]['month']} to {ok[-1]['month']}, nodes {', '.join(NODES)}, one CSV per month",
            "url": URL + "?queryname=PRC_LMP&market_run_id=DAM&version=12", "final_url": URL, "filename": f"{len(ok)} files",
            "local_path": str(out.relative_to(RAW.parent.parent)), "access_date": a.access_date, "sha256": combined,
            "bytes": sum(int(r["bytes"]) for r in ok), "http_status": "200", "content_type": "text/csv", "tags": "collection",
            "notes": f"Rows per hour-node = 5 (LMP, MCE energy, MCC congestion, MCL loss, MGHG greenhouse gas). OASIS retains ~39 months; earlier months return no data. Per-month hashes in manifest_dam_lmp_{a.nodes}.csv."})
    print("done:", len(ok), "months ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
