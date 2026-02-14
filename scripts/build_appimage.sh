#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="WhatsAppClient"
APP_DIR="${ROOT_DIR}/AppDir"
ICON_SRC="${ROOT_DIR}/whatsapp_icon.png"
SPEC_FILE="${ROOT_DIR}/WhatsAppClient.spec"

mkdir -p "${ROOT_DIR}/dist"

pyinstaller --clean "${SPEC_FILE}"

rm -rf "${APP_DIR}"
mkdir -p "${APP_DIR}/usr/bin"
mkdir -p "${APP_DIR}/usr/share/icons/hicolor/256x256/apps"

cp "${ROOT_DIR}/dist/${APP_NAME}" "${APP_DIR}/usr/bin/${APP_NAME}"
cp "${ICON_SRC}" "${APP_DIR}/usr/share/icons/hicolor/256x256/apps/whatsapp.png"
cp "${ICON_SRC}" "${APP_DIR}/whatsapp.png"
cp "${ROOT_DIR}/packaging/AppRun" "${APP_DIR}/AppRun"
cp "${ROOT_DIR}/packaging/WhatsAppClient.desktop" "${APP_DIR}/WhatsAppClient.desktop"

chmod +x "${APP_DIR}/AppRun"

if command -v appimagetool >/dev/null 2>&1; then
  appimagetool "${APP_DIR}"
else
  echo "appimagetool not found. Install it and run: appimagetool AppDir"
fi
