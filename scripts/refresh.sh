#!/usr/bin/env bash
set -euo pipefail
cd /workspace/Analysis_Company
result=0
.venv/bin/python -m economic_reality update "$@" || result=$?
.venv/bin/python -m economic_reality export
.venv/bin/python -m economic_reality report
exit "$result"
