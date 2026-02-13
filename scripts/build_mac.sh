#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="WhatsAppClient"
ICON_SRC="${ROOT_DIR}/whatsapp_icon.png"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller not found. Install it first: pip install -r requirements.txt"
  exit 1
fi

pyinstaller \
  --name "${APP_NAME}" \
  --windowed \
  --icon "${ICON_SRC}" \
  "${ROOT_DIR}/main.py"
