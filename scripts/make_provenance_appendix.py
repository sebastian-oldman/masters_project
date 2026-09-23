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
from src.provenance import FREEZE_DATE, figure_manifest_ids, source_line  # noqa: E402

OUT = ROOT / "report" / "tables"
MAN = pd.read_csv(RAW / "manifest.csv").sort_values("access_date").groupby("source_id").tail(1).set_index("source_id")


def esc(s):
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_\allowbreak{}").replace("#", r"\#")


def bown(o):
    """Owner text with break points after slashes, dots and colons and inside long digit runs (Wayback capture ids, DOIs)."""
    import re as _re
    t = esc(str(o))
    for ch in ("/", ".", ":"):
        t = t.replace(ch, ch + r"\allowbreak{}")
    return _re.sub(r"(\d{5})(?=\d)", r"\1\\allowbreak{}", t)


def burl(u):
    """A URL in typewriter type that may break after every slash, dot, hyphen or equals sign."""
    t = esc(str(u)).replace("~", r"\textasciitilde{}")
    for ch in ("/", ".", "-", "=", "?", ":", r"\%", r"\&"):
        t = t.replace(ch, ch + r"\allowbreak{}")
    return r"\texttt{" + t + "}"


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
    # every raw-source label must resolve to manifest ids in the frozen manifest; then print the rows behind the figures (Appendix B)
    frozen = RAW / f"manifest_frozen_{FREEZE_DATE}.csv"
    fm = (pd.read_csv(frozen) if frozen.exists() else pd.read_csv(RAW / "manifest.csv")).sort_values("access_date").groupby("source_id").tail(1).set_index("source_id")
    used = {}
    for ch, rows in ROWS.items():
        for fig, *_ in rows:
            try:
                for i in figure_manifest_ids(fig, fm.index):
                    used.setdefault(i, set()).add(fig)
            except (KeyError, RecursionError) as e:
                problems.append(f"{fig}: {e}")
    if problems:
        print("PROBLEMS:", problems); return 1
    rows_out = [{"source_id": i, "figures": " ".join(sorted(f)), "owner": fm.loc[i, "owner"], "access_date": fm.loc[i, "access_date"], "sha256": fm.loc[i, "sha256"], "url": fm.loc[i, "url"], "bytes": int(fm.loc[i, "bytes"]) if pd.notna(fm.loc[i, "bytes"]) else None} for i, f in sorted(used.items())]
    df = pd.DataFrame(rows_out); df.to_csv(PROCESSED / "ch5_manifest_rows_used.csv", index=False)
    # group ids that share a stem and a figure set into one line when there are more than 12 of them; list the rest individually
    import re as _re
    df["stem"] = df.source_id.str.replace(r"_?(20\d\d|\d{4}q[1-4]|\d{4}_\d{2}|\d{4}_(jan_jun|jul_dec)).*$", "", regex=True)
    colr = r"\begin{longtable}{>{\raggedright\arraybackslash}p{3.0cm}>{\raggedright\arraybackslash}p{1.5cm}>{\raggedright\arraybackslash}p{1.4cm}>{\raggedright\arraybackslash}p{2.0cm}>{\raggedright\arraybackslash}p{6.0cm}}"
    lines = [colr, r"\caption{Manifest rows behind the figures: every source id named in a figure's source line, with owner, access date, SHA-256 (first 12 hex digits) and URL; groups of dated files are listed on one line with their count and the URL of the first file. The frozen manifest holds every row in full.}\\", r"\toprule", r"Manifest id (figures) & Owner & Access date & SHA-256 & URL \\", r"\midrule", r"\endfirsthead", r"\toprule", r"Manifest id (figures) & Owner & Access date & SHA-256 & URL \\", r"\midrule", r"\endhead"]
    n_lines = 0
    for stem, g in df.groupby("stem", sort=True):
        g = g.sort_values("source_id")
        if len(g) > 12:
            first, last = g.iloc[0], g.iloc[-1]
            lines.append(f"{esc(first.source_id)} to {esc(last.source_id)} ({len(g)} files; figures {esc(' '.join(sorted(set(' '.join(g.figures).split()))))}) & {bown(first.owner)} & {esc(first.access_date)} to {esc(g.access_date.max())} & {esc(str(first.sha256)[:12])} (first file) & {burl(first.url)} (first file) \\\\"); n_lines += 1
        else:
            for r in g.itertuples():
                lines.append(f"{esc(r.source_id)} ({esc(r.figures)}) & {bown(r.owner)} & {esc(r.access_date)} & {esc(str(r.sha256)[:12])} & {burl(r.url)} \\\\"); n_lines += 1
    lines += [r"\bottomrule", r"\end{longtable}"]
    (OUT / "manifest_rows_used.tex").write_text("\n".join(lines))
    print(f"all referenced figures and processed files exist; {len(df)} manifest ids resolve behind the figures ({n_lines} table lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
