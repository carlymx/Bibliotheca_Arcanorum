#!/usr/bin/env bash
# build-linux.sh — Construye Gestor_biblioteca + AppImage
set -euo pipefail

export PDFTOPPM=$(which pdftoppm)

pyinstaller build.spec \
    --distpath dist \
    --workpath build

APPDIR="dist/AppDir"
mkdir -p "$APPDIR/usr/bin"

if [ -d "dist/Gestor_biblioteca.app" ]; then
    cp -r dist/Gestor_biblioteca.app/* "$APPDIR/usr/bin/"
elif [ -d "dist/Gestor_biblioteca" ]; then
    cp -r dist/Gestor_biblioteca/* "$APPDIR/usr/bin/"
elif [ -f "dist/Gestor_biblioteca" ]; then
    cp dist/Gestor_biblioteca "$APPDIR/usr/bin/"
else
    echo "ERROR: no se encuentra el ejecutable en dist/"
    exit 1
fi

cat > "$APPDIR/gestor_biblioteca.desktop" <<EOF
[Desktop Entry]
Name=Gestor biblioteca
Comment=Gestor del catálogo de la biblioteca
Exec=Gestor_biblioteca
Icon=gestor_biblioteca
Type=Application
Categories=Office;
Terminal=false
EOF

if [ -f "assets/icon.png" ]; then
    cp assets/icon.png "$APPDIR/gestor_biblioteca.png"
fi

wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" \
    -O /tmp/appimagetool
chmod +x /tmp/appimagetool

ARCH=x86_64 /tmp/appimagetool "$APPDIR" "dist/Gestor_biblioteca-x86_64.AppImage"

rm -rf "$APPDIR"
