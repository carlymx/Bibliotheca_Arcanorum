#!/usr/bin/env bash
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"
MAIN_PY="$APP_DIR/main.py"
REQUIREMENTS="$APP_DIR/requirements.txt"

# ── Colores (si el terminal los soporta) ──
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
fi

info()  { printf "${CYAN}%s${NC}\n" "$*"; }
ok()    { printf "${GREEN}✓ %s${NC}\n" "$*"; }
warn()  { printf "${YELLOW}⚠ %s${NC}\n" "$*"; }
error() { printf "${RED}✗ %s${NC}\n" "$*"; exit 1; }

# ── flags ──
RESET_VENV=false
for arg in "$@"; do
    if [ "$arg" = "--reset-venv" ]; then RESET_VENV=true; fi
done

# ── 1. Detectar SO ──
OS="$(uname -s)"
case "$OS" in
    Linux*)  OS_NAME="linux"  ;;
    Darwin*) OS_NAME="darwin" ;;
    CYGWIN*|MINGW*|MSYS*) OS_NAME="windows" ;;
    *)       error "Sistema operativo no soportado: $OS" ;;
esac
info "[1/8] Sistema detectado: $OS_NAME"

# ── 2. Localizar Python ──
if [ "$OS_NAME" = "windows" ]; then
    PYTHON="python"
else
    PYTHON="python3"
fi

if command -v "$PYTHON" >/dev/null 2>&1; then
    ok "Python: $($PYTHON --version 2>&1)"
else
    # Fallback a python
    PYTHON="python"
    if ! command -v "$PYTHON" >/dev/null 2>&1; then
        error "Python no encontrado. Instala Python 3.8+."
    fi
    ok "Python: $($PYTHON --version 2>&1)"
fi

