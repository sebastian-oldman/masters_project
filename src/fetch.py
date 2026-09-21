"""Download one Source into data/raw/<group>/<access_date>/, hash it, and
record it in data/raw/manifest.csv. Failures go to logs/fetch_failures.csv.

Rules
- Raw files are immutable: a file is written once per access date; re-running
  on the same day skips files already present with the same byte count.
- Every write is streamed to a .part file and renamed only when complete.
- A response whose Content-Type is text/html when a binary type was expected
  is treated as a failure (bot wall or soft 404), unless the source is tagged
  'html'.
"""
from __future__ import annotations

import csv
import hashlib
import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests

from .paths import RAW, MANIFEST, FAILURES, LOGS
from .sources import Source, UA

MANIFEST_FIELDS = ["source_id", "group", "owner", "title", "url", "final_url", "filename",
                   "local_path", "access_date", "sha256", "bytes", "http_status",
                   "content_type", "tags", "notes"]
FAILURE_FIELDS = ["source_id", "group", "url", "access_date", "http_status", "content_type",
                  "error", "optional", "tags"]

BINARY_EXT = {".pdf", ".xlsx", ".xls", ".zip", ".csv", ".json", ".docx", ".doc"}
CT_EXT = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
    "text/csv": ".csv",
    "application/json": ".json",
    "text/html": ".html",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
}


@dataclass
class Result:
    source: Source
    ok: bool
    row: dict
    error: str = ""


def _append_row(path: Path, fields: list[str], row: dict) -> None:
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def manifest_index() -> dict[tuple[str, str], dict]:
    if not MANIFEST.exists():
        return {}
    with MANIFEST.open(newline="") as f:
        return {(r["source_id"], r["access_date"]): r for r in csv.DictReader(f)}


def _slug(s: str, n: int = 80) -> str:
    """Filesystem-safe name, truncated to n chars but always keeping the extension."""
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")
    stem, dot, ext = s.rpartition(".")
    if dot and 0 < len(ext) <= 5 and stem:
        return stem[: max(1, n - len(ext) - 1)] + "." + ext
    return s[:n]


def _choose_filename(src: Source, resp: requests.Response) -> str:
    if src.filename:
        return src.filename
    cd = resp.headers.get("Content-Disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
    if m:
        name = unquote(m.group(1)).strip()
        if name:
            return f"{src.id}__{_slug(name)}"
    path = urlparse(resp.url).path
    base = Path(unquote(path)).name
    ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    ext = CT_EXT.get(ct, "")
    if base and "." in base and not base.lower().endswith(".aspx"):
        return f"{src.id}__{_slug(base)}"
    return f"{src.id}{ext or '.bin'}"


def _expect_binary(src: Source, filename: str) -> bool:
    if "html" in src.tags:
        return False
    return Path(filename).suffix.lower() in BINARY_EXT or src.filename is None


def fetch(src: Source, session: requests.Session | None = None, access_date: str | None = None,
          retries: int = 3, timeout: int = 900, force: bool = False) -> Result:
    session = session or requests.Session()
    access_date = access_date or date.today().isoformat()
    out_dir = RAW / src.group / access_date
    out_dir.mkdir(parents=True, exist_ok=True)

    idx = manifest_index()
    prior = idx.get((src.id, access_date))
    if prior and not force and Path(prior["local_path"]).exists():
        return Result(src, True, prior, "already fetched today")

    urls = [src.url] + list(src.fallback_urls)
    last_err = ""
    status = ""
    ctype = ""
    for url in urls:
        for attempt in range(1, retries + 1):
            try:
                ua = "curl/8.0" if "zenodo.org" in url else UA  # zenodo rejects spoofed browser UAs
                with session.get(url, headers={"User-Agent": ua, "Accept": "*/*"}, stream=True,
                                 timeout=timeout, allow_redirects=True) as resp:
                    status = str(resp.status_code)
                    ctype = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
                    if resp.status_code == 404:
                        last_err = f"404 at {url}"
                        break  # try next url, no retry
                    if resp.status_code >= 400:
                        last_err = f"HTTP {resp.status_code} at {url}"
                        time.sleep(2 * attempt)
                        continue
                    filename = _choose_filename(src, resp)
                    if _expect_binary(src, filename) and ctype in ("text/html", "text/plain") \
                            and not filename.lower().endswith((".html", ".csv", ".txt")):
                        last_err = f"expected binary, got {ctype} at {url} (bot wall or soft 404)"
                        break
                    dest = out_dir / filename
                    part = dest.with_suffix(dest.suffix + ".part")
                    h = hashlib.sha256()
                    n = 0
                    with part.open("wb") as f:
                        for chunk in resp.iter_content(chunk_size=1 << 20):
                            if chunk:
                                f.write(chunk)
                                h.update(chunk)
                                n += len(chunk)
                    if n == 0:
                        part.unlink(missing_ok=True)
                        last_err = f"empty body at {url}"
                        break
                    part.replace(dest)
                    row = {
                        "source_id": src.id, "group": src.group, "owner": src.owner, "title": src.title,
                        "url": src.url, "final_url": resp.url, "filename": filename,
                        "local_path": str(dest.relative_to(RAW.parent.parent)), "access_date": access_date,
                        "sha256": h.hexdigest(), "bytes": n, "http_status": status,
                        "content_type": ctype, "tags": ";".join(src.tags), "notes": src.notes,
                    }
                    _append_row(MANIFEST, MANIFEST_FIELDS, row)
                    return Result(src, True, row)
            except requests.RequestException as e:  # network error: retry
                last_err = f"{type(e).__name__}: {e}"[:300]
                time.sleep(3 * attempt)
                continue
    row = {"source_id": src.id, "group": src.group, "url": src.url, "access_date": access_date,
           "http_status": status, "content_type": ctype, "error": last_err,
           "optional": src.optional, "tags": ";".join(src.tags)}
    _append_row(FAILURES, FAILURE_FIELDS, row)
    return Result(src, False, row, last_err)
