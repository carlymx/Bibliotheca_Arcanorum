#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# extractor_de_portadas.sh
# Extrae portadas de PDFs y redimensiona imágenes,
# manteniendo la estructura de directorios.
# ─────────────────────────────────────────────────────────────

readonly VERSION="1.1.0"

# Colores
readonly C_VERDE='\033[0;32m'
readonly C_AMARILLO='\033[1;33m'
readonly C_ROJO='\033[0;31m'
readonly C_CYAN='\033[0;36m'
readonly C_GRIS='\033[0;90m'
readonly C_NEGRITA='\033[1m'
readonly C_RESET='\033[0m'

log_info()  { echo -e "${C_VERDE}[INFO]${C_RESET}  $*"; }
log_warn()  { echo -e "${C_AMARILLO}[WARN]${C_RESET}  $*"; }
log_error() { echo -e "${C_ROJO}[ERROR]${C_RESET} $*"; }
log_step()  { echo -e "${C_CYAN}[  >>]${C_RESET} $*"; }

# ── Helper: leer con valor por defecto ──
read_default() {
    local prompt="$1"
    local default="$2"
    local input
    read -r -p "$(echo -e "${C_NEGRITA}${prompt}${C_RESET} [${default}]: ")" input
    echo "${input:-$default}"
}

# ── Helper: resolver tamaño ──
# Devuelve string para -resize de ImageMagick
resolver_resize() {
    local modo="$1" valor="$2"
    case "$modo" in
        original) echo "" ;;
        pct)      echo "${valor}%" ;;
        ancho)    echo "${valor}x" ;;
        alto)     echo "x${valor}" ;;
        *)        echo "" ;;
    esac
}

# ── Helper: conteo archivos ──
contar_archivos() {
    local dir="$1"
    local total=0
    local pdf=0 jpg=0 png=0 tiff=0 bmp=0 webp=0 gif=0
    local pdf_b=0 jpg_b=0 png_b=0 tiff_b=0 bmp_b=0 webp_b=0 gif_b=0
    local archivo ext ext_lower tam

    while IFS= read -r -d '' archivo; do
        ext="${archivo##*.}"
        ext_lower="$(echo "$ext" | tr '[:upper:]' '[:lower:]')"
        tam=$(stat -c%s "$archivo" 2>/dev/null || echo 0)
        total=$(( total + 1 ))
        case "$ext_lower" in
            pdf)      pdf=$(( pdf + 1 ));   pdf_b=$(( pdf_b + tam )) ;;
            jpg|jpeg) jpg=$(( jpg + 1 ));   jpg_b=$(( jpg_b + tam )) ;;
            png)      png=$(( png + 1 ));   png_b=$(( png_b + tam )) ;;
            tif|tiff) tiff=$(( tiff + 1 )); tiff_b=$(( tiff_b + tam )) ;;
            bmp)      bmp=$(( bmp + 1 ));   bmp_b=$(( bmp_b + tam )) ;;
            webp)     webp=$(( webp + 1 )); webp_b=$(( webp_b + tam )) ;;
            gif)      gif=$(( gif + 1 ));   gif_b=$(( gif_b + tam )) ;;
        esac
    done < <(find "$dir" -type f \( \
        -iname '*.pdf' -o \
        -iname '*.jpg' -o -iname '*.jpeg' -o \
        -iname '*.png' -o \
        -iname '*.tif' -o -iname '*.tiff' -o \
        -iname '*.bmp' -o \
        -iname '*.webp' -o \
        -iname '*.gif' \) -print0 2>/dev/null)

    echo "total=${total}"
    echo "pdf=${pdf}"
    echo "jpg=${jpg}"
    echo "png=${png}"
    echo "tiff=${tiff}"
    echo "bmp=${bmp}"
    echo "webp=${webp}"
    echo "gif=${gif}"
    echo "pdf_b=${pdf_b}"
    echo "jpg_b=${jpg_b}"
    echo "png_b=${png_b}"
    echo "tiff_b=${tiff_b}"
    echo "bmp_b=${bmp_b}"
    echo "webp_b=${webp_b}"
    echo "gif_b=${gif_b}"
}

