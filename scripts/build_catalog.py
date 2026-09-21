#!/usr/bin/env python
"""Render docs/DATA_CATALOG.md from data/raw/manifest.csv and logs/fetch_failures.csv."""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.paths import MANIFEST, FAILURES, ROOT  # noqa: E402
from src.sources import all_sources  # noqa: E402

out = ROOT / "docs" / "DATA_CATALOG.md"
out.parent.mkdir(exist_ok=True)
rows = list(csv.DictReader(MANIFEST.open())) if MANIFEST.exists() else []
fails = list(csv.DictReader(FAILURES.open())) if FAILURES.exists() else []
fetched_ids = {r["source_id"] for r in rows}
by_group = defaultdict(list)
for r in rows:
    by_group[r["group"]].append(r)
registered = {s.id: s for s in all_sources()}

lines = ["# Data catalog", "",
         f"Generated from `data/raw/manifest.csv` ({len(rows)} files, "
         f"{sum(int(r['bytes'] or 0) for r in rows)/1e9:.2f} GB) and `logs/fetch_failures.csv`.", "",
         "| Group | Files | Bytes | Owners |", "|---|---:|---:|---|"]
for g, rs in sorted(by_group.items()):
    lines.append(f"| {g} | {len(rs)} | {sum(int(r['bytes'] or 0) for r in rs)/1e6:,.1f} MB | {', '.join(sorted({r['owner'] for r in rs}))} |")
lines += ["", "## Files", ""]
for g, rs in sorted(by_group.items()):
    lines += [f"### {g}", "", "| id | title | access date | bytes | sha256 (12) | path |", "|---|---|---|---:|---|---|"]
    for r in sorted(rs, key=lambda r: r["source_id"]):
        lines.append(f"| {r['source_id']} | {r['title'][:110]} | {r['access_date']} | {int(r['bytes'] or 0):,} | {r['sha256'][:12]} | `{r['local_path']}` |")
    lines.append("")
missing = [s for i, s in registered.items() if i not in fetched_ids]
if missing:
    lines += ["## Registered but not fetched", "", "| id | optional | tags | reason |", "|---|---|---|---|"]
    reasons = {f["source_id"]: f["error"] for f in fails}
    for s in sorted(missing, key=lambda s: (not s.optional, s.group, s.id)):
        lines.append(f"| {s.id} | {s.optional} | {';'.join(s.tags)} | {reasons.get(s.id, '')[:120]} |")
out.write_text("\n".join(lines) + "\n")
print(f"wrote {out} ({len(rows)} files, {len(missing)} not fetched)")
