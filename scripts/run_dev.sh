#!/usr/bin/env bash
# 開發用啟動腳本：建立虛擬環境（如尚未建立）、安裝相依套件、啟動 API。
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
exec uvicorn app.main:app --reload --port 8000
