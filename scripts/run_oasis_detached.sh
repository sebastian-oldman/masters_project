#!/bin/sh
# Detached OASIS LMP fetch (DLAPs first, then hubs). Safe to re-run: completed months are skipped.
cd "$(dirname "$0")/.." || exit 1
LOG=logs/fetch_caiso_oasis_$(date +%F)_detached.log
nohup sh -c './.venv/bin/python scripts/fetch_caiso_oasis.py --nodes dlap --start 2023-07 --end 2026-09; ./.venv/bin/python scripts/fetch_caiso_oasis.py --nodes hubs --start 2023-07 --end 2026-09; echo EXIT=$?' >> "$LOG" 2>&1 &
echo "started, pid $! -> $LOG"
