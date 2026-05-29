import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from .models import Item

BIBLIOTEX_FORMAT_VERSION = 1
BIBLIOTEX_JSON_EXT = ".bibliotex"
BIBLIOTEX_ZIP_EXT = ".bibliotex.zip"


class BibliotexError(Exception):
    pass


class InvalidFormatError(BibliotexError):
    pass


class UnsupportedVersionError(BibliotexError):
    pass


def _build_metadata(
    biblioteca_origen: str = "",
    comentario: str = "",
    directorio_base: str = "",
    app_version: str = "0.9.2",
) -> dict:
    return {
        "format_version": BIBLIOTEX_FORMAT_VERSION,
        "tipo_exportacion": "item_selection",
        "fecha_exportacion": datetime.now(timezone.utc).isoformat(),
        "app_version": app_version,
        "biblioteca_origen": biblioteca_origen,
        "comentario": comentario,
        "directorio_base": directorio_base,
    }


def _validate_metadata(metadata: dict):
    fv = metadata.get("format_version", 0)
    if not isinstance(fv, int) or fv < 1:
        raise InvalidFormatError(
            "El archivo no es un formato .bibliotex válido"
        )
    if fv > BIBLIOTEX_FORMAT_VERSION:
        raise UnsupportedVersionError(
            f"Este archivo fue creado con una versión más reciente "
            f"(v{fv}). La app soporta hasta v{BIBLIOTEX_FORMAT_VERSION}. "
            "Algunos campos podrían no importarse correctamente."
        )
    if "items" not in metadata or not isinstance(metadata["items"], list):
        raise InvalidFormatError(
            "El archivo .bibliotex no contiene la clave 'items'"
        )


def write_bibliotex_json(
    path: str,
    items: list[Item],
    metadata: Optional[dict] = None,
    **meta_kw,
) -> str:
    p = Path(path)
    meta = {**(_build_metadata(**meta_kw)), **(metadata or {})}
    meta["items"] = [item.to_dict() for item in items]
    p.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(p)


def read_bibliotex_json(path: str) -> tuple[list[dict], dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No se encuentra el archivo: {path}")

    raw = p.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise InvalidFormatError("El archivo .bibliotex no contiene un objeto JSON válido")

    _validate_metadata(data)

    items = data.pop("items", [])
    return items, data


def write_bibliotex_zip(
    path: str,
    items: list[Item],
    portada_paths: Optional[list[str]] = None,
    pdf_paths: Optional[list[str]] = None,
    metadata: Optional[dict] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    portadas_root: str = "",
    library_root: str = "",
    **meta_kw,
) -> str:
    p = Path(path)

    def cb(step, msg):
        if progress_callback:
            progress_callback(step, msg)

    cb(0, "Preparando metadatos...")
    meta = {**(_build_metadata(**meta_kw)), **(metadata or {})}
    meta["items"] = [item.to_dict() for item in items]

    cb(15, "Escribiendo metadatos...")
    json_bytes = json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8")

    portada_paths = portada_paths or []
    pdf_paths = pdf_paths or []
    total_files = 1 + len(portada_paths) + len(pdf_paths)
    processed = 0

    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("metadata.bibliotex", json_bytes)
        processed += 1

        portadas_written = 0
        for src in portada_paths:
            sp = Path(src)
            if sp.exists() and portadas_root:
                try:
                    rel = str(sp.relative_to(Path(portadas_root)))
                except ValueError:
                    rel = sp.name
                arcname = f"portadas/{rel}"
                zf.write(str(sp), arcname)
                portadas_written += 1
            processed += 1
            pct = 15 + int(processed / total_files * 70) if total_files > 1 else 85
            cb(pct, f"Portadas: {portadas_written}/{len(portada_paths)}")

        pdfs_written = 0
        for src in pdf_paths:
            sp = Path(src)
            if sp.exists() and library_root:
                try:
                    rel = str(sp.relative_to(Path(library_root)))
                except ValueError:
                    rel = sp.name
                arcname = f"pdfs/{rel}"
                zf.write(str(sp), arcname)
                pdfs_written += 1
            processed += 1
            pct = 15 + int(processed / total_files * 70) if total_files > 1 else 85
            cb(pct, f"PDFs: {pdfs_written}/{len(pdf_paths)}")

        cb(90, "Finalizando...")

    cb(100, "Completado")
    return str(p)


def read_bibliotex_zip(
    path: str,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    load_portadas: bool = True,
    load_pdfs: bool = True,
) -> tuple[list[dict], dict, dict[str, bytes], dict[str, bytes]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No se encuentra el archivo: {path}")

    def cb(step, msg):
        if progress_callback:
            progress_callback(step, msg)

    cb(0, "Leyendo paquete...")

    with zipfile.ZipFile(p, "r") as zf:
        names = zf.namelist()

        if "metadata.bibliotex" not in names:
            raise InvalidFormatError(
                "Falta metadata.bibliotex en el paquete ZIP"
            )

        raw = zf.read("metadata.bibliotex")
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise InvalidFormatError("metadata.bibliotex no contiene un JSON válido")

        _validate_metadata(data)

        items = data.pop("items", [])

        portadas: dict[str, bytes] = {}
        pdfs: dict[str, bytes] = {}

        for name in names:
            if name == "metadata.bibliotex":
                continue
            if name.endswith("/"):
                continue
            if name.startswith("portadas/") and load_portadas:
                portadas[name[len("portadas/"):]] = zf.read(name)
            elif name.startswith("pdfs/") and load_pdfs:
                pdfs[name[len("pdfs/"):]] = zf.read(name)

    cb(100, "Completado")
    return items, data, portadas, pdfs


def detect_format(path: str) -> str:
    p = Path(path)
    if str(p).endswith(BIBLIOTEX_ZIP_EXT):
        return "zip"
    if str(p).endswith(BIBLIOTEX_JSON_EXT):
        return "json"
    if p.suffix == ".zip":
        return "zip"
    return "unknown"


def extract_zip_to_temp(
    path: str,
    portadas_root: str,
    library_root: str = "",
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> tuple[list[Item], dict, int, int]:
    items_dicts, metadata, portadas_data, pdfs_data = read_bibliotex_zip(
        path, progress_callback
    )

    items = [Item.from_dict(d) for d in items_dicts]

    portadas_extracted = 0
    if portadas_root and portadas_data:
        pr = Path(portadas_root)
        pr.mkdir(parents=True, exist_ok=True)
        for relpath, data in portadas_data.items():
            dest = pr / relpath
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            portadas_extracted += 1

    pdfs_extracted = 0
    if library_root and pdfs_data:
        lr = Path(library_root)
        lr.mkdir(parents=True, exist_ok=True)
        for relpath, data in pdfs_data.items():
            dest = lr / relpath
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            pdfs_extracted += 1

    return items, metadata, portadas_extracted, pdfs_extracted
