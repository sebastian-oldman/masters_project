#!/usr/bin/env python
"""Assemble a tidy semiannual series for California markets from the CBRE Infogram tables.

Reads data/raw/market_reports/<date>/cbre_*_overview_infogram/*_table1.csv and
cbre_*_silicon_valley_infogram/*_table1.csv, writes data/processed/cbre_california_market_series.csv
(one row per edition x market x metric) so every value keeps its source file.
"""
from __future__ import annotations

import csv
import glob
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.paths import RAW, PROCESSED  # noqa: E402

MARKETS = {"silicon valley": "Silicon Valley", "southern california": "Southern California",
           "los angeles": "Los Angeles", "sacramento": "Sacramento"}
ORDER = {f"{h} {y}": (y, h) for y in range(2016, 2030) for h in ("H1", "H2")}


def num(v):
    v = str(v).replace(",", "").replace("$", "").replace("%", "").strip()
    m = re.match(r"^-?\d+(\.\d+)?", v)
    return float(m.group(0)) if m else None


def market_of(cell):
    return MARKETS.get(str(cell).strip().lower())


def parse_state_table(rows, edition, src, out):
    """Fig 1 / Fig 2: Market, Inventory, YoY, Available [/ Vacancy], [Vacancy], bps, Absorption, YoY, Rent."""
    for r in rows[1:]:
        mk = market_of(r[0]) if r else None
        if not mk:
            continue
        vals = [c.strip() for c in r[1:] if c.strip() != ""]
        if len(vals) < 5:
            continue
        inv, yoy_inv, third = vals[0], vals[1], vals[2]
        if "/" in third:  # "25.9 / 6.3%"
            avail, vac = [x.strip() for x in third.split("/", 1)]
            rest = vals[3:]
        else:
            avail, vac = third, vals[3]
            rest = vals[4:]
        bps, absorb, yoy_abs, rent = (rest + [None] * 4)[:4]
        for metric, val in (("inventory_mw", num(inv)), ("inventory_yoy_change_mw", num(yoy_inv)), ("available_mw", num(avail)),
                            ("vacancy_pct", num(vac)), ("vacancy_yoy_change_bps", num(bps)), ("net_absorption_mw", num(absorb)),
                            ("net_absorption_yoy_change_mw", num(yoy_abs)), ("rental_rate_kw_month", rent)):
            out.append({"edition": edition, "market": mk, "metric": metric, "value": val, "source_file": src})


def parse_uc_table(rows, edition, src, out):
    """',<ed> Total Inventory,<ed> Under Construction' tables."""
    for r in rows[1:]:
        mk = market_of(r[0]) if r else None
        if not mk or len(r) < 3:
            continue
        out.append({"edition": edition, "market": mk, "metric": "total_inventory_mw", "value": num(r[1]), "source_file": src})
        out.append({"edition": edition, "market": mk, "metric": "under_construction_mw", "value": num(r[2]), "source_file": src})


def parse_pct_table(rows, edition, src, out):
    for r in rows[1:]:
        mk = market_of(r[0]) if r else None
        if mk and len(r) >= 2:
            out.append({"edition": edition, "market": mk, "metric": "under_construction_yoy_change_pct", "value": num(r[1]), "source_file": src})


def parse_sv_history(rows, edition, src, out):
    """Silicon Valley chapter Fig 1: period, Under Construction, Preleased, New Deliveries, Vacancy."""
    hdr = [h.strip().lower() for h in rows[0]]
    if "under construction" not in hdr:
        return
    for r in rows[1:]:
        per = r[0].strip()
        if not re.match(r"^H[12] \d{4}$", per):
            continue
        for i, h in enumerate(hdr[1:], 1):
            if i < len(r):
                out.append({"edition": f"{edition} chapter history", "market": "Silicon Valley",
                            "metric": {"under construction": "under_construction_mw", "preleased": "preleased_mw",
                                       "new deliveries": "new_deliveries_mw", "vacancy": "vacancy_pct"}.get(h, h),
                            "value": num(r[i]), "period": per, "source_file": src})


def main() -> int:
    out = []
    for d in sorted(glob.glob(str(RAW / "market_reports" / "*" / "cbre_*_infogram"))):
        m = re.search(r"cbre_(h[12])_(\d{4})_(overview|silicon_valley)_infogram", d)
        if not m:
            continue
        edition = f"{m.group(1).upper()} {m.group(2)}"
        kind = m.group(3)
        for f in sorted(glob.glob(d + "/*_table1.csv")):
            rows = list(csv.reader(open(f)))
            if not rows or not rows[0]:
                continue
            hdr = ",".join(rows[0]).lower()
            src = str(Path(f).relative_to(RAW.parent.parent))
            if kind == "silicon_valley":
                parse_sv_history(rows, edition, src, out)
            elif "under construction" in hdr and "inventory" in hdr:
                parse_uc_table(rows, edition, src, out)
            elif "% change" in hdr:
                parse_pct_table(rows, edition, src, out)
            elif hdr.startswith("market") and "inventory" in hdr:
                parse_state_table(rows, edition, src, out)
    for r in out:
        r.setdefault("period", r["edition"].split(" chapter")[0])
    out.sort(key=lambda r: (r["market"], ORDER.get(r["period"], (0, "")), r["metric"]))
    dest = PROCESSED / "cbre_california_market_series.csv"
    with dest.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["market", "period", "metric", "value", "edition", "source_file"])
        w.writeheader(); w.writerows(out)
    print(f"{len(out)} rows -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
