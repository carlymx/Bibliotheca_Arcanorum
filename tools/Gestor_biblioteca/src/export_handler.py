from pathlib import Path
from typing import Callable, Optional

from .models import Item
from .io_pack import write_bibliotex_json, write_bibliotex_zip
from .portada_mgr import resolve_portada_file


def export_items(
    items: list[Item],
    destino: str,
    formato: str,
    incluir_portadas: bool = False,
    incluir_pdfs: bool = False,
    comentario: str = "",
    biblioteca_origen: str = "",
    library_root: str = "",
    portadas_root: str = "",
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> str:
    if not items:
        raise ValueError("No hay items para exportar")

    portada_paths: list[str] = []
    pdf_paths: list[str] = []

    if formato == "zip" and (incluir_portadas or incluir_pdfs):
        if incluir_portadas and portadas_root:
            for item in items:
                if item.has_portada():
                    found = resolve_portada_file(
                        portadas_root,
                        item.destino,
                        Path(item.nombre_legible).stem,
                    )
                    if found and found.exists():
                        portada_paths.append(str(found))

        if incluir_pdfs and library_root:
            for item in items:
                pdf = _resolve_pdf_path(library_root, item)
                if pdf:
                    pdf_paths.append(str(pdf))

    meta_kw = {
        "comentario": comentario,
        "biblioteca_origen": biblioteca_origen,
        "directorio_base": library_root or "",
    }

    if formato == "zip":
        return write_bibliotex_zip(
            destino,
            items,
            portada_paths=portada_paths,
            pdf_paths=pdf_paths,
            portadas_root=portadas_root,
            library_root=library_root,
            progress_callback=progress_callback,
            **meta_kw,
        )
    else:
        return write_bibliotex_json(destino, items, **meta_kw)


def _resolve_pdf_path(library_root: str, item: Item) -> Optional[Path]:
    if not item.destino and not item.nombre_legible:
        return None
    if item.nombre_legible and item.destino:
        pdf = Path(library_root) / item.destino / item.nombre_legible
        if pdf.exists():
            return pdf
    pdf = Path(library_root) / (item.destino or item.nombre_legible or "")
    if pdf.exists():
        return pdf
    return None
