#!/usr/bin/env python
"""Fetch every registered raw source (or a subset) into data/raw.

Examples
  python scripts/fetch_all.py --dry-run
  python scripts/fetch_all.py --group eia930 --exclude-tag large
  python scripts/fetch_all.py --workers 6
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from src.fetch import fetch  # noqa: E402
from src.sources import all_sources  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", action="append", help="only these groups (repeatable)")
    ap.add_argument("--id", action="append", help="only these source ids (repeatable)")
    ap.add_argument("--exclude-tag", action="append", default=[])
    ap.add_argument("--only-tag", action="append", default=[])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-download even if fetched today")
    ap.add_argument("--access-date", default=date.today().isoformat())
    a = ap.parse_args()

    srcs = all_sources()
    if a.group or a.id:  # union of the selected groups and ids
        srcs = [s for s in srcs if (a.group and s.group in a.group) or (a.id and s.id in a.id)]
    if a.exclude_tag:
        srcs = [s for s in srcs if not set(s.tags) & set(a.exclude_tag)]
    if a.only_tag:
        srcs = [s for s in srcs if set(s.tags) & set(a.only_tag)]
    print(f"{len(srcs)} sources selected", flush=True)
    if a.dry_run:
        for s in srcs:
            print(f"  [{s.group}] {s.id}  <- {s.url}")
        return 0

    ok = fail = skipped = 0
    failures = []
    t0 = time.time()

    def work(s):
        with requests.Session() as sess:
            return fetch(s, sess, access_date=a.access_date, force=a.force)

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(work, s): s for s in srcs}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            if r.ok and r.error == "already fetched today":
                skipped += 1
                tag = "SKIP"
            elif r.ok:
                ok += 1
                tag = "OK  "
            else:
                fail += 1
                failures.append(r)
                tag = "FAIL" if not r.source.optional else "MISS"
            size = r.row.get("bytes", "")
            print(f"[{i:4d}/{len(srcs)}] {tag} {r.source.id:45s} {size:>12} {r.error[:80]}", flush=True)

    print(f"\nfetched {ok}, skipped {skipped}, failed {fail} in {time.time()-t0:.0f}s")
    hard = [r for r in failures if not r.source.optional]
    if hard:
        print(f"\n{len(hard)} non-optional failures:")
        for r in hard:
            print(f"  {r.source.id}: {r.error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
