import json
from pathlib import Path
from typing import List, Tuple

from .models import Item, FORMAT_VERSION


def load(path: str) -> Tuple[List[Item], dict, set, dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No se encuentra el archivo: {path}")

    raw = p.read_text(encoding="utf-8")
    data = json.loads(raw)

    metadata = {
        "format_version": 0,
        "nombre_biblioteca": "Biblioteca sin nombre",
        "url_base": "",
        "library_root": "",
        "portadas_root": "",
        "web_root": "",
        "catalogo_js_path": "",
    }

    if isinstance(data, list):
        items = data
        dir_visible = {}
        directorios = set()
    elif isinstance(data, dict) and "clasificaciones" in data:
        items = data["clasificaciones"]
        dir_visible = data.get("dir_visible", {})
        directorios = set(data.get("directorios", []))
        metadata["format_version"] = data.get("format_version", 0)
        metadata["nombre_biblioteca"] = data.get("nombre_biblioteca", "Biblioteca sin nombre")
        metadata["url_base"] = data.get("url_base", "")
        metadata["library_root"] = data.get("library_root", "")
        metadata["portadas_root"] = data.get("portadas_root", "")
        metadata["web_root"] = data.get("web_root", "")
        metadata["catalogo_js_path"] = data.get("catalogo_js_path", "")
    else:
        raise ValueError("Formato JSON inválido: debe ser un array o tener clave 'clasificaciones'")

    return [Item.from_dict(item) for item in items], dir_visible, directorios, metadata


ROOT_PATH_KEYS = ["library_root", "portadas_root", "web_root", "catalogo_js_path"]


def save(items: List[Item], path: str, dir_visible: dict = None,
         directorios: set = None, nombre_biblioteca: str = "",
         url_base: str = "", **paths) -> str:
    p = Path(path)
    data = {
        "format_version": FORMAT_VERSION,
        "nombre_biblioteca": nombre_biblioteca or "Biblioteca sin nombre",
        "clasificaciones": [item.to_dict() for item in items],
    }
    if url_base:
        data["url_base"] = url_base
    for key in ROOT_PATH_KEYS:
        val = paths.get(key, "")
        if val:
            data[key] = val
    if dir_visible:
        data["dir_visible"] = dir_visible
    if directorios:
        data["directorios"] = sorted(directorios)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    p.write_text(text, encoding="utf-8")
    return str(p)


def save_catalogo_js(items: List[Item], output_path: str, dir_visible: dict = None,
                     nombre_biblioteca: str = "", url_base: str = "") -> str:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "format_version": FORMAT_VERSION,
        "nombre_biblioteca": nombre_biblioteca or "Biblioteca sin nombre",
        "clasificaciones": [item.to_dict() for item in items],
    }
    if url_base:
        data["url_base"] = url_base
    if dir_visible:
        data["dir_visible"] = dir_visible

    with open(p, "w", encoding="utf-8") as f:
        f.write("const CATALOGO_DATA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    return str(p)