# ── 3. Validar version (3.8+) ──
PY_MAJOR=$($PYTHON -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$($PYTHON -c 'import sys; print(sys.version_info.minor)')
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    error "Se requiere Python 3.8+ (versión actual: $PY_MAJOR.$PY_MINOR)"
fi
ok "Versión: $PY_MAJOR.$PY_MINOR"

# ── 4. Chequear Tkinter del sistema (Linux) ──
if [ "$OS_NAME" = "linux" ]; then
    if ! $PYTHON -c "import tkinter" 2>/dev/null; then
        # Detectar distro para dar el comando correcto
        if command -v apt >/dev/null 2>&1; then
            PKG="python3-tk"
        elif command -v dnf >/dev/null 2>&1; then
            PKG="python3-tkinter"
        elif command -v pacman >/dev/null 2>&1; then
            PKG="tk"
        elif command -v zypper >/dev/null 2>&1; then
            PKG="python3-tk"
        else
            PKG="python3-tk (o su equivalente en tu distro)"
        fi
        info ""
        warn "Tkinter no está instalado en el sistema."
        info "  Instálalo con:"
        info "    sudo apt install $PKG   (Debian/Ubuntu)"
        info "    sudo dnf install $PKG   (Fedora)"
        info "    sudo pacman -S $PKG     (Arch)"
        info ""
        read -rp "¿Quieres intentar instalarlo ahora? [s/N] " REPLY
        if [ "$REPLY" = "s" ] || [ "$REPLY" = "S" ]; then
            if command -v apt >/dev/null 2>&1; then
                sudo apt install -y "$PKG" || error "No se pudo instalar $PKG"
            elif command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y "$PKG" || error "No se pudo instalar $PKG"
            elif command -v pacman >/dev/null 2>&1; then
                sudo pacman -S --noconfirm "$PKG" || error "No se pudo instalar $PKG"
            else
                error "No se pudo determinar el gestor de paquetes. Instala $PKG manualmente."
            fi
            ok "Tkinter instalado"
        else
            error "Tkinter es necesario para la aplicación. Instálalo manualmente."
        fi
    else
        ok "Tkinter del sistema disponible"
    fi
fi

# ── 5. Crear / resetear venv ──
if [ "$RESET_VENV" = true ] && [ -d "$VENV_DIR" ]; then
    info "  --reset-venv: eliminando venv existente..."
    rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
    info "[5/8] Creando entorno virtual..."
    if [ "$OS_NAME" = "linux" ]; then
        $PYTHON -m venv --system-site-packages "$VENV_DIR"
    else
        $PYTHON -m venv "$VENV_DIR"
    fi
    ok "Entorno virtual creado"
else
    ok "Entorno virtual ya existe"
fi

# ── Activar venv ──
if [ "$OS_NAME" = "windows" ]; then
    ACTIVATE="$VENV_DIR/Scripts/activate"
else
    ACTIVATE="$VENV_DIR/bin/activate"
fi
# shellcheck disable=SC1090
source "$ACTIVATE"

# ── 6. Instalar dependencias ──
if [ -f "$REQUIREMENTS" ]; then
    info "[6/8] Verificando dependencias..."
    pip install --quiet --upgrade -r "$REQUIREMENTS" 2>&1 | tail -1
    ok "Dependencias OK"
fi

# ── 7. Chequear dependencias del sistema (pdftoppm, mutagen, sv-ttk) ──
info "[7/8] Comprobando herramientas del sistema..."
DEP_FALTANTES=()
command -v pdftoppm >/dev/null 2>&1 || DEP_FALTANTES+=("pdftoppm (poppler-utils)")
if [ ${#DEP_FALTANTES[@]} -gt 0 ]; then
    echo ""
    warn "Faltan herramientas del sistema necesarias:"
    for dep in "${DEP_FALTANTES[@]}"; do
        echo "  - $dep"
    done
    echo ""
    info "  Instálalas con:"
    info "    sudo apt install poppler-utils   # Debian/Ubuntu"
    info "    sudo pacman -S poppler            # Arch"
    info "    sudo dnf install poppler-utils    # Fedora"
    echo ""
    read -rp "¿Quieres intentar instalarlo ahora? [s/N] " REPLY
    if [ "$REPLY" = "s" ] || [ "$REPLY" = "S" ]; then
        if command -v apt >/dev/null 2>&1; then
            sudo apt install -y poppler-utils || warn "No se pudo instalar poppler-utils"
        elif command -v dnf >/dev/null 2>&1; then
            sudo dnf install -y poppler-utils || warn "No se pudo instalar poppler-utils"
        elif command -v pacman >/dev/null 2>&1; then
            sudo pacman -S --noconfirm poppler || warn "No se pudo instalar poppler"
        else
            warn "Instala poppler-utils manualmente."
        fi
        if command -v pdftoppm >/dev/null 2>&1; then
            ok "pdftoppm disponible"
        fi
    else
        warn "pdftoppm no disponible. La extracción de portadas PDF no funcionará."
    fi
else
    ok "pdftoppm disponible"
fi

# Chequear mutagen (Python)
if $PYTHON -c "import mutagen" 2>/dev/null; then
    ok "mutagen disponible"
else
    warn "mutagen no encontrado. Instalando..."
    pip install mutagen 2>&1 | tail -1
    if $PYTHON -c "import mutagen" 2>/dev/null; then
        ok "mutagen instalado"
    else
        warn "mutagen no se pudo instalar. La extracción de carátulas de audio no funcionará."
    fi
fi

# Chequear sv-ttk (tema moderno para Tkinter)
if $PYTHON -c "import sv_ttk" 2>/dev/null; then
    ok "sv-ttk disponible"
else
    warn "sv-ttk no encontrado. Instalando..."
    pip install sv-ttk 2>&1 | tail -1
    if $PYTHON -c "import sv_ttk" 2>/dev/null; then
        ok "sv-ttk instalado"
    else
        warn "sv-ttk no se pudo instalar. Los temas Sun Valley no estarán disponibles."
    fi
fi

# ── Ejecutar app ──
echo ""
info "◆  Iniciando Gestor de Biblioteca..."
exec "$PYTHON" "$MAIN_PY" "$@"
