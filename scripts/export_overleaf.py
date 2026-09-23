#!/usr/bin/env python
"""Package the report, the advisor memo and the defense deck as one Overleaf-ready project: release/overleaf_consumption_gap_<date>.zip.
All three documents share figures/ and references.bib; graphicspath is rewritten to the flat project layout. Overleaf compiles
main.tex by default; the memo (brief.tex) and the deck (defense.tex) are selected as the main document from the Overleaf menu."""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.paths import FIGURES, ROOT  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = ROOT / "release" / f"overleaf_consumption_gap_{a.date}"
    if out.exists():
        shutil.rmtree(out)
    (out / "figures").mkdir(parents=True); (out / "sections").mkdir(); (out / "tables").mkdir()
    main_tex = (ROOT / "report" / "main.tex").read_text().replace("\\graphicspath{{../figures/}}", "\\graphicspath{{figures/}}")
    (out / "main.tex").write_text(main_tex)
    for f in (ROOT / "report" / "sections").glob("*.tex"):
        shutil.copy2(f, out / "sections" / f.name)
    for f in (ROOT / "report" / "tables").glob("*.tex"):
        shutil.copy2(f, out / "tables" / f.name)
    shutil.copy2(ROOT / "report" / "references.bib", out / "references.bib")
    for f in sorted(FIGURES.glob("fig*.pdf")) + sorted(FIGURES.glob("fig*.png")):
        shutil.copy2(f, out / "figures" / f.name)
    briefs = sorted((ROOT / "report" / "brief").glob("advisor_brief_*.tex"))
    if briefs:
        b = briefs[-1].read_text().replace("\\graphicspath{{../../figures/}}", "\\graphicspath{{figures/}}"); (out / "brief.tex").write_text(b)
    d = (ROOT / "report" / "defense" / "defense.tex").read_text().replace("\\graphicspath{{../../figures/}}", "\\graphicspath{{figures/}}"); (out / "defense.tex").write_text(d)
    (out / "README_OVERLEAF.md").write_text(f"""# Overleaf project: Mapping the Consumption Gap ({a.date})

Upload this zip as a new Overleaf project (New Project > Upload Project). Three documents share the same figures and bibliography:

- `main.tex`: the report (compiles by default; pdfLaTeX with BibTeX, both run automatically by Overleaf).
- `brief.tex`: the progress memo for the advisor. Select it as the main document in Menu > Settings > Main document, then Recompile.
- `defense.tex`: the 21-slide beamer deck; select it the same way.

Figures are in `figures/` (PDF and PNG of each), tables in `tables/`, chapter sources in `sections/`. Every figure carries its source line;
Appendix B of the report lists the manifest rows (URL, access date, SHA-256) behind every source id. The raw and processed data stay in the
repository and are not needed to read or compile any of the three documents.
""")
    zip_path = shutil.make_archive(str(out), "zip", root_dir=out.parent, base_dir=out.name)
    n = sum(1 for _ in out.rglob("*") if _.is_file()); print(f"Overleaf project: {n} files in {out}; zip {Path(zip_path).name} ({Path(zip_path).stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
