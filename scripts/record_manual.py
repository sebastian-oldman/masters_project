#!/usr/bin/env python
"""Record a file obtained outside fetch.py (hand download, browser capture) in data/raw/manifest.csv.

Example:
  python scripts/record_manual.py --id cbre_h1_2026_pdf --group market_reports --owner CBRE \
      --title "North America Data Center Trends H1 2026 (PDF, downloaded by hand)" \
      --url https://www.cbre.com/insights/books/north-america-data-center-trends-h1-2026 \
      --file data/raw/market_reports/2026-09-21/cbre_h1_2026.pdf --tags manual
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.fetch import _append_row, MANIFEST_FIELDS  # noqa: E402
from src.paths import MANIFEST, ROOT  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    for k in ("id", "group", "owner", "title", "url", "file"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--notes", default="")
    ap.add_argument("--tags", default="manual")
    ap.add_argument("--access-date", default=date.today().isoformat())
    ap.add_argument("--content-type", default="")
    a = ap.parse_args()
    p = Path(a.file)
    if not p.is_absolute():
        p = ROOT / p
    data = p.read_bytes()
    _append_row(MANIFEST, MANIFEST_FIELDS, {
        "source_id": a.id, "group": a.group, "owner": a.owner, "title": a.title, "url": a.url, "final_url": a.url,
        "filename": p.name, "local_path": str(p.relative_to(ROOT)), "access_date": a.access_date,
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "http_status": "manual",
        "content_type": a.content_type or {"pdf": "application/pdf", "txt": "text/plain", "html": "text/html",
                                            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}.get(p.suffix.lstrip("."), ""),
        "tags": a.tags, "notes": a.notes})
    print(f"recorded {a.id}: {len(data):,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
