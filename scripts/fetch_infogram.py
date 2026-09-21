#!/usr/bin/env python
"""Save Infogram embed data (window.infographicData JSON) and extract any tabular data to CSV.

CBRE's market chapters render their figures as Infogram embeds; the embed page carries
the chart's data. Usage:
  python scripts/fetch_infogram.py --group market_reports --prefix cbre_h1_2026_silicon_valley \
      --parent-url <chapter url> <embed-id> [<embed-id> ...]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests  # noqa: E402
from src.fetch import _append_row, MANIFEST_FIELDS  # noqa: E402
from src.paths import RAW, MANIFEST  # noqa: E402
from src.sources import UA  # noqa: E402


def _cell(c):
    """Infogram chart cells are {"value": x}; table cells are spreadsheet-style dicts
    ({"value", "ct", "ht", "mc", "im", ...}); cells with no value are merged/image cells."""
    if isinstance(c, dict):
        v = c.get("value", c.get("v", ""))
        return v if not isinstance(v, (list, dict)) else json.dumps(v)
    return c


def _is_row(r):
    return isinstance(r, list) and r and all(isinstance(c, (dict, str, int, float, type(None))) for c in r) \
        and any(isinstance(c, dict) and ("value" in c or "v" in c) or isinstance(c, (str, int, float)) for c in r)


def tables(obj, path="", out=None):
    """Find 2-D arrays (rows of scalar cells, or of {"value": ...} cells) anywhere in the JSON."""
    out = [] if out is None else out
    if isinstance(obj, list) and len(obj) >= 2 and all(_is_row(r) for r in obj):
        out.append((path, [[_cell(c) for c in r] for r in obj]))
        return out
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            tables(v, f"{path}[{i}]", out)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            tables(v, f"{path}.{k}", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="market_reports")
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--owner", default="CBRE (Infogram embed)")
    ap.add_argument("--parent-url", required=True)
    ap.add_argument("--access-date", default=date.today().isoformat())
    ap.add_argument("--reextract", action="store_true", help="re-parse JSON already saved; no fetch, no manifest row")
    ap.add_argument("ids", nargs="*")
    a = ap.parse_args()
    out = RAW / a.group / a.access_date / f"{a.prefix}_infogram"
    out.mkdir(parents=True, exist_ok=True)
    if a.reextract:
        for jpath in sorted(out.glob("*.json")):
            d = json.loads(jpath.read_text())
            for old in out.glob(jpath.stem + "_table*.csv"):
                old.unlink()
            for i, (pth, rows) in enumerate(tables(d), 1):
                tp = out / f"{jpath.stem}_table{i}.csv"
                with tp.open("w", newline="") as f:
                    csv.writer(f).writerows(rows)
                print(f"{tp.name}: {len(rows)} rows <- {pth}")
        return 0
    for n, eid in enumerate(a.ids, 1):
        url = f"https://e.infogram.com/{eid}"
        r = requests.get(url, headers={"User-Agent": UA}, timeout=90)
        m = re.search(r"window\.infographicData\s*=\s*(\{.*?\});\s*</script>", r.text, re.S)
        if not m:
            print(f"{eid}: no infographicData (status {r.status_code})"); continue
        d = json.loads(m.group(1))
        title = re.sub(r"[^A-Za-z0-9]+", "_", str(d.get("title", "untitled"))).strip("_")[:60]
        jpath = out / f"fig{n}_{title}_{eid}.json"
        jpath.write_text(json.dumps(d, indent=1))
        tabs = tables(d)
        tpaths = []
        for i, (p, rows) in enumerate(tabs, 1):
            tp = out / f"fig{n}_{title}_{eid}_table{i}.csv"
            with tp.open("w", newline="") as f:
                csv.writer(f).writerows(rows)
            tpaths.append((p, tp, len(rows)))
        print(f"fig{n} '{d.get('title')}' ({eid}): {len(tabs)} tables")
        for p, tp, nrows in tpaths:
            print(f"    {tp.name}: {nrows} rows  <- json path {p}")
        _append_row(MANIFEST, MANIFEST_FIELDS, {
            "source_id": f"{a.prefix}_infogram_fig{n}", "group": a.group, "owner": a.owner,
            "title": f"{a.prefix}: figure {n} '{d.get('title')}' Infogram data (JSON + {len(tabs)} extracted CSV tables)",
            "url": url, "final_url": a.parent_url, "filename": jpath.name, "local_path": str(jpath.relative_to(RAW.parent.parent)),
            "access_date": a.access_date, "sha256": hashlib.sha256(jpath.read_bytes()).hexdigest(), "bytes": jpath.stat().st_size,
            "http_status": str(r.status_code), "content_type": "application/json", "tags": "vintage;embed",
            "notes": f"Embedded in {a.parent_url}; tables extracted heuristically (2-D arrays in the JSON)."})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
