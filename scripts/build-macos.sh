#!/usr/bin/env bash
# build-macos.sh — Construye Gestor_biblioteca.app + .dmg
# MACOS_ARCH debe estar definido (arm64 | x86_64) o se detecta automáticamente
set -euo pipefail

ARCH="${MACOS_ARCH:-$(uname -m)}"
export MACOS_ARCH="$ARCH"

if ! command -v pdftoppm &>/dev/null; then
    echo "Instalando poppler..."
    brew install poppler
fi
export PDFTOPPM=$(which pdftoppm)

pyinstaller build.spec \
    --distpath dist \
    --workpath build

APP="dist/Gestor_biblioteca.app"
if [ ! -d "$APP" ]; then
    echo "ERROR: no se encontró $APP"
    exit 1
fi

if ! command -v create-dmg &>/dev/null; then
    echo "Instalando create-dmg..."
    brew install create-dmg
fi

DMG_NAME="Gestor_biblioteca-${ARCH}.dmg"

create-dmg \
    --volname "Gestor_biblioteca" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "Gestor_biblioteca.app" 180 120 \
    --app-drop-link 420 120 \
    "dist/${DMG_NAME}" \
    "$APP"
