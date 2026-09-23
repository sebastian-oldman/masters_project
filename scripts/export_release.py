#!/usr/bin/env python
"""Export the deliverables: the report PDF, the defense deck, every processed CSV and JSON, the figures, the LaTeX tables, the executed
notebooks, the frozen manifest and the docs, into release/consumption_gap_<date>/ with a CONTENTS.md listing every file and its SHA-256,
then zip the folder. Hourly parquet caches are left out (they are rebuilt by `make ch1`); the Monte Carlo draws parquet is included."""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.paths import FIGURES, PROCESSED, RAW, ROOT  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = ROOT / "release" / f"consumption_gap_{a.date}"
    if out.exists():
        shutil.rmtree(out)
    groups = {
        "report": [ROOT / "report" / "main.pdf"] + ([ROOT / "report" / "defense" / "defense.pdf"] if (ROOT / "report" / "defense" / "defense.pdf").exists() else []),
        "data_processed": sorted(PROCESSED.glob("ch*_*.csv")) + sorted(PROCESSED.glob("ch*_*.json")) + sorted(PROCESSED.glob("ch4_mc_draws.parquet")) + sorted(PROCESSED.glob("cec_*.csv")) + sorted(PROCESSED.glob("cbre_*.csv")),
        "figures": sorted(FIGURES.glob("fig*_*.png")) + sorted(FIGURES.glob("fig*_*.pdf")),
        "tables": sorted((ROOT / "report" / "tables").glob("*.tex")),
        "notebooks": sorted((ROOT / "notebooks").glob("0*.ipynb")),
        "manifest": [RAW / f"manifest_frozen_{a.date}.csv"],
        "docs": [ROOT / "docs" / n for n in ("DATA_FREEZE.md", "DATA_NOTES.md", "DATA_CATALOG.md", "PLAN.md")] + [ROOT / "README.md"],
        "report_source": sorted((ROOT / "report" / "sections").glob("*.tex")) + [ROOT / "report" / "main.tex", ROOT / "report" / "references.bib"],
    }
    rows = []
    for g, files in groups.items():
        for f in files:
            if not f.exists():
                print("  skip (missing)", f); continue
            dst = out / g / f.name; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, dst)
            rows.append((g, f.name, dst.stat().st_size, sha(dst)))
    lines = [f"# Contents of the {a.date} release", "", f"Report, defense deck, processed outputs, figures, tables, notebooks, frozen manifest and documentation exported from the repository at the data freeze of {a.date}. "
             "Every figure carries its source line (processed files, manifest ids, code); `manifest/manifest_frozen_*.csv` gives URL, access date and SHA-256 for every raw file.", "",
             "| Folder | File | Bytes | SHA-256 |", "|---|---|---:|---|"]
    lines += [f"| {g} | {n} | {b:,} | `{h}` |" for g, n, b, h in rows]
    (out / "CONTENTS.md").write_text("\n".join(lines) + "\n")
    zip_path = shutil.make_archive(str(out), "zip", root_dir=out.parent, base_dir=out.name)
    total = sum(b for _, _, b, _ in rows)
    print(f"exported {len(rows)} files ({total/1e6:.1f} MB) to {out} and {zip_path} ({Path(zip_path).stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
