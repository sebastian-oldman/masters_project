#!/usr/bin/env python
"""Crawl CAISO library index pages and download every report they list.

Collections (each -> data/raw/caiso_library/<access_date>/<collection>/):
  curtailment_daily_pdf   Daily wind/solar real-time dispatch curtailment reports, Jun 2016 - May 2025
                          (library year pages -> month pages -> /documents/*.pdf)
  renewables_daily_html   Daily Renewable Reports, Jun 2025 onward (HTML pages with embedded JS data
                          arrays incl. hourly VER curtailment MWh and MW)
  renewables_monthly_pdf  Monthly Renewables Performance Reports, 2017 onward

Index pages are crawled two levels deep from the roots below; only links under
/documents/ are downloaded. A per-collection manifest records url, status, bytes,
sha256; one summary row per collection goes to data/raw/manifest.csv.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests  # noqa: E402
from src.fetch import _append_row, MANIFEST_FIELDS  # noqa: E402
from src.paths import RAW, MANIFEST  # noqa: E402
from src.sources import UA  # noqa: E402

BASE = "https://www.caiso.com"
ROOTS = {
    "curtailment_daily_pdf": ["/library/daily-wind-solar-real-time-dispatch-curtailment-reports"],
    "renewables_daily_html": ["/library/daily-renewable-reports"],
    "renewables_monthly_pdf": ["/library/monthly-renewables-performance-report"],
}
INDEX_PAT = {
    "curtailment_daily_pdf": re.compile(r"/library/[^\"']*curtailment-reports[^\"']*"),
    "renewables_daily_html": re.compile(r"/library/[^\"']*daily-renewable-reports[^\"']*"),
    "renewables_monthly_pdf": re.compile(r"/library/[^\"']*renewables-performance-report[^\"']*"),
}
DOC_PAT = re.compile(r"/documents/[^\"'#?]+\.(?:pdf|html|xlsx|xls|csv)")

S = requests.Session()
S.headers["User-Agent"] = UA


def get(url: str, tries: int = 4) -> requests.Response | None:
    for i in range(tries):
        try:
            r = S.get(url, timeout=90)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(2 * (i + 1))
    return None


def crawl(collection: str) -> list[str]:
    seen_idx, docs = set(), set()
    frontier = [urljoin(BASE, p) for p in ROOTS[collection]]
    depth = 0
    while frontier and depth <= 2:
        nxt = []
        for url in frontier:
            if url in seen_idx:
                continue
            seen_idx.add(url)
            r = get(url)
            if not r:
                continue
            html = r.text
            docs.update(urljoin(BASE, m.group(0)) for m in DOC_PAT.finditer(html))
            for m in INDEX_PAT[collection].finditer(html):
                u = urljoin(BASE, m.group(0))
                if u not in seen_idx:
                    nxt.append(u)
        frontier = sorted(set(nxt))
        depth += 1
    print(f"[{collection}] {len(seen_idx)} index pages, {len(docs)} documents", flush=True)
    return sorted(docs)


def download(collection: str, urls: list[str], out: Path, workers: int) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    man = out / "manifest_collection.csv"
    done = {}
    if man.exists():
        with man.open(newline="") as f:
            done = {r["url"]: r for r in csv.DictReader(f) if r["status"] == "200"}
    todo = [u for u in urls if u not in done]
    print(f"[{collection}] {len(todo)} to download ({len(done)} present)", flush=True)

    def work(u):
        name = u.rsplit("/", 1)[-1]
        dest = out / name
        r = get(u)
        if r is None or not r.content:
            return {"url": u, "file": name, "status": "404", "bytes": 0, "sha256": ""}
        ct = r.headers.get("Content-Type", "")
        if name.endswith(".pdf") and not r.content.startswith(b"%PDF"):
            return {"url": u, "file": name, "status": f"bad:{ct[:30]}", "bytes": 0, "sha256": ""}
        dest.write_bytes(r.content)
        return {"url": u, "file": name, "status": "200", "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest()}

    new = not man.exists()
    rows = list(done.values())
    with man.open("a", newline="") as f, ThreadPoolExecutor(max_workers=workers) as ex:
        w = csv.DictWriter(f, fieldnames=["url", "file", "status", "bytes", "sha256"])
        if new:
            w.writeheader()
        for i, fut in enumerate(as_completed([ex.submit(work, u) for u in todo]), 1):
            row = fut.result(); w.writerow(row); rows.append(row)
            if i % 250 == 0:
                f.flush(); print(f"[{collection}] {i}/{len(todo)}", flush=True)
    return [r for r in rows if r["status"] == "200"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collection", choices=list(ROOTS) + ["all"], default="all")
    ap.add_argument("--access-date", default=date.today().isoformat())
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    for c in (list(ROOTS) if a.collection == "all" else [a.collection]):
        out = RAW / "caiso_library" / a.access_date / c
        urls = crawl(c)
        ok = download(c, urls, out, a.workers)
        if ok:
            ok = sorted(ok, key=lambda r: r["file"])
            combined = hashlib.sha256("".join(r["sha256"] for r in ok).encode()).hexdigest()
            _append_row(MANIFEST, MANIFEST_FIELDS, {
                "source_id": f"caiso_library_{c}", "group": "caiso_library", "owner": "CAISO",
                "title": f"CAISO library collection {c}: {len(ok)} documents crawled from {ROOTS[c][0]}",
                "url": urljoin(BASE, ROOTS[c][0]), "final_url": urljoin(BASE, ROOTS[c][0]), "filename": f"{len(ok)} files",
                "local_path": str(out.relative_to(RAW.parent.parent)), "access_date": a.access_date,
                "sha256": combined, "bytes": sum(int(r["bytes"]) for r in ok), "http_status": "200",
                "content_type": "mixed", "tags": "collection",
                "notes": "Per-file hashes in manifest_collection.csv; combined hash = sha256 of concatenated per-file hashes in filename order."})
        print(f"[{c}] done: {len(ok)} files", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
