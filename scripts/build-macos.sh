#!/usr/bin/env bash
# build-macos.sh — Construye Gestor_biblioteca.app + .dmg
set -euo pipefail

if ! command -v pdftoppm &>/dev/null; then
    echo "Instalando poppler..."
    brew install poppler
fi
PDFTOPPM=$(which pdftoppm)

pyinstaller build.spec \
    --add-binary "$PDFTOPPM:." \
    --collect-all sv_ttk \
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

create-dmg \
    --volname "Gestor_biblioteca" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "Gestor_biblioteca.app" 180 120 \
    --app-drop-link 420 120 \
    "dist/Gestor_biblioteca.dmg" \
    "$APP"
