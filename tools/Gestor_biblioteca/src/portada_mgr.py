import os
import shutil
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import Item

PORTADA_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def _web_rel_path(abs_path: str, web_root: str) -> str:
    """Returns the relative path from web_root to abs_path.
    Falls back to just the filename if web_root is empty."""
    if not web_root:
        return Path(abs_path).name
    return os.path.relpath(abs_path, web_root)


def resolve_portada_file(portadas_root: str, destino: str,
                          nombre_stem: str) -> Optional[Path]:
    """Search for an existing portada file with any supported extension.
    First tries exact match, then case-insensitive fallback."""
    base = Path(portadas_root) / destino / f"[portada]_{nombre_stem}"
    for ext in PORTADA_EXTENSIONS:
        candidate = base.with_suffix(ext)
        if candidate.exists():
            return candidate

    dest_dir = Path(portadas_root) / destino
    if dest_dir.exists():
        prefix = f"[portada]_{nombre_stem}.".lower()
        valid_suffixes = {s.lower() for s in PORTADA_EXTENSIONS}
        for f in dest_dir.iterdir():
            if (f.is_file()
                    and f.name.lower().startswith(prefix)
                    and f.suffix.lower() in valid_suffixes):
                return f
    return None


def upload(item: Item, source_path: str, portadas_root: str,
           web_root: str = "") -> str:
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"La imagen no existe: {source_path}")

    portadas_dir = Path(portadas_root)
    dest_dir = portadas_dir / item.destino
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_file = dest_dir / item.portada_filename(".jpg")

    if src.resolve() != dest_file.resolve():
        shutil.copy2(str(src), str(dest_file))

    item.portada = _web_rel_path(str(dest_file), web_root)

    return str(dest_file)


def find_existing(item: Item, portadas_root: str) -> Optional[str]:
    found = resolve_portada_file(
        portadas_root, item.destino, Path(item.nombre_legible).stem)
    return str(found) if found else None


def move_portada(item: Item, old_destino: str, new_destino: str,
                 portadas_root: str, web_root: str = "") -> Optional[str]:
    if not item.portada:
        return None

    old_file = resolve_portada_file(
        portadas_root, old_destino, Path(item.nombre_legible).stem)
    if not old_file:
        return None

    new_dir = Path(portadas_root) / new_destino
    new_dir.mkdir(parents=True, exist_ok=True)
    new_file = new_dir / old_file.name

    shutil.move(str(old_file), str(new_file))

    item.portada = _web_rel_path(str(new_file), web_root)

    return str(new_file)


def delete(item: Item, portadas_root: str) -> bool:
    found = resolve_portada_file(
        portadas_root, item.destino, Path(item.nombre_legible).stem)
    if not found:
        return False

    found.unlink()
    item.portada = ""
    return True


# ── index / search for missing portadas ─────────────────────


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return nfkd.encode("ascii", "ignore").decode("ascii").lower()


def build_portada_index(portadas_root: str) -> dict:
    root = Path(portadas_root)
    exact: Dict[str, List[Tuple[str, str]]] = {}
    fuzzy: Dict[str, List[Tuple[str, str, str]]] = {}
    valid_suffixes = {s.lower() for s in PORTADA_EXTENSIONS}

    if root.exists():
        for f in sorted(root.rglob("[portada]_*")):
            if (not f.is_file()
                    or not f.name.startswith("[portada]_")
                    or f.suffix.lower() not in valid_suffixes):
                continue
            filename = f.name
            rel_dir = str(f.parent.relative_to(root))
            abs_path = str(f)
            exact.setdefault(filename, []).append((rel_dir, abs_path))
            norm = _normalize(filename)
            fuzzy.setdefault(norm, []).append((rel_dir, abs_path, filename))

    return {"exact": exact, "fuzzy": fuzzy}


def find_missing_portadas(
    items: List[Item], portadas_root: str, index: dict
) -> dict:
    results = {
        "ok": [],
        "exact": [],
        "fuzzy": [],
        "not_found": [],
    }

    for item in items:
        found = resolve_portada_file(
            portadas_root, item.destino, Path(item.nombre_legible).stem)
        if found:
            results["ok"].append((item, str(found)))
            continue

        stem = Path(item.nombre_legible).stem
        matched = False
        for ext in PORTADA_EXTENSIONS:
            filename = f"[portada]_{stem}{ext}"

            if filename in index["exact"]:
                rel_dir, abs_path = index["exact"][filename][0]
                results["exact"].append((item, abs_path, rel_dir))
                matched = True
                break

            norm = _normalize(filename)
            if norm in index["fuzzy"]:
                rel_dir, abs_path, orig = index["fuzzy"][norm][0]
                results["fuzzy"].append((item, abs_path, rel_dir, orig))
                matched = True
                break

        if not matched:
            results["not_found"].append(item)

    return results


def make_web_path(rel_dir: str, filename: str, portadas_root: str,
                  web_root: str) -> str:
    abs_path = str(Path(portadas_root) / rel_dir / filename)
    return _web_rel_path(abs_path, web_root)


def move_item(item: Item, old_destino: str, new_destino: str,
              library_root: str):
    origen = Path(library_root) / old_destino / item.nombre_legible
    destino = Path(library_root) / new_destino / item.nombre_legible
    if origen.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origen), str(destino))
