#!/bin/sh
# Installs a crontab entry that runs the monthly snapshot at 09:00 on the 1st of each month.
# Review the line below, then run:  sh scripts/install_snapshot_cron.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LINE="0 9 1 * * cd $ROOT && ./.venv/bin/python scripts/snapshot.py >> logs/snapshot_cron.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'scripts/snapshot.py' ; echo "$LINE" ) | crontab -
echo "installed:"; crontab -l | grep snapshot.py
