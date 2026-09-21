from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
SNAPSHOTS = DATA / "snapshots"
FIGURES = ROOT / "figures"
LOGS = ROOT / "logs"
MANIFEST = RAW / "manifest.csv"
FAILURES = LOGS / "fetch_failures.csv"

for _p in (RAW, PROCESSED, SNAPSHOTS, FIGURES, LOGS):
    _p.mkdir(parents=True, exist_ok=True)