fmt_bytes() {
    local bytes=$1
    if (( bytes < 1024 )); then echo "${bytes} B"
    elif (( bytes < 1048576 )); then echo "$(( bytes / 1024 )) KB"
    elif (( bytes < 1073741824 )); then echo "$(awk "BEGIN { printf \"%.1f\", $bytes / 1048576 }") MB"
    else echo "$(awk "BEGIN { printf \"%.2f\", $bytes / 1073741824 }") GB"
    fi
}

# ── Inicio ──
clear
echo -e "${C_NEGRITA}╔══════════════════════════════════════════════════════╗${C_RESET}"
echo -e "${C_NEGRITA}║${C_RESET}        extractor_de_portadas.sh  v${VERSION}            ${C_NEGRITA}║${C_RESET}"
echo -e "${C_NEGRITA}╚══════════════════════════════════════════════════════╝${C_RESET}"
echo ""

# ── Verificar dependencias ──
DEP_FALTANTES=()
command -v pdftoppm >/dev/null 2>&1 || DEP_FALTANTES+=("pdftoppm (poppler-utils)")
command -v convert  >/dev/null 2>&1 || DEP_FALTANTES+=("convert (ImageMagick)")
command -v identify >/dev/null 2>&1 || DEP_FALTANTES+=("identify (ImageMagick)")

