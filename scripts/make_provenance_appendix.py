#!/usr/bin/env python
"""Write report/tables/provenance_ch{1,2,3}.tex: for every figure, the processed files it is drawn from, the raw sources
(manifest ids) behind those files, and the code that produces them. The appendix section report/sections/07_appendix_provenance.tex
inputs these tables. Rows are checked against the file system: every processed file and figure named here must exist."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402

from src.paths import FIGURES, PROCESSED, RAW, ROOT  # noqa: E402
from src.provenance import source_line  # noqa: E402

OUT = ROOT / "report" / "tables"
MAN = pd.read_csv(RAW / "manifest.csv").sort_values("access_date").groupby("source_id").tail(1).set_index("source_id")


def esc(s):
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_\allowbreak{}").replace("#", r"\#")


from src.provenance import ROWS  # noqa: E402


def main() -> int:
    problems = []
    for ch, rows in ROWS.items():
        lines = [r"\begin{tabular}{lp{4.6cm}p{5.2cm}p{4.6cm}p{4.8cm}}", r"\toprule", r"Figure & Content & Processed files (data/processed) & Raw sources (manifest ids) & Code \\", r"\midrule"]
        for fig, what, files, raws, code in rows:
            if not list(FIGURES.glob(f"{fig}_*.png")):
                problems.append(f"missing figure {fig}")
            for f in files:
                if not (PROCESSED / f).exists():
                    problems.append(f"missing processed file {f}")
            lines.append(f"{esc(fig)} & {esc(what)} & " + esc("; ".join(files)) + " & " + esc("; ".join(raws)) + " & " + esc(code) + r" \\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        (OUT / f"provenance_ch{ch}.tex").write_text("\n".join(lines)); print("  table", f"provenance_ch{ch}")
        for fig, what, files, raws, code in rows:
            (OUT / f"figsrc_{fig}.tex").write_text("{\\scriptsize\\textit{Source line:} " + esc(source_line(fig)) + "}")
    if problems:
        print("PROBLEMS:", problems); return 1
    print("all referenced figures and processed files exist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
