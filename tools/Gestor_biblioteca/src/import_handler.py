from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .models import Item
from .io_pack import (
    detect_format,
    read_bibliotex_json,
    extract_zip_to_temp,
    BibliotexError,
)


@dataclass
class ImportOptions:
    comportamiento_duplicados: str = "saltar"
    modo_destino: str = "estructura"
    carpeta_destino: str = "Importados"


@dataclass
class ImportResult:
    importados: list[Item] = field(default_factory=list)
    saltados: list[dict] = field(default_factory=list)
    sobrescritos: list[Item] = field(default_factory=list)
    errores: list[dict] = field(default_factory=list)
    pdfs_faltantes: list[str] = field(default_factory=list)
    portadas_extraidas: int = 0


def import_file(
    path: str,
    library_root: str,
    portadas_root: str,
    opciones: Optional[ImportOptions] = None,
    existing_items: Optional[list[Item]] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    selected_indices: Optional[set[int]] = None,
) -> ImportResult:
    if opciones is None:
        opciones = ImportOptions()

    fmt = detect_format(path)

    def cb(step, msg):
        if progress_callback:
            progress_callback(step, msg)

    cb(0, "Leyendo archivo...")

    if fmt == "zip":
        items, metadata, portadas_extracted, pdfs_extracted = extract_zip_to_temp(
            path, portadas_root, library_root, progress_callback
        )
    elif fmt == "json":
        items_dicts, metadata = read_bibliotex_json(path)
        items = [Item.from_dict(d) for d in items_dicts]
        portadas_extracted = 0
    else:
        raise BibliotexError(
            "Formato no reconocido. Debe ser .bibliotex o .bibliotex.zip"
        )

    if selected_indices is not None:
        items = [items[i] for i in sorted(selected_indices) if i < len(items)]

    cb(50, f"Procesando {len(items)} items...")

    result = ImportResult(portadas_extraidas=portadas_extracted)

    existing = existing_items or []
    existing_by_hash: dict[str, Item] = {}
    for it in existing:
        if it.archivo_hash:
            existing_by_hash[it.archivo_hash] = it

    for idx, item in enumerate(items):
        pct = 50 + int(idx / max(len(items), 1) * 45)
        cb(pct, f"Procesando item {idx + 1}/{len(items)}...")

        try:
            _remap_destino(item, library_root, opciones)
        except Exception as e:
            result.errores.append({
                "item": item,
                "error": f"Error al remapear destino: {e}",
            })
            continue

        duplicado = existing_by_hash.get(item.archivo_hash) if item.archivo_hash else None

        if duplicado:
            if opciones.comportamiento_duplicados == "saltar":
                result.saltados.append(item.to_dict())
                continue
            elif opciones.comportamiento_duplicados == "sobrescribir":
                for key in (
                    "juego", "tipo", "idioma", "nombre_legible", "escaneado",
                    "confianza", "edicion", "descripcion", "justificacion",
                    "portada", "peso", "oculto", "contenido",
                ):
                    setattr(duplicado, key, getattr(item, key))
                if item.destino:
                    duplicado.destino = item.destino
                result.sobrescritos.append(duplicado)
                continue
            else:
                result.saltados.append(item.to_dict())
                continue

        _check_pdf_existence(item, library_root, result)

        if item.portada:
            pr = Path(portadas_root) if portadas_root else None
            if not pr or not (pr / item.portada).exists():
                item.portada = ""

        result.importados.append(item)

    cb(98, "Completado...")
    cb(100, "Listo")

    return result


def _remap_destino(item: Item, library_root: str, opciones: ImportOptions):
    if not item.destino:
        return

    if opciones.modo_destino == "carpeta_fija" and opciones.carpeta_destino:
        item.destino = opciones.carpeta_destino.rstrip("/") + "/"
        return

    if library_root:
        dest_path = Path(library_root, item.destino)
        if item.destino.endswith("/"):
            dest_path.mkdir(parents=True, exist_ok=True)
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)


def _check_pdf_existence(
    item: Item, library_root: str, result: ImportResult
):
    if not library_root:
        return

    if item.nombre_legible and item.destino:
        pdf = Path(library_root) / item.destino / item.nombre_legible
        if pdf.exists():
            return
    pdf = Path(library_root) / (item.destino or item.nombre_legible or "")
    if pdf.exists():
        return

    rel = str(Path(item.destino or ".") / (item.nombre_legible or ""))
    result.pdfs_faltantes.append(rel)