if [[ ${#DEP_FALTANTES[@]} -gt 0 ]]; then
    log_error "Faltan dependencias:"
    for dep in "${DEP_FALTANTES[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo "Instálalas con:"
    echo "  sudo apt install poppler-utils imagemagick   # Debian/Ubuntu"
    echo "  sudo pacman -S poppler imagemagick           # Arch"
    echo "  sudo dnf install poppler-utils ImageMagick   # Fedora"
    exit 1
fi
log_info "Dependencias OK (pdftoppm, convert, identify)"

# ── 1. Directorios ──
echo ""
while true; do
    read -r -p "$(echo -e "${C_NEGRITA}Directorio ORIGEN${C_RESET}: ")" DIR_ORIGEN
    DIR_ORIGEN="${DIR_ORIGEN%/}"
    if [[ -z "$DIR_ORIGEN" ]]; then
        log_error "Debes indicar un directorio."
        continue
    fi
    if [[ ! -d "$DIR_ORIGEN" ]]; then
        log_error "El directorio '$DIR_ORIGEN' no existe."
        continue
    fi
    # Resolver ruta absoluta
    DIR_ORIGEN="$(realpath "$DIR_ORIGEN")"
    break
done

read -r -p "$(echo -e "${C_NEGRITA}Directorio DESTINO${C_RESET}: ")" DIR_DESTINO
DIR_DESTINO="${DIR_DESTINO%/}"
if [[ -z "$DIR_DESTINO" ]]; then
    log_error "Debes indicar un directorio destino."
    exit 1
fi
DIR_DESTINO="$(realpath -m "$DIR_DESTINO")"
mkdir -p "$DIR_DESTINO"

# ── 2. Página (solo PDF) ──
PAGINA_PDF=$(read_default "Página a extraer (PDF)" "1")

# ── 3. Formato de salida ──
echo ""
echo -e "  ${C_GRIS}Formatos disponibles:${C_RESET} png, jpg, tiff, bmp, webp, gif"
FORMATOS_VALIDOS=("png" "jpg" "tiff" "bmp" "webp" "gif")
while true; do
    FORMATO=$(read_default "Formato de salida" "jpg")
    FORMATO="${FORMATO,,}"
    for f in "${FORMATOS_VALIDOS[@]}"; do
        if [[ "$FORMATO" == "$f" ]]; then
            FORMATO_OK=1
            break
        fi
    done
    if [[ -n "${FORMATO_OK:-}" ]]; then break; fi
    log_error "Formato no válido. Usa: ${FORMATOS_VALIDOS[*]}"
done

# ── 4. Resolución ──
echo ""
echo -e "  ${C_GRIS}Opciones de resolución:${C_RESET}"
echo -e "    ${C_GRIS}O${C_RESET}  Original (sin escalar)"
echo -e "    ${C_GRIS}75${C_RESET}  Escalar al 75%"
echo -e "    ${C_GRIS}50${C_RESET}  Escalar al 50%"
echo -e "    ${C_GRIS}25${C_RESET}  Escalar al 25%"
echo -e "    ${C_GRIS}W 800${C_RESET}    Ancho fijo (ej: 800 px, alto proporcional)"
echo -e "    ${C_GRIS}H 600${C_RESET}    Alto fijo (ej: 600 px, ancho proporcional)"
echo ""

RESIZE_OPTS=""
RESOLUCION_MODO="original"
RESOLUCION_VALOR=""

while true; do
    read -r -p "$(echo -e "${C_NEGRITA}Resolución${C_RESET} [H 300]: ")" RES_INPUT
    RES_INPUT="${RES_INPUT:-H 300}"
    if [[ "${RES_INPUT^^}" == "O" ]]; then
        RESOLUCION_MODO="original"
        break
    elif [[ "$RES_INPUT" =~ ^[0-9]+$ ]]; then
        if (( RES_INPUT > 0 && RES_INPUT <= 100 )); then
            RESOLUCION_MODO="pct"
            RESOLUCION_VALOR="$RES_INPUT"
            break
        else
            log_error "Porcentaje debe ser entre 1 y 100."
        fi
    elif [[ "${RES_INPUT:0:1}" =~ [WwHh] ]]; then
        letra="${RES_INPUT:0:1}"
        num="${RES_INPUT:1}"
        num="${num## }"
        if [[ "$num" =~ ^[0-9]+$ ]] && (( num > 0 )); then
            if [[ "${letra^^}" == "W" ]]; then
                RESOLUCION_MODO="ancho"
            else
                RESOLUCION_MODO="alto"
            fi
            RESOLUCION_VALOR="$num"
            break
        else
            log_error "Debes indicar un número de píxeles válido (ej: H 300)."
        fi
    else
        log_error "Opción no reconocida. Usa O, 25-100, W <px> o H <px>."
    fi
done

RESIZE_STR=$(resolver_resize "$RESOLUCION_MODO" "$RESOLUCION_VALOR")

# ── 5. Sobrescritura ──
echo ""
echo -e "  ${C_GRIS}Política de sobrescritura:${C_RESET}"
echo -e "    ${C_GRIS}S${C_RESET}  Saltar si ya existe"
echo -e "    ${C_GRIS}R${C_RESET}  Reemplazar siempre"
echo -e "    ${C_GRIS}P${C_RESET}  Preguntar cada vez"
while true; do
    SOBRESCRIBIR=$(read_default "Sobrescritura" "S")
    SOBRESCRIBIR="${SOBRESCRIBIR^^}"
    case "$SOBRESCRIBIR" in
        S|R|P) break ;;
        *) log_error "Opción no válida. Usa S, R o P." ;;
    esac
done

# ── 6. Paralelismo ──
echo ""
MAX_HILOS=$(read_default "Trabajos en paralelo" "4")
if ! [[ "$MAX_HILOS" =~ ^[0-9]+$ ]] || (( MAX_HILOS < 1 )); then
    MAX_HILOS=1
fi

# ── 7. Escanear ──
echo ""
log_info "Escaneando '$DIR_ORIGEN'..."
eval "$(contar_archivos "$DIR_ORIGEN")"

TOTAL_ARCHIVOS="${total:-0}"

if (( TOTAL_ARCHIVOS == 0 )); then
    log_warn "No se encontraron archivos compatibles (PDF, JPG, PNG, TIFF, BMP, WEBP, GIF)."
    exit 0
fi

# ── 8. Resumen ──
echo ""
echo -e "${C_NEGRITA}══════════════════════════════════════════════════════${C_RESET}"
echo -e "  ${C_GRIS}Origen:${C_RESET}        $DIR_ORIGEN"
echo -e "  ${C_GRIS}Destino:${C_RESET}       $DIR_DESTINO"
echo -e "  ${C_GRIS}Página PDF:${C_RESET}    $PAGINA_PDF"
echo -e "  ${C_GRIS}Formato salida:${C_RESET} $FORMATO"
echo -e "  ${C_GRIS}Resolución:${C_RESET}    ${RESOLUCION_MODO^} ${RESOLUCION_VALOR}"
echo -e "  ${C_GRIS}Sobrescritura:${C_RESET} $SOBRESCRIBIR ($(case "$SOBRESCRIBIR" in S) echo "Saltar" ;; R) echo "Reemplazar" ;; P) echo "Preguntar" ;; esac))"
echo -e "  ${C_GRIS}Paralelismo:${C_RESET}   ${MAX_HILOS} hilo(s)"
echo -e "  ${C_GRIS}──────────────────────────────────────${C_RESET}"
echo -e "  ${C_NEGRITA}Archivos encontrados:${C_RESET}"
total_bytes=0
for tipo in pdf jpg png tiff bmp webp gif; do
    count_var="${tipo}"
    count="${!count_var:-0}"
    if (( count > 0 )); then
        bytes_var="${tipo}_b"
        bytes="${!bytes_var:-0}"
        total_bytes=$(( total_bytes + bytes ))
        printf "    %-5s %4d  (%s)\n" "${tipo^^}" "$count" "$(fmt_bytes $bytes)"
    fi
done
echo -e "  ${C_GRIS}──────────────────────────────────────${C_RESET}"
printf "    ${C_NEGRITA}%-5s %4d  (%s)${C_RESET}\n" "Total" "$TOTAL_ARCHIVOS" "$(fmt_bytes $total_bytes)"
echo -e "${C_NEGRITA}══════════════════════════════════════════════════════${C_RESET}"
echo ""

read -r -p "$(echo -e "${C_NEGRITA}¿Empezar?${C_RESET} [S/n]: ")" CONFIRMAR
CONFIRMAR="${CONFIRMAR:-S}"
if [[ "${CONFIRMAR^^}" != "S" ]]; then
    log_info "Cancelado."
    exit 0
fi

# ── 9. Procesamiento ──
echo ""
log_info "Procesando..."

LOGFILE="$DIR_DESTINO/extractor_de_portadas.log"
> "$LOGFILE"

TMPDIR_BASE=$(mktemp -d)
trap 'rm -rf "$TMPDIR_BASE"' EXIT

CONTADOR=0
ERRORES=0
SALTADOS=0

export DIR_ORIGEN DIR_DESTINO PAGINA_PDF FORMATO RESIZE_STR
export SOBRESCRIBIR LOGFILE TMPDIR_BASE
export C_VERDE C_AMARILLO C_ROJO C_CYAN C_GRIS C_NEGRITA C_RESET
export TOTAL_ARCHIVOS
export CONTADOR_FILE="$TMPDIR_BASE/contador"
export ERRORES_FILE="$TMPDIR_BASE/errores"
export SALTADOS_FILE="$TMPDIR_BASE/saltados"
> "$CONTADOR_FILE"
> "$ERRORES_FILE"
> "$SALTADOS_FILE"

procesar_archivo() {
    local archivo="$1"
    local ext="${archivo##*.}"
    ext="$(echo "$ext" | tr '[:upper:]' '[:lower:]')"
    local rel_path="${archivo#$DIR_ORIGEN/}"
    local dir_rel
    dir_rel="$(dirname "$rel_path")"
    local nombre_base
    nombre_base="$(basename "$archivo")"
    nombre_base="${nombre_base%.*}"

    # Crear subdirectorio espejo
    local subdir_dest="$DIR_DESTINO/$dir_rel"
    mkdir -p "$subdir_dest"

    local archivo_salida="$subdir_dest/[portada]_${nombre_base}.${FORMATO}"

    # Política de sobrescritura
    if [[ -f "$archivo_salida" ]]; then
        case "$SOBRESCRIBIR" in
            S)
                echo "1" >> "$SALTADOS_FILE"
                return 0
                ;;
            P)
                echo ""
                read -r -p "$(echo -e "${C_AMARILLO}¿Sobrescribir?${C_RESET} $archivo_salida [s/N]: ")" RES
                if [[ "${RES^^}" != "S" ]]; then
                    echo "1" >> "$SALTADOS_FILE"
                    return 0
                fi
                ;;
            R) ;;
        esac
    fi

    # Procesar
    local ok=0
    case "$ext" in
        pdf)
            local tmp_pdf="${TMPDIR_BASE}/pdf_${RANDOM}_${$}"
            if pdftoppm -f "$PAGINA_PDF" -l "$PAGINA_PDF" -png -r 150 "$archivo" "${tmp_pdf}" >/dev/null 2>>"$LOGFILE"; then
                local tmp_png="${tmp_pdf}-${PAGINA_PDF}.png"
                # Renombrar si pdftoppm usó padding
                if [[ ! -f "$tmp_png" ]]; then
                    tmp_png="${tmp_pdf}-$(printf "%02d" "$PAGINA_PDF").png"
                fi
                if [[ ! -f "$tmp_png" ]]; then
                    # Buscar cualquier png generado
                    tmp_png=$(ls "${tmp_pdf}"-*.png 2>/dev/null | head -1)
                fi
                if [[ -f "$tmp_png" ]]; then
                    if [[ -n "$RESIZE_STR" ]]; then
                        convert "$tmp_png" -resize "$RESIZE_STR" "$archivo_salida" 2>>"$LOGFILE" && ok=1
                    else
                        convert "$tmp_png" "$archivo_salida" 2>>"$LOGFILE" && ok=1
                    fi
                    rm -f "$tmp_png"
                fi
            fi
            rm -f "${tmp_pdf}"-*.png 2>/dev/null
            ;;
        jpg|jpeg|png|tif|tiff|bmp|webp|gif)
            if [[ -n "$RESIZE_STR" ]]; then
                convert "$archivo" -resize "$RESIZE_STR" "$archivo_salida" 2>>"$LOGFILE" && ok=1
            else
                # Copia directa si el formato es el mismo
                if [[ "$ext" == "$FORMATO" ]] || { [[ "$ext" == "jpeg" && "$FORMATO" == "jpg" ]]; }; then
                    cp "$archivo" "$archivo_salida" 2>>"$LOGFILE" && ok=1
                else
                    convert "$archivo" "$archivo_salida" 2>>"$LOGFILE" && ok=1
                fi
            fi
            ;;
    esac

    if (( ok )); then
        echo "1" >> "$CONTADOR_FILE"
    else
        echo "$archivo" >> "$LOGFILE"
        echo "1" >> "$ERRORES_FILE"
    fi

    # Mostrar progreso
    local cont=$(wc -l < "$CONTADOR_FILE" 2>/dev/null || echo 0)
    local err=$(wc -l < "$ERRORES_FILE" 2>/dev/null || echo 0)
    local skip=$(wc -l < "$SALTADOS_FILE" 2>/dev/null || echo 0)
    local done_total=$(( cont + err + skip ))
    echo -ne "\r  ${C_GRIS}[${done_total}/${TOTAL_ARCHIVOS}]${C_RESET} $(basename "$archivo")${C_GRIS}  (✓ $cont  ⚠ $err  ⏭ $skip)${C_RESET}   \033[K"
}

export -f procesar_archivo

# Recolectar archivos
ARCHIVOS=()
while IFS= read -r -d '' f; do
    ARCHIVOS+=("$f")
done < <(find "$DIR_ORIGEN" -type f \( \
    -iname '*.pdf' -o \
    -iname '*.jpg' -o -iname '*.jpeg' -o \
    -iname '*.png' -o \
    -iname '*.tif' -o -iname '*.tiff' -o \
    -iname '*.bmp' -o \
    -iname '*.webp' -o \
    -iname '*.gif' \) -print0 2>/dev/null)

# Ejecutar en paralelo o secuencial
if (( MAX_HILOS > 1 )); then
    printf "%s\0" "${ARCHIVOS[@]}" | xargs -0 -P "$MAX_HILOS" -I {} bash -c 'procesar_archivo "$@"' _ {}
else
    for f in "${ARCHIVOS[@]}"; do
        procesar_archivo "$f"
    done
fi

echo ""

# ── 10. Resumen final ──
CONTADOR=$(wc -l < "$CONTADOR_FILE" 2>/dev/null || echo 0)
ERRORES=$(wc -l < "$ERRORES_FILE" 2>/dev/null || echo 0)
SALTADOS=$(wc -l < "$SALTADOS_FILE" 2>/dev/null || echo 0)

echo ""
echo -e "${C_NEGRITA}══════════════════════════════════════════════════════${C_RESET}"
if (( ERRORES == 0 )); then
    echo -e "  ${C_VERDE}✅ Completado${C_RESET}"
else
    echo -e "  ${C_AMARILLO}⚠️  Completado con errores${C_RESET}"
fi
echo -e "  ${C_GRIS}Procesados:${C_RESET}  $CONTADOR"
echo -e "  ${C_GRIS}Errores:${C_RESET}    $ERRORES"
echo -e "  ${C_GRIS}Saltados:${C_RESET}   $SALTADOS"
if (( ERRORES > 0 )); then
    echo -e "  ${C_GRIS}Log:${C_RESET}         $LOGFILE"
fi
echo -e "${C_NEGRITA}══════════════════════════════════════════════════════${C_RESET}"
